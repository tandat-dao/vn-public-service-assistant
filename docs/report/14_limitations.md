# Section 14 — Limitations and Deferred Work

## 14.1 Status of P1–P16 Known Problems

This section assesses each known problem documented in `docs/PROJECT_CONTEXT.md §6` against the actual implementation state found during the codebase review.

---

### P1 — Jurisdiction Signal Reliability

**Design decision**: `filing_jurisdiction` stored as a first-class `SessionData` field, set only by explicit user confirmation. OCR address pre-fills suggestion only.

**Current status**: Partially addressed.

- `filing_jurisdiction: str | None` exists in `AgentState` (declared in `state.py` with the comment "confirmed by user — never set from raw OCR alone").
- The field is never written directly from OCR output — the OCR path sets only `extracted_personal_data`.
- However, no explicit user confirmation flow exists in the current synthesizer modes. The 8 synthesizer modes do not include a `jurisdiction_confirmation` mode. The field is declared but relies on future guided-mode integration to be populated.
- The `SessionData` schema in `redis_service.py` does not persist `filing_jurisdiction` across turns — only `personal_data`, `completed_procedure_ids`, `form_fill_state`, and `conversation_history` are persisted to Redis.

**Upgrade condition not met**: The silent skip (OCR confidence > 0.90) has not been implemented.

---

### P2 — Silent Failure on Empty Qdrant Results

**Design decision**: Cascade fallback with explicit logging. Surface `scope_used` to user. Add `scope_coverage` table.

**Current status**: Implemented.

- `rag_fn` implements the scope cascade: most-specific scope first, broadening to VN-wide if all narrower scopes return empty.
- `scope_used: str | None` is set in `AgentState` and passed through to response metadata.
- `rag_returned_empty: bool` is set in `AgentState` when all scope levels are exhausted.
- `scope_coverage` table was added in migration `0003_jurisdiction_and_domain.py` and is populated by `ingest_full_documents.py` on each ingestion run.

---

### P3 — LLM as Primary Jurisdiction Arbiter

**Design decision**: Filter-first architecture. Qdrant filter handles jurisdiction selection. Article-number deduplication when two chunks from different scopes share `(article_number, document_number)`.

**Current status**: Implemented.

- `QdrantService._build_filter()` uses the `location_scope` payload field (not `scope`) — the critical bug from the design note was fixed in v3.3.
- `_deduplicate_by_article()` was added in v3.60 and runs after RRF sorting, before the `[:top_k]` slice.
- Both dense and BM25 search stages always include `_active_filter()`.

---

### P4 — Missing Ancestor Chain Computation

**Design decision**: `expand_scope_hierarchy()` in `app/core/jurisdiction.py`.

**Current status**: Implemented.

- `expand_scope_hierarchy()` exists in `backend/app/core/jurisdiction.py`.
- Pure Python, zero infrastructure dependencies.
- Covered by `test_jurisdiction.py`.

---

### P5 — Non-Standardized Ward Codes

**Design decision**: Official administrative unit codes as canonical identifiers. `administrative_units` PostgreSQL lookup table. OCR-parsed name → fuzzy match → official code.

**Current status**: Partially addressed.

- `administrative_units` table exists (migration 0003): `code` PK (text), `name`, `level`, `parent_code` (self-referential FK).
- `seed_administrative_units.py` populates the lookup table.
- The fuzzy matching path (OCR-parsed ward name → official code) is **not implemented** in `ocr_service.py` or any other active module. No fuzzy string matching library is imported or used. OCR output is passed through as-is into `PersonalData.permanent_address.ward`.

**Upgrade condition not met**: Clean match rate on real OCR output has not been measured.

---

### P6 — Out-of-Scope Procedure Validation

**Design decision**: Two-layer validation. Layer 1 in `procedure_planner_fn`: existence check. Layer 2 in `rag_fn`: empty chunk check after filtering.

**Current status**: Implemented.

- Router sets `out_of_scope=True` and `execution_plan=[]` when `intent == "out_of_scope"`. This is the primary gate.
- `rag_returned_empty` is set in `rag_fn` when all scope cascade levels return zero chunks, and added to `errors[]`.
- The `out_of_scope` synthesizer mode has highest priority (checked before all other modes) — it short-circuits to a fixed refusal response without calling any worker functions.

---

### P7 — Router Prompt Domain Bias

**Design decision**: Add 4 domain-diverse examples per new domain before multi-domain testing. Measure router accuracy per domain.

**Current status**: Partially addressed.

- Router prompt now includes 36+ few-shot examples spanning housing, civil registration, adoption, and out-of-scope cases (expanded from 8 examples).
- Benchmark dataset expanded from 23 cases (v3.79) to 81 labeled cases (v3.81), covering `rag_only=40`, `guided_step=16`, `out_of_scope=15`, `fallback=5`, `ambiguous/null-domain=5`.
- Per-domain accuracy breakdown is not reported separately in the benchmark output — the 80% threshold applies to the overall dataset.

**Upgrade condition**: Domain-specific accuracy below 85% triggers session-start domain selection UX — not yet evaluated.

---

### P8 — procedure_tags Assignment Inconsistency Across Domains

**Design decision**: Per-domain YAML configuration files at `ingestion/domain_configs/[domain].yaml`. Ingestion script reads config — never infers tags automatically.

**Current status**: NOT implemented as designed. (See deviation D16 in Section 13.)

- `ingestion/domain_configs/` directory exists and contains YAML files.
- `ingest_full_documents.py` (the active script) does NOT read these YAML files. `procedure_ids` are hardcoded directly in the `DOCUMENT_REGISTRY` Python dict within the script.
- Tags are effectively hardcoded per document in the ingestion script, not YAML-driven.
- The design intent (no automatic inference, explicit mapping) is honored — but via Python constants, not YAML config.

---

### P9 — verify_citations() Citation Format Variation

**Design decision**: Refactor `verify_citations()` to match against chunk payload `(article_number, document_number)` pairs, not against citation string format.

**Current status**: Partially addressed.

- `verify_citations()` in `citation_formatter.py` uses two regex patterns: `_CITATION_RE` (Điều/Khoản format) and `_ALT_CITATION_RE` (Mục/số/Phụ lục format added in v3.68).
- The alt format (`_ALT_CITATION_RE`) provides broader coverage, but the matching is still regex-based on citation string patterns.
- The design decision called for payload-based matching against `(article_number, document_number)` pairs — this approach is **not implemented**. Citation strings are still extracted via regex, then verified against chunk payloads by comparing extracted article numbers.

**Upgrade condition**: Full payload-based matching should have been completed before multi-domain ingestion per the design note.

---

### P10 — Missing Domain Classification in Data Model

**Design decision**: `domain` column added to `procedures` table (migration 0003). `domain` field in `AgentState` and `SessionData`. Router outputs `domain` as structured field.

**Current status**: Implemented, with one ORM gap.

- Migration `0003_jurisdiction_and_domain.py` adds `domain VARCHAR(50) NOT NULL DEFAULT 'housing'` to `procedures`.
- `RouterOutput` includes `domain: str | None`.
- `AgentState` has `domain: str | None`.
- **Gap**: The `Procedure` SQLAlchemy ORM model (`backend/app/models/procedure.py`) does NOT declare the `domain` column — it is only in the migration, not in the ORM mapping. ORM drift. Direct SQL or raw queries use the column correctly, but SQLAlchemy model-based access to `procedure.domain` would raise `AttributeError`.

---

### P11 — Scope Coverage Gaps During Active Development

**Design decision**: `scope_coverage` table built as part of TASK-16. Ingestion script upserts coverage rows. Benchmark skips unavailable combinations.

**Current status**: Implemented.

- `scope_coverage` table: composite PK `(location_scope, procedure_id)`, FK to `procedures` with CASCADE DELETE.
- `ingest_full_documents.py` truncates `scope_coverage` and re-inserts from `DOCUMENT_REGISTRY` on every run.
- Benchmark dataset notes case R16 as a known flaky case, but scope unavailability is not separately tracked in the benchmark output.

---

### P12 — Cross-Domain Router Confusion on Ambiguous Queries

**Design decision**: Router outputs `domain: str | None`. When `domain=None`, Synthesizer asks for clarification before proceeding.

**Current status**: Partially addressed.

- Router outputs `domain: str | None`.
- AgentState carries `domain`.
- The `fallback` synthesizer mode handles cases where no specific mode is triggered, but there is no dedicated `domain_clarification` synthesizer mode.
- When the router returns `domain=None` and the query is genuinely ambiguous, the `rag_fn` executes without domain filtering — it does not trigger a clarification prompt. The design's "ask for clarification" behavior is not explicitly implemented as a synthesizer path.

---

### P13 — Evaluation Dataset Construction Methodology

**Design decision**: Three-tier ground truth structure. Tier 1 (self-labelable): router intent, scope. Tier 2 (document-verifiable): citation recall. Tier 3 (external validation): legal correctness — out of scope.

**Current status**: Partially implemented.

- Tier 1 is substantially implemented: 81 labeled cases measuring `mode`, `domain`, `procedure_id`, `location_scope` router accuracy.
- Tier 2 is partially implemented: the benchmark measures citation recall for cases with `expected_citations` in the dataset — but not all 81 cases have citation ground truth.
- Tier 3 (legal correctness) is explicitly excluded from measurement — this is the correct approach per the design and for the thesis scope.
- The three-tier methodology is documented in design but not explicitly stated in benchmark output reports.

---

### P14 — Token Diversity in Retrieved Context (MMR)

**Design decision**: DEFERRED. Do not implement until: corpus > 2,000 chunks AND citation recall < 80% AND root cause is confirmed as redundant chunk selection.

**Current status**: Still deferred.

- No MMR implementation exists anywhere in the codebase.
- `_deduplicate_by_article()` provides light per-article deduplication but is not MMR.
- Current corpus: ~904 Qdrant points (from PROJECT_STATUS.md v3.51). Upgrade condition (2,000 chunks) not met.

---

### P15 — Retrieval Precision for Low-Frequency Article Queries (Cross-Encoder)

**Design decision**: DEFERRED. Do not implement until citation recall < 80% AND root cause confirmed as retrieval precision.

**Current status**: Still deferred.

- No cross-encoder reranker implemented.
- No `sentence-transformers` cross-encoder model in `requirements.txt`.
- Citation recall metric exists in the benchmark but results from a live run are not available from static analysis.

---

### P16 — Document Authority Hierarchy Not Modeled

**Design decision**: DEFERRED. No `document_authority_level` field until conflicting provisions observed in evaluation.

**Current status**: Still deferred.

- No `document_authority_level` field in Qdrant payload. Ingestion scripts do not write it.
- All ingested documents for a given procedure are treated as complementary (Luật sets principles, Nghị định elaborates, Thông tư specifies details) — no conflicts observed in the current corpus.
- The design note for thesis explicitly acknowledges this as outside the research contribution scope.

---

## 14.2 P1–P16 Status Summary

| # | Problem | Status | Notes |
|---|---|---|---|
| P1 | Jurisdiction signal reliability | Partially addressed | `filing_jurisdiction` field declared but not persisted across sessions; no confirmation flow |
| P2 | Empty Qdrant result silent failure | Implemented | Cascade fallback, `scope_used`, `rag_returned_empty`, `scope_coverage` table |
| P3 | LLM as jurisdiction arbiter | Implemented | Filter-first, `_deduplicate_by_article()` (v3.60), `_active_filter()` always applied |
| P4 | Ancestor chain computation | Implemented | `expand_scope_hierarchy()` in `jurisdiction.py`, tested |
| P5 | Non-standardized ward codes | Partially addressed | `administrative_units` table seeded; fuzzy match NOT implemented |
| P6 | Out-of-scope procedure validation | Implemented | Router `out_of_scope` intent + `rag_returned_empty` flag + `errors[]` |
| P7 | Router domain bias | Partially addressed | 36+ examples, 81-case benchmark, but per-domain accuracy not reported separately |
| P8 | procedure_tags inconsistency | Not as designed | YAML files exist but not consumed; tags hardcoded in DOCUMENT_REGISTRY |
| P9 | Citation format variation | Partially addressed | Alt format added (v3.68); payload-based matching not implemented |
| P10 | Missing domain classification | Implemented (with ORM gap) | Migration + RouterOutput + AgentState; Procedure ORM missing `domain` attribute |
| P11 | Scope coverage gaps | Implemented | `scope_coverage` table + ingestion upsert |
| P12 | Cross-domain router confusion | Partially addressed | Router outputs `domain`; clarification synthesizer mode not implemented |
| P13 | Evaluation dataset methodology | Partially implemented | Tier 1 and Tier 2 measured; Tier 3 correctly excluded |
| P14 | Token diversity / MMR | Still deferred | Upgrade conditions not met |
| P15 | Cross-encoder reranking | Still deferred | Upgrade conditions not evaluated |
| P16 | Document authority hierarchy | Still deferred | No conflicts observed; correctly out of research scope |

---

## 14.3 Additional Limitations Found During Review

These limitations were identified during the section-by-section codebase review and are **not** documented in `PROJECT_CONTEXT.md §6`.

### L1 — Qdrant `status` Field Not Written by Active Ingestion Script

**Severity: High (potential data availability bug)**

`ingest_full_documents.py` does NOT write a `status` field to the Qdrant payload. The upserted point dict contains `document_number`, `document_name`, `domain`, `location_scope`, `procedure_tags`, `article_number`, `khoan_number`, `content` — but no `status` key.

`QdrantService._active_filter()` creates a `FieldCondition` for `status == "active"` that is applied to every search. Per Qdrant's behavior, a `must` filter on a payload field that does not exist on a given point evaluates to false — those points are excluded from results.

**Impact**: All ~904 currently ingested points may be silently filtered out by `_active_filter()` in every search. The system would receive empty results from every query, triggering the `rag_returned_empty` path. This was not caught by unit tests because `QdrantService` is mocked in all unit tests. Runtime verification against a live Qdrant instance is required to confirm actual behavior.

### L2 — `FormFieldMapper` Not Called in Live Pipeline

**Severity: Medium (feature not used)**

`form_field_mapper.py` implements LLM-based semantic field mapping with a DB cache. It is tested (`test_form_mapper.py`) and the DB cache mechanism (`form_templates.fields` JSONB) exists.

In practice, `form_filler_fn` uses the static `cccd_source` mapping from `form_field_configs.py` — a hardcoded dict that maps form template placeholder names to `PersonalData` attribute paths. `FormFieldMapper.map()` is never called in the live pipeline. The `form_templates.fields` JSONB column is always null in production.

**Impact**: Adding a new form template requires editing `form_field_configs.py` as a code change, rather than relying on the zero-code LLM mapping described in the design.

### L3 — ORM Drift: `domain` Column Not Mapped

**Severity: Low (workaround exists)**

Migration `0003_jurisdiction_and_domain.py` adds `domain VARCHAR(50) NOT NULL DEFAULT 'housing'` to the `procedures` table. The `Procedure` SQLAlchemy ORM model (`models/procedure.py`) does not declare this column.

SQLAlchemy will not raise an error at startup — the column exists in the database but is invisible to the ORM. Any query that uses SQLAlchemy model attributes to read `procedure.domain` would raise `AttributeError`. The router and ingestion scripts avoid this by working with the column via raw SQL or by accessing state fields directly.

### L4 — No Frontend Automated Tests

**Severity: Medium (quality assurance gap)**

No frontend test framework is installed or configured. No Jest, Playwright, or Cypress tests exist. Frontend component behavior — including the 4-step guided wizard, SSE streaming, citation hover tooltips, and `AgentActivityPanel` — is untested by automated means.

The only frontend quality signal is TypeScript compilation (which the project passes cleanly) and manual QA.

### L5 — Stub Endpoints for Procedures and Legal Documents

**Severity: Medium (feature gap in portal)**

All 8 endpoints in `procedures.py` and `legal.py` raise `NotImplementedError`. The frontend's `api.procedures.stats()`, `api.procedures.list()`, `api.faq.list()`, `api.submissions.lookup()`, and `api.qualityIndex.list()` calls all receive HTTP 500 responses in the live system. The portal landing page and several auxiliary pages silently fail to load their data.

### L6 — LibreOffice Path Hardcoded to Windows

**Severity: Low (portability)**

`doc_filler.py` and `ingest_full_documents.py` hardcode the LibreOffice executable path as `C:\Program Files\LibreOffice\program\soffice.exe`. The Docker Compose setup does not include a LibreOffice container. Form fill via LibreOffice and `.doc`-to-PDF conversion during ingestion are platform-specific to the Windows development environment.

### L7 — BM25 Index Rebuilt Per Query

**Severity: Low (latency)**

The BM25 search stage in `QdrantService._bm25_search()` scrolls Qdrant for the relevant corpus (filtered by `procedure_id` if provided), then builds an in-memory BM25 index from scratch. This index is not cached between requests. For a corpus of ~904 points, the scroll + index build adds measurable latency on every chat request.

### L8 — `eventsource-parser` Library Installed but Unused

**Severity: Negligible (dead dependency)**

`eventsource-parser==^2.0.1` is listed in `frontend/package.json` but the SSE parsing in `client.ts` is implemented manually (line-by-line parsing with a `currentEventType` variable). The installed library is never imported.

### L9 — `sessions` Table Used as Form Submission Log

**Severity: Low (design mismatch)**

The `sessions` PostgreSQL table (defined in migration 0001 to store session data with `form_fill_state` JSONB) is used only by `POST /api/v1/forms/submit` to store form submission metadata — not as a general session store. All actual session data is in Redis. The table has no `form_submissions` equivalent; `forms.py` notes this as "a temporary measure." The tracking code generated by submit (`DVC-YYYYMMDD-XXXXXX`) has no lookup endpoint.

### L10 — `filing_jurisdiction` Not Persisted Across Sessions

**Severity: Low**

`filing_jurisdiction: str | None` is in `AgentState` and is carried within a single LangGraph invocation. The `SessionData` schema in `redis_service.py` does not include a `filing_jurisdiction` field. If a user confirms their filing jurisdiction in one turn, it is not available in the next turn — the guidance in CLAUDE.md ("confirmed by user — never set from raw OCR alone") is only enforced within a single invocation.

### L11 — `structured_summary` Always Null

**Severity: Low (deferred feature)**

The `rag_fn` token budget code references `chunk.structured_summary` as a fallback for near-budget chunks. `ingest_full_documents.py` never writes this field to the Qdrant payload. The field is effectively dead code in the retrieval path — `chunk.structured_summary` will always be `None`, and the fallback path will always use `chunk.content`.

### L12 — Celery Never Implemented

**Severity: Low (planned feature absent)**

`PROJECT_CONTEXT.md` describes "Celery + Redis — ⚙️ Partially set up." No Celery code exists anywhere in the codebase. `celery` is not in `requirements.txt`. No task definitions, worker files, or broker configuration exist. Long-running operations (LibreOffice PDF conversion, PaddleOCR inference) block the FastAPI event loop during their executor-wrapped calls, and there is no async task queue to offload them.

### L13 — Response Cache Not Verified in Active Pipeline

**Severity: Low**

`RedisService` implements a response cache (`cache:{cache_key}` with 300s TTL). The cache check and write patterns exist in `redis_service.py`. Whether `chat.py` or any other caller actively uses this cache at runtime is not evident from static analysis — `chat.py` does not call `get_cached_response()` or `set_cached_response()` in its current implementation.

### L14 — Single-Tenant Architecture

**Severity: Low (by design)**

The system has no user account model. Session isolation is enforced only by `session_id` (a client-generated UUID). The PIN gate is a demo-level access control mechanism. There is no authorization model preventing one session from accessing another session's MinIO files if the path is known (the download endpoint validates that the path's session component matches the `session_id` query parameter, but this is a convention, not cryptographic authorization).

---

## 14.4 Out-of-Scope Items for Thesis

These items are explicitly outside the research scope and should be acknowledged as such in the thesis.

| Item | Rationale |
|---|---|
| Document authority hierarchy (P16) | Vietnamese administrative law hierarchy is a valid structure, but current corpus has no conflicting documents — modeling it adds complexity with no observable benefit at current scale |
| Production authentication | PIN gate is demo-only; a production deployment would require OAuth2 or national identity integration |
| MMR diversity reranking (P14) | Deferred until corpus exceeds 2,000 chunks and citation recall measurement confirms need |
| Cross-encoder reranking (P15) | Deferred until citation recall measurement confirms retrieval precision is the bottleneck |
| Legal correctness of AI responses (P13 Tier 3) | Requires qualified legal review; outside research prototype scope |
| Frontend automated testing | No test framework was selected during development; manual QA only |
| Real government data integration | All procedures are mock data; no integration with actual government systems |
| Production deployment and scaling | Ngrok tunnel used for external access; no load balancing, HTTPS termination, or horizontal scaling |
| Celery async task queue | Never implemented; blocking executor calls are adequate at prototype scale |
| Multi-tenant isolation | Single-tenant architecture; no user accounts or cryptographic session binding |
| Fuzzy ward-code matching (P5) | Table exists but matching logic not implemented; affects jurisdiction pre-fill quality |

---

## 14.5 Research Contribution Boundary

The thesis contribution is bounded by the following implemented capabilities:

1. **Procedural dependency resolution via DAG** — Kahn's topological sort over a PostgreSQL adjacency list, producing an ordered execution plan (implemented, 100% tested in `test_procedure_graph.py`).

2. **Hierarchical jurisdiction-aware RAG** — Scope cascade (VN → VN-HCM → ward level) with `expand_scope_hierarchy()`, article-level deduplication, and citation verification (implemented, tested in `test_qdrant_service.py` and `test_rag_fn.py`).

3. **Multi-agent orchestration** — LangGraph linear pipeline with parallel wave execution of independent worker functions, synthesizer mode selection, and SSE streaming (implemented, tested in `test_agent_graph.py`).

4. **CCCD-to-form-fill pipeline** — QR decode (confidence=1.0, zero tokens) + PaddleOCR fallback with LLM extraction, confidence-wins session carry-forward, docx template fill + LibreOffice PDF conversion (implemented, integration-tested).

Items outside the boundary that the system demonstrates but does not validate scientifically:
- Citation accuracy (requires Tier 3 legal review)
- OCR accuracy on real CCCD images (tested on synthetic images only)
- LibreOffice PDF rendering fidelity on real printers
- System behavior at >100 concurrent sessions
