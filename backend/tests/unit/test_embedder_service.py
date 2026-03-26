"""Unit tests for EmbedderService (app.services.embedder).

All external calls are mocked. No real model downloads or API calls are made.
asyncio_mode=auto is set in pyproject.toml — no @pytest.mark.asyncio needed.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from app.services.embedder import EmbedderService


# ---------------------------------------------------------------------------
# Helper: build a mock SentenceTransformer instance that returns a 1024-dim vector
# ---------------------------------------------------------------------------

def _make_st_instance_mock() -> MagicMock:
    """A mock that behaves like a loaded SentenceTransformer instance."""
    model = MagicMock()
    model.encode.return_value = np.ones(1024, dtype=np.float32)
    return model


def _make_st_class_mock() -> MagicMock:
    """A mock that behaves like the SentenceTransformer class (callable → instance)."""
    cls_mock = MagicMock(return_value=_make_st_instance_mock())
    return cls_mock


# ---------------------------------------------------------------------------
# Test 1 — bge-m3 returns 1024 floats
# ---------------------------------------------------------------------------

async def test_bge_m3_returns_1024_floats():
    """EmbedderService with bge-m3 backend should return a list of 1024 floats."""
    st_class = _make_st_class_mock()
    with patch("app.services.embedder.SentenceTransformer", st_class):
        with patch("app.services.embedder.settings") as mock_settings:
            mock_settings.EMBEDDING_BACKEND = "bge-m3"
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.SENTENCE_TRANSFORMERS_HOME = ".cache/"

            svc = EmbedderService()
            result = await svc.embed("test query")

    assert isinstance(result, list)
    assert len(result) == 1024
    assert all(isinstance(x, float) for x in result)


# ---------------------------------------------------------------------------
# Test 2 — OpenAI backend returns 1024 floats and passes dimensions=1024
# ---------------------------------------------------------------------------

async def test_openai_returns_1024_floats():
    """EmbedderService with openai backend returns 1024 floats and passes dimensions=1024."""
    fake_embedding = [0.1] * 1024
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=fake_embedding)]

    mock_create = AsyncMock(return_value=mock_response)
    mock_client_instance = MagicMock()
    mock_client_instance.embeddings = MagicMock()
    mock_client_instance.embeddings.create = mock_create

    with patch("app.services.embedder.openai.AsyncOpenAI", return_value=mock_client_instance):
        with patch("app.services.embedder.settings") as mock_settings:
            mock_settings.EMBEDDING_BACKEND = "openai"
            mock_settings.OPENAI_API_KEY = "sk-test"
            mock_settings.SENTENCE_TRANSFORMERS_HOME = ".cache/"

            svc = EmbedderService()
            result = await svc.embed("test query")

    assert isinstance(result, list)
    assert len(result) == 1024

    # Verify dimensions=1024 was passed to create()
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs.get("dimensions") == 1024


# ---------------------------------------------------------------------------
# Test 3 — bge-m3 ImportError falls back to OpenAI
# ---------------------------------------------------------------------------

async def test_bge_m3_import_error_falls_back_to_openai():
    """When SentenceTransformer raises ImportError, service falls back to OpenAI backend."""
    mock_client_instance = MagicMock()
    mock_client_instance.embeddings = MagicMock()
    mock_client_instance.embeddings.create = AsyncMock()

    # Patch the class-level name so calling it raises ImportError
    with patch(
        "app.services.embedder.SentenceTransformer",
        side_effect=ImportError("no module"),
    ):
        with patch("app.services.embedder.openai.AsyncOpenAI", return_value=mock_client_instance):
            with patch("app.services.embedder.settings") as mock_settings:
                mock_settings.EMBEDDING_BACKEND = "bge-m3"
                mock_settings.OPENAI_API_KEY = "sk-test"
                mock_settings.SENTENCE_TRANSFORMERS_HOME = ".cache/"

                svc = EmbedderService()
                assert svc._backend == "openai"


# ---------------------------------------------------------------------------
# Test 4 — both backends fail → RuntimeError raised at __init__
# ---------------------------------------------------------------------------

def test_both_fail_raises_runtime_error():
    """When bge-m3 fails AND OPENAI_API_KEY is empty, RuntimeError is raised at init."""
    with patch(
        "app.services.embedder.SentenceTransformer",
        side_effect=ImportError("no module"),
    ):
        with patch("app.services.embedder.settings") as mock_settings:
            mock_settings.EMBEDDING_BACKEND = "bge-m3"
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.SENTENCE_TRANSFORMERS_HOME = ".cache/"

            with pytest.raises(RuntimeError, match="No embedding backend available"):
                EmbedderService()


# ---------------------------------------------------------------------------
# Test 5 — embed is a coroutine function (async)
# ---------------------------------------------------------------------------

def test_embed_is_async():
    """EmbedderService.embed must be a coroutine function."""
    assert asyncio.iscoroutinefunction(EmbedderService.embed)
