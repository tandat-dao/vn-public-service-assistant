"""Citation formatter — parses and formats legal citations from LLM output."""

from app.schemas.chat import Citation


def parse_citations(text: str, retrieved_chunks: list[dict]) -> list[Citation]:
    """
    Extract citation markers from LLM output and map them to retrieved chunks.
    Format: [Điều X, Nghị định/Thông tư YYY/YYYY/NĐ-CP]
    """
    raise NotImplementedError


def build_citations(chunks: list[dict]) -> list[Citation]:
    """Build Citation objects from a list of retrieved DocumentChunk dicts."""
    raise NotImplementedError
