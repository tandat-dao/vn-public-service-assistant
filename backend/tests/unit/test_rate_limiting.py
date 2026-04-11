"""Unit tests for rate-limiting middleware on POST /api/v1/chat.

Strategy:
- Use in-memory slowapi storage (no Redis needed).
- Patch MinIO lifespan so TestClient startup doesn't require a running MinIO.
- Patch the chat handler to return 200 (stub raises NotImplementedError → 500,
  which would mask the 429 we're testing).
- Use sync TestClient (simpler, no async event-loop issues with slowapi).
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.rate_limit import _get_session_id_key, limiter as prod_limiter


def _make_test_app() -> tuple[FastAPI, Limiter]:
    """Build a minimal FastAPI app that mirrors the real app's rate-limit setup."""
    test_limiter = Limiter(key_func=_get_session_id_key, storage_uri="memory://")

    @asynccontextmanager
    async def _noop_lifespan(app):
        yield  # skip MinIO / external service init

    from app.api.v1.router import router as v1_router
    from app.config import settings

    app = FastAPI(lifespan=_noop_lifespan)
    app.state.limiter = test_limiter

    async def _rate_limit_handler(request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"error": "rate_limit_exceeded", "detail": "Too many requests"},
        )

    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.include_router(v1_router, prefix="/api/v1")
    return app, test_limiter


@pytest.fixture()
def rate_limited_client():
    """TestClient with in-memory rate limiter and mocked infrastructure."""
    app, test_limiter = _make_test_app()

    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(
        return_value={"final_response": "ok", "response_metadata": {}}
    )
    mock_redis = MagicMock()
    mock_redis.get_session = AsyncMock(return_value=None)
    mock_redis.save_session = AsyncMock(return_value=None)

    # Patch the limiter used by the @limiter.limit() decorator on the chat route
    # so it shares the same in-memory storage as app.state.limiter.
    # Also mock agent_graph and _get_redis so the real endpoint doesn't hit
    # real infrastructure (patching `chat` itself doesn't work for already-
    # registered FastAPI route handlers).
    with patch("app.rate_limit.limiter", test_limiter), \
         patch("app.api.v1.chat.limiter", test_limiter), \
         patch("app.api.v1.chat.agent_graph", mock_graph), \
         patch("app.api.v1.chat._get_redis", return_value=mock_redis):
        yield TestClient(app, raise_server_exceptions=False)


class TestChatRateLimit:
    def test_eleventh_request_returns_429(self, rate_limited_client):
        client = rate_limited_client
        payload = {"message": "test", "session_id": "sess-429-test"}

        for i in range(10):
            resp = client.post("/api/v1/chat", json=payload)
            assert resp.status_code != 429, f"Unexpected 429 on request #{i + 1}"

        resp = client.post("/api/v1/chat", json=payload)
        assert resp.status_code == 429
        body = resp.json()
        assert body["error"] == "rate_limit_exceeded"
        assert body["detail"] == "Too many requests"

    def test_different_sessions_have_separate_limits(self, rate_limited_client):
        client = rate_limited_client

        for _ in range(10):
            client.post("/api/v1/chat", json={"message": "x", "session_id": "sess-A"})

        resp_a = client.post("/api/v1/chat", json={"message": "x", "session_id": "sess-A"})
        assert resp_a.status_code == 429

        # Different session_id → fresh counter, not blocked yet
        resp_b = client.post("/api/v1/chat", json={"message": "x", "session_id": "sess-B"})
        assert resp_b.status_code != 429


class TestSessionIdKeyFunction:
    def test_returns_session_id_when_body_cached(self):
        """_get_session_id_key reads session_id from cached _body attribute."""

        class FakeRequest:
            _body = b'{"session_id": "my-session", "message": "hi"}'

            class client:
                host = "127.0.0.1"

        result = _get_session_id_key(FakeRequest())
        assert result == "my-session"

    def test_falls_back_to_ip_when_no_body(self):
        class FakeRequest:
            _body = None

            class client:
                host = "10.0.0.1"

        result = _get_session_id_key(FakeRequest())
        assert result == "10.0.0.1"

    def test_falls_back_to_ip_when_no_session_id_in_body(self):
        class FakeRequest:
            _body = b'{"message": "hi"}'

            class client:
                host = "192.168.1.1"

        result = _get_session_id_key(FakeRequest())
        assert result == "192.168.1.1"
