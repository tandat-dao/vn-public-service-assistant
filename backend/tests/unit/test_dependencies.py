"""Unit tests for FastAPI dependency providers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture()
def mock_session():
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture()
def mock_factory(mock_session):
    factory = MagicMock(return_value=mock_session)
    return factory


async def _collect_get_db(factory):
    """Helper: patch factory and collect yielded session + track close/rollback calls."""
    with patch("app.dependencies._async_session_factory", factory):
        from app.dependencies import get_db

        gen = get_db()
        session = await gen.__anext__()
        return gen, session


class TestGetDb:
    async def test_yields_async_session(self, mock_factory, mock_session):
        gen, session = await _collect_get_db(mock_factory)
        assert session is mock_session
        # clean teardown
        try:
            await gen.aclose()
        except StopAsyncIteration:
            pass

    async def test_rollback_called_on_exception(self, mock_factory, mock_session):
        with patch("app.dependencies._async_session_factory", mock_factory):
            from app.dependencies import get_db

            gen = get_db()
            await gen.__anext__()
            with pytest.raises(ValueError):
                await gen.athrow(ValueError("boom"))

        mock_session.rollback.assert_awaited_once()

    async def test_close_always_called(self, mock_factory, mock_session):
        # Happy path
        with patch("app.dependencies._async_session_factory", mock_factory):
            from app.dependencies import get_db

            gen = get_db()
            await gen.__anext__()
            await gen.aclose()

        mock_session.close.assert_awaited()

    async def test_close_called_on_exception(self, mock_factory, mock_session):
        with patch("app.dependencies._async_session_factory", mock_factory):
            from app.dependencies import get_db

            gen = get_db()
            await gen.__anext__()
            with pytest.raises(RuntimeError):
                await gen.athrow(RuntimeError("err"))

        mock_session.close.assert_awaited()
