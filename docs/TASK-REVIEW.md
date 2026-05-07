# TASK-REVIEW — Codebase Review and Technical Report

**Status:** Not started  
**Priority:** High — thesis report source of truth  
**Depends on:** Nothing — pure read-only analysis

---

## Purpose

Produce a comprehensive, accurate technical report of the DichVuCong AI Assistant system **as it currently exists in the codebase**, not as described in `PROJECT_CONTEXT.md` or `CLAUDE.md`. Those documents are partially outdated (last accurate around v3.0; the system is now at v3.79 with 366 unit tests).

The output of this task is the authoritative source of truth used to write the thesis report. It must describe what is actually implemented, not what was planned.

The report covers:
- System architecture (layers, components, data flows)
- Multi-agent pipeline (LangGraph topology, nodes, state, execution model)
- RAG pipeline (ingestion, retrieval, ranking, citation verification)
- OCR pipeline (preprocessing, extraction, QR decode path)
- Form fill pipeline (field mapping, PDF generation, LibreOffice conversion)
- Data ingestion pipeline (legal document pipeline, chunking strategy)
- Database schema (all tables, columns, relationships)
- API surface (all endpoints, request/response shapes)
- Technical decisions and their rationale (what diverged from original design and why)
- Known limitations and deferred work

All architecture diagrams and pipeline flow diagrams must be written as **Mermaid code blocks**, not ASCII art or dash-based diagrams.

---

## Output Structure

⚠️ **Token limit warning:** This report is large. Write each section to its own file immediately after completing it. Do NOT accumulate all sections in memory and write at the end — context compaction will lose work. Use the file system as your working memory.

Output directory: `docs/report/`

Write these files in order. After writing each file, continue to the next. Do not skip ahead.

| Order | File | Content |
|---|---|---|
| 0 | `docs/report/00_progress.md` | Progress tracker — update after each section completes |
| 1 | `docs/report/01_system_overview.md` | Vision, scope, scientific contribution, system layers diagram |
| 2 | `docs/report/02_tech_stack.md` | Full technology stack table with actual versions from requirements.txt and package.json |
| 3 | `docs/report/03_agent_pipeline.md` | LangGraph topology, all nodes, AgentState fields, execution model, synthesizer modes |
| 4 | `docs/report/04_rag_pipeline.md` | Ingestion pipeline, chunking, hybrid search, RRF, citation verification, jurisdiction cascade |
| 5 | `docs/report/05_ocr_pipeline.md` | OCR two-path pipeline (QR + PaddleOCR), preprocessing, LLM extraction, PersonalData schema |
| 6 | `docs/report/06_form_fill_pipeline.md` | doc_filler.py + pdf_service.py, field mapping, LibreOffice conversion, field configs |
| 7 | `docs/report/07_database_schema.md` | All PostgreSQL tables with columns, types, constraints, foreign keys, ERD in Mermaid |
| 8 | `docs/report/08_api_surface.md` | All FastAPI endpoints: method, path, request, response, rate limiting |
| 9 | `docs/report/09_data_ingestion.md` | Legal document ingestion script, DOCUMENT_REGISTRY, chunking strategy, scope_coverage |
| 10 | `docs/report/10_frontend.md` | Next.js pages, components, Zustand stores, SSE streaming, form field configs |
| 11 | `docs/report/11_infrastructure.md` | Docker Compose services, Redis session model, MinIO storage, Alembic migrations |
| 12 | `docs/report/12_testing.md` | Test coverage, test file inventory, what is and isn't tested, benchmark system |
| 13 | `docs/report/13_deviations.md` | What changed from PROJECT_CONTEXT.md — features added, features removed, design decisions that diverged |
| 14 | `docs/report/14_limitations.md` | Known limitations, deferred architectural decisions (P1–P16 from PROJECT_CONTEXT.md status), what is out of scope |

---

## Instructions for the Reviewing Agent

### Before Starting

1. Read `docs/PROJECT_CONTEXT.md` in full — this is your baseline. Everything in the report that matches PROJECT_CONTEXT.md does not need to be re-explained; note it as "as designed." Everything that differs must be called out explicitly.
2. Read `docs/PROJECT_STATUS.md` versions from v3.49 onward — this is the changelog. The most recent entries describe the current state.
3. Create `docs/report/00_progress.md` immediately with an empty checklist of all 14 sections. Check off each section as you complete it.

### How to Work Through Each Section

For each section:
1. Read the relevant source files listed in that section's "Source Files" below
2. Write an accurate description of what you find — not what PROJECT_CONTEXT.md says
3. Write Mermaid diagrams for any pipeline or architecture visualization
4. Save the file immediately
5. Update `00_progress.md` to mark it complete
6. Proceed to the next section

### Mermaid Diagram Requirements

- Architecture diagrams: use `graph TD` or `graph LR`
- Pipeline flows: use `flowchart TD`
- Database ERD: use `erDiagram`
- Sequence diagrams (for request/response flows): use `sequenceDiagram`
- Do NOT use ASCII art, box-drawing characters, or markdown table-based diagrams for any architecture or flow visualization
- Each diagram must be in a fenced code block with the `mermaid` language tag

### What "Accurate" Means

- If a field exists in `AgentState` but is never set by any node, note it as "declared but unused"
- If a service is imported but the endpoint that calls it is stubbed, note it as "implemented but not wired to a live endpoint"
- If `PROJECT_CONTEXT.md` describes a behavior that the code does not implement, note it as "designed but not implemented"
- If the code implements something not in `PROJECT_CONTEXT.md`, note it as "implemented, not in design doc"
- Versions must come from actual files (`requirements.txt`, `package.json`), not from PROJECT_CONTEXT.md

---

## Section-by-Section Source Files

### Section 01 — System Overview
Read:
- `docs/PROJECT_CONTEXT.md` §1 (for the original vision statement)
- `docs/PROJECT_STATUS.md` (latest version entry for current state)
- `backend/app/main.py` (lifespan, middleware, CORS, rate limiting setup)
- `docker-compose.yml` (infrastructure topology)

Produce:
- System vision paragraph (1–2 paragraphs, accurate to current scope)
- Scientific contribution statement (verify it still holds — DAG dependency resolution + hierarchical jurisdiction)
- A Mermaid `graph LR` or `graph TD` of the system layers (frontend → backend → infrastructure)

### Section 02 — Technology Stack
Read:
- `backend/requirements.txt` (get actual pinned versions)
- `frontend/package.json` (get actual Next.js, React, Tailwind versions)
- `backend/app/config.py` (which LLM model is configured, which embedding backend)
- `backend/app/services/llm.py` (which SDK: Gemini or Anthropic, what model ID)

Produce:
- Full table: Layer | Technology | Actual Version | Status (implemented/partial/stub)
- Note the LLM backend: **Anthropic is the only active backend** — Gemini code may still exist in `LLMService` but is not the active path. Haiku was trialled in v3.76 but reverted. Verify the actual active model ID from `config.py` and `.env` (should be Claude Sonnet 4).
- Note how `LLM_BACKEND` env var controls backend selection and what the current default is

### Section 03 — Multi-Agent Pipeline
Read:
- `backend/app/agents/graph.py` — graph assembly, recursion_limit, node wiring
- `backend/app/agents/state.py` — every field in AgentState
- `backend/app/agents/node_registry.py` — NODE_REGISTRY, NODE_DEPENDENCIES, VALID_PLAN_STEPS
- `backend/app/agents/nodes/router.py` — RouterOutput schema, how execution_plan is set
- `backend/app/agents/nodes/enrichment.py` — two-condition guard, procedure_planner_fn call
- `backend/app/agents/nodes/plan_executor.py` — wave execution, MAX_PLAN_STEPS, asyncio.gather
- `backend/app/agents/nodes/synthesizer.py` — ALL synthesizer modes and their priority order
- `backend/app/agents/prompts/router_prompt.py` — RouterOutput fields, few-shot count

Produce:
- Mermaid flowchart of the full LangGraph topology (Entry → Router → Enrichment → PlanExecutor loop → Synthesizer → END)
- Table of all 4 true graph nodes with their inputs/outputs
- Table of all worker functions (rag_fn, ocr_fn, form_filler_fn) with inputs/outputs
- Full AgentState field inventory: field name | type | set by | read by
- List of ALL synthesizer modes with their trigger condition and priority order
- Description of the parallel wave execution model (NODE_DEPENDENCIES matrix)
- Router few-shot example count (check actual prompt file, not CLAUDE.md)

### Section 04 — RAG Pipeline
Read:
- `backend/app/services/qdrant_service.py` — full implementation: `search()`, `_dense_search()`, `_bm25_search()`, `_rrf_merge()`, `_active_filter()`, `_apply_token_budget()`, `_deduplicate_by_article()`, `_build_filter()`
- `backend/app/agents/nodes/rag.py` — `rag_fn`, query augmentation, scope cascade logic, `verify_citations()` call
- `backend/app/core/citation_formatter.py` — `verify_citations()`, `_ALT_CITATION_RE`, Điều + Mục/số/Phụ lục format handling
- `backend/app/core/jurisdiction.py` — `expand_scope_hierarchy()`
- `backend/app/agents/prompts/rag_prompt.py` — RAG system prompt, citation format instructions, markdown prohibition
- `backend/app/config.py` — `RAG_TOP_K`, `RAG_MIN_SCORE_THRESHOLD`, token budget constants

Produce:
- Mermaid flowchart of the query-time RAG pipeline (query → augmentation → scope cascade → dense search + BM25 → RRF → dedup → token budget → LLM → citation verify → output)
- Mermaid flowchart of the ingestion-time pipeline (document → chunking → embedding → Qdrant upsert)
- Description of the scope cascade fallback mechanism (most specific → broadest)
- Description of RRF merge formula and parameters
- Description of query augmentation (proportional scaling from v3.63)
- Description of citation verification (Điều format + alt format from v3.68)
- List of actual `RAG_TOP_K` value and `RAG_MIN_SCORE_THRESHOLD` value from config

### Section 05 — OCR Pipeline
Read:
- `backend/app/services/ocr_service.py` — full two-path pipeline
- `backend/app/agents/nodes/ocr.py` — `ocr_fn`, lazy singleton
- `backend/app/agents/prompts/document_classifier_prompt.py` — 5 categories
- `backend/app/agents/prompts/ocr_extraction_prompt.py` — SCHEMA_BLOCK, XML tag injection hardening
- `backend/app/schemas/personal_data.py` — PersonalData schema, Address schema, all fields

Produce:
- Mermaid flowchart of the OCR pipeline: two paths (QR path and PaddleOCR path)
- PersonalData schema field inventory
- Description of QR decode: format (7 fields split on `|`), pyzbar library, preprocessing attempts
- Description of PaddleOCR path: preprocessing steps (deskew, CLAHE, denoise), confidence filtering, LLM extraction
- Prompt injection hardening mechanisms

### Section 06 — Form Fill Pipeline
Read:
- `backend/app/services/doc_filler.py` — main form fill service (replaces PDFService for this flow)
- `backend/app/api/v1/forms.py` — `/fill` endpoint, request/response
- `backend/app/core/form_field_configs.py` — field configs for all 8 forms
- `frontend/src/data/formFieldConfigs.ts` — frontend equivalent
- `backend/app/agents/nodes/form_filler.py` — `form_filler_fn`, field mapping, cache check
- `backend/app/core/form_field_mapper.py` — LLM semantic mapping

Produce:
- Mermaid flowchart of the form fill pipeline (user uploads CCCD → OCR → PersonalData → field mapping → doc_filler.py → LibreOffice → PDF → download)
- List of all 8 forms with their template filenames and field counts (from `form_field_configs.py`)
- Description of how `doc_filler.py` differs from `pdf_service.py` (docx templates + LibreOffice conversion vs AcroForm)
- Description of the field cache mechanism (form_templates.fields JSONB)

### Section 07 — Database Schema
Read:
- `backend/alembic/versions/` — all migration files (read each one)
- `backend/app/models/` — all ORM model files
- `backend/app/schemas/` — Pydantic schemas (not the DB schema, but document for contrast)

Produce:
- Mermaid `erDiagram` covering ALL tables with their columns and foreign key relationships
- Table inventory: table name | purpose | primary key type | notable columns
- Note which tables have JSONB columns and what they store
- Note the `status` field pattern (active/superseded) on `legal_documents`
- Note the `scope_coverage` table if it exists in migrations

### Section 08 — API Surface
Read:
- `backend/app/api/v1/chat.py`
- `backend/app/api/v1/forms.py`
- `backend/app/api/v1/documents.py`
- `backend/app/api/v1/procedures.py`
- `backend/app/api/v1/legal.py`
- `backend/app/api/v1/feedback.py`
- `backend/app/main.py` (router registration, middleware)

Produce:
- Complete API endpoint table: Method | Path | Description | Rate Limited | Auth Required | Request Body | Response
- Note which endpoints are fully implemented vs stubbed
- Note the SSE streaming endpoint and its event format
- Note the `/api/v1/forms/fill` endpoint (LibreOffice PDF generation)
- Note the `/api/v1/feedback` endpoint

### Section 09 — Data Ingestion Pipeline
Read:
- `backend/ingestion/ingest_full_documents.py` — the active ingestion script
- `DOCUMENT_REGISTRY` within that file — all 19 documents, their metadata, location_scope, procedure_ids
- Note the chunking strategy: Điều/Khoản boundaries, fallback paragraph chunker, Phụ lục handling
- Note `scope_coverage` table updates during ingestion

Produce:
- Mermaid flowchart of the ingestion pipeline (source .doc/.pdf → LibreOffice conversion → text extraction → chunking → UUID5 dedup → embedding → Qdrant upsert → scope_coverage update)
- Full document registry table: document_number | title | location_scope | procedure_ids | domain
- Chunking rules: MAX chars, MIN chars, khoản number in article_number, Phụ lục handling
- Current Qdrant collection stats if determinable from code (904 points from v3.51)

### Section 10 — Frontend Architecture
Read:
- `frontend/src/app/` — all page files (list them)
- `frontend/src/components/chat/ChatWidget.tsx` — full implementation
- `frontend/src/lib/stores/` — all Zustand stores
- `frontend/src/lib/api/client.ts` — `streamChat()`, SSE event handling
- `frontend/src/data/formFieldConfigs.ts` — form field definitions
- `frontend/src/app/chat/page.tsx` — full-page chat
- `frontend/src/components/layout/Header.tsx` — PIN gate, navigation

Produce:
- Page inventory: path | component | description
- Mermaid flowchart of the SSE streaming flow (user sends message → client.ts → FastAPI → LangGraph → SSE events → ChatWidget state updates → render)
- Description of the `AgentActivityPanel`... wait, that doesn't exist yet (TASK-SHOWCASE). Note it as "planned but not implemented"
- Zustand store field inventory for chatStore, formStore, procedureStore
- Citation rendering description (renderWithCitations, hover tooltip, verified vs unverified)

### Section 11 — Infrastructure
Read:
- `docker-compose.yml` — all services, ports, volumes, env vars
- `backend/app/services/redis_service.py` — session model, TTL, encryption, compaction
- `backend/app/services/storage_service.py` — MinIO bucket, PRIVATE policy
- `backend/alembic/` — migration history

Produce:
- Docker Compose service inventory: service | image | port | purpose
- Redis session model: key structure, TTL, encryption scheme, compaction (from v3.45)
- MinIO bucket structure: bucket name, path prefixes (tmp/ vs final paths)

### Section 12 — Testing
Read:
- `backend/tests/unit/` — list all test files and their test counts
- `backend/scripts/benchmark/run_benchmark.py` — benchmark runner
- `backend/scripts/benchmark/datasets/` — dataset files

Produce:
- Test file inventory: filename | test count | what it covers
- Total test count (should be 366 at v3.79)
- Benchmark system description: what measurements exist, what datasets, how run
- Notable gaps: what is NOT covered by unit tests (integration, end-to-end)

### Section 13 — Deviations from PROJECT_CONTEXT.md
This section requires careful comparison. For each deviation, note:
- What PROJECT_CONTEXT.md says
- What the code actually does
- Why it changed (reference the PROJECT_STATUS.md version entry if possible)

Key known deviations to investigate and document (may not be exhaustive):

1. **LLM model**: PROJECT_CONTEXT.md says `claude-sonnet-4-20250514`. Code may use Haiku (v3.76) or Gemini.
2. **`doc_filler.py` vs `pdf_service.py`**: PROJECT_CONTEXT.md describes `PDFService` with AcroForm fill. Code has `doc_filler.py` using .docx templates + LibreOffice (document_draft feature was removed in v3.69).
3. **OCR Tesseract fallback**: PROJECT_CONTEXT.md lists Tesseract. Stack table says "Not used — actual fallback is PaddleOCR + LLM field extraction."
4. **`ingest_legal_docs.py` vs `ingest_full_documents.py`**: The active ingestion script is different from what PROJECT_CONTEXT.md describes.
5. **Router `location_scope` field**: PROJECT_CONTEXT.md does not describe this field in RouterOutput. It was added in v3.54.
6. **Conversation history compaction**: Added in v3.45 — not in PROJECT_CONTEXT.md.
7. **`domain` field in RouterOutput**: Added late in development — verify implementation against design doc.
8. **Any nodes that were designed but not implemented** (check against node_registry.py and graph.py).
9. **`document_draft` mode removed**: v3.69 — this entire intent/synthesizer mode was removed.
10. **PIN gate**: Not in PROJECT_CONTEXT.md — added in v3.44.
11. **Query augmentation in `_build_search_query()`**: Not in PROJECT_CONTEXT.md — added in v3.63.
12. **`_deduplicate_by_article()`** in QdrantService: Not in PROJECT_CONTEXT.md — added in v3.60.
13. **`strip_markdown()` in `text_utils.py`**: Not in PROJECT_CONTEXT.md — added in v3.59.
14. **Feedback endpoint**: Not in PROJECT_CONTEXT.md — added in v3.44.
15. Anything else discovered during the section-by-section review.

### Section 14 — Limitations and Deferred Work
Read:
- `docs/PROJECT_CONTEXT.md` §6 (P1–P16, Known Problems and Architectural Decisions)
- Verify which of P1–P16 are still deferred vs have been implemented

Produce:
- For each P1–P16: status (still deferred / partially addressed / implemented in vX.XX)
- Additional limitations found during the review that are NOT in P1–P16
- Out-of-scope items that should be acknowledged in the thesis

---

## Definition of Done

- [ ] `docs/report/00_progress.md` exists with all 14 sections checked off
- [ ] All 14 section files exist in `docs/report/`
- [ ] Every pipeline diagram is Mermaid code, not ASCII art
- [ ] Section 02 tech stack versions come from actual `requirements.txt` and `package.json`, not from PROJECT_CONTEXT.md
- [ ] Section 03 AgentState field inventory is complete — every field in `state.py` is documented
- [ ] Section 03 synthesizer modes are exhaustively listed — check `synthesizer.py` for every `if/elif` branch
- [ ] Section 07 ERD covers every table from every Alembic migration file
- [ ] Section 08 API surface marks each endpoint as "implemented" or "stub/partial"
- [ ] Section 13 deviations list is written from evidence in the code, not from memory
- [ ] No section contradicts another section (cross-check: agent pipeline section and API section must describe the same SSE flow)

---

## Hard Constraints

- **Write each section file immediately upon completion.** Do not hold content in memory across sections.
- **Update `00_progress.md` after each section.** If the session is interrupted mid-task, the progress file shows exactly where to resume.
- **All diagrams must be Mermaid.** If you find yourself writing `┌──────┐` or `│ node │`, stop and convert to Mermaid.
- **No speculation.** If a file doesn't exist, say it doesn't exist. If behavior is unclear from reading the code, say "unclear from static analysis — requires runtime verification." Do not infer behavior from comments or docstrings alone — read the implementation.
- **Do not modify any source files.** This task is read-only. The only files written are under `docs/report/`.
- **Do not run the backend or any scripts.** Static analysis only. Runtime state (actual Qdrant point count, actual Redis contents) should be noted as "from PROJECT_STATUS.md vX.XX" if referenced.
- **This task is a new Claude Code session.** Do not assume the reviewing agent has context from prior conversations. All context must come from reading the files listed.

---

## PROJECT_STATUS.md Update (Required on Completion)

When all 14 section files are written and `00_progress.md` is fully checked off, add a new version entry to `docs/PROJECT_STATUS.md` following the existing changelog format. The entry must include:
- That a comprehensive codebase review was completed
- The output location (`docs/report/`, 14 files)
- A one-line summary of the most significant deviation found from `PROJECT_CONTEXT.md`
- Current test count (do not run tests — use the count from the most recent PROJECT_STATUS.md entry)

This update is the final step. Do not skip it.
