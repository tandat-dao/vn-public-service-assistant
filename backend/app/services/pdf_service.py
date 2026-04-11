"""PDF service — detects AcroForm vs flat PDF and fills form fields accordingly.

Partially filled PDFs are always written to a ``tmp/`` MinIO prefix and only
promoted to the final path when the caller confirms all required fields are present.

StorageService is injected via the constructor — PDFService never instantiates it
internally.  This keeps both services independently testable.

Note: The flat-PDF overlay fill (_fill_overlay) places text at approximate positions.
Exact coordinates require per-form mapping which will be implemented in TASK-15 when
real form templates are collected.
"""

import io
import os
import tempfile
from typing import Any

import pdfrw
import pdfplumber
import structlog
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.services.storage_service import StorageService

logger = structlog.get_logger(__name__)

# pdfrw annotation constants
_ANNOT_KEY = "/Annots"
_SUBTYPE_KEY = "/Subtype"
_WIDGET = "/Widget"
_FIELD_NAME_KEY = "/T"
_PARENT_KEY = "/Parent"


class PDFService:
    """PDF template fill service using pdfrw (AcroForm) or reportlab (flat overlay)."""

    def __init__(self, storage_service: StorageService) -> None:
        self._storage = storage_service

    async def fill(
        self,
        template_minio_path: str,
        field_values: dict[str, str],
        session_id: str,
        form_id: str,
    ) -> str:
        """Download template from MinIO, fill fields, upload to tmp prefix.

        Returns the MinIO path ``tmp/{session_id}/{form_id}.pdf``.
        Never writes directly to the final path — caller must call
        StorageService.promote_tmp() after confirming all required fields.
        """
        # 1. Download template bytes from MinIO
        template_bytes = await self._storage.download(template_minio_path)

        # 2. Write to a temp file for PDF library access
        tmp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        try:
            tmp_file.write(template_bytes)
            tmp_file.flush()
            tmp_path = tmp_file.name
        finally:
            tmp_file.close()

        try:
            # 3. Detect PDF type via pdfplumber
            with pdfplumber.open(tmp_path) as pdf:
                is_acroform = pdf.doc.catalog.get("AcroForm") is not None

            # 4. Fill
            if is_acroform:
                filled_bytes = self._fill_acroform(tmp_path, field_values)
            else:
                filled_bytes = self._fill_overlay(tmp_path, field_values)
        finally:
            # 5. Clean up temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        # 6. Upload to tmp/ prefix in MinIO
        output_path = f"tmp/{session_id}/{form_id}.pdf"
        await self._storage.upload(output_path, filled_bytes, "application/pdf")

        logger.info(
            "PDF filled and uploaded",
            template=template_minio_path,
            output=output_path,
            acroform=is_acroform,
            fields=len(field_values),
        )

        # 7. Return MinIO path
        return output_path

    def _fill_acroform(self, template_path: str, field_values: dict[str, str]) -> bytes:
        """Fill an AcroForm PDF using pdfrw.

        Sets /NeedAppearances=True so PDF viewers regenerate field appearances.
        """
        reader = pdfrw.PdfReader(template_path)

        # Enable appearance regeneration
        if reader.Root.AcroForm:
            reader.Root.AcroForm.update(
                pdfrw.PdfDict(NeedAppearances=pdfrw.PdfObject("true"))
            )

        for page in reader.pages:
            annotations = page.get(_ANNOT_KEY)
            if not annotations:
                continue
            for annotation in annotations:
                if annotation.get(_SUBTYPE_KEY) != _WIDGET:
                    continue
                field_name = _get_field_name(annotation)
                if field_name and field_name in field_values:
                    annotation.update(
                        pdfrw.PdfDict(V=f"{field_values[field_name]}", AP="")
                    )

        buf = io.BytesIO()
        pdfrw.PdfWriter().write(buf, reader)
        return buf.getvalue()

    def _fill_overlay(self, template_path: str, field_values: dict[str, str]) -> bytes:
        """Overlay text onto a flat (non-AcroForm) PDF using reportlab.

        NOTE: Field positions are approximate (top-left quadrant, stacked vertically).
        Exact positioning requires per-form coordinate mapping — to be addressed in TASK-15
        when real form templates are collected.
        """
        # Build overlay
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=A4)
        c.setFont("Helvetica", 10)

        y = A4[1] - 60  # start near top
        for i, (field_name, value) in enumerate(field_values.items()):
            c.drawString(50, y - i * 20, f"{field_name}: {value}")
            if y - i * 20 < 50:
                c.showPage()
                y = A4[1] - 60

        c.save()
        packet.seek(0)

        # Merge overlay onto each page of the template
        overlay_reader = pdfrw.PdfReader(packet)
        base_reader = pdfrw.PdfReader(template_path)

        writer = pdfrw.PdfWriter()
        for i, page in enumerate(base_reader.pages):
            if overlay_reader.pages and i < len(overlay_reader.pages):
                merger = pdfrw.PageMerge(page)
                merger.add(overlay_reader.pages[min(i, len(overlay_reader.pages) - 1)]).render()
            writer.addpage(page)

        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()

    def get_field_names(self, template_path: str) -> list[str]:
        """Return all AcroForm field names (empty list for flat PDFs)."""
        reader = pdfrw.PdfReader(template_path)
        if reader.Root.AcroForm is None:
            return []
        fields: list[str] = []
        for page in reader.pages:
            for annotation in (page.get(_ANNOT_KEY) or []):
                name = _get_field_name(annotation)
                if name:
                    fields.append(name)
        return fields

    def is_acroform(self, template_path: str) -> bool:
        """Return True if the PDF contains fillable AcroForm fields."""
        with pdfplumber.open(template_path) as pdf:
            return pdf.doc.catalog.get("AcroForm") is not None


def _get_field_name(annotation: Any) -> str | None:
    """Extract the /T field name from a PDF annotation, traversing /Parent if needed."""
    if annotation.get(_FIELD_NAME_KEY):
        raw = annotation[_FIELD_NAME_KEY]
        return raw[1:-1] if isinstance(raw, str) and raw.startswith("(") else str(raw)
    parent = annotation.get(_PARENT_KEY)
    if parent and parent.get(_FIELD_NAME_KEY):
        raw = parent[_FIELD_NAME_KEY]
        return raw[1:-1] if isinstance(raw, str) and raw.startswith("(") else str(raw)
    return None
