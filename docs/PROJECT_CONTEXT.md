---
> This file contains project vision, system architecture, design decisions,
> technology stack, and feature roadmap. It changes rarely.
> For task progress, DoD checklists, and next actions, see PROJECT_STATUS.md.
---

# DichVuCong AI Assistant — System Context & Architecture

**Version 2.3 | Updated 2026-04-13**

> **What changed in v2.2:** P14 (MMR token diversity) and P15 (cross-encoder reranking) added to §6 as architectural considerations with explicit upgrade conditions. MMR note added to §2.3 RAG pipeline. Feature roadmap updated with token optimization features and cross-encoder condition clarified. Boilerplate removal, Docling hierarchy prefix, threshold-based stopping, and structured summary extraction added to roadmap.

> **What changed in v2.1:** Scientific contribution statement added to System Vision. Hierarchical jurisdiction architecture added as §2.6. AgentState updated with domain and filing_jurisdiction fields. Feature roadmap expanded for multi-domain scope. Known Problems and Architectural Decisions section added (P1–P13).

## Table of Contents
1. [System Vision](#1-system-vision)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Feature Roadmap](#4-feature-roadmap)
5. [Open Questions & Blockers](#5-open-questions--blockers)
6. [Known Problems & Architectural Decisions](#6-known-problems-and-architectural-decisions)

---

## 1. System Vision

DichVuCong AI Assistant is a mock Vietnamese government public administration portal that adds a conversational AI layer on top of an otherwise static service directory. The core problem it solves is **navigational complexity**: Vietnamese citizens must complete multiple interdependent administrative procedures in a specific order, and the legal basis for each step is scattered across dozens of decrees and circulars. Today, citizens either hire intermediaries or make repeated trips to government offices due to missing prerequisites. This system removes that friction.

The system is built around a **procedure dependency graph** (DAG) stored in PostgreSQL. All AI capabilities — RAG, OCR, and form auto-fill — exist to serve that graph: RAG answers legal questions about *why* a procedure requires certain documents, OCR extracts personal data from identity documents so it can be *carried forward* into form fields, and form fill automates the tedious transcription of data across multiple government PDF templates.

### Scientific Contribution

The system makes the following architectural claim, validated empirically:

**A single unified pipeline architecture is sufficient to handle both procedural dependency resolution (DAG-based) and hierarchical jurisdiction scoping (tree-based) for Vietnamese administrative procedures, and this architecture is domain-agnostic with respect to procedure type.**

This is validated by demonstrating one complete hierarchical branch (national → city → ward scope) per procedure domain across three domains: housing (nhà ở), civil registration (hộ tịch), and adoption (nuôi con nuôi). Each branch uses representative procedures. This demonstrates that scaling within a domain (adding more procedures) is a data and ingestion task, not an architectural change, and that scaling across domains requires only router prompt coverage and correctly tagged legal documents.

Additionally, the system validates DAG-based procedural dependency resolution in two of the three domains: within civil registration, TTHC-CR-002 (Cấp bản sao Trích lục hộ tịch) requires TTHC-CR-001 (Đăng ký khai sinh) per Điều 63–64 Luật Hộ tịch 2014; within adoption, TTHC-AD-002 (Đăng ký lại việc nuôi con nuôi trong nước) requires TTHC-AD-001 (Đăng ký việc nuôi con nuôi trong nước) per Điều 24 Nghị định 123/2015/NĐ-CP. This strengthens the scientific claim: DAG dependency resolution is validated across two independent procedure domains, not just one.

### Hierarchical Jurisdiction

Vietnamese administrative law operates at multiple geographic levels. A national decree sets the baseline rule. A Ho Chi Minh City circular may override it for city residents. A ward-level decision may further override it for ward residents. According to Luật Ban hành văn bản quy phạm pháp luật 2015, Điều 156, the narrower geographic scope always takes precedence. The system enforces this automatically through jurisdiction-scoped Qdrant filtering — the correct rule reaches the LLM without the LLM needing to adjudicate which jurisdiction applies.

### Current Scope

**Phase 1 (core demo — housing domain):**
Three residence registration procedures as the primary validation domain:
- Đăng ký thường trú (TTHC-001)
- Đăng ký tạm trú (TTHC-002)
- Xác nhận thông tin về cư trú (TTHC-003)

These three procedures, fully implemented end-to-end with hierarchical jurisdiction support at VN → VN-HCM → VN-HCM-[ward] scope, constitute the runnable demo. All multi-domain and scientific validation work begins after this demo is stable.

**Phase 2 (multi-domain validation — after Phase 1 demo complete):**
One or more representative procedures per additional domain, each with a full three-level hierarchical branch:
- Civil registration (hộ tịch): Đăng ký khai sinh (TTHC-CR-001), Cấp bản sao Trích lục hộ tịch (TTHC-CR-002)
- Adoption (nuôi con nuôi): Đăng ký việc nuôi con nuôi trong nước (TTHC-AD-001), Đăng ký lại việc nuôi con nuôi trong nước (TTHC-AD-002)

**Not in scope:** UI/UX design, full national ward coverage, production security hardening, legal correctness certification.

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
    # --- Routing (plan_executor topology) ---
    execution_plan: list[str]    # e.g. ["ocr_fn", "form_filler_fn"]
    plan_cursor: int             # incremented by plan_executor only
    entities: dict[str, Any]
    domain: str | None           # "housing"|"civil_registration"|
                                 # "adoption"|None
                                 # set by router, None = ambiguous
    filing_jurisdiction: str | None  # e.g. "VN-HCM-26968"
                                     # set by confirmed user input,
                                     # never by raw OCR alone
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

> **Note on Maximal Marginal Relevance (MMR):** MMR-based result diversification was evaluated as a candidate mechanism to reduce near-duplicate chunk retrieval within the 6,000-token context budget. It was deferred because article-boundary chunking produces naturally distinct chunks per article, making token budget exhaustion the primary bottleneck rather than content redundancy at current corpus size (< 500 chunks). The RRF merge already provides light diversity by combining dense and BM25 rankings. See P14 for the upgrade condition under which MMR should be revisited.

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

Residence procedure dependency edges (housing domain):
  → TTHC-003 (Xác nhận thông tin cư trú) requires TTHC-001 or TTHC-002
  → TTHC-001 (Đăng ký thường trú) may follow TTHC-002 under Luật Cư trú 2020 Điều 20
  → See Q4 resolution notes in Section 5

Civil registration procedure dependency edges:
  → TTHC-CR-002 (Cấp bản sao Trích lục hộ tịch) requires TTHC-CR-001 (Đăng ký khai sinh)
  → Legal basis: Điều 63–64 Luật Hộ tịch 2014 — a copy of a birth record can only be
    issued after the original birth event has been registered

Adoption procedure dependency edges:
  → TTHC-AD-002 (Đăng ký lại việc nuôi con nuôi trong nước) requires TTHC-AD-001
  → Legal basis: Điều 24 Nghị định 123/2015/NĐ-CP — re-registration only applies when
    the original adoption was previously registered and all records have since been lost
```

### 2.6 Hierarchical Jurisdiction Architecture

#### Scope Code Convention

Geographic jurisdiction is encoded as a hyphen-delimited hierarchy following ISO 3166-2 conventions extended to ward level:

- `VN` — national rule (applies everywhere)
- `VN-HCM` — Ho Chi Minh City rule (overrides VN for city residents)
- `VN-HCM-[code]` — ward-level rule (overrides VN-HCM for ward residents)

Where `[code]` is the official Ministry of Home Affairs administrative unit code (mã đơn vị hành chính), not the ward name string. Ward names are stored in the `administrative_units` PostgreSQL lookup table and resolved from OCR-parsed address strings via fuzzy matching.

#### Ancestor Chain Expansion

At query time, `rag_fn` calls `expand_scope_hierarchy()` from `app/core/jurisdiction.py` to build the full ancestor list before constructing the Qdrant filter:

```python
# app/core/jurisdiction.py
def expand_scope_hierarchy(scope: str) -> list[str]:
    parts = scope.split("-")
    return ["-".join(parts[:i+1]) for i in range(len(parts))]
# "VN-HCM-26968" → ["VN", "VN-HCM", "VN-HCM-26968"]
```

#### Cascade Fallback

`rag_fn` queries Qdrant in order from most specific to broadest scope, stopping when results are found. Each fallback level is logged. The `scope_used` metadata field is passed to the Synthesizer so the user sees which level of rules applied:

```
Query with ["VN", "VN-HCM", "VN-HCM-26968"]
  → Try VN-HCM-26968 first → results found? → use these
  → No results → try VN-HCM → results found? → use these + log fallback
  → No results → try VN → use these + log fallback
  → No results at any level → add to errors[]
```

User-facing message when fallback occurs: "Chưa tìm thấy quy định cấp phường — đang áp dụng quy định cấp thành phố."

#### Jurisdiction Determination

Filing jurisdiction (`filing_jurisdiction`) is a first-class field in `SessionData`, determined by procedure-driven confirmation — not by raw OCR output alone. When a user selects a procedure, the Synthesizer asks "Bạn đang nộp hồ sơ tại phường/xã nào?" and pre-fills the answer from the OCR-parsed address as a suggestion. The confirmed jurisdiction is stored separately from `PersonalData.permanent_address`.

`filing_jurisdiction` in `SessionData` is always set by explicit user action or confirmed OCR — never by raw OCR parsing alone.

#### Scope Coverage Tracking

The `scope_coverage` PostgreSQL table records which `(location_scope, procedure_id, domain)` combinations have been ingested. The ingestion script upserts a row on every ingest run. This table enables:
- Knowing which scopes are available before querying Qdrant
- Distinguishing "no ward rule exists" from "ward rule not ingested yet"
- Benchmark evaluation: skipping unavailable combinations rather than counting them as pipeline failures

```sql
scope_coverage (
    location_scope  VARCHAR(50),
    procedure_id    UUID REFERENCES procedures(id),
    domain          VARCHAR(50),
    chunk_count     INTEGER,
    last_ingested_at TIMESTAMPTZ,
    PRIMARY KEY (location_scope, procedure_id)
)
```

#### Domain Classification

Each procedure belongs to exactly one domain. Domain is a first-class column on the `procedures` table and a first-class field in `AgentState` and `SessionData`. The router extracts `domain` as a structured output field alongside `execution_plan` and `entities`. If domain is ambiguous from the query alone, the router sets `domain: None` and the Synthesizer asks for clarification.

Valid domain values: `"housing"`, `"civil_registration"`, `"adoption"`.

#### Ingestion Metadata Per Domain

`procedure_tags` assignment is driven by per-domain configuration files at `ingestion/domain_configs/[domain].yaml`. Each config explicitly maps procedure IDs to the legal document articles relevant to that procedure. This makes tagging auditable and reproducible — the ingestion script never infers tags automatically.

```yaml
# ingestion/domain_configs/housing.yaml
domain: housing
procedures:
  - id: "TTHC-001"
    name: "Đăng ký thường trú"
    relevant_documents:
      - document_number: "68/2020/QH14"
        relevant_articles: ["Điều 20", "Điều 21", "Điều 22"]
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
| **Vector DB** | Qdrant | latest (Docker) | ✅ Implemented & Running |
| **Cache / Sessions** | Redis | 7-alpine (Docker) | ✅ Implemented & Running |
| **Object Storage** | MinIO | latest (Docker) | ✅ Implemented & Running |
| **LLM Backbone** | Gemini (active) + Claude claude-sonnet-4-20250514 (primary, pending API key) | `google-genai` SDK + Anthropic SDK 0.85.0; dual-backend via `LLM_BACKEND` env var (`gemini`\|`anthropic`) | ✅ Implemented & Running (Gemini active; Anthropic pending ANTHROPIC_API_KEY) |
| **Embeddings** | bge-m3 (local) | sentence-transformers | ✅ Implemented & Running |
| **Agent Framework** | LangGraph | 1.1.2 | ✅ Implemented & Running |
| **OCR Engine** | PaddleOCR (primary) | PP-OCRv4 | ✅ Implemented & Running |
| **OCR Fallback** | Tesseract | 5.x | ❌ Not used — actual fallback path is PaddleOCR + LLM field extraction (never implemented Tesseract) |
| **PDF Processing** | pdfplumber + pdfrw | latest | ✅ Implemented & Running |
| **PDF Form Fill** | pdfrw + reportlab | latest | ✅ Implemented & Running |
| **Document Parsing** | Docling (IBM) | latest | ✅ Implemented & Running |
| **Image Processing** | OpenCV (cv2) | 4.x | ✅ Implemented & Running |
| **Observability** | LangSmith | via langchain | ⚙️ Implemented (wired in TASK-01; requires ANTHROPIC_API_KEY for Anthropic backend; not active on Gemini backend) |
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
| Cross-encoder reranker — implement only if TASK-18 Measurement 5 shows citation recall below 80% and root cause is confirmed as retrieval precision (see P15) | 4 | Enhancement |
| MMR result diversification — implement only if corpus exceeds 2,000 chunks AND citation recall below 80% AND root cause confirmed as redundant chunk selection (see P14) | 4 | Enhancement |
| Boilerplate removal before Docling parsing (regex cleanup of headers, footers, preamble) | 2 | Core |
| Docling hierarchy prefix on chunks (chapter/section context, no LLM call) | 2 | Core |
| Threshold-based stopping in _apply_token_budget() (min_score_threshold parameter) — current value 0.01; requires calibration against real retrieval data in TASK-18 (effective RRF range is 0.005–0.015 for k=60) | 3 | Core |
| Structured summary field in Qdrant payload (obligation/condition/consequence, offline) | 2 | Core |
| Hierarchical jurisdiction scope filtering (location_scope metadata) | 3 | Core |
| Ancestor chain expansion utility (expand_scope_hierarchy) | 3 | Core |
| Cascade fallback with scope_used metadata | 3 | Core |
| Administrative units lookup table (name → official code) | 3 | Core |
| Domain classification in router output | 3 | Core |
| Domain-diverse router few-shot examples (3 domains) | 3 | Core |
| scope_coverage tracking table | 3 | Core |
| Out-of-scope procedure validation in procedure_planner_fn | 2 | Core |
| verify_citations() format-agnostic chunk payload matching | 3 | Core |
| Multi-domain ingestion pipeline with domain_configs YAML | 4 | Core |
| Evaluation dataset — 3 domains, 3 tiers | 4 | Core |
| Benchmark suite — 8 measurements across all domains | 4 | Core |

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
| `procedure_dependencies` edges seeded (TTHC-003 → TTHC-001/002) | 0 | Core |
| Real Vietnamese legal PDFs collected | 2 | Core |
| Legal documents ingested into Qdrant (with `status: "active"` field) | 2 | Core |
| Blank PDF form templates collected/created | 3 | Core |
| Form templates uploaded to MinIO | 3 | Core |
| Synthetic CCCD mock images generated | 3 | Core |
| administrative_units lookup table seeded (test wards) | 3 | Core |
| domain_configs YAML files (3 domains) | 3 | Core |
| Civil registration legal documents (VN + VN-HCM + ward) | 4 | Core |
| Adoption legal documents (VN + VN-HCM + ward) | 4 | Core |
| One representative procedure per new domain seeded | 4 | Core |
| Evaluation dataset (labeled queries, citation ground truth) | 4 | Core |

---

## 5. Open Questions & Blockers

| # | Question / Blocker | Blocks | Resolution |
|---|---|---|---|
| **Q1** | Which Vietnamese legal PDFs to ingest? | TASK-05, TASK-06 | Collect Luật Cư trú 2020, Nghị định 62/2021/NĐ-CP, Nghị định 144/2021/NĐ-CP from thuvienphapluat.vn. Download today — non-code prerequisite. |
| **Q2** | Are real blank government PDF form templates available, or must we mock them? | TASK-08, TASK-15 | Create mock AcroForm PDFs using reportlab/pdfrw with realistic Vietnamese field names |
| **Q3** | ANTHROPIC_API_KEY not set in `.env` | TASK-01, all agent nodes | Add key to `backend/.env` before starting Phase 2 work |
| **Q4** | `procedure_dependencies` table is empty | TASK-09 | **Resolved (design):** TTHC-003 (Xác nhận thông tin cư trú) depends on TTHC-001 or TTHC-002. TTHC-001 may follow prior tạm trú under Luật Cư trú 2020 Điều 20. Seed edges in TASK-0B. |
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

---

## 6. Known Problems and Architectural Decisions

This section documents design problems identified during architecture review and the decisions made to address them. Each problem includes the chosen approach and the condition under which it should be upgraded.

### P1 — Jurisdiction signal reliability
OCR-parsed address cannot be the sole signal for filing jurisdiction. Address on CCCD reflects permanent residence, not filing location, and OCR confidence on address fields is not a proxy for address validity.

**Decision:** Procedure-driven confirmation. `filing_jurisdiction` is stored as a first-class `SessionData` field set by explicit user confirmation. OCR address pre-fills the suggestion only.

**Upgrade condition:** When OCR confidence on ward field is measurably above 0.90 for returning users with prior confirmed jurisdiction, skip confirmation silently.

### P2 — Silent failure on empty Qdrant results
If no documents are ingested for a given scope/procedure combination, Qdrant returns zero chunks and the system either hallucinates or produces an unexplained empty response.

**Decision:** Cascade fallback with explicit logging. Query from most specific scope to broadest. Surface `scope_used` to user. Add to `errors[]` if all scope levels return empty.

**Upgrade condition:** Once TASK-05 ingestion is complete, add `scope_coverage` table to replace cascade trial-and-error with a single lookup.

### P3 — LLM as primary jurisdiction arbiter
Asking the LLM to apply narrower-scope-wins across conflicting documents is unreliable and unverifiable.

**Decision:** Filter-first architecture. Qdrant filter handles primary jurisdiction selection. Prompt instruction is safety net only. Article-number deduplication added when two chunks from different scopes share the same `(article_number, document_number)` within the same `procedure_tag`.

**Implementation note (v3.3 bug fix):** The Qdrant payload field for jurisdiction scope is `location_scope` — not `scope`. All filter construction in `QdrantService._build_filter()` must use the field key `"location_scope"`. A filter built with `"scope"` silently returns no results — this was a critical silent bug present since TASK-05. Ingestion scripts must write `"location_scope"` into the Qdrant payload on every upsert. Scope filtering is now confirmed working end-to-end as of v3.3.

**Upgrade condition:** Build deduplication only after TASK-17 ingestion is complete and conflicts are observed in >10% of evaluation test cases.

### P4 — Missing ancestor chain computation
Qdrant filter requires a pre-computed ancestor list. No utility existed.

**Decision:** `expand_scope_hierarchy()` in `app/core/jurisdiction.py`. Pure Python, zero infrastructure dependencies, consistent with CLAUDE.md Rule 5.

**Upgrade condition:** Add validation against `administrative_units` table when scope code count exceeds ~20.

### P5 — Non-standardized ward codes
Ward names from OCR are ambiguous — "Phường Tân Hòa" exists in multiple cities. Name-based codes are not stable across administrative boundary changes.

**Decision:** Official Ministry of Home Affairs administrative unit codes as canonical identifiers. `administrative_units` PostgreSQL lookup table maps names ↔ codes. OCR-parsed name → fuzzy match → official code.

**Upgrade condition:** Add common abbreviation expansion ("P." → "Phường", "Q." → "Quận", "X." → "Xã") if clean match rate on real OCR output falls below 90%.

### P6 — Out-of-scope procedure validation
If a user requests a procedure not in the database, `procedure_planner_fn` returns an empty plan silently. `rag_fn` returns empty chunks silently. Neither surfaces a useful error.

**Decision:** Two-layer validation. Layer 1 in `procedure_planner_fn`: existence check, return named error if zero DB results. Layer 2 in `rag_fn`: check for empty chunks after filtering, add to `errors[]` if empty.

**Upgrade condition:** Once three domains are seeded, add supported procedures registry query at session initialization so the Synthesizer can redirect users proactively rather than failing at query time.

### P7 — Router prompt domain bias
8 few-shot examples, all housing domain. Router accuracy on non-housing queries is untested and likely degraded.

**Decision:** Add 4 domain-diverse examples per new domain before any multi-domain testing. Measure router accuracy per domain against a labeled query set of ~20 queries per domain (Measurement 6).

**Upgrade condition:** If router accuracy on any domain falls below 85% after adding examples, add domain selection at session start as a UX pattern rather than relying on router classification.

### P8 — procedure_tags assignment inconsistency across domains
Tags inferred automatically may be wrong for non-housing domains. Wrong tags make chunks unretrievable in filtered search silently.

**Decision:** Per-domain YAML configuration files at `ingestion/domain_configs/[domain].yaml` explicitly map procedure IDs to relevant document articles. Ingestion script reads config — never infers tags automatically.

**Upgrade condition:** If procedure count exceeds 50, add LLM-assisted draft tagging at ingestion time with human review before marking chunks `status: "active"`.

### P9 — verify_citations() citation format variation
Housing decrees use `[Điều X, Nghị định YYY/YYYY/NĐ-CP]`. Luật uses `[Điều X, Luật YYY năm YYYY]`. Older circulars use `[Khoản X, Điều Y, Thông tư Z]`. Format-specific regex produces false positives and false negatives on non-housing domains.

**Decision:** Refactor `verify_citations()` to match against chunk payload `(article_number, document_number)` pairs, not against citation string format. Format-agnostic matching works correctly across all document types.

**Upgrade condition:** None — this refactor should be completed before TASK-17 multi-domain ingestion, not after.

### P10 — Missing domain classification in data model
No `domain` concept in procedures table, AgentState, or SessionData. Without it, multi-domain disambiguation is impossible and the scope_coverage table cannot be keyed correctly.

**Decision:** `domain` column added to `procedures` table in Alembic migration 0003. `domain` field added to `AgentState` and `SessionData`. Router extended to output `domain` as a structured field.

**Upgrade condition:** If domain count exceeds 10, replace string column with foreign key to a `domains` metadata table.

### P11 — Scope coverage gaps during active development
During TASK-17, coverage is partial. Test failures are ambiguous — pipeline bug or data gap cannot be distinguished without a coverage map.

**Decision:** `scope_coverage` table built as part of TASK-16, not as a later upgrade. Ingestion script upserts coverage rows on every run. Benchmark evaluation queries coverage table first and skips unavailable combinations rather than counting them as failures.

### P12 — Cross-domain router confusion on ambiguous queries
"Đăng ký" appears in housing, civil registration, and adoption. Without domain context, router may misclassify intent.

**Decision:** Router outputs `domain: str | None`. When None, Synthesizer asks for clarification before proceeding. Domain stored in `SessionData` for session lifetime after first disambiguation.

**Upgrade condition:** If domain count exceeds 5, add explicit domain selection at session start as primary mechanism, reducing reliance on router classification.

### P13 — Evaluation dataset construction methodology
Self-labeled ground truth risks circular validation. Need explicit methodology distinguishing what requires legal expertise from what does not.

**Decision:** Three-tier ground truth structure.
- Tier 1 (self-labelable): router intent, scope selection correctness — deterministic given procedure definition.
- Tier 2 (document-verifiable): citation ground truth — manually verified against source legal documents, 10 pairs per domain.
- Tier 3 (requires external validation): legal correctness of guidance — explicitly noted as outside research prototype scope.

Presentation must state clearly which metrics belong to which tier.

### P14 — Token diversity in retrieved context (MMR)

With article-boundary chunking, multiple chunks from closely related articles (e.g. Điều 20 and Điều 21 of the same decree) may be returned in the same retrieval, consuming disproportionate budget on near-duplicate content. Maximal Marginal Relevance (MMR) re-scores candidates by penalizing similarity to already-selected chunks, trading relevance for diversity.

⚠️ CONSIDERATION ONLY — DO NOT IMPLEMENT until upgrade condition is met.

**Decision:** Deferred. At current corpus size (< 500 chunks across 4 documents), article-boundary chunking produces naturally distinct chunks. Budget exhaustion caused by near-duplicate selection has not been observed in evaluation. The RRF merge already provides light diversity by combining dense and BM25 rankings.

**Upgrade condition:** Implement MMR if: (a) corpus exceeds 2,000 chunks AND (b) TASK-18 Measurement 5 shows citation recall below 80% AND (c) root cause is confirmed as redundant chunk selection, not embedding quality or generation failures.

### P15 — Retrieval precision for low-frequency article queries (cross-encoder)

Cross-encoder rerankers improve retrieval precision by jointly encoding query and candidate passage, but require an additional inference call per candidate and add ~200–500ms latency. For Vietnamese legal queries, dense + BM25 RRF already handles article-number exact-match queries (the primary failure mode of semantic-only search). Cross-encoder adds cost without addressing the known failure modes at current scale.

⚠️ CONSIDERATION ONLY — DO NOT IMPLEMENT until upgrade condition is met.

**Decision:** Deferred. The current hybrid retrieval (dense + BM25 RRF) is the correct baseline for Vietnamese legal text. Cross-encoder overhead is not justified until retrieval precision is measured as the bottleneck.

**Upgrade condition:** Implement cross-encoder reranking only if TASK-18 Measurement 5 (citation recall) is below 80% AND root cause analysis confirms the failure is retrieval precision (wrong chunks returned), not generation quality (correct chunks returned but LLM fails to cite). See §4 Feature Roadmap.

### P16 — Document authority hierarchy not modeled

Vietnamese normative documents operate on a two-dimensional hierarchy:
(1) geographic scope (VN → VN-HCM → VN-HCM-[ward]) — already
implemented in the system, and (2) document authority level defined
by Luật Ban hành văn bản quy phạm pháp luật 2015, from highest to
lowest: Hiến pháp → Luật/Bộ luật → Pháp lệnh → Nghị định → Quyết
định Thủ tướng → Thông tư. These two axes are orthogonal — a Thông
tư at national scope and a Luật at national scope are treated as
peers in the current retrieval architecture.

Within each geographic scope level, the system currently retrieves
chunks from all document authority levels with equal weight. When a
Nghị định and a Thông tư contain complementary provisions for the
same procedure, this is correct behavior (they are not in conflict).
When they conflict (which occurs during policy transitions), the LLM
must adjudicate without structural guidance — an unreliable mechanism
for legal accuracy.

**Decision:** Deferred. At current corpus size and scope (housing,
civil registration, adoption domains with non-conflicting document
sets), all ingested documents for a given procedure are complementary
rather than conflicting. The Luật sets principles, the Nghị định
elaborates, the Thông tư specifies procedural details. No conflict
has been observed.

**Upgrade condition:** Add a `document_authority_level` integer field
to the Qdrant payload (1=Hiến pháp, 2=Luật/Bộ luật, 3=Pháp lệnh,
4=Nghị định, 5=Quyết định Thủ tướng, 6=Thông tư/Thông tư liên tịch)
if TASK-18 evaluation reveals conflicting provisions being retrieved
simultaneously for the same procedure at the same geographic scope.
Until conflict is observed in evaluation, the current flat retrieval
within a scope level is correct for complementary document sets.

**Note for thesis:** The scientific contribution addresses geographic
jurisdiction hierarchy (tree-based) and procedural dependency
resolution (DAG-based). Document authority hierarchy is a third
structure that exists in Vietnamese administrative law and is
explicitly noted as outside the current research scope. Any
presentation must acknowledge this limitation.
