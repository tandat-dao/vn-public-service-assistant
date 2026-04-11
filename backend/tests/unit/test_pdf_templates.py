"""Smoke tests for the synthetic AcroForm PDF templates (TASK-15).

These tests verify that the generated PDF templates exist on disk, are
recognised as AcroForm PDFs, contain the expected field names, and can
be filled by PDFService without raising.

DEPENDENCY: The PDF files must exist before these tests run.
Generate them with:
    cd backend
    PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python data/pdf_templates/generate_templates.py
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pdfrw

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
TEMPLATE_DIR = Path(__file__).parent.parent.parent / "data" / "pdf_templates"

TTHC001_PATH = TEMPLATE_DIR / "TTHC-001.pdf"
TTHC002_PATH = TEMPLATE_DIR / "TTHC-002.pdf"
TTHC003_PATH = TEMPLATE_DIR / "TTHC-003.pdf"

# Expected fields for TTHC-001 and TTHC-003 (shared CT01 base)
SHARED_FIELDS = [
    "ho_chu_dem_va_ten",
    "ngay_thang_nam_sinh",
    "gioi_tinh",
    "dan_toc",
    "so_dinh_danh_ca_nhan",
    "que_quan",
    "noi_thuong_tru",
    "noi_o_hien_tai",
    "nghe_nghiep",
    "noi_lam_viec",
    "ho_ten_chu_ho",
    "quan_he_voi_chu_ho",
    "so_dinh_danh_chu_ho",
    "noi_dung_de_nghi",
]

TTHC002_EXTRA_FIELD = "thoi_han_tam_tru"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _read_acroform_fields(path: Path) -> list[str]:
    """Return AcroForm field names from a PDF using pdfrw."""

    def _get_name(ann) -> str | None:
        raw = ann.get("/T")
        if raw:
            return raw[1:-1] if isinstance(raw, str) and raw.startswith("(") else str(raw)
        parent = ann.get("/Parent")
        if parent:
            raw2 = parent.get("/T")
            if raw2:
                return raw2[1:-1] if isinstance(raw2, str) and raw2.startswith("(") else str(raw2)
        return None

    reader = pdfrw.PdfReader(str(path))
    fields: list[str] = []
    for page in reader.pages:
        for ann in page.get("/Annots") or []:
            name = _get_name(ann)
            if name:
                fields.append(name)
    return fields


# ---------------------------------------------------------------------------
# Test 1-3 — File existence
# ---------------------------------------------------------------------------

class TestTemplateFilesExist:
    def test_tthc001_template_exists(self):
        assert TTHC001_PATH.exists(), (
            f"TTHC-001.pdf not found at {TTHC001_PATH}. "
            "Run: cd backend && PYTHONPATH=. .venv/Scripts/python "
            "data/pdf_templates/generate_templates.py"
        )

    def test_tthc002_template_exists(self):
        assert TTHC002_PATH.exists(), (
            f"TTHC-002.pdf not found at {TTHC002_PATH}. "
            "Run: cd backend && PYTHONPATH=. .venv/Scripts/python "
            "data/pdf_templates/generate_templates.py"
        )

    def test_tthc003_template_exists(self):
        assert TTHC003_PATH.exists(), (
            f"TTHC-003.pdf not found at {TTHC003_PATH}. "
            "Run: cd backend && PYTHONPATH=. .venv/Scripts/python "
            "data/pdf_templates/generate_templates.py"
        )


# ---------------------------------------------------------------------------
# Test 4 — AcroForm detection via pdfrw
# ---------------------------------------------------------------------------

class TestTemplateIsAcroform:
    def test_tthc001_is_acroform(self):
        """TTHC-001.pdf must be a valid AcroForm PDF (has /AcroForm in root)."""
        reader = pdfrw.PdfReader(str(TTHC001_PATH))
        assert reader.Root.AcroForm is not None, (
            "TTHC-001.pdf is not an AcroForm PDF — PDFService._fill_acroform() "
            "will not be able to fill it by field name."
        )
        # Also confirm it has a /Fields array
        fields_array = reader.Root.AcroForm.get("/Fields")
        assert fields_array is not None and len(fields_array) > 0


# ---------------------------------------------------------------------------
# Test 5 — Field names in TTHC-001
# ---------------------------------------------------------------------------

class TestTthc001HasExpectedFields:
    def test_tthc001_has_expected_fields(self):
        """All 14 CT01 base field names must be present in TTHC-001.pdf."""
        actual = _read_acroform_fields(TTHC001_PATH)
        missing = [f for f in SHARED_FIELDS if f not in actual]
        assert not missing, (
            f"TTHC-001.pdf is missing {len(missing)} expected field(s): {missing}"
        )
        assert len(actual) == 14, (
            f"TTHC-001.pdf should have exactly 14 fields, got {len(actual)}: {actual}"
        )


# ---------------------------------------------------------------------------
# Test 6 — TTHC-002 has the extra field; TTHC-001 does not
# ---------------------------------------------------------------------------

class TestThanhTamTruFieldPresence:
    def test_tthc002_has_thoi_han_tam_tru_field(self):
        """TTHC-002.pdf must contain 'thoi_han_tam_tru' (temporary-stay duration)."""
        actual = _read_acroform_fields(TTHC002_PATH)
        assert TTHC002_EXTRA_FIELD in actual, (
            f"'thoi_han_tam_tru' not found in TTHC-002.pdf fields: {actual}"
        )
        assert len(actual) == 15, (
            f"TTHC-002.pdf should have exactly 15 fields, got {len(actual)}"
        )

    def test_tthc001_does_not_have_thoi_han_tam_tru_field(self):
        """TTHC-001.pdf must NOT contain 'thoi_han_tam_tru' — that field is TTHC-002 only."""
        actual = _read_acroform_fields(TTHC001_PATH)
        assert TTHC002_EXTRA_FIELD not in actual, (
            f"'thoi_han_tam_tru' should not be in TTHC-001.pdf but was found"
        )


# ---------------------------------------------------------------------------
# Test 7 — PDFService round-trip fill
# ---------------------------------------------------------------------------

class TestPdfServiceCanFillTthc001:
    def test_pdf_service_can_fill_tthc001(self):
        """PDFService.fill() must route to _fill_acroform() and return a path.

        StorageService is mocked: download() returns the real PDF bytes,
        upload() is a no-op.  No pdfplumber patching is required — Fix 1
        corrected catalog key lookup from '/AcroForm' to 'AcroForm'.
        """
        from app.services.pdf_service import PDFService

        template_bytes = TTHC001_PATH.read_bytes()

        mock_storage = MagicMock()
        mock_storage.download = AsyncMock(return_value=template_bytes)
        mock_storage.upload = AsyncMock(return_value=None)

        pdf_svc = PDFService(storage_service=mock_storage)

        result = asyncio.run(
            pdf_svc.fill(
                "pdf_templates/TTHC-001.pdf",
                {
                    "ho_chu_dem_va_ten": "Nguyễn Văn A",
                    "so_dinh_danh_ca_nhan": "079123456789",
                },
                "test-session",
                "TTHC-001",
            )
        )

        assert isinstance(result, str)
        assert result == "tmp/test-session/TTHC-001.pdf"

        # Verify upload was called (filled bytes were produced)
        mock_storage.upload.assert_called_once()
        upload_path, upload_bytes, upload_ct = mock_storage.upload.call_args.args
        assert upload_path == "tmp/test-session/TTHC-001.pdf"
        assert isinstance(upload_bytes, bytes)
        assert len(upload_bytes) > 0
        assert upload_ct == "application/pdf"
