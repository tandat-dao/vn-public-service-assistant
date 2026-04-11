"""Unit tests for app.core.citation_formatter.

Covers format_citation() and verify_citations() directly,
independent of rag_fn.
"""

from __future__ import annotations

from app.schemas.rag import DocumentChunk


def _make_chunk(
    article_number: str,
    document_number: str,
    content: str = "text",
) -> DocumentChunk:
    return DocumentChunk(
        point_id="p-1",
        legal_document_id="doc-uuid-1",
        document_number=document_number,
        article_number=article_number,
        content=content,
        procedure_tags=[],
        status="active",
        rrf_score=0.9,
    )


# ---------------------------------------------------------------------------
# format_citation
# ---------------------------------------------------------------------------

def test_format_citation_returns_correct_string():
    """format_citation must include article_number and document_number in brackets."""
    from app.core.citation_formatter import format_citation

    chunk = _make_chunk("Điều 20", "62/2021/NĐ-CP")
    result = format_citation(chunk)

    assert result.startswith("[")
    assert result.endswith("]")
    assert "Điều 20" in result
    assert "62/2021/NĐ-CP" in result


# ---------------------------------------------------------------------------
# verify_citations — hallucinated article → flagged
# ---------------------------------------------------------------------------

def test_verify_citations_flags_hallucinated_article():
    """verify_citations must flag citations whose article number is not in any chunk."""
    from app.core.citation_formatter import verify_citations

    response = "Theo [Điều 99, Nghị định 62/2021/NĐ-CP], điều này áp dụng."
    chunks = [_make_chunk("20", "62/2021/NĐ-CP")]

    result = verify_citations(response, chunks)

    assert "[unverified:" in result
    assert "Điều 99" in result
    # Original citation text preserved inside the unverified marker
    assert "62/2021/NĐ-CP" in result


# ---------------------------------------------------------------------------
# verify_citations — matching citation → unchanged
# ---------------------------------------------------------------------------

def test_verify_citations_passes_correct_citation():
    """verify_citations must not alter a citation that matches a chunk."""
    from app.core.citation_formatter import verify_citations

    response = "Theo [Điều 20, Nghị định 62/2021/NĐ-CP], điều này áp dụng."
    chunks = [_make_chunk("20", "62/2021/NĐ-CP")]

    result = verify_citations(response, chunks)

    assert "[unverified:" not in result
    assert "[Điều 20, Nghị định 62/2021/NĐ-CP]" in result


# ---------------------------------------------------------------------------
# verify_citations — Luật format → flagged (documented limitation)
# ---------------------------------------------------------------------------

def test_verify_citations_luat_format_is_flagged():
    """[Điều 20, Luật Cư trú năm 2020] is flagged as unverified.

    Chunk carries document_number="68/2020/QH14".  The substring "68/2020/QH14"
    does not appear in "Luật Cư trú năm 2020", so the verifier cannot confirm
    the match.  This is the documented limitation of substring-based matching.
    """
    from app.core.citation_formatter import verify_citations

    response = "Theo [Điều 20, Luật Cư trú năm 2020], công dân có quyền đăng ký."
    chunks = [_make_chunk("20", "68/2020/QH14")]

    result = verify_citations(response, chunks)

    assert "[unverified:" in result
