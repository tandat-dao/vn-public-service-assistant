"""Unit tests for rag_fn worker function (app.agents.nodes.rag).

All Qdrant and LLM calls are mocked — no real API calls here.
asyncio_mode=auto is set in pyproject.toml so async test functions run directly.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.rag import DocumentChunk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunk(
    article_number: str,
    document_number: str,
    content: str = "Nội dung điều luật về đăng ký cư trú.",
    rrf_score: float = 0.9,
    structured_summary: str | None = None,
) -> DocumentChunk:
    return DocumentChunk(
        point_id=f"p-{article_number}",
        legal_document_id="doc-uuid-1",
        document_number=document_number,
        article_number=article_number,
        content=content,
        procedure_tags=["TTHC-001"],
        status="active",
        rrf_score=rrf_score,
        structured_summary=structured_summary,
    )


def _base_state(**overrides) -> dict:
    state: dict = {
        "user_message": "Tôi cần đăng ký thường trú tại Hồ Chí Minh",
        "session_id": "sess-test-001",
        "iteration_count": 0,
        "target_procedure_id": None,
        "filing_jurisdiction": None,
        "entities": {},
        "errors": [],
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_qdrant():
    """Patch _get_qdrant to return an AsyncMock QdrantService."""
    svc = AsyncMock()
    svc.search = AsyncMock(return_value=[])
    with patch("app.agents.nodes.rag._get_qdrant", return_value=svc):
        yield svc


@pytest.fixture
def mock_llm():
    """Patch _get_llm to return an AsyncMock LLMService."""
    svc = AsyncMock()
    svc.async_invoke = AsyncMock(
        return_value=(
            "Theo quy định tại [Điều 20, Nghị định 62/2021/NĐ-CP], "
            "hồ sơ đăng ký thường trú cần có các giấy tờ sau..."
        )
    )
    with patch("app.agents.nodes.rag._get_llm", return_value=svc):
        yield svc


# ---------------------------------------------------------------------------
# Test 1 — happy path: returns all expected keys
# ---------------------------------------------------------------------------

async def test_rag_fn_returns_citations_for_residence_query(mock_qdrant, mock_llm):
    """rag_fn returns retrieved_chunks, citations, final_response, scope_used."""
    chunks = [
        _make_chunk("20", "62/2021/NĐ-CP", rrf_score=0.92),
        _make_chunk("21", "62/2021/NĐ-CP", rrf_score=0.85),
        _make_chunk("22", "62/2021/NĐ-CP", rrf_score=0.78),
    ]
    mock_qdrant.search.return_value = chunks
    mock_llm.async_invoke.return_value = (
        "Theo [Điều 20, Nghị định 62/2021/NĐ-CP], thủ tục đăng ký thường trú..."
    )

    from app.agents.nodes.rag import rag_fn

    result = await rag_fn(_base_state())

    assert "retrieved_chunks" in result
    assert "citations" in result
    assert "final_response" in result
    assert "scope_used" in result
    # _base_state has no location_scope set — city scope comes from the router LLM
    # (not from keyword detection in rag.py). Without location_scope in state,
    # the cascade starts at "VN" (the default when no filing_jurisdiction is set).
    assert result["scope_used"] == "VN"
    assert len(result["retrieved_chunks"]) > 0
    assert len(result["citations"]) > 0


# ---------------------------------------------------------------------------
# Test 2 — cascade fallback to broader scope
# ---------------------------------------------------------------------------

async def test_rag_fn_cascade_fallback_to_broader_scope(mock_qdrant, mock_llm):
    """rag_fn tries most-specific scope first, falls back to VN on empty results."""
    chunks_vn = [
        _make_chunk("10", "62/2021/NĐ-CP", rrf_score=0.8),
        _make_chunk("11", "62/2021/NĐ-CP", rrf_score=0.75),
    ]

    def search_side_effect(query=None, procedure_id=None, scope=None, top_k=None):
        if scope in ("VN-HCM-26968", "VN-HCM"):
            return []
        return chunks_vn

    mock_qdrant.search.side_effect = search_side_effect
    mock_llm.async_invoke.return_value = "Trả lời chung về cư trú."

    from app.agents.nodes.rag import rag_fn

    result = await rag_fn(_base_state(filing_jurisdiction="VN-HCM-26968"))

    assert result["scope_used"] == "VN"
    assert len(result["retrieved_chunks"]) == 2


# ---------------------------------------------------------------------------
# Test 3 — all scopes return empty → LLM never called
# ---------------------------------------------------------------------------

async def test_rag_fn_all_scopes_empty_returns_error_no_llm_call(mock_qdrant, mock_llm):
    """When all scopes return no chunks, LLM must not be called."""
    mock_qdrant.search.return_value = []

    from app.agents.nodes.rag import rag_fn

    result = await rag_fn(_base_state(filing_jurisdiction="VN-HCM-26968"))

    mock_llm.async_invoke.assert_not_called()
    assert result["retrieved_chunks"] == []
    assert result["citations"] == []
    assert len(result.get("errors", [])) > 0


# ---------------------------------------------------------------------------
# Test 4 — Qdrant exception → graceful error dict
# ---------------------------------------------------------------------------

async def test_rag_fn_qdrant_exception_does_not_crash(mock_qdrant, mock_llm):
    """rag_fn must not raise when Qdrant raises an exception."""
    mock_qdrant.search.side_effect = RuntimeError("Qdrant connection refused")

    from app.agents.nodes.rag import rag_fn

    result = await rag_fn(_base_state())

    assert isinstance(result, dict)
    assert len(result.get("errors", [])) > 0
    assert result["retrieved_chunks"] == []


# ---------------------------------------------------------------------------
# Test 5 — verify_citations flags hallucinated article number
# ---------------------------------------------------------------------------

def test_verify_citations_flags_hallucinated_article():
    """verify_citations flags citations for articles not in retrieved chunks."""
    from app.core.citation_formatter import verify_citations

    response = "Theo [Điều 99, Nghị định 62/2021/NĐ-CP], điều này áp dụng."
    chunks = [_make_chunk("20", "62/2021/NĐ-CP")]

    result = verify_citations(response, chunks)

    assert "[unverified:" in result
    assert "Điều 99" in result


# ---------------------------------------------------------------------------
# Test 6 — verify_citations leaves correct citation unchanged
# ---------------------------------------------------------------------------

def test_verify_citations_passes_correct_citation():
    """verify_citations must not flag a citation that matches a retrieved chunk."""
    from app.core.citation_formatter import verify_citations

    response = "Theo [Điều 20, Nghị định 62/2021/NĐ-CP], điều này áp dụng."
    chunks = [_make_chunk("20", "62/2021/NĐ-CP")]

    result = verify_citations(response, chunks)

    assert "[unverified:" not in result
    assert "[Điều 20, Nghị định 62/2021/NĐ-CP]" in result


# ---------------------------------------------------------------------------
# Test 7 — Luật citation is flagged as unverified (known limitation)
# ---------------------------------------------------------------------------

def test_verify_citations_luat_format_no_false_flag():
    """[Điều 20, Luật Cư trú năm 2020] is flagged as unverified because
    document_number '68/2020/QH14' is not a substring of 'Luật Cư trú năm 2020'.
    This is a documented limitation — the verifier uses substring matching only."""
    from app.core.citation_formatter import verify_citations

    response = "Theo [Điều 20, Luật Cư trú năm 2020], công dân có quyền đăng ký."
    chunks = [_make_chunk("20", "68/2020/QH14")]

    result = verify_citations(response, chunks)

    # Expected: flagged unverified (document_number not substring of citation text)
    assert "[unverified:" in result


# ---------------------------------------------------------------------------
# Test 8 — threshold stopping drops low-score chunks
# ---------------------------------------------------------------------------

async def test_threshold_stopping_drops_low_score_chunks(mock_qdrant, mock_llm):
    """Chunks with RRF score below RAG_MIN_SCORE_THRESHOLD (0.01) are dropped."""
    chunks = [
        _make_chunk("10", "62/2021/NĐ-CP", rrf_score=0.8),
        _make_chunk("11", "62/2021/NĐ-CP", rrf_score=0.005),  # below threshold 0.01
    ]
    mock_qdrant.search.return_value = chunks
    mock_llm.async_invoke.return_value = "Trả lời về đăng ký cư trú."

    from app.agents.nodes.rag import rag_fn

    result = await rag_fn(_base_state())

    assert len(result["retrieved_chunks"]) == 1
    assert result["retrieved_chunks"][0].article_number == "10"


# ---------------------------------------------------------------------------
# Test 9 — confidence scoring: high
# ---------------------------------------------------------------------------

async def test_confidence_scoring_high(mock_qdrant, mock_llm):
    """confidence is 'high' when top RRF > 0.025 AND at least 3 chunks returned.
    RRF max is ~0.033 (1/(1+60) per source); scores are calibrated to that range."""
    chunks = [
        _make_chunk("10", "62/2021/NĐ-CP", rrf_score=0.030),
        _make_chunk("11", "62/2021/NĐ-CP", rrf_score=0.028),
        _make_chunk("12", "62/2021/NĐ-CP", rrf_score=0.026),
    ]
    mock_qdrant.search.return_value = chunks
    mock_llm.async_invoke.return_value = "Trả lời."

    from app.agents.nodes.rag import rag_fn

    result = await rag_fn(_base_state())

    assert result["response_metadata"]["rag_confidence"] == "high"


# ---------------------------------------------------------------------------
# Test 10 — confidence scoring: low
# ---------------------------------------------------------------------------

async def test_confidence_scoring_low(mock_qdrant, mock_llm):
    """confidence is 'low' when top RRF score ≤ 0.016."""
    chunks = [
        _make_chunk("10", "62/2021/NĐ-CP", rrf_score=0.012),
    ]
    mock_qdrant.search.return_value = chunks
    mock_llm.async_invoke.return_value = "Trả lời."

    from app.agents.nodes.rag import rag_fn

    result = await rag_fn(_base_state())

    assert result["response_metadata"]["rag_confidence"] == "low"


# ---------------------------------------------------------------------------
# Test 10b — confidence scoring: medium
# ---------------------------------------------------------------------------

async def test_confidence_scoring_medium(mock_qdrant, mock_llm):
    """confidence is 'medium' when 0.016 < top RRF ≤ 0.025."""
    chunks = [
        _make_chunk("10", "62/2021/NĐ-CP", rrf_score=0.020),
        _make_chunk("11", "62/2021/NĐ-CP", rrf_score=0.018),
    ]
    mock_qdrant.search.return_value = chunks
    mock_llm.async_invoke.return_value = "Trả lời."

    from app.agents.nodes.rag import rag_fn

    result = await rag_fn(_base_state())

    assert result["response_metadata"]["rag_confidence"] == "medium"


# ---------------------------------------------------------------------------
# Test 10c — threshold-filtered empty → rag_returned_empty=True (not fallback)
# ---------------------------------------------------------------------------

async def test_threshold_filtered_empty_sets_rag_returned_empty(mock_qdrant, mock_llm):
    """When all chunks are above Qdrant's minimum score but below RAG_MIN_SCORE_THRESHOLD,
    the filtered-empty path must set rag_returned_empty=True so the synthesizer uses
    the rag_empty mode instead of fallback (which can hallucinate constraints)."""
    # Qdrant returns chunks but all scores are below RAG_MIN_SCORE_THRESHOLD (0.01)
    chunks = [
        _make_chunk("10", "62/2021/NĐ-CP", rrf_score=0.005),
        _make_chunk("11", "62/2021/NĐ-CP", rrf_score=0.003),
    ]
    mock_qdrant.search.return_value = chunks

    from app.agents.nodes.rag import rag_fn

    result = await rag_fn(_base_state())

    mock_llm.async_invoke.assert_not_called()
    assert result["retrieved_chunks"] == []
    assert result.get("rag_returned_empty") is True, (
        "Threshold-filtered empty must set rag_returned_empty=True to prevent "
        "synthesizer from entering fallback mode and hallucinating constraints"
    )


# ---------------------------------------------------------------------------
# Tests 11–13 — Query rewriting (_build_search_query)
# ---------------------------------------------------------------------------

async def test_short_followup_uses_augmented_query(mock_qdrant, mock_llm):
    """Short follow-up (<10 words) with prior history augments the Qdrant query
    with the last assistant message (first 200 chars)."""
    chunks = [_make_chunk("20", "62/2021/NĐ-CP", rrf_score=0.9)]
    mock_qdrant.search.return_value = chunks
    mock_llm.async_invoke.return_value = "Trả lời về phường khác."

    prior_assistant = (
        "Theo quy định tại Điều 20, Nghị định 62/2021/NĐ-CP, hồ sơ đăng ký thường trú "
        "cần có CCCD và giấy tờ chứng minh chỗ ở hợp pháp."
    )
    state = _base_state(
        user_message="Thế còn phường khác thì sao?",  # 5 words — short follow-up
        conversation_history=[
            {"role": "user", "content": "Hồ sơ đăng ký thường trú gồm những gì?"},
            {"role": "assistant", "content": prior_assistant},
        ],
    )

    from app.agents.nodes.rag import rag_fn

    await rag_fn(state)

    # Qdrant.search must have been called with a query that contains the assistant context
    call_args = mock_qdrant.search.call_args
    actual_query: str = call_args.kwargs.get("query") or call_args.args[0]
    assert "phường khác thì sao" in actual_query, (
        f"User message must be in augmented query, got: {actual_query!r}"
    )
    assert prior_assistant[:50] in actual_query, (
        f"Prior assistant context must be prepended, got: {actual_query!r}"
    )


async def test_long_query_not_augmented(mock_qdrant, mock_llm):
    """Queries with 10+ words are sent to Qdrant as-is, without history context."""
    chunks = [_make_chunk("20", "62/2021/NĐ-CP", rrf_score=0.9)]
    mock_qdrant.search.return_value = chunks
    mock_llm.async_invoke.return_value = "Trả lời."

    long_message = (
        "Tôi muốn biết điều kiện để đăng ký thường trú tại thành phố Hồ Chí Minh là gì?"
    )  # 16 words — long, self-contained
    state = _base_state(
        user_message=long_message,
        conversation_history=[
            {"role": "user", "content": "Câu hỏi trước."},
            {"role": "assistant", "content": "Câu trả lời trước rất dài và chi tiết."},
        ],
    )

    from app.agents.nodes.rag import rag_fn

    await rag_fn(state)

    call_args = mock_qdrant.search.call_args
    actual_query: str = call_args.kwargs.get("query") or call_args.args[0]
    assert actual_query == long_message, (
        f"Long query must not be augmented. Expected:\n{long_message!r}\nGot:\n{actual_query!r}"
    )


async def test_no_history_uses_raw_query(mock_qdrant, mock_llm):
    """Empty conversation_history: search query is user_message without augmentation."""
    chunks = [_make_chunk("20", "62/2021/NĐ-CP", rrf_score=0.9)]
    mock_qdrant.search.return_value = chunks
    mock_llm.async_invoke.return_value = "Trả lời."

    short_message = "Điều kiện là gì?"  # short but no history
    state = _base_state(
        user_message=short_message,
        conversation_history=[],  # no prior turns
    )

    from app.agents.nodes.rag import rag_fn

    await rag_fn(state)

    call_args = mock_qdrant.search.call_args
    actual_query: str = call_args.kwargs.get("query") or call_args.args[0]
    assert actual_query == short_message, (
        f"No history → raw query. Expected {short_message!r}, got {actual_query!r}"
    )


# ---------------------------------------------------------------------------
# Tests 14–17 — _build_search_query proportional augmentation
# ---------------------------------------------------------------------------

def test_augment_short_query_gets_max_context():
    """1-word query receives ~450 chars of prior context (ratio=0.1, result≈450)."""
    from app.agents.nodes.rag import _build_search_query

    prior = "A" * 600  # longer than max to verify truncation
    state = {
        "user_message": "Còn?",  # 1 word
        "conversation_history": [
            {"role": "user", "content": "Câu hỏi."},
            {"role": "assistant", "content": prior},
        ],
    }
    result = _build_search_query(state)

    # ratio = 1/10 = 0.1 → context_chars = int(500*0.9 + 50*0.1) = int(455) = 455
    assert result.endswith("Còn?")
    context_prefix = result[: result.index("Còn?")].rstrip()
    assert len(context_prefix) == 455, f"Expected 455 chars, got {len(context_prefix)}"


def test_augment_medium_query_gets_medium_context():
    """5-word query receives 275 chars of prior context (ratio=0.5, result=275)."""
    from app.agents.nodes.rag import _build_search_query

    prior = "B" * 600
    state = {
        "user_message": "Lệ phí tại Hà Nội?",  # 5 words: Lệ/phí/tại/Hà/Nội?
        "conversation_history": [
            {"role": "assistant", "content": prior},
        ],
    }
    result = _build_search_query(state)

    # ratio = 5/10 = 0.5 → context_chars = int(500*0.5 + 50*0.5) = int(275) = 275
    assert "Lệ phí tại Hà Nội?" in result
    context_prefix = result[: result.index("Lệ phí tại Hà Nội?")].rstrip()
    assert len(context_prefix) == 275, f"Expected 275 chars, got {len(context_prefix)}"


def test_augment_long_query_no_augmentation():
    """10-word query is returned unchanged — no context prepended."""
    from app.agents.nodes.rag import _build_search_query

    ten_word_msg = "Thủ tục đăng ký tạm trú cần những giấy tờ gì?"  # 9 words in Vietnamese but let's count exactly
    # Build a message that is exactly 10 words
    msg = "Một hai ba bốn năm sáu bảy tám chín mười"  # exactly 10 words
    state = {
        "user_message": msg,
        "conversation_history": [
            {"role": "assistant", "content": "Câu trả lời dài trước đó."},
        ],
    }
    result = _build_search_query(state)

    assert result == msg, f"10-word query must not be augmented, got: {result!r}"


def test_augment_no_history_returns_user_msg():
    """Short query with no conversation history returns user_message unchanged."""
    from app.agents.nodes.rag import _build_search_query

    state = {
        "user_message": "Còn?",  # 1 word — would be augmented if history existed
        "conversation_history": [],
    }
    result = _build_search_query(state)

    assert result == "Còn?", f"No history must return raw query, got: {result!r}"


# ---------------------------------------------------------------------------
# Tests 18–20 — _extract_khoan_number() (ingestion chunker helper)
# ---------------------------------------------------------------------------

def test_extract_khoan_number_detects_numeric_khoan():
    """Returns khoản number when the second line is a numeric khoản header."""
    from ingestion.ingest_full_documents import _extract_khoan_number

    content = (
        "Điều 3. Điều khoản thi hành\n"
        "6. Lệ phí hộ tịch\n"
        "a. Đối tượng nộp phí là công dân Việt Nam."
    )
    assert _extract_khoan_number(content) == "6"


def test_extract_khoan_number_returns_none_when_no_khoan():
    """Returns None when the lines after the Điều header are plain prose (no khoản)."""
    from ingestion.ingest_full_documents import _extract_khoan_number

    content = (
        "Điều 15. Trách nhiệm đăng ký khai sinh\n"
        "Trong thời hạn 60 ngày kể từ ngày sinh con, cha hoặc mẹ có trách nhiệm đăng ký."
    )
    assert _extract_khoan_number(content) is None


def test_extract_khoan_number_ignores_letter_subdivision():
    """Returns None when the line after Điều header is a letter subdivision (a., b., c.)."""
    from ingestion.ingest_full_documents import _extract_khoan_number

    content = (
        "Điều 14. Điều kiện đối với người nhận con nuôi\n"
        "a) Có năng lực hành vi dân sự đầy đủ;\n"
        "b) Hơn con nuôi từ 20 tuổi trở lên."
    )
    assert _extract_khoan_number(content) is None
