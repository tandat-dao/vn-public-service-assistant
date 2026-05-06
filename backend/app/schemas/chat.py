"""Pydantic schemas for the chat API."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.procedure import ProcedureExecutionPlan


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(..., max_length=128)
    image_path: str | None = None
    citizen_id: str | None = None

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message cannot be blank")
        return stripped


class Citation(BaseModel):
    doc_id: str
    document_number: str
    article: str
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    execution_plan: ProcedureExecutionPlan | None = None
    confidence: Literal["high", "medium", "low"]
