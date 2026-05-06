"""OCR worker function — two-path pipeline (QR decode → OCR fallback).

This is a plain async function called by plan_executor via NODE_REGISTRY["ocr_fn"].
It is NOT a LangGraph graph node and must NOT import from graph.py.

Orchestration:
  1. Try QR decode (fast, zero-token) — return immediately on success.
  2. On QR failure: classify document type (vision LLM), then run full OCR + LLM extraction.
"""

import os
import tempfile
from pathlib import Path

from app.agents.state import AgentState
from app.services.ocr_service import OCRService

# Module-level singletons — lazy-initialised on first call.
# Replace in tests: patch('app.agents.nodes.ocr._get_svc', return_value=mock_svc)
_ocr_svc: OCRService | None = None
_storage_svc = None


def _get_svc() -> OCRService:
    global _ocr_svc
    if _ocr_svc is None:
        _ocr_svc = OCRService()
    return _ocr_svc


def _get_storage():
    global _storage_svc
    if _storage_svc is None:
        from app.services.storage_service import StorageService
        _storage_svc = StorageService()
    return _storage_svc


def _is_minio_path(path: str) -> bool:
    """Return True if path is a MinIO object key, not a local filesystem path.

    MinIO keys are relative strings like "tmp/{session_id}/{uuid}.png".
    Local paths are either absolute (start with / or drive letter) or exist on disk.
    """
    return not os.path.isabs(path) and not os.path.exists(path)


async def ocr_fn(state: AgentState) -> dict:
    """Run the two-path OCR pipeline on state["uploaded_image_path"].

    If uploaded_image_path is a MinIO object key (set by the upload endpoint and
    stored in the Redis session), download it to a local temp file first.
    OCRService methods require local filesystem paths — cv2.imread() cannot open
    MinIO keys directly.

    Returns:
        {"personal_data": PersonalData | None, "document_type": str | None}
    """
    image_path = state.get("uploaded_image_path")
    if not image_path:
        return {"personal_data": None, "document_type": None}

    # Download from MinIO when the path is an object key, not a local file.
    tmp_file_path: str | None = None
    local_path = image_path
    if _is_minio_path(image_path):
        storage = _get_storage()
        file_bytes = await storage.download(image_path)
        suffix = Path(image_path).suffix or ".jpg"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_file_path = tmp.name
        local_path = tmp_file_path

    try:
        svc = _get_svc()

        # QR path — attempt first for all uploads (~200ms, zero LLM tokens)
        personal_data = await svc.decode_qr(local_path)
        if personal_data is not None:
            return {"personal_data": personal_data, "document_type": "cccd"}

        # OCR path — QR failed or non-CCCD document
        document_type = await svc.classify_document_type(local_path)
        personal_data = await svc.extract(local_path, document_type)
        return {"personal_data": personal_data, "document_type": document_type}
    finally:
        if tmp_file_path:
            try:
                os.unlink(tmp_file_path)
            except OSError:
                pass
