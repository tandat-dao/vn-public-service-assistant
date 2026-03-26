"""Unit tests for PDFService.

All tests mock StorageService and pdfplumber — no real MinIO or PDF files required.
"""

from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest


def _make_pdf_service():
    """Return a PDFService with a mocked StorageService."""
    from app.services.pdf_service import PDFService

    mock_storage = AsyncMock()
    mock_storage.download = AsyncMock(return_value=b"%PDF-1.4 fake bytes")
    mock_storage.upload = AsyncMock(return_value="tmp/sess/form.pdf")

    svc = PDFService(storage_service=mock_storage)
    return svc, mock_storage


class TestFillDetection:
    async def test_fill_detects_acroform_and_calls_acroform_filler(self):
        """When the PDF has an AcroForm catalog entry, _fill_acroform must be called."""
        svc, mock_storage = _make_pdf_service()

        mock_pdf_ctx = MagicMock()
        mock_pdf_ctx.__enter__ = MagicMock(return_value=mock_pdf_ctx)
        mock_pdf_ctx.__exit__ = MagicMock(return_value=False)
        mock_pdf_ctx.doc.catalog.get.return_value = MagicMock()  # truthy = has AcroForm

        with patch("app.services.pdf_service.pdfplumber.open", return_value=mock_pdf_ctx):
            with patch.object(svc, "_fill_acroform", return_value=b"filled") as mock_acro:
                with patch.object(svc, "_fill_overlay", return_value=b"overlay") as mock_overlay:
                    with patch("tempfile.NamedTemporaryFile") as mock_tmp:
                        mock_tmp.return_value.__enter__ = MagicMock(return_value=MagicMock(name="/tmp/t.pdf"))
                        mock_tmp.return_value.name = "/tmp/t.pdf"
                        mock_tmp.return_value.write = MagicMock()
                        mock_tmp.return_value.flush = MagicMock()
                        mock_tmp.return_value.close = MagicMock()
                        with patch("os.unlink"):
                            await svc.fill("templates/form.pdf", {"name": "Test"}, "sess", "form")

        mock_acro.assert_called_once()
        mock_overlay.assert_not_called()

    async def test_fill_detects_flat_pdf_and_calls_overlay_filler(self):
        """When the PDF has no AcroForm, _fill_overlay must be called."""
        svc, mock_storage = _make_pdf_service()

        mock_pdf_ctx = MagicMock()
        mock_pdf_ctx.__enter__ = MagicMock(return_value=mock_pdf_ctx)
        mock_pdf_ctx.__exit__ = MagicMock(return_value=False)
        mock_pdf_ctx.doc.catalog.get.return_value = None  # None = flat PDF

        with patch("app.services.pdf_service.pdfplumber.open", return_value=mock_pdf_ctx):
            with patch.object(svc, "_fill_acroform", return_value=b"filled") as mock_acro:
                with patch.object(svc, "_fill_overlay", return_value=b"overlay") as mock_overlay:
                    with patch("tempfile.NamedTemporaryFile") as mock_tmp:
                        mock_tmp.return_value.name = "/tmp/t.pdf"
                        mock_tmp.return_value.write = MagicMock()
                        mock_tmp.return_value.flush = MagicMock()
                        mock_tmp.return_value.close = MagicMock()
                        with patch("os.unlink"):
                            await svc.fill("templates/flat.pdf", {"name": "Test"}, "sess", "form")

        mock_overlay.assert_called_once()
        mock_acro.assert_not_called()


class TestFillOutputPath:
    async def test_fill_writes_to_tmp_prefix(self):
        """The returned MinIO path must start with tmp/{session_id}/."""
        svc, mock_storage = _make_pdf_service()

        mock_pdf_ctx = MagicMock()
        mock_pdf_ctx.__enter__ = MagicMock(return_value=mock_pdf_ctx)
        mock_pdf_ctx.__exit__ = MagicMock(return_value=False)
        mock_pdf_ctx.doc.catalog.get.return_value = None

        with patch("app.services.pdf_service.pdfplumber.open", return_value=mock_pdf_ctx):
            with patch.object(svc, "_fill_overlay", return_value=b"bytes"):
                with patch("tempfile.NamedTemporaryFile") as mock_tmp:
                    mock_tmp.return_value.name = "/tmp/t.pdf"
                    mock_tmp.return_value.write = MagicMock()
                    mock_tmp.return_value.flush = MagicMock()
                    mock_tmp.return_value.close = MagicMock()
                    with patch("os.unlink"):
                        result = await svc.fill("t.pdf", {}, "my-session", "form-001")

        assert result.startswith("tmp/my-session/")

    async def test_fill_never_writes_to_final_path_directly(self):
        """StorageService.upload() must only be called with a path starting with 'tmp/'."""
        svc, mock_storage = _make_pdf_service()

        mock_pdf_ctx = MagicMock()
        mock_pdf_ctx.__enter__ = MagicMock(return_value=mock_pdf_ctx)
        mock_pdf_ctx.__exit__ = MagicMock(return_value=False)
        mock_pdf_ctx.doc.catalog.get.return_value = None

        with patch("app.services.pdf_service.pdfplumber.open", return_value=mock_pdf_ctx):
            with patch.object(svc, "_fill_overlay", return_value=b"bytes"):
                with patch("tempfile.NamedTemporaryFile") as mock_tmp:
                    mock_tmp.return_value.name = "/tmp/t.pdf"
                    mock_tmp.return_value.write = MagicMock()
                    mock_tmp.return_value.flush = MagicMock()
                    mock_tmp.return_value.close = MagicMock()
                    with patch("os.unlink"):
                        await svc.fill("t.pdf", {}, "s1", "f1")

        # Inspect all calls to upload()
        for upload_call in mock_storage.upload.call_args_list:
            object_path = upload_call.args[0]
            assert object_path.startswith("tmp/"), (
                f"upload() called with non-tmp path: {object_path}"
            )


class TestAcroformFill:
    def test_acroform_fill_sets_need_appearances(self):
        """_fill_acroform must set /NeedAppearances=True on the AcroForm dict."""
        svc, _ = _make_pdf_service()

        mock_reader = MagicMock()
        mock_reader.Root.AcroForm = MagicMock()
        mock_reader.pages = []

        mock_writer = MagicMock()
        mock_writer.write = MagicMock()

        with patch("app.services.pdf_service.pdfrw.PdfReader", return_value=mock_reader):
            with patch("app.services.pdf_service.pdfrw.PdfWriter", return_value=mock_writer):
                with patch("app.services.pdf_service.pdfrw.PdfDict") as mock_pdf_dict:
                    with patch("app.services.pdf_service.pdfrw.PdfObject") as mock_pdf_obj:
                        with patch("io.BytesIO") as mock_buf:
                            mock_buf.return_value.getvalue.return_value = b"pdf-bytes"
                            svc._fill_acroform("/tmp/template.pdf", {"field1": "value1"})

        # AcroForm.update must have been called with NeedAppearances=true
        mock_reader.Root.AcroForm.update.assert_called_once()
        update_call_arg = mock_reader.Root.AcroForm.update.call_args[0][0]
        # The PdfDict was constructed with NeedAppearances
        mock_pdf_dict.assert_any_call(NeedAppearances=mock_pdf_obj.return_value)
