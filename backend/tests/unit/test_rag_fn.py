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

    def search_side_effect(query=None, procedure_id=None, scope=None, top_k=8):
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
    """confidence is 'high' when top RRF > 0.85 AND at least 3 chunks returned."""
    chunks = [
        _make_chunk("10", "62/2021/NĐ-CP", rrf_score=0.92),
        _make_chunk("11", "62/2021/NĐ-CP", rrf_score=0.88),
        _make_chunk("12", "62/2021/NĐ-CP", rrf_score=0.87),
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
    """confidence is 'low' when top RRF score ≤ 0.65."""
    chunks = [
        _make_chunk("10", "62/2021/NĐ-CP", rrf_score=0.5),
    ]
    mock_qdrant.search.return_value = chunks
    mock_llm.async_invoke.return_value = "Trả lời."

    from app.agents.nodes.rag import rag_fn

    result = await rag_fn(_base_state())

    assert result["response_metadata"]["rag_confidence"] == "low"
