"""Session data schema — stored in Redis, loaded into AgentState at invocation start."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.personal_data import PersonalData


class SessionData(BaseModel):
    """Cross-turn state persisted in Redis between agent invocations."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    session_id: str
    personal_data: PersonalData | None = None
    completed_procedure_ids: list[str] = Field(default_factory=list)
    form_fill_state: dict[str, Any] = Field(default_factory=dict)
    conversation_history: list[dict] = Field(default_factory=list)  # trimmed to 6 by save_session()
    filing_jurisdiction: str | None = None
    # e.g. "VN-HCM-26968" — set by confirmed user input only,
    # never by raw OCR alone. None until user confirms jurisdiction.

    domain: str | None = None
    # "housing" | "civil_registration" | "business_registration" | None
    # None means ambiguous — Synthesizer will ask for clarification.

    # Document upload state — set by POST /api/v1/documents/upload
    extracted_personal_data: PersonalData | None = None
    # Most recent OCR result from the upload endpoint; not yet merged into personal_data.
    uploaded_document_path: str | None = None
    # MinIO tmp/ path of the most recently uploaded document; read by ocr_fn when
    # body.image_path is absent from the chat request.

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
