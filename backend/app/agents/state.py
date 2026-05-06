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

    location_scope: str | None   # "VN-HCM" | "VN-HN" | "VN-DN" | None
                                 # Detected by the router LLM from query text.
                                 # None when no specific city is mentioned.

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

    # Guided procedure completion wizard — TASK-APP-18
    # Hydrated from SessionData at graph entry; written back after graph completes.
    # None = not in guided mode; "TTHC-001" | "TTHC-002" | "TTHC-003" = active guided procedure
    guided_procedure_id: str | None
    # 0=INTRO, 1=AWAIT_CCCD, 2=FORM_FILLING, 3=COMPLETE; None when not in guided mode
    guided_step: int | None

    # Output
    final_response: str
    response_metadata: dict

    # Out-of-scope guard — set by router_node when intent == "out_of_scope"
    out_of_scope: bool

    # RAG degradation — set by rag_fn when cascade exhausted all scope levels with zero chunks
    rag_returned_empty: bool

    # Control
    errors: list[str]
