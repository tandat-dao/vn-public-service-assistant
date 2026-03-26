"""File upload validation — MIME type, extension, and size checks.

Called as the first line of every document upload handler before any MinIO
or OCR interaction. Raises HTTPException(422) on any violation.
"""

from pathlib import Path

from fastapi import HTTPException, UploadFile

ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/webp", "application/pdf"}
)
ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
)
MAX_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB
_MAGIC_READ_BYTES: int = 2048


async def validate_upload(file: UploadFile) -> None:
    """Validate an uploaded file for MIME type, extension, and size.

    Args:
        file: The FastAPI UploadFile received from the multipart request.

    Raises:
        HTTPException(422): If the file fails any validation check.
    """
    # --- 1. Extension check (fast, no I/O) ---
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"File extension '{ext}' is not allowed. "
            f"Accepted: {sorted(ALLOWED_EXTENSIONS)}",
        )

    # --- 2. Size pre-check via Content-Length (no I/O if header present) ---
    if file.size is not None and file.size > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=422,
            detail=f"File size {file.size} bytes exceeds the 5 MB limit.",
        )

    # --- 3. MIME check via python-magic (reads first 2048 bytes) ---
    import magic  # lazy import — avoids DLL load at module import time (Windows)
    header = await file.read(_MAGIC_READ_BYTES)
    await file.seek(0)
    detected_mime = magic.from_buffer(header, mime=True)
    if detected_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Detected MIME type '{detected_mime}' is not allowed. "
            f"Accepted: {sorted(ALLOWED_MIME_TYPES)}",
        )

    # --- 4. Full-size check by streaming (only when Content-Length absent) ---
    if file.size is None:
        total = len(header)
        while chunk := await file.read(65_536):
            total += len(chunk)
            if total > MAX_SIZE_BYTES:
                raise HTTPException(
                    status_code=422,
                    detail="File exceeds the 5 MB size limit.",
                )
        await file.seek(0)
