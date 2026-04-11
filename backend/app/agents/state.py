"""LangGraph agent state definition — the single source of truth per invocation."""

from typing import Any

from typing_extensions import Required, TypedDict

from app.schemas.chat import Citation
from app.schemas.personal_data import PersonalData
from app.schemas.procedure import ProcedureStep


class DocumentChunk(TypedDict, total=False):
    chunk_id: str
    document_number: str
    article: str
    text: str
    score: float
    procedure_tags: list[str]


class AgentState(TypedDict, total=False):
    # Required fields
    user_message: Required[str]
    session_id: Required[str]
    iteration_count: Required[int]

    # Input
    uploaded_image_path: str | None

    # Routing (plan_executor topology)
    execution_plan: list[str]    # Valid entries: "rag_fn", "ocr_fn", "form_filler_fn" ONLY.
                                 # "procedure_planner_fn" is NOT valid — handled by enrichment_node.
    plan_cursor: int             # current index into execution_plan — incremented by plan_executor only
    entities: dict[str, Any]

    domain: str | None           # "housing" | "civil_registration" | "business_registration" | None
                                 # Set by router on every invocation. None = ambiguous query.

    filing_jurisdiction: str | None  # e.g. "VN-HCM-26968"
                                     # Loaded from SessionData at graph entry.
                                     # Set by confirmed user input — never by raw OCR alone.
                                     # None on first invocation until user confirms.

    # Conversation history — last 6 turns only.
    # Trimmed by RedisService.save_session() before write.
    # Each entry: {"role": "user" | "assistant", "content": str}
    conversation_history: list[dict]

    # RAG
    retrieved_chunks: list[DocumentChunk]
    citations: list[Citation]
    scope_used: str | None  # scope code that produced results (e.g. "VN", "VN-HCM")

    # OCR (this invocation only — persist to Redis after)
    personal_data: PersonalData | None         # accumulated merged PersonalData (carry-forward)
    extracted_personal_data: PersonalData | None  # most recent OCR output, not yet merged into personal_data
    document_type: str | None

    # Procedure
    target_procedure_id: str | None
    procedure_execution_plan: list[ProcedureStep]
    completed_procedures: list[str]  # loaded from Redis at start

    # Form
    form_id: str | None
    filled_fields: dict[str, Any]
    unfilled_required_fields: list[str]
    filled_form_path: str | None      # MinIO path to filled PDF (tmp/ or forms/ prefix)
    form_fill_complete: bool           # True only when all required fields filled and form promoted

    # Output
    final_response: str
    response_metadata: dict

    # Control
    errors: list[str]
