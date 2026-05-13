# DichVuCong AI Assistant

**Tiếng Việt:** Cổng dịch vụ công hành chính Việt Nam tích hợp trợ lý AI hội thoại. Công dân mô tả nhu cầu, hệ thống xác định các thủ tục hành chính cần thực hiện (theo đúng thứ tự phụ thuộc), truy xuất cơ sở pháp lý liên quan, trích xuất thông tin cá nhân từ giấy tờ tùy thân, và điền tự động các mẫu tờ khai của chính phủ. Hỗ trợ ba lĩnh vực: cư trú (nhà ở), hộ tịch, và nuôi con nuôi. Hệ thống trích dẫn căn cứ pháp lý theo định dạng `[Điều X, Nghị định YYY/YYYY/NĐ-CP]` và xác minh từng trích dẫn trước khi trả về kết quả.

**English:** A mock Vietnamese government public administration portal with a conversational AI assistant. Citizens describe what they need to accomplish, and the system determines which administrative procedures are required (in DAG-topological order), retrieves the relevant legal basis, extracts personal data from identity documents, and pre-fills government form templates.

This is a university thesis project demonstrating that a single unified pipeline — LangGraph-orchestrated agents over a PostgreSQL procedure DAG, a Qdrant hybrid-search legal corpus, and a MinIO form-fill backend — is sufficient to handle both procedural dependency resolution and hierarchical jurisdiction scoping for Vietnamese administrative procedures. The architecture is validated across three domains: housing (nhà ở), civil registration (hộ tịch), and adoption (nuôi con nuôi).

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the System](#running-the-system)
- [User Guide](#user-guide)
- [Benchmark Suite](#benchmark-suite)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Known Limitations](#known-limitations)

---

## Architecture Overview

```
Next.js Frontend (port 3000)
        |
        | SSE stream / REST
        v
FastAPI Backend (port 8000)
        |
        +-- LangGraph Agent Pipeline
        |       router_node -> enrichment_node -> plan_executor (loop) -> synthesizer_node
        |       Worker functions (via NODE_REGISTRY): rag_fn, ocr_fn, form_filler_fn
        |
        +-- PostgreSQL (port 5432)   -- Procedure DAG, form templates, legal docs, sessions
        +-- Qdrant      (port 6333)  -- Legal document vectors (hybrid dense+BM25 search)
        +-- MinIO       (port 9000)  -- Uploaded identity documents, filled form PDFs
        +-- Redis       (port 6379)  -- Fernet-encrypted session storage, response cache
```

The agent pipeline decomposes every user message into an ordered `execution_plan: list[str]`. A `plan_executor` node drives worker functions through that plan via `NODE_REGISTRY`, accumulating results into a shared `AgentState` TypedDict. The `synthesizer_node` assembles the final response from all accumulated state at the end of each turn using one of eight priority-ordered response modes.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), Tailwind CSS, React Hook Form + Zod, Zustand (with `persist` middleware) |
| Backend | FastAPI (async), SQLAlchemy 2.0, Alembic (3 migrations), Python 3.12 |
| AI — Primary LLM | **Claude Sonnet 4 (`claude-sonnet-4-20250514`) via Anthropic SDK** — only active LLM backend |
| AI — Router (optional) | Ollama local LLM (`qwen2.5:3b-instruct`) via OpenAI-compatible endpoint — reduces API cost on router classification |
| AI — Orchestration | LangGraph (compiled graph, `recursion_limit=10`) |
| Embeddings | BAAI/bge-m3 (primary, 1024-dim, GPU auto-detect) or OpenAI `text-embedding-3-large` (fallback) |
| Vector DB | Qdrant — hybrid dense + BM25 search with Reciprocal Rank Fusion (RRF), scope-cascade retrieval |
| OCR | PaddleOCR PP-OCRv4 + OpenCV pre-processing; pyzbar QR fast-path (~200ms, confidence 1.0) |
| Form Fill | python-docx + LibreOffice headless (active path); pdfplumber/pdfrw/reportlab (AcroForm path, exists but not primary) |
| Document Parsing | Docling (IBM) — article-boundary chunking for Vietnamese legal text |
| Storage | MinIO (S3-compatible, private bucket) |
| Cache / Sessions | Redis with Fernet encryption, 3600s TTL, 6-turn history compaction |

---

## Prerequisites

- **Docker Desktop** (includes Compose v2) — version 24+ recommended
- **Python 3.12+**
- **Node.js 18+** (20 LTS recommended)
- **LibreOffice** — required for converting filled `.doc` form templates to PDF
- An **Anthropic API key** (`ANTHROPIC_API_KEY`) — required for all LLM-dependent features
- **Optional:** [Ollama](https://ollama.com/) with `qwen2.5:3b-instruct` pulled, to route the router node through a local model and reduce Anthropic API calls

For bge-m3 (default embedding model): a GPU with 2+ GB VRAM is recommended. The model also runs on CPU but the first embedding call after server start will take ~30–60 seconds. If your machine is constrained, switch to `EMBEDDING_BACKEND=openai` and supply `OPENAI_API_KEY`.

---

## Installation

### 1. Clone the repository

```powershell
git clone <repository-url>
cd dichvucong
```

### 2. Start infrastructure services

```powershell
docker compose up -d
```

This starts PostgreSQL (5432), Redis (6379), Qdrant (6333), and MinIO (9000) with the credentials in `docker-compose.yml`. Wait about 10 seconds for all services to be ready.

### 3. Set up the backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Apply all three database migrations:

```powershell
$env:PYTHONPATH = "."
alembic upgrade head
```

Seed the procedure graph (7 procedures across 3 domains with DAG dependency edges):

```powershell
$env:PYTHONPATH = "."
.venv\Scripts\python ingestion/ingest_procedures.py
```

Seed the administrative units lookup table (used for jurisdiction scoping):

```powershell
$env:PYTHONPATH = "."
.venv\Scripts\python ingestion/seed_administrative_units.py
```

### 4. Ingest legal documents

Run the full-document ingestion script. The script processes all 19 legal documents across the three domains, chunks them at article boundaries, embeds with bge-m3, and upserts into Qdrant. On first run bge-m3 downloads ~1.5 GB of model weights.

```powershell
$env:PYTHONPATH = "."
.venv\Scripts\python ingestion/ingest_full_documents.py
```

Expected output: **1,180 Qdrant points** across 19 documents. The script soft-supersedes any existing chunks for each document before upserting new ones, so it is safe to re-run.

> **Note:** Source documents live in `backend/data/legal_documents/` as `.doc` files. LibreOffice must be installed so the ingestion script can convert them to PDF for Docling parsing. If LibreOffice is not on your `PATH`, set `LIBREOFFICE_PATH` in your environment.

### 5. Set up the frontend

```powershell
cd frontend
npm install
```

---

## Configuration

Copy the example environment file and fill in the required values:

```powershell
Copy-Item .env.example .env
```

Open `.env`. The only value that **must** be changed for the system to function is the Anthropic API key. All other values have working defaults for the local Docker Compose environment.

```bash
# ── Required ──────────────────────────────────────────────────────────────────

# Anthropic Claude — the only active LLM backend
ANTHROPIC_API_KEY=sk-ant-...
LLM_BACKEND=anthropic
LLM_MODEL=claude-sonnet-4-20250514

# Redis session encryption (32-byte base64 Fernet key)
# Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
REDIS_ENCRYPTION_KEY=<your-fernet-key>

# ── Optional: Local LLM router via Ollama ─────────────────────────────────────
# Runs the router node through a local model — reduces Anthropic API calls by
# ~50% for workloads where most messages need routing but not RAG generation.
# Requires: ollama serve  &&  ollama pull qwen2.5:3b-instruct
ROUTER_LLM_BACKEND=local        # "anthropic" | "local"  (default: anthropic)
LOCAL_LLM_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=qwen2.5:3b-instruct

# ── Optional: LangSmith tracing ───────────────────────────────────────────────
LANGSMITH_API_KEY=
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=dichvucong

# ── Optional: Public access PIN gate ─────────────────────────────────────────
# Frontend PIN shown to users at /  (default: 2026)
NEXT_PUBLIC_ACCESS_PIN=2026

# ── Optional: Ngrok public tunnel ────────────────────────────────────────────
CORS_EXTRA_ORIGINS=https://<your-subdomain>.ngrok-free.app
NEXT_PUBLIC_API_URL_PUBLIC=https://<your-subdomain>.ngrok-free.app
```

All database URLs, MinIO credentials, Qdrant URL, CORS origins, and rate limits are pre-configured in `config.py` with defaults matching `docker-compose.yml` and do not need to be changed for local development.

---

## Running the System

```powershell
# 1. Start infrastructure
docker compose up -d

# 2. Start backend (in one terminal — from backend/ directory)
cd backend
$env:PYTHONPATH = "."
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

> **Note:** On first startup the bge-m3 model loads into GPU memory. Watch for `bge-m3 loaded device=cuda` in the server log before sending the first message. This takes about 60–90 seconds on a mid-range GPU. The `/health` endpoint returns HTTP 200 once the API is ready (the model load happens during the lifespan startup hook).

```powershell
# 3. Start frontend (in a separate terminal — from frontend/ directory)
cd frontend
npm run dev
```

| Service | URL |
|---|---|
| Frontend | `http://localhost:3000` |
| Backend API | `http://localhost:8000` |
| API docs (Swagger) | `http://localhost:8000/docs` |
| MinIO console | `http://localhost:9001` |

**PIN gate:** The frontend is protected by a PIN gate. The default PIN is `2026` (configurable via `NEXT_PUBLIC_ACCESS_PIN`).

---

## User Guide

### Procedure Domains

The system supports three domains with seven procedures total:

| Domain | Procedure | Path |
|---|---|---|
| Housing (cư trú) | Permanent residence registration — Đăng ký thường trú | `/thu-tuc/dang-ky-thuong-tru` |
| Housing | Temporary residence registration — Đăng ký tạm trú | `/thu-tuc/dang-ky-tam-tru` |
| Housing | Residence confirmation — Xác nhận thông tin cư trú | `/thu-tuc/xac-nhan-cu-tru` |
| Civil registration (hộ tịch) | Birth registration — Đăng ký khai sinh | `/thu-tuc/dang-ky-khai-sinh` |
| Civil registration | Extract copy — Cấp bản sao trích lục hộ tịch | `/thu-tuc/cap-ban-sao-trich-luc` |
| Adoption (nuôi con nuôi) | Domestic adoption — Nuôi con nuôi trong nước | `/thu-tuc/nhan-con-nuoi` |
| Adoption | Re-register adoption — Đăng ký lại việc nuôi con nuôi | `/thu-tuc/dang-ky-lai-nuoi-con-nuoi` |

### Chat Assistant

The chat assistant is accessible in two ways:

- **Floating widget:** available on every page via the button in the bottom-right corner.
- **Full-page chat:** navigate to `/chat` for a dedicated view with a sidebar and procedure progress bar.

**Example queries:**

```
Điều kiện để đăng ký thường trú theo Luật Cư trú hiện hành là gì?
Hồ sơ đăng ký tạm trú gồm những gì?
Lệ phí đăng ký khai sinh tại TP.HCM là bao nhiêu?
Điều kiện nhận con nuôi trong nước?
Tôi muốn đăng ký thường trú, cần làm gì trước?
```

The assistant cites every legal claim in the format `[Điều X, Nghị định YYY/YYYY/NĐ-CP]`. Each citation is verified server-side against the retrieved chunk payload — hallucinated citations are rewritten to `[unverified: ...]` before the response reaches the client.

### Guided Procedure Wizard

When you ask about a specific procedure (e.g. "tôi muốn đăng ký thường trú"), the assistant enters guided mode — a 4-step wizard:

1. **Intro** — explains what the procedure requires
2. **CCCD upload** — prompts you to upload your identity card
3. **Form filling** — extracts personal data and pre-fills the relevant form
4. **Complete** — provides the filled form for download

The wizard progress bar is shown in the chat header during guided mode.

### CCCD Upload and OCR

1. Click the paperclip icon in the chat input bar.
2. Select a CCCD (Citizen Identity Card) image — JPEG, PNG, or PDF, max 5 MB.
3. The system first attempts QR decode (~200ms, confidence 1.0). If the image has no machine-readable QR code it falls back to PaddleOCR + LLM field extraction.
4. Extracted data (name, date of birth, ID number, permanent address) is stored in your session and carried forward automatically into form fields.

### Jurisdiction Scoping

When asking about fees or specific local requirements, include your city to get locally-applicable regulations:

```
Lệ phí đăng ký khai sinh tại Hà Nội là bao nhiêu?
Lệ phí tại TP.HCM?
Lệ phí tại Đà Nẵng?
```

The system supports three city-specific regulation sets: TP.HCM (`VN-HCM`), Hà Nội (`VN-HN`), and Đà Nẵng (`VN-DN`).

### Session Persistence

Each browser tab maintains an independent session stored in `sessionStorage`. Sessions expire after 1 hour of inactivity (Redis TTL). Accumulated personal data and completed procedure state persist across page navigation within the same session but are cleared when the tab is closed.

---

## Benchmark Suite

The benchmark harness at `backend/scripts/benchmark/run_benchmark.py` measures four metrics against a live backend.

```powershell
cd backend
$env:PYTHONPATH = "."

# Run all four metrics
.venv\Scripts\python scripts/benchmark/run_benchmark.py

# Run a specific metric
.venv\Scripts\python scripts/benchmark/run_benchmark.py --metric router
.venv\Scripts\python scripts/benchmark/run_benchmark.py --metric citations
.venv\Scripts\python scripts/benchmark/run_benchmark.py --metric faithfulness
.venv\Scripts\python scripts/benchmark/run_benchmark.py --metric latency

# Label a comparison run (appended to the report filename)
.venv\Scripts\python scripts/benchmark/run_benchmark.py --metric faithfulness --backend-label anthropic
```

| Metric | Dataset | LLM calls | Description |
|---|---|---|---|
| Router Accuracy | `router_accuracy.json` (81 cases) | 1/case (router only) | Intent, domain, procedure_id, location_scope classification |
| Document Retrieval Recall@k | `retrieval_recall.json` (52 cases) | 0 | Recall@5 / @10 / @24 against ground-truth document–article pairs |
| Citation Faithfulness | `retrieval_recall.json` (52 cases) | 1/case (RAG only) | Verified vs unverified citations in LLM output; bypasses router via `/rag_direct` |
| Latency Baseline | Built-in queries (20 samples) | 2/query | End-to-end p50/p90/p95 by query type |

Reports are saved to `backend/scripts/benchmark/reports/` as both `.json` and `.md`.

**Cost tip:** Set `ROUTER_LLM_BACKEND=local` to use Ollama for router calls and eliminate the per-case router API cost. The faithfulness benchmark (`--metric faithfulness`) already bypasses the router entirely — only 1 RAG LLM call per case.

---

## Project Structure

```
dichvucong/
├── backend/
│   ├── app/
│   │   ├── api/v1/                    # Route handlers — thin (validate + call service only)
│   │   │   ├── chat.py                # SSE streaming, /classify, /rag_direct
│   │   │   ├── documents.py           # POST /upload, GET /download
│   │   │   ├── forms.py               # POST /fill, GET /configs/{procedure_id}
│   │   │   ├── legal.py               # GET /search (pure Qdrant, zero LLM)
│   │   │   ├── procedures.py
│   │   │   └── feedback.py
│   │   ├── agents/
│   │   │   ├── graph.py               # LangGraph compiled graph (recursion_limit=10)
│   │   │   ├── state.py               # AgentState TypedDict
│   │   │   ├── node_registry.py       # NODE_REGISTRY, NODE_DEPENDENCIES, VALID_PLAN_STEPS
│   │   │   ├── nodes/
│   │   │   │   ├── router.py          # router_node — sets execution_plan + plan_cursor=0
│   │   │   │   ├── enrichment.py      # enrichment_node — two-condition DAG pre-flight
│   │   │   │   ├── plan_executor.py   # plan_executor_node — wave execution via asyncio.gather
│   │   │   │   ├── synthesizer.py     # synthesizer_node — 8 response modes
│   │   │   │   ├── rag.py             # rag_fn — hybrid retrieval + cited generation
│   │   │   │   ├── ocr.py             # ocr_fn — QR-first + PaddleOCR pipeline
│   │   │   │   ├── procedure_planner.py # procedure_planner_fn — DB query + topo sort
│   │   │   │   └── form_filler.py     # form_filler_fn — field mapping + LibreOffice PDF
│   │   │   └── prompts/               # System prompts and message builders
│   │   ├── core/                      # Pure domain logic — zero infrastructure imports
│   │   │   ├── procedure_graph.py     # Kahn's topological sort, plan resolver
│   │   │   ├── citation_formatter.py  # verify_citations(), [unverified: ...] flagging
│   │   │   ├── form_field_configs.py  # Field configs for 8 form templates
│   │   │   ├── form_field_mapper.py   # LLM semantic mapper + DB cache
│   │   │   ├── jurisdiction.py        # expand_scope_hierarchy() — VN → VN-HCM → district
│   │   │   ├── session_accumulator.py # Confidence-wins PersonalData merge
│   │   │   ├── file_validator.py      # MIME/extension/size validation (pure Python)
│   │   │   └── text_utils.py          # strip_markdown() applied to all LLM output
│   │   ├── services/
│   │   │   ├── llm.py                 # LLMService — Anthropic (active) + Gemini + Ollama
│   │   │   ├── embedder.py            # bge-m3 (primary) / OpenAI (fallback), 1024-dim
│   │   │   ├── qdrant_service.py      # Hybrid search, RRF merge, active-status filter
│   │   │   ├── ocr_service.py         # QR decode + PaddleOCR + LLM field extraction
│   │   │   ├── doc_filler.py          # ACTIVE form fill: python-docx + LibreOffice PDF
│   │   │   ├── pdf_service.py         # AcroForm/overlay (exists; not the active path)
│   │   │   ├── redis_service.py       # Fernet-encrypted sessions, 6-turn compaction
│   │   │   └── storage_service.py     # MinIO upload/download/promote_tmp
│   │   ├── models/                    # SQLAlchemy ORM (UUID PKs, TIMESTAMPTZ)
│   │   └── schemas/                   # Pydantic v2 request/response schemas
│   ├── ingestion/
│   │   ├── ingest_full_documents.py   # ACTIVE — ingests all 19 documents (DOCUMENT_REGISTRY)
│   │   ├── ingest_targeted.py         # Re-ingests a subset of documents (after source update)
│   │   ├── ingest_procedures.py       # Seeds 7 procedures + DAG edges into PostgreSQL
│   │   ├── seed_administrative_units.py
│   │   └── domain_configs/            # Per-domain YAML: procedure→document article mappings
│   ├── alembic/versions/
│   │   ├── 0001_initial_schema.py     # 7 tables
│   │   ├── 0002_legal_doc_versioning.py  # superseded_by FK
│   │   └── 0003_domain_column.py      # domain column on procedures
│   ├── data/
│   │   ├── legal_documents/           # 19 source .doc legal files
│   │   ├── form_sources/              # 8 source .doc form templates
│   │   └── mock_documents/            # Synthetic CCCD images for testing
│   ├── scripts/
│   │   └── benchmark/
│   │       ├── run_benchmark.py       # 4-metric benchmark harness
│   │       └── datasets/
│   │           ├── router_accuracy.json    # 81 cases
│   │           └── retrieval_recall.json   # 52 cases (42 filtered + 10 unfiltered)
│   └── tests/
│       ├── unit/                      # 366 unit tests — all LLM calls mocked
│       └── integration/               # 8 integration tests — require Docker services
├── frontend/
│   └── src/
│       ├── app/                       # 10 portal pages + 7 procedure pages under /thu-tuc/
│       ├── components/
│       │   ├── chat/                  # ChatWidget (floating+inline), citation chips
│       │   ├── procedure/             # ProcedurePageLayout, ProcedureForm
│       │   ├── layout/                # Header, FloatingChatWidget
│       │   └── auth/                  # PinGate
│       └── lib/
│           ├── api/client.ts          # streamChat() SSE generator
│           ├── stores/                # chatStore, formStore, procedureStore (Zustand persist)
│           └── types/
├── docs/
│   ├── PROJECT_CONTEXT.md             # Architecture, design decisions, data models
│   └── PROJECT_STATUS.md              # Version log, task cards, DoD checklists
└── docker-compose.yml
```

---

## Running Tests

```powershell
cd backend
$env:PYTHONPATH = "."

# All unit tests (no infrastructure required — all LLM calls mocked)
.venv\Scripts\pytest tests/unit/ -v

# Integration tests (requires docker compose up -d)
.venv\Scripts\pytest tests/integration/ -m integration -v

# Unit tests only (exclude integration markers)
.venv\Scripts\pytest tests/ -v -m "not integration"
```

Current test count: **366 unit tests passing** across 34 test files.

---

## Known Limitations

- **bge-m3 cold start:** On first startup the embedding model loads into GPU memory. Watch for `bge-m3 loaded device=cuda` in the server log — this takes ~60–90 seconds on a mid-range GPU (e.g. GTX 1650 Ti). Do not send the first chat message until this line appears. Subsequent requests use the warm model (~200ms per embed).

- **GPU VRAM:** bge-m3 occupies ~2.3 GB of VRAM. If you also run Ollama for the local router, ensure your GPU has at least 4 GB total VRAM. On a 4 GB card (e.g. GTX 1650 Ti), bge-m3 and `qwen2.5:3b-instruct` can coexist but only if no other GPU-bound processes are running. `qwen2.5:7b-instruct` will not fit alongside bge-m3 on a 4 GB card and will fall back to CPU (~100s/inference).

- **LibreOffice required for form fill:** The active form-fill path (`doc_filler.py`) converts filled `.doc` templates to PDF via LibreOffice headless. If LibreOffice is not installed or not on `PATH`, form fill will fail silently. Install LibreOffice and ensure `soffice` is accessible from the backend's working directory.

- **Anthropic API is required:** The Gemini backend code exists in `LLMService` but is not actively used — `LLM_BACKEND=anthropic` is the only tested and production-ready path. All synthesis, RAG generation, OCR extraction, and form field mapping go through `claude-sonnet-4-20250514`.

- **OCR quality:** The QR decode path (for CCCD cards with a machine-readable QR code) is fast (~200 ms) and produces confidence 1.0 per field. The PaddleOCR fallback requires clear, well-lit images. Photos taken at an angle, in low light, or with motion blur will produce partial or incorrect extractions.

- **Legal correctness:** The system retrieves and cites text from Vietnamese legal documents using RAG. It does not guarantee legal accuracy. Cited provisions may be outdated if the underlying documents have not been re-ingested after a legislative update. Always verify administrative requirements with official government sources before acting on them.

- **Rate limits:** Chat is limited to 10 requests/minute per IP; document upload to 5 requests/minute. These are configurable via `CHAT_RATE_LIMIT` and `UPLOAD_RATE_LIMIT` in `.env`.
