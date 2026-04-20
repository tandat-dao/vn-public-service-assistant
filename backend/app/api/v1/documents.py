"""Documents API routes — file upload with validation, MinIO storage, and OCR."""

import os
import tempfile
import uuid
from pathlib import Path
from statistics import mean

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.file_validator import validate_upload
from app.dependencies import get_db
from app.rate_limit import limiter
from app.schemas.document import DocumentUploadResponse
from app.schemas.personal_data import PersonalData
from app.schemas.session import SessionData
from app.services.ocr_service import OCRService
from app.services.redis_service import RedisService
from app.services.storage_service import StorageError, StorageService

logger = structlog.get_logger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Lazy-initialized module-level singletons.
# Replace in tests via:
#   patch("app.api.v1.documents._get_storage", return_value=mock_storage)
#   patch("app.api.v1.documents._get_ocr",     return_value=mock_ocr)
#   patch("app.api.v1.documents._get_redis",   return_value=mock_redis)
# ---------------------------------------------------------------------------

_storage_svc: StorageService | None = None
_ocr_svc: OCRService | None = None
_redis_svc: RedisService | None = None


def _get_storage() -> StorageService:
    global _storage_svc
    if _storage_svc is None:
        _storage_svc = StorageService()
    return _storage_svc


def _get_ocr() -> OCRService:
    global _ocr_svc
    if _ocr_svc is None:
        _ocr_svc = OCRService()
    return _ocr_svc


def _get_redis() -> RedisService:
    global _redis_svc
    if _redis_svc is None:
        _redis_svc = RedisService()
    return _redis_svc


def _compute_ocr_confidence(personal_data: PersonalData) -> float:
    """Return mean of per-field confidences, falling back to extraction_confidence."""
    if personal_data.field_confidences:
        return mean(personal_data.field_confidences.values())
    return personal_data.extraction_confidence


@router.post("/upload", response_model=DocumentUploadResponse)
@limiter.limit(settings.UPLOAD_RATE_LIMIT)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = Form(...),
    citizen_id: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Validate, store, and OCR an uploaded identity document.

    Returns JSON (not SSE). On MinIO failure: HTTP 500.
    On OCR failure: HTTP 200 with status="partial" — the file is still stored.
    filing_jurisdiction is NEVER set from OCR output.
    """
    # ---- Step 1: Validate ----
    await validate_upload(file)

    # ---- Step 2: Read file bytes ----
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=422, detail="File rỗng.")

    suffix = Path(file.filename or "upload").suffix.lower() or ".jpg"
    mime_type = file.content_type or "application/octet-stream"

    # ---- Step 3: Store to MinIO tmp/{session_id}/{uuid}{ext} ----
    tmp_path = f"tmp/{session_id}/{uuid.uuid4()}{suffix}"
    storage = _get_storage()
    try:
        await storage.upload(tmp_path, file_bytes, mime_type)
    except (StorageError, Exception) as exc:
        logger.warning("upload_document: MinIO upload failed", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail="Không thể lưu tệp. Vui lòng thử lại.",
        )

    # ---- Step 4: Run OCR via temp file (QR-first, mirrors ocr_fn worker) ----
    # OCRService methods take file paths. Write bytes to a temp file, then
    # call the async methods (PaddleOCR is already wrapped in run_in_executor
    # inside OCRService — do NOT add another run_in_executor layer here).
    ocr_result: PersonalData | None = None
    tmp_file_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_file_path = tmp.name

        svc = _get_ocr()

        # Path A: QR decode (~200ms, zero LLM tokens, confidence=1.0)
        ocr_result = await svc.decode_qr(tmp_file_path)

        # Path B: PaddleOCR + LLM extraction — only when QR decode fails
        if ocr_result is None:
            doc_type = await svc.classify_document_type(tmp_file_path)
            ocr_result = await svc.extract(tmp_file_path, doc_type)
            # extract() never raises — it returns PersonalData with confidence=0.0
            # on internal failure. We propagate it as-is; callers see all-None fields.

    except Exception as exc:
        logger.warning("upload_document: OCR pipeline error", error=str(exc))
        ocr_result = None
    finally:
        if tmp_file_path:
            try:
                os.unlink(tmp_file_path)
            except OSError:
                pass

    # ---- Step 5: Persist to Redis session ----
    redis = _get_redis()
    try:
        session = await redis.get_session(session_id)
        if session is None:
            session = SessionData(session_id=session_id)
        session = session.model_copy(
            update={
                "extracted_personal_data": ocr_result,
                "uploaded_document_path": tmp_path,
            }
        )
        await redis.save_session(session_id, session)
    except Exception as exc:
        # Redis save failure must not fail the response.
        logger.warning("upload_document: Redis session save failed", error=str(exc))

    # ---- Step 5b: Write citizen carry-forward key on full OCR success ----
    # Only write when OCR produced usable data (not partial/None). The method
    # is non-fatal internally — no try/except needed here.
    if citizen_id and ocr_result is not None:
        await redis.save_citizen_personal_data(citizen_id, ocr_result)

    # ---- Step 6: Return JSON response ----
    if ocr_result is not None:
        confidence = _compute_ocr_confidence(ocr_result)
        return DocumentUploadResponse(
            status="success",
            tmp_path=tmp_path,
            personal_data=ocr_result,
            ocr_confidence=confidence,
            message="Đã trích xuất thông tin thành công.",
        )

    return DocumentUploadResponse(
        status="partial",
        tmp_path=tmp_path,
        personal_data=None,
        ocr_confidence=0.0,
        message=(
            "Tệp đã được lưu nhưng không thể đọc thông tin. "
            "Vui lòng thử ảnh rõ hơn."
        ),
    )


@router.get("/download")
@limiter.limit(settings.UPLOAD_RATE_LIMIT)
async def download_filled_form(
    request: Request,
    path: str,
    session_id: str,
) -> Response:
    """Serve a filled PDF form stored in MinIO.

    Security: the ``path`` must belong to the requesting ``session_id``.
    MinIO paths are structured as ``tmp/{session_id}/...`` or
    ``forms/{session_id}/...``.  The session_id component is extracted from
    the path and compared to the ``session_id`` query parameter — mismatches
    return HTTP 403.

    On missing file: HTTP 404.
    On match: returns the PDF bytes with Content-Disposition: attachment.
    """
    # ---- Step 1: Security — verify path belongs to this session ----
    # Expected path formats:
    #   tmp/{session_id}/TTHC-001.pdf
    #   forms/{session_id}/TTHC-001.pdf
    path_parts = path.split("/")
    if len(path_parts) < 3 or path_parts[0] not in ("tmp", "forms"):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền truy cập tệp này.",
        )
    path_session_id = path_parts[1]
    if path_session_id != session_id:
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền truy cập tệp này.",
        )

    # ---- Step 2: Retrieve file from MinIO ----
    # StorageService.download() is already async — it wraps the blocking
    # MinIO SDK call internally in asyncio.get_running_loop().run_in_executor().
    storage = _get_storage()
    try:
        file_bytes = await storage.download(path)
    except (StorageError, Exception) as exc:
        logger.warning("download_filled_form: MinIO download failed", path=path, error=str(exc))
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy tệp. Tệp có thể đã hết hạn.",
        )

    # ---- Step 3: Derive filename from path ----
    # Extract procedure ID from path, e.g. "forms/abc/TTHC-001.pdf" → "TTHC-001"
    filename_part = Path(path).stem  # e.g. "TTHC-001"
    download_filename = f"to-khai-{filename_part}.pdf" if filename_part else "to-khai.pdf"

    return Response(
        content=file_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{download_filename}"',
        },
    )
