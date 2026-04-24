"""Unit tests for app/core/file_validator.py.

All tests mock python-magic and use AsyncMock for UploadFile — no real file I/O.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.file_validator import MAX_SIZE_BYTES, validate_upload


def _make_upload_file(
    filename: str,
    content: bytes = b"fake content",
    size: int | None = None,
) -> AsyncMock:
    """Build a mock UploadFile that behaves like the real FastAPI class."""
    mock = AsyncMock()
    mock.filename = filename
    mock.size = size if size is not None else len(content)
    # Simulate read() returning the content bytes then b"" on subsequent calls
    mock.read = AsyncMock(side_effect=[content, b""])
    mock.seek = AsyncMock()
    return mock


# Fake JPEG magic bytes header
_JPEG_HEADER = b"\xff\xd8\xff" + b"\x00" * 2045
# Fake PDF magic bytes header
_PDF_HEADER = b"%PDF-1.4" + b"\x00" * 2040


class TestValidExtensionAndMime:
    async def test_valid_jpeg_passes(self):
        f = _make_upload_file("photo.jpg", content=_JPEG_HEADER)
        with patch("magic.from_buffer", return_value="image/jpeg"):
            await validate_upload(f)  # must not raise

    async def test_valid_pdf_passes(self):
        f = _make_upload_file("form.pdf", content=_PDF_HEADER)
        with patch("magic.from_buffer", return_value="application/pdf"):
            await validate_upload(f)  # must not raise

    async def test_valid_png_passes(self):
        f = _make_upload_file("scan.png", content=b"\x89PNG\r\n\x1a\n" + b"\x00" * 2040)
        await validate_upload(f)


class TestExtensionRejection:
    async def test_exe_extension_rejected(self):
        f = _make_upload_file("malware.exe", content=b"MZ" + b"\x00" * 2046)
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(f)
        assert exc_info.value.status_code == 422
        assert ".exe" in exc_info.value.detail

    async def test_no_extension_rejected(self):
        f = _make_upload_file("noextension", content=_JPEG_HEADER)
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(f)
        assert exc_info.value.status_code == 422

    async def test_html_extension_rejected(self):
        f = _make_upload_file("xss.html", content=b"<html>" + b" " * 2042)
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(f)
        assert exc_info.value.status_code == 422


class TestSizeRejection:
    async def test_file_over_5mb_rejected_via_content_length(self):
        # size set to 6 MB — rejected before MIME check
        f = _make_upload_file("big.jpg", content=b"\xff" * 10, size=MAX_SIZE_BYTES + 1)
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(f)
        assert exc_info.value.status_code == 422
        assert "5 MB" in exc_info.value.detail
        # Confirm magic.from_buffer was NOT called (early exit on size)
        # (no patch needed — test would fail if from_buffer raises)

    async def test_file_exactly_5mb_passes(self):
        content = b"\xff\xd8\xff" + b"\x00" * (MAX_SIZE_BYTES - 3)
        f = _make_upload_file("exact.jpg", content=content[:2048], size=MAX_SIZE_BYTES)
        with patch("magic.from_buffer", return_value="image/jpeg"):
            await validate_upload(f)  # must not raise


class TestMimeMismatch:
    async def test_pdf_extension_but_exe_mime_rejected(self):
        """File named .pdf but bytes don't match any known signature → reject."""
        f = _make_upload_file("trick.pdf", content=b"MZ" + b"\x00" * 2046)
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(f)
        assert exc_info.value.status_code == 422
        assert "application/octet-stream" in exc_info.value.detail

    async def test_jpg_extension_but_html_mime_rejected(self):
        f = _make_upload_file("photo.jpg", content=b"<html>" + b" " * 2042)
        with patch("magic.from_buffer", return_value="text/html"):
            with pytest.raises(HTTPException) as exc_info:
                await validate_upload(f)
        assert exc_info.value.status_code == 422
