"""LLM service — wraps Anthropic AsyncAnthropic or Google Gemini (google.genai).

The active backend is controlled by the LLM_BACKEND environment variable:
  - "anthropic" (default) — uses anthropic.AsyncAnthropic
  - "gemini"              — uses google.genai (synchronous client wrapped in executor)

The public interface (async_invoke / stream) is identical regardless of backend.
Nothing outside this module needs to know which backend is active.

Usage
-----
    svc = LLMService()
    text = await svc.async_invoke(system="...", messages=[{"role": "user", "content": "..."}])

    async for chunk in svc.stream(system="...", messages=[...]):
        print(chunk, end="", flush=True)
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
from collections.abc import AsyncIterator

import structlog

log = structlog.get_logger(__name__)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Message conversion helpers
# ---------------------------------------------------------------------------

def _anthropic_to_genai_contents(messages: list[dict]) -> list:
    """Convert Anthropic-format messages to google.genai types.Content list.

    Anthropic:  {"role": "user"|"assistant", "content": str | list[block]}
    google.genai Content: types.Content(role="user"|"model", parts=[types.Part(...)])
    """
    from google.genai import types as _types

    contents = []
    for msg in messages:
        role = msg.get("role", "user")
        genai_role = "model" if role == "assistant" else "user"
        content = msg.get("content", "")

        if isinstance(content, str):
            parts = [_types.Part(text=content)]
        elif isinstance(content, list):
            parts = []
            for block in content:
                btype = block.get("type")
                if btype == "text":
                    parts.append(_types.Part(text=block.get("text", "")))
                elif btype == "image":
                    source = block.get("source", {})
                    if source.get("type") == "base64":
                        img_bytes = base64.b64decode(source["data"])
                        mime = source.get("media_type", "image/jpeg")
                        parts.append(_types.Part.from_bytes(data=img_bytes, mime_type=mime))
        else:
            parts = []

        if parts:
            contents.append(_types.Content(role=genai_role, parts=parts))
    return contents


def _has_image_content(messages: list[dict]) -> bool:
    """Return True if any message contains an image content block."""
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                if block.get("type") == "image":
                    return True
    return False


# ---------------------------------------------------------------------------
# LLMService
# ---------------------------------------------------------------------------

class LLMService:
    """Unified async LLM wrapper supporting Anthropic, Gemini, and local (Ollama) backends.

    Constructor accepts an optional ``backend`` override so individual callers
    (e.g. the router singleton) can target a different backend than the rest of
    the system without modifying ``LLM_BACKEND`` globally.

    Args:
        backend: Override the backend for this instance.  If None, reads
                 ``settings.LLM_BACKEND``.  Valid: ``"anthropic"``,
                 ``"gemini"``, ``"local"``.
        settings: Injected settings for testing.  Defaults to global settings.
    """

    def __init__(self, backend: str | None = None, model: str | None = None, settings=None) -> None:
        if settings is None:
            from app.config import settings as _s
            settings = _s

        self.backend: str = backend or settings.LLM_BACKEND

        if self.backend == "anthropic":
            import anthropic as _anthropic
            self._client = _anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            self._model: str = settings.LLM_MODEL
            logger.warning(f"[LLM INIT] model={self._model}")
            # LangSmith tracing — wire env vars at construction so every call is traced
            if settings.LANGSMITH_API_KEY:
                os.environ["LANGCHAIN_TRACING_V2"] = "true"
                os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
            else:
                logger.warning(
                    "LANGSMITH_API_KEY is not set — LangSmith tracing is disabled. "
                    "Set it in .env to enable observability."
                )

        elif self.backend == "gemini":
            from google import genai
            self._genai_client = genai.Client(api_key=settings.GOOGLE_API_KEY)
            self._model = settings.GEMINI_MODEL
            log.info(
                "llm_backend_gemini",
                note="LangSmith tracing not active for Gemini backend",
                model=self._model,
            )

        elif self.backend == "local":
            import openai as _openai
            self._local_client = _openai.AsyncOpenAI(
                base_url=settings.LOCAL_LLM_URL,
                api_key="ollama",  # Ollama ignores the key; SDK requires non-empty
            )
            self._model: str = model or settings.LOCAL_LLM_MODEL
            log.info(
                "llm_backend_local",
                model=self._model,
                base_url=settings.LOCAL_LLM_URL,
                note="LangSmith tracing not active for local backend",
            )

        else:
            raise ValueError(
                f"Unknown LLM_BACKEND: {self.backend!r}. "
                f"Valid values: 'anthropic', 'gemini', 'local'"
            )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def async_invoke(
        self,
        system: str | None = None,
        messages: list[dict] | None = None,
        max_tokens: int = 1024,
        json_mode: bool = False,
    ) -> str:
        """Send a non-streaming request and return the full response text.

        json_mode is only honoured by the local (Ollama) backend — it activates
        response_format={"type": "json_object"}.  The Anthropic and Gemini paths
        are completely unchanged by this parameter.
        """
        if messages is None:
            messages = []

        if self.backend == "anthropic":
            logger.warning(f"[LLM CALL] sending model={self._model} to API")
            response = await self._client.messages.create(
                model=self._model,
                system=system or "",
                messages=messages,
                max_tokens=max_tokens,
            )
            return response.content[0].text

        elif self.backend == "gemini":
            return await self._gemini_invoke(system, messages, max_tokens)

        elif self.backend == "local":
            return await self._local_invoke(system, messages, max_tokens, json_mode)

        raise ValueError(f"Unknown backend: {self.backend!r}")

    async def stream(
        self,
        system: str | None = None,
        messages: list[dict] | None = None,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        """Stream the response, yielding text deltas as they arrive."""
        if messages is None:
            messages = []

        if self.backend == "anthropic":
            async with self._client.messages.stream(
                model=self._model,
                system=system or "",
                messages=messages,
                max_tokens=max_tokens,
            ) as stream_ctx:
                async for text in stream_ctx.text_stream:
                    yield text

        elif self.backend == "gemini":
            async for chunk in self._gemini_stream(system, messages, max_tokens):
                yield chunk

        elif self.backend == "local":
            raise NotImplementedError(
                "Local (Ollama) backend does not support streaming. "
                "Use async_invoke() for local-backend callers (router, RAG)."
            )

        else:
            raise ValueError(f"Unknown backend: {self.backend!r}")

    # ------------------------------------------------------------------
    # Local (Ollama) private helper
    # ------------------------------------------------------------------

    async def _local_invoke(
        self,
        system: str | None,
        messages: list[dict],
        max_tokens: int,
        json_mode: bool = False,
    ) -> str:
        """Non-streaming call to Ollama via the OpenAI-compatible endpoint."""
        import openai as _openai

        openai_messages: list[dict] = []
        if system:
            openai_messages.append({"role": "system", "content": system})
        openai_messages.extend(messages)

        create_kwargs: dict = {
            "model": self._model,
            "messages": openai_messages,
            "max_tokens": max_tokens,
        }
        if json_mode:
            create_kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await self._local_client.chat.completions.create(**create_kwargs)
            return response.choices[0].message.content or ""
        except _openai.APIConnectionError as exc:
            raise RuntimeError(
                f"Ollama is not running or not reachable at {self._local_client.base_url}. "
                "Start it with: ollama serve"
            ) from exc

    # ------------------------------------------------------------------
    # Gemini private helpers (google.genai SDK)
    # ------------------------------------------------------------------

    async def _gemini_invoke(
        self,
        system: str | None,
        messages: list[dict],
        max_tokens: int,
    ) -> str:
        """Non-streaming Gemini call using google.genai."""
        from google.genai import types

        loop = asyncio.get_running_loop()
        contents = _anthropic_to_genai_contents(messages)
        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
        )

        response = await loop.run_in_executor(
            None,
            lambda: self._genai_client.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            ),
        )
        if response.text is None:
            finish_reason = (
                response.candidates[0].finish_reason
                if response.candidates
                else "unknown"
            )
            log.warning(
                "gemini_invoke_empty_response",
                model=self._model,
                finish_reason=str(finish_reason),
                max_tokens=max_tokens,
            )
            return ""
        return response.text

    async def _gemini_stream(
        self,
        system: str | None,
        messages: list[dict],
        max_tokens: int,
    ) -> AsyncIterator[str]:
        """Streaming Gemini call — wraps synchronous stream in executor."""
        from google.genai import types

        loop = asyncio.get_running_loop()
        contents = _anthropic_to_genai_contents(messages)
        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
        )

        chunks = await loop.run_in_executor(
            None,
            lambda: list(
                self._genai_client.models.generate_content_stream(
                    model=self._model,
                    contents=contents,
                    config=config,
                )
            ),
        )
        for chunk in chunks:
            if chunk.text:
                yield chunk.text
