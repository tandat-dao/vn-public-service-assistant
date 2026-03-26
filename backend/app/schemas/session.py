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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
