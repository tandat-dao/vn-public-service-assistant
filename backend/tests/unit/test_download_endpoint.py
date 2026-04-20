"""Unit tests for GET /api/v1/documents/download.

Tests:
  1. Valid path + matching session_id → 200 + application/pdf
  2. Path session_id ≠ query session_id → 403
  3. StorageService.download() raises → 404
  4. synthesizer_node includes filled_form_path in metadata for
     form_fill_complete mode only

All external I/O (MinIO, LLM) is mocked.
asyncio_mode=auto is set in pyproject.toml so async test functions run directly.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.storage_service import StorageError


# ---------------------------------------------------------------------------
# Test 1 — valid path returns 200 application/pdf
# ---------------------------------------------------------------------------

async def test_download_valid_path_returns_pdf():
    """GET /download with session_id matching the path returns PDF bytes."""
    session_id = "abc-123"
    object_path = f"forms/{session_id}/TTHC-001.pdf"
    fake_pdf_bytes = b"%PDF-1.4 fake content"

    mock_storage = AsyncMock()
    mock_storage.download = AsyncMock(return_value=fake_pdf_bytes)

    with patch("app.api.v1.documents._get_storage", return_value=mock_storage):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/documents/download",
                params={"path": object_path, "session_id": session_id},
            )

    assert resp.status_code == 200, (
        f"Expected 200 for valid path, got {resp.status_code}: {resp.text}"
    )
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content == fake_pdf_bytes
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert "TTHC-001" in resp.headers.get("content-disposition", "")
    mock_storage.download.assert_awaited_once_with(object_path)


# ---------------------------------------------------------------------------
# Test 2 — session_id in path ≠ query param → 403
# ---------------------------------------------------------------------------

async def test_download_wrong_session_returns_403():
    """GET /download where path session_id != query session_id returns 403."""
    owner_session = "real-owner-session"
    attacker_session = "attacker-session"
    object_path = f"forms/{owner_session}/TTHC-001.pdf"

    mock_storage = AsyncMock()
    mock_storage.download = AsyncMock(return_value=b"should not be reached")

    with patch("app.api.v1.documents._get_storage", return_value=mock_storage):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/documents/download",
                params={"path": object_path, "session_id": attacker_session},
            )

    assert resp.status_code == 403, (
        f"Expected 403 for session mismatch, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert "quyền" in data.get("detail", ""), (
        "Expected Vietnamese 403 message mentioning 'quyền'"
    )
    # StorageService.download must never be called on a forbidden request
    mock_storage.download.assert_not_awaited()


# ---------------------------------------------------------------------------
# Test 3 — StorageService.download raises → 404
# ---------------------------------------------------------------------------

async def test_download_file_not_found_returns_404():
    """GET /download returns 404 when StorageService.download raises StorageError."""
    session_id = "session-xyz"
    object_path = f"tmp/{session_id}/TTHC-002.pdf"

    mock_storage = AsyncMock()
    mock_storage.download = AsyncMock(
        side_effect=StorageError("NoSuchKey: The specified key does not exist.")
    )

    with patch("app.api.v1.documents._get_storage", return_value=mock_storage):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/documents/download",
                params={"path": object_path, "session_id": session_id},
            )

    assert resp.status_code == 404, (
        f"Expected 404 for missing file, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert "Không tìm thấy tệp" in data.get("detail", ""), (
        f"Expected Vietnamese 404 message, got: {data.get('detail')}"
    )


# ---------------------------------------------------------------------------
# Test 4 — synthesizer_node includes filled_form_path only in form_fill_complete
# ---------------------------------------------------------------------------

async def test_synthesizer_includes_filled_form_path_in_metadata():
    """synthesizer_node returns filled_form_path in metadata for form_fill_complete."""
    from app.agents.nodes.synthesizer import synthesizer_node

    filled_path = "forms/session-abc/TTHC-001.pdf"
    state = {
        "errors": [],
        "plan_cursor": 1,
        "form_fill_complete": True,
        "unfilled_required_fields": [],
        "retrieved_chunks": [],
        "filled_form_path": filled_path,
        "user_message": "Điền tờ khai thường trú cho tôi",
        "conversation_history": [],
        "procedure_execution_plan": [],
        "scope_used": None,
        "filing_jurisdiction": None,
        "response_metadata": {},
    }

    mock_llm = AsyncMock()
    mock_llm.async_invoke = AsyncMock(
        return_value="Tờ khai đã được điền. Bấm nút tải xuống bên dưới."
    )

    with patch("app.agents.nodes.synthesizer._get_llm", return_value=mock_llm):
        result = await synthesizer_node(state)

    assert result["response_metadata"]["mode"] == "form_fill_complete"
    assert result["response_metadata"].get("filled_form_path") == filled_path, (
        f"Expected filled_form_path={filled_path!r}, "
        f"got: {result['response_metadata'].get('filled_form_path')!r}"
    )


async def test_synthesizer_no_filled_form_path_for_other_modes():
    """synthesizer_node does NOT include filled_form_path for rag_only mode."""
    from app.agents.nodes.synthesizer import synthesizer_node
    from app.schemas.rag import DocumentChunk

    chunk = MagicMock(spec=DocumentChunk)
    chunk.text = "Điều 1. Phạm vi điều chỉnh..."
    chunk.document_number = "62/2021/NĐ-CP"
    chunk.article = "Điều 1"
    chunk.score = 0.9

    state = {
        "errors": [],
        "plan_cursor": 1,
        "form_fill_complete": False,
        "unfilled_required_fields": [],
        "retrieved_chunks": [chunk],
        "filled_form_path": None,
        "user_message": "Nghị định 62 quy định gì?",
        "conversation_history": [],
        "procedure_execution_plan": [],
        "scope_used": None,
        "filing_jurisdiction": None,
        "response_metadata": {"rag_confidence": 0.9},
        "final_response": "Nghị định 62/2021/NĐ-CP quy định...",
    }

    # rag_only fast-path skips LLM when no scope notice needed, so no mock needed
    result = await synthesizer_node(state)

    assert result["response_metadata"]["mode"] == "rag_only"
    assert "filled_form_path" not in result["response_metadata"], (
        "filled_form_path must not appear in non-form_fill_complete metadata"
    )
