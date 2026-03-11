# CLAUDE.md — DichVuCong AI Assistant

## Project Overview

A mock Vietnamese government public administration portal (dichvucong.gov.vn) with an AI assistant. **Backend logic, RAG architecture, and multi-agent orchestration are the primary focus. Frontend is secondary.**

---

## Stack at a Glance

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), Tailwind, React Hook Form + Zod, Zustand |
| Backend | FastAPI (Python, async), SQLAlchemy 2.0, Alembic, Celery + Redis |
| AI | Claude claude-sonnet-4-20250514 (Anthropic), bge-m3 embeddings, LangGraph agents |
| Vector DB | Qdrant |
| OCR | PaddleOCR (primary), Tesseract (fallback) |
| PDF | pdfplumber, pdfrw, reportlab |
| Document Parsing | Docling (IBM) |
| Storage | MinIO (S3-compatible), PostgreSQL, Redis |

---

## Repository Structure

```
dichvucong/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Route handlers (thin — no business logic here)
│   │   ├── agents/          # LangGraph graph, state, nodes/, prompts/
│   │   ├── core/            # Pure domain logic (no FastAPI imports)
│   │   ├── services/        # Infrastructure wrappers (LLM, Qdrant, OCR, PDF, Redis)
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic v2 request/response schemas
│   │   └── ingestion/       # Offline scripts (ingest legal docs, seed procedures, mock data gen)
│   ├── data/
│   │   ├── legal_documents/ # Raw Vietnamese legal PDFs
│   │   ├── form_templates/  # Blank government PDF forms
│   │   └── mock_documents/  # Synthetic CCCD images etc.
│   └── tests/
│       ├── unit/
│       └── integration/
└── frontend/
    ├── app/                 # Next.js App Router pages
    ├── components/          # chat/, forms/, documents/, ui/
    └── lib/                 # api/, stores/, types/
```

---

## Critical Architecture Rules

### 1. The Procedure DAG is the Core of the System

All other features (RAG, OCR, form fill) exist to serve the procedure dependency graph. When in doubt about any design decision, ask: "does this make it easier or harder to resolve procedure dependencies correctly?"

The DAG lives in PostgreSQL as a self-referential adjacency list (`procedure_dependencies` table). Traversal and topological sort happen in `backend/app/core/procedure_graph.py` — pure Python, no DB queries inside, no FastAPI.

```python
# CORRECT — dependency resolution is pure domain logic
# backend/app/core/procedure_graph.py
def resolve_execution_plan(
    target_procedure_id: str,
    all_dependencies: list[ProcedureDependency],
    completed_ids: set[str]
) -> list[ProcedureStep]:
    # Topological sort, gap analysis, return ordered plan
    ...

# WRONG — never put graph traversal inside a route handler or agent node
@router.get("/procedures/{id}/plan")
async def get_plan(id: str, db: AsyncSession = Depends(get_db)):
    # Do NOT put topological sort logic here
    ...
```

### 2. API Routes are Thin

Route handlers in `app/api/v1/` do three things only: validate input (Pydantic does this automatically), call a service or agent, return a response. No business logic, no direct DB queries, no LLM calls.

> **Skills:** Run `/fastapi` before writing or refactoring any route handler or service file. Run `/review-api-route` on your output before marking the task complete.

```python
# CORRECT
@router.post("/chat")
async def chat(request: ChatRequest, agent: AgentGraph = Depends(get_agent)):
    return StreamingResponse(agent.stream(request), media_type="text/event-stream")

# WRONG
@router.post("/chat")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    chunks = await db.execute(select(LegalDocument)...)  # No. Move this to a service.
    response = anthropic.messages.create(...)             # No. Move this to the agent.
```

### 3. Agent State is the Single Source of Truth Per Invocation

`AgentState` (TypedDict in `app/agents/state.py`) is the only thing passed between LangGraph nodes. Nodes must be pure functions: they receive state, return a partial state update. No globals, no shared mutable objects between nodes.

```python
# CORRECT — node returns a partial state dict
def rag_node(state: AgentState) -> dict:
    chunks = qdrant_service.search(state["user_message"])
    return {"retrieved_chunks": chunks, "citations": build_citations(chunks)}

# WRONG — node mutates state in place or calls other nodes directly
def rag_node(state: AgentState) -> AgentState:
    state["retrieved_chunks"] = qdrant_service.search(...)  # mutation — bad
    state = form_filler_node(state)                          # direct call — bad
    return state
```

### 4. Session Data Lives in Redis, Not Agent State

Cross-turn data (accumulated PersonalData, list of completed procedures, partial form fills) is stored in Redis keyed by `session_id`. It is loaded into `AgentState` at the start of each invocation and saved back at the end. Agent state is always reconstructed fresh — never persisted directly.

```python
# Pattern for every agent invocation entry point
async def run(session_id: str, message: str) -> AsyncIterator[str]:
    session = await redis_service.get_session(session_id)   # load
    initial_state = AgentState(
        session_id=session_id,
        user_message=message,
        personal_data=session.personal_data,
        completed_procedures=session.completed_procedure_ids,
        ...
    )
    async for chunk in graph.astream(initial_state):
        yield chunk
    await redis_service.save_session(session_id, extract_session(final_state))  # save
```

### 5. Core Domain Logic Has Zero Infrastructure Dependencies

Everything in `app/core/` must be importable and testable without a running database, Redis, LLM, or Qdrant. If a function in `core/` needs to call an external service, it is in the wrong place — move it to `services/` or an agent node.

```python
# backend/app/core/procedure_graph.py
# CORRECT — no imports from services/, no DB sessions, no HTTP calls
from app.schemas.procedure import ProcedureDependency, ProcedureStep

def topological_sort(deps: list[ProcedureDependency]) -> list[str]: ...
def find_missing_prerequisites(plan: list[str], completed: set[str]) -> list[str]: ...
```

---

## Data Models — What Matters Most

> **Skills:** Run `/review-schema` after writing or modifying any file in `app/schemas/`.

### PersonalData (the carry-forward contract)

`app/schemas/personal_data.py` — this schema is the interface between OCR output and form fill input. Every field must be optional (OCR is imperfect) and carry a per-field confidence score.

```python
class PersonalData(BaseModel):
    full_name: str | None = None
    full_name_latin: str | None = None   # No diacritics — required by some forms
    date_of_birth: date | None = None
    gender: Literal["Nam", "Nữ"] | None = None
    nationality: str = "Việt Nam"
    id_number: str | None = None
    id_issue_date: date | None = None
    id_issue_place: str | None = None
    permanent_address: Address | None = None
    temporary_address: Address | None = None

    # Provenance — never omit these
    source_document_type: str
    source_image_path: str
    extraction_confidence: float          # overall document confidence
    field_confidences: dict[str, float]   # per-field confidence
    extracted_at: datetime
```

### AgentState (the agent contract)

`app/agents/state.py` — add fields here when a new node needs to communicate data downstream. Never add fields for data that belongs in the session (Redis).

```python
class AgentState(TypedDict):
    # --- Input ---
    user_message: str
    uploaded_image_path: str | None
    session_id: str

    # --- Routing ---
    intent: Literal["procedure_inquiry", "document_ocr", "form_fill",
                    "legal_question", "dependency_check"]
    entities: dict[str, Any]

    # --- RAG ---
    retrieved_chunks: list[DocumentChunk]
    citations: list[Citation]

    # --- OCR (this invocation only — persist to Redis after) ---
    personal_data: PersonalData | None
    document_type: str | None

    # --- Procedure ---
    target_procedure_id: str | None
    procedure_execution_plan: list[ProcedureStep]
    completed_procedures: list[str]        # loaded from Redis at start

    # --- Form ---
    form_id: str | None
    filled_fields: dict[str, Any]
    unfilled_required_fields: list[str]

    # --- Output ---
    final_response: str
    response_metadata: dict

    # --- Control ---
    iteration_count: int
    errors: list[str]
```

---

## LangGraph Node Conventions

All nodes live in `app/agents/nodes/`. Each file exports exactly one function named after the node.

```
nodes/
├── router.py           → router_node(state) + route_after_classification(state) -> str
├── rag.py              → rag_node(state)
├── ocr.py              → ocr_node(state)
├── procedure_planner.py → procedure_planner_node(state)
├── form_filler.py      → form_filler_node(state)
└── synthesizer.py      → synthesizer_node(state)
```

**Routing:** Conditional edges use a dedicated function (not a lambda) so they are testable.

```python
# app/agents/nodes/router.py
def route_after_classification(state: AgentState) -> str:
    """Returns the name of the next node. Must be pure — no side effects."""
    intent = state["intent"]
    has_image = state["uploaded_image_path"] is not None

    if has_image and intent in ("document_ocr", "form_fill"):
        return "ocr_node"
    if intent in ("procedure_inquiry", "dependency_check"):
        return "procedure_planner_node"
    if intent == "legal_question":
        return "rag_node"
    return "rag_node"  # safe default
```

**Graph assembly** (`app/agents/graph.py`) is the only place that imports all nodes and wires them together. It is not imported anywhere else except the FastAPI dependency.

> **Skills:** Before implementing or modifying any node, read its `.claude/agents/` spec. Run `/review-agent-node` on the finished node before marking the task complete.

---

## .claude/ Directory

The `.claude/` directory contains three subsystems that govern how Claude Code behaves on this project. Read the relevant files before implementing any feature.

### Hooks — Automated Guardrails

Hooks in `.claude/hooks/` run automatically before and after every tool use. They cannot be bypassed from within Claude Code. If a hook blocks an operation, its error message will state the exact rule violated and the relevant `CLAUDE.md` section.

| Hook | Trigger | Enforces |
|---|---|---|
| `pre-bash.sh` | Before every bash command | Blocks destructive commands (rm -rf, DROP TABLE, force push, remote pipe-to-shell) |
| `check-env-safety.sh` | Before bash + file writes | Prevents accessing real `.env` files or echoing secret variable values |
| `check-migration.sh` | Before any file write | Prevents modifying committed Alembic migrations |
| `check-test-imports.sh` | Before writing to `tests/unit/` | Prevents direct infrastructure instantiation in unit tests |
| `pre-tool-use.sh` | Before Edit/Write/Create | Enforces: `app/core/` has no service imports; route handlers have no direct LLM imports |
| `post-tool-use.sh` | After every bash command | Surfaces pytest failures, Alembic errors, and import errors |

If you need to run a legitimately blocked command (e.g., `DROP TABLE` during a manual environment reset), run it directly in your terminal outside Claude Code. Never modify hooks to permit a one-off operation — add a targeted exemption with a comment if the pattern is genuinely needed.

### Skills — Development and Review Workflows

Skills live in `.claude/skills/` (code-review checklists) and `.agents/skills/` (development guides). Invoke any skill with `/skill-name` in the chat.

#### Development Skills — invoke before starting a feature area

| Skill | Invoke | Use When |
|---|---|---|
| FastAPI best practices | `/fastapi` | Writing or refactoring any file in `app/api/v1/` or `app/services/` |
| FastAPI Best Architecture | `/fba` | Designing service/repository layers or plugin patterns |
| Next.js App Router | `/nextjs-app-router-fundamentals` | Adding pages, layouts, or routing in `frontend/src/app/` |
| React Hook Form + Zod | `/react-hook-form-zod` | Building or modifying any validated form in the frontend |
| UI Components | `/building-components` | Creating new reusable components in `frontend/src/components/` |
| Tailwind design system | `/tailwind-design-system` | Extending or standardising Tailwind tokens and patterns |

#### Code Review Skills — run on your own output before marking a task complete

| Skill | Invoke | Use For |
|---|---|---|
| Review agent node | `/review-agent-node` | Any file in `app/agents/nodes/` |
| Review schema | `/review-schema` | Any file in `app/schemas/` |
| Review migration | `/review-migration` | Any new Alembic migration before committing |
| Review API route | `/review-api-route` | Any file in `app/api/v1/` |

### Agents — Behavioural Specifications

Files in `.claude/agents/` define the complete behavioural contract for each LangGraph node: inputs, outputs, processing rules, error handling, and which prompt file to use.

**Read the spec file before implementing or modifying any node.**
**If the implementation needs to diverge from the spec, update the spec first and explain why in the commit.**

| Spec File | Node |
|---|---|
| `router-agent.md` | `router_node` — intent classification and routing |
| `rag-agent.md` | `rag_node` — hybrid retrieval and citation generation |
| `ocr-agent.md` | `ocr_node` — document image extraction pipeline |
| `procedure-planner-agent.md` | `procedure_planner_node` — dependency resolution |
| `form-filler-agent.md` | `form_filler_node` — semantic field mapping and PDF fill |
| `synthesizer-agent.md` | `synthesizer_node` — final response assembly |

---

## Frontend Development

The frontend is secondary to the backend, but the following skills keep it consistent:

| Task | Skill |
|---|---|
| New page or layout in `frontend/src/app/` | `/nextjs-app-router-fundamentals` |
| New reusable component in `frontend/src/components/` | `/building-components` |
| Any form with validation | `/react-hook-form-zod` |
| Tailwind tokens, spacing, or colour system changes | `/tailwind-design-system` |

---

## RAG — Implementation Notes

### Chunking (do not change this without a good reason)

Legal documents must be chunked at **article boundaries**. A chunk never spans two articles. This is enforced in `app/ingestion/ingest_legal_docs.py`. The article number and decree reference are stored as Qdrant payload — they are what make citations possible.

### Hybrid Search (always use both stages)

Never call Qdrant with dense search only. BM25 is critical because users query by decree number ("Nghị định 123") and article number ("Điều 15"), which are exact-match queries that semantic search handles poorly.

```python
# app/services/qdrant_service.py
async def search(
    query: str,
    procedure_id: str | None = None,
    top_k: int = 8
) -> list[DocumentChunk]:
    semantic = await self._dense_search(query, procedure_id, top_k * 2)
    lexical = self._bm25_search(query, top_k * 2)
    return self._rrf_merge(semantic, lexical, top_k)
```

### Citation Format

Every legal claim in an LLM response must map to a chunk that was actually retrieved. The citation format is: `[Điều X, Nghị định/Thông tư YYY/YYYY/NĐ-CP]`. The LLM prompt enforces this — see `app/agents/prompts/rag_prompt.py`. Do not change the prompt without updating the citation parser in `app/core/citation_formatter.py`.

---

## OCR — Implementation Notes

### Pre-processing is Not Optional

Raw uploaded images must go through OpenCV pre-processing (deskew, CLAHE, denoise) before PaddleOCR. Skipping this step causes significant accuracy drops on government document scans.

```python
# app/services/ocr_service.py
async def extract(image_path: str, document_type: str) -> PersonalData:
    img = cv2.imread(image_path)
    img = _deskew(img)
    img = _clahe(img)
    img = _denoise(img)
    raw_text = paddleocr_engine.ocr(img)
    return await _llm_field_extraction(raw_text, document_type)
```

### LLM Field Extraction Prompt

The OCR LLM call uses a dedicated prompt in `app/agents/prompts/ocr_extraction_prompt.py`. It receives the raw OCR text and the detected document type, and returns a JSON object matching `PersonalData`. The prompt must instruct the model to return `null` for fields it cannot find — never guess or hallucinate a value.

---

## Form Fill — Implementation Notes

### Never Hard-Code Field Mappings

Do not create a file like `cccd_to_form_a_mapping.py`. The semantic field mapper (`app/core/form_field_mapper.py`) uses the LLM to map `PersonalData` fields to PDF form field names at runtime. Adding a new PDF template requires no code changes.

### PDF Type Detection

The PDF service must detect whether a template is an AcroForm (fillable fields) or a flat PDF before attempting to fill it. Using pdfrw on a flat PDF will silently produce an unfilled output.

```python
# app/services/pdf_service.py
def fill(template_path: str, field_values: dict[str, str]) -> str:
    reader = PdfReader(template_path)
    if reader.get_fields():
        return _fill_acroform(template_path, field_values)
    else:
        return _fill_overlay(template_path, field_values)  # reportlab overlay
```

### Carry-Forward Merge Rule

When `SessionDataAccumulator.merge()` combines two `PersonalData` objects, the higher-confidence value always wins. Never overwrite a high-confidence extraction with a low-confidence one just because it is newer.

---

## Database Conventions

- All primary keys are `UUID` (PostgreSQL `gen_random_uuid()`), never auto-increment integers.
- All timestamps are `TIMESTAMPTZ` (timezone-aware), never `TIMESTAMP`.
- The procedure dependency graph uses a **nullable `condition_description` TEXT column** for conditional dependencies (e.g., "only if not a city resident"). Do not model conditions as separate tables — the LLM reads the text description when building the execution plan.
- JSONB columns (`fields` on `form_templates`, `personal_data` on `sessions`) are used for schema-flexible data only. Structured, queryable data goes in proper columns.
- All migrations are in `backend/alembic/versions/`. Never modify a committed migration — add a new one.

---

## Testing Priorities

Test these things first, in this order:

1. `test_procedure_graph.py` — topological sort, cycle detection, gap analysis. This is pure Python and must have 100% coverage.
2. `test_form_mapper.py` — field mapping logic, merge rules, confidence-based overwrite.
3. `test_ocr_extraction.py` — field extraction from synthetic CCCD images.
4. `test_rag_pipeline.py` — integration test: ingest a real legal PDF, retrieve a chunk, verify citation metadata is present.
5. `test_agent_graph.py` — integration test: run the full graph end-to-end with a mocked LLM.

LLM calls in unit tests must always be mocked. Never make real API calls in `tests/unit/`.

---

## Environment Variables

```bash
# LLM
ANTHROPIC_API_KEY=

# Databases
POSTGRES_URL=postgresql+asyncpg://user:pass@localhost:5432/dichvucong
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333

# Storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_BUCKET=dichvucong

# Embeddings (choose one)
EMBEDDING_BACKEND=bge-m3          # or "openai"
OPENAI_API_KEY=                    # only needed if EMBEDDING_BACKEND=openai

# Observability
LANGSMITH_API_KEY=
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=dichvucong
```

---

## Common Mistakes to Avoid

- **Do not stream raw LangGraph state to the frontend.** The synthesizer node produces the final user-facing string. Only that string (and structured metadata) goes over SSE.
- **Do not call `topological_sort` inside an async route.** It is CPU-bound. If it becomes slow, offload to a thread pool via `asyncio.run_in_executor`.
- **Do not store images in PostgreSQL.** All uploaded files go to MinIO. PostgreSQL stores the MinIO path only.
- **Do not skip the BM25 stage of retrieval** to save latency. Semantic-only search on Vietnamese legal text misses article-number queries and produces poor citations.
- **Do not let the form fill node fail silently.** If a required field cannot be filled, it must be added to `unfilled_required_fields` in agent state so the synthesizer can ask the user for it explicitly.
- **Do not ingest legal documents without procedure tags.** A chunk with no `procedure_tags` payload is effectively unretrievable in filtered searches. The ingestion script must resolve tags before uploading to Qdrant.
- **Do not work around hooks** by running blocked commands in a separate terminal and continuing in Claude Code as if they succeeded. Hooks exist because those patterns caused bugs. If a hook incorrectly blocks a legitimate operation, add a targeted exemption to the hook with a comment explaining the exception.
- **Do not implement a node without reading its `.claude/agents/` spec first.** Spec files define the state key contract other nodes depend on. Implementing from memory leads to key mismatches that break the entire graph and are difficult to trace.
- **Do not skip code-review skills before marking a task complete.** Running the relevant skill on your own output takes under a minute and catches structural violations before they propagate into other phases.
