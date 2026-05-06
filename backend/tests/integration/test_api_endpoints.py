"""Integration tests for FastAPI endpoints.

Uses in-process ASGI transport — no external port needed. All heavy
dependencies (agent graph, Redis, DB) are mocked so the tests exercise
the HTTP/SSE contract and serialisation layer only.

If Qdrant is not reachable, the ``require_qdrant`` autouse fixture in
conftest.py skips the entire integration session cleanly.

Run:
    cd backend && PYTHONPATH=. .venv/Scripts/pytest tests/integration/test_api_endpoints.py -v
"""

from __future__ import annotations

import json

import pytest
from unittest.mock import AsyncMock, patch


# ---------------------------------------------------------------------------
# Test 12: POST /api/v1/chat — SSE stream with metadata event
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_endpoint_returns_sse_stream(http_client, session_id):
    """POST /api/v1/chat streams SSE with a final metadata event.

    Verifies:
    - HTTP 200 with content-type text/event-stream
    - At least one data: {"content": ...} chunk
    - A data: {"metadata": {...}} event with a recognised "mode" value
    - data: [DONE] termination signal

    No real LLM, Qdrant, or Redis calls are made — all are mocked.
    """
    fake_result = {
        "final_response": "Điều kiện đăng ký thường trú bao gồm có chỗ ở hợp pháp.",
        "response_metadata": {
            "mode": "rag_only",
            "scope_used": "VN",
            "scope_notice_included": False,
            "rag_confidence": "high",
            "retrieved_sources": [],
        },
        "guided_procedure_id": None,
        "guided_step": None,
    }

    mock_redis = AsyncMock()
    mock_redis.get_session = AsyncMock(return_value=None)
    mock_redis.get_citizen_personal_data = AsyncMock(return_value=None)
    mock_redis.save_session = AsyncMock(return_value=None)

    with patch("app.api.v1.chat.agent_graph") as mock_graph, \
         patch("app.api.v1.chat._get_redis", return_value=mock_redis):
        mock_graph.ainvoke = AsyncMock(return_value=fake_result)

        response = await http_client.post(
            "/api/v1/chat",
            json={
                "message": "Điều kiện đăng ký thường trú là gì?",
                "session_id": session_id,
            },
        )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:300]}"
    )
    assert "text/event-stream" in response.headers.get("content-type", ""), (
        f"Expected text/event-stream content-type, got: {response.headers.get('content-type')}"
    )

    # Parse SSE events
    lines = response.text.split("\n")
    content_chunks: list[str] = []
    metadata: dict | None = None
    done_seen = False

    for line in lines:
        if not line.startswith("data: "):
            continue
        payload = line[6:]
        if payload == "[DONE]":
            done_seen = True
            continue
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if "content" in data:
            content_chunks.append(data["content"])
        if "metadata" in data:
            metadata = data["metadata"]

    assert content_chunks, "Expected at least one content chunk in SSE stream"
    assert done_seen, "Expected [DONE] termination signal in SSE stream"
    assert metadata is not None, "Expected metadata event in SSE stream"
    assert metadata.get("mode") in (
        "rag_only", "fallback", "rag_empty", "out_of_scope",
        "error", "guided_step", "circuit_breaker",
        "form_fill_complete", "form_fill_partial",
    ), f"Unexpected mode in metadata: {metadata.get('mode')}"

    # Reassemble and verify full text matches
    full_text = "".join(content_chunks)
    assert "thường trú" in full_text or "hợp pháp" in full_text, (
        f"Expected response content in stream, got: {full_text[:200]}"
    )


# ---------------------------------------------------------------------------
# Test 13: POST /api/v1/forms/fill — PDF bytes response
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.asyncio
async def test_form_fill_endpoint_returns_pdf_bytes(http_client):
    """POST /api/v1/forms/fill returns PDF bytes for TTHC-002 + valid form_file.

    fill_doc is mocked to return synthetic PDF header bytes so the test
    does not require LibreOffice to be installed.

    Verifies:
    - HTTP 200
    - content-type == application/pdf
    - Response body starts with PDF magic bytes (%PDF)
    """
    fake_pdf_bytes = b"%PDF-1.4 1 0 obj << /Type /Catalog >> endobj"

    with patch("app.services.doc_filler.fill_doc", new_callable=AsyncMock) as mock_fill:
        mock_fill.return_value = fake_pdf_bytes

        response = await http_client.post(
            "/api/v1/forms/fill",
            json={
                "procedure_id": "TTHC-002",
                "form_file": "1.MuCT01banhnhkmtheoThngts53.doc",
                "field_values": {
                    "ho_chu_dem_va_ten": "Nguyễn Văn A",
                    "ngay_thang_nam_sinh": "01/01/1990",
                    "gioi_tinh": "Nam",
                    "so_dinh_danh_ca_nhan": "001234567890",
                },
            },
        )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:300]}"
    )
    assert response.headers.get("content-type") == "application/pdf", (
        f"Expected application/pdf, got: {response.headers.get('content-type')}"
    )
    assert response.content[:4] == b"%PDF", (
        f"Expected PDF magic bytes at start of response, got: {response.content[:8]!r}"
    )
