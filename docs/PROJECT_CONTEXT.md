---
> This file contains project vision, system architecture, design decisions,
> technology stack, and feature roadmap. It changes rarely.
> For task progress, DoD checklists, and next actions, see PROJECT_STATUS.md.
---

# DichVuCong AI Assistant — System Context & Architecture

## Table of Contents
1. [System Vision](#1-system-vision)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Feature Roadmap](#4-feature-roadmap)
5. [Open Questions & Blockers](#5-open-questions--blockers)

---

## 1. System Vision

DichVuCong AI Assistant is a mock Vietnamese government public administration portal that adds a conversational AI layer on top of an otherwise static service directory. The core problem it solves is **navigational complexity**: Vietnamese citizens must complete multiple interdependent administrative procedures in a specific order, and the legal basis for each step is scattered across dozens of decrees and circulars. Today, citizens either hire intermediaries or make repeated trips to government offices due to missing prerequisites. This system removes that friction.

The system is built around a **procedure dependency graph** (DAG) stored in PostgreSQL. All AI capabilities — RAG, OCR, and form auto-fill — exist to serve that graph: RAG answers legal questions about *why* a procedure requires certain documents, OCR extracts personal data from identity documents so it can be *carried forward* into form fields, and form fill automates the tedious transcription of data across multiple government PDF templates. The AI assistant acts as a guide that knows the entire procedural landscape and can route a citizen from their first question to a fully filled form package, citing the exact legal articles at each step.

The target audience is Vietnamese citizens interacting with administrative procedures such as birth registration, residence registration, business formation, and land transactions. The primary AI value proposition over a plain portal is threefold: (1) **cited answers** — every legal claim traces to a specific article number in a real decree; (2) **automatic dependency resolution** — the system tells you what you need *before* you need it; (3) **carry-forward form fill** — data extracted from one document (e.g., CCCD) is automatically propagated into every subsequent form in the procedure chain, without the user re-typing it.

---

## 2. System Architecture

### 2.1 System Layers Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                        NEXT.JS FRONTEND (Port 3000)                  │
│                                                                       │
│  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────────────┐ │
│  │  Chat UI     │  │ 3 Residence     │  │  Document Upload         │ │
│  │  (Widget +   │  │ Form Pages      │  │  (DropZone, OCR result)  │ │
│  │  Full page)  │  │ (manual input,  │  │                          │ │
│  │              │  │  AI-fill ready) │  │                          │ │
│  └──────┬───────┘  └────────┬────────┘  └────────────┬─────────────┘ │
└─────────┼───────────────────┼────────────────────────┼───────────────┘
          │  SSE stream       │  REST POST             │  REST POST
          │  text/event-stream│  /api/v1/forms/submit  │  /api/v1/documents/ocr
┌─────────▼───────────────────▼────────────────────────▼───────────────┐
│                    FASTAPI BACKEND (Port 8000)                        │
│                                                                       │
│   /api/v1/chat      /api/v1/forms     /api/v1/documents              │
│   /api/v1/procedures  /api/v1/legal                                  │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │               LANGGRAPH AGENT PIPELINE                        │   │
│  │                                                               │   │
│  │  Entry ──► Router ──► enrichment_node ──► plan_executor (loop) ──► Synth │   │
│  │                                                   │                │     │   │
│  │                                          NODE_REGISTRY calls:  ──► END   │   │
│  │                                          · rag_fn(state)                 │   │
│  │                                          · ocr_fn(state)                 │   │
│  │                                          · form_filler_fn(state)          │   │
│  │                                                               │   │
│  │  Worker functions accumulate into AgentState each step.      │   │
│  │  plan_executor loops until execution_plan is exhausted,      │   │
│  │  then routes to Synthesizer.                                  │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ PostgreSQL  │  │   Qdrant     │  │  MinIO   │  │   Redis      │  │
│  │ (Port 5432) │  │ (Port 6333)  │  │(Port 9000│  │ (Port 6379)  │  │
│  │ Procedures  │  │ Legal doc    │  │ PDF files│  │ Sessions     │  │
│  │ DAG, Forms  │  │ vectors      │  │ Images   │  │ Cache        │  │
│  └─────────────┘  └──────────────┘  └──────────┘  └──────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Multi-Agent LangGraph Pipeline

The graph topology is a **linear loop**, not a conditional fan-out:

```
Entry → Router → enrichment_node → plan_executor (loops) → Synthesizer → END
```

The Router Node decomposes the user message into an ordered `execution_plan: list[str]` (e.g. `["ocr_fn", "form_filler_fn"]`). The `plan_executor` node reads `execution_plan[plan_cursor]`, calls the corresponding worker function via `NODE_REGISTRY[node_name](state)`, increments `plan_cursor`, and loops back to itself until the plan is exhausted. Worker functions are **never graph nodes** — they are plain Python functions called internally by `plan_executor`. Their outputs accumulate into `AgentState` across each step.

| Component | File | Role |
|---|---|---|
| **Router Node** | `agents/nodes/router.py` | Decomposes user message into `execution_plan: list[str]` and `entities`. Uses structured LLM output. Sets `plan_cursor = 0`. |
| **enrichment_node** | `agents/nodes/enrichment.py` | **(new)** Pre-flight enrichment node. Runs unconditionally after Router, before plan_executor. Calls `procedure_planner_fn` directly only when BOTH conditions are true: (1) `target_procedure_id` is set in state AND (2) `"form_filler_fn"` is present in `execution_plan`. If either condition is false, returns `{}` immediately. No LLM call. Completes in < 50ms. |
| **plan_executor Node** | `agents/nodes/plan_executor.py` | Reads `NODE_DEPENDENCIES` from `node_registry.py`, groups remaining plan steps into execution waves where all dependencies are satisfied, runs each wave with `asyncio.gather()`, advances `plan_cursor` by wave size. Enforces `MAX_PLAN_STEPS` circuit-breaker. |
| **NODE_REGISTRY** | `agents/node_registry.py` | Dict mapping name strings to worker functions. Valid keys: `"rag_fn"`, `"ocr_fn"`, `"form_filler_fn"`. Also exports `NODE_DEPENDENCIES: dict[str, list[str]]` — static dependency matrix driving parallel waves. The only file that imports all worker functions. |
| **rag_fn** | `agents/nodes/rag.py` | Worker: hybrid retrieval from Qdrant + cited generation + `verify_citations()`. Called by `plan_executor`. |
| **ocr_fn** | `agents/nodes/ocr.py` | Worker: OpenCV pre-processing → PaddleOCR → prompt-injection-hardened LLM extraction → `PersonalData`. Called by `plan_executor`. |
| **procedure_planner_fn** | `agents/nodes/procedure_planner.py` | Pre-flight enrichment helper: DB query + topological sort → `ExecutionPlan`. Called **directly by `enrichment_node`** — never a `NODE_REGISTRY` entry, never an `execution_plan` step. |
| **form_filler_fn** | `agents/nodes/form_filler.py` | Worker: LLM semantic field mapping → PDF fill to `tmp/` → promote to final path only when complete. Called by `plan_executor`. |
| **Synthesizer Node** | `agents/nodes/synthesizer.py` | True graph node: assembles `final_response` from all accumulated state fields. Always the last graph node before END. |

**AgentState additions for plan_executor topology** — new fields required in `app/agents/state.py`:

```python
# New routing control fields (add to existing AgentState TypedDict)
execution_plan: list[str]    # e.g. ["ocr_fn", "form_filler_fn"] — set by Router, read by plan_executor
                             # Valid entries: "rag_fn", "ocr_fn", "form_filler_fn" ONLY.
                             # "procedure_planner_fn" is NOT a valid execution_plan entry —
                             # procedure resolution happens in enrichment_node before plan_executor.
plan_cursor: int             # current index into execution_plan — incremented by plan_executor only
conversation_history: list[dict]  # last 6 turns only — trimmed by RedisService.save_session()
                                   # each entry: {"role": "user"|"assistant", "content": str}
```

Conversation history in `AgentState` holds at most the last 6 turns. Older turns are dropped before the state is passed to any LLM call. The full history is never persisted — only the current window is stored in Redis `SessionData`.

### Parallel execution model

`plan_executor` reads a static `NODE_DEPENDENCIES` dict from `node_registry.py` before each iteration. It groups all steps in the remaining plan whose dependencies are already satisfied into a single wave and runs them with `asyncio.gather()`. Steps with unsatisfied dependencies wait for the next wave. The dependency rules are:

- `rag_fn`: no dependencies
- `ocr_fn`: no dependencies
- `form_filler_fn`: depends on `ocr_fn`

For a plan `["ocr_fn", "rag_fn", "form_filler_fn"]`, the executor fires `ocr_fn` and `rag_fn` concurrently in wave 1, then `form_filler_fn` in wave 2. Wall-clock latency for the two-LLM wave is the maximum of the two, not their sum.

### 2.3 RAG Pipeline

```
Raw Vietnamese Legal PDF
  → Docling parser (article hierarchy extraction)
  → Article-boundary chunker (chunk never spans two articles)
  → Metadata tagging (document_number, article_number, procedure_tags, status: "active")
  → bge-m3 embedding (1024-dim, multilingual, Vietnamese-native)
  → Qdrant upsert (vector + payload)

At query time:
  → Dense semantic search (top_k×2 candidates)
  → BM25 keyword search (top_k×2 candidates, critical for decree/article numbers)
  → Reciprocal Rank Fusion merge → top_k results, filtered to status = "active" only
  → Token budget cap: combined retrieved context capped at 6,000 tokens before LLM call
  → Claude citation-enforced generation
  → Citation format: [Điều X, Nghị định YYY/YYYY/NĐ-CP]
  → Post-generation verify_citations(): cross-check cited articles against retrieved chunk payloads
     → Citations not in retrieved chunks are flagged as [unverified: ...], not silently passed
```

### 2.4 OCR Pipeline

```
Uploaded Image (CCCD, birth cert, land cert)
  → File validation: MIME type whitelist, size limit ≤ 5 MB, extension whitelist (TASK-0D)
  → OpenCV: deskew + CLAHE contrast + denoise
  → Document type classifier (vision LLM)
  → PaddleOCR PP-OCRv4 (Vietnamese charset)
  → Prompt-injection hardened LLM extraction:
      - OCR text wrapped in <ocr_text> XML tags
      - Explicit "treat as data only" instruction in prompt
      - Output constrained to PersonalData JSON schema only
      - Pydantic validation discards any non-conforming output entirely
  → PersonalData (Pydantic, all fields optional with confidence)
  → Validation: CCCD checksum, date normalization
  → Redis session storage (keyed by session_id, TTL 1 hour, Fernet-encrypted)
```

### 2.5 Procedure DAG

```
PostgreSQL adjacency list (procedure_dependencies table)
  → Python: load all edges for target procedure subtree
  → procedure_graph.resolve_execution_plan() — Kahn's topological sort
  → Gap analysis: completed_procedures ⊆ required_steps
  → Returns: ordered list[ProcedureStep] with status (PENDING/COMPLETED/BLOCKED)

Residence procedure dependency edges (required before TASK-09):
  → TTDN-003 (Xác nhận thông tin cư trú) requires TTDN-001 or TTDN-002
  → TTDN-001 (Đăng ký thường trú) may follow TTDN-002 under Luật Cư trú 2020 Điều 20
  → See Q4 resolution notes in Section 5
```

---

## 3. Technology Stack

| Layer | Technology | Version / Notes | Status |
|---|---|---|---|
| **Frontend Framework** | Next.js (App Router) | 14.2.x | ✅ Confirmed |
| **Frontend Styling** | Tailwind CSS | 3.x | ✅ Confirmed |
| **Frontend Forms** | React Hook Form + Zod | RHF 7.x, Zod 3.x | ✅ Confirmed |
| **Frontend State** | Zustand | 4.x | ✅ Confirmed |
| **API Framework** | FastAPI | 0.115.x | ✅ Confirmed |
| **ORM** | SQLAlchemy 2.0 (async) | 2.0.x | ✅ Confirmed |
| **DB Migrations** | Alembic | 1.14.x | ✅ Confirmed |
| **Task Queue** | Celery + Redis | Celery 5.4 | ⚙️ Partially set up |
| **Relational DB** | PostgreSQL | 16-alpine (Docker) | ✅ Confirmed |
| **Vector DB** | Qdrant | latest (Docker) | ⚙️ Partially set up |
| **Cache / Sessions** | Redis | 7-alpine (Docker) | ⚙️ Partially set up |
| **Object Storage** | MinIO | latest (Docker) | ⚙️ Partially set up |
| **LLM Backbone** | Claude claude-sonnet-4-20250514 | Anthropic SDK 0.85.0 | ⚙️ Partially set up |
| **Embeddings** | bge-m3 (local) | sentence-transformers | ⚙️ Partially set up |
| **Agent Framework** | LangGraph | 1.1.2 | ⚙️ Partially set up |
| **OCR Engine** | PaddleOCR (primary) | PP-OCRv4 | 📋 Planned |
| **OCR Fallback** | Tesseract | 5.x | 📋 Planned |
| **PDF Processing** | pdfplumber + pdfrw | latest | 📋 Planned |
| **PDF Form Fill** | pdfrw + reportlab | latest | 📋 Planned |
| **Document Parsing** | Docling (IBM) | latest | 📋 Planned |
| **Image Processing** | OpenCV (cv2) | 4.x | 📋 Planned |
| **Observability** | LangSmith | via langchain | 📋 Planned — wired in TASK-01 (Phase 2), not Phase 4 |
| **Containerization** | Docker Compose | v2 | ✅ Confirmed |

---

## 4. Feature Roadmap

### Core AI

| Feature | Phase | Core / Enhancement |
|---|---|---|
| Multi-intent plan decomposition (Router → `execution_plan: list[str]`) | 2 | Core |
| `plan_executor` loop node + `NODE_REGISTRY` | 2 | Core |
| Parallel worker execution via `NODE_DEPENDENCIES` matrix (`asyncio.gather`) | 2 | Core |
| Iteration circuit-breaker in `plan_executor` (`MAX_PLAN_STEPS`) | 2 | Core |
| Hybrid RAG retrieval (dense + BM25 RRF) | 2 | Core |
| Legal citation generation | 2 | Core |
| Post-generation citation verification (`verify_citations()`) | 2 | Core |
| RAG context window token budget cap (6,000 tokens) | 2 | Core |
| OCR raw text token cap (8,000 tokens, truncation with warning log) | 2 | Core |
| Vietnamese legal document ingestion pipeline | 2 | Core |
| Legal document versioning + re-ingestion strategy (`status` field) | 2 | Core |
| Streaming SSE chat endpoint | 2 | Core |
| LangSmith agent tracing | 2 | Core — moved from Phase 4 |
| PaddleOCR image pre-processing + field extraction | 3 | Core |
| Prompt-injection hardening on OCR extraction prompt | 3 | Core |
| PersonalData carry-forward merge | 3 | Core |
| LLM semantic form field mapping | 3 | Core |
| PDF AcroForm fill + overlay fallback | 3 | Core |
| Partial form write protection (tmp/ MinIO prefix) | 3 | Core |
| Procedure dependency resolution (pre-flight enrichment node, no LLM call) | 2 | Core |
| Full LangGraph graph assembly (plan_executor topology) | 4 | Core |
| Multi-turn conversation history (windowed, last 6 turns — caps input token growth) | 4 | Core |
| Session persistence across turns (Redis, TTL, encrypted) | 4 | Core |
| Rate limiting middleware on `/chat` endpoint | 4 | Core |
| Cross-encoder reranker | 4 | Enhancement |

### Frontend

| Feature | Phase | Core / Enhancement |
|---|---|---|
| Government portal UI (10 pages) | 1 | Core |
| Floating AI chat widget (SSE streaming) | 1 | Core |
| 3 residence registration form pages | 1 | Core |
| Zustand formStore with AI-fill-ready setFieldValue | 1 | Core |
| AI-highlighted field visual indicator | 3 | Core |
| Procedure execution plan panel | 1 | Core |
| Document upload DropZone | 1 | Core |
| OCR result display card | 3 | Core |
| PDF preview (react-pdf) | 3 | Enhancement |

### Backend

| Feature | Phase | Core / Enhancement |
|---|---|---|
| FastAPI app factory + config | 0 | Core |
| API stubs (chat, forms, procedures, documents, legal) | 0 | Core |
| `get_db()` async session factory (`app/dependencies.py`) | 0 | Core |
| ORM model column definitions (all 4 models) | 0 | Core |
| Functional chat SSE endpoint | 2 | Core |
| Functional form submit endpoint | 2 | Core |
| Document upload + OCR endpoint | 3 | Core |
| File upload validation (MIME, size, extension whitelist) | 3 | Core |
| Rate limiting middleware on chat endpoint | 4 | Core |
| Procedure CRUD + graph endpoint | 2 | Core |
| Pydantic schemas (all) | 0 | Core |
| AgentState TypedDict (with `execution_plan`, `plan_cursor`) | 0 | Core |
| Procedure graph topological sort | 0 | Core |
| Session accumulator (carry-forward merge) | 3 | Core |
| Citation formatter + `verify_citations()` post-check | 2 | Core |

### Infrastructure

| Feature | Phase | Core / Enhancement |
|---|---|---|
| Docker Compose (all 4 services) | 0 | Core |
| Redis authentication (`requirepass`) | 0 | Core |
| CORS config: explicit origin allowlist (not `*`) | 0 | Core |
| Alembic migration (7 tables) | 0 | Core |
| Procedure seed data + dependency edges | 0 | Core |
| MinIO bucket initialization with explicit PRIVATE policy | 2 | Core |
| Redis session TTL (1 hour) + Fernet encryption at rest | 3 | Core |
| Celery worker setup | 3 | Enhancement |

### Data

| Feature | Phase | Core / Enhancement |
|---|---|---|
| 3 residence procedures seeded in PostgreSQL | 0 | Core |
| `procedure_dependencies` edges seeded (TTDN-003 → TTDN-001/002) | 0 | Core |
| Real Vietnamese legal PDFs collected | 2 | Core |
| Legal documents ingested into Qdrant (with `status: "active"` field) | 2 | Core |
| Blank PDF form templates collected/created | 3 | Core |
| Form templates uploaded to MinIO | 3 | Core |
| Synthetic CCCD mock images generated | 3 | Core |

---

## 5. Open Questions & Blockers

| # | Question / Blocker | Blocks | Resolution |
|---|---|---|---|
| **Q1** | Which Vietnamese legal PDFs to ingest? | TASK-05, TASK-06 | Collect Luật Cư trú 2020, Nghị định 62/2021/NĐ-CP, Nghị định 144/2021/NĐ-CP from thuvienphapluat.vn. Download today — non-code prerequisite. |
| **Q2** | Are real blank government PDF form templates available, or must we mock them? | TASK-08, TASK-15 | Create mock AcroForm PDFs using reportlab/pdfrw with realistic Vietnamese field names |
| **Q3** | ANTHROPIC_API_KEY not set in `.env` | TASK-01, all agent nodes | Add key to `backend/.env` before starting Phase 2 work |
| **Q4** | `procedure_dependencies` table is empty | TASK-09 | **Resolved (design):** TTDN-003 (Xác nhận thông tin cư trú) depends on TTDN-001 or TTDN-002. TTDN-001 may follow prior tạm trú under Luật Cư trú 2020 Điều 20. Seed edges in TASK-0B. |
| **Q5** | MinIO bucket `dichvucong` not created yet | TASK-07, TASK-15 | **Resolved → TASK-0A scope:** Add bucket init with explicit PRIVATE policy to FastAPI lifespan in `app/dependencies.py`. |
| **Q6** | PaddleOCR requires CUDA or CPU mode — local hardware unclear | TASK-04 | Default to CPU mode (`use_gpu=False`); document GPU path for later |
| **Q7** | `bge-m3` model download size (~2.2 GB) — first run will be slow | TASK-02 | Pre-download model in a setup script; cache in `.cache/` via `SENTENCE_TRANSFORMERS_HOME` |
| **Q8** | No `get_db()` async session factory implemented | TASK-09, TASK-11, all routes | **Resolved → TASK-0A:** Implement using `async_sessionmaker` with `expire_on_commit=False`. |
| **Q9** | ORM model stubs have no column definitions | All DB-touching tasks | **Resolved → TASK-0B:** Write full column definitions before any Phase 2 task writes to the DB. |
| **Q10** | Chat endpoint makes 3–5 LLM calls per message with no rate limiting | TASK-11 | **Resolved → TASK-0C:** `slowapi` middleware, 10 req/min per `session_id`. |
| **Q11** | Document upload has no file type or size validation | TASK-12 | **Resolved → TASK-0D:** MIME whitelist, 5 MB max, extension whitelist in `file_validator.py`. |
| **Q12** | No legal document versioning strategy | TASK-05, RAG accuracy | **Resolved → TASK-0E:** `status: "active" \| "superseded"` field in Qdrant payload. Re-ingestion soft-deprecates old chunks. `QdrantService.search()` always filters `status = "active"`. |
| **Q13** | `plan_executor` loop has no iteration limit | TASK-11 | **Resolved → TASK-0F / TASK-11:** `MAX_PLAN_STEPS = 8` constant inside `plan_executor`. `graph.compile(recursion_limit=10)` as second safeguard. `GraphRecursionError` caught in chat endpoint. |
| **Q14** | OCR text fed directly into LLM prompt — prompt injection risk | TASK-04 | **Resolved → TASK-04:** OCR text wrapped in `<ocr_text>` XML tags; "treat as data only" instruction; Pydantic validation discards non-conforming output. |
| **Q15** | PersonalData (PII) stored in Redis with no TTL or encryption | TASK-03 | **Resolved → TASK-03:** `ex=3600` TTL on all session `redis.set()` calls. Fernet encryption of Redis values at rest using `REDIS_ENCRYPTION_KEY` env var. |
| **Q16** | MinIO bucket has no access policy — may default to public | TASK-07 | **Resolved → TASK-07:** Explicit PRIVATE policy set in `StorageService.__init__()`. Verified by unit test (anonymous `get_object` returns 403). |
| **Q17** | No RAG context window token budget — large contexts overflow | TASK-06 | **Resolved → TASK-02/TASK-06:** Combined retrieved chunk text capped at 6,000 tokens in `QdrantService`. Lowest-ranked chunks truncated first. |
| **Q18** | Partially filled PDFs written to final MinIO path prematurely | TASK-08 | **Resolved → TASK-07/TASK-08:** `PDFService.fill()` writes to `tmp/{session_id}/`. `form_filler_fn` calls `storage_service.promote_tmp()` only when `unfilled_required_fields` is empty. |
| **Q19** | CORS config likely `allow_origins=["*"]` in scaffold | `app/main.py` | **Resolved → TASK-0A:** `allow_origins=["http://localhost:3000"]` from env var. |
| **Q20** | Redis has no authentication in Docker Compose | `docker-compose.yml` | **Resolved → TASK-0A:** `redis-server --requirepass ${REDIS_PASSWORD}` in compose; `REDIS_PASSWORD` added to `.env`. |
| **Q21** | Citation enforcement is prompt-based only — hallucinated article numbers pass silently | TASK-06, `citation_formatter.py` | **Resolved → TASK-06:** `verify_citations(response_text, retrieved_chunks) -> str` cross-checks every `[Điều X, Nghị định YYY]` reference against retrieved payloads. Unverified citations flagged as `[unverified: ...]`. |
| **Q22** | LangSmith wired in Phase 4 — no observability during routing development | All agent phases | **Resolved → TASK-01:** `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` wired in `LLMService.__init__()`. Active from first real invocation. |
| **Q23** | Conversation history grows unboundedly across long sessions, inflating input tokens on every LLM call | All LLM-calling nodes (TASK-01, TASK-06, TASK-10) | **Resolved — Decision 3:** History capped at 6 turns in both `AgentState` and `SessionData`. `RedisService.save_session()` trims before write. Estimated saving: 3–4× reduction in history token spend for sessions beyond 10 turns. |
