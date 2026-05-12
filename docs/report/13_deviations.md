# Section 13 — Deviations from PROJECT_CONTEXT.md

PROJECT_CONTEXT.md is version 2.3 (last updated 2026-04-13). The codebase is at v3.81. This section documents systematic differences between what the design document describes and what the code actually implements, with the PROJECT_STATUS.md version entry for each change where known.

---

## D1 — LLM Backend: Gemini Listed as Active, Anthropic Listed as Pending

**PROJECT_CONTEXT.md says**: "Gemini (active) + Claude claude-sonnet-4-20250514 (primary, pending API key)"; `LLM_BACKEND=gemini` as default.

**Code does**: `LLM_BACKEND=anthropic` is the default in `config.py`. Anthropic (`claude-sonnet-4-20250514`) is the ONLY active backend. Gemini code exists in `LLMService` but is not the active path. `ROUTER_LLM_BACKEND` defaults to `"anthropic"`. A third `"local"` backend (Ollama via OpenAI-compat API) was added in v3.81 for router-only use.

**Version**: Anthropic became primary around v3.26. Haiku trialled in v3.76, reverted. Local LLM added in v3.81.

---

## D2 — Form Fill: AcroForm PDF → python-docx + LibreOffice

**PROJECT_CONTEXT.md says**: "PDF AcroForm fill + overlay fallback" as the active form fill mechanism. References `PDFService` with pdfrw + reportlab as the production path.

**Code does**: The active form fill path is `doc_filler.py` — fills `.docx` templates via python-docx, then converts to PDF via LibreOffice headless. `pdf_service.py` (AcroForm + reportlab) exists, is tested, but is NOT called by `form_filler_fn` or `POST /api/v1/forms/fill`. The switch happened in v3.29 when `.docx` templates replaced AcroForm PDFs.

**Impact**: All 8 form templates are `.docx` files. `form_templates.fields` JSONB (designed for the LLM semantic mapper) is populated by `form_filler_fn` using `cccd_source` static mapping — not by calling `FormFieldMapper.map()`.

---

## D3 — OCR Fallback: Tesseract Not Implemented

**PROJECT_CONTEXT.md says**: Tech stack table lists "Tesseract 5.x" as OCR fallback.

**Code does**: No Tesseract implementation exists anywhere in the codebase. No `import pytesseract` in any file. The actual structure is: QR decode (Path A, zero LLM) → PaddleOCR + LLM extraction (Path B). PROJECT_CONTEXT.md's own tech stack table already notes "Not used — actual fallback path is PaddleOCR + LLM field extraction."

---

## D4 — Ingestion Script: Docling Replaced by pdfplumber + Custom Chunker

**PROJECT_CONTEXT.md says**: "Docling parser (article hierarchy extraction)" as the primary ingestion approach. Also references `ingest_legal_docs.py`.

**Code does**: The active ingestion script is `ingest_full_documents.py`. Text extraction uses pdfplumber (`.pdf`), python-docx (`.docx`), and LibreOffice conversion for `.doc` files. No Docling call in `ingest_full_documents.py`. `docling==2.5.0` is installed in `requirements.txt` but not imported in any active ingestion path. The custom `chunk_document()` function implements Điều/Khoản-boundary splitting directly.

**Version**: `ingest_full_documents.py` replaced the older script during multi-domain expansion work.

---

## D5 — Router Output: `location_scope` Field Added Post-Design

**PROJECT_CONTEXT.md says**: RouterOutput fields: `execution_plan`, `entities`, `intent`, `procedure_id`. No `location_scope` field.

**Code does**: `RouterOutput` includes `location_scope: str | None` — added in v3.54. Valid values: `{"VN-HCM", "VN-HN", "VN-DN"}` (coerced to None if not in this set). The `location_scope` from the router is used in the RAG scope cascade as a secondary signal alongside `filing_jurisdiction`.

---

## D6 — History Compaction: LLM Path Added But Not Active by Default

**PROJECT_CONTEXT.md says**: "Conversation history in AgentState holds at most the last 6 turns. Older turns are dropped."

**Code does**: `RedisService._compact_history()` (v3.45) summarizes older turns into a synthetic assistant message rather than dropping them. Two paths: (1) LLM-based Vietnamese summary (1-3s latency, opt-in), (2) plain concatenation fallback (< 1ms, currently used in production). The `llm_service` parameter is always `None` in `save_session()` — the LLM path is never invoked in the default pipeline. PROJECT_CONTEXT.md predates this feature.

---

## D7 — `document_draft` Mode Removed

**PROJECT_CONTEXT.md**: Does not explicitly mention `document_draft` mode (this was added and removed during v3.x development).

**Code does**: `document_draft` synthesizer mode was removed entirely in v3.69. The current 8 synthesizer modes do not include it. This is not a deviation FROM the design doc but a feature added-then-removed that is absent from both places.

---

## D8 — PIN Gate Not in Design

**PROJECT_CONTEXT.md says**: No mention of authentication or access control.

**Code does**: A PIN gate (`PinGate` component, `NEXT_PUBLIC_ACCESS_PIN=2026`) wraps the root layout. Added in v3.44. It is a demo/dev access control mechanism, not production authentication.

---

## D9 — Query Augmentation Not in Design

**PROJECT_CONTEXT.md says**: No mention of query augmentation for short queries.

**Code does**: `_build_search_query()` in `rag_fn` (v3.63) prepends context from the last assistant response to queries with fewer than 10 words. Augmentation size scales linearly from ~450 chars (0-word query) to ~50 chars (9-word query). Augmentation targets the Qdrant search query only — the raw user message is passed unchanged to the LLM.

---

## D10 — Per-Article Deduplication Not in Design

**PROJECT_CONTEXT.md says**: RRF merge → top_k results. No deduplication step mentioned.

**Code does**: `_deduplicate_by_article()` (v3.60) runs after RRF sorting and before the `[:top_k]` slice. Keeps only the highest-scoring chunk per `(article_number, document_number)` pair to prevent paragraph-split duplicates from flooding the top-K context window.

---

## D11 — `strip_markdown()` Not in Design

**PROJECT_CONTEXT.md says**: No mention of server-side markdown stripping.

**Code does**: `strip_markdown()` from `app/core/text_utils.py` (v3.59) is applied to ALL LLM-generated responses in `synthesizer_node` and `rag_fn` before writing to `final_response`. This is a two-layer system: (1) prompts forbid markdown formatting, (2) server-side stripping as a safety net.

---

## D12 — Feedback Endpoint Not in Design

**PROJECT_CONTEXT.md says**: No mention of a feedback collection endpoint.

**Code does**: `POST /api/v1/feedback` (v3.44) appends `{session_id, message_id, feedback, timestamp}` to `backend/data/feedback.jsonl`. Append-only, never fails the response on write error.

---

## D13 — Zustand Version: v4 vs v5

**PROJECT_CONTEXT.md says**: "Zustand 4.x".

**Code does**: `package.json` has `"zustand": "^5.0.0"`. The `createJSONStorage` API changed between v4 and v5 — the current code uses the v5 API. This is a version upgrade, not a behavioral change.

---

## D14 — LangGraph Version: Design Doc vs requirements.txt

**PROJECT_CONTEXT.md says**: "LangGraph 1.1.2".

**Code does**: `requirements.txt` has `langgraph==0.2.28`. The design doc appears to reference a planned or aspirational version; the actual installed version is 0.2.28, which is from the 0.2.x branch. This is a significant version discrepancy that may affect API compatibility with future code.

---

## D15 — `recursion_limit` at Compile vs Invocation Time

**CLAUDE.md says**: "Graph compiled with `recursion_limit=10`".

**Code does**: `graph.compile()` in `graph.py` does NOT pass `recursion_limit`. The limit is set at invocation time: `agent_graph.astream_events(initial_state, config={"recursion_limit": 10}, version="v2")` in `chat.py`. Functionally equivalent in practice.

---

## D16 — `domain_configs` YAML Not Used in Active Ingestion

**PROJECT_CONTEXT.md says**: "Per-domain YAML configuration files at `ingestion/domain_configs/[domain].yaml` explicitly map procedure IDs to relevant document articles. Ingestion script reads config — never infers tags automatically."

**Code does**: `ingest_full_documents.py` hardcodes `procedure_ids` directly in `DOCUMENT_REGISTRY` (a Python dict in the script). The YAML config approach described in the design doc is not implemented in the active script. The `ingestion/domain_configs/` directory exists but its YAML files are not consumed by `ingest_full_documents.py`.

---

## D17 — `status` Field NOT Written by Active Ingestion Script

**PROJECT_CONTEXT.md says**: Legal documents ingested with `status: "active"` field in Qdrant payload. `QdrantService.search()` always filters `status = "active"`.

**Code does**: `ingest_full_documents.py` does NOT write a `status` field to the Qdrant payload. The upserted point dict contains: `document_number`, `document_name`, `domain`, `location_scope`, `procedure_tags`, `article_number`, `khoan_number`, `content`. No `status` key. The `QdrantService._active_filter()` method creates a `must` condition for `status == "active"`. Points without a `status` key may be filtered OUT depending on Qdrant's handling of missing payload fields — requires runtime verification to confirm.

This is a potentially significant gap between the described architecture and the implementation.

---

## D18 — `structured_summary` Field Always Null

**PROJECT_CONTEXT.md says**: "Structured summary field in Qdrant payload (obligation/condition/consequence, offline)" as a Feature Roadmap item.

**Code does**: `structured_summary` is described in section comments but is NOT written by `ingest_full_documents.py`. PROJECT_STATUS.md v3.5 notes "all chunks have structured_summary: null". The field appears in the design docs and in `rag_fn` token budget code (which reads `chunk.structured_summary` as a fallback when token budget is near-exhausted), but is never populated.

---

## D19 — AgentActivityPanel and Pipeline SSE Events Not in Design

**PROJECT_CONTEXT.md says**: No mention of pipeline event streaming or AgentActivityPanel.

**Code does**: `schemas/pipeline_events.py` defines 10 event types. `chat.py` emits these events over SSE as each LangGraph node completes. `AgentActivityPanel.tsx` renders a real-time timeline. Added in v3.80 (TASK-SHOWCASE).

---

## D20 — Celery Task Queue: Listed as Planned, Not Implemented

**PROJECT_CONTEXT.md says**: "Celery + Redis — Celery 5.4 — ⚙️ Partially set up".

**Code does**: No Celery code exists in the codebase. `celery` does not appear in `requirements.txt`. No task definitions, no worker files, no broker configuration. This feature was never started.

---

## D21 — `sessions` PostgreSQL Table Not Used as Session Store

**PROJECT_CONTEXT.md says**: Sessions stored in Redis (TTL, encrypted). The `sessions` table is defined.

**Code does**: The `sessions` table is used ONLY by `POST /api/v1/forms/submit` to store form submission metadata in `form_fill_state` JSONB — not for actual session storage. All actual session reads/writes go through `RedisService`. The `sessions` table is effectively repurposed as a form submissions log (without a dedicated `form_submissions` table). This is noted in `forms.py` as "a temporary measure."

---

## D22 — `form_field_mapper.py` Not Called in Live Pipeline

**PROJECT_CONTEXT.md says** (CLAUDE.md): "FormFieldMapper.map() makes an LLM call. After the first successful mapping for a given form_id, store the resolved mapping in the form_templates.fields JSONB column."

**Code does**: `form_filler_fn` uses the static `cccd_source` mapping from `form_field_configs.py` to fill fields. `FormFieldMapper` is implemented and tested but is NOT called in the active pipeline. `form_templates.fields` JSONB is unpopulated in production.

---

## Summary Table

| # | Area | Design Says | Code Does |
|---|---|---|---|
| D1 | LLM Backend | Gemini active | Anthropic only |
| D2 | Form Fill | AcroForm PDFService | doc_filler.py + LibreOffice |
| D3 | OCR Fallback | Tesseract | Not implemented; PaddleOCR+LLM is the only non-QR path |
| D4 | Ingestion | Docling + ingest_legal_docs.py | pdfplumber/python-docx + ingest_full_documents.py |
| D5 | RouterOutput | No location_scope | location_scope added (v3.54) |
| D6 | History | Trim to 6 | Compact older turns into summary (v3.45) |
| D7 | Synthesizer | N/A | document_draft mode removed (v3.69) |
| D8 | Auth | None | PIN gate added (v3.44) |
| D9 | RAG Query | No augmentation | Proportional augmentation (v3.63) |
| D10 | RAG Dedup | No dedup | Per-article deduplication (v3.60) |
| D11 | Markdown | No mention | strip_markdown() added (v3.59) |
| D12 | Feedback | No mention | POST /api/v1/feedback added (v3.44) |
| D13 | Zustand | v4 | v5 |
| D14 | LangGraph | 1.1.2 | 0.2.28 |
| D15 | recursion_limit | compile() | astream_events() config |
| D16 | domain_configs | YAML-driven tagging | Hardcoded in DOCUMENT_REGISTRY |
| D17 | Qdrant status | status=active written | NOT written by active script |
| D18 | structured_summary | Planned | Always null |
| D19 | Pipeline events | None | 10 SSE event types (v3.80) |
| D20 | Celery | "Partially set up" | Never implemented |
| D21 | sessions table | Session store | Only used for form submission metadata |
| D22 | FormFieldMapper | LLM mapper with DB cache | Not called; static cccd_source used instead |
