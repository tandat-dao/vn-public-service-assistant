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

# ---------------------------------------------------------------------------
# Alternative citation regex — matches Mục/số/Phụ lục patterns used in
# NQ-HĐND fee-schedule documents (e.g. 124/2016/NQ-HĐND, 05/2025/NQ-HĐND)
# that use section/item structure instead of Điều/Khoản.
#
# Matches:
#   [Mục A, số 1, 124/2016/NQ-HĐND]
#   [số 3, Phụ lục, 124/2016/NQ-HĐND]
#   [Phụ lục, 05/2025/NQ-HĐND]
# ---------------------------------------------------------------------------
_ALT_CITATION_RE = re.compile(
    r"\[(?:Mục|số|Phụ lục)[^\]]*(?:/NQ-|/TT-|/NĐ-|/QH|/VBHN)[^\]]*\]",
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
_KHOAN_NUM_RE = re.compile(r"Khoản\s+(\d+)", re.UNICODE)


def _khoản_in_content(khoản_ref: str, content: str) -> bool:
    """Check whether a khoản reference is supported by a single chunk's content.

    Three acceptance paths (in order):
      1. Direct substring: "Khoản 1" appears verbatim in content.
      2. Numbered-list: "1." at the start of a paragraph (after newline or start
         of string), optionally preceded by a Markdown "- " list marker. This
         handles YAML-ingested chunks where paragraphs are written as "1. Text"
         or "- 1. Text" rather than "Khoản 1. Text".
      3. Fees-table fallback: monetary amount pattern present — accept at article
         level (fees table format suppresses explicit Khoản markers).
    """
    if khoản_ref in content:
        return True
    m = _KHOAN_NUM_RE.search(khoản_ref)
    if m:
        num = re.escape(m.group(1))
        if re.search(r"(?:^|\n)-?\s*" + num + r"\.", content):
            return True
    if _MONEY_PATTERN.search(content):
        return True
    return False


def _khoản_verified(
    khoản_ref: str,
    all_chunks: list,
    article_num: str,
    document_num: str,
) -> bool:
    """Check khoản reference against ALL retrieved chunks for the matching article.

    With full-document chunking an article may be split across multiple khoản-level
    chunks. Searching only the first retrieved chunk for the article misses khoản
    references whose content lives in a sibling chunk. This function finds ALL
    chunks that match (article_num, document_num) and checks each one, returning
    True as soon as any chunk satisfies the khoản reference.

    Args:
        khoản_ref:   e.g. "Khoản 1" or "Khoản 2a"
        all_chunks:  full list of retrieved DocumentChunk objects (or dicts)
        article_num: numeric article string with no "Điều " prefix (e.g. "14")
        document_num: document number to match (e.g. "52/2010/QH12")
    """
    for chunk in all_chunks:
        raw_art = (
            chunk.article_number if hasattr(chunk, "article_number")
            else chunk.get("article_number", "")
        ) or ""
        # Strip "Điều " prefix then "Khoản N" suffix so "Điều 3 Khoản 6"
        # compares equal to base article_num "3".
        chunk_art_stripped = re.sub(r"^Điều\s+", "", raw_art).strip()
        chunk_art_num = re.sub(r"\s+Khoản\s+\d+.*$", "", chunk_art_stripped).strip()

        chunk_doc_num = (
            chunk.document_number if hasattr(chunk, "document_number")
            else chunk.get("document_number", "")
        ) or ""

        if chunk_art_num != article_num:
            continue
        if document_num.lower() not in chunk_doc_num.lower():
            continue

        content = (
            chunk.content if hasattr(chunk, "content")
            else chunk.get("content", "")
        ) or ""
        if _khoản_in_content(khoản_ref, content):
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
        """Return the base article number, stripping 'Điều ' prefix and
        any ' Khoản N' suffix so that a Điều-only citation matches chunks
        stored as 'Điều X Khoản Y'.
        """
        raw = (
            chunk.article_number
            if hasattr(chunk, "article_number")
            else chunk.get("article_number", "")
        ) or ""
        without_dieu = re.sub(r"^Điều\s+", "", raw).strip()
        return re.sub(r"\s+Khoản\s+\d+.*$", "", without_dieu).strip()

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

        # Step 3 — Khoản-level verification against ALL chunks for this article.
        # An article may be split across multiple khoản-level chunks after
        # full-document chunking; searching only matching_chunk misses siblings.
        chunk_doc_num = _get_doc_number(matching_chunk)
        if _khoản_verified(khoản_ref, retrieved_chunks, base_article_num, chunk_doc_num):
            return full_citation

        # Khoản reference not found in any matching chunk's content
        log.warning(
            "khoản_not_found_in_any_chunk: article=%s khoản_ref=%s document_number=%s",
            base_article,
            khoản_ref,
            chunk_doc_num,
        )
        return f"[unverified: {inner}]"

    # --- Second pass: Mục/số/Phụ lục alternative citation format ---
    # Verification is permissive: if the document number (last comma-separated
    # component) matches any retrieved chunk's document_number, the citation
    # is verified.  The exact sub-item reference (Mục, số N) does not need to
    # match a separate chunk field — fee-schedule Phụ lục chunks are stored
    # at document level.
    def _replace_alt(match: re.Match) -> str:
        full_citation = match.group(0)
        inner = full_citation[1:-1]
        parts = [p.strip() for p in inner.split(",")]
        doc_num = parts[-1] if parts else ""
        for chunk in retrieved_chunks:
            chunk_doc = _get_doc_number(chunk)
            if doc_num and (
                doc_num.lower() in chunk_doc.lower()
                or chunk_doc.lower() in doc_num.lower()
            ):
                return full_citation
        log.warning(
            "alt_citation_doc_not_in_chunks: doc_number=%s",
            doc_num,
        )
        return f"[unverified: {inner}]"

    intermediate = _CITATION_RE.sub(_replace, response_text)
    return _ALT_CITATION_RE.sub(_replace_alt, intermediate)
