"""LangGraph agent state definition — the single source of truth per invocation."""

from typing import Any, Literal

from typing_extensions import Required, TypedDict

from app.schemas.chat import Citation
from app.schemas.personal_data import PersonalData
from app.schemas.procedure import ProcedureExecutionPlan, ProcedureStep


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

    # Routing
    intent: Literal[
        "procedure_inquiry", "document_ocr", "form_fill", "legal_question", "dependency_check"
    ]
    entities: dict[str, Any]

    # RAG
    retrieved_chunks: list[DocumentChunk]
    citations: list[Citation]

    # OCR (this invocation only — persist to Redis after)
    personal_data: PersonalData | None
    document_type: str | None

    # Procedure
    target_procedure_id: str | None
    procedure_execution_plan: list[ProcedureStep]
    completed_procedures: list[str]  # loaded from Redis at start

    # Form
    form_id: str | None
    filled_fields: dict[str, Any]
    unfilled_required_fields: list[str]

    # Output
    final_response: str
    response_metadata: dict

    # Control
    errors: list[str]
