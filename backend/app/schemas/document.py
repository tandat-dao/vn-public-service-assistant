"""Pydantic schemas for document upload and OCR responses."""

from pydantic import BaseModel

from app.schemas.personal_data import PersonalData


class DocumentUploadResponse(BaseModel):
    status: str          # "success" | "partial"
    tmp_path: str
    personal_data: PersonalData | None
    ocr_confidence: float
    message: str


class OCRResponse(BaseModel):
    personal_data: PersonalData
    raw_text: str
    processing_time_ms: int
