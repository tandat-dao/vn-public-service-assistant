"""OCR worker function — two-path pipeline (QR decode → OCR fallback).

This is a plain async function called by plan_executor via NODE_REGISTRY["ocr_fn"].
It is NOT a LangGraph graph node and must NOT import from graph.py.

Orchestration:
  1. Try QR decode (fast, zero-token) — return immediately on success.
  2. On QR failure: classify document type (vision LLM), then run full OCR + LLM extraction.
"""

from app.agents.state import AgentState
from app.services.ocr_service import OCRService

# Module-level OCRService singleton — lazy-initialised on first call.
# Replace in tests: patch('app.agents.nodes.ocr._get_svc', return_value=mock_svc)
_ocr_svc: OCRService | None = None


def _get_svc() -> OCRService:
    global _ocr_svc
    if _ocr_svc is None:
        _ocr_svc = OCRService()
    return _ocr_svc


async def ocr_fn(state: AgentState) -> dict:
    """Run the two-path OCR pipeline on state["uploaded_image_path"].

    Returns:
        {"personal_data": PersonalData | None, "document_type": str | None}
    """
    image_path = state.get("uploaded_image_path")
    if not image_path:
        return {"personal_data": None, "document_type": None}

    svc = _get_svc()

    # QR path — attempt first for all uploads (~200ms, zero LLM tokens)
    personal_data = await svc.decode_qr(image_path)
    if personal_data is not None:
        return {"personal_data": personal_data, "document_type": "cccd"}

    # OCR path — QR failed or non-CCCD document
    document_type = await svc.classify_document_type(image_path)
    personal_data = await svc.extract(image_path, document_type)
    return {"personal_data": personal_data, "document_type": document_type}
