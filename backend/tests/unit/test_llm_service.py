"""Unit tests for LLMService — Anthropic and Gemini backends.

All LLM calls are mocked — no real API calls are made.

Gemini backend uses google.genai (Client-based API, NOT the deprecated
google.generativeai). The client is constructed with:
    genai.Client(api_key=...) → client.models.generate_content(...)

Mocking strategy:
  Both backends use lazy `import X` statements inside __init__, so stubs
  must be active at instance-construction time. The helpers below build
  the instance inside a patch.dict context so those imports pick up stubs.
"""

from __future__ import annotations

import importlib
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(backend: str = "anthropic") -> MagicMock:
    s = MagicMock()
    s.LLM_BACKEND = backend
    s.ANTHROPIC_API_KEY = "sk-ant-test"
    s.LLM_MODEL = "claude-test-model"
    s.LANGSMITH_API_KEY = ""
    s.GOOGLE_API_KEY = "AIza-test"
    s.GEMINI_MODEL = "gemini-test-model"
    return s


def _make_anthropic_service(mock_client: MagicMock):
    """Create an Anthropic LLMService with a stubbed anthropic module."""
    mock_anthropic = MagicMock()
    mock_anthropic.AsyncAnthropic = MagicMock(return_value=mock_client)

    sys.modules.pop("app.services.llm", None)
    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        import app.services.llm as llm_mod
        importlib.reload(llm_mod)
        svc = llm_mod.LLMService(settings=_make_settings("anthropic"))
        svc._client = mock_client
    return svc


def _make_gemini_service(mock_genai_module: MagicMock, mock_google: MagicMock):
    """Create a Gemini LLMService with stubbed google.genai module.

    The instance is built inside the patch.dict context so that
    `from google import genai` inside __init__ picks up the stub.
    """
    sys.modules.pop("app.services.llm", None)
    with patch.dict("sys.modules", {
        "google": mock_google,
        "google.genai": mock_genai_module,
        "google.genai.types": MagicMock(),
    }):
        import app.services.llm as llm_mod
        importlib.reload(llm_mod)
        svc = llm_mod.LLMService(settings=_make_settings("gemini"))
    return svc


def _stub_google_genai(response_text: str = "ok"):
    """Build minimal google / google.genai stubs.

    Returns (mock_genai_module, mock_google, mock_genai_client, mock_models).
    """
    mock_response = MagicMock()
    mock_response.text = response_text

    mock_models = MagicMock()
    mock_models.generate_content = MagicMock(return_value=mock_response)
    mock_models.generate_content_stream = MagicMock(return_value=iter([mock_response]))

    mock_client = MagicMock()
    mock_client.models = mock_models

    mock_genai_module = MagicMock()
    mock_genai_module.Client = MagicMock(return_value=mock_client)

    mock_google = MagicMock()
    mock_google.genai = mock_genai_module

    return mock_genai_module, mock_google, mock_client, mock_models


# ---------------------------------------------------------------------------
# Unknown backend
# ---------------------------------------------------------------------------

def test_unknown_backend_raises_value_error():
    sys.modules.pop("app.services.llm", None)
    import app.services.llm as llm_mod
    importlib.reload(llm_mod)
    with pytest.raises(ValueError, match="Unknown LLM_BACKEND"):
        llm_mod.LLMService(settings=_make_settings("turbo-gpt-99"))


# ---------------------------------------------------------------------------
# Anthropic backend — init
# ---------------------------------------------------------------------------

def test_anthropic_backend_initialises_without_error():
    mock_client = MagicMock()
    svc = _make_anthropic_service(mock_client)
    assert svc.backend == "anthropic"


# ---------------------------------------------------------------------------
# Anthropic backend — async_invoke
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anthropic_async_invoke_returns_string():
    mock_content = MagicMock()
    mock_content.text = "Hà Nội là thủ đô Việt Nam."
    mock_response = MagicMock()
    mock_response.content = [mock_content]

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    svc = _make_anthropic_service(mock_client)
    result = await svc.async_invoke(
        system="Bạn là trợ lý.",
        messages=[{"role": "user", "content": "Thủ đô Việt Nam?"}],
    )
    assert result == "Hà Nội là thủ đô Việt Nam."


# ---------------------------------------------------------------------------
# Anthropic backend — stream
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anthropic_stream_yields_chunks():
    async def _fake_text_stream():
        for chunk in ["Xin ", "chào", "!"]:
            yield chunk

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream_ctx)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_stream_ctx.text_stream = _fake_text_stream()

    mock_client = MagicMock()
    mock_client.messages.stream = MagicMock(return_value=mock_stream_ctx)

    svc = _make_anthropic_service(mock_client)
    chunks = []
    async for chunk in svc.stream(
        system="Bạn là trợ lý.",
        messages=[{"role": "user", "content": "Chào!"}],
    ):
        chunks.append(chunk)

    assert chunks == ["Xin ", "chào", "!"]


# ---------------------------------------------------------------------------
# Gemini backend — init
# ---------------------------------------------------------------------------

def test_gemini_backend_initialises_without_error():
    mock_genai_module, mock_google, mock_client, _ = _stub_google_genai()
    svc = _make_gemini_service(mock_genai_module, mock_google)
    assert svc.backend == "gemini"
    mock_genai_module.Client.assert_called_once_with(api_key="AIza-test")


# ---------------------------------------------------------------------------
# Gemini backend — async_invoke (text-only)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gemini_async_invoke_returns_string():
    mock_genai_module, mock_google, mock_client, mock_models = _stub_google_genai(
        "Thành phố Hồ Chí Minh."
    )
    svc = _make_gemini_service(mock_genai_module, mock_google)

    result = await svc.async_invoke(
        system="Bạn là trợ lý.",
        messages=[{"role": "user", "content": "Thành phố lớn nhất VN?"}],
    )
    assert isinstance(result, str)
    assert result == "Thành phố Hồ Chí Minh."
    mock_models.generate_content.assert_called_once()


# ---------------------------------------------------------------------------
# Gemini backend — stream (text-only)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gemini_stream_yields_chunks():
    chunk1 = MagicMock()
    chunk1.text = "Xin "
    chunk2 = MagicMock()
    chunk2.text = "chào!"

    mock_models = MagicMock()
    mock_models.generate_content_stream = MagicMock(return_value=iter([chunk1, chunk2]))

    mock_client = MagicMock()
    mock_client.models = mock_models

    mock_genai_module = MagicMock()
    mock_genai_module.Client = MagicMock(return_value=mock_client)
    mock_google = MagicMock()
    mock_google.genai = mock_genai_module

    svc = _make_gemini_service(mock_genai_module, mock_google)
    chunks = []
    async for chunk in svc.stream(
        system="Bạn là trợ lý.",
        messages=[{"role": "user", "content": "Chào!"}],
    ):
        chunks.append(chunk)

    assert "Xin " in chunks
    assert "chào!" in chunks


# ---------------------------------------------------------------------------
# Gemini backend — async_invoke with vision content (image blocks)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gemini_async_invoke_with_image_content():
    mock_genai_module, mock_google, mock_client, mock_models = _stub_google_genai("cccd")

    # Minimal 1×1 white PNG in base64
    tiny_png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
        "z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
    )
    image_message = {
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": tiny_png_b64},
            },
            {"type": "text", "text": "Loại tài liệu này là gì?"},
        ],
    }

    svc = _make_gemini_service(mock_genai_module, mock_google)
    result = await svc.async_invoke(
        system="Phân loại tài liệu.",
        messages=[image_message],
    )
    assert result == "cccd"
    mock_models.generate_content.assert_called_once()
