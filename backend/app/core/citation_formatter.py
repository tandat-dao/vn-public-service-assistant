"""Citation formatter — formats and verifies legal citations from LLM output.

Two public functions:

  format_citation(chunk)                    -> human-readable citation string
  verify_citations(response_text, chunks)   -> response with unverified citations flagged

Both live in app/core/ — pure Python, zero infrastructure dependencies.
"""

from __future__ import annotations

import re

from app.schemas.rag import DocumentChunk


def format_citation(chunk: DocumentChunk) -> str:
    """Return a human-readable citation string from a DocumentChunk's payload.

    Example output: "[Điều 20, 62/2021/NĐ-CP]"

    Args:
        chunk: A DocumentChunk returned by QdrantService.search().

    Returns:
        A bracketed citation string.
    """
    return f"[{chunk.article_number}, {chunk.document_number}]"


# ---------------------------------------------------------------------------
# Citation regex — matches [Điều X, <anything>] and [Điều Xa, <anything>]
# Group 1: article number (digits + optional lowercase letter)
# Group 2: full citation text inside brackets (used for substring matching)
# ---------------------------------------------------------------------------
_CITATION_RE = re.compile(r"\[Điều\s+(\d+[a-z]?),\s*([^\]]+)\]")


def verify_citations(response_text: str, retrieved_chunks: list) -> str:
    """Post-generation citation verifier.

    Extracts every [Điều X, ...] citation from response_text and checks
    whether a retrieved chunk supports it.  Matching rule:

      A citation is VERIFIED when ANY retrieved chunk satisfies BOTH:
        1. chunk.article_number (digits only, "Điều " prefix stripped) ==
           the article number extracted from the citation.
        2. chunk.document_number appears as a case-insensitive substring
           of the full citation text (e.g. "62/2021/NĐ-CP" in
           "[Điều 20, Nghị định 62/2021/NĐ-CP]").

    If no chunk satisfies both conditions the citation is replaced with:
        [unverified: Điều X, <original text>]

    Known limitation: Luật citations like "[Điều 20, Luật Cư trú năm 2020]"
    will be flagged unverified when the chunk carries document_number
    "68/2020/QH14", because that number is not a substring of
    "Luật Cư trú năm 2020".  This is intentional — the verifier only uses
    payload data and does not maintain a document-number ↔ common-name
    lookup table.

    Args:
        response_text:    LLM-generated response string.
        retrieved_chunks: list[DocumentChunk] that were actually retrieved
                          and passed to the LLM.  May also be plain dicts
                          with "article_number" and "document_number" keys.

    Returns:
        The response string with unverified citations flagged in-place.
    """

    def _get_article(chunk) -> str:
        """Return just the numeric part of article_number (strip 'Điều ' prefix)."""
        raw = (
            chunk.article_number
            if hasattr(chunk, "article_number")
            else chunk.get("article_number", "")
        )
        return re.sub(r"^Điều\s+", "", raw).strip()

    def _get_doc_number(chunk) -> str:
        return (
            chunk.document_number
            if hasattr(chunk, "document_number")
            else chunk.get("document_number", "")
        )

    def _check_match(full_citation: str, article_num: str) -> bool:
        """Return True if any retrieved chunk verifies this citation."""
        full_lower = full_citation.lower()
        for chunk in retrieved_chunks:
            chunk_article = _get_article(chunk)
            chunk_doc_num = _get_doc_number(chunk)
            if chunk_article == article_num and chunk_doc_num.lower() in full_lower:
                return True
        return False

    def _replace(match: re.Match) -> str:
        full_citation = match.group(0)   # e.g. "[Điều 20, Nghị định 62/2021/NĐ-CP]"
        article_num = match.group(1)     # e.g. "20"
        inner = match.group(0)[1:-1]     # strip outer brackets

        if _check_match(full_citation, article_num):
            return full_citation
        return f"[unverified: {inner}]"

    return _CITATION_RE.sub(_replace, response_text)
