"""Pydantic schemas for document upload and OCR responses."""

from pydantic import BaseModel

from app.schemas.personal_data import PersonalData


class DocumentUploadResponse(BaseModel):
    file_path: str
    document_type: str
    detected_type: str


class OCRResponse(BaseModel):
    personal_data: PersonalData
    raw_text: str
    processing_time_ms: int
