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


# ---------------------------------------------------------------------------
# Fix A regression tests — exact document_number format (QHxx / QHxx)
# ---------------------------------------------------------------------------

def test_verify_citations_exact_doc_number_luat_ho_tich():
    """[Điều 15 Khoản 1, 60/2014/QH13] verifies when content uses '- 1.' list format."""
    from app.core.citation_formatter import verify_citations

    content = (
        "[Luật Hộ tịch 2014 > Điều 15]\n"
        "## Điều 15. Trách nhiệm đăng ký khai sinh\n\n"
        "- 1. Trong thời hạn 60 ngày kể từ ngày sinh con, cha hoặc mẹ có trách nhiệm.\n"
        "- 2. Công chức tư pháp - hộ tịch thường xuyên kiểm tra."
    )
    response = "Theo [Điều 15 Khoản 1, 60/2014/QH13], cha mẹ phải đăng ký khai sinh."
    chunks = [_make_chunk("Điều 15", "60/2014/QH13", content)]

    result = verify_citations(response, chunks)

    assert "[unverified:" not in result
    assert "[Điều 15 Khoản 1, 60/2014/QH13]" in result


def test_verify_citations_exact_doc_number_luat_nuoi_con_nuoi_khoan1():
    """[Điều 14 Khoản 1, 52/2010/QH12] verifies when content uses '1.' paragraph format."""
    from app.core.citation_formatter import verify_citations

    content = (
        "[Luật Nuôi con nuôi 2010 > Điều 14]\n"
        "Điều 14. Điều kiện đối với người nhận con nuôi\n\n"
        "1. Người nhận con nuôi phải có đủ các điều kiện sau đây:\n"
        "a) Có năng lực hành vi dân sự đầy đủ;\n"
        "2. Những người sau đây không được nhận con nuôi:\n"
        "3. Trường hợp cha dượng nhận con riêng."
    )
    response = "Theo [Điều 14 Khoản 1, 52/2010/QH12], người nhận con nuôi phải đủ điều kiện."
    chunks = [_make_chunk("Điều 14", "52/2010/QH12", content)]

    result = verify_citations(response, chunks)

    assert "[unverified:" not in result


def test_verify_citations_exact_doc_number_luat_nuoi_con_nuoi_khoan2():
    """[Điều 14 Khoản 2, 52/2010/QH12] verifies via numbered-list pattern."""
    from app.core.citation_formatter import verify_citations

    content = (
        "[Luật Nuôi con nuôi 2010 > Điều 14]\n"
        "1. Điều kiện:\na) Năng lực hành vi;\n"
        "2. Những người sau đây không được nhận con nuôi:\n"
        "3. Trường hợp đặc biệt."
    )
    response = "Theo [Điều 14 Khoản 2, 52/2010/QH12], một số người không được nhận con nuôi."
    chunks = [_make_chunk("Điều 14", "52/2010/QH12", content)]

    result = verify_citations(response, chunks)

    assert "[unverified:" not in result


def test_verify_citations_exact_doc_number_luat_nuoi_con_nuoi_khoan3():
    """[Điều 14 Khoản 3, 52/2010/QH12] verifies via numbered-list pattern."""
    from app.core.citation_formatter import verify_citations

    content = (
        "[Luật Nuôi con nuôi 2010 > Điều 14]\n"
        "1. Điều kiện chung.\n"
        "2. Những người bị cấm.\n"
        "3. Trường hợp cha dượng nhận con riêng của vợ."
    )
    response = "Theo [Điều 14 Khoản 3, 52/2010/QH12], cha dượng có thể nhận con riêng."
    chunks = [_make_chunk("Điều 14", "52/2010/QH12", content)]

    result = verify_citations(response, chunks)

    assert "[unverified:" not in result


# ---------------------------------------------------------------------------
# Multi-chunk khoản verification — khoản in second chunk for same article
# ---------------------------------------------------------------------------

def test_khoản_verified_finds_in_any_chunk():
    """verify_citations finds khoản when it appears in a second chunk for same article.

    Full-document chunking may split Điều 20 into multiple khoản-level chunks.
    The first chunk retrieved (header) lacks Khoản 1 content, but the second
    chunk contains it. _khoản_verified must search ALL matching chunks.
    """
    from app.core.citation_formatter import verify_citations

    # First chunk: Điều 20 header — no khoản 1 content
    chunk_header = _make_chunk(
        "Điều 20",
        "62/2021/NĐ-CP",
        "Điều 20. Điều kiện về chỗ ở.\n\nQuy định chung về chỗ ở hợp pháp.",
    )
    # Second chunk: Điều 20 Khoản 1 — contains the khoản reference
    chunk_khoan1 = _make_chunk(
        "Điều 20",
        "62/2021/NĐ-CP",
        "Khoản 1. Diện tích bình quân tối thiểu là 8m² sàn/người.",
    )

    response = "Theo [Điều 20 Khoản 1, Nghị định 62/2021/NĐ-CP], diện tích tối thiểu là 8m²."
    chunks = [chunk_header, chunk_khoan1]

    result = verify_citations(response, chunks)

    assert "[unverified:" not in result
    assert "[Điều 20 Khoản 1, Nghị định 62/2021/NĐ-CP]" in result


# ---------------------------------------------------------------------------
# New format — Điều X Khoản Y stored in article_number field (v3.56 chunker)
# ---------------------------------------------------------------------------

def test_verify_citations_dieu_only_matches_khoan_chunk():
    """[Điều 3, 06/2020/NQ-HĐND] must match a chunk with article_number='Điều 3 Khoản 6'.

    After the v3.56 chunker update, fee-schedule documents store chunks with
    article_number='Điều 3 Khoản 6'. A Điều-only citation must still verify
    against these chunks (backward compatibility).
    """
    from app.core.citation_formatter import verify_citations

    chunk = _make_chunk(
        "Điều 3 Khoản 6",
        "06/2020/NQ-HĐND",
        "Điều 3. Điều khoản thi hành\n6. Lệ phí hộ tịch\na. Đối tượng nộp phí là công dân.",
    )
    response = "Theo [Điều 3, 06/2020/NQ-HĐND], lệ phí hộ tịch được quy định."

    result = verify_citations(response, [chunk])

    assert "[unverified:" not in result
    assert "[Điều 3, 06/2020/NQ-HĐND]" in result


# ---------------------------------------------------------------------------
# Mục/số alternative citation format (NQ-HĐND fee-schedule documents)
# ---------------------------------------------------------------------------

def test_verify_citations_muc_so_format():
    """[Mục A, số 1, 124/2016/NQ-HĐND] is verified when doc number matches a chunk.

    HCM fee schedule (124/2016/NQ-HĐND) uses Mục/số structure.  The verifier
    must match at document-number level — the exact Mục/số sub-item does not
    need a corresponding chunk field.
    """
    from app.core.citation_formatter import verify_citations

    chunk = _make_chunk(
        "Phụ lục",
        "124/2016/NQ-HĐND",
        "Phụ lục ban hành kèm theo Nghị quyết 124/2016/NQ-HĐND\n"
        "Mục A. Đăng ký hộ tịch tại UBND cấp xã\n"
        "1. Đăng ký khai sinh: 8.000 đồng",
    )
    response = (
        "Lệ phí đăng ký khai sinh tại TP.HCM là 8.000 đồng "
        "[Mục A, số 1, 124/2016/NQ-HĐND]."
    )

    result = verify_citations(response, [chunk])

    assert "[unverified:" not in result
    assert "[Mục A, số 1, 124/2016/NQ-HĐND]" in result


def test_verify_citations_phu_luc_format():
    """[Phụ lục, 05/2025/NQ-HĐND] is verified when doc number matches a chunk.

    Da Nang fee schedule (05/2025/NQ-HĐND) stores amounts in a Phụ lục appendix.
    The bare [Phụ lục, doc_number] citation format must be recognised and verified.
    """
    from app.core.citation_formatter import verify_citations

    chunk = _make_chunk(
        "Phụ lục",
        "05/2025/NQ-HĐND",
        "Biểu mức thu lệ phí hộ tịch trên địa bàn thành phố Đà Nẵng\n"
        "1. Đăng ký khai sinh: 5.000 đồng\n"
        "2. Đăng ký kết hôn: 20.000 đồng",
    )
    response = (
        "Theo biểu phí [Phụ lục, 05/2025/NQ-HĐND], "
        "lệ phí đăng ký khai sinh tại Đà Nẵng là 5.000 đồng."
    )

    result = verify_citations(response, [chunk])

    assert "[unverified:" not in result
    assert "[Phụ lục, 05/2025/NQ-HĐND]" in result


def test_verify_citations_muc_so_flagged_when_doc_missing():
    """[Mục A, số 1, 124/2016/NQ-HĐND] is flagged when no chunk matches the doc number."""
    from app.core.citation_formatter import verify_citations

    chunk = _make_chunk("Điều 3", "06/2020/NQ-HĐND", "unrelated content")
    response = "Lệ phí là 8.000 đồng [Mục A, số 1, 124/2016/NQ-HĐND]."

    result = verify_citations(response, [chunk])

    assert "[unverified:" in result
    assert "Mục A" in result
