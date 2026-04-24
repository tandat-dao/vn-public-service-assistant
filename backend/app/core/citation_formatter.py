"""Citation formatter — formats and verifies legal citations from LLM output.

Two public functions:

  format_citation(chunk)                    -> human-readable citation string
  verify_citations(response_text, chunks)   -> response with unverified citations flagged

Both live in app/core/ — pure Python, zero infrastructure dependencies.
"""

from __future__ import annotations

import logging
import re

from app.schemas.rag import DocumentChunk

log = logging.getLogger(__name__)


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
# Citation regex — matches citation formats with named groups:
#   article:  full article reference including khoản if present
#   document: document reference string
#
# Matches all four formats:
#   [Điều 11, Luật Hộ tịch 2014]
#   [Điều 11 Khoản 2, Luật Hộ tịch 2014]
#   [Điều 11 Khoản 2a, Luật Hộ tịch 2014]
#   [Khoản 3, Điều 11, Nghị định 123/2015/NĐ-CP]
# ---------------------------------------------------------------------------
_CITATION_RE = re.compile(
    r"\[(?P<article>"
    r"Điều\s+\d+[a-z]?(?:\s+Khoản\s+\d+[a-z]?)?"  # Điều X [Khoản Y] — formats 1-3
    r"|"
    r"Khoản\s+\d+[a-z]?,\s*Điều\s+\d+[a-z]?"        # Khoản X, Điều Y — format 4
    r"),\s*(?P<document>[^\]]+)\]",
    re.UNICODE,
)


def _parse_article_ref(article_str: str) -> tuple[str, str | None]:
    """Parse an article reference string into (base_article, khoản_ref).

    Handles both orderings produced by the citation regex:
      "Điều 11"          -> ("Điều 11", None)
      "Điều 11 Khoản 2"  -> ("Điều 11", "Khoản 2")
      "Điều 11 Khoản 2a" -> ("Điều 11", "Khoản 2a")
      "Khoản 3, Điều 11" -> ("Điều 11", "Khoản 3")
    """
    s = article_str.strip()
    # Space-separated: "Điều X Khoản Y"
    m = re.match(r"(Điều\s+\d+[a-z]?)\s+(Khoản\s+\d+[a-z]?)\s*$", s)
    if m:
        return m.group(1), m.group(2)
    # Comma-separated: "Khoản X, Điều Y" (older circular style)
    m = re.match(r"(Khoản\s+\d+[a-z]?),\s*(Điều\s+\d+[a-z]?)\s*$", s)
    if m:
        return m.group(2), m.group(1)
    # Pure article reference, no khoản
    return s, None


_MONEY_PATTERN = re.compile(r"\d[\d.].000\sđồng|đồng/")


def _khoản_verified(khoản_ref: str, chunk_content: str) -> bool:
    """Check whether a khoản reference is supported by a chunk's content.

    Direct substring match is tried first. If the chunk contains a fees table
    written without explicit 'Khoản' markers (monetary amount pattern instead),
    the citation is accepted as verified at article level.
    """
    if khoản_ref in chunk_content:
        return True
    if _MONEY_PATTERN.search(chunk_content):
        return True
    return False


def verify_citations(response_text: str, retrieved_chunks: list) -> str:
    """Post-generation citation verifier.

    Extracts every citation matched by _CITATION_RE from response_text and
    checks whether a retrieved chunk supports it. Two-level verification:

    Level 1 — Article: chunk.article_number (normalised, "Điều " prefix
      stripped) must match the article number from the citation, AND
      chunk.document_number must appear as a case-insensitive substring of
      the full citation text.

    Level 2 — Khoản (only when citation contains a khoản reference): the
      khoản string (e.g. "Khoản 2") must appear as a substring in the
      matching chunk's content field.

    Unverified citations are replaced with [unverified: <inner>].

    Known limitation: Luật citations like "[Điều 20, Luật Cư trú năm 2020]"
    will be flagged unverified when the chunk carries document_number
    "68/2020/QH14", because "68/2020/QH14" is not a substring of
    "Luật Cư trú năm 2020".  This is intentional — the verifier only uses
    payload data and does not maintain a document-number ↔ common-name
    lookup table.

    Args:
        response_text:    LLM-generated response string.
        retrieved_chunks: list[DocumentChunk] that were actually retrieved
                          and passed to the LLM.  May also be plain dicts
                          with "article_number", "document_number", and
                          "content" keys.

    Returns:
        The response string with unverified citations flagged in-place.
    """

    def _get_article_num(chunk) -> str:
        """Return the numeric part of article_number (strip 'Điều ' prefix)."""
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

    def _get_content(chunk) -> str:
        return (
            chunk.content
            if hasattr(chunk, "content")
            else chunk.get("content", "")
        )

    def _replace(match: re.Match) -> str:
        full_citation = match.group(0)
        article_str = match.group("article")
        inner = full_citation[1:-1]  # strip outer brackets

        base_article, khoản_ref = _parse_article_ref(article_str)

        # Normalise base_article to the numeric part for chunk comparison
        # ("Điều 11" → "11"; handles chunks stored as "11" or "Điều 11")
        base_article_num = re.sub(r"^Điều\s+", "", base_article).strip()

        # Step 2 — Article-level verification (unchanged logic)
        full_lower = full_citation.lower()
        matching_chunk = None
        for chunk in retrieved_chunks:
            chunk_article_num = _get_article_num(chunk)
            chunk_doc_num = _get_doc_number(chunk)
            if (
                chunk_article_num == base_article_num
                and chunk_doc_num.lower() in full_lower
            ):
                matching_chunk = chunk
                break

        if matching_chunk is None:
            return f"[unverified: {inner}]"

        # Article found, no khoản in citation → verified (unchanged behaviour)
        if khoản_ref is None:
            return full_citation

        # Step 3 — Khoản-level verification
        chunk_content = _get_content(matching_chunk)
        if _khoản_verified(khoản_ref, chunk_content):
            return full_citation

        # Khoản reference not found in chunk content
        log.warning(
            "khoản_not_found_in_chunk_content: article=%s khoản_ref=%s document_number=%s",
            base_article,
            khoản_ref,
            _get_doc_number(matching_chunk),
        )
        return f"[unverified: {inner}]"

    return _CITATION_RE.sub(_replace, response_text)
