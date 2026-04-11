"""Unit tests for QdrantService (app.services.qdrant_service).

All Qdrant client calls and EmbedderService calls are mocked.
asyncio_mode=auto is set in pyproject.toml — no @pytest.mark.asyncio needed.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers: build mock ScoredPoint / Record-like objects
# ---------------------------------------------------------------------------

def _make_scored_point(point_id: str, payload: dict) -> MagicMock:
    p = MagicMock()
    p.id = point_id
    p.payload = payload
    return p


def _make_scroll_point(point_id: str, payload: dict) -> MagicMock:
    p = MagicMock()
    p.id = point_id
    p.payload = payload
    return p


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_qdrant_client():
    with patch("app.services.qdrant_service.AsyncQdrantClient") as mock_cls:
        client = AsyncMock()
        mock_cls.return_value = client
        # Safe defaults
        client.search.return_value = []
        client.scroll.return_value = ([], None)
        client.upsert = AsyncMock()
        client.create_collection = AsyncMock()
        client.set_payload = AsyncMock()
        yield client


@pytest.fixture
def mock_embedder():
    with patch("app.services.qdrant_service.EmbedderService") as mock_cls:
        embedder = AsyncMock()
        embedder.embed.return_value = [0.1] * 1024
        mock_cls.return_value = embedder
        yield embedder


@pytest.fixture
def service(mock_qdrant_client, mock_embedder):
    """Instantiate QdrantService with all infrastructure mocked."""
    from app.services.qdrant_service import QdrantService

    return QdrantService()


# ---------------------------------------------------------------------------
# Test 1 — search always applies status="active" filter
# ---------------------------------------------------------------------------

async def test_search_always_applies_status_active_filter(service, mock_qdrant_client):
    """QdrantService.search() must pass a status=active filter to client.search()."""
    await service.search("query")

    call_kwargs = mock_qdrant_client.search.call_args.kwargs
    f = call_kwargs["query_filter"]

    # Inspect must conditions
    must_conditions = f.must
    status_conditions = [
        c for c in must_conditions
        if getattr(c, "key", None) == "status"
    ]
    assert len(status_conditions) == 1
    assert status_conditions[0].match.value == "active"


# ---------------------------------------------------------------------------
# Test 2 — procedure_id filter is included when provided
# ---------------------------------------------------------------------------

async def test_search_applies_procedure_id_filter_when_provided(service, mock_qdrant_client):
    """When procedure_id is given, filter must include a procedure_tags condition."""
    await service.search("query", procedure_id="TTHC-001")

    call_kwargs = mock_qdrant_client.search.call_args.kwargs
    f = call_kwargs["query_filter"]
    must_conditions = f.must

    tag_conditions = [
        c for c in must_conditions
        if getattr(c, "key", None) == "procedure_tags"
    ]
    assert len(tag_conditions) == 1
    assert "TTHC-001" in tag_conditions[0].match.any


# ---------------------------------------------------------------------------
# Test 3 — no procedure_tags filter when procedure_id is None
# ---------------------------------------------------------------------------

async def test_search_no_procedure_filter_when_none(service, mock_qdrant_client):
    """When procedure_id is None, only the status filter should be present."""
    await service.search("query", procedure_id=None)

    call_kwargs = mock_qdrant_client.search.call_args.kwargs
    f = call_kwargs["query_filter"]
    must_conditions = f.must

    tag_conditions = [
        c for c in must_conditions
        if getattr(c, "key", None) == "procedure_tags"
    ]
    assert len(tag_conditions) == 0
    assert len(must_conditions) == 1  # only status condition


# ---------------------------------------------------------------------------
# Test 4 — RRF merge assigns higher score to ID appearing in both result lists
# ---------------------------------------------------------------------------

async def test_rrf_merge_combines_both_result_lists(service, mock_qdrant_client):
    """ID appearing in both dense and BM25 results should have the highest RRF score."""
    # Dense results: IDs 1, 2, 3
    dense_payload = {"content": "hello world", "document_number": "A", "article_number": "Điều 1",
                     "legal_document_id": "x", "procedure_tags": [], "status": "active"}
    mock_qdrant_client.search.return_value = [
        _make_scored_point("1", dense_payload),
        _make_scored_point("2", dense_payload),
        _make_scored_point("3", dense_payload),
    ]
    # Scroll results: IDs 3, 4, 5 (ID 3 overlaps with dense)
    scroll_payload = {"content": "hello world", "document_number": "A", "article_number": "Điều 1",
                      "legal_document_id": "x", "procedure_tags": [], "status": "active"}
    mock_qdrant_client.scroll.return_value = (
        [
            _make_scroll_point("3", scroll_payload),
            _make_scroll_point("4", scroll_payload),
            _make_scroll_point("5", scroll_payload),
        ],
        None,
    )

    results = await service.search("hello world", top_k=5)

    # ID "3" appears in both dense and BM25 — must have the highest RRF score
    assert len(results) > 0
    result_ids = [r.point_id for r in results]
    assert "3" in result_ids
    # "3" should be ranked first
    assert result_ids[0] == "3"


# ---------------------------------------------------------------------------
# Test 5 — token budget truncates results
# ---------------------------------------------------------------------------

async def test_token_budget_truncates_results(service, mock_qdrant_client):
    """Results exceeding the 6000-token budget should be truncated."""
    # Each chunk has content of ~1600 chars ≈ 400 tokens. Budget is 6000 tokens.
    # After 15 chunks we'd have 6000 tokens — 16th should be cut.
    long_content = "x " * 800  # 1600 chars / 4 = 400 tokens per chunk
    payload = {"content": long_content, "document_number": "A", "article_number": "Điều 1",
               "legal_document_id": "x", "procedure_tags": [], "status": "active"}

    scroll_points = [_make_scroll_point(str(i), payload) for i in range(20)]
    mock_qdrant_client.scroll.return_value = (scroll_points, None)
    mock_qdrant_client.search.return_value = []

    results = await service.search("query", top_k=20)
    assert len(results) < 20


# ---------------------------------------------------------------------------
# Test 6 — token budget log message is emitted
# ---------------------------------------------------------------------------

async def test_token_budget_log_is_emitted(service, mock_qdrant_client, caplog):
    """A debug log containing 'RAG token budget' must be emitted after search."""
    payload = {"content": "hello", "document_number": "A", "article_number": "Điều 1",
               "legal_document_id": "x", "procedure_tags": [], "status": "active"}
    mock_qdrant_client.scroll.return_value = ([_make_scroll_point("1", payload)], None)
    mock_qdrant_client.search.return_value = []

    with caplog.at_level(logging.DEBUG, logger="app.services.qdrant_service"):
        await service.search("test")

    assert "RAG token budget" in caplog.text


# ---------------------------------------------------------------------------
# Test 7 — upsert always sets status="active" in payload
# ---------------------------------------------------------------------------

async def test_upsert_always_sets_status_active(service, mock_qdrant_client, mock_embedder):
    """upsert() must force status="active" in every PointStruct payload."""
    chunk = {
        "point_id": "abc-123",
        "legal_document_id": "doc-1",
        "document_number": "62/2021/NĐ-CP",
        "article_number": "Điều 5",
        "content": "Some legal text",
        "procedure_tags": ["TTHC-001"],
        "status": "superseded",  # should be overridden to "active"
    }
    mock_embedder.embed.return_value = [0.1] * 1024

    await service.upsert([chunk])

    assert mock_qdrant_client.upsert.called
    call_kwargs = mock_qdrant_client.upsert.call_args.kwargs
    points = call_kwargs["points"]
    assert len(points) == 1
    assert points[0].payload["status"] == "active"


# ---------------------------------------------------------------------------
# Test 8 — update_status returns count of updated points
# ---------------------------------------------------------------------------

async def test_update_status_returns_count(service, mock_qdrant_client):
    """update_status() should return the number of points updated."""
    scroll_points = [
        _make_scroll_point("p1", {}),
        _make_scroll_point("p2", {}),
        _make_scroll_point("p3", {}),
    ]
    mock_qdrant_client.scroll.return_value = (scroll_points, None)

    count = await service.update_status("123/2021/NĐ-CP", "superseded")
    assert count == 3


# ---------------------------------------------------------------------------
# Test 9 — create_collection is idempotent (UnexpectedResponse on 2nd call)
# ---------------------------------------------------------------------------

async def test_create_collection_is_idempotent(service, mock_qdrant_client):
    """create_collection() must not raise when collection already exists."""
    from qdrant_client.http.exceptions import UnexpectedResponse

    mock_qdrant_client.create_collection.side_effect = [
        None,  # first call succeeds
        UnexpectedResponse(
            status_code=400,
            reason_phrase="Bad Request",
            content=b"already exists",
            headers={},
        ),
    ]

    # First call — should succeed
    await service.create_collection()

    # Second call — should NOT raise
    await service.create_collection()
