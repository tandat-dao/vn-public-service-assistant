"""Unit tests for POST /api/v1/chat endpoint.

All agent graph calls and Redis calls are mocked — no real infrastructure.

Covers TASK-11 DoD items 9–11:
  9.  test_chat_endpoint_returns_sse_stream
  10. test_chat_endpoint_handles_graph_recursion_error
  11. test_chat_endpoint_redis_save_failure_does_not_fail_request

Updated for TASK-SHOWCASE: agent_graph.astream_events() replaces ainvoke().
GraphRecursionError is now emitted as an SSE error chunk (HTTP 200), not HTTP 500.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.schemas.session import SessionData


# ---------------------------------------------------------------------------
# App fixture — creates TestClient with mocked infrastructure
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """TestClient with agent_graph and Redis mocked out."""
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def _default_events(final_response: str = "Xin chào bạn"):
    """Minimal valid event sequence for a successful pipeline run."""
    return [
        {"event": "on_chain_start", "name": "router_node", "data": {"input": {}}},
        {
            "event": "on_chain_end",
            "name": "router_node",
            "data": {"output": {"execution_plan": [], "plan_cursor": 0}},
        },
        {"event": "on_chain_end", "name": "enrichment_node", "data": {"output": {}}},
        {
            "event": "on_chain_end",
            "name": "synthesizer_node",
            "data": {
                "output": {
                    "final_response": final_response,
                    "response_metadata": {"mode": "fallback"},
                }
            },
        },
    ]


def _mock_graph(final_response: str = "Xin chào", raise_exc: Exception | None = None):
    """Build a mock agent_graph with astream_events() as an async generator.

    If raise_exc is given, the generator raises it on first iteration —
    simulating a mid-pipeline exception (e.g. GraphRecursionError).
    """
    mock = MagicMock()

    if raise_exc is not None:
        async def _stream(*args, **kwargs):
            raise raise_exc
            yield  # unreachable — presence of yield makes this an async generator

        mock.astream_events = _stream
    else:
        _events = _default_events(final_response)

        async def _stream(*args, **kwargs):
            for ev in _events:
                yield ev

        mock.astream_events = _stream

    return mock


def _mock_redis(session: SessionData | None = None, save_raises: Exception | None = None):
    """Build a mock RedisService."""
    svc = MagicMock()
    svc.get_session = AsyncMock(return_value=session)
    if save_raises is not None:
        svc.save_session = AsyncMock(side_effect=save_raises)
    else:
        svc.save_session = AsyncMock(return_value=None)
    svc.get_citizen_personal_data = AsyncMock(return_value=None)
    return svc


# ---------------------------------------------------------------------------
# Test 9 — SSE stream response
# ---------------------------------------------------------------------------

def test_chat_endpoint_returns_sse_stream(client):
    """POST /chat returns 200 text/event-stream with data chunks and [DONE]."""
    mock_graph = _mock_graph(final_response="Xin chào bạn")
    mock_redis = _mock_redis()

    with patch("app.api.v1.chat.agent_graph", mock_graph), \
         patch("app.api.v1.chat._get_redis", return_value=mock_redis):

        response = client.post(
            "/api/v1/chat",
            json={"message": "Xin chào", "session_id": "sess-test-001"},
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    body = response.text
    # At least one data: chunk must be present
    assert "data:" in body
    # Termination signal must be present
    assert "[DONE]" in body


# ---------------------------------------------------------------------------
# Test 10 — GraphRecursionError is handled in the SSE stream (HTTP 200)
#
# With astream_events(), GraphRecursionError is caught inside the SSE generator
# and emitted as a data chunk. The response is always HTTP 200 for streaming.
# (Previously HTTP 500 was returned by ainvoke() before the stream started.)
# ---------------------------------------------------------------------------

def test_chat_endpoint_handles_graph_recursion_error(client):
    """GraphRecursionError → HTTP 200 SSE stream with error content + [DONE].

    With astream_events() the HTTP headers (200) are sent before the graph
    executes. The error is surfaced as a data chunk inside the SSE stream.
    """
    try:
        from langgraph.errors import GraphRecursionError
    except ImportError:
        GraphRecursionError = RecursionError  # type: ignore[misc,assignment]

    mock_graph = _mock_graph(raise_exc=GraphRecursionError("recursion limit"))
    mock_redis = _mock_redis()

    with patch("app.api.v1.chat.agent_graph", mock_graph), \
         patch("app.api.v1.chat._get_redis", return_value=mock_redis):

        response = client.post(
            "/api/v1/chat",
            json={"message": "phức tạp", "session_id": "sess-test-002"},
        )

    # SSE streams always return 200 — the error appears in the stream body
    assert response.status_code == 200
    body = response.text
    # Must still terminate properly
    assert "[DONE]" in body
    # Error message must appear in the streamed content
    assert "phức tạp" in body or "lỗi" in body or "Vui lòng thử lại" in body


# ---------------------------------------------------------------------------
# Test 11 — Redis save failure does not fail the request
# ---------------------------------------------------------------------------

def test_chat_endpoint_redis_save_failure_does_not_fail_request(client):
    """Redis save_session raising must not result in a non-200 response."""
    mock_graph = _mock_graph(final_response="Câu trả lời")
    mock_redis = _mock_redis(save_raises=ConnectionError("Redis down"))

    with patch("app.api.v1.chat.agent_graph", mock_graph), \
         patch("app.api.v1.chat._get_redis", return_value=mock_redis):

        response = client.post(
            "/api/v1/chat",
            json={"message": "Xin hỏi", "session_id": "sess-test-003"},
        )

    # Must still return 200 — Redis save failure is non-fatal
    assert response.status_code == 200
    assert "[DONE]" in response.text


# ---------------------------------------------------------------------------
# Input validation — Fix A
# ---------------------------------------------------------------------------

def test_chat_message_too_long_returns_422(client):
    """Message longer than 2000 chars → HTTP 422."""
    response = client.post(
        "/api/v1/chat",
        json={"message": "X" * 2001, "session_id": "sess-valid-001"},
    )
    assert response.status_code == 422


def test_chat_message_blank_returns_422(client):
    """Whitespace-only message → HTTP 422."""
    response = client.post(
        "/api/v1/chat",
        json={"message": "   ", "session_id": "sess-valid-002"},
    )
    assert response.status_code == 422


def test_generate_streams_char_groups(client):
    """generate() emits content in chunks of ≤3 chars; concatenation is lossless."""
    final_response = "Xin chào bạn!"
    mock_graph = _mock_graph(final_response=final_response)
    mock_redis = _mock_redis()

    with patch("app.api.v1.chat.agent_graph", mock_graph), \
         patch("app.api.v1.chat._get_redis", return_value=mock_redis):

        response = client.post(
            "/api/v1/chat",
            json={"message": "Xin chào", "session_id": "sess-chargroup-001"},
        )

    assert response.status_code == 200

    content_chunks: list[str] = []
    for line in response.text.splitlines():
        if not line.startswith("data:"):
            continue
        raw = line[len("data:"):].strip()
        if raw == "[DONE]":
            break
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if "content" in parsed:
            chunk = parsed["content"]
            assert len(chunk) <= 3, (
                f"Chunk '{chunk}' has {len(chunk)} chars — expected ≤ 3"
            )
            content_chunks.append(chunk)

    # All content chunks concatenated must exactly equal final_response
    assert "".join(content_chunks) == final_response
