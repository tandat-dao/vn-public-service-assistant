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

# Magic byte signatures for supported MIME types (pure Python, no native DLL).
ALLOWED_MIME_SIGNATURES: dict[bytes, str] = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"%PDF": "application/pdf",
}


async def _detect_mime(file: UploadFile) -> str:
    """Detect MIME type by reading the first 16 bytes and matching magic signatures."""
    header = await file.read(16)
    await file.seek(0)
    for sig, mime in ALLOWED_MIME_SIGNATURES.items():
        if header.startswith(sig):
            return mime
    # WebP: RIFF????WEBP where ???? is a 4-byte little-endian size
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


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

    # --- 3. MIME check via magic byte signatures (pure Python, no native DLL) ---
    detected_mime = await _detect_mime(file)
    if detected_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Detected MIME type '{detected_mime}' is not allowed. "
            f"Accepted: {sorted(ALLOWED_MIME_TYPES)}",
        )

    # --- 4. Full-size check by streaming (only when Content-Length absent) ---
    if file.size is None:
        total = 0
        while chunk := await file.read(65_536):
            total += len(chunk)
            if total > MAX_SIZE_BYTES:
                raise HTTPException(
                    status_code=422,
                    detail="File exceeds the 5 MB size limit.",
                )
        await file.seek(0)
