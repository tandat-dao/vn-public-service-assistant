"""OCR node — extracts personal data from uploaded identity documents."""

from app.agents.state import AgentState


def ocr_node(state: AgentState) -> dict:
    """Run OCR pipeline on uploaded_image_path and populate personal_data."""
    raise NotImplementedError
