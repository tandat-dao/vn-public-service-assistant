"""Integration tests for the RAG pipeline.

These tests run against a live Qdrant collection (populated by ingest_legal_docs.py).
All LLM calls are mocked — no real API calls are made.

If Qdrant is not reachable, tests are skipped cleanly via the ``require_qdrant``
autouse fixture in conftest.py.

Run only integration tests:
    cd backend && PYTHONPATH=. .venv/Scripts/pytest tests/integration/ -m integration -v

Skip integration tests in CI:
    cd backend && PYTHONPATH=. .venv/Scripts/pytest tests/unit/ -m "not integration" -v
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.citation_formatter import verify_citations
from app.schemas.rag import DocumentChunk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_state(**overrides) -> dict:
    """Build a minimal AgentState dict suitable for rag_fn."""
    state: dict = {
        "user_message": "Điều kiện đăng ký thường trú là gì?",
        "session_id": "integ-rag-test",
        "iteration_count": 0,
        "target_procedure_id": None,
        "filing_jurisdiction": None,
        "entities": {},
        "errors": [],
        "retrieved_chunks": [],
        "citations": [],
        "scope_used": None,
        "conversation_history": [],
        "domain": "housing",
    }
    state.update(overrides)
    return state


def _make_fake_llm_response(chunks: list[DocumentChunk]) -> str:
    """Build a plausible cited response string referencing the first real chunk."""
    if not chunks:
        return "Không tìm thấy thông tin."
    first = chunks[0]
    return (
        f"Theo [{first.article_number}, {first.document_number}], "
        f"điều kiện đăng ký thường trú bao gồm việc có chỗ ở hợp pháp tại nơi đề nghị đăng ký."
    )


# ---------------------------------------------------------------------------
# Test 1: rag_fn returns chunks for a residence query
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.asyncio
async def test_rag_fn_returns_chunks_for_residence_query(require_qdrant):
    """rag_fn retrieves real chunks from Qdrant for a Vietnamese residence query.

    Verifies:
    - returned dict contains "retrieved_chunks" key
    - at least 1 chunk is returned (collection is populated)
    - scope_used == "VN" (no jurisdiction filter → national scope)
    - each chunk has article_number and document_number in its payload
    """
    from app.agents.nodes.rag import rag_fn

    state = _minimal_state(
        user_message="Điều kiện đăng ký thường trú là gì?",
    )

    # Mock only the LLM call — Qdrant is real
    with patch("app.agents.nodes.rag._get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_get_llm.return_value = mock_llm
        # We can't know the real chunks yet, so use a generic cited response
        mock_llm.async_invoke = AsyncMock(
            return_value=(
                "Theo [Điều 20, 62/2021/NĐ-CP], điều kiện đăng ký thường trú "
                "bao gồm có chỗ ở hợp pháp."
            )
        )

        # Reset the lazy singleton so our mock is picked up
        import app.agents.nodes.rag as _rag_module
        original_qdrant = _rag_module._qdrant_svc
        original_llm = _rag_module._llm_svc
        _rag_module._llm_svc = None  # force re-init via _get_llm

        try:
            result = await rag_fn(state)
        finally:
            _rag_module._qdrant_svc = original_qdrant
            _rag_module._llm_svc = original_llm

    # If Qdrant collection is empty, rag_fn returns errors — skip gracefully
    if result.get("errors") and not result.get("retrieved_chunks"):
        first_error = result["errors"][0]
        if "Không tìm thấy" in first_error:
            pytest.skip(
                "Qdrant collection is empty — run ingestion first: "
                "cd backend && PYTHONPATH=. .venv/Scripts/python ingestion/ingest_legal_docs.py"
            )

    chunks: list = result.get("retrieved_chunks", [])
    assert len(chunks) >= 1, (
        f"Expected at least 1 chunk, got {len(chunks)}. "
        f"Errors: {result.get('errors')}"
    )

    scope = result.get("scope_used")
    assert scope == "VN", f"Expected scope_used='VN' but got {scope!r}"

    for chunk in chunks:
        assert chunk.article_number, f"Chunk missing article_number: {chunk}"
        assert chunk.document_number, f"Chunk missing document_number: {chunk}"


# ---------------------------------------------------------------------------
# Test 2: rag_fn with procedure_id filter returns chunks tagged to TTHC-001
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.asyncio
async def test_rag_fn_procedure_filter_returns_relevant_chunks(
    require_qdrant, tthc001_uuid
):
    """rag_fn with target_procedure_id filters chunks to those tagged TTHC-001.

    Verifies:
    - all returned chunks have tthc001_uuid in their procedure_tags
    - no chunks from unrelated procedures sneak through
    """
    from app.agents.nodes.rag import rag_fn

    state = _minimal_state(
        user_message="Hồ sơ đăng ký thường trú cần những giấy tờ gì?",
        target_procedure_id=tthc001_uuid,
    )

    with patch("app.agents.nodes.rag._get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.async_invoke = AsyncMock(
            return_value="Hồ sơ cần có [Điều 22, 62/2021/NĐ-CP] theo quy định."
        )

        import app.agents.nodes.rag as _rag_module
        original_qdrant = _rag_module._qdrant_svc
        original_llm = _rag_module._llm_svc
        _rag_module._llm_svc = None

        try:
            result = await rag_fn(state)
        finally:
            _rag_module._qdrant_svc = original_qdrant
            _rag_module._llm_svc = original_llm

    if result.get("errors") and not result.get("retrieved_chunks"):
        first_error = result["errors"][0]
        if "Không tìm thấy" in first_error:
            pytest.skip(
                "Qdrant collection is empty or TTHC-001 has no tagged chunks — "
                "run ingestion first."
            )

    chunks: list = result.get("retrieved_chunks", [])
    assert len(chunks) >= 1, (
        f"Expected at least 1 chunk for TTHC-001, got {len(chunks)}. "
        f"Errors: {result.get('errors')}"
    )

    for chunk in chunks:
        assert tthc001_uuid in chunk.procedure_tags, (
            f"Chunk {chunk.point_id} procedure_tags {chunk.procedure_tags!r} "
            f"does not include TTHC-001 UUID {tthc001_uuid!r}"
        )


# ---------------------------------------------------------------------------
# Test 3: verify_citations against real chunk payloads
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.asyncio
async def test_verify_citations_against_real_chunk_payloads(
    qdrant_service, require_qdrant
):
    """Retrieve real chunks and verify citation matching logic.

    Uses real Qdrant chunks to validate verify_citations():
    - A citation referencing a real article_number + document_number is kept.
    - A hallucinated citation for "Điều 99" that cannot be matched is flagged
      as [unverified: ...].
    """
    # Retrieve real chunks directly via QdrantService
    chunks: list[DocumentChunk] = await qdrant_service.search(
        query="điều kiện đăng ký thường trú",
        procedure_id=None,
        scope="VN",
        top_k=5,
    )

    if not chunks:
        pytest.skip(
            "Qdrant collection is empty — run ingestion first to populate legal_documents."
        )

    # Pick the first real chunk to build a verified citation
    real_chunk = chunks[0]
    real_article_num = real_chunk.article_number  # e.g. "Điều 20"
    real_doc_num = real_chunk.document_number     # e.g. "62/2021/NĐ-CP"

    # Strip "Điều " prefix for the citation string if present
    article_display = real_article_num  # keep as-is (e.g. "Điều 20")

    # Build a response with one real citation and one hallucinated one
    synthetic_response = (
        f"Theo [{article_display}, {real_doc_num}], "
        f"người đăng ký thường trú cần đáp ứng các điều kiện nhất định. "
        f"Ngoài ra theo [Điều 99, 99/9999/NĐ-CP] có quy định bổ sung."
    )

    verified = verify_citations(synthetic_response, chunks)

    # The real citation must pass through unchanged
    real_citation = f"[{article_display}, {real_doc_num}]"
    assert real_citation in verified, (
        f"Real citation {real_citation!r} was unexpectedly flagged as unverified. "
        f"Verified response: {verified!r}"
    )

    # The hallucinated citation must be flagged
    assert "[unverified:" in verified, (
        f"Hallucinated 'Điều 99' citation was NOT flagged as unverified. "
        f"Verified response: {verified!r}"
    )
    assert "Điều 99" in verified, (
        f"Unverified citation content not preserved in response: {verified!r}"
    )


# ---------------------------------------------------------------------------
# Test 4: Jurisdiction cascade fallback — ward scope falls back to VN
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.asyncio
async def test_rag_fn_jurisdiction_cascade_fallback_to_vn(require_qdrant):
    """rag_fn cascades from ward scope to VN when no ward-specific chunks exist.

    Verifies:
    - With filing_jurisdiction="VN-HCM-26968" (a ward code with no specific chunks),
      rag_fn cascades through VN-HCM and VN until it finds chunks.
    - scope_used == "VN" in the returned dict (cascade reached national scope).
    """
    from app.agents.nodes.rag import rag_fn

    state = _minimal_state(
        user_message="Điều kiện đăng ký thường trú tại phường là gì?",
        filing_jurisdiction="VN-HCM-26968",  # ward scope — no ward-specific chunks ingested
    )

    with patch("app.agents.nodes.rag._get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.async_invoke = AsyncMock(
            return_value=(
                "Theo [Điều 20, 62/2021/NĐ-CP], điều kiện đăng ký thường trú "
                "là phải có chỗ ở hợp pháp."
            )
        )

        import app.agents.nodes.rag as _rag_module
        original_qdrant = _rag_module._qdrant_svc
        original_llm = _rag_module._llm_svc
        _rag_module._llm_svc = None

        try:
            result = await rag_fn(state)
        finally:
            _rag_module._qdrant_svc = original_qdrant
            _rag_module._llm_svc = original_llm

    if result.get("errors") and not result.get("retrieved_chunks"):
        first_error = result.get("errors", [""])[0]
        if "Không tìm thấy" in first_error:
            pytest.skip(
                "Qdrant collection is empty — run ingestion first. "
                "Cannot test jurisdiction cascade against empty collection."
            )

    chunks = result.get("retrieved_chunks", [])
    assert len(chunks) >= 1, (
        f"Expected cascade to find chunks at VN scope but got {len(chunks)} chunks. "
        f"Errors: {result.get('errors')}"
    )

    scope_used = result.get("scope_used")
    assert scope_used == "VN", (
        f"Expected scope_used='VN' after ward-level cascade, got {scope_used!r}"
    )
