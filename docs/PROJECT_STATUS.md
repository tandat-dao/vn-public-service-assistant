# DichVuCong AI Assistant — Project Status

> **What changed in v2.0:** Documentation restructured — PROJECT_STATUS.md split into PROJECT_CONTEXT.md (architecture, vision, stack, roadmap, open questions) and PROJECT_STATUS.md (version log, progress, task cards, next actions). CLAUDE.md updated to read both files before any work.

> **What changed in v1.9:** Documentation audit — enrichment_node two-condition guard clarified, BM25 procedure_id pre-filter rule added, form field mapping cache rule added, conversation history load-time trim rule added, TASK-13 elevated to High priority, TASK-10 expanded to M (2 days) with six Synthesizer response modes specified, TASK-08 DoD updated with field mapping cache requirements.

> **What changed in v1.8:** Full DoD audit of TASK-01 through TASK-07 — all checks passed except one bug: `app/services/embedder.py:118` used deprecated `asyncio.get_event_loop()` inside `async _embed_bge_m3()`. Fixed to `get_running_loop()`. `storage_service.py` docstring updated to correctly document `_ensure_bucket()` startup exception. 1 new test `test_bge_m3_uses_get_running_loop` added (144 total).

> **What changed in v1.7:** TASK-04 post-review fixes — `asyncio.get_event_loop()` replaced with `get_running_loop()` in both `ocr_service.py` and `storage_service.py`; Vietnamese address in QR data now parsed into `street/ward/district/city` components (raw string preserved in `PersonalData.raw_address`); `Address.city` field added; `tests/fixtures/minimal_cccd.jpg` committed; `minimal_image_path` fixture added to `conftest.py`; "Reasoning and Self-Verification Rules" section added to `CLAUDE.md`. 6 new unit tests (143 total).

> **What changed in v1.6:** TASK-04 complete — OCRService (two-path pipeline: QR decode via pyzbar with 5-attempt OpenCV preprocessing, plus full OCR fallback via PaddleOCR + LLM extraction), `document_classifier_prompt.py`, `ocr_extraction_prompt.py` (SCHEMA_BLOCK ≤150 tokens, injection-hardened), and `ocr_fn` worker all implemented and tested. PaddleOCR wrapped in `run_in_executor` (never blocking async). `pyzbar==0.1.9` added to requirements. 15 new unit tests (137 total).

> **What changed in v1.5:** TASK-03 and TASK-07 complete — RedisService (Fernet-encrypted session storage, 3600s TTL, 6-turn history trim, response cache), SessionData schema, StorageService (MinIO PRIVATE bucket, upload/download/promote_tmp), and PDFService (AcroForm+pdfrw, flat overlay+reportlab, pdfplumber-based type detection) all implemented and tested. `REDIS_ENCRYPTION_KEY` and `MINIO_SECURE` added to config. `cryptography==43.0.1` added to requirements. 19 new unit tests (113 total).

> **What changed in v1.4:** TASK-02 complete — EmbedderService (bge-m3 primary, OpenAI text-embedding-3-large fallback, auto-fallback on load failure) and QdrantService (hybrid dense+BM25 RRF, status="active" filter, 6,000-token budget, update_status for soft-deprecation) implemented and tested. DocumentChunk schema added to app/schemas/rag.py. rank-bm25 and openai added to requirements.txt.

> **What changed in v1.3:** TASK-01 complete — `LLMService`, `node_registry.py`, `router_prompt.py`, `router_node` all implemented and 31 unit tests passing (89 total). `AgentState` updated: `execution_plan`, `plan_cursor`, `conversation_history` added; old `intent` field removed. Worker function stubs renamed to `_fn` suffix (`rag_fn`, `ocr_fn`, `form_filler_fn`). Legal source documents downloaded to `backend/data/legal_documents/` (4 files — Luật Cư trú 2020, NĐ 62/2021, NĐ 104/2022, TT 55/2021). ⚠️ Files are `.doc` format — must convert to PDF before TASK-05 ingestion.

> **What changed in v1.2:** Three architecture decisions applied: (1) `procedure_planner_fn` moved out of `execution_plan` — now called by a new `enrichment_node` graph node (pre-flight, no LLM call, < 50ms); (2) `plan_executor` runs `rag_fn`/`ocr_fn` concurrently via `asyncio.gather()` driven by static `NODE_DEPENDENCIES` matrix; (3) conversation history capped at 6 turns in both `AgentState` and Redis `SessionData`. OCR raw text token cap (8,000 tokens) added as defensive measure.

> **What changed in v1.1:** Six missing tasks added (TASK-0A through TASK-0F) covering the async DB session factory, ORM column stubs, rate limiting, upload validation, legal doc versioning, and iteration circuit-breaker. Multi-agent graph architecture redesigned from conditional fan-out edges to a `plan_executor` loop topology — the Router now produces an ordered `execution_plan: list[str]` and a new `plan_executor` node drives all worker nodes as plain function calls via `NODE_REGISTRY`. Worker nodes (RAG, OCR, Procedure Planner, Form Filler) are no longer graph nodes. LangSmith tracing moved from Phase 4 to Phase 1 (TASK-01). Six security issues documented as new blockers (Redis auth, MinIO policy, CORS, session TTL/encryption, prompt injection hardening, RAG token budget). `procedure_dependencies` seeding elevated to a required Phase 0 data task. Citation post-generation verification (`verify_citations()`) added to `citation_formatter.py` scope.

---

## Table of Contents
1. [Current Progress Status](#1-current-progress-status)
2. [Task Delegation Board](#2-task-delegation-board)
3. [Dependency Graph](#3-dependency-graph)
4. [Recommended Next Actions](#4-recommended-next-actions)

---

## 1. Current Progress Status

### 1.1 Completed ✅

#### Infrastructure
| Item | File | Confidence |
|---|---|---|
| Docker Compose (postgres, redis, qdrant, minio) | `docker-compose.yml` | Implemented & Running |
| PostgreSQL 7-table schema | `alembic/versions/0001_initial_schema.py` | Implemented & Tested |
| Alembic migration applied | (live DB, run `alembic upgrade head`) | Implemented & Running |
| 3 residence procedures seeded | `ingestion/ingest_procedures.py` | Implemented & Running |
| Python venv with all deps | `backend/.venv/` | Implemented |

#### Backend — Implemented
| Item | File | Confidence |
|---|---|---|
| FastAPI app factory + CORS + MinIO init + rate limit middleware | `app/main.py` | Implemented ✅ |
| Settings from env (pydantic-settings) | `app/config.py` | Implemented |
| Async DB session factory with rollback | `app/dependencies.py` | Implemented & Tested |
| Shared slowapi Limiter module | `app/rate_limit.py` | Implemented & Tested |
| MIME/extension/size file validation | `app/core/file_validator.py` | Implemented & Tested |
| All 4 ORM models (UUID PKs, TIMESTAMPTZ, JSONB, ARRAY) | `app/models/*.py` | Implemented & Tested |
| Legal doc versioning migration (`superseded_by` FK) | `alembic/versions/0002_legal_doc_versioning.py` | Implemented & Tested |
| Procedure graph — Kahn's topo sort | `app/core/procedure_graph.py` | Implemented & Tested |
| AgentState TypedDict (all fields) | `app/agents/state.py` | Implemented & Tested |
| PersonalData schema w/ confidence | `app/schemas/personal_data.py` (41 lines) | Implemented |
| ResidenceFormData + submission schemas | `app/schemas/form.py` (75 lines) | Implemented |
| ChatRequest/Response/Citation schemas | `app/schemas/chat.py` (28 lines) | Implemented |
| ProcedureDependency/Step/Plan schemas | `app/schemas/procedure.py` (51 lines) | Implemented |
| 10 unit tests for procedure graph | `tests/unit/test_procedure_graph.py` | Implemented & Tested |
| LLMService (async_invoke + stream + LangSmith) | `app/services/llm.py` | Implemented & Tested |
| EmbedderService (bge-m3 + OpenAI fallback) | `app/services/embedder.py` | Implemented & Tested |
| QdrantService (hybrid dense+BM25, RRF, active filter) | `app/services/qdrant_service.py` | Implemented & Tested |
| RedisService (Fernet-encrypted, 6-turn trim, 3600s TTL) | `app/services/redis_service.py` | Implemented & Tested |
| StorageService (MinIO PRIVATE, run_in_executor, promote_tmp) | `app/services/storage_service.py` | Implemented & Tested |
| PDFService (AcroForm+pdfrw, flat+reportlab, DI constructor) | `app/services/pdf_service.py` | Implemented & Tested |
| OCRService (two-path: QR decode + PaddleOCR, injection-hardened) | `app/services/ocr_service.py` | Implemented & Tested |
| router_node (execution_plan, ordering, ValueError on drift) | `app/agents/nodes/router.py` | Implemented & Tested |
| ocr_fn (QR-first → PaddleOCR fallback, lazy singleton) | `app/agents/nodes/ocr.py` | Implemented & Tested |
| node_registry (VALID_PLAN_STEPS, NODE_DEPENDENCIES, NODE_REGISTRY) | `app/agents/node_registry.py` | Implemented & Tested |
| router_prompt (RouterOutput, 8-shot Vietnamese prompt) | `app/agents/prompts/router_prompt.py` | Implemented & Tested |
| document_classifier_prompt (5-category vision classifier) | `app/agents/prompts/document_classifier_prompt.py` | Implemented & Tested |
| ocr_extraction_prompt (injection-hardened, SCHEMA_BLOCK ≤150 tokens) | `app/agents/prompts/ocr_extraction_prompt.py` | Implemented & Tested |
| SessionData schema | `app/schemas/session.py` | Implemented & Tested |
| DocumentChunk schema | `app/schemas/rag.py` | Implemented & Tested |
| 144 unit tests passing | `tests/unit/` | Implemented & Tested |

#### Backend — Scaffolded (stubs, not functional)
| Item | File | Confidence |
|---|---|---|
| Chat route stub | `app/api/v1/chat.py` | Scaffolded |
| Forms route stub | `app/api/v1/forms.py` | Scaffolded |
| Documents/procedures/legal routes | `app/api/v1/` | Scaffolded |
| enrichment_node, plan_executor_node, synthesizer_node | `app/agents/nodes/` | Scaffolded — implemented in TASK-09/TASK-10/TASK-11 |
| rag_fn, form_filler_fn worker stubs | `app/agents/nodes/rag.py`, `form_filler.py` | Scaffolded |
| LLM prompts: rag, form_mapping, synthesis | `app/agents/prompts/rag_prompt.py`, `form_mapping_prompt.py`, `synthesis_prompt.py` | Scaffolded |
| LangGraph graph stub | `app/agents/graph.py` | Scaffolded — fully rewritten in TASK-11 |
| procedure_planner_fn stub | `app/agents/nodes/procedure_planner.py` | Scaffolded — implemented in TASK-09 |

#### Frontend — Implemented
| Item | File | Confidence |
|---|---|---|
| Home page + all portal pages (7 total) | `src/app/*/page.tsx` | Implemented |
| 3 residence form pages w/ validation | `src/app/thu-tuc/*/page.tsx` | Implemented |
| ChatWidget (floating, SSE-ready) | `src/components/chat/ChatWidget.tsx` (267 lines) | Implemented |
| Header, Footer, layout | `src/components/layout/` | Implemented |
| All UI primitives | `src/components/ui/` | Implemented |
| chatStore (Zustand, SSE support) | `src/lib/stores/chatStore.ts` (54 lines) | Implemented |
| formStore (setFieldValue w/ source+confidence) | `src/lib/stores/formStore.ts` (124 lines) | Implemented |
| procedureStore | `src/lib/stores/procedureStore.ts` | Implemented |
| All TypeScript types (mirrors Pydantic) | `src/lib/types/index.ts` (135 lines) | Implemented |
| Zod validation schemas (3 forms) | `src/lib/schemas/residence-forms.ts` (96 lines) | Implemented |
| streamChat SSE client | `src/lib/api/client.ts` | Implemented |

#### Documentation
| Item | File | Confidence |
|---|---|---|
| Architecture blueprint | `docs/dichvucong_architecture_blueprint.md` | Documented |
| UI analysis (colors, spacing, components) | `docs/dichvucong_ui_analysis.md` | Documented |
| CLAUDE.md (architecture rules + skills index) | `CLAUDE.md` | Documented ✅ |
| Agent spec files | `.claude/agents/*.md` | Documented ✅ (router-agent.md updated for plan_executor topology) |
| 6 hook scripts | `.claude/hooks/*.sh` | Implemented |
| 10 skill files | `.claude/skills/` + `.agents/skills/` | Documented |

---

### 1.2 In Progress 🔄

Nothing is currently mid-implementation (all work is either complete or not yet started).

---

### 1.3 Not Started 📋

#### Backend Services (all 7 — skeletons exist but contain no logic)
- `app/services/redis_consumer.py` — Celery worker / async consumer (**TASK-03 Enhancement — not yet implemented**)

#### Backend Core Logic (skeletons exist)
- `app/core/form_field_mapper.py` — LLM semantic mapping of PersonalData → form fields
- `app/core/session_accumulator.py` — confidence-based PersonalData merge
- `app/core/citation_formatter.py` — `format_citation(chunk) -> str` + `verify_citations(response_text, retrieved_chunks) -> str`

#### LangGraph Graph Components

**True graph nodes still to implement (3):**
- `app/agents/nodes/enrichment.py` — `enrichment_node`: runs after Router, calls `procedure_planner_fn` directly if `target_procedure_id` is set AND `form_filler_fn` in plan, no-op otherwise. No LLM call. **(TASK-09)**
- `app/agents/nodes/plan_executor.py` — loop node; reads `NODE_DEPENDENCIES`, calls workers via `NODE_REGISTRY`, enforces `MAX_PLAN_STEPS=8` circuit-breaker. **(TASK-11)**
- `app/agents/nodes/synthesizer.py` — final response assembly with 6 response modes. **(TASK-10)**

**Pre-flight enrichment helper (called by enrichment_node, not in NODE_REGISTRY):**
- `app/agents/nodes/procedure_planner.py` — `procedure_planner_fn(state) -> dict` — DB query + topo sort → ExecutionPlan. **(TASK-09)**

**Worker functions still to implement:**
- `app/agents/nodes/rag.py` — `rag_fn(state) -> dict` — hybrid retrieval + cited generation + `verify_citations()` call. **(TASK-06)**
- `app/agents/nodes/form_filler.py` — `form_filler_fn(state) -> dict` — field mapping + PDF fill to `tmp/` + promote on completion. **(TASK-08)**

**Graph assembly:**
- `app/agents/graph.py` — `build_graph()` with topology: Entry → router_node → enrichment_node → plan_executor_node (loop) → synthesizer_node → END; `recursion_limit=10`. **(TASK-11)**

#### LLM Prompts (3 remaining stubs)
- `app/agents/prompts/rag_prompt.py` — cited generation prompt; must enforce `[Điều X, NĐ YYY]` citation format. **(TASK-06)**
- `app/agents/prompts/form_mapping_prompt.py` — semantic PersonalData → PDF field mapping. **(TASK-08)**
- `app/agents/prompts/synthesis_prompt.py` — 6 response modes (procedure plan / form fill / legal Q&A / clarification / error / hybrid). **(TASK-10)**

#### API Endpoints (functional implementations)
- `POST /api/v1/chat` — functional streaming SSE; catches `GraphRecursionError`
- `POST /api/v1/forms/submit` — real DB write + tracking code
- `POST /api/v1/documents/upload` — MIME/size/extension validation + MinIO store + OCR trigger
- `GET /api/v1/procedures/{id}/plan` — real DAG resolution

#### Data
- Real Vietnamese legal PDFs — **4 collected ✅, converted to PDF ✅ (2026-03-26), 0 ingested into Qdrant** — Luật Cư trú 2020 (68/2020/QH14), NĐ 62/2021/NĐ-CP, NĐ 104/2022/NĐ-CP, TT 55/2021/TT-BCA; stored in `backend/data/legal_documents/`
- Qdrant `legal_documents` collection (0 vectors) — chunks need `status: "active"` payload field
- PDF form templates for 3 residence procedures (0 collected)
- Synthetic CCCD images (0 generated)

#### Tests
- `tests/unit/test_plan_executor.py` — verify loop terminates correctly, circuit-breaker fires at `MAX_PLAN_STEPS`. **(TASK-11)**
- `tests/unit/test_form_mapper.py` — beyond placeholder (confidence-based merge, LLM cache check). **(TASK-08)**
- `tests/unit/test_session_accumulator.py` — beyond placeholder (carry-forward merge, higher-confidence wins). **(TASK-08)**
- `tests/integration/test_rag_pipeline.py` — ingest real PDF, retrieve chunk, verify citation metadata. **(TASK-14)**
- `tests/integration/test_agent_graph.py` — end-to-end with plan_executor topology, mocked LLM. **(TASK-14)**

---

## 2. Task Delegation Board

### Phase 0 Gaps — Complete Before Any Phase 2 Work ✅ COMPLETE

---
### TASK-0A: Async DB Session Factory + Security Baseline Fixes ✅ COMPLETE
**Phase:** 0 (pre-Phase 2 blocker)
**Priority:** Critical
**Estimated effort:** XS (2–3 hours)
**Depends on:** Nothing
**Can be parallelized with:** TASK-0B, TASK-0C, TASK-0D, TASK-0E
**Completed:** 2026-03-19

#### Goal
Implement `get_db()` async session factory and fix the three infrastructure security baseline items that cost nothing to do now but are expensive to retrofit later.

#### Inputs
- `app/dependencies.py` → stub (or create new)
- `docker-compose.yml` → Redis service configuration
- `app/main.py` → CORS config

#### Outputs
- `app/dependencies.py` — `get_db()` async generator using `async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)`; FastAPI lifespan function that initializes MinIO bucket with PRIVATE policy on startup
- `docker-compose.yml` — Redis service updated with `command: redis-server --requirepass ${REDIS_PASSWORD}`; `REDIS_PASSWORD` added to `.env`
- `app/main.py` — CORS `allow_origins` set to `["http://localhost:3000"]`, loaded from env var `CORS_ALLOW_ORIGINS`
- `tests/unit/test_dependencies.py` — verify `get_db()` yields `AsyncSession` and closes cleanly on exception

#### Definition of Done
- [x] `get_db()` yields an `AsyncSession` and rolls back correctly on exception
- [x] Redis container requires password authentication (verify with `redis-cli` without password → rejected)
- [x] CORS no longer uses `allow_origins=["*"]`
- [x] MinIO bucket initialized with explicit PRIVATE policy on backend startup
- [x] Unit test for `get_db()` passes with mocked engine

#### Notes / Constraints
- Use `async_sessionmaker` (not the legacy `sessionmaker`) — SQLAlchemy 2.0 async pattern
- `expire_on_commit=False` is required to avoid lazy-load errors in async contexts after commit
---

---
### TASK-0B: ORM Model Column Definitions + Procedure DAG Seed Edges ✅ COMPLETE
**Phase:** 0 (pre-Phase 2 blocker)
**Priority:** Critical
**Estimated effort:** S (half day)
**Depends on:** Nothing (schema already in `0001_initial_schema.py`)
**Can be parallelized with:** TASK-0A
**Completed:** 2026-03-19

#### Goal
Write the full SQLAlchemy ORM column definitions for all 4 model stubs and seed at least one real `procedure_dependencies` edge. The procedure DAG is the most critical data structure in the system — it must have real edges before TASK-09 can be tested meaningfully.

#### Inputs
- `app/models/procedure.py`, `app/models/form.py`, `app/models/legal_document.py`, `app/models/session.py` → stubs to implement
- `alembic/versions/0001_initial_schema.py` → source of truth for column names and types
- `ingestion/ingest_procedures.py` → add dependency edges

#### Outputs
- All 4 ORM model files — full column definitions matching the migration exactly (UUID PKs, TIMESTAMPTZ, JSONB where specified)
- `ingestion/ingest_procedures.py` — updated to insert at least one `procedure_dependencies` row (TTDN-003 requires TTDN-001 or TTDN-002, per Luật Cư trú 2020 Điều 20)
- `tests/unit/test_orm_models.py` — verify each model maps to the correct table and column types

#### Definition of Done
- [x] All 4 ORM models importable without error
- [x] `procedure_dependencies` table has at least 1 edge after running the seed script
- [x] `procedure_graph.resolve_execution_plan()` returns a non-trivial ordered plan with the new edge
- [x] ORM column names match migration exactly (no drift)
- [x] `/review-schema` checklist passes on all 4 model files

#### Notes / Constraints
- Do not modify `0001_initial_schema.py` — the ORM must match it, not the other way around
- All PKs are UUID using PostgreSQL `gen_random_uuid()` — do not use `Integer` auto-increment
---

---
### TASK-0C: Rate Limiting Middleware ✅ COMPLETE
**Phase:** 0 (implement before TASK-11 chat endpoint goes live)
**Priority:** High
**Estimated effort:** XS (1–2 hours)
**Depends on:** TASK-03 (Redis — rate limiter uses Redis backend)
**Can be parallelized with:** TASK-0A, TASK-0B, and all Phase 2 tasks
**Completed:** 2026-03-19

#### Goal
Add request rate limiting to the chat endpoint. Without throttling, a single client can exhaust API quota with 3–5 LLM calls per message.

#### Inputs
- `app/main.py` → add slowapi middleware
- `app/api/v1/chat.py` → apply limiter decorator
- Redis connection from `RedisService` (reuse existing)

#### Outputs
- `app/main.py` — `slowapi` `Limiter` registered as middleware; `RateLimitExceeded` exception handler returns HTTP 429 JSON
- `app/api/v1/chat.py` — `@limiter.limit(settings.CHAT_RATE_LIMIT)` on `POST /chat`, keyed by `session_id`
- `tests/unit/test_rate_limiting.py` — verify 429 returned after limit exceeded

#### Definition of Done
- [x] 11th request within 60 seconds for the same `session_id` returns HTTP 429 with JSON error body
- [x] Rate limit is keyed per `session_id`, not per IP
- [x] `CHAT_RATE_LIMIT` env var configures the limit (default `"10/minute"`)
- [x] Unit test passes with mocked Redis limiter backend

#### Notes / Constraints
- Use `slowapi` — do not implement a custom token bucket
- The limiter must reuse the Redis connection from `RedisService`, not open a separate connection
---

---
### TASK-0D: File Upload Validation ✅ COMPLETE
**Phase:** 0 (implement before TASK-12 document upload endpoint)
**Priority:** High
**Estimated effort:** XS (1–2 hours)
**Depends on:** Nothing
**Can be parallelized with:** TASK-0A, TASK-0B, TASK-0C
**Completed:** 2026-03-19

#### Goal
Add MIME type, file size, and extension validation to the document upload endpoint before it touches MinIO or the OCR pipeline.

#### Inputs
- `app/api/v1/documents.py` → call validator as first step
- `app/core/file_validator.py` → create new validation module

#### Outputs
- `app/core/file_validator.py` — `validate_upload(file: UploadFile) -> None` raising `HTTPException(422)` on:
  - MIME type not in whitelist: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`
  - File size > 5 MB
  - Extension not in whitelist: `.jpg`, `.jpeg`, `.png`, `.webp`, `.pdf`
- `tests/unit/test_file_validator.py` — test each rejection case

#### Definition of Done
- [x] Uploading a `.exe` returns HTTP 422 before touching MinIO
- [x] Uploading a file > 5 MB returns HTTP 422
- [x] A JPEG renamed to `.pdf` is caught by MIME check (not extension-based)
- [x] Valid JPEG, PNG, PDF uploads pass validation
- [x] Unit tests cover all rejection cases

#### Notes / Constraints
- Check actual MIME type via `python-magic`, not just the `Content-Type` header (clients can lie)
- File size check must not require reading the entire file into memory
---

---
### TASK-0E: Legal Document Versioning Strategy ✅ COMPLETE
**Phase:** 0 (design decision required before TASK-05 ingestion)
**Priority:** High
**Estimated effort:** XS (1 hour)
**Depends on:** Nothing
**Can be parallelized with:** TASK-0A through TASK-0D
**Completed:** 2026-03-19

#### Goal
Add a `status` field to the Qdrant chunk payload schema and update ingestion and search to use it. Implement soft-deprecation on re-ingestion so amended decrees can be updated without losing audit history.

#### Inputs
- `app/services/qdrant_service.py` → add `status` filter to all search calls
- `ingestion/ingest_legal_docs.py` → set `status: "active"` on new chunks; mark old as `"superseded"` on re-ingestion

#### Outputs
- `app/services/qdrant_service.py` — all `search()` calls include `FieldCondition(key="status", match=MatchValue(value="active"))`
- `ingestion/ingest_legal_docs.py` — `status: "active"` on every new chunk payload; re-ingestion path: scroll chunks matching `document_number`, batch-update to `"superseded"`, then upsert new
- `alembic/versions/0002_legal_doc_versioning.py` — new migration adding `superseded_by UUID REFERENCES legal_documents(id) NULLABLE` column to `legal_documents` table
- `tests/unit/test_legal_doc_versioning.py` — verify superseded chunks are excluded from search results

#### Definition of Done
- [x] Search never returns chunks with `status = "superseded"` — verified by unit test
- [x] Re-running ingestion on an updated PDF marks old chunks superseded, not deleted
- [x] Alembic migration `0002` created and applies cleanly on top of `0001`
- [x] Unit test passes (mock Qdrant, verify `status` filter is always applied)

#### Notes / Constraints
- Do not hard-delete old chunks on re-ingestion — soft-deprecate for auditability
- `status` is a string (not boolean) to allow future states like `"draft"`, `"pending_review"`
---

---
### TASK-0F: plan_executor Circuit-Breaker Design ⚠️ DESIGN COMPLETE — IMPLEMENTATION IN TASK-11
**Phase:** 0 (design; implemented inside TASK-11)
**Priority:** High
**Estimated effort:** XS (document design; implementation is part of TASK-11)
**Depends on:** Nothing
**Can be parallelized with:** Everything

#### Goal
Ensure the `plan_executor` loop cannot run forever. Two independent safeguards must be specified here and implemented in TASK-11.

#### Design (implement inside TASK-11)
- `MAX_PLAN_STEPS = 8` constant in `app/agents/nodes/plan_executor.py` (configurable via `MAX_PLAN_STEPS` env var)
- Inside `plan_executor`: if `state["plan_cursor"] >= MAX_PLAN_STEPS`, append `"Plan execution limit reached"` to `state["errors"]` and route to Synthesizer immediately without executing further steps
- `graph.compile(recursion_limit=10)` — LangGraph raises `GraphRecursionError` as a second independent safeguard
- `POST /api/v1/chat` handler catches `GraphRecursionError` and returns HTTP 500 JSON with a user-facing message (not a Python traceback)
- Worker functions in `NODE_REGISTRY` must never write to `execution_plan` or `plan_cursor` — only `plan_executor` owns those fields

#### Definition of Done (verified in TASK-11)
- [ ] `plan_executor` routes to Synthesizer when `plan_cursor >= MAX_PLAN_STEPS`
- [ ] `GraphRecursionError` caught in chat endpoint, returns HTTP 500 JSON
- [ ] `MAX_PLAN_STEPS` is configurable via env var (default 8)
- [ ] Unit test: a plan with 9 entries triggers circuit-breaker after step 8
---

---

### Phase 2 — AI Core (implement services + nodes)

---
### TASK-01: LLM Service + Router Node + LangSmith Init ✅ COMPLETE
**Phase:** 2
**Priority:** Critical
**Estimated effort:** S (1 day)
**Depends on:** TASK-0A (get_db + env baseline), TASK-0B (ORM models), ANTHROPIC_API_KEY in .env
**Can be parallelized with:** TASK-02, TASK-03, TASK-07
**Completed:** 2026-03-26

#### Goal
Implement the Anthropic LLM client wrapper, wire LangSmith tracing from day one, and implement the Router Node that decomposes every user message into an ordered `execution_plan: list[str]`. Update `.claude/agents/router-agent.md` before writing any code.

#### Inputs
- `app/agents/state.py` → verify `execution_plan: list[str]` and `plan_cursor: int` fields exist
- `app/services/llm.py` → stub to implement
- `app/agents/nodes/router.py` → stub to implement
- `app/agents/prompts/router_prompt.py` → stub to implement
- `.claude/agents/router-agent.md` → **update this spec for `execution_plan` output before implementing**
- `ANTHROPIC_API_KEY`, `LANGSMITH_API_KEY`, `LANGCHAIN_TRACING_V2` env variables (must be set)

#### Outputs
- `app/services/llm.py` — `LLMService` class with `async_invoke()` and `stream()` methods wrapping `anthropic.AsyncAnthropic`; `__init__` initialises LangSmith via `os.environ["LANGCHAIN_TRACING_V2"]` and `os.environ["LANGCHAIN_API_KEY"]` from settings
- `app/agents/prompts/router_prompt.py` — structured prompt returning `RouterOutput` with `execution_plan: list[str]` and `entities: dict`. Valid plan step values: `"rag_fn"`, `"ocr_fn"`, `"form_filler_fn"` ONLY. `"procedure_planner_fn"` is NOT a valid plan step — procedure resolution is handled by `enrichment_node`. Ordering rules: `ocr_fn` always precedes `form_filler_fn` if both present; `rag_fn` may appear in any position. An empty execution_plan is only valid for unclassifiable or trivial messages. Any message expressing procedural intent, legal inquiry, or form fill intent must produce a non-empty plan.
- `app/agents/nodes/router.py` — `router_node(state)` returning `{"execution_plan": [...], "entities": {...}, "plan_cursor": 0}`
- `tests/unit/test_router_node.py` — 20+ tests with mocked LLM covering diverse Vietnamese government queries; verify `execution_plan` list contents, ordering, and that `plan_cursor` is reset to 0

#### Definition of Done
- [x] `router_node` returns `execution_plan = ["rag_fn"]` for "Tôi muốn đăng ký thường trú" — `enrichment_node` handles DAG resolution; `rag_fn` handles the cited legal explanation the user actually needs
- [x] `router_node` returns `execution_plan = []` ONLY for messages that require neither legal retrieval, OCR, nor form filling — for example a bare greeting or a question the Router cannot classify. This must be tested explicitly with a case like "Xin chào" → `[]`.
- [x] `router_node` returns `execution_plan = ["ocr_fn", "form_filler_fn"]` when `uploaded_image_path` is not None and message implies form fill
- [x] `router_node` returns `execution_plan = ["rag_fn"]` for a pure legal question with no image
- [x] `router_node` returns a multi-step plan for a message with both an uploaded image and a legal question
- [x] `plan_cursor` is always `0` in the returned dict
- [ ] LangSmith traces visible in project dashboard for a real invocation (requires ANTHROPIC_API_KEY to be set — not verified in unit tests)
- [x] All 20+ unit tests pass with mocked Anthropic client — 31 tests passing
- [x] `.claude/agents/router-agent.md` updated before implementation starts
- [ ] `/review-agent-node` checklist passes

#### Notes / Constraints
- LLM calls in unit tests **must** be mocked — no real API calls in `tests/unit/` (CLAUDE.md rule)
- Valid `execution_plan` strings must exactly match `NODE_REGISTRY` keys — define them as a constant and import into the prompt template to prevent typo drift
- Do not use Claude Vision as fallback for OCR — document type classification is the only permitted vision call
---

---
### TASK-02: Embedder Service + Qdrant Service ✅ COMPLETE
**Phase:** 2
**Priority:** Critical
**Estimated effort:** M (2 days)
**Depends on:** TASK-0E (status field design confirmed)
**Can be parallelized with:** TASK-01, TASK-03, TASK-04, TASK-07
**Completed:** 2026-03-26

#### Goal
Implement the embedding service supporting two backends — bge-m3 (local, primary) and OpenAI `text-embedding-3-large` (cloud, fallback) — selected via `EMBEDDING_BACKEND` env var. Also implement the Qdrant hybrid search service with `status = "active"` filtering and a 6,000-token context budget cap.

#### Inputs
- `app/services/embedder.py` → stub to implement
- `app/services/qdrant_service.py` → stub to implement
- Qdrant running at `http://localhost:6333` (Docker already up)
- Architecture blueprint §5.2 — retrieval strategy
- `EMBEDDING_BACKEND` env var — already defined in `backend/.env` as `bge-m3`; set to `openai` to activate fallback. `OPENAI_API_KEY` env var — only required when `EMBEDDING_BACKEND=openai`.

#### Outputs
- `app/services/embedder.py` — `EmbedderService` with `embed(text: str) -> list[float]`. Backend selected at init time from `settings.EMBEDDING_BACKEND`:
  - `"bge-m3"` (default): loads `BAAI/bge-m3` via `sentence-transformers`, returns 1024-dim vectors. Model cached in `.cache/` via `SENTENCE_TRANSFORMERS_HOME`. First load downloads ~2.2 GB.
  - `"openai"`: calls `openai.embeddings.create(model="text-embedding-3-large")`, returns 3072-dim vectors truncated to 1024 via the `dimensions` parameter to keep Qdrant collection schema consistent. Requires `OPENAI_API_KEY` to be set.
  - Both backends expose the same `embed(text: str) -> list[float]` interface — all callers are backend-agnostic.
  - If `EMBEDDING_BACKEND=bge-m3` and the model fails to load (import error, download failure, or OOM), `EmbedderService.__init__` logs a warning and automatically falls back to `"openai"`. If `OPENAI_API_KEY` is also absent, raises `RuntimeError` with a clear message: `"No embedding backend available: bge-m3 failed to load and OPENAI_API_KEY is not set."`.
- `app/services/qdrant_service.py` — `QdrantService` with:
  - `create_collection()` — creates `legal_documents` collection
  - `upsert(chunks)` — batch upsert with payload including `status: "active"`
  - `search(query, procedure_id, top_k) -> list[DocumentChunk]` — dense + BM25 + RRF, always filtered to `status = "active"`, combined text truncated to 6,000 tokens (lowest-ranked chunks dropped first). BM25 stage: scrolls all payload-matching chunks from Qdrant, builds in-memory `BM25Okapi` index, scores query, returns top-k results. RRF merge formula: `score = 1 / (rank + 60)` summed across both result lists. Final list truncated to 6,000 tokens (lowest RRF score dropped first).
- `tests/unit/test_qdrant_service.py` — mocked Qdrant client; verify `status` filter is always present in search payload

#### Definition of Done
- [x] `EmbedderService.embed("test")` returns a list of 1024 floats when `EMBEDDING_BACKEND=bge-m3` — verified with mocked sentence-transformers
- [x] `EmbedderService.embed("test")` returns a list of 1024 floats when `EMBEDDING_BACKEND=openai` — verified with mocked `openai` client; confirms `dimensions=1024` is passed to the API call
- [x] When bge-m3 load raises an `ImportError`, `EmbedderService` automatically switches to OpenAI backend — verified by unit test that mocks the sentence-transformers import to fail and asserts the OpenAI client is used instead
- [x] `QdrantService.search(...)` always includes `status = "active"` filter — verified by unit test intercepting the Qdrant call
- [x] Combined retrieved text is truncated to ≤ 6,000 tokens before being returned
- [x] BM25 index built on-demand from `content` field
- [x] `rank-bm25` is listed in `backend/requirements.txt` and `BM25Okapi` is importable without error
- [ ] `/review-agent-node` checklist passes

#### Notes / Constraints
- Always use **both** dense + BM25 stages — never skip BM25 (CLAUDE.md rule). BM25 is implemented in-memory using the `rank_bm25` library (Option C). At search time, `QdrantService` scrolls all chunks for the relevant `procedure_tags` filter from Qdrant, builds a `BM25Okapi` index from their `content` fields, scores the query against it, and merges the top-k BM25 results with the dense search results via RRF. The BM25 index is rebuilt per search call — it is not persisted. This is appropriate for the current corpus size (4 documents, ~200–400 chunks) and can be replaced with Qdrant native sparse vectors if the collection grows beyond a few thousand chunks. Add `rank-bm25` to `backend/requirements.txt`.
- The `procedure_id` parameter in `search(query, procedure_id, top_k)` is optional (`str | None`). When provided, it filters Qdrant retrieval to chunks whose `procedure_tags` payload contains that procedure UUID. When `None`, search runs unfiltered across the full collection — this is the correct behaviour for general legal questions not tied to a specific procedure. The value flows from `state["entities"].get("procedure_id")` inside `rag_fn` (TASK-06) — `QdrantService` itself never reads `AgentState` directly.
- The Qdrant collection is created with `vector_size=1024` regardless of which embedding backend is active — the OpenAI backend uses `dimensions=1024` truncation to stay consistent. Never create the collection with `vector_size=3072` even when using OpenAI embeddings directly.
- Qdrant collection name: `"legal_documents"` (defined in architecture blueprint §10)
- bge-m3 first load downloads ~2.2 GB — cache in `.cache/` via `SENTENCE_TRANSFORMERS_HOME`
---

---
### TASK-03: Redis Service + Session Management ✅ COMPLETE
**Phase:** 2
**Priority:** High
**Estimated effort:** S (1 day)
**Depends on:** TASK-0A (Redis auth configured in Docker Compose)
**Can be parallelized with:** TASK-01, TASK-02, TASK-04, TASK-07
**Completed:** 2026-03-26

#### Goal
Implement the Redis session service with 1-hour TTL and Fernet encryption of all PII values at rest.

#### Inputs
- `app/services/redis_service.py` → stub to implement
- `app/schemas/personal_data.py` → `PersonalData` schema (source of truth)
- Redis running with password auth (configured in TASK-0A)
- Architecture blueprint §ADR-006

#### Outputs
- `app/services/redis_service.py` — `RedisService` with:
  - `get_session(session_id: str) -> SessionData` — decrypts value after retrieval
  - `save_session(session_id: str, data: SessionData) -> None` — Fernet-encrypts value, sets `ex=3600`
  - `get_cached_response(key: str) -> str | None`
  - `cache_response(key: str, value: str, ttl: int) -> None`
- `app/schemas/session.py` (new) — `SessionData` Pydantic model with `personal_data`, `completed_procedure_ids`, `form_fill_state`
- `tests/unit/test_redis_service.py` — mocked Redis; verify TTL argument, verify raw stored value is ciphertext not plaintext JSON

#### Definition of Done
- [x] `save_session` + `get_session` round-trips `SessionData` correctly
- [x] `PersonalData` serializes/deserializes without data loss (dates, confidence scores)
- [x] Session TTL is exactly 3600 seconds — unit test inspects the `ex` argument passed to `redis.set()`
- [x] Raw `redis.get()` on a saved session returns ciphertext, not plaintext JSON
- [x] Unit tests pass with mocked Redis
- [x] `save_session()` trims `conversation_history` to the last 6 entries before serialising — verified by unit test with a 10-turn history input

#### Notes / Constraints
- `REDIS_ENCRYPTION_KEY` env var — 32-byte base64 Fernet key; add to `.env`
- JSON serialization of `date` fields requires custom encoder
- Session data lives in Redis, **never** persisted in `AgentState` long-term (CLAUDE.md Rule 4)
- The trim happens in `save_session()`, not in the agent nodes — nodes append freely to history, the service enforces the window on write
---

---
### TASK-04: OCR Service + ocr_fn Worker + OCR Prompt ✅ COMPLETE
**Phase:** 2
**Priority:** High
**Estimated effort:** M (2–3 days)
**Depends on:** TASK-01 (LLMService), TASK-0D (upload validation)
**Can be parallelized with:** TASK-02 ✅, TASK-03 ✅, TASK-07 ✅
**Completed:** 2026-03-27

#### Goal
Implement the document extraction pipeline as a worker function. The pipeline has two primary paths: a fast zero-token QR decode path for CCCD documents, and a full OCR path for all other document types and CCCD fallback. The two paths are implemented as separate sub-components under a single `ocr_fn` entry point.

#### Architecture: Two-path pipeline

```
Uploaded image
  → QR decode path (CCCD primary):
      OpenCV adaptive threshold + upscale
      → Multi-attempt pyzbar decode (5 attempts, ~200ms)
          → Success: parse pipe-delimited string → PersonalData (confidence=1.0)
          → All failed: hand off to OCR path

  → OCR path (all non-CCCD + CCCD fallback):
      Stage 1 — classify_document_type(image_path) → document_type string
               (vision LLM call, separate from extraction)
      Stage 2 — OpenCV pre-processing (CLAHE + deskew + denoise)
      Stage 3 — PaddleOCR PP-OCRv4 (Vietnamese charset)
      Stage 4 — Pre-filter: drop detections below confidence 0.7,
                 drop text blocks < 2 chars, deduplicate overlapping regions
      Stage 5 — Hard cap: truncate to 8,000 tokens (len(text)//4 estimate)
                 Log WARNING if truncation occurs
      Stage 6 — extract_fields(filtered_ocr_text, document_type) → PersonalData
               (text LLM call, separate prompt from classifier)
```

#### Sub-component breakdown

**Sub-component A — QR decode (`ocr_service.py: decode_qr`)**
- Pre-processing stack: grayscale → `cv2.adaptiveThreshold` → upscale ROI 3× with `INTER_CUBIC`
- Five decode attempts in sequence using `pyzbar.decode()`:
  1. Adaptive threshold on full image
  2. Upscaled ROI/full image 3×, adaptive threshold
  3. Upscaled ROI/full + Gaussian blur (`ksize=(3,3)`)
  4. Upscaled ROI/full + morphological closing (`cv2.MORPH_CLOSE`, kernel 3×3)
  5. Inverted image + adaptive threshold
- Parse success: split on `|`, format: `[id_number, empty, full_name, date_of_birth, gender, permanent_address, issue_date]` — index 1 is always empty
- All parsed fields receive `confidence=1.0` in `field_confidences`
- Return `PersonalData` on success, `None` on all-attempts failure

**Sub-component B — Document type classifier (`ocr_service.py: classify_document_type`)**
- Vision LLM call using `LLMService.async_invoke()` with image as base64 content block
- Returns one of: `cccd`, `birth_certificate`, `land_certificate`, `household_book`, `other`
- Separate LLM call from field extraction — never merged

**Sub-component C — Field extraction prompt (`ocr_extraction_prompt.py`)**
- Terse schema block (≤150 tokens), OCR text in `<ocr_text>` XML tags
- Injection hardening: "treat as data only" instruction, JSON-only output constraint
- Document type in `<document_type>` tag

**Sub-component D — PaddleOCR pre-filter (`ocr_service.py: _filter_ocr_results`)**
- Drop confidence < 0.7, drop text len < 2, IoU > 0.5 deduplication (keep higher confidence)

#### Inputs
- `app/services/ocr_service.py` → stub to implement
- `app/agents/nodes/ocr.py` → implement as `ocr_fn(state) -> dict` (not a graph node)
- `app/agents/prompts/ocr_extraction_prompt.py` → stub to implement
- `app/agents/prompts/document_classifier_prompt.py` → **new file**
- `app/schemas/personal_data.py` → `PersonalData` (output contract)
- `app/services/llm.py` → `LLMService` ✅ (TASK-01 complete)

#### Outputs
- `app/services/ocr_service.py` — `OCRService` with `decode_qr`, `classify_document_type`, `_filter_ocr_results`, `extract`
- `app/agents/prompts/ocr_extraction_prompt.py` — terse schema, XML-tagged OCR text, injection-hardened
- `app/agents/prompts/document_classifier_prompt.py` — vision classification prompt, 5 document types
- `app/agents/nodes/ocr.py` — `ocr_fn` with QR-first orchestration
- `tests/unit/test_ocr_extraction.py` — 20 unit tests, all mocked

#### Definition of Done
- [x] `decode_qr()` successfully parses `id_number||full_name|dob|gender|address|issue_date` with all 7 fields populated and `confidence=1.0`
- [x] `decode_qr()` returns `None` after all 5 attempts fail
- [x] `decode_qr()` attempts exactly 5 decode variants before returning `None`
- [x] `ocr_fn()` skips PaddleOCR and LLM extraction entirely when `decode_qr()` succeeds
- [x] `classify_document_type()` returns one of the 5 valid document type strings
- [x] Extraction prompt schema block is ≤ 150 tokens
- [x] `_filter_ocr_results()` drops detections below confidence 0.7
- [x] `_filter_ocr_results()` drops text blocks shorter than 2 characters
- [x] LLM extraction returns `null` for fields it cannot find
- [x] An injection string in OCR text does not appear in `PersonalData` output
- [x] PaddleOCR is called via `run_in_executor`
- [x] OCR text truncated to ≤ 8,000 tokens before LLM call — WARNING log emitted
- [x] `PersonalData.field_confidences` populated for every non-null field
- [x] CCCD id_number validation: 12 digits, province code 001–096
- [x] OpenCV pre-processing runs without error on a test JPEG
- [x] `ocr_fn` does not import from `graph.py`

#### Notes / Constraints
- PaddleOCR is synchronous — always wrap in `run_in_executor`. Never call directly in async context.
- `classify_document_type()` and `extract()` are two separate LLM calls with two separate prompts.
- QR-decoded fields receive `confidence=1.0` — always win over OCR in `SessionDataAccumulator.merge()`.
- CCCD QR format: `id_number||full_name|dob|gender|address|issue_date` — index 1 always empty.
- `pyzbar` requires `libzbar0` system library: `sudo apt-get install libzbar0` on Linux.
---

---
### TASK-05: Legal Document Ingestion Pipeline
**Phase:** 2
**Priority:** Critical
**Estimated effort:** M (2 days)
**Depends on:** TASK-02 (EmbedderService + QdrantService), TASK-0E (status field)
**Can be parallelized with:** TASK-03, TASK-04, TASK-07

#### Goal
Implement the offline ingestion script with soft-deprecation on re-ingestion. Every chunk must have `status: "active"` and non-empty `procedure_tags`.

#### Inputs
- `ingestion/ingest_legal_docs.py` → stub to implement
- `app/services/embedder.py` → `EmbedderService` ⚠️ Blocked until TASK-02
- `app/services/qdrant_service.py` → `QdrantService` ⚠️ Blocked until TASK-02
- Vietnamese legal source documents — **downloaded ✅** to `backend/data/legal_documents/`:
  - `68_2020_QH14_435315.doc` — Luật Cư trú 2020 (Luật số 68/2020/QH14)
  - `62_2021_ND-CP_473325.doc` — Nghị định 62/2021/NĐ-CP
  - `104_2022_ND-CP_544177.doc` — Nghị định 104/2022/NĐ-CP (supersedes 144/2021)
  - `55_2021_TT-BCA_466836.doc` — Thông tư 55/2021/TT-BCA
  - ⚠️ **All files are `.doc` (Word) format.** The ingestion script uses Docling which works best with PDF. Convert each `.doc` to `.pdf` using LibreOffice (`libreoffice --headless --convert-to pdf *.doc`) before running the ingestion pipeline.

#### Outputs
- `ingestion/ingest_legal_docs.py` — PDF → Docling → chunker → embed → Qdrant; re-ingestion marks old chunks `"superseded"` before upserting new
- Qdrant `legal_documents` collection populated with chunks
- Each chunk payload: `legal_document_id`, `document_number`, `article_number`, `procedure_tags`, `content`, `status: "active"`, `effective_date`

#### Definition of Done
- [ ] Script runs to completion on at least one real legal PDF without error
- [ ] Chunks in Qdrant never span two articles
- [ ] Every chunk has non-empty `procedure_tags` and `status: "active"`
- [ ] Re-running script on same PDF marks old chunks `"superseded"` without duplicating content
- [ ] `QdrantService.search("đăng ký thường trú")` returns relevant chunks
- [ ] Integration test `tests/integration/test_rag_pipeline.py` passes

#### Notes / Constraints
- **Never ingest without procedure_tags** — untagged chunks are unretrievable in filtered search (CLAUDE.md rule)
- Chunk at article boundaries — never split mid-article
---

---
### TASK-06: RAG Worker Function + RAG Prompt + Citation Verifier
**Phase:** 2
**Priority:** Critical
**Estimated effort:** S (1 day)
**Depends on:** TASK-01 (LLMService), TASK-02 (QdrantService), TASK-0E (status field)
**Can be parallelized with:** TASK-03, TASK-04, TASK-07, TASK-08

#### Goal
Implement `rag_fn` as a worker function (not a graph node) and implement `verify_citations()` as a post-generation check in `citation_formatter.py`.

#### Inputs
- `app/agents/nodes/rag.py` → implement as `rag_fn(state) -> dict`
- `app/agents/prompts/rag_prompt.py` → stub to implement
- `app/services/qdrant_service.py` → `QdrantService` ⚠️ Blocked until TASK-02
- `app/services/llm.py` → `LLMService` ⚠️ Blocked until TASK-01
- `app/core/citation_formatter.py` → implement both functions
- `.claude/agents/rag-agent.md` → full behavioural spec — **read before starting**

#### Outputs
- `app/agents/nodes/rag.py` — `rag_fn(state) -> dict` returning `{"retrieved_chunks": [...], "citations": [...], "final_response": "..."}`; calls `verify_citations()` before returning
- `app/agents/prompts/rag_prompt.py` — system prompt enforcing `[Điều X, Nghị định YYY]` citation format
- `app/core/citation_formatter.py`:
  - `format_citation(chunk) -> str`
  - `verify_citations(response_text: str, retrieved_chunks: list[QdrantChunk]) -> str` — cross-checks every `[Điều X, Nghị định YYY]` reference against retrieved chunk payloads; flags unverified citations as `[unverified: Điều X, Nghị định YYY]`

#### Definition of Done
- [ ] `rag_fn` returns at least 1 citation for a question about residence registration
- [ ] `verify_citations()` flags a hallucinated article number as `[unverified: ...]` — verified by unit test
- [ ] A correct citation present in retrieved chunks passes through unchanged
- [ ] Citation format matches `[Điều X, Nghị định/Thông tư YYY/YYYY/NĐ-CP]`
- [ ] `/review-agent-node` checklist passes

#### Notes / Constraints
- `rag_fn` is a plain function, not a LangGraph node
- Do not use dense-only retrieval — always call `_bm25_search` as well (CLAUDE.md rule)
---

---
### TASK-07: PDF Service + Storage Service + MinIO Bucket Init ✅ COMPLETE
**Phase:** 2
**Priority:** High
**Estimated effort:** S (1 day)
**Depends on:** TASK-0A (PRIVATE bucket policy pattern established)
**Can be parallelized with:** TASK-01, TASK-02, TASK-03, TASK-04, TASK-05, TASK-06
**Completed:** 2026-03-26

#### Goal
Implement MinIO file storage with PRIVATE bucket policy and the PDF form fill service. Partially filled PDFs must be written to a `tmp/` prefix and only moved to the final path when all required fields are confirmed.

#### Inputs
- `app/services/pdf_service.py` → stub to implement
- `app/services/storage_service.py` → stub to implement
- MinIO running at `localhost:9000` (Docker already up, bucket not yet created)
- Architecture blueprint §8.3

#### Outputs
- `app/services/storage_service.py` — `StorageService` with:
  - `upload(path, file)`, `download(path) -> bytes`, `get_url(path) -> str`
  - `promote_tmp(tmp_path, final_path)` — `copy_object` then delete tmp; called by `form_filler_fn` on completion
  - `__init__` creates bucket with explicit PRIVATE policy (anonymous `get_object` returns 403)
- `app/services/pdf_service.py` — `PDFService` with:
  - `fill(template_path, field_values, session_id, form_id) -> str` — returns `tmp/{session_id}/{form_id}.pdf` MinIO path
  - `_fill_acroform(...)` using pdfrw
  - `_fill_overlay(...)` using reportlab
  - PDF type detection via pdfplumber `catalog.get("/AcroForm")` check

#### Definition of Done
- [x] `StorageService.upload()` + `download()` round-trip a file through MinIO
- [x] MinIO bucket has explicit PRIVATE policy — anonymous `get_object` returns 403
- [x] `PDFService.fill()` writes to `tmp/` prefix, not final path
- [x] `PDFService.fill()` correctly detects AcroForm vs flat PDF
- [x] `_fill_acroform` fills at least one test field and produces a readable PDF

#### Notes / Constraints
- Using pdfrw on a flat PDF will silently produce unfilled output — the type detection check is mandatory (CLAUDE.md rule)
- Uploaded images go to MinIO, **never** stored in PostgreSQL
---

---
### TASK-08: Form Field Mapper + Session Accumulator + form_filler_fn Worker
**Phase:** 3
**Priority:** High
**Estimated effort:** M (2–3 days)
**Depends on:** TASK-01 (LLMService), TASK-04 (OCR/PersonalData), TASK-07 (PDFService + StorageService)
**Can be parallelized with:** TASK-09 (after deps satisfied)

#### Goal
Implement the LLM-driven semantic field mapping, the confidence-based carry-forward merge, and the `form_filler_fn` worker function. Partially filled forms must never be promoted to the final MinIO path.

#### Inputs
- `app/core/form_field_mapper.py` → stub to implement
- `app/core/session_accumulator.py` → stub to implement
- `app/agents/nodes/form_filler.py` → implement as `form_filler_fn(state) -> dict` (not a graph node)
- `app/agents/prompts/form_mapping_prompt.py` → stub to implement
- `app/services/storage_service.py` → `StorageService.promote_tmp()` ⚠️ Blocked until TASK-07
- `.claude/agents/form-filler-agent.md` → full behavioural spec — **read before starting**

#### Outputs
- `app/core/form_field_mapper.py` — `FormFieldMapper.map(personal_data, form_fields) -> FieldMapping` using LLM
- `app/core/session_accumulator.py` — `SessionDataAccumulator.merge(existing, new) -> PersonalData` (higher confidence wins)
- `app/agents/nodes/form_filler.py` — `form_filler_fn(state) -> dict` returning `{"filled_fields": ..., "unfilled_required_fields": [...]}`;  calls `storage_service.promote_tmp()` only when `unfilled_required_fields` is empty
- `tests/unit/test_form_mapper.py` — real implementation tests
- `form_filler_fn` includes cache-check logic: load `form_templates.fields` → if populated use directly → if null call `FormFieldMapper.map()` then persist result to DB before continuing

#### Definition of Done
- [ ] `merge()` overwrites with new value only when `new_confidence >= old_confidence`
- [ ] `form_filler_fn` adds unfillable required fields to `unfilled_required_fields` — never fails silently
- [ ] LLM mapping returns `REQUIRES_USER_INPUT` for fields not in PersonalData
- [ ] PDF is only promoted from `tmp/` to final path when `unfilled_required_fields` is empty
- [ ] Unit tests for merge rule pass (4 edge cases minimum)
- [ ] `/review-agent-node` checklist passes
- [ ] `form_filler_fn` checks `form_templates.fields` JSONB before calling `FormFieldMapper.map()` — LLM mapping call is skipped if cached mapping exists
- [ ] On first successful mapping for a given `form_id`, the resolved mapping is written back to `form_templates.fields` in PostgreSQL
- [ ] Unit test verifies that a second call for the same `form_id` does NOT invoke `FormFieldMapper.map()` (mock confirms LLM is not called)

#### Notes / Constraints
- **Never hard-code field mappings** (CLAUDE.md rule) — use `FormFieldMapper` for every form
- `form_filler_fn` is a plain function, not a LangGraph node
---

---
### TASK-09: Procedure Planner — Pre-flight Enrichment Node
**Phase:** 2
**Priority:** High
**Estimated effort:** S (1 day)
**Depends on:** TASK-0A (`get_db()`), TASK-0B (ORM models + seed edges)
**Can be parallelized with:** TASK-08

#### Goal
Implement `enrichment_node` as a true LangGraph graph node (not a worker function) that runs after the Router on every invocation. If `target_procedure_id` is set in state AND `form_filler_fn` is present in `state['execution_plan']`, calls `procedure_planner_fn` directly and writes `procedure_execution_plan` into state. If either condition is false, returns an empty dict immediately (no-op). This prevents unnecessary DB queries and token injection for queries that mention a procedure but do not involve form filling.

`procedure_planner_fn` makes no LLM call — it is a DB query plus a pure Python topological sort taking under 50ms. It must not occupy a plan slot in `execution_plan` alongside LLM-heavy workers. It is called directly by `enrichment_node`, never via `NODE_REGISTRY`.

#### Inputs
- `app/agents/nodes/enrichment.py` → **new file** to create
- `app/agents/nodes/procedure_planner.py` → implement `procedure_planner_fn(state) -> dict` (helper, not a graph node)
- `app/core/procedure_graph.py` → `resolve_execution_plan()` — **already implemented and tested**
- PostgreSQL `procedure_dependencies` table — must have edges from TASK-0B seed
- `app/schemas/procedure.py` → `ProcedureDependency`, `ProcedureStep`, `ExecutionPlan`
- `.claude/agents/procedure-planner-agent.md` → full behavioural spec — **read before starting**

#### Outputs
- `app/agents/nodes/enrichment.py` — `enrichment_node(state) -> dict`: if `state["target_procedure_id"]` is set AND `"form_filler_fn"` is present in `state["execution_plan"]`, calls `procedure_planner_fn(state)` and returns the result dict; otherwise returns `{}` (no-op). This is a true LangGraph graph node wired between Router and plan_executor.
- `app/agents/nodes/procedure_planner.py` — `procedure_planner_fn(state) -> dict` querying DB via `get_db()`, calling `resolve_execution_plan()`, returning `{"procedure_execution_plan": [...]}`. Plain Python helper — not a graph node, not in `NODE_REGISTRY`.
- `tests/unit/test_procedure_planner_node.py` — mocked DB session; includes test that `enrichment_node` returns `{}` when `target_procedure_id` is `None`

#### Definition of Done
- [ ] `enrichment_node` correctly writes `procedure_execution_plan` for a procedure with at least one dependency
- [ ] `enrichment_node` is a no-op (returns `{}`) when `target_procedure_id` is `None` — verified by unit test
- [ ] `enrichment_node` returns empty dict when `target_procedure_id` is set but `form_filler_fn` is NOT in `execution_plan` — verified by unit test
- [ ] `enrichment_node` returns empty dict when `form_filler_fn` is in `execution_plan` but `target_procedure_id` is None — verified by unit test
- [ ] Completed steps (from `state["completed_procedures"]`) are marked `COMPLETED` in the plan
- [ ] `topological_sort` is called via `procedure_graph.py`, **not** re-implemented in the function
- [ ] `"procedure_planner_fn"` does NOT appear as a key in `NODE_REGISTRY`
- [ ] `"procedure_planner_fn"` does NOT appear as a valid `execution_plan` entry in any router test
- [ ] `/review-agent-node` checklist passes

#### Notes / Constraints
- `enrichment_node` must never make an LLM call — if you find yourself adding one, the logic belongs in the Synthesizer or a worker function instead
- `procedure_planner_fn` is a plain helper function called by `enrichment_node` — not a LangGraph node, not in `NODE_REGISTRY`
- **Do not put topological sort logic inside either function** — call `procedure_graph.resolve_execution_plan()` (CLAUDE.md Rule 1)
- `enrichment_node` must check whether `"form_filler_fn"` is present in `state["execution_plan"]` before performing any work. If `"form_filler_fn"` is not in the plan, return an empty dict immediately regardless of whether `target_procedure_id` is set.
- The lazy-check guard (`form_filler_fn` in `execution_plan`) is the primary token-saving mechanism of this node. Without it, any procedure-related query injects a full procedure plan into the Synthesizer prompt regardless of relevance. Do not remove this guard without a documented reason.
---

---
### TASK-10: Synthesizer Node + Synthesis Prompt
**Phase:** 3
**Priority:** High
**Estimated effort:** M (2 days)
**Depends on:** TASK-06 (rag_fn), TASK-08 (form_filler_fn), TASK-09 (enrichment_node)
**Can be parallelized with:** TASK-11 (after deps)

#### Goal
Implement the Synthesizer — the only true output graph node after `plan_executor`. It assembles `final_response` from all accumulated state fields. The Synthesizer must handle six distinct response modes cleanly from a single node — the synthesis prompt must be designed to cover all of them before any code is written:

  1. **RAG only** — legal question answered with citations, no form or OCR context
  2. **OCR only** — document uploaded and extracted, no form fill requested
  3. **Form fill complete** — all required fields filled, PDF ready for download
  4. **Form fill partial** — some required fields missing, user must be prompted for specific missing values (sourced from `unfilled_required_fields`)
  5. **Multi-worker combined** — RAG + OCR + form fill all ran in same invocation
  6. **Circuit-breaker or error** — `errors` list is non-empty; surface a user-friendly message without exposing internal state or tracebacks

Design the synthesis prompt to handle all six modes via conditional sections keyed on which state fields are populated. Do not implement six separate prompts — one prompt with conditional logic is correct.

#### Inputs
- `app/agents/nodes/synthesizer.py` → stub to implement
- `app/agents/prompts/synthesis_prompt.py` → stub to implement
- `app/services/llm.py` → `LLMService` ⚠️ Blocked until TASK-01
- `app/agents/state.py` → reads `retrieved_chunks`, `citations`, `procedure_execution_plan`, `unfilled_required_fields`, `errors`
- `.claude/agents/synthesizer-agent.md` → full behavioural spec — **read before starting**

#### Outputs
- `app/agents/nodes/synthesizer.py` — `synthesizer_node(state)` (true LangGraph node) returning `{"final_response": "...", "response_metadata": {...}}`; surfaces `errors` gracefully if present
- `app/agents/prompts/synthesis_prompt.py`

#### Definition of Done
- [ ] `final_response` is a clean string (not raw state dump)
- [ ] If `unfilled_required_fields` is non-empty, response asks user for missing data
- [ ] If `errors` is non-empty (e.g. circuit-breaker fired), response surfaces a user-friendly message
- [ ] Citations included in response when `retrieved_chunks` is non-empty
- [ ] **Only** `final_response` and `response_metadata` stream to frontend — not raw state
- [ ] `/review-agent-node` checklist passes
- [ ] Unit tests cover all six response modes with appropriate mocked state
- [ ] Synthesis prompt reviewed against all six modes before implementation begins — do not write code until the prompt handles all six cleanly

#### Notes / Constraints
- **Do not stream raw LangGraph state** — only `final_response` goes over SSE (CLAUDE.md rule)
- The synthesis prompt receives only the windowed history from state — never construct a full session history inside the node
- This is the only node that must be aware of the full accumulated state shape after all worker functions have run
---

---
### TASK-11: LangGraph Graph Assembly (plan_executor topology) + Functional Chat Endpoint
**Phase:** 4
**Priority:** Critical
**Estimated effort:** M (2 days)
**Depends on:** TASK-01, TASK-06, TASK-08, TASK-09, TASK-10, TASK-0F (circuit-breaker design)
**Can be parallelized with:** TASK-13

#### Goal
Wire the graph using the `plan_executor` loop topology (with `enrichment_node` and parallel wave execution via `NODE_DEPENDENCIES`), implement `NODE_REGISTRY`, and wire the functional streaming SSE chat endpoint. Implements the TASK-0F circuit-breaker design.

#### Inputs
- `app/agents/graph.py` → 6-line stub to fully rewrite
- `app/agents/nodes/plan_executor.py` → **new file** to create
- `app/agents/node_registry.py` → **new file** to create
- All worker functions from `app/agents/nodes/`
- `app/api/v1/chat.py` → 15-line stub to implement
- `app/services/redis_service.py` → `RedisService` ⚠️ Blocked until TASK-03

#### Outputs
- `app/agents/node_registry.py` — `NODE_REGISTRY: dict[str, Callable[[AgentState], dict]]` mapping `"rag_fn"`, `"ocr_fn"`, `"form_filler_fn"` to their worker function implementations. **`"procedure_planner_fn"` is NOT a valid `NODE_REGISTRY` key.** Also exports `NODE_DEPENDENCIES: dict[str, list[str]] = {"rag_fn": [], "ocr_fn": [], "form_filler_fn": ["ocr_fn"]}`. **This is the only file that imports all worker functions.**
- `app/agents/nodes/plan_executor.py` — `plan_executor_node(state) -> dict`: reads `NODE_DEPENDENCIES` from `node_registry.py`, groups the remaining plan into execution waves where all dependencies are satisfied, runs each wave with `asyncio.gather()`, merges all returned dicts into state, advances `plan_cursor` by the wave size, checks `MAX_PLAN_STEPS` circuit-breaker against the new cursor value. Conditional routing: if plan exhausted or circuit-breaker triggered → `"synthesizer_node"`, else → `"plan_executor_node"` (loop).
- `app/agents/graph.py` — `build_graph()` with topology:
  ```
  Entry → router_node → enrichment_node → plan_executor_node (loop) → synthesizer_node → END
  ```
  Compiled with `recursion_limit=10`; session load at entry, session save at exit
- `app/api/v1/chat.py` — functional `POST /api/v1/chat` with `StreamingResponse` (SSE); catches `GraphRecursionError` and returns HTTP 500 JSON (not traceback)
- `tests/integration/test_agent_graph.py` — end-to-end tests with mocked LLM and mocked `NODE_REGISTRY`

#### Definition of Done
- [ ] `POST /chat` with `{"message": "Tôi muốn đăng ký thường trú"}` returns SSE stream
- [ ] SSE events contain only `final_response` chunks, not raw state
- [ ] `plan_executor` correctly calls `rag_fn` for a `["rag_fn"]` plan
- [ ] `plan_executor` correctly calls `ocr_fn` then `form_filler_fn` in order for a `["ocr_fn", "form_filler_fn"]` plan
- [ ] Circuit-breaker fires and routes to Synthesizer when `plan_cursor >= MAX_PLAN_STEPS`
- [ ] A plan `["ocr_fn", "rag_fn", "form_filler_fn"]` results in `ocr_fn` and `rag_fn` being called concurrently in a single `asyncio.gather()`, verified by unit test that asserts gather was called with both
- [ ] `enrichment_node` is wired between `router_node` and `plan_executor_node` in the compiled graph
- [ ] `GraphRecursionError` returns HTTP 500 JSON (not a traceback)
- [ ] Full graph traversal integration test passes with mocked LLM and mocked `NODE_REGISTRY`
- [ ] `/review-api-route` checklist passes for `chat.py`

#### Notes / Constraints
- `node_registry.py` is the **only** file that imports all worker functions — `graph.py` imports only from `node_registry` and `nodes/router.py`, `nodes/enrichment.py`, `nodes/plan_executor.py`, `nodes/synthesizer.py`
- Valid `NODE_REGISTRY` keys: `"rag_fn"`, `"ocr_fn"`, `"form_filler_fn"`. `"procedure_planner_fn"` is NOT a valid key.
- Worker functions called via `asyncio.gather()` each receive a snapshot copy of state at the start of the wave — they must not mutate shared state in place. Each returns a dict; plan_executor merges all dicts after the wave completes.
- Worker functions in `NODE_REGISTRY` must never write to `execution_plan` or `plan_cursor`
- Session load at graph entry hydrates `conversation_history` from Redis — this is already the trimmed 6-turn window. No additional trimming needed inside the graph.
- Session load/save wraps every invocation (CLAUDE.md Rule 4 pattern)
---

---
### TASK-12: Document Upload + OCR API Endpoint
**Phase:** 4
**Priority:** High
**Estimated effort:** S (1 day)
**Depends on:** TASK-04 (OCR service), TASK-07 (Storage service), TASK-0D (upload validation)
**Can be parallelized with:** TASK-11, TASK-13

#### Goal
Implement functional document upload and OCR endpoints with full file validation as the first gate before any storage or processing occurs.

#### Inputs
- `app/api/v1/documents.py` → stub to implement
- `app/services/ocr_service.py` → `OCRService` ⚠️ Blocked until TASK-04
- `app/services/storage_service.py` → `StorageService` ⚠️ Blocked until TASK-07
- `app/core/file_validator.py` → `validate_upload()` ⚠️ Blocked until TASK-0D
- `app/schemas/personal_data.py` → `PersonalData` (response schema)

#### Outputs
- `app/api/v1/documents.py`:
  - `POST /api/v1/documents/upload` — calls `validate_upload()` first, then stores file in MinIO, returns MinIO path
  - `POST /api/v1/documents/ocr` — triggers OCR, returns `PersonalData` JSON
- `/review-api-route` checklist passes

#### Definition of Done
- [ ] Upload a JPEG → file appears in MinIO bucket `dichvucong`
- [ ] Invalid file type (e.g. `.exe`) returns HTTP 422 before touching MinIO
- [ ] File > 5 MB returns HTTP 422 before touching MinIO
- [ ] OCR endpoint returns `PersonalData` with at least `id_number` and `full_name` populated
- [ ] Endpoint does NOT store the image in PostgreSQL (MinIO path only)

#### Notes / Constraints
- Images go to MinIO only — never to PostgreSQL (CLAUDE.md rule)
---

---
### TASK-13: Synthetic CCCD Mock Image Generation
**Phase:** 4
**Priority:** High
**Estimated effort:** S (1 day)
**Depends on:** None (pure Pillow/qrcode, no services) — but should be started in parallel with TASK-05, not after it
**Can be parallelized with:** Any task

#### Goal
Generate a library of synthetic CCCD identity card images for testing the OCR pipeline and validating the prompt injection hardening from TASK-04.

#### Inputs
- `ingestion/generate_mock_data.py` → stub to implement

#### Outputs
- `ingestion/generate_mock_data.py` — script generating 10+ synthetic CCCD images using Pillow
- `backend/data/mock_documents/` — populated with generated images, including at least one image whose name field contains an injection-attempt string

#### Definition of Done
- [ ] Script generates 10+ synthetic CCCD images without error
- [ ] Images contain readable Vietnamese text (Pillow with Vietnamese font)
- [ ] Running OCR on generated images returns non-empty `PersonalData`
- [ ] At least one image contains an injection-attempt string in a text field to validate TASK-04 hardening
- [ ] At least 3 images include a **QR code** encoding the CCCD data in `id_number||full_name|dob|gender|address|issue_date` format (index 1 always empty) to test `OCRService.decode_qr()` success path
- [ ] At least 3 images have **no QR code** to test the PaddleOCR fallback path

#### Notes / Constraints
- Use fake names and IDs — never use real citizen data
- CCCD QR format: `id_number||full_name|DDMMYYYY|gender|address|DDMMYYYY` (index 1 always empty string; gender is "Nam" or "Nu")
- Province code in first 3 digits of id_number must be 1–96 to pass `_validate_id_number()` check in `ocr_service.py`
- Generate QR codes using the `qrcode` Python library; embed in the image using Pillow
---

---
### TASK-14: End-to-End Integration Tests
**Phase:** 4
**Priority:** High
**Estimated effort:** M (2 days)
**Depends on:** TASK-11 (full graph), TASK-12 (OCR endpoint), TASK-05 (Qdrant populated)
**Can be parallelized with:** None (requires all above)

#### Goal
Write the full integration test suite verifying the complete citizen journey from question to filled form under the new `plan_executor` topology.

#### Inputs
- `tests/integration/test_rag_pipeline.py` → stub to implement
- `tests/integration/test_agent_graph.py` → stub to implement

#### Outputs
- `tests/integration/test_rag_pipeline.py` — ingest 1 legal PDF → search → verify citation metadata present; verify `status = "active"` filter applied; verify `verify_citations()` runs
- `tests/integration/test_agent_graph.py`:
  - `POST /chat` end-to-end with mocked LLM → verify SSE stream
  - Test `["rag_fn"]` single-step plan executes correctly
  - Test `["ocr_fn", "form_filler_fn"]` two-step plan executes in correct order
  - Test circuit-breaker: a 9-step plan triggers `MAX_PLAN_STEPS` and routes to Synthesizer

#### Definition of Done
- [ ] `test_rag_pipeline.py` passes against live Qdrant (populated from TASK-05)
- [ ] `test_agent_graph.py` passes with mocked Anthropic client
- [ ] Multi-step plan integration test verifies worker functions execute in declared order
- [ ] Circuit-breaker integration test verifies error surfaces in `final_response`
- [ ] No real API calls in integration tests (mock at service boundary)
---

---
### TASK-15: PDF Form Templates Collection + MinIO Upload
**Phase:** 3
**Priority:** Medium
**Estimated effort:** S (1 day)
**Depends on:** TASK-07 (StorageService)
**Can be parallelized with:** TASK-08, TASK-09

#### Goal
Obtain or create blank PDF form templates for the 3 residence procedures and seed them into MinIO and the `form_templates` PostgreSQL table.

#### Inputs
- `app/services/storage_service.py` → `StorageService` ⚠️ Blocked until TASK-07
- `form_templates` PostgreSQL table (already created in migration 0001)
- Architecture blueprint §10 — `form_templates.fields` JSONB structure

#### Outputs
- `backend/data/form_templates/` — 3 PDF files (one per procedure)
- `ingestion/seed_form_templates.py` (new) — uploads PDFs to MinIO `dichvucong/form_templates/` prefix, inserts rows into `form_templates`
- MinIO `dichvucong/form_templates/` prefix populated

#### Definition of Done
- [ ] 3 PDF templates exist in MinIO
- [ ] `form_templates` table has 3 rows with `pdf_template_path` and `fields` JSONB populated
- [ ] `PDFService.fill()` can load a template from MinIO and fill it

#### Notes / Constraints
- Prefer AcroForm PDFs where possible (simpler fill path)
- If real government forms unavailable, create mock PDFs with reportlab with realistic Vietnamese field names
---

## 3. Dependency Graph

```
TASK-0A (get_db + security baseline) ──┐
                                        ├─► TASK-03 (Redis — needs auth)
TASK-0B (ORM models + DAG edges) ──────┤
                                        └─► TASK-09 (enrichment_node — needs real edges)

TASK-0C (rate limiting) — depends on TASK-03; can develop in parallel with rest
TASK-0D (file validation) — no deps, develop immediately
TASK-0E (status field) — no deps, develop immediately

TASK-01 (LLM Service + Router + LangSmith)
  ├─► TASK-04 (OCR worker)
  │     └─► TASK-08 (Form Filler worker)
  ├─► TASK-06 (RAG worker) ◄── TASK-02 (Qdrant + Embedder)
  └─► TASK-09 (Procedure Planner worker)

TASK-02 ✅ (Embedder + Qdrant)
  └─► TASK-05 (Legal Ingestion)
        └─► TASK-06 (RAG worker — needs data)

TASK-03 (Redis) ──────────────────────────────────────────────────►┐
TASK-07 (PDF + Storage) ──► TASK-08 (Form Filler worker)           │
                        └─► TASK-15 (Templates)                    │
                                                                    │
TASK-01 + TASK-06 + TASK-08 + TASK-09 + TASK-10 + TASK-0A + TASK-0B + TASK-0F
  └─► TASK-11 (Graph Assembly + plan_executor + NODE_REGISTRY + Chat) ◄─┘

TASK-11 + TASK-04 + TASK-07 + TASK-0D
  └─► TASK-12 (Document Upload + OCR Endpoint)

TASK-13 (Mock Images) ─── independent

TASK-11 + TASK-12 + TASK-05
  └─► TASK-14 (Integration Tests)
```

Parallelizable from day 1 (no dependencies):
- **TASK-0A, TASK-0B, TASK-0D, TASK-0E, TASK-13** can all start simultaneously

---

## 4. Recommended Next Actions

~~**1. TASK-0A + TASK-0B — do today, in parallel**~~ ✅ Complete (2026-03-19)

~~**2. Collect Vietnamese legal PDFs**~~ ✅ Complete (2026-03-26) — 4 documents downloaded. ⚠️ Convert `.doc` → PDF before ingestion: `libreoffice --headless --convert-to pdf backend/data/legal_documents/*.doc`

~~**3. Update `.claude/agents/router-agent.md` before TASK-01 starts**~~ ✅ Complete (2026-03-26)

~~**4. Define `NODE_REGISTRY` key vocabulary as a constant**~~ ✅ Complete (2026-03-26) — `VALID_PLAN_STEPS` in `app/agents/node_registry.py`

~~**5. TASK-01 — LLM Service + Router Node + LangSmith**~~ ✅ Complete (2026-03-26) — 31 unit tests passing

~~**1. Convert `.doc` source documents to PDF**~~ ✅ Complete (2026-03-26)

~~**2. TASK-02 + TASK-03 + TASK-07 + TASK-13 — start simultaneously (Group A)**~~ ✅ TASK-02 complete (2026-03-26) | ✅ TASK-03 complete (2026-03-26) | ✅ TASK-07 complete (2026-03-26) | TASK-13 pending
- ~~`TASK-02`~~ ✅ Embedder + Qdrant service
- ~~`TASK-03`~~ ✅ Redis service (1-hour TTL, Fernet encryption, 6-turn history trim)
- ~~`TASK-07`~~ ✅ PDF service + MinIO storage service
- `TASK-13` Mock CCCD image generation (synthetic test data) — **remaining Group A task**

~~**3. TASK-04 — OCR Service + ocr_fn Worker**~~ ✅ Complete (2026-03-27) — 15 unit tests passing

**4. TASK-05 + TASK-06 + TASK-09 + TASK-13 — current Group B tasks**
TASK-04 done. The following can start simultaneously:
- ~~`TASK-04`~~ ✅ OCR service (two-path: QR decode + PaddleOCR fallback, prompt-injection hardened)
- `TASK-05` Legal doc ingestion (requires TASK-02 ✅ + converted PDFs ✅ — run `libreoffice --headless --convert-to pdf`)
- `TASK-06` RAG worker function (requires TASK-01 ✅ + TASK-02 ✅ + TASK-05)
- `TASK-09` enrichment_node + procedure_planner_fn (can start now — no TASK-05/06 dependency)
- `TASK-13` Mock CCCD image generation — ⚠️ **start this in parallel with TASK-05, not after**. The OCR pipeline (TASK-04) is fully implemented but has no realistic test images beyond `minimal_cccd.jpg`. The injection-hardening in the extraction prompt is unvalidated without a synthetic image that contains an injection-attempt string. Must generate both QR-encoded and non-QR images.

**4. TASK-08 + TASK-09 + TASK-10 — start after Group B (Group C)**
- `TASK-09` enrichment_node + procedure_planner_fn (pre-flight, no LLM call)
- `TASK-08` form_filler_fn worker
- `TASK-10` Synthesizer node (windowed history — never construct full session history inside node)
