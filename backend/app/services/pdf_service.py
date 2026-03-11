"""PDF service — detects AcroForm vs flat PDF and fills form fields accordingly."""


class PDFService:
    """PDF template fill service using pdfrw (AcroForm) or reportlab (flat overlay)."""

    def fill(self, template_path: str, field_values: dict[str, str]) -> str:
        """
        Auto-detect PDF type and fill fields. Returns path to filled PDF in MinIO.
        Raises ValueError if a required field cannot be filled (never fails silently).
        """
        raise NotImplementedError
