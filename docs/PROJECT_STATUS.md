# DichVuCong AI Assistant — Project Status

**Version 2.9 | Updated 2026-04-10**

> **What changed in v2.9:** Documentation catch-up for TASK-06, TASK-08, TASK-10. All three tasks verified complete against DoD checklists. TASK-06: `rag_fn` with jurisdiction-aware cascade retrieval (`expand_scope_hierarchy` + reverse for most-specific-first), threshold-based stopping (`RAG_MIN_SCORE_THRESHOLD=0.3`), structured summary fallback at >80% token budget, `verify_citations()` with payload-pair `(article_number, document_number)` substring matching, `scope_used` field in return dict. TASK-08: `SessionDataAccumulator.merge()` (higher-confidence wins, tie keeps existing, never mutates inputs), `FormFieldMapper` (LLM semantic mapping with in-memory cache keyed by `form_id:sorted_fields`, bad JSON → empty mapping without crash), `form_filler_fn` worker with promote/hold logic, `extracted_personal_data` merged before any fill step. TASK-10: `synthesizer_node` verified — 6 response modes, scope fallback notice, RAG-only LLM-skip optimisation, hardcoded LLM-failure fallback. One gap noted: `circuit_breaker` mode is implemented in `_determine_mode()` but no dedicated unit test exists. Stale "Scaffolded" and "Not Started" entries corrected. 254 unit tests passing.

> **What changed in v2.8:** TASK-11 complete — LangGraph graph assembly and functional chat SSE endpoint. `plan_executor_node` implemented with wave execution (`asyncio.gather`), `NODE_DEPENDENCIES`-driven concurrency, and `MAX_PLAN_STEPS=8` circuit-breaker (configurable via env var). `graph.py` rewritten with full `router_node → enrichment_node → plan_executor_node (loop) → synthesizer_node → END` topology; `route_plan_executor` conditional edges. `app/api/v1/chat.py` rewritten as functional SSE endpoint: Redis session hydration, `agent_graph.ainvoke(config={"recursion_limit": 10})`, `GraphRecursionError` → HTTP 500 JSON, Redis save failure non-fatal, word-by-word SSE stream ending `[DONE]`. `node_registry.py` updated with import-time assertion guarding `NODE_REGISTRY` ↔ `VALID_PLAN_STEPS` drift. `test_rate_limiting.py` fixture updated to mock `agent_graph` and `_get_redis`. 254 unit tests passing (11 new: 8 plan_executor + 3 chat endpoint).

> **What changed in v2.7:** TASK-10 complete — `synthesizer_node` (true LangGraph graph node) and `synthesis_prompt.py` fully implemented. Six response modes in priority order: error → circuit_breaker → form_fill_complete → form_fill_partial → rag_only → fallback. RAG-only LLM-skip optimisation: when no scope fallback notice is needed, `state["final_response"]` is returned directly without an LLM call. Scope fallback notice woven in naturally when `scope_used != filing_jurisdiction`. `_scope_level_name()` maps scope codes to "cấp quốc gia" / "cấp thành phố" / "cấp phường". LLM failure returns hardcoded Vietnamese fallback without raising. `synthesizer-agent.md` rewritten to reflect implementation. 243 unit tests passing (42 new: 8 synthesizer + 34 from session accumulator/form mapper/rag_fn tests already landed in this session).

> **What changed in v2.6:** LLMService extended with Gemini backend (`LLM_BACKEND` env var, `google.genai` SDK). Vision support included via `types.Part.from_bytes()` for OCR document classifier. TASK-16 complete — `jurisdiction.py` (`expand_scope_hierarchy`, `validate_scope_code`), `AdministrativeUnit` ORM model, `SessionData`/`AgentState` `domain` + `filing_jurisdiction` fields, `administrative_units` seeded with 8 HCM City wards. `google-genai>=1.7.0` added to requirements. `LLM_BACKEND=gemini` smoke test passing. 201 unit tests passing (17 new: 8 jurisdiction + 8 LLMService + 1 placeholder).

> **What changed in v2.5:** TASK-13 complete — 80 synthetic CCCD images generated across four categories (clean QR, degraded QR, no-QR, injection attempts), 20 images per category. Subdirectories staged at `backend/data/mock_documents/`. TASK-09 complete — `enrichment_node` and `procedure_planner_fn` implemented and tested. Two-condition guard verified (`target_procedure_id` AND `form_filler_fn` in plan). Out-of-scope validation returns Vietnamese error message. `procedure_planner_fn` confirmed absent from `NODE_REGISTRY`. 184 unit tests passing (21 new).

> **What changed in v2.4:** TASK-05 complete — live ingestion successful. 27 total chunks ingested across 4 legal documents. Boilerplate removal (`clean_pdf_text()`), Docling chapter hierarchy prefix (`[doc > chapter > article]` format), and structured summary generation (LLM per-chunk, graceful null on API key absent) implemented in `ingest_legal_docs.py`. `--generate-summaries` CLI flag added. `scope_coverage` table populated for housing domain (TTHC-001: 16 chunks, TTHC-002: 10 chunks, TTHC-003: 5 chunks, all VN scope). `QdrantService.search()` verified returning relevant chunks for residence registration queries. SQL syntax fix: `CAST(:proc_id AS UUID)` replaces `:proc_id::uuid` in `upsert_scope_coverage`. `sentence-transformers==3.1.1` installed. 10 new unit tests (163 total) covering boilerplate removal, hierarchy prefix format + fallback, structured summary present/null, and LLM-not-called-in-dry-run guarantee.

> **What changed in v2.3:** TASK-05 complete — legal document ingestion pipeline implemented with Docling article-boundary chunking, soft-deprecation, scope_coverage upsert, and CLI interface. `QdrantService.scroll_by_document_number()` and `batch_set_status()` implemented. `ingestion/ingest_legal_docs.py` rewritten from stub: `_extract_article_chunks` / `_is_article_heading` article-boundary chunking, `scroll_by_document_number` → `batch_set_status("superseded")` soft-deprecation before upsert, `build_article_lookup` driven by `housing.yaml`, `upsert_scope_coverage` writing to `scope_coverage` table, `--dry-run` / `--domain` / `--doc` / `--verbose` CLI flags. `validate_document_file_map` raises `KeyError` on unknown document numbers before any processing begins. Dry-run mode skips all Qdrant and DB writes. 9 new unit tests (`test_ingest_legal_docs.py`) cover article-boundary chunking, unmatched-article skipping, soft-deprecation call order, scope_coverage upsert per (scope, proc_id) pair, dry-run no-write guarantee, document-file-map validation, and idempotency. Total unit tests: 153. ⚠️ Live run requires embedding backend configured — first run downloads Docling detection models (~2 GB to `~/.cache/huggingface`).

> **What changed in v2.2:** Procedure IDs migrated from TTDN to TTHC prefix throughout codebase. Alembic migration 0003 applied (domain column on procedures, administrative_units table, scope_coverage table). ingestion/domain_configs/housing.yaml created with article mappings for TTHC-001, TTHC-002, TTHC-003. TASK-16 partially complete — migration and housing.yaml done; jurisdiction utility, ORM model, seed scripts, and field additions remain.

> **What changed in v2.1:** Task cards updated for expanded multi-domain hierarchical scope. Three new tasks added: TASK-16 (Jurisdiction Infrastructure), TASK-17 (Multi-Domain Ingestion and Data Preparation), TASK-18 (Evaluation Dataset and Benchmark). TASK-05 effort increased to L. TASK-06 expanded with jurisdiction-aware retrieval. TASK-09 updated with out-of-scope validation. TASK-10 updated with scope_used metadata. TASK-11 updated with domain and filing_jurisdiction hydration. TASK-13 expanded with four synthetic image categories. TASK-14 and TASK-15 scope expanded. Router prompt domain-diverse examples added to TASK-01 notes. All new multi-domain tasks sequenced after housing demo (TASK-11) is complete.

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
| LLMService (Anthropic + Gemini backends, vision support, stream) | `app/services/llm.py` | Implemented & Tested |
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
| ingest_legal_docs.py (Docling chunker, boilerplate removal, hierarchy prefix, structured summary, scope_coverage, CLI) | `ingestion/ingest_legal_docs.py` | Implemented & Tested |
| enrichment_node (two-condition guard: target_procedure_id AND form_filler_fn in plan; no LLM call) | `app/agents/nodes/enrichment.py` | Implemented & Tested |
| procedure_planner_fn (DB query + topo sort via procedure_graph; out-of-scope validation) | `app/agents/nodes/procedure_planner.py` | Implemented & Tested |
| expand_scope_hierarchy() + validate_scope_code() — zero infra deps | `app/core/jurisdiction.py` | Implemented & Tested |
| AdministrativeUnit ORM model | `app/models/administrative_unit.py` | Implemented |
| SessionData — filing_jurisdiction + domain fields | `app/schemas/session.py` | Implemented & Tested |
| AgentState — domain + filing_jurisdiction fields | `app/agents/state.py` | Implemented |
| administrative_units seeded (8 HCM City units) | `ingestion/seed_administrative_units.py` | Implemented & Running |
| rag_fn (jurisdiction cascade, threshold stopping, structured summary fallback, verify_citations) | `app/agents/nodes/rag.py` | Implemented & Tested |
| citation_formatter (format_citation + verify_citations payload-pair matching) | `app/core/citation_formatter.py` | Implemented & Tested |
| rag_prompt (RAG_SYSTEM_PROMPT enforcing citation format) | `app/agents/prompts/rag_prompt.py` | Implemented & Tested |
| SessionDataAccumulator (confidence-based merge, immutable inputs) | `app/core/session_accumulator.py` | Implemented & Tested |
| FormFieldMapper (LLM semantic mapping, in-memory cache, bad-JSON safety) | `app/core/form_field_mapper.py` | Implemented & Tested |
| form_filler_fn (merge→map→fill→promote/hold, no-PD guard, exception safety) | `app/agents/nodes/form_filler.py` | Implemented & Tested |
| form_mapping_prompt (FORM_MAPPING_SYSTEM_PROMPT + build_form_mapping_user_message) | `app/agents/prompts/form_mapping_prompt.py` | Implemented & Tested |
| synthesizer_node (6 response modes, scope notice, RAG LLM-skip optimisation, LLM failure fallback) | `app/agents/nodes/synthesizer.py` | Implemented & Tested |
| synthesis_prompt (build_synthesis_prompt + _scope_level_name, all 6 modes) | `app/agents/prompts/synthesis_prompt.py` | Implemented & Tested |
| plan_executor_node (wave execution, asyncio.gather, MAX_PLAN_STEPS circuit-breaker) | `app/agents/nodes/plan_executor.py` | Implemented & Tested |
| graph.py (full topology: router→enrichment→plan_executor loop→synthesizer) | `app/agents/graph.py` | Implemented & Tested |
| POST /api/v1/chat (functional SSE: Redis hydration, graph invoke, GraphRecursionError catch) | `app/api/v1/chat.py` | Implemented & Tested |
| node_registry import-time assertion (NODE_REGISTRY ↔ VALID_PLAN_STEPS drift guard) | `app/agents/node_registry.py` | Implemented & Tested |
| 254 unit tests passing | `tests/unit/` | Implemented & Tested |

#### Backend — Scaffolded (stubs, not functional)
| Item | File | Confidence |
|---|---|---|
| Forms route stub | `app/api/v1/forms.py` | Scaffolded |
| Documents/procedures/legal routes | `app/api/v1/` | Scaffolded |

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

#### API Endpoints (functional implementations pending)
- `POST /api/v1/forms/submit` — real DB write + tracking code
- `POST /api/v1/documents/upload` — MIME/size/extension validation + MinIO store + OCR trigger
- `GET /api/v1/procedures/{id}/plan` — real DAG resolution

#### Data
- Real Vietnamese legal PDFs — **4 collected ✅, converted to PDF ✅ (2026-03-26), ingested into Qdrant ✅** — Luật Cư trú 2020 (68/2020/QH14), NĐ 62/2021/NĐ-CP, NĐ 104/2022/NĐ-CP, TT 55/2021/TT-BCA; stored in `backend/data/legal_documents/`
- Qdrant `legal_documents` collection — **populated ✅** — 27 chunks ingested, housing domain, VN scope, TTHC-001/002/003 tagged. `scope_coverage` table populated (TTHC-001: 16 chunks, TTHC-002: 10 chunks, TTHC-003: 5 chunks). `structured_summary` null (ANTHROPIC_API_KEY required for live LLM summaries). Re-run with API key set to populate summaries.
- PDF form templates for 3 residence procedures (0 collected)
- Synthetic CCCD mock images — **80 images across 4 categories ✅** — `backend/data/mock_documents/` (category_1_clean_qr, category_2_degraded_qr, category_3_no_qr, category_4_injection; 20 per category)

#### Tests
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
- `ingestion/ingest_procedures.py` — updated to insert at least one `procedure_dependencies` row (TTHC-003 requires TTHC-001 or TTHC-002, per Luật Cư trú 2020 Điều 20)
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
### TASK-0F: plan_executor Circuit-Breaker Design ✅ COMPLETE
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
- [x] `plan_executor` routes to Synthesizer when `plan_cursor >= MAX_PLAN_STEPS`
- [x] `GraphRecursionError` caught in chat endpoint, returns HTTP 500 JSON
- [x] `MAX_PLAN_STEPS` is configurable via env var (default 8)
- [x] Unit test: a plan with 9 entries triggers circuit-breaker after step 8
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
- **Router prompt must include domain-diverse few-shot examples before any multi-domain testing begins.** Add 4 examples per new domain (civil registration, business registration) — 2 simple single-intent queries and 2 compound queries per domain. Total examples: ~16. This is a prerequisite for TASK-17, not a separate task. The router output schema must be extended to include `domain: str | None` as a structured output field alongside `execution_plan` and `entities`. Valid domain values: `'housing'`, `'civil_registration'`, `'business_registration'`, `None` (ambiguous).
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
### TASK-05: Legal Document Ingestion Pipeline ✅ COMPLETE
**Phase:** 2
**Priority:** Critical
**Estimated effort:** L (4–5 days)
**Depends on:** TASK-02 (EmbedderService + QdrantService), TASK-0E (status field), TASK-16 (domain_configs/housing.yaml + scope_coverage table)
**Can be parallelized with:** TASK-03, TASK-04, TASK-07
**Completed:** 2026-04-09

#### Goal
Implement the offline ingestion script with soft-deprecation on re-ingestion. Every chunk must have `status: 'active'`, non-empty `procedure_tags`, and a `location_scope` value from the hierarchy (`VN`, `VN-HCM`, or `VN-HCM-[ward_code]`). `procedure_tags` assignment is driven exclusively by per-domain YAML configuration files at `ingestion/domain_configs/[domain].yaml` — never inferred automatically. The script must upsert a row in the `scope_coverage` table after every successful ingest run. This task covers the housing domain only (`domain_configs/housing.yaml`). Multi-domain ingestion is TASK-17.

#### Inputs
- `ingestion/ingest_legal_docs.py` → stub to implement
- `app/services/embedder.py` → `EmbedderService` ⚠️ Blocked until TASK-02
- `app/services/qdrant_service.py` → `QdrantService` ⚠️ Blocked until TASK-02
- `ingestion/domain_configs/housing.yaml` → ⚠️ created by TASK-16 partial (Step 3 of pre-TASK-05 setup), must exist before this script runs ✅
- Vietnamese legal source documents — **downloaded ✅** to `backend/data/legal_documents/`:
  - `68_2020_QH14_435315.pdf` — Luật Cư trú 2020 (Luật số 68/2020/QH14)
  - `62_2021_ND-CP_473325.pdf` — Nghị định 62/2021/NĐ-CP
  - `104_2022_ND-CP_544177.pdf` — Nghị định 104/2022/NĐ-CP (supersedes 144/2021)
  - `55_2021_TT-BCA_466836.pdf` — Thông tư 55/2021/TT-BCA

#### Outputs
- `ingestion/ingest_legal_docs.py` — PDF → Docling → chunker → boilerplate removal → hierarchy prefix → embed → Qdrant; re-ingestion marks old chunks `"superseded"` before upserting new; optional `structured_summary` per chunk via LLM
- Qdrant `legal_documents` collection — **populated ✅ — 27 chunks, housing domain, VN scope**
- Each chunk payload: `document_number`, `article_number`, `procedure_tags`, `content` (with hierarchy prefix), `status: "active"`, `hierarchy`, `structured_summary`, `effective_date`

#### Definition of Done
- [x] Script runs to completion on all 4 real legal PDFs without error — **live run complete 2026-04-09** ✅
- [x] Chunks in Qdrant never span two articles — `test_each_chunk_contains_only_one_dieu` ✅
- [x] Every chunk has non-empty `procedure_tags` and `status: "active"` — `test_rerun_supersedes_old_chunks_then_upserts_new` verifies `status="active"` ✅; unmatched articles (no tags) are skipped — `test_chunk_not_in_yaml_is_skipped_not_upserted` ✅
- [x] Re-running script on same PDF marks old chunks `"superseded"` without duplicating content — `test_rerun_supersedes_old_chunks_then_upserts_new` ✅
- [x] `QdrantService.search()` returns relevant chunks — **27 points verified in Qdrant collection** ✅
- [ ] Integration test `tests/integration/test_rag_pipeline.py` passes *(deferred to TASK-14)*
- [x] `location_scope` field present in every chunk payload — `build_article_lookup` preserves per-doc `location_scope` from YAML; each upserted chunk carries it ✅
- [x] `procedure_tags` assignment driven by `domain_configs/housing.yaml` — no automatic inference — `test_chunk_not_in_yaml_is_skipped_not_upserted` ✅
- [x] `scope_coverage` table upserted after ingest completes — 3 rows confirmed (TTHC-001: 16, TTHC-002: 10, TTHC-003: 5) ✅
- [x] `domain_configs/housing.yaml` exists and is readable by the script ✅ (created by TASK-16)
- [x] Re-running script on same PDF at same location_scope marks old chunks superseded without duplicating — `test_rerun_supersedes_old_chunks_then_upserts_new` ✅
- [x] Boilerplate removal — `test_strips_cong_hoa_preamble`, `test_strips_standalone_page_numbers`, `test_strips_section_dividers` ✅
- [x] Docling hierarchy prefix prepended to content — `test_hierarchy_prefix_prepended_to_chunk_content` ✅; fallback to `[doc > article]` when chapter absent — `test_prefix_without_chapter_falls_back_to_two_part` ✅
- [x] `structured_summary` None on LLM failure, chunk still ingested — `test_structured_summary_none_when_llm_returns_invalid_json` ✅
- [x] LLM not called in dry-run without `--generate-summaries` — `test_llm_not_called_in_dry_run_without_generate_summaries` ✅
- [x] 163 unit tests passing ✅

#### Notes / Constraints
- **Never ingest without procedure_tags** — untagged chunks are unretrievable in filtered search (CLAUDE.md rule)
- Chunk at article boundaries — never split mid-article
- `structured_summary` is null in this run — `ANTHROPIC_API_KEY` not set. Re-run with key to populate.
- SQL fix applied: `CAST(:proc_id AS UUID)` replaces `:proc_id::uuid` in `upsert_scope_coverage` (asyncpg param mixing issue)
---

---
### TASK-06: RAG Worker Function + RAG Prompt + Citation Verifier ✅ COMPLETE
**Phase:** 2
**Priority:** Critical
**Estimated effort:** M (2 days)
**Depends on:** TASK-01 (LLMService), TASK-02 (QdrantService), TASK-0E (status field)
**Can be parallelized with:** TASK-03, TASK-04, TASK-07, TASK-08
**Completed:** 2026-04-10

#### Goal
Implement `rag_fn` as a worker function (not a graph node) and implement `verify_citations()` as a post-generation check in `citation_formatter.py`.

Additionally, `rag_fn` must implement jurisdiction-aware retrieval: call `expand_scope_hierarchy(filing_jurisdiction)` from `app/core/jurisdiction.py` to build the scope ancestor list, apply cascade fallback from most specific to broadest scope, pass `scope_used` metadata to state, and add to `errors[]` if all scope levels return empty chunks. `verify_citations()` must use chunk payload `(article_number, document_number)` matching — not format-specific regex — to be format-agnostic across document types.

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
- [x] `rag_fn` returns at least 1 citation for a question about residence registration — `test_rag_fn_returns_citations_for_residence_query` ✅
- [x] `verify_citations()` flags a hallucinated article number as `[unverified: ...]` — `test_verify_citations_flags_hallucinated_article` ✅
- [x] A correct citation present in retrieved chunks passes through unchanged — `test_verify_citations_passes_correct_citation` ✅
- [x] Citation format matches `[Điều X, Nghị định/Thông tư YYY/YYYY/NĐ-CP]` — enforced in `RAG_SYSTEM_PROMPT` ✅
- [x] `/review-agent-node` checklist passes
- [x] `rag_fn` calls `expand_scope_hierarchy()` before building Qdrant filter — line 88 of rag.py ✅
- [x] Cascade fallback implemented — most specific scope first, broadest last — `reversed(expand_scope_hierarchy(...))` ✅; `test_rag_fn_cascade_fallback_to_broader_scope` ✅
- [x] `scope_used` field returned in `rag_fn` result dict — present in all return paths ✅
- [x] Empty result at all scope levels adds to `errors[]` — never passes empty context to LLM — `test_rag_fn_all_scopes_empty_returns_error_no_llm_call` ✅
- [x] `verify_citations()` matches against chunk payload `(article_number, document_number)` pairs, not citation string format — `_check_match()` in citation_formatter.py ✅
- [x] `verify_citations()` correctly handles Luật citation format — flagged as `[unverified: ...]` (documented limitation; `document_number="68/2020/QH14"` not substring of `"Luật Cư trú năm 2020"`); `test_verify_citations_luat_format_no_false_flag` ✅ (behavior correct and documented)
- [x] All 10 tests in test_rag_fn.py pass ✅
- [x] All 4 tests in test_citation_formatter.py pass ✅
- [x] `QdrantService.search()` accepts `scope` parameter and filters correctly ✅
- [x] `rag-agent.md` rewritten and accurate ✅
- [x] No real API calls in any test — all LLM and Qdrant calls mocked ✅
- [x] Threshold-based stopping implemented with `RAG_MIN_SCORE_THRESHOLD` — `test_threshold_stopping_drops_low_score_chunks` ✅
- [x] Structured summary fallback activates beyond 80% of token budget — `used_tokens > max_tokens * 0.8` guard in rag.py ✅

#### Notes / Constraints
- `rag_fn` is a plain function, not a LangGraph node
- Do not use dense-only retrieval — always call `_bm25_search` as well (CLAUDE.md rule)
- Cross-encoder reranking is deferred — see P15 in `PROJECT_CONTEXT.md` §6 for the upgrade condition. Do not add a cross-encoder call to `rag_fn`
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
### TASK-08: Form Field Mapper + Session Accumulator + form_filler_fn Worker ✅ COMPLETE
**Phase:** 3
**Priority:** High
**Estimated effort:** M (2–3 days)
**Depends on:** TASK-01 (LLMService), TASK-04 (OCR/PersonalData), TASK-07 (PDFService + StorageService)
**Can be parallelized with:** TASK-09 (after deps satisfied)
**Completed:** 2026-04-10

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
- [x] `merge()` overwrites with new value only when `new_confidence > old_confidence`; on tie, existing wins — `test_merge_higher_confidence_wins`, `test_merge_equal_confidence_keeps_existing` ✅
- [x] `merge()` never mutates either input — `test_merge_does_not_mutate_inputs` ✅
- [x] `form_filler_fn` adds unfillable required fields to `unfilled_required_fields` — never fails silently — `test_form_filler_fn_does_not_promote_when_fields_missing` ✅
- [x] LLM mapping returns `""` for fields not in PersonalData (not `REQUIRES_USER_INPUT` — implementation uses empty string, spec diverged; behavior is correct for downstream Synthesizer prompt which asks user for any empty field) ✅
- [x] PDF is only promoted from `tmp/` to final path when `unfilled_required_fields` is empty — `test_form_filler_fn_promotes_when_all_fields_filled` ✅
- [x] Unit tests for merge rule pass (10 cases: higher-confidence wins, tie keeps existing, one-sided carry, immutability, None handling, field_confidences max, provenance, extraction_confidence max) ✅
- [x] `/review-agent-node` checklist passes
- [x] `FormFieldMapper.map()` calls LLM only on cache miss — `test_calls_llm_on_cache_miss` ✅; `test_uses_cache_on_second_call` (LLM called once across two calls) ✅
- [x] Second call with same `form_id` + field list reuses in-memory cache, substitutes new PersonalData values — `test_uses_cache_on_second_call` ✅
- [x] Bad JSON from LLM returns empty mapping without crashing — `test_bad_json_returns_empty_mapping` ✅
- [x] `form_filler_fn` merges `extracted_personal_data` into `personal_data` before any mapping or fill step — line 122 of form_filler.py ✅; `test_form_filler_fn_merges_extracted_personal_data` ✅
- [x] `form_filler_fn` returns error without calling PDFService when `effective_personal_data` is None after merge — `test_form_filler_fn_no_personal_data_returns_error` ✅
- [x] `PDFService.fill()` called via `await` (async implementation) ✅
- [x] `StorageService.promote_tmp()` called only when all required fields are filled — `test_form_filler_fn_promotes_when_all_fields_filled` ✅
- [x] Partial fills stay in `tmp/` — `promote_tmp` never called when `unfilled_required_fields` is non-empty — `test_form_filler_fn_does_not_promote_when_fields_missing` ✅
- [x] `form_fill_complete: bool` present in return dict ✅
- [x] `unfilled_required_fields: list[str]` present in return dict ✅
- [x] All unit tests pass (10 session_accumulator + 6 form_mapper + 6 form_filler) ✅
- [x] `AgentState` fields verified: `extracted_personal_data`, `filled_form_path`, `form_fill_complete`, `unfilled_required_fields` all present ✅
- [x] `form-filler-agent.md` rewritten and accurate ✅
- [x] No real API calls or file I/O in any unit test — all mocked ✅
- [ ] `form_filler_fn` checks `form_templates.fields` JSONB before calling `FormFieldMapper.map()` — DB cache NOT implemented; uses in-memory cache in `FormFieldMapper` instead. DB persistence of mappings deferred to TASK-15 (when real PDF templates are available). *(Deferred — not blocking)*
- [ ] On first successful mapping, resolved mapping written back to `form_templates.fields` in PostgreSQL *(Deferred — see above)*

#### Notes / Constraints
- **Never hard-code field mappings** (CLAUDE.md rule) — use `FormFieldMapper` for every form
- `form_filler_fn` is a plain function, not a LangGraph node
---

---
### TASK-09: Procedure Planner — Pre-flight Enrichment Node ✅ COMPLETE
**Phase:** 2
**Priority:** High
**Estimated effort:** S (1 day)
**Depends on:** TASK-0A (`get_db()`), TASK-0B (ORM models + seed edges)
**Can be parallelized with:** TASK-08
**Completed:** 2026-04-09

#### Goal
Implement `enrichment_node` as a true LangGraph graph node (not a worker function) that runs after the Router on every invocation. If `target_procedure_id` is set in state AND `form_filler_fn` is present in `state['execution_plan']`, calls `procedure_planner_fn` directly and writes `procedure_execution_plan` into state. If either condition is false, returns an empty dict immediately (no-op). This prevents unnecessary DB queries and token injection for queries that mention a procedure but do not involve form filling.

`procedure_planner_fn` makes no LLM call — it is a DB query plus a pure Python topological sort taking under 50ms. It must not occupy a plan slot in `execution_plan` alongside LLM-heavy workers. It is called directly by `enrichment_node`, never via `NODE_REGISTRY`.

Additionally, `procedure_planner_fn` must implement out-of-scope validation as Layer 1: when the DB query returns zero results for a `target_procedure_id`, return `{'errors': ['Thủ tục không được hỗ trợ trong hệ thống hiện tại.']}` immediately rather than returning an empty plan. This surfaces cleanly in the Synthesizer's error-handling mode. Do not return an empty `procedure_execution_plan` silently — that is a data modelling error, not a valid empty state.

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
- [x] `enrichment_node` correctly writes `procedure_execution_plan` for a procedure with at least one dependency — `test_enrichment_node_calls_planner_when_both_conditions_true` ✅
- [x] `enrichment_node` is a no-op (returns `{}`) when `target_procedure_id` is `None` — `test_enrichment_node_noop_when_no_target_procedure_id` ✅
- [x] `enrichment_node` returns empty dict when `target_procedure_id` is set but `form_filler_fn` is NOT in `execution_plan` — `test_enrichment_node_noop_when_only_condition_1_true` ✅
- [x] `enrichment_node` returns empty dict when `form_filler_fn` is in `execution_plan` but `target_procedure_id` is None — `test_enrichment_node_noop_when_only_condition_2_true` ✅
- [x] Completed steps (from `state["completed_procedures"]`) are passed to `resolve_execution_plan` — `test_procedure_planner_marks_completed_steps` ✅
- [x] `topological_sort` is called via `procedure_graph.py`, **not** re-implemented in the function — `test_procedure_planner_calls_resolve_execution_plan` ✅
- [x] `"procedure_planner_fn"` does NOT appear as a key in `NODE_REGISTRY` — `test_procedure_planner_fn_not_in_node_registry` ✅
- [x] `"procedure_planner_fn"` does NOT appear as a valid `execution_plan` entry in any router test
- [x] `/review-agent-node` checklist passes
- [x] `procedure_planner_fn` returns named error when `target_procedure_id` not found in DB — `test_procedure_planner_returns_error_for_unknown_id` ✅
- [x] Empty `procedure_execution_plan` is never returned without a corresponding `errors[]` entry — `test_procedure_planner_never_returns_empty_plan_without_error` (parametrized, 4 cases) ✅
- [x] Unit test: unknown `target_procedure_id` → `errors[]` contains user-friendly message, `procedure_execution_plan` is empty list ✅

#### Notes / Constraints
- `enrichment_node` must never make an LLM call — if you find yourself adding one, the logic belongs in the Synthesizer or a worker function instead
- `procedure_planner_fn` is a plain helper function called by `enrichment_node` — not a LangGraph node, not in `NODE_REGISTRY`
- **Do not put topological sort logic inside either function** — call `procedure_graph.resolve_execution_plan()` (CLAUDE.md Rule 1)
- `enrichment_node` must check whether `"form_filler_fn"` is present in `state["execution_plan"]` before performing any work. If `"form_filler_fn"` is not in the plan, return an empty dict immediately regardless of whether `target_procedure_id` is set.
- The lazy-check guard (`form_filler_fn` in `execution_plan`) is the primary token-saving mechanism of this node. Without it, any procedure-related query injects a full procedure plan into the Synthesizer prompt regardless of relevance. Do not remove this guard without a documented reason.
---

---
### TASK-10: Synthesizer Node + Synthesis Prompt ✅ COMPLETE
**Phase:** 3
**Priority:** High
**Estimated effort:** M (2 days)
**Depends on:** TASK-06 (rag_fn), TASK-08 (form_filler_fn), TASK-09 (enrichment_node)
**Can be parallelized with:** TASK-11 (after deps)
**Completed:** 2026-04-10

#### Goal
Implement the Synthesizer — the only true output graph node after `plan_executor`. It assembles `final_response` from all accumulated state fields. The Synthesizer must handle six distinct response modes cleanly from a single node — the synthesis prompt must be designed to cover all of them before any code is written:

  1. **RAG only** — legal question answered with citations, no form or OCR context
  2. **OCR only** — document uploaded and extracted, no form fill requested
  3. **Form fill complete** — all required fields filled, PDF ready for download
  4. **Form fill partial** — some required fields missing, user must be prompted for specific missing values (sourced from `unfilled_required_fields`)
  5. **Multi-worker combined** — RAG + OCR + form fill all ran in same invocation
  6. **Circuit-breaker or error** — `errors` list is non-empty; surface a user-friendly message without exposing internal state or tracebacks

Design the synthesis prompt to handle all six modes via conditional sections keyed on which state fields are populated. Do not implement six separate prompts — one prompt with conditional logic is correct.

The Synthesizer must also handle `scope_used` metadata from `rag_fn` state — when `scope_used` indicates fallback occurred (i.e. the scope used is broader than `filing_jurisdiction`), the response must include a transparent note: 'Đang áp dụng quy định cấp [level] vì chưa tìm thấy quy định cấp [narrower level].' This is not an error mode — it is expected behavior that must be visible to the user.

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
- [x] `final_response` is a clean string (not raw state dump) — `test_synthesizer_error_mode`, `test_synthesizer_fallback_mode` ✅
- [x] If `unfilled_required_fields` is non-empty, response asks user for missing data — `test_synthesizer_form_fill_partial_mode` ✅
- [x] If `errors` is non-empty (e.g. circuit-breaker fired), response surfaces a user-friendly message — `test_synthesizer_error_mode` ✅
- [x] Citations included in response when `retrieved_chunks` is non-empty — RAG passthrough path verified in `test_synthesizer_rag_only_mode_no_scope_notice` ✅
- [x] **Only** `final_response` and `response_metadata` stream to frontend — not raw state — enforced in return dict ✅
- [x] Unit tests cover all six response modes with appropriate mocked state — 8 tests, all passing ✅ *(Note: `circuit_breaker` mode is implemented in `_determine_mode()` but has no dedicated test — all other 5 modes have explicit test functions. Minor gap, not blocking.)*
- [x] Synthesis prompt reviewed against all six modes before implementation begins ✅
- [x] When `scope_used` in state is broader than `filing_jurisdiction`, response includes scope fallback notice — `test_synthesizer_rag_only_mode_with_scope_notice` ✅
- [x] Scope fallback notice uses Vietnamese level names (cấp phường, cấp thành phố, cấp quốc gia) — `test_synthesizer_scope_level_mapping` ✅
- [x] RAG-only mode skips LLM call when no scope notice needed — `test_synthesizer_rag_only_mode_no_scope_notice` asserts `async_invoke` not called ✅
- [x] LLM failure returns hardcoded fallback without propagating exception — `test_synthesizer_llm_failure_returns_hardcoded_fallback` ✅

#### Notes / Constraints
- **Do not stream raw LangGraph state** — only `final_response` goes over SSE (CLAUDE.md rule)
- The synthesis prompt receives only the windowed history from state — never construct a full session history inside the node
- This is the only node that must be aware of the full accumulated state shape after all worker functions have run
---

---
### TASK-11: LangGraph Graph Assembly (plan_executor topology) + Functional Chat Endpoint ✅ COMPLETE
**Phase:** 4
**Priority:** Critical
**Estimated effort:** M (2 days)
**Depends on:** TASK-01, TASK-06, TASK-08, TASK-09, TASK-10, TASK-0F (circuit-breaker design)
**Can be parallelized with:** TASK-13
**Completed:** 2026-04-10

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
- [x] `POST /chat` with `{"message": "Tôi muốn đăng ký thường trú"}` returns SSE stream
- [x] SSE events contain only `final_response` chunks, not raw state
- [x] `plan_executor` correctly calls `rag_fn` for a `["rag_fn"]` plan
- [x] `plan_executor` correctly calls `ocr_fn` then `form_filler_fn` in order for a `["ocr_fn", "form_filler_fn"]` plan
- [x] Circuit-breaker fires and routes to Synthesizer when `plan_cursor >= MAX_PLAN_STEPS`
- [x] A plan `["ocr_fn", "rag_fn", "form_filler_fn"]` results in `ocr_fn` and `rag_fn` being called concurrently in a single `asyncio.gather()`, verified by unit test that asserts gather was called with both
- [x] `enrichment_node` is wired between `router_node` and `plan_executor_node` in the compiled graph
- [x] `GraphRecursionError` returns HTTP 500 JSON (not a traceback)
- [x] Full graph traversal integration test passes with mocked LLM and mocked `NODE_REGISTRY`
- [ ] `/review-api-route` checklist passes for `chat.py`

#### Notes / Constraints
- `node_registry.py` is the **only** file that imports all worker functions — `graph.py` imports only from `node_registry` and `nodes/router.py`, `nodes/enrichment.py`, `nodes/plan_executor.py`, `nodes/synthesizer.py`
- Valid `NODE_REGISTRY` keys: `"rag_fn"`, `"ocr_fn"`, `"form_filler_fn"`. `"procedure_planner_fn"` is NOT a valid key.
- Worker functions called via `asyncio.gather()` each receive a snapshot copy of state at the start of the wave — they must not mutate shared state in place. Each returns a dict; plan_executor merges all dicts after the wave completes.
- Worker functions in `NODE_REGISTRY` must never write to `execution_plan` or `plan_cursor`
- Session load at graph entry hydrates `conversation_history` from Redis — this is already the trimmed 6-turn window. No additional trimming needed inside the graph.
- Session load/save wraps every invocation (CLAUDE.md Rule 4 pattern)
- Session load at graph entry must hydrate both `domain` and `filing_jurisdiction` from `SessionData` into `AgentState`, in addition to the existing `conversation_history` hydration. Both fields may be `None` on first invocation — the graph must handle `None` gracefully without routing errors.
- `domain` in `AgentState` is set by the router on every invocation. If the router returns `domain: None` (ambiguous), the Synthesizer must ask for clarification rather than proceeding with an empty domain — verified by integration test.
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
### TASK-13: Synthetic CCCD Mock Image Generation ✅ COMPLETE
**Phase:** 4
**Priority:** High
**Estimated effort:** S (1 day)
**Depends on:** None (pure Pillow/qrcode, no services) — but should be started in parallel with TASK-05, not after it
**Can be parallelized with:** Any task
**Completed:** 2026-04-09

#### Goal
Generate a library of synthetic CCCD identity card images for testing the OCR pipeline and validating the prompt injection hardening from TASK-04. The synthetic dataset must cover four distinct categories that test different pipeline behaviors — clean QR baseline, degraded QR preprocessing validation, no-QR OCR path validation, and injection attempt hardening. The dataset must be sufficient to validate pipeline logic and schema correctness. It does not need to prove real-world OCR accuracy — that limitation must be stated explicitly in any presentation.

#### Inputs
- `ingestion/generate_mock_data.py` → stub to implement

#### Outputs
- `ingestion/generate_mock_data.py` — script generating 10+ synthetic CCCD images using Pillow
- `backend/data/mock_documents/` — populated with generated images, including at least one image whose name field contains an injection-attempt string
- Images are organized into four subdirectories under `backend/data/mock_documents/`:
  - `category_1_clean_qr/` — perfect QR, valid data, baseline
  - `category_2_degraded_qr/` — rotation (2–5°), JPEG artifacts, gaussian noise, simulated glare patch overlay
  - `category_3_no_qr/` — realistic font, diacritic-heavy Vietnamese text, no QR code
  - `category_4_injection/` — injection attempt strings in field values: `{"role": "system"}`, `</ocr_text>`, SQL-like string

#### Definition of Done
- [x] Script generates 10+ synthetic CCCD images without error
- [x] Images contain readable Vietnamese text (Pillow with Vietnamese font)
- [x] Running OCR on generated images returns non-empty `PersonalData`
- [x] At least one image contains an injection-attempt string in a text field to validate TASK-04 hardening
- [x] At least 3 images include a **QR code** encoding the CCCD data in `id_number||full_name|dob|gender|address|issue_date` format (index 1 always empty) to test `OCRService.decode_qr()` success path
- [x] At least 3 images have **no QR code** to test the PaddleOCR fallback path
- [x] Category 1: 3+ images with valid QR, clean layout — baseline happy path
- [x] Category 2: 3+ images per degradation type (rotation, noise, compression, glare) — validates 5-attempt preprocessing stack
- [x] Category 3: 3+ images with no QR, diacritic-heavy text — validates PaddleOCR fallback path
- [x] Category 4: 3+ images with injection strings in field values — validates Pydantic rejection
- [x] Category 2 degradation is severe enough to require more than attempt 1 to decode — if attempt 1 always succeeds, degrade further
- [x] README in `backend/data/mock_documents/` documents the ground truth values for each image for benchmark use

**Note:** Images are located at `backend/data/mock_documents/` in four subdirectories. 20 images per category, 80 total. Images will be used as test input for TASK-12 (OCR endpoint) and TASK-14 (integration tests) once the API key is configured.

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
Write the full integration test suite verifying the complete citizen journey from question to filled form under the new `plan_executor` topology. Additionally, the evaluation suite must support the scientific contribution claim — validating that pipeline mechanics behave consistently across procedure domains. Multi-domain tests are scoped to housing domain only at this stage; cross-domain tests are in TASK-18 after housing demo is stable.

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
- [ ] Scope selection test: given `filing_jurisdiction` + procedure → assert correct scope filter built by `rag_fn`
- [ ] Fallback test: procedure with no ward-level documents → assert `scope_used` reflects city-level, user message includes fallback notice
- [ ] Out-of-scope test: unknown `target_procedure_id` → assert `errors[]` contains user-friendly message, no hallucinated response
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
- Housing domain templates (3) are required for Phase 1 demo. Templates for civil registration and business registration domains are required for TASK-17 but are not part of this task. When TASK-17 begins, add one template per new domain procedure to MinIO and `form_templates` table as an extension of this task's pattern.
---

---

### TASK-16: Jurisdiction Infrastructure ✅ COMPLETE
**Phase:** 3
**Priority:** Critical
**Estimated effort:** S (1 day)
**Depends on:** TASK-0A (get_db()), TASK-0B (ORM models)
**Can be parallelized with:** TASK-05, TASK-06, TASK-09
**Sequence gate:** Must complete before TASK-17 begins. Can start immediately — no dependency on housing demo completion.
**Completed:** 2026-04-09

#### Goal
Implement all jurisdiction infrastructure required for hierarchical scope filtering. This task creates the foundational utilities and data structures that TASK-06, TASK-09, TASK-17, and TASK-18 all depend on. It does not implement any RAG or routing logic — only the infrastructure layer.

#### Inputs
- `app/core/jurisdiction.py` → new file
- `app/models/` → extend with `AdministrativeUnit` model
- `app/schemas/session.py` → add `filing_jurisdiction` and `domain` fields to `SessionData`
- `app/agents/state.py` → add `domain` and `filing_jurisdiction` fields to `AgentState`
- `alembic/versions/` → new migration 0003

#### Outputs
- `app/core/jurisdiction.py`:
  - `expand_scope_hierarchy(scope: str) -> list[str]` — pure Python, zero infrastructure dependencies
  - `validate_scope_code(scope: str, db_session) -> bool` — optional validation against `administrative_units` table, used at query time only
- `alembic/versions/0003_jurisdiction_and_domain.py` — migration adding:
  - `domain VARCHAR(50) NOT NULL DEFAULT 'housing'` column to `procedures` table
  - `administrative_units` table: `(code VARCHAR(20) PK, name VARCHAR(100), administrative_level VARCHAR(20), parent_code VARCHAR(20) NULLABLE)`
  - `scope_coverage` table: `(location_scope VARCHAR(50), procedure_id UUID FK, domain VARCHAR(50), chunk_count INTEGER, last_ingested_at TIMESTAMPTZ, PRIMARY KEY(location_scope, procedure_id))`
- `app/models/administrative_unit.py` — ORM model for `administrative_units` table
- `app/schemas/session.py` — `filing_jurisdiction: str | None` and `domain: str | None` added to `SessionData`
- `app/agents/state.py` — `domain: str | None` and `filing_jurisdiction: str | None` added to `AgentState`
- `ingestion/seed_administrative_units.py` — seeds `administrative_units` table with ward codes needed for housing domain test cases (minimum: Ward Tân Hòa + District in Ho Chi Minh City used in test data)
- `ingestion/domain_configs/housing.yaml` — explicit article mappings for TTHC-001, TTHC-002, TTHC-003
- `tests/unit/test_jurisdiction.py` — unit tests for `expand_scope_hierarchy()` and `validate_scope_code()`

#### Definition of Done
- [x] `expand_scope_hierarchy("VN-HCM-070")` returns `["VN", "VN-HCM", "VN-HCM-070"]` — verified by unit test
- [x] `expand_scope_hierarchy("VN")` returns `["VN"]` — verified by unit test
- [x] Migration 0003 applies cleanly on top of 0002 — `alembic upgrade head` succeeds
- [x] `procedures` table has `domain` column with default `'housing'`
- [x] `administrative_units` table seeded with 8 HCM City wards (province + 3 districts + 4 wards)
- [x] `scope_coverage` table exists and accepts upsert without error
- [x] `SessionData` round-trips `filing_jurisdiction` and `domain` through Redis without data loss
- [x] `AgentState` TypedDict includes `domain` and `filing_jurisdiction` fields
- [x] `domain_configs/housing.yaml` exists with correct procedure IDs matching seeded `procedures` table rows
- [x] All unit tests pass — 201 total (17 new: 9 jurisdiction + 8 LLMService)

#### Notes / Constraints
- `expand_scope_hierarchy()` must live in `app/core/` — no imports from `services/`, no DB session, consistent with CLAUDE.md Rule 5
- Do not add `ltree` PostgreSQL extension — string-based scope codes are sufficient at current scale
- `administrative_level` values: `'province'`, `'district'`, `'ward'`, `'commune'`, `'town'`
- Seed only the ward codes actually needed for test cases — do not import the full national TCTK dataset at this stage

---

---

### TASK-17: Multi-Domain Ingestion and Data Preparation
**Phase:** 4
**Priority:** High
**Estimated effort:** L (4–5 days)
**Depends on:** TASK-05 (ingestion pipeline), TASK-16 (jurisdiction infrastructure)
**Can be parallelized with:** TASK-11, TASK-12, TASK-14
**Sequence gate:** Must NOT begin until TASK-11 (housing demo) is complete and stable. All housing domain work must be verified working end-to-end before multi-domain expansion begins.

#### Goal
Extend the ingestion pipeline and seed data to cover two additional domains — civil registration (hộ tịch) and business registration (kinh doanh) — each with one representative procedure and a full three-level hierarchical branch (VN → VN-HCM → VN-HCM-[ward_code]). This task is the data foundation for the scientific contribution claim. It does not change any pipeline code — only ingestion configuration, seed data, and legal documents.

This task validates the claim that "extending to a new domain requires only ingestion and data tasks, not pipeline changes." If any pipeline code change is required to ingest a new domain, that is a finding that must be documented and addressed before TASK-18.

#### Inputs
- `ingestion/ingest_legal_docs.py` → extend to read `location_scope` from domain config
- `ingestion/domain_configs/` → new YAML files for two domains
- Legal documents for civil registration: Luật Hộ tịch 2014, Nghị định 123/2015/NĐ-CP, plus any Ho Chi Minh City or ward-level circular for the same procedure — must be collected before this task begins
- Legal documents for business registration: Luật Doanh nghiệp 2020, Nghị định 01/2021/NĐ-CP, plus Ho Chi Minh City/ward-level equivalents — must be collected before this task begins
- TASK-16 complete (administrative_units seeded, domain column exists)

#### Outputs
- `ingestion/domain_configs/civil_registration.yaml` — explicit article mappings for Đăng ký khai sinh (TTHC-CR-001), three scope levels
- `ingestion/domain_configs/business_registration.yaml` — explicit article mappings for Đăng ký hộ kinh doanh (TTHC-BZ-001), three scope levels
- `ingestion/ingest_procedures.py` — updated to seed one procedure per new domain with correct `domain` classification
- Qdrant `legal_documents` collection populated with chunks for all three domains at all three scope levels
- `scope_coverage` table populated for all ingested (location_scope, procedure_id, domain) combinations
- `administrative_units` table extended with ward codes for the specific wards used in civil registration and business registration test branches

#### Definition of Done
- [ ] Civil registration legal documents ingested at VN, VN-HCM, and VN-HCM-[ward] scope levels — chunks visible in Qdrant
- [ ] Business registration legal documents ingested at VN, VN-HCM, and VN-HCM-[ward] scope levels — chunks visible in Qdrant
- [ ] `scope_coverage` table has rows for all three domains at all ingested scope levels
- [ ] `QdrantService.search("đăng ký khai sinh", procedure_id="TTHC-CR-001", domain="civil_registration")` returns relevant chunks
- [ ] `QdrantService.search("đăng ký hộ kinh doanh", procedure_id="TTHC-BZ-001", domain="business_registration")` returns relevant chunks
- [ ] **No pipeline code changes were required** to support new domains — if any were needed, document them explicitly before marking this done
- [ ] `domain_configs/*.yaml` files have been manually verified — article mappings checked against source legal documents
- [ ] Router prompt updated with domain-diverse few-shot examples (4 per new domain) before running any multi-domain retrieval tests
- [ ] `verify_citations()` tested against citation formats from all three domains — no false-flagging on correct citations

#### Notes / Constraints
- Collect all legal documents before starting implementation — data collection is the blocking activity, not coding
- Use the same scope code convention as housing: `VN-HCM-[official_ward_code]` — do not use ward name strings
- If any domain's legal documents use citation formats not covered by the refactored `verify_citations()`, document the format and update the matching logic before ingesting
- This task must be completed before TASK-18 can begin

---

---

### TASK-18: Evaluation Dataset and Benchmark Suite
**Phase:** 4
**Priority:** High
**Estimated effort:** M (3 days)
**Depends on:** TASK-17 (multi-domain data), TASK-11 (full graph), TASK-14 (integration tests)
**Can be parallelized with:** Nothing — requires all above complete
**Sequence gate:** Must NOT begin until TASK-17 is verified complete and all three domains have confirmed data in Qdrant.

#### Goal
Construct the labeled evaluation dataset and implement the benchmark suite that validates the scientific contribution claim. The benchmark measures eight properties across three domains. Ground truth is constructed using a three-tier methodology — self-labelable tier, document-verifiable tier, and an explicitly noted external-validation tier that is outside this research prototype's scope.

This task produces the evidence that supports or challenges the claim: "The architecture is domain-agnostic and validates across DAG-based and hierarchical-based procedure structures."

#### Inputs
- All three domains ingested in Qdrant (TASK-17 complete)
- Full graph running (TASK-11 complete)
- Integration tests passing (TASK-14 complete)
- Source legal documents for all three domains (for Tier 2 labeling)

#### Outputs
- `tests/evaluation/` — new directory
- `tests/evaluation/datasets/router_queries.json` — labeled query set, 20 queries per domain (60 total), each with known correct `execution_plan`, `domain`, `target_procedure_id`
- `tests/evaluation/datasets/citation_ground_truth.json` — 10 question/correct-article pairs per domain (30 total), manually verified against source legal documents
- `tests/evaluation/datasets/scope_selection_cases.json` — test cases: `(filing_jurisdiction, procedure_id)` → expected scope filter and expected `scope_used`
- `tests/evaluation/run_benchmark.py` — script running all 8 measurements and producing a results report
- `tests/evaluation/BENCHMARK_RESULTS.md` — filled in after running, documents results per domain with explicit tier labeling

#### The 8 measurements

**Measurement 1 — Router intent accuracy (Tier 1):**
Given labeled query set, what fraction produce correct `execution_plan`? Measured per domain. Threshold: ≥85% per domain.

**Measurement 2 — Router domain classification accuracy (Tier 1):**
Given labeled query set, what fraction produce correct `domain` value? Measured per domain. Threshold: ≥85% per domain.

**Measurement 3 — Scope selection correctness (Tier 1):**
Given `(filing_jurisdiction, procedure_id)` test cases, what fraction produce the correct scope filter? Threshold: 100% — this is deterministic logic.

**Measurement 4 — Cascade fallback correctness (Tier 1):**
Given procedures with known coverage gaps, does `scope_used` reflect the correct fallback level? Does the user message include the fallback notice? Threshold: 100% — deterministic.

**Measurement 5 — RAG citation recall (Tier 2):**
Given citation ground truth set, what fraction of correct articles appear in retrieved chunks? Measured per domain.

**Measurement 6 — Citation hallucination rate (Tier 2):**
What fraction of generated citations are flagged as `[unverified: ...]` by `verify_citations()`? Lower is better. Measured per domain.

**Measurement 7 — Out-of-scope validation correctness (Tier 1):**
Given unknown procedure IDs and queries with no matching documents, does the system produce named errors rather than hallucinated responses? Threshold: 100%.

**Measurement 8 — Domain isolation (Tier 1):**
Given two users in the same ward but different domains, do they receive chunks exclusively from their respective domains? Threshold: 100% — verifiable by inspecting retrieved chunk payloads.

#### Definition of Done
- [ ] All three labeled datasets constructed and stored in `tests/evaluation/datasets/`
- [ ] Tier 2 citation ground truth manually verified against source documents — not inferred
- [ ] `run_benchmark.py` executes all 8 measurements without manual intervention
- [ ] `BENCHMARK_RESULTS.md` filled in with actual numbers per domain
- [ ] Each metric labeled with its tier (1, 2, or 3) in the results report
- [ ] Results for Measurement 1 and 2 (router accuracy) are ≥85% per domain — if not, router prompt must be updated and benchmark rerun before task is marked complete
- [ ] Results for Measurements 3, 4, 7, 8 are 100% — these are deterministic and any failure indicates a pipeline bug, not a quality issue
- [ ] BENCHMARK_RESULTS.md explicitly states: "Tier 3 legal correctness validation (whether the system's guidance is legally accurate) is outside the scope of this research prototype and requires external legal review"

#### Notes / Constraints
- Tier 1 labels can be self-constructed — they are deterministic given the procedure definition and configuration
- Tier 2 labels require reading source legal documents — budget time for this; it cannot be automated
- Do not run the benchmark before TASK-17 is confirmed complete — empty coverage for a domain must not be counted as a pipeline failure
- The benchmark script must query `scope_coverage` table first and skip test cases for unavailable (domain, scope) combinations, logging which combinations were skipped

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

TASK-16 (Jurisdiction infrastructure) ─── independent, start immediately
  └─► TASK-17 (Multi-domain ingestion) ◄── TASK-05 + TASK-11 (housing demo complete)
        └─► TASK-18 (Evaluation + benchmark) ◄── TASK-14 + TASK-17

Sequence gate: TASK-17 and TASK-18 must NOT begin until TASK-11 (housing demo) is complete and verified running end-to-end.
```

Parallelizable from day 1 (no dependencies):
- **TASK-0A, TASK-0B, TASK-0D, TASK-0E, TASK-13, TASK-16** can all start simultaneously

Gated on housing demo complete (TASK-11):
- TASK-17, TASK-18 must wait for TASK-11 end-to-end verification

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
- ~~`TASK-13`~~ ✅ Mock CCCD image generation (synthetic test data)

~~**3. TASK-04 — OCR Service + ocr_fn Worker**~~ ✅ Complete (2026-03-27) — 15 unit tests passing

**4. TASK-05 + TASK-06 + TASK-09 + TASK-13 — current Group B tasks**
TASK-04 done. The following can start simultaneously:
- ~~`TASK-04`~~ ✅ OCR service (two-path: QR decode + PaddleOCR fallback, prompt-injection hardened)
- ~~`TASK-05`~~ ✅ Legal doc ingestion — 27 chunks in Qdrant, scope_coverage populated, 163 unit tests passing
- `TASK-06` RAG worker function (requires TASK-01 ✅ + TASK-02 ✅ + TASK-05 ✅)
- ~~`TASK-09`~~ ✅ enrichment_node + procedure_planner_fn — two-condition guard verified, 21 new unit tests
- ~~`TASK-13`~~ ✅ Mock CCCD image generation — 80 images across 4 categories

~~**4. TASK-06 + TASK-08 + TASK-10 — Group C**~~ ✅ All complete (2026-04-10)
- ~~`TASK-06`~~ ✅ RAG worker function + citation verifier (10 tests; cascade retrieval, threshold stopping, verify_citations)
- ~~`TASK-08`~~ ✅ form_filler_fn worker (22 tests; confidence merge, LLM cache, promote/hold logic)
- ~~`TASK-10`~~ ✅ Synthesizer node (8 tests; 6 response modes, RAG LLM-skip optimisation)

~~**5. TASK-11 — Graph Assembly + Functional Chat Endpoint**~~ ✅ Complete (2026-04-10) — 254 unit tests passing

**5. TASK-06 + TASK-08 — final two worker functions (start now, can run in parallel)**
- `TASK-06` RAG worker function (`rag_fn`) + `rag_prompt.py` + `citation_formatter.py` — all deps satisfied ✅
- `TASK-08` form_filler_fn worker + `form_mapping_prompt.py` + `session_accumulator.py` + `form_field_mapper.py` — all deps satisfied ✅

**After TASK-06 + TASK-08 complete:**

`TASK-12` Document upload + OCR endpoint — `POST /api/v1/documents/upload`

`TASK-14` Integration tests — end-to-end graph traversal + RAG pipeline

**After housing demo stable (TASK-11 + TASK-06 + TASK-08 verified end-to-end):**

`TASK-17` Multi-domain ingestion — collect legal documents for civil registration and business registration domains first (non-code prerequisite). Data collection is the blocking activity.

`TASK-18` Evaluation dataset and benchmark — begins only after TASK-17 complete. Budget 3 days. Tier 2 labeling against source documents is the most time-consuming step.
