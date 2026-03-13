# DichVuCong AI Assistant — Architecture Blueprint
**Version 1.0 | Full-Stack AI / RAG / Multi-Agent System**

---

## Table of Contents

1. [Philosophy & Design Constraints](#1-philosophy--design-constraints)
2. [Complete Tech Stack](#2-complete-tech-stack)
3. [System Architecture Overview](#3-system-architecture-overview)
4. [Core Domain Model: Administrative Procedures](#4-core-domain-model-administrative-procedures)
5. [RAG Pipeline Architecture](#5-rag-pipeline-architecture)
6. [OCR & Multimodal Document Pipeline](#6-ocr--multimodal-document-pipeline)
7. [Multi-Agent Orchestration](#7-multi-agent-orchestration)
8. [Agentic Form Auto-Fill Pipeline](#8-agentic-form-auto-fill-pipeline)
9. [Project Directory Structure](#9-project-directory-structure)
10. [Database Schema](#10-database-schema)
11. [Phased Implementation Roadmap](#11-phased-implementation-roadmap)
12. [Key Architectural Decisions (ADRs)](#12-key-architectural-decisions-adrs)

---

## 1. Philosophy & Design Constraints

### Core Priorities (in order)
1. **Correctness of procedural logic** — the dependency graph between administrative forms is the most critical data structure in the system.
2. **Traceability** — every answer must cite a real legal document (Decree, Circular, Decision).
3. **Agentic autonomy** — the system should be able to navigate multi-step form chains without user hand-holding.
4. **Multimodal grounding** — document images are first-class inputs, not an afterthought.
5. **Frontend** — functional, not beautiful.

### Non-Goals (for this blueprint)
- Production-grade auth / e-signature (use mocked sessions)
- Real submission to government APIs
- Multi-tenancy

---

## 2. Complete Tech Stack

### Frontend
| Layer | Tool | Rationale |
|---|---|---|
| Framework | Next.js 14 (App Router) | SSR for SEO, API routes for lightweight proxying |
| Styling | Tailwind CSS | Utility-first, fast iteration |
| Forms | React Hook Form + Zod | Schema-driven validation, critical for form auto-fill mapping |
| State | Zustand | Lightweight, avoids Redux boilerplate |
| File Upload | react-dropzone | Handles ID card / doc image uploads |
| PDF Preview | react-pdf | Render filled PDFs in-browser |

### Backend / API
| Layer | Tool | Rationale |
|---|---|---|
| API Framework | FastAPI | Async-native, automatic OpenAPI docs, Pydantic model validation |
| Task Queue | Celery + Redis | Offload OCR and embedding jobs from request thread |
| Object Storage | MinIO (local S3-compatible) | Store uploaded images and generated PDFs |
| Relational DB | PostgreSQL | Procedure graph, form schemas, session state |
| ORM | SQLAlchemy 2.0 (async) | Async-compatible, type-safe with Pydantic |
| Cache | Redis | Session cache, LLM response cache |

### AI / ML
| Layer | Tool | Rationale |
|---|---|---|
| LLM Backbone | Claude claude-sonnet-4-20250514 (Anthropic API) | Best-in-class long-context reasoning, native vision |
| Embedding Model | `text-embedding-3-large` (OpenAI) or `bge-m3` (local) | bge-m3 supports Vietnamese natively — prefer for legal docs |
| Vector DB | Qdrant | Rust-based, fast, supports payload filtering (by decree type, year) |
| OCR Engine | **PaddleOCR** (primary) + **Tesseract** (fallback) | PaddleOCR has best Vietnamese language support |
| PDF Processing | **pdfplumber** + **pypdf2** | pdfplumber for text extraction with layout, pypdf2 for field detection |
| PDF Form Fill | **pdfrw** + **reportlab** | pdfrw reads/writes AcroForm fields; reportlab for custom overlays |
| Agent Framework | **LangGraph** | Stateful agent graphs, explicit node/edge control, better than LangChain LCEL for dependency resolution |
| Document Parsing | **Docling** (IBM) | State-of-the-art structured extraction from official PDF documents |

### Infrastructure
| Tool | Purpose |
|---|---|
| Docker Compose | Local orchestration of all services |
| Alembic | PostgreSQL migration management |
| Pytest | Backend testing |
| Pydantic v2 | Shared data contracts between API layers |

---

## 3. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         NEXT.JS FRONTEND                            │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  Chat UI    │  │ Form Builder │  │  Document Upload/Preview │  │
│  └──────┬──────┘  └──────┬───────┘  └────────────┬─────────────┘  │
└─────────┼────────────────┼──────────────────────┼─────────────────┘
          │                │  REST / SSE           │
┌─────────▼────────────────▼──────────────────────▼─────────────────┐
│                        FASTAPI BACKEND                              │
│                                                                     │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐    │
│  │ /chat        │  │ /procedure    │  │ /document            │    │
│  │ (streaming)  │  │ (CRUD + graph)│  │ (upload/OCR/fill)    │    │
│  └──────┬───────┘  └───────┬───────┘  └──────────┬───────────┘    │
│         │                  │                      │                 │
│  ┌──────▼──────────────────▼──────────────────────▼─────────────┐ │
│  │                    AGENT ORCHESTRATOR (LangGraph)              │ │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────┐  ┌──────────┐ │ │
│  │  │  Router    │  │  RAG Agent │  │OCR Agent │  │Form Agent│ │ │
│  │  │  Agent     │  │            │  │          │  │          │ │ │
│  │  └────────────┘  └─────┬──────┘  └────┬─────┘  └────┬─────┘ │ │
│  └────────────────────────┼──────────────┼──────────────┼────────┘ │
│                           │              │              │           │
│  ┌────────────────┐  ┌────▼──────┐  ┌───▼────┐  ┌─────▼──────┐   │
│  │  PostgreSQL    │  │  Qdrant   │  │ MinIO  │  │  Redis     │   │
│  │  (procedures, │  │  (vectors)│  │(files) │  │  (cache,   │   │
│  │   form graph) │  │           │  │        │  │   queue)   │   │
│  └────────────────┘  └───────────┘  └────────┘  └────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Request Lifecycle (Chat Query)
```
User sends: "I need to register a newborn child"
  │
  ▼
Router Agent classifies intent
  │ → "procedure_inquiry" with entities: ["birth_registration"]
  ▼
RAG Agent retrieves legal context from Qdrant
  │ → Fetches chunks from Nghị định 123/2015/NĐ-CP (civil registration)
  ▼
Procedure Resolver queries PostgreSQL
  │ → Identifies required forms + prerequisite chain
  │   Form A (birth cert) → depends on → Form B (hospital declaration)
  ▼
LLM synthesizes response with citations
  │
  ▼
User receives: Structured answer + list of forms + cited legal basis
```

---

## 4. Core Domain Model: Administrative Procedures

This is the most critical part of the system. Administrative procedures are modeled as a **Directed Acyclic Graph (DAG)** in PostgreSQL.

### Conceptual Model

```
ProcedureCategory (e.g., "Hộ tịch", "Đất đai", "Doanh nghiệp")
    └── Procedure (e.g., "Đăng ký khai sinh")
            ├── requires → [Procedure, Procedure, ...]   (dependency edges)
            ├── produces → [DocumentType, ...]           (outputs)
            ├── requires_documents → [DocumentType, ...] (input docs)
            └── forms → [FormTemplate, ...]              (fillable PDFs)

FormTemplate
    ├── fields → [FormField, ...]    (field name, type, source mapping)
    └── pdf_template_path           (stored in MinIO)

FormField
    ├── field_name: str
    ├── field_type: enum (text, date, checkbox, signature)
    ├── source: enum (ocr_extraction, user_input, derived, carry_forward)
    └── carry_from_procedure_id     (if source = carry_forward)
```

### Procedure Dependency Resolution

When a user asks to complete Procedure X, the system must:

1. **Topologically sort** the dependency subgraph rooted at X.
2. Identify which prerequisite procedures the user has already completed (via session state).
3. Present the user with an **ordered execution plan** — a checklist of procedures to complete in sequence.
4. **Carry forward** data extracted from earlier procedures/documents into later forms (e.g., the full name extracted from an ID card populates every subsequent form automatically).

**Example dependency chain:**
```
Procedure: Đăng ký khai sinh (Birth Registration)
  └── requires: Giấy chứng sinh (Birth Declaration from hospital)
        └── requires: CCCD of mother (document type, not procedure)
              └── requires: Đăng ký thường trú (Residency Registration) [if not yet done]
```

The system resolves this and tells the user: "To register a birth, you first need X, Y, Z."

---

## 5. RAG Pipeline Architecture

### 5.1 Document Ingestion Pipeline

```
[Raw Legal PDF/DOC]
      │
      ▼
  Docling Parser
  ├── Extracts: article hierarchy, table structure, enumerations
  ├── Preserves: article numbers, cross-references
  └── Output: structured JSON with semantic sections
      │
      ▼
  Chunking Strategy (CRITICAL for legal docs)
  ├── Primary: Article-boundary chunking (never split mid-article)
  ├── Secondary: Sliding window for preamble/general clauses
  └── Metadata attached per chunk:
      ├── document_id, document_type (Decree/Circular/Law)
      ├── issuing_authority, issue_date, effective_date
      ├── article_number, chapter_number
      └── procedure_tags [ ] (linked to PostgreSQL procedures)
      │
      ▼
  bge-m3 Embedding (multilingual, 1024-dim)
      │
      ▼
  Qdrant Collection: "legal_documents"
  ├── Vector: embedding
  └── Payload: all metadata above (used for filtered search)
```

### 5.2 Retrieval Strategy

Simple top-k cosine similarity is insufficient for legal text. Use a **hybrid retrieval** approach:

```python
# Pseudo-code for retrieval
def retrieve(query: str, procedure_id: str | None, top_k: int = 8):
    
    # Step 1: Semantic search
    semantic_results = qdrant.search(
        query_vector=embed(query),
        limit=top_k * 2,
        query_filter=Filter(
            must=[FieldCondition(key="procedure_tags", match=procedure_id)]
        ) if procedure_id else None
    )
    
    # Step 2: BM25 keyword search (sparse)
    bm25_results = bm25_index.search(query, top_k=top_k * 2)
    
    # Step 3: Reciprocal Rank Fusion
    final_results = rrf_merge(semantic_results, bm25_results, top_k=top_k)
    
    # Step 4: Rerank with cross-encoder (optional, adds latency)
    return rerank(query, final_results) if len(final_results) > top_k else final_results
```

**Key design decisions:**
- BM25 is critical for legal text (article numbers, decree IDs are exact-match queries).
- Filter by `procedure_tags` first to constrain the search space when context is known.
- Never retrieve from a single query — decompose complex questions into sub-queries.

### 5.3 Generation with Citations

The LLM is prompted with a strict citation format:

```
SYSTEM:
You are a Vietnamese administrative procedure assistant. Answer only based on
provided context. For every legal claim, cite the exact article using the format:
[Điều X, Nghị định/Thông tư YYY/YYYY/NĐ-CP]. If context is insufficient, say so.

CONTEXT:
[Retrieved chunks with metadata]

USER QUERY:
[Question]

RESPONSE FORMAT:
{
  "answer": "...",
  "citations": [{"doc_id": "...", "article": "Điều X", "excerpt": "..."}],
  "required_procedures": ["procedure_id_1", ...],
  "confidence": "high|medium|low"
}
```

---

## 6. OCR & Multimodal Document Pipeline

### 6.1 OCR Pipeline

```
[Uploaded Image (CCCD, Giấy tờ)]
      │
      ▼
  Pre-processing (OpenCV)
  ├── Deskew / perspective correction
  ├── Contrast enhancement (CLAHE)
  └── Noise reduction
      │
      ▼
  Document Classification (Vision LLM or lightweight classifier)
  └── Identifies: CCCD / passport / birth_cert / land_cert / etc.
      │
      ▼
  PaddleOCR (Vietnamese PP-OCRv4)
  ├── Text detection (EAST-based)
  ├── Text recognition (CRNN with Vietnamese charset)
  └── Layout analysis (table/field detection)
      │
      ▼
  Field Extraction (LLM-assisted)
  ├── Raw OCR text → LLM prompt with document type hint
  ├── LLM extracts structured fields with confidence scores
  └── Output: PersonalData schema (Pydantic model)
      │
      ▼
  Validation Layer
  ├── CCCD checksum validation
  ├── Date format normalization (DD/MM/YYYY Vietnamese)
  └── Cross-field consistency checks
      │
      ▼
  PersonalDataStore (session-scoped, Redis)
  └── Available to Form Agent for auto-fill
```

### 6.2 PersonalData Schema

```python
class PersonalData(BaseModel):
    # Identity
    full_name: str | None
    full_name_latin: str | None  # Không dấu
    date_of_birth: date | None
    gender: Literal["Nam", "Nữ"] | None
    nationality: str = "Việt Nam"
    ethnicity: str | None
    
    # ID Document
    id_number: str | None          # CCCD/CMND number
    id_issue_date: date | None
    id_issue_place: str | None
    
    # Address
    permanent_address: Address | None
    temporary_address: Address | None
    
    # Source tracking
    source_document_type: str
    source_image_path: str
    extraction_confidence: float
    extracted_at: datetime
```

### 6.3 Multimodal LLM Query (Direct Image Q&A)

For direct document Q&A (e.g., "What is the expiry date on this document?"):

```python
async def query_document_image(image_path: str, question: str) -> str:
    image_b64 = encode_image_base64(image_path)
    
    response = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", 
                 "media_type": "image/jpeg", "data": image_b64}},
                {"type": "text", "text": question}
            ]
        }]
    )
    return response.content[0].text
```

---

## 7. Multi-Agent Orchestration

The agent system is built with **LangGraph** — this is a deliberate choice over LangChain LCEL or CrewAI because:
- LangGraph exposes the state machine explicitly (nodes + edges + conditional routing)
- Easier to debug, trace, and test each node independently
- State is a typed Python dict passed between nodes — no "magic" context passing

### 7.1 Agent Graph Structure

```
                    ┌─────────────────┐
                    │  ENTRY NODE     │
                    │  (parse intent) │
                    └────────┬────────┘
                             │
              ┌──────────────▼──────────────┐
              │       ROUTER NODE           │
              │  classifies to one of:      │
              └──┬──────┬──────┬────────────┘
                 │      │      │
          ┌──────▼─┐ ┌──▼───┐ ┌▼──────────────┐
          │  RAG   │ │ OCR  │ │  PROCEDURE    │
          │  NODE  │ │ NODE │ │  PLANNER NODE │
          └──┬─────┘ └──┬───┘ └──────┬────────┘
             │          │            │
             │          ▼            │
             │   ┌─────────────┐     │
             │   │ FORM FILL   │◄────┘
             │   │ NODE        │
             │   └──────┬──────┘
             │          │
             └──────────▼
                  ┌─────────────┐
                  │  SYNTHESIS  │
                  │  NODE       │
                  └─────────────┘
```

### 7.2 Agent State Schema

```python
class AgentState(TypedDict):
    # Input
    user_message: str
    uploaded_image_path: str | None
    session_id: str
    
    # Routing
    intent: Literal["procedure_inquiry", "document_ocr", "form_fill", 
                    "legal_question", "dependency_check"]
    entities: dict[str, Any]  # extracted NL entities
    
    # RAG
    retrieved_chunks: list[DocumentChunk]
    citations: list[Citation]
    
    # OCR
    personal_data: PersonalData | None
    document_type: str | None
    
    # Procedure
    target_procedure_id: str | None
    procedure_execution_plan: list[ProcedureStep]
    completed_procedures: list[str]
    
    # Form
    form_id: str | None
    filled_fields: dict[str, Any]
    unfilled_required_fields: list[str]
    
    # Output
    final_response: str
    response_metadata: dict
    
    # Control
    iteration_count: int
    errors: list[str]
```

### 7.3 Router Node Logic

```python
def router_node(state: AgentState) -> AgentState:
    """
    Classifies intent using LLM with structured output.
    Returns updated state with intent + entities populated.
    """
    classification = llm.with_structured_output(IntentClassification).invoke(
        ROUTER_PROMPT.format(message=state["user_message"])
    )
    
    return {
        **state,
        "intent": classification.intent,
        "entities": classification.entities,
        "target_procedure_id": classification.procedure_id
    }

def route_after_classification(state: AgentState) -> str:
    """LangGraph conditional edge — returns node name to route to."""
    intent = state["intent"]
    has_image = state["uploaded_image_path"] is not None
    
    if has_image and intent in ("document_ocr", "form_fill"):
        return "ocr_node"
    elif intent in ("procedure_inquiry", "dependency_check"):
        return "procedure_planner_node"
    elif intent == "legal_question":
        return "rag_node"
    elif intent == "form_fill":
        return "form_fill_node"
    else:
        return "rag_node"  # default fallback
```

---

## 8. Agentic Form Auto-Fill Pipeline

### 8.1 Overview

This pipeline connects OCR output → field mapping → PDF population. The key challenge is mapping **extracted personal data fields** to **diverse PDF form field names** across different government form templates.

### 8.2 Field Mapping Strategy

Rather than hard-coding mappings per form (brittle), use a **semantic mapping layer**:

```python
class FormFieldMapper:
    """
    Uses LLM to semantically map PersonalData fields to 
    form-specific field names.
    """
    
    MAPPING_PROMPT = """
    You have a person's data:
    {personal_data_schema}
    
    And a PDF form with these fields:
    {form_fields_list}
    
    Map each form field to the correct personal data field.
    If a field cannot be filled from personal data, mark as "REQUIRES_USER_INPUT".
    If a field can be derived (e.g., age from date_of_birth), mark as "DERIVABLE" with formula.
    
    Return JSON: {"field_name": "source_field_or_REQUIRES_USER_INPUT"}
    """
    
    def map_fields(self, personal_data: PersonalData, 
                   form_fields: list[FormField]) -> FieldMapping:
        # LLM call returns structured mapping
        ...
```

### 8.3 PDF Population

```python
async def fill_pdf_form(
    template_path: str,
    field_mapping: FieldMapping,
    personal_data: PersonalData
) -> str:
    """
    Supports two PDF types:
    1. AcroForm PDFs (fillable fields) → use pdfrw
    2. Non-fillable PDFs (image/text overlays) → use reportlab
    """
    
    reader = PdfReader(template_path)
    
    if reader.get_fields():  # AcroForm detected
        return _fill_acroform(template_path, field_mapping, personal_data)
    else:
        return _fill_overlay(template_path, field_mapping, personal_data)
```

### 8.4 Carry-Forward Between Forms

When completing a multi-step procedure chain, field values are carried forward automatically:

```python
class SessionDataAccumulator:
    """
    Accumulates extracted data across a user session.
    When filling Form N, data from Forms 1..N-1 is available.
    """
    
    def merge(self, existing: PersonalData, new_extraction: PersonalData) -> PersonalData:
        """New data overwrites existing only if confidence is higher."""
        merged = existing.model_copy()
        for field in PersonalData.model_fields:
            new_val = getattr(new_extraction, field)
            new_conf = new_extraction.field_confidences.get(field, 0.0)
            old_conf = existing.field_confidences.get(field, 0.0)
            if new_val is not None and new_conf >= old_conf:
                setattr(merged, field, new_val)
        return merged
```

---

## 9. Project Directory Structure

### Backend (FastAPI)

```
backend/
├── alembic/                        # DB migrations
│   └── versions/
├── app/
│   ├── main.py                     # FastAPI app factory
│   ├── config.py                   # Settings (pydantic-settings)
│   ├── dependencies.py             # FastAPI DI (DB, Redis, Clients)
│   │
│   ├── api/                        # Route handlers (thin layer)
│   │   ├── v1/
│   │   │   ├── chat.py             # POST /chat (streaming SSE)
│   │   │   ├── procedures.py       # GET/POST /procedures
│   │   │   ├── documents.py        # POST /documents/upload, /ocr
│   │   │   ├── forms.py            # GET /forms/{id}, POST /forms/fill
│   │   │   └── legal.py            # GET /legal/search
│   │   └── router.py
│   │
│   ├── agents/                     # LangGraph agent definitions
│   │   ├── graph.py                # Main graph assembly (nodes + edges)
│   │   ├── state.py                # AgentState TypedDict
│   │   ├── nodes/
│   │   │   ├── router.py           # Intent classification node
│   │   │   ├── rag.py              # RAG retrieval + generation node
│   │   │   ├── ocr.py              # OCR processing node
│   │   │   ├── procedure_planner.py # Dependency resolution node
│   │   │   ├── form_filler.py      # Field mapping + PDF fill node
│   │   │   └── synthesizer.py      # Final response assembly node
│   │   └── prompts/                # All LLM prompt templates
│   │       ├── router_prompt.py
│   │       ├── rag_prompt.py
│   │       ├── ocr_extraction_prompt.py
│   │       ├── form_mapping_prompt.py
│   │       └── synthesis_prompt.py
│   │
│   ├── core/                       # Domain logic (pure Python, no FastAPI)
│   │   ├── procedure_graph.py      # DAG traversal, dependency resolution
│   │   ├── form_field_mapper.py    # Semantic field mapping
│   │   ├── session_accumulator.py  # Cross-form data carry-forward
│   │   └── citation_formatter.py  # Legal citation formatting
│   │
│   ├── services/                   # Infrastructure wrappers
│   │   ├── llm.py                  # Anthropic client wrapper
│   │   ├── embedder.py             # bge-m3 / OpenAI embeddings
│   │   ├── qdrant_service.py       # Vector DB operations
│   │   ├── ocr_service.py          # PaddleOCR wrapper
│   │   ├── pdf_service.py          # PDF read/write/fill
│   │   ├── storage_service.py      # MinIO file operations
│   │   └── redis_service.py        # Session + cache
│   │
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── procedure.py
│   │   ├── form_template.py
│   │   ├── legal_document.py
│   │   └── session.py
│   │
│   ├── schemas/                    # Pydantic request/response schemas
│   │   ├── chat.py
│   │   ├── procedure.py
│   │   ├── document.py
│   │   ├── form.py
│   │   └── personal_data.py
│   │
│   └── ingestion/                  # Offline data ingestion scripts
│       ├── ingest_legal_docs.py    # PDF → Qdrant pipeline
│       ├── ingest_procedures.py    # Seed procedure graph to PostgreSQL
│       └── generate_mock_data.py  # Synthetic ID cards, documents
│
├── data/
│   ├── legal_documents/            # Raw Vietnamese legal PDFs
│   ├── form_templates/             # Blank PDF form templates
│   └── mock_documents/             # Synthetic CCCD images, etc.
│
├── tests/
│   ├── unit/
│   │   ├── test_procedure_graph.py
│   │   ├── test_form_mapper.py
│   │   └── test_ocr_extraction.py
│   ├── integration/
│   │   ├── test_rag_pipeline.py
│   │   └── test_agent_graph.py
│   └── fixtures/
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── pyproject.toml
```

### Frontend (Next.js)

```
frontend/
├── app/                            # Next.js App Router
│   ├── (chat)/
│   │   └── page.tsx                # Main chat interface
│   ├── (procedures)/
│   │   ├── page.tsx                # Procedure browser
│   │   └── [id]/page.tsx           # Procedure detail + form chain
│   ├── (forms)/
│   │   └── [id]/page.tsx           # Form fill + PDF preview
│   ├── layout.tsx
│   └── globals.css
│
├── components/
│   ├── chat/
│   │   ├── ChatWindow.tsx
│   │   ├── MessageBubble.tsx
│   │   ├── CitationCard.tsx        # Displays legal citations inline
│   │   └── ProcedurePlanCard.tsx   # Shows dependency execution plan
│   ├── forms/
│   │   ├── DynamicForm.tsx         # React Hook Form driven by schema
│   │   ├── FormFieldMapper.tsx     # Shows auto-filled vs manual fields
│   │   └── PDFPreview.tsx
│   ├── documents/
│   │   ├── DropZone.tsx
│   │   └── OCRResultCard.tsx
│   └── ui/                         # Shared primitives (Button, Input, etc.)
│
├── lib/
│   ├── api/                        # API client functions
│   │   ├── chat.ts
│   │   ├── procedures.ts
│   │   └── documents.ts
│   ├── stores/                     # Zustand stores
│   │   ├── sessionStore.ts         # Personal data, completed procedures
│   │   └── chatStore.ts
│   └── types/                      # TypeScript types (mirroring Pydantic schemas)
│
└── public/
```

---

## 10. Database Schema

### PostgreSQL — Core Tables

```sql
-- Procedure dependency graph
CREATE TABLE procedure_categories (
    id UUID PRIMARY KEY,
    name VARCHAR(200) NOT NULL,           -- "Hộ tịch"
    name_slug VARCHAR(200) UNIQUE,
    ministry VARCHAR(200)
);

CREATE TABLE procedures (
    id UUID PRIMARY KEY,
    category_id UUID REFERENCES procedure_categories(id),
    code VARCHAR(50) UNIQUE NOT NULL,     -- official government code
    name TEXT NOT NULL,                   -- "Đăng ký khai sinh"
    description TEXT,
    legal_basis TEXT[],                   -- array of decree references
    processing_time_days INT,
    fee_vnd INT,
    competent_authority VARCHAR(200),
    is_online BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- DAG edges: procedure A requires procedure B to be completed first
CREATE TABLE procedure_dependencies (
    id UUID PRIMARY KEY,
    procedure_id UUID REFERENCES procedures(id),
    depends_on_procedure_id UUID REFERENCES procedures(id),
    is_mandatory BOOLEAN DEFAULT true,
    condition_description TEXT,           -- e.g., "only if not a city resident"
    UNIQUE(procedure_id, depends_on_procedure_id)
);

-- What document types a procedure requires as INPUT
CREATE TABLE procedure_required_documents (
    id UUID PRIMARY KEY,
    procedure_id UUID REFERENCES procedures(id),
    document_type VARCHAR(100) NOT NULL,  -- "CCCD", "giay_khai_sinh"
    is_mandatory BOOLEAN DEFAULT true,
    quantity INT DEFAULT 1,
    notes TEXT
);

-- Form templates linked to procedures
CREATE TABLE form_templates (
    id UUID PRIMARY KEY,
    procedure_id UUID REFERENCES procedures(id),
    form_code VARCHAR(50) UNIQUE,
    name TEXT NOT NULL,
    version VARCHAR(20),
    pdf_template_path TEXT NOT NULL,      -- MinIO path
    fields JSONB NOT NULL,                -- field definitions
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Legal documents for RAG ingestion tracking
CREATE TABLE legal_documents (
    id UUID PRIMARY KEY,
    document_number VARCHAR(100) UNIQUE,  -- "123/2015/NĐ-CP"
    document_type VARCHAR(50),            -- "nghi_dinh", "thong_tu", "quyet_dinh"
    title TEXT NOT NULL,
    issuing_authority VARCHAR(200),
    issue_date DATE,
    effective_date DATE,
    pdf_path TEXT,
    ingested_at TIMESTAMPTZ,
    chunk_count INT DEFAULT 0
);

-- Link legal documents to procedures (for filtered RAG)
CREATE TABLE procedure_legal_docs (
    procedure_id UUID REFERENCES procedures(id),
    legal_document_id UUID REFERENCES legal_documents(id),
    PRIMARY KEY (procedure_id, legal_document_id)
);

-- User sessions (mock — no real auth)
CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    personal_data JSONB,                  -- accumulated PersonalData
    completed_procedure_ids UUID[],
    form_fill_state JSONB
);
```

### Qdrant Collection Schema

```python
# Collection: "legal_documents"
{
    "vector": [float * 1024],   # bge-m3 embedding
    "payload": {
        "legal_document_id": "uuid",
        "document_number": "123/2015/NĐ-CP",
        "document_type": "nghi_dinh",
        "article_number": "Điều 15",
        "chapter": "Chương III",
        "content": "raw text chunk",
        "procedure_tags": ["uuid1", "uuid2"],
        "effective_date": "2016-01-01",
        "chunk_index": 3
    }
}
```

---

## 11. Phased Implementation Roadmap

### Phase 0 — Foundation (Week 1–2)
**Goal: Everything runs locally, database seeded, no AI yet.**

1. `docker-compose.yml` with PostgreSQL, Redis, Qdrant, MinIO
2. FastAPI skeleton with health check and CORS
3. Alembic migrations for all tables above
4. Seed script: manually enter 3–5 procedures with their dependency graph
5. Next.js skeleton with API client wired up
6. MinIO bucket setup for form templates

**Deliverable:** `GET /procedures` returns a DAG you can visualize. Dependency resolution logic (topological sort) is unit-tested.

---

### Phase 1 — RAG Pipeline (Week 3–4)
**Goal: Ask a legal question, get a cited answer.**

1. Collect 5–10 real Vietnamese legal PDFs relevant to chosen procedures
2. Build `ingest_legal_docs.py`: Docling → chunker → bge-m3 → Qdrant
3. Build `qdrant_service.py` with hybrid search (semantic + BM25)
4. Build `rag_node` in LangGraph with Claude prompt + structured citation output
5. Wire to `POST /chat` endpoint (non-streaming first)
6. Add streaming SSE support
7. Basic chat UI in Next.js

**Deliverable:** "What documents do I need for birth registration?" returns a cited answer from real Vietnamese legal text.

---

### Phase 2 — OCR & Multimodal (Week 5–6)
**Goal: Upload a mock CCCD image, extract structured personal data.**

1. Generate synthetic CCCD images using Pillow (fake names, IDs, addresses)
2. Build `ocr_service.py`: OpenCV pre-processing → PaddleOCR → LLM field extraction
3. Build `PersonalData` Pydantic schema with confidence scores
4. Build `ocr_node` in LangGraph
5. Build `POST /documents/upload` and `POST /documents/ocr` endpoints
6. Add multimodal direct-query path (Claude vision for ad-hoc questions)
7. Store extracted data in Redis session

**Deliverable:** Upload a synthetic CCCD → receive JSON with name, DOB, ID number, address.

---

### Phase 3 — Procedure Planner & Form Filler (Week 7–8)
**Goal: Given a target procedure, resolve the full dependency chain and fill all required forms.**

1. Implement `procedure_graph.py`: topological sort + dependency checker
2. Build `procedure_planner_node`: takes target procedure, returns ordered execution plan
3. Add 2–3 real blank form PDF templates (obtain or mock government forms)
4. Build `form_field_mapper.py`: LLM-driven semantic mapping
5. Build `pdf_service.py`: AcroForm fill + overlay fallback
6. Build `form_filler_node`: orchestrates mapping + fill + storage
7. Implement `SessionDataAccumulator` for carry-forward
8. Frontend: dynamic form display with auto-filled fields highlighted

**Deliverable:** "I want to register a birth" → system shows you need 3 prerequisites → upload CCCD → Form A auto-fills with extracted data → PDF download.

---

### Phase 4 — Full Agent Integration & Polish (Week 9–10)
**Goal: All agents work as one coherent graph, conversation is stateful.**

1. Assemble full LangGraph graph with all nodes
2. Implement `router_node` with robust intent classification
3. Add conversation history to agent state (multi-turn context)
4. Add `synthesizer_node` that combines RAG answer + procedure plan + form status
5. Implement session persistence (user can resume a session)
6. Build `generate_mock_data.py`: generate a library of synthetic docs for demo
7. End-to-end testing of full citizen journey
8. Add LangSmith tracing for agent observability

**Deliverable:** A complete, demo-able journey from question → OCR → plan → filled PDFs with citations throughout.

---

## 12. Key Architectural Decisions (ADRs)

### ADR-001: LangGraph over CrewAI/AutoGen
CrewAI is role-based and harder to debug when agent handoffs fail. AutoGen is better for code generation tasks. LangGraph's explicit state machine is the right choice here because the procedure dependency logic **is** a graph — using a graph framework to model a graph problem is natural.

### ADR-002: Qdrant over Pinecone/Weaviate
Qdrant runs fully locally (no cloud dependency for a mock project), supports rich payload filtering crucial for legal document retrieval, and has a Python client with excellent async support.

### ADR-003: PaddleOCR over Tesseract as Primary
Tesseract's Vietnamese support is adequate but PaddleOCR's PP-OCRv4 significantly outperforms it on Vietnamese government document layouts (dense, small text, watermarks). Keep Tesseract as fallback.

### ADR-004: Procedure Graph in PostgreSQL, NOT in a Graph DB (Neo4j)
For an educational mock with a limited number of procedures (dozens, not thousands), PostgreSQL with a self-referential adjacency table is simpler to set up, maintain, and query. The topological sort is done in Python. Neo4j would be justified if the graph had hundreds of nodes with complex relationship types.

### ADR-005: bge-m3 over OpenAI Embeddings for Legal Documents
`bge-m3` is a multilingual model trained on Vietnamese text and supports hybrid dense+sparse retrieval natively. For Vietnamese legal text, domain-appropriate embeddings matter more than convenience. Use OpenAI embeddings only if bge-m3 proves too slow on local hardware.

### ADR-006: Session State in Redis, NOT in the Agent State
Agent state is per-invocation. Cross-turn session data (accumulated personal data, completed procedures) lives in Redis, keyed by session ID, and is loaded into agent state at the start of each invocation. This keeps agent state deterministic and testable.

### ADR-007: LLM-Driven Field Mapping (Not Hard-Coded)
Hard-coding `personal_data.full_name → form_field_ho_ten` for every form is brittle and doesn't scale. The LLM semantic mapping approach works for any new form added to the system without code changes — the only requirement is that the PDF form has human-readable field names (which Vietnamese government forms do).

---

*End of Architecture Blueprint v1.0*
*Next step: Begin Phase 0 — run `docker-compose up` and verify all infrastructure services.*
