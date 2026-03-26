"""LLM service — wraps the Anthropic AsyncAnthropic client for agent use.

Usage
-----
    svc = LLMService()
    text = await svc.async_invoke(system="...", messages=[{"role": "user", "content": "..."}])

    async for chunk in svc.stream(system="...", messages=[...]):
        print(chunk, end="", flush=True)
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Thin async wrapper around :class:`anthropic.AsyncAnthropic`.

    Handles LangSmith tracing wiring at construction time so every call
    made through this service is automatically traced when the API key is
    present.
    """

    def __init__(self) -> None:
        if settings.LANGSMITH_API_KEY:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
        else:
            logger.warning(
                "LANGSMITH_API_KEY is not set — LangSmith tracing is disabled. "
                "Set it in .env to enable observability."
            )

        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.LLM_MODEL

    async def async_invoke(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = 1024,
    ) -> str:
        """Send a non-streaming request and return the full response text.

        Args:
            system:     System prompt string.
            messages:   List of ``{"role": ..., "content": ...}`` dicts.
            max_tokens: Maximum tokens in the response.

        Returns:
            The model's text response as a single string.

        Raises:
            anthropic.APIError: On network or API errors — not swallowed here.
        """
        response = await self._client.messages.create(
            model=self._model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
        )
        return response.content[0].text

    async def stream(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        """Stream the response, yielding text deltas as they arrive.

        Args:
            system:     System prompt string.
            messages:   List of ``{"role": ..., "content": ...}`` dicts.
            max_tokens: Maximum tokens in the response.

        Yields:
            Text delta strings from the streaming response.

        Raises:
            anthropic.APIError: On network or API errors — not swallowed here.
        """
        async with self._client.messages.stream(
            model=self._model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
        ) as stream:
            async for text in stream.text_stream:
                yield text
