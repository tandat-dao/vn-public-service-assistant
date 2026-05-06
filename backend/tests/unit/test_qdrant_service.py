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
        _default_response = MagicMock()
        _default_response.points = []
        client.query_points = AsyncMock(return_value=_default_response)
        client.scroll.return_value = ([], None)
        client.upsert = AsyncMock()
        client.create_collection = AsyncMock()
        client.set_payload = AsyncMock()
        yield client


@pytest.fixture
def mock_embedder():
    # QdrantService now calls _get_embedder() (returns instance directly),
    # not EmbedderService() — patch the factory, not the class.
    with patch("app.services.qdrant_service._get_embedder") as mock_fn:
        embedder = AsyncMock()
        embedder.embed.return_value = [0.1] * 1024
        mock_fn.return_value = embedder
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
    """QdrantService.search() must pass a status=active filter to client.query_points()."""
    await service.search("query")

    call_kwargs = mock_qdrant_client.query_points.call_args.kwargs
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

    call_kwargs = mock_qdrant_client.query_points.call_args.kwargs
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

    call_kwargs = mock_qdrant_client.query_points.call_args.kwargs
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
    _dense_response = MagicMock()
    _dense_response.points = [
        _make_scored_point("1", dense_payload),
        _make_scored_point("2", dense_payload),
        _make_scored_point("3", dense_payload),
    ]
    mock_qdrant_client.query_points.return_value = _dense_response
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
    _empty_response = MagicMock()
    _empty_response.points = []
    mock_qdrant_client.query_points.return_value = _empty_response

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
    _empty_response = MagicMock()
    _empty_response.points = []
    mock_qdrant_client.query_points.return_value = _empty_response

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


# ---------------------------------------------------------------------------
# Helpers shared by deduplication tests
# ---------------------------------------------------------------------------

def _make_doc_chunk(
    article_number: str,
    document_number: str,
    rrf_score: float,
    pid_suffix: str = "",
):
    from app.schemas.rag import DocumentChunk

    return DocumentChunk(
        point_id=f"p-{article_number}-{pid_suffix or rrf_score}",
        legal_document_id="doc-1",
        document_number=document_number,
        article_number=article_number,
        content="test content",
        procedure_tags=[],
        status="active",
        rrf_score=rrf_score,
    )


# ---------------------------------------------------------------------------
# Test 10 — _deduplicate_by_article collapses plain article duplicates
# ---------------------------------------------------------------------------

def test_deduplication_collapses_plain_article_duplicates(service):
    """Two chunks with the same (article_number, document_number) → only highest score kept.

    Chunks are passed in descending rrf_score order (as search() pre-sorts them).
    The first-seen chunk per key is kept — i.e. the highest-scoring one.
    """
    chunks = [
        _make_doc_chunk("13", "123/2015/NĐ-CP", rrf_score=0.030, pid_suffix="high"),
        _make_doc_chunk("14", "123/2015/NĐ-CP", rrf_score=0.028),
        _make_doc_chunk("13", "123/2015/NĐ-CP", rrf_score=0.025, pid_suffix="low"),
        _make_doc_chunk("13", "123/2015/NĐ-CP", rrf_score=0.020, pid_suffix="lowest"),
    ]

    result = service._deduplicate_by_article(chunks)

    article_numbers = [c.article_number for c in result]
    assert article_numbers.count("13") == 1, "Article 13 must appear exactly once after dedup"
    assert len(result) == 2, f"Expected 2 unique articles, got {len(result)}: {article_numbers}"

    kept_13 = next(c for c in result if c.article_number == "13")
    assert kept_13.rrf_score == 0.030, "The highest-scoring chunk for article 13 must be kept"


# ---------------------------------------------------------------------------
# Test 11 — _deduplicate_by_article preserves khoản-split articles
# ---------------------------------------------------------------------------

def test_deduplication_preserves_khoan_split_articles(service):
    """'Điều 20 Khoản 1' and 'Điều 20 Khoản 2' are distinct keys — both survive dedup."""
    chunks = [
        _make_doc_chunk("Điều 20 Khoản 1", "123/2015/NĐ-CP", rrf_score=0.030),
        _make_doc_chunk("Điều 20 Khoản 2", "123/2015/NĐ-CP", rrf_score=0.028),
        _make_doc_chunk("Điều 21", "123/2015/NĐ-CP", rrf_score=0.025),
    ]

    result = service._deduplicate_by_article(chunks)

    assert len(result) == 3, (
        f"Khoản-split articles must NOT be collapsed. Got {len(result)}: "
        f"{[c.article_number for c in result]}"
    )
    article_numbers = [c.article_number for c in result]
    assert "Điều 20 Khoản 1" in article_numbers
    assert "Điều 20 Khoản 2" in article_numbers


# ---------------------------------------------------------------------------
# Test 12 — top_k slice applied AFTER deduplication
# ---------------------------------------------------------------------------

def test_top_k_applied_after_deduplication(service):
    """The [:top_k] slice is applied to the deduplicated list, not the raw list.

    If slice happens BEFORE dedup: raw[:2] → [A(0.9), A_dup(0.8)] → dedup → [A] (1 item, wrong).
    If dedup happens BEFORE slice: dedup([A, A_dup, B, C]) → [A, B, C] → [:2] → [A, B] (correct).

    This test calls _deduplicate_by_article() directly and then applies [:2] to verify
    the dedup method does NOT itself apply any top_k capping — the caller (search) does.
    """
    raw_sorted = [
        _make_doc_chunk("13", "X", rrf_score=0.030, pid_suffix="high"),   # rank 1
        _make_doc_chunk("13", "X", rrf_score=0.028, pid_suffix="low"),    # rank 2 — duplicate
        _make_doc_chunk("14", "X", rrf_score=0.026),                      # rank 3 — missed if sliced[:2] first
        _make_doc_chunk("15", "X", rrf_score=0.020),                      # rank 4
    ]

    deduplicated = service._deduplicate_by_article(raw_sorted)

    assert len(deduplicated) == 3, (
        f"Dedup should yield 3 unique articles (13, 14, 15), got {len(deduplicated)}: "
        f"{[c.article_number for c in deduplicated]}"
    )

    final = deduplicated[:2]
    article_numbers = [c.article_number for c in final]
    assert "13" in article_numbers, "Article 13 (highest score) must be in top-2"
    assert "14" in article_numbers, "Article 14 must be in top-2 (not displaced by duplicate 13)"
    assert article_numbers.count("13") == 1, "Article 13 must not appear twice in final result"
