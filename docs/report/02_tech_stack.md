# Section 02 — Technology Stack

All versions are taken from `backend/requirements.txt` and `frontend/package.json` — not from PROJECT_CONTEXT.md.

## 2.1 Full Technology Stack

| Layer | Technology | Actual Version | Status |
|---|---|---|---|
| **Frontend Framework** | Next.js (App Router) | 14.2.14 | Implemented |
| **Frontend Language** | TypeScript | ^5 | Implemented |
| **Frontend Styling** | Tailwind CSS | ^3.4.1 | Implemented |
| **Frontend Forms** | React Hook Form | ^7.53.0 | Implemented |
| **Frontend Validation** | Zod | ^3.23.8 | Implemented |
| **Frontend State** | Zustand | ^5.0.0 | Implemented |
| **Frontend Components** | Radix UI (dropdown, tabs, dialog, select, tooltip) | ^2.x / ^1.x | Implemented |
| **Frontend Icons** | Lucide React | ^0.453.0 | Implemented |
| **Frontend SSE** | eventsource-parser | ^2.0.1 | Implemented |
| **Frontend PDF** | react-pdf | ^9.1.1 | Installed, not prominently used in active UI |
| **Frontend Charts** | recharts | ^2.12.7 | Installed |
| **API Framework** | FastAPI | 0.115.0 | Implemented |
| **ASGI Server** | uvicorn[standard] | 0.30.6 | Implemented |
| **ORM** | SQLAlchemy 2.0 (async) | 2.0.35 | Implemented |
| **Async PostgreSQL driver** | asyncpg | 0.29.0 | Implemented |
| **DB Migrations** | Alembic | 1.13.2 | Implemented (3 migrations) |
| **Sync PostgreSQL driver** | psycopg2-binary | 2.9.9 | Implemented (integration tests) |
| **Redis client** | redis[hiredis] | 5.0.8 | Implemented |
| **Task Queue** | Celery | 5.4.0 | Installed — not used in live pipeline; dormant infrastructure |
| **Primary LLM** | Anthropic Claude (claude-sonnet-4-20250514) | anthropic==0.34.2 | **Active — default backend** |
| **Secondary LLM** | Google Gemini (gemini-2.5-flash-lite) | google-genai>=1.7.0 | Implemented but inactive (LLM_BACKEND=anthropic default) |
| **Local LLM** | Ollama (qwen2.5:3b-instruct) | openai==1.54.3 (compat) | Implemented for router node only via ROUTER_LLM_BACKEND=local; requires Ollama running |
| **Agent Framework** | LangGraph | 0.2.28 | Implemented |
| **Agent Tracing** | LangSmith | 0.1.129 | Implemented (wired in LLMService.__init__; inactive when LANGSMITH_API_KEY empty) |
| **LangChain** | langchain / langchain-anthropic | 0.3.1 / 0.2.1 | Installed (LangGraph dependency) |
| **Embeddings (primary)** | bge-m3 via FlagEmbedding | sentence-transformers==3.1.1, FlagEmbedding==1.2.11 | Implemented — 1024-dim, CUDA auto-detect |
| **Embeddings (fallback)** | OpenAI text-embedding-3-small | openai==1.54.3 | Implemented — inactive when EMBEDDING_BACKEND=bge-m3 |
| **BM25** | rank-bm25 | 0.2.2 | Implemented |
| **Vector DB** | Qdrant | qdrant-client[fastembed]==1.11.1 | Implemented (~905 points) |
| **Relational DB** | PostgreSQL | 16-alpine (Docker) | Implemented |
| **Cache/Sessions** | Redis | 7-alpine (Docker) | Implemented |
| **Object Storage** | MinIO | latest (Docker) | Implemented |
| **OCR Engine** | PaddleOCR PP-OCRv4 | paddleocr==2.8.1, paddlepaddle==2.6.1 | Implemented |
| **QR Decode** | pyzbar | 0.1.9 | Implemented (requires libzbar0 system library) |
| **Image Processing** | OpenCV (headless) | opencv-python-headless==4.10.0.84 | Implemented |
| **OCR Fallback** | Tesseract | — | **Never implemented** — PROJECT_CONTEXT.md listed it; actual fallback is PaddleOCR + LLM extraction |
| **PDF Read** | pdfplumber | 0.11.4 | Implemented |
| **PDF Read (alt)** | pypdf | 4.3.1 | Installed |
| **PDF Write (AcroForm)** | pdfrw | 0.4 | Implemented in pdf_service.py (not the active form-fill path) |
| **PDF Overlay** | reportlab | 4.2.2 | Implemented in pdf_service.py (not the active form-fill path) |
| **Doc Templates (active)** | python-docx | 1.1.2 | Implemented — active form-fill path via doc_filler.py |
| **PDF Conversion** | LibreOffice headless (soffice) | System dependency | Implemented — doc_filler.py calls soffice for .docx → PDF |
| **Document Parsing** | Docling (IBM) | 2.5.0 | Installed — referenced in PROJECT_CONTEXT.md; actual ingestion uses pdfplumber + manual Điều-boundary chunker |
| **Rate Limiting** | slowapi | 0.1.9 | Implemented |
| **File Validation** | python-magic / python-magic-bin | 0.4.27 / 0.4.14 | Installed; replaced by pure-Python magic byte detection in file_validator.py (avoids Windows DLL crash) |
| **Encryption** | cryptography (Fernet) | 43.0.1 | Implemented — Redis session encryption |
| **Validation** | pydantic / pydantic-settings | 2.9.2 / 2.5.2 | Implemented |
| **HTTP Client** | httpx | 0.27.2 | Implemented (integration tests) |
| **Logging** | structlog | 24.4.0 | Implemented |
| **Containerization** | Docker Compose | v2 (3.9 schema) | Implemented |

## 2.2 LLM Backend Architecture

The LLM backend is controlled by two environment variables:

```
LLM_BACKEND=anthropic           # "anthropic" | "gemini" — used by all nodes except router
ROUTER_LLM_BACKEND=anthropic    # "anthropic" | "local" — router-specific override (v3.81)
```

**Active configuration:**
- `LLM_MODEL=claude-sonnet-4-20250514` — all LLM calls except router when ROUTER_LLM_BACKEND=local
- `GEMINI_MODEL=gemini-2.5-flash-lite` — present in config, inactive unless LLM_BACKEND=gemini
- `LOCAL_LLM_MODEL=qwen2.5:3b-instruct` — active only when ROUTER_LLM_BACKEND=local

**History:** Gemini was the active backend in early development (v2.x). Anthropic became the default in Phase 2. Haiku (claude-haiku-4-5-20251001) was trialled briefly in v3.76 for latency improvement but reverted. Local Ollama support added in v3.81 for the router node only.

**Backend switch history:**
- v3.0 and earlier: Gemini active, Anthropic pending API key
- v3.x (current): Anthropic active (`claude-sonnet-4-20250514`)
- v3.76: Temporary Haiku trial — reverted
- v3.81: Local (Ollama) backend added for router, off by default

## 2.3 Notable Version Observations

- **Zustand v5.0.0** (not v4.x as stated in PROJECT_CONTEXT.md) — breaking changes from v4 were handled
- **LangGraph 0.2.28** — older than current 1.x series; `astream_events(version="v2")` API used for pipeline event streaming (v3.80)
- **anthropic==0.34.2** — SDK version matches Claude Sonnet 4 API support
- **docling==2.5.0** — installed but the active ingestion script (`ingest_full_documents.py`) uses pdfplumber + manual Điều-boundary chunker, not Docling
- **Celery==5.4.0** — installed but not wired into any live pipeline path; Redis response cache in RedisService is also dormant infrastructure (implemented but not called)
- **python-magic**: installed but not used in production code — `file_validator.py` uses pure-Python magic byte detection to avoid Windows DLL crash
