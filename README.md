# DichVuCong AI Assistant

A mock Vietnamese government public administration portal with a conversational AI assistant. Citizens describe what they need to accomplish, and the system determines which administrative procedures are required, in what order, retrieves the relevant legal basis, extracts personal data from identity documents, and pre-fills government PDF forms.

The system is a university thesis project demonstrating that a single unified pipeline architecture is sufficient to handle both procedural dependency resolution (DAG-based) and hierarchical jurisdiction scoping (tree-based) for Vietnamese administrative procedures.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the System](#running-the-system)
- [User Guide](#user-guide)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)

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
        |       Router -> enrichment_node -> plan_executor (loop) -> Synthesizer
        |       Worker functions: rag_fn, ocr_fn, form_filler_fn
        |
        +-- PostgreSQL (port 5432)   -- Procedure DAG, form templates, sessions
        +-- Qdrant      (port 6333)  -- Legal document vectors (hybrid search)
        +-- MinIO       (port 9000)  -- Uploaded files, filled PDFs
        +-- Redis       (port 6379)  -- Encrypted session storage, response cache
```

The agent pipeline decomposes every user message into an ordered execution plan. A `plan_executor` node drives worker functions through that plan, accumulating results into a shared `AgentState`. The Synthesizer node assembles the final response from all accumulated state at the end of each turn.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), Tailwind CSS, React Hook Form + Zod, Zustand |
| Backend | FastAPI, SQLAlchemy 2.0 (async), Alembic, Python 3.12 |
| AI | Claude claude-sonnet-4-20250514 / Gemini 2.5 Flash (switchable), LangGraph |
| Embeddings | bge-m3 (primary, 1024-dim) or OpenAI text-embedding-3-large (fallback) |
| Vector DB | Qdrant -- hybrid dense + BM25 search with Reciprocal Rank Fusion |
| OCR | PaddleOCR + OpenCV pre-processing, pyzbar QR decode path |
| PDF | pdfplumber (AcroForm detection), pdfrw (fill), reportlab (overlay) |
| Document parsing | Docling (IBM) -- article-boundary chunking |
| Storage | MinIO (S3-compatible) |
| Cache / Sessions | Redis with Fernet encryption |

---

## Prerequisites

- Docker and Docker Compose
- Python 3.12+
- Node.js 20+
- An Anthropic API key **or** a Google AI API key

For the bge-m3 embedding model (default): at least 4 GB of free RAM. If your machine is constrained, switch to `EMBEDDING_BACKEND=openai` and supply an `OPENAI_API_KEY`.

---

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd dichvucong
```

### 2. Start infrastructure services

```bash
docker compose up -d
```

This starts PostgreSQL, Redis, Qdrant, and MinIO with the credentials defined in `docker-compose.yml`. Wait about 10 seconds for all services to be ready.

### 3. Set up the backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

Apply database migrations:

```bash
alembic upgrade head
```

Seed the procedure graph (3 residence procedures + dependency edges):

```bash
python ingestion/ingest_procedures.py
```

### 4. Ingest legal documents

The legal documents must be in PDF format. If you have the source `.doc` files, convert them first:

```bash
libreoffice --headless --convert-to pdf data/legal_documents/*.doc --outdir data/legal_documents/
```

Then run the ingestion script:

```bash
python ingestion/ingest_legal_docs.py
```

This chunks documents at article boundaries, embeds them with bge-m3, and upserts them into Qdrant with `status: active`.

### 5. Set up the frontend

```bash
cd frontend
npm install
```

---

## Configuration

Copy the example environment file and fill in your API keys:

```bash
cp .env.example .env
```

Open `.env` and set the following. Everything else has working defaults for local development.

```bash
# Required -- pick one LLM backend

# Option A: Anthropic
LLM_BACKEND=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Option B: Google Gemini
LLM_BACKEND=gemini
GOOGLE_API_KEY=AIza...
GEMINI_MODEL=gemini-2.5-flash

# Required -- embeddings
# Leave as bge-m3 unless you want to use OpenAI embeddings
EMBEDDING_BACKEND=bge-m3
# OPENAI_API_KEY=sk-...   # only needed if EMBEDDING_BACKEND=openai

# Optional -- LangSmith tracing (Anthropic backend only)
LANGSMITH_API_KEY=
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=dichvucong
```

All other values (database URLs, Redis password, MinIO credentials, CORS origins) are pre-configured for the local Docker Compose environment and do not need to be changed for local development.

---

## Running the System

### Backend

```bash
cd backend

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive API docs are at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:3000`.

---

## User Guide

### Chat Assistant

The chat assistant is accessible in two ways:

- **Floating widget**: available on every page via the button in the bottom-right corner.
- **Full-page chat**: navigate to `/chat` for a dedicated chat view with a procedure plan panel on the right.

**What you can ask:**

- Legal questions about residence registration procedures:
  - "Toi can nhung giay to gi de dang ky thuong tru?"
  - "Dieu kien de dang ky tam tru la gi?"
- Procedure guidance:
  - "Toi muon dang ky thuong tru, can lam gi truoc?"
- Upload a CCCD image and the assistant will extract your personal data and offer to pre-fill the relevant form fields.

The assistant cites every legal claim in the format `[Dieu X, Nghi dinh YYY/YYYY/ND-CP]`, linked to the retrieved source chunk.

### Document Upload and OCR

1. Click the paperclip icon in the chat input bar.
2. Select a CCCD (Citizen Identity Card) image -- JPEG, PNG, or PDF, maximum 5 MB.
3. The system attempts QR decode first (fast path, ~200ms, confidence 1.0). If the image has no machine-readable QR code, it falls back to PaddleOCR + LLM field extraction.
4. Extracted personal data (name, date of birth, ID number, address) is stored in your session and carried forward automatically into form fields for the rest of the session.

### Residence Registration Forms

Three form pages are available under `/thu-tuc/`:

| Page | Path |
|---|---|
| Permanent residence registration | `/thu-tuc/dang-ky-thuong-tru` |
| Temporary residence registration | `/thu-tuc/dang-ky-tam-tru` |
| Residence confirmation | `/thu-tuc/xac-nhan-cu-tru` |

Each form supports both manual input and AI-assisted fill. If you have uploaded a CCCD in the same session, click "Tu dong dien" (Auto-fill) to populate fields from the extracted data. Fields with a confidence score below 0.8 are highlighted for manual review.

### Session Persistence

Each browser tab maintains an independent session identified by a `session_id` stored in `localStorage`. Sessions expire after 1 hour of inactivity. Accumulated personal data and completed procedure state persist across page navigation within the same session.

---

## Project Structure

```
dichvucong/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Route handlers (thin -- validation + service call only)
│   │   ├── agents/          # LangGraph graph, state, nodes, prompts
│   │   │   ├── nodes/       # router, enrichment, plan_executor, synthesizer
│   │   │   │                # Worker fns: rag, ocr, form_filler, procedure_planner
│   │   │   └── prompts/     # System prompts and message builders
│   │   ├── core/            # Pure domain logic -- no infrastructure imports
│   │   │   ├── procedure_graph.py   # Kahn's topological sort, plan resolver
│   │   │   ├── form_field_mapper.py # LLM semantic field mapping
│   │   │   └── file_validator.py    # MIME/extension/size validation
│   │   ├── services/        # Infrastructure wrappers
│   │   │   ├── llm.py           # Anthropic + Gemini backends
│   │   │   ├── embedder.py      # bge-m3 / OpenAI embeddings
│   │   │   ├── qdrant_service.py # Hybrid search, RRF merge, active filter
│   │   │   ├── ocr_service.py   # QR decode + PaddleOCR pipeline
│   │   │   ├── pdf_service.py   # AcroForm fill + overlay
│   │   │   ├── redis_service.py # Encrypted session storage
│   │   │   └── storage_service.py # MinIO upload/download
│   │   ├── models/          # SQLAlchemy ORM models (UUID PKs, TIMESTAMPTZ)
│   │   └── schemas/         # Pydantic v2 request/response schemas
│   ├── ingestion/           # Offline scripts
│   │   ├── ingest_procedures.py  # Seeds procedure DAG into PostgreSQL
│   │   └── ingest_legal_docs.py  # Chunks, embeds, and upserts legal PDFs
│   ├── alembic/versions/    # Database migrations -- never modify a committed one
│   ├── data/
│   │   ├── legal_documents/ # Source legal PDFs (not committed)
│   │   └── form_templates/  # Blank government PDF forms (not committed)
│   └── tests/
│       ├── unit/            # Pure unit tests -- all LLM calls mocked
│       └── integration/     # Integration tests -- require running infrastructure
├── frontend/
│   └── src/
│       ├── app/             # Next.js App Router pages
│       ├── components/      # Chat widget, forms, document upload, UI primitives
│       └── lib/             # API client, Zustand stores, TypeScript types
├── docs/
│   ├── PROJECT_CONTEXT.md   # Architecture, design decisions, tech stack
│   └── PROJECT_STATUS.md    # Version log, task cards, DoD checklists
└── docker-compose.yml
```

---

## Running Tests

### Unit tests (no infrastructure required)

```bash
cd backend
pytest tests/unit/ -v
```

### Integration tests (requires Docker Compose services running)

```bash
pytest tests/integration/ -v -m integration
```

To run only unit tests and exclude integration tests:

```bash
pytest tests/ -v -m "not integration"
```

Current test count: 271 unit tests passing.
