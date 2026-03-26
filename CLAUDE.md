# CLAUDE.md — DichVuCong AI Assistant

## Project Overview

A mock Vietnamese government public administration portal (dichvucong.gov.vn) with an AI assistant. **Backend logic, RAG architecture, and multi-agent orchestration are the primary focus. Frontend is secondary.**

---

## Current Implementation Status

> Last updated: 2026-03-26. Update this section whenever a phase completes.

### ✅ Done

**Infrastructure**
- Docker Compose up (PostgreSQL 5432, Redis 6379 with `requirepass` auth, Qdrant 6333, MinIO 9000)
- Alembic migrations applied: `0001_initial_schema.py` (7 tables) + `0002_legal_doc_versioning.py` (`superseded_by` FK on `legal_documents`)
- Redis password auth (`REDIS_PASSWORD` env var, `--requirepass` in docker-compose.yml)
- CORS locked to explicit origin list (`CORS_ALLOW_ORIGINS` env var, no `*`)
- MinIO bucket auto-init with private policy on FastAPI startup (lifespan)
- `slowapi` rate limiting: 10 req/min per `session_id` on `POST /api/v1/chat`

**Backend — Implemented**
- `procedure_graph.py` — Kahn's topological sort + `resolve_execution_plan()` — 8 unit tests passing
- `get_db()` async session factory with explicit rollback on exception (`app/dependencies.py`)
- `app/rate_limit.py` — shared `Limiter` module (avoids circular import with `main.py`)
- `app/core/file_validator.py` — MIME whitelist, 5 MB size limit, extension whitelist
- All 4 ORM models — fully implemented (UUID PKs, TIMESTAMPTZ, JSONB, ARRAY)
- `ingest_procedures.py` — 3 residence procedures + 2 dependency edges (TTDN-003 → TTDN-001 mandatory, TTDN-003 → TTDN-002 conditional)
- `qdrant_service.py` — `_active_filter()`, `scroll_by_document_number()`, `batch_set_status()` stubs
- `ingest_legal_docs.py` — re-ingestion outline with supersede-before-upsert flow

**Phase 2 — AI Core (TASK-01 complete)**
- `app/services/llm.py` — `LLMService` wrapping `anthropic.AsyncAnthropic`; `async_invoke()` + `stream()`; LangSmith tracing wired in `__init__`
- `app/agents/node_registry.py` — `VALID_PLAN_STEPS`, `NODE_DEPENDENCIES`, `NODE_REGISTRY` (rag_fn / ocr_fn / form_filler_fn only)
- `app/agents/prompts/router_prompt.py` — `RouterOutput` Pydantic model, Vietnamese system prompt with 8 few-shot examples, `build_router_messages()`
- `app/agents/nodes/router.py` — `async router_node()` with JSON fallback + ordering enforcement + ValueError on invalid steps
- `app/agents/state.py` — updated: `execution_plan`, `plan_cursor`, `conversation_history` added; old `intent` field removed
- `.claude/agents/router-agent.md` — fully rewritten for plan_executor topology
- `config.py` / `.env` — `LLM_MODEL=claude-sonnet-4-20250514` added

**Phase 2 — AI Core (TASK-02 complete)**
- `app/services/embedder.py` — `EmbedderService`: bge-m3 primary (1024-dim), OpenAI `text-embedding-3-large` fallback (dimensions=1024), automatic fallback on bge-m3 load failure. Backend selected via `EMBEDDING_BACKEND` env var.
- `app/services/qdrant_service.py` — `QdrantService`: hybrid dense + BM25 (in-memory rank_bm25) search with RRF merge (`1/(rank+60)`), `status="active"` filter on every search, 6,000-token context budget cap, `update_status()` for soft-deprecation. Collection: `legal_documents`, vector size: 1024.
- `app/schemas/rag.py` — `DocumentChunk` Pydantic model

**Legal Documents — downloaded to `backend/data/legal_documents/`**
- `68_2020_QH14_435315.doc` — Luật Cư trú 2020 (Luật số 68/2020/QH14)
- `62_2021_ND-CP_473325.doc` — Nghị định 62/2021/NĐ-CP
- `104_2022_ND-CP_544177.doc` — Nghị định 104/2022/NĐ-CP
- `55_2021_TT-BCA_466836.doc` — Thông tư 55/2021/TT-BCA
- ⚠️ Files are `.doc` (Word) format — ingestion script expects PDF. Convert to PDF before running TASK-05.

**Tests — 103 unit tests passing**
- `test_procedure_graph.py` (8) | `test_dependencies.py` (4) | `test_orm_models.py` (21)
- `test_rate_limiting.py` (5) | `test_file_validator.py` (10) | `test_legal_doc_versioning.py` (8)
- `test_router_node.py` (31) | `test_embedder_service.py` (5) | `test_qdrant_service.py` (9)
- `test_form_mapper.py` (1 placeholder) | `test_session_accumulator.py` (1 placeholder)

**Frontend** — 10 pages (7 portal + 3 residence forms), ChatWidget (SSE-ready), all Zustand stores, TypeScript types

### 🔄 Next Up (Phase 2 — AI Core, continued)
TASK-01 complete. Remaining Group A tasks can now proceed.

**Group A — remaining (start simultaneously):**
~~`TASK-02`~~ ✅ Complete | `TASK-03` Redis service (TTL + Fernet encryption) | `TASK-07` PDF + storage service | `TASK-13` Mock CCCD image generation

**Group B (after Group A):**
`TASK-04` OCR service (prompt-injection hardened) | `TASK-05` Legal doc ingestion ⚠️ convert .doc → PDF first | `TASK-06` RAG node (hybrid + `verify_citations()`)

**Group C (after Group B):**
`TASK-08` Form filler worker fn | `TASK-09` Procedure planner worker fn | `TASK-10` Synthesizer node

**Group D (all nodes done):**
`TASK-11` Graph assembly (`plan_executor` loop topology) + functional chat SSE | `TASK-12` Document upload + OCR endpoint | `TASK-14` Integration tests

See `docs/PROJECT_STATUS_v1.1.md` for full task cards with inputs/outputs/DoD checklists.

---

## Stack at a Glance

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), Tailwind, React Hook Form + Zod, Zustand |
| Backend | FastAPI (Python, async), SQLAlchemy 2.0, Alembic, Celery + Redis |
| AI | Claude claude-sonnet-4-20250514 (Anthropic), bge-m3 embeddings (OpenAI text-embedding-3-large fallback), LangGraph agents |
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
│   │   │   └── file_validator.py  # ✅ MIME/size/extension validation
│   │   ├── rate_limit.py    # ✅ shared slowapi Limiter (avoids circular import)
│   │   ├── services/        # Infrastructure wrappers (LLM, Qdrant, OCR, PDF, Redis)
│   │   ├── models/          # SQLAlchemy ORM models (all 4 fully implemented ✅)
│   │   └── schemas/         # Pydantic v2 request/response schemas
│   ├── ingestion/           # Offline scripts (ingest legal docs, seed procedures, mock data gen)
│   │   ├── ingest_procedures.py   # ✅ 3 procedures + 2 dependency edges seeded
│   │   ├── ingest_legal_docs.py   # ✅ re-ingestion outline (real impl in TASK-05)
│   │   └── generate_mock_data.py  # 📋 not yet implemented
│   ├── data/
│   │   ├── legal_documents/ # Raw Vietnamese legal PDFs (empty — collect before Phase 2)
│   │   ├── form_templates/  # Blank government PDF forms (empty — collect before Phase 3)
│   │   └── mock_documents/  # Synthetic CCCD images (empty — generate in TASK-13)
│   ├── alembic/             # Migrations — never modify a committed version
│   │   └── versions/
│   │       ├── 0001_initial_schema.py          # ✅ applied — 7 tables
│   │       └── 0002_legal_doc_versioning.py    # ✅ superseded_by FK on legal_documents
│   └── tests/
│       └── unit/            # 58 tests passing ✅
│           ├── conftest.py  # stubs python-magic DLL for Windows unit tests
│           ├── test_procedure_graph.py     # 8 tests
│           ├── test_dependencies.py        # 4 tests
│           ├── test_orm_models.py          # 21 tests
│           ├── test_rate_limiting.py       # 5 tests
│           ├── test_file_validator.py      # 10 tests
│           └── test_legal_doc_versioning.py # 8 tests
└── frontend/
    └── src/
        ├── app/             # Next.js App Router pages (10 pages ✅)
        ├── components/      # chat/ (ChatWidget ✅), forms/, documents/, ui/ (all ✅)
        └── lib/             # api/, stores/ (all 3 stores ✅), types/ (✅)
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

    # --- Routing (plan_executor topology) ---
    execution_plan: list[str]    # e.g. ["ocr_fn", "form_filler_fn"] — set by Router
    plan_cursor: int             # current index — incremented by plan_executor only
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

The graph topology is a **linear loop** — not a conditional fan-out. The Router decomposes the user message into an ordered `execution_plan: list[str]`, and `plan_executor` drives all worker functions as plain function calls via `NODE_REGISTRY`.

**Graph topology:**
```
Entry → router_node → plan_executor (loops) → synthesizer_node → END
```

**True graph nodes (only 3):**
```
nodes/
├── router.py           → router_node(state): sets execution_plan + plan_cursor=0
├── plan_executor.py    → plan_executor_node(state): calls NODE_REGISTRY[plan[cursor]](state)
└── synthesizer.py      → synthesizer_node(state): assembles final_response
```

**Worker functions (called by plan_executor — never graph nodes):**
```
nodes/
├── rag.py              → rag_fn(state) -> dict
├── ocr.py              → ocr_fn(state) -> dict
├── procedure_planner.py → procedure_planner_fn(state) -> dict
└── form_filler.py      → form_filler_fn(state) -> dict
```

**NODE_REGISTRY** (`app/agents/node_registry.py`) is the ONLY file that imports all worker functions. `plan_executor` calls workers through it — never directly.

```python
# app/agents/node_registry.py
NODE_REGISTRY: dict[str, Callable[[AgentState], dict]] = {
    "rag_fn": rag_fn,
    "ocr_fn": ocr_fn,
    "procedure_planner_fn": procedure_planner_fn,
    "form_filler_fn": form_filler_fn,
}

# app/agents/nodes/plan_executor.py
MAX_PLAN_STEPS = 8  # circuit-breaker

def plan_executor_node(state: AgentState) -> dict:
    cursor = state["plan_cursor"]
    plan = state["execution_plan"]
    if cursor >= len(plan) or cursor >= MAX_PLAN_STEPS:
        return {}  # signals synthesizer to take over
    worker = NODE_REGISTRY[plan[cursor]]
    update = worker(state)
    return {**update, "plan_cursor": cursor + 1}
```

**Graph assembly** (`app/agents/graph.py`) is compiled with `recursion_limit=10`. `GraphRecursionError` must be caught in the chat endpoint.

> **Skills:** Before implementing or modifying any node, read its `.claude/agents/` spec. Run `/review-agent-node` on the finished node before marking the task complete.

> ⚠️ `router-agent.md` must be updated before TASK-01 begins — the spec predates the `plan_executor` topology and still documents the old fan-out routing.

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

| Spec File | Node / Function |
|---|---|
| `router-agent.md` | `router_node` — produces `execution_plan: list[str]`, sets `plan_cursor=0` ⚠️ needs update for plan_executor topology |
| `rag-agent.md` | `rag_fn` — hybrid retrieval + cited generation + `verify_citations()` |
| `ocr-agent.md` | `ocr_fn` — image → PersonalData pipeline (prompt-injection hardened) |
| `procedure-planner-agent.md` | `procedure_planner_fn` — DB query + topo sort → ExecutionPlan |
| `form-filler-agent.md` | `form_filler_fn` — field mapping + PDF fill to `tmp/` + promote on completion |
| `synthesizer-agent.md` | `synthesizer_node` — final response assembly from accumulated state |

---

## Frontend Development

The frontend is secondary to the backend, but the following skills keep it consistent:

| Task | Skill |
|---|---|
| New page or layout in `frontend/src/app/` | `/nextjs-app-router-fundamentals` |
| New reusable component in `frontend/src/components/` | `/building-components` |
| Any form with validation | `/react-hook-form-zod` |
| Tailwind tokens, spacing, or colour system changes | `/tailwind-design-system` |

**Existing pages (do not recreate):**
- `/` home, `/chat`, `/dich-vu-cong`, `/tra-cuu-ho-so`, `/cau-hoi-thuong-gap`, `/danh-gia-chat-luong`, `/thanh-toan`
- `/thu-tuc/dang-ky-thuong-tru`, `/thu-tuc/dang-ky-tam-tru`, `/thu-tuc/xac-nhan-cu-tru`

**Zustand store API (do not change field names — backend contracts depend on these):**
- `chatStore`: `sessionId`, `messages`, `isStreaming`, `uploadedFile`, `procedurePlan`
- `formStore`: `setFieldValue(field, value, source, confidence)`, `getFieldState(field)`
- `procedureStore`: `selectedProcedureId`, `executionPlan`, `completedProcedureIds`

---

## RAG — Implementation Notes

### Chunking (do not change this without a good reason)

Legal documents must be chunked at **article boundaries**. A chunk never spans two articles. This is enforced in `backend/ingestion/ingest_legal_docs.py`. The article number and decree reference are stored as Qdrant payload — they are what make citations possible.

### Hybrid Search (always use both stages)

Never call Qdrant with dense search only. BM25 is critical because users query by decree number ("Nghị định 123") and article number ("Điều 15"), which are exact-match queries that semantic search handles poorly.

```python
# app/services/qdrant_service.py
async def search(
    query: str,
    procedure_id: str | None = None,
    top_k: int = 8
) -> list[DocumentChunk]:
    # BOTH search stages MUST include _active_filter() — never skip it
    active = self._active_filter()
    semantic = await self._dense_search(query, procedure_id, top_k * 2, filter=active)
    lexical = self._bm25_search(query, top_k * 2, filter=active)
    results = self._rrf_merge(semantic, lexical, top_k)
    # Token budget: cap combined retrieved text at 6,000 tokens (truncate lowest-ranked first)
    return self._apply_token_budget(results, max_tokens=6000)
```

### Active Status Filter — Never Skip

Every Qdrant search MUST filter on `status = "active"`. Use `QdrantService._active_filter()` to get the filter object. Do not inline the filter condition. Superseded chunks must never reach the LLM or appear in citations.

### Legal Document Versioning

When re-ingesting a legal document, ALWAYS supersede old chunks before upserting new ones:
1. `scroll_by_document_number(document_number)` → get existing point IDs
2. `batch_set_status(existing_ids, "superseded")` → soft-delete
3. Upsert new chunks with `"status": "active"` in payload

### Citation Format

Every legal claim in an LLM response must map to a chunk that was actually retrieved. The citation format is: `[Điều X, Nghị định/Thông tư YYY/YYYY/NĐ-CP]`. The LLM prompt enforces this — see `app/agents/prompts/rag_prompt.py`. After generation, `verify_citations(response_text, retrieved_chunks)` must cross-check every citation against retrieved chunk payloads — unverified citations are flagged as `[unverified: ...]`, never passed silently.

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

The `.env` file lives at the project root. The following values are already configured for local dev:

```bash
# LLM — ⚠️ ANTHROPIC_API_KEY must be filled before any agent node will work
ANTHROPIC_API_KEY=

# Databases (all running via Docker Compose)
POSTGRES_URL=postgresql+asyncpg://dichvucong:dichvucong@localhost:5432/dichvucong
REDIS_URL=redis://:dichvucong_redis_secret@localhost:6379/0   # password included
QDRANT_URL=http://localhost:6333

# Security (added in Phase 0 gap tasks)
REDIS_PASSWORD=dichvucong_redis_secret
CORS_ALLOW_ORIGINS=http://localhost:3000
CHAT_RATE_LIMIT=10/minute

# Storage (MinIO default dev credentials — fine for local)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=dichvucong

# Embeddings
EMBEDDING_BACKEND=bge-m3          # bge-m3 preferred; set to "openai" + add key if local model too slow
OPENAI_API_KEY=                    # only needed if EMBEDDING_BACKEND=openai

# Observability — wired in TASK-01 (Phase 2), not Phase 4
LANGSMITH_API_KEY=
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=dichvucong

# App
ENVIRONMENT=development
LOG_LEVEL=INFO
```

---

## Common Mistakes to Avoid

- **Do not implement worker functions as LangGraph graph nodes.** `rag_fn`, `ocr_fn`, `procedure_planner_fn`, and `form_filler_fn` are plain Python functions called by `plan_executor` via `NODE_REGISTRY`. Only `router_node`, `plan_executor_node`, and `synthesizer_node` are wired into the graph.
- **Do not skip `_active_filter()` in any Qdrant search call.** Both the dense and BM25 search stages must filter on `status = "active"`. Superseded chunks must never reach the LLM.
- **Do not call `verify_citations()` — never skip it.** After every RAG generation, cross-check cited articles against retrieved chunk payloads. Unverified citations get flagged `[unverified: ...]`.
- **Do not stream raw LangGraph state to the frontend.** The synthesizer node produces the final user-facing string. Only that string (and structured metadata) goes over SSE.
- **Do not call `topological_sort` inside an async route.** It is CPU-bound. If it becomes slow, offload to a thread pool via `asyncio.run_in_executor`.
- **Do not store images in PostgreSQL.** All uploaded files go to MinIO. PostgreSQL stores the MinIO path only.
- **Do not skip the BM25 stage of retrieval** to save latency. Semantic-only search on Vietnamese legal text misses article-number queries and produces poor citations.
- **Do not let the form fill node fail silently.** If a required field cannot be filled, it must be added to `unfilled_required_fields` in agent state so the synthesizer can ask the user for it explicitly.
- **Do not ingest legal documents without procedure tags.** A chunk with no `procedure_tags` payload is effectively unretrievable in filtered searches. The ingestion script must resolve tags before uploading to Qdrant.
- **Do not work around hooks** by running blocked commands in a separate terminal and continuing in Claude Code as if they succeeded. Hooks exist because those patterns caused bugs. If a hook incorrectly blocks a legitimate operation, add a targeted exemption to the hook with a comment explaining the exception.
- **Do not implement a node without reading its `.claude/agents/` spec first.** Spec files define the state key contract other nodes depend on. Implementing from memory leads to key mismatches that break the entire graph and are difficult to trace.
- **Do not skip code-review skills before marking a task complete.** Running the relevant skill on your own output takes under a minute and catches structural violations before they propagate into other phases.
- **Do not call `QdrantService.search()` without a status filter.** The `status="active"` filter is applied inside `QdrantService` automatically — never add it at the call site. If you see `status` filter logic outside `qdrant_service.py`, move it inside.
- **Do not hard-code `vector_size=1024` at call sites.** Always use `settings.QDRANT_VECTOR_SIZE`. The OpenAI backend uses `dimensions=1024` truncation to stay consistent — never create the collection with 3072 dimensions even when `EMBEDDING_BACKEND=openai`.
