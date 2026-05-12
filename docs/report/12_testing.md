# Section 12 — Testing

## 12.1 Test Suite Overview

| Category | Location | Count | Status |
|---|---|---|---|
| Unit tests | `backend/tests/unit/` | 366 (as of v3.79) | Passing per PROJECT_STATUS.md |
| Integration tests | `backend/tests/integration/` | 4 test files (8 tests) | Skip when Docker not running |
| Benchmark | `backend/scripts/benchmark/` | 81 labeled cases | Requires live backend |

**Current collection status** (static analysis): 207 tests collected from 19 of 32 unit test files. 13 files fail to collect due to import errors — likely caused by API contract changes in the current working tree (modified files: `router.py`, `chat.py`, `config.py`, `llm.py`). The 366 count reflects the clean commit state at v3.79.

## 12.2 Unit Test File Inventory

32 unit test files in `backend/tests/unit/`:

| Test File | What It Covers |
|---|---|
| `test_procedure_graph.py` | Topological sort, cycle detection, gap analysis — pure Python domain logic |
| `test_dependencies.py` | Import-level dependency guards (no service imports in `app/core/`) |
| `test_pdf_service.py` | PDFService AcroForm fill + overlay fallback (inactive path) |
| `test_ocr_extraction.py` | OCRService QR decode path + PaddleOCR path (with LLM mock) |
| `test_storage_service.py` | StorageService upload/download/promote_tmp (MinIO mocked) |
| `test_embedder_service.py` | EmbedderService bge-m3 + OpenAI fallback (model mocked) |
| `test_orm_models.py` | SQLAlchemy ORM model instantiation and relationship declarations |
| `test_ingest_legal_docs.py` | Chunking helpers from `ingest_legal_docs.py` (reference script) |
| `test_procedure_planner_node.py` | `procedure_planner_fn` — DB query + topo sort (DB mocked) |
| `test_jurisdiction.py` | `expand_scope_hierarchy()` ancestor chain construction |
| `test_llm_service.py` | LLMService with all 3 backends (Anthropic/Gemini/local) — API mocked |
| `test_session_accumulator.py` | `SessionDataAccumulator.merge()` confidence-wins rule |
| `test_form_mapper.py` | `FormFieldMapper` LLM semantic mapping + DB cache check |
| `test_plan_executor.py` | `plan_executor_node` wave execution, circuit-breaker, error accumulation |
| `test_rate_limiting.py` | Rate limiter configuration and 429 response format |
| `test_document_upload.py` | `POST /api/v1/documents/upload` — file validation, OCR, Redis save |
| `test_pdf_templates.py` | PDF template fill with AcroForm detection |
| `test_forms_endpoint.py` | `POST /api/v1/forms/submit` + `POST /api/v1/forms/fill` + `GET /api/v1/forms/configs/{id}` |
| `test_legal_doc_versioning.py` | `superseded_by` FK + soft-deprecate pattern in QdrantService |
| `test_download_endpoint.py` | `GET /api/v1/documents/download` session-scoped 403 guard |
| `test_form_filler.py` | `form_filler_fn` — field mapping, MinIO promote, partial fill |
| `test_file_validator.py` | `validate_upload()` — magic byte MIME detection, extension check, size limit |
| `test_redis_service.py` | `RedisService` encrypt/decrypt, session compaction, citizen key |
| `test_text_utils.py` | `strip_markdown()` — all markdown patterns |
| `test_qdrant_service.py` | `QdrantService` hybrid search, RRF merge, token budget, active filter |
| `test_ingest_full_documents.py` | Chunking logic from `ingest_full_documents.py` (Điều/khoản split, Phụ lục, paragraph fallback) |
| `test_rag_fn.py` | `rag_fn` — query augmentation, scope cascade, token budget |
| `test_doc_filler.py` | `doc_filler.fill_doc()` — all 4 fill rules (dot-sequence, CCCD grid, family table, signing skip) |
| `test_citation_formatter.py` | `verify_citations()` — Điều/Khoản + Mục/số/Phụ lục formats |
| `test_synthesizer_node.py` | All 8 synthesizer modes, priority ordering |
| `test_chat_endpoint.py` | `POST /api/v1/chat` — SSE streaming, session lifecycle, pipeline events |
| `test_router_node.py` | `router_node` — all 3 execution paths, RouterOutput validation, `_enforce_ordering()` |

## 12.3 Integration Test Files

4 files, skipped when Docker services not running:

| Test File | What It Tests |
|---|---|
| `test_rag_pipeline.py` | End-to-end: ingest a real chunk → search → verify citation metadata |
| `test_agent_graph.py` | Full LangGraph graph run with real services (LLM mocked) |
| `test_session_persistence.py` | Redis session store/load round-trip with real Redis |
| `test_api_endpoints.py` | HTTP-level endpoint tests against running FastAPI app |

## 12.4 Test Infrastructure

**`conftest.py`** (`backend/tests/unit/conftest.py`): Stubs problematic system dependencies at `sys.modules` level before any test imports run:
- `python-magic`: replaced with a stub to avoid `libmagic` DLL crash on Windows
- `pyzbar`: replaced with a stub to avoid `libzbar0` dependency
- MinIO, PaddleOCR, cv2: selectively mocked in individual test files

**Mock pattern**: All LLM calls in unit tests use `unittest.mock.patch`. Patch targets use the `module_under_test.baz` pattern (not `foo.bar.baz`). Real API calls are never made in unit tests.

**Test fixtures**: `tests/fixtures/minimal_cccd.jpg` — committed minimal JPEG fixture used for OCR tests that require a real image path.

## 12.5 Benchmark System

**Script**: `backend/scripts/benchmark/run_benchmark.py`

**Requirements**: Live backend at `localhost:8000`, Docker Compose running, real ANTHROPIC_API_KEY configured.

**Three metrics**:

| Metric | Description | Dataset |
|---|---|---|
| Router Accuracy | Classification accuracy for `mode`, `domain`, `procedure_id`, `location_scope` | `datasets/router_accuracy.json` |
| Citation Recall | Whether expected articles appear in `retrieved_sources` metadata | Same dataset (cases with `expected_citations`) |
| Latency Baseline | End-to-end response time distribution (p50, p90, p99) | All test cases |

**Router accuracy dataset** (`datasets/router_accuracy.json`):
- 81 labeled test cases (expanded from 23 in v3.79 to 81 in v3.81)
- Distribution: `rag_only=40`, `guided_step=16`, `out_of_scope=15`, `fallback=5`, `ambiguous/null-domain=5`
- Accuracy threshold: 80% (configured in dataset JSON as `"threshold": 0.80`)
- Note: `"mode"` field uses synthesizer mode names (`rag_only`, `guided_step`) not router intent names — the benchmark reads the `metadata.mode` field from the SSE response

**Output**: JSON + Markdown report written to `scripts/benchmark/reports/benchmark_YYYYMMDD_HHMMSS.{json,md}`.

**Case R16 note**: The dataset comments that R16 should be excluded from accuracy calculation if it times out at 90s — this is a known flaky case, not a classification failure.

## 12.6 What Is NOT Tested

| Gap | Notes |
|---|---|
| End-to-end CCCD upload → form fill (real images) | Integration test exists but requires Docker + real images |
| LibreOffice PDF conversion | Mocked in unit tests; requires LibreOffice installed for integration testing |
| Real Qdrant vector search quality | Unit tests mock `QdrantService`; only integration tests use real Qdrant |
| PaddleOCR accuracy on real documents | PaddleOCR mocked in unit tests; tested via manual QA only |
| Frontend component behavior | No frontend tests exist (no Jest, no Playwright, no Cypress) |
| SSE streaming (end-to-end) | `test_chat_endpoint.py` tests the HTTP response; actual browser SSE rendering is untested |
| Rate limiting under concurrent load | `test_rate_limiting.py` tests configuration, not concurrent behavior |
| Redis TTL expiry behavior | Not tested — TTL correctness assumed from `ex=3600` in `set()` call |
| Guided wizard state machine (4-step) | Tested via `test_synthesizer_node.py` for mode logic; wizard E2E flow is untested |
