"""Pydantic schemas for the chat API."""

from typing import Literal

from pydantic import BaseModel

from app.schemas.procedure import ProcedureExecutionPlan


class ChatRequest(BaseModel):
    message: str
    session_id: str
    image_path: str | None = None
    citizen_id: str | None = None


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
