"""Documents API routes."""

from fastapi import APIRouter

from app.schemas.document import DocumentUploadResponse, OCRResponse

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document() -> DocumentUploadResponse:
    """Upload a document image to MinIO."""
    raise NotImplementedError


@router.post("/ocr", response_model=OCRResponse)
async def run_ocr() -> OCRResponse:
    """Run OCR pipeline on an uploaded document."""
    raise NotImplementedError


@router.post("/query", response_model=str)
async def query_document() -> str:
    """Answer a multimodal direct question about an uploaded document."""
    raise NotImplementedError
