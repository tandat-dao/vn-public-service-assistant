"""Unit tests for POST /api/v1/forms/submit.

All DB calls are mocked — no real PostgreSQL connection required.
asyncio_mode=auto is set in pyproject.toml so async test functions run directly.
"""

from __future__ import annotations

import re
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_db
from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_BODY = {
    "form_type": "thuong-tru",
    "session_id": "test-session-id",
    "submission_mode": "manual",
    "form_data": {
        "ho_ten": "Nguyễn Văn A",
        "ngay_sinh": "01/01/1990",
        "gioi_tinh": "Nam",
        "so_cccd": "123456789012",
    },
}

TRACKING_CODE_PATTERN = re.compile(r"^DVC-\d{8}-[A-Z0-9]{6}$")


def _make_mock_db():
    """Return an AsyncMock AsyncSession where execute and commit succeed."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=None)
    mock_db.commit = AsyncMock(return_value=None)
    return mock_db


# ---------------------------------------------------------------------------
# Test 1 — happy path: returns tracking code in correct format
# ---------------------------------------------------------------------------

async def test_submit_returns_tracking_code():
    """POST /submit returns ma_ho_so matching DVC-YYYYMMDD-XXXXXX."""
    mock_db = _make_mock_db()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/v1/forms/submit", json=VALID_BODY)

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "ma_ho_so" in data, "Response missing ma_ho_so"
        assert TRACKING_CODE_PATTERN.match(data["ma_ho_so"]), (
            f"Tracking code format mismatch: {data['ma_ho_so']}"
        )
        assert data["form_type"] == "thuong-tru"
        assert data["status"] == "received"
        assert data["ma_ho_so"] in data["message"]
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 2 — empty form_data returns 422
# ---------------------------------------------------------------------------

async def test_submit_empty_form_data_returns_422():
    """POST /submit with all-None form_data fields returns HTTP 422."""
    mock_db = _make_mock_db()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/forms/submit",
                json={
                    "form_type": "thuong-tru",
                    "session_id": "test-session-id",
                    "submission_mode": "manual",
                    "form_data": {},  # all fields None → model_dump(exclude_none=True) → {}
                },
            )
        assert resp.status_code == 422, (
            f"Expected 422 for empty form_data, got {resp.status_code}: {resp.text}"
        )
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 3 — DB failure returns 500
# ---------------------------------------------------------------------------

async def test_submit_db_failure_returns_500():
    """POST /submit returns HTTP 500 when the DB execute raises an exception."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/v1/forms/submit", json=VALID_BODY)

        assert resp.status_code == 500, (
            f"Expected 500 on DB failure, got {resp.status_code}: {resp.text}"
        )
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 4 — tracking code generator format (pure unit, no HTTP)
# ---------------------------------------------------------------------------

def test_tracking_code_format():
    """_generate_tracking_code() produces DVC-YYYYMMDD-XXXXXX every time."""
    from app.api.v1.forms import _generate_tracking_code

    for _ in range(20):
        code = _generate_tracking_code()
        assert TRACKING_CODE_PATTERN.match(code), (
            f"Expected DVC-YYYYMMDD-[A-Z0-9]{{6}} format, got: {code}"
        )

    # Codes should be unique across invocations (collision rate negligible)
    codes = {_generate_tracking_code() for _ in range(200)}
    assert len(codes) > 190, "Too many collisions in tracking code generation"
