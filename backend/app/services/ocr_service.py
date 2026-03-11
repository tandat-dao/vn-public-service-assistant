"""OCR service — PaddleOCR with OpenCV pre-processing and LLM field extraction."""

from app.schemas.personal_data import PersonalData


class OCRService:
    """Identity document OCR pipeline."""

    async def extract(self, image_path: str, document_type: str) -> PersonalData:
        """
        Pre-process image (deskew, CLAHE, denoise), run PaddleOCR, then use LLM
        to extract structured PersonalData fields.
        """
        raise NotImplementedError
