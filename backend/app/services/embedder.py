"""Embedding service — produces dense vectors for Qdrant ingestion and queries.

Backend selection (via EMBEDDING_BACKEND env var):
  "bge-m3"  — BAAI/bge-m3 via sentence-transformers (primary, 1024-dim)
  "openai"  — text-embedding-3-large via OpenAI API (fallback, dimensions=1024)

bge-m3 is attempted first. If it fails to load (ImportError, missing weights, etc.)
AND OPENAI_API_KEY is set, the service automatically falls back to OpenAI.
If both fail, RuntimeError is raised at __init__ time.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import openai
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Attempt top-level import of SentenceTransformer so that it can be patched
# in unit tests via patch("app.services.embedder.SentenceTransformer").
# If the package is unavailable the name is set to None and the fallback
# logic in _init_bge_m3 will handle it.
# ---------------------------------------------------------------------------
try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except ImportError:
    SentenceTransformer = None  # type: ignore[assignment,misc]


class EmbedderService:
    """Wraps bge-m3 (primary) or OpenAI text-embedding-3-large (fallback).

    Always returns exactly 1024 floats from embed().
    Backend is selected once at __init__ time and never changes.
    """

    def __init__(self) -> None:
        self._backend: str
        self._st_model = None
        self._openai_client = None

        if settings.EMBEDDING_BACKEND == "openai":
            self._init_openai()
        else:
            # Default: bge-m3, with OpenAI fallback on failure
            self._init_bge_m3()

    # ------------------------------------------------------------------
    # Private init helpers
    # ------------------------------------------------------------------

    def _init_bge_m3(self) -> None:
        """Try to load BAAI/bge-m3; fall back to OpenAI on any failure."""
        os.environ["SENTENCE_TRANSFORMERS_HOME"] = settings.SENTENCE_TRANSFORMERS_HOME
        try:
            # Use the module-level SentenceTransformer so that unit tests can
            # patch it via patch("app.services.embedder.SentenceTransformer").
            if SentenceTransformer is None:
                raise ImportError("sentence_transformers is not installed")
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._st_model = SentenceTransformer("BAAI/bge-m3", device=device)
            self._backend = "bge-m3"
            print(f"[DIAGNOSTIC] bge-m3 model.device = {self._st_model.device}")
            logger.info("bge-m3 loaded", device=device, cuda_available=torch.cuda.is_available())
        except (ImportError, Exception) as exc:
            logger.warning(
                "EmbedderService: bge-m3 failed to load (%s: %s). "
                "Attempting OpenAI fallback.",
                type(exc).__name__,
                exc,
            )
            if not settings.OPENAI_API_KEY:
                raise RuntimeError(
                    "No embedding backend available: bge-m3 failed to load and "
                    "OPENAI_API_KEY is not set."
                ) from exc
            self._init_openai()

    def _init_openai(self) -> None:
        """Initialise OpenAI async client for text-embedding-3-large."""
        if not settings.OPENAI_API_KEY:
            raise RuntimeError(
                "EmbedderService: EMBEDDING_BACKEND=openai but OPENAI_API_KEY is not set."
            )
        self._openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._backend = "openai"
        logger.info("EmbedderService: OpenAI text-embedding-3-large backend initialised.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def embed(self, text: str) -> list[float]:
        """Embed a single text string and return exactly 1024 floats.

        Args:
            text: The text to embed (will be encoded as-is).

        Returns:
            List of 1024 float values representing the embedding vector.
        """
        if self._backend == "bge-m3":
            return await self._embed_bge_m3(text)
        else:
            return await self._embed_openai(text)

    # ------------------------------------------------------------------
    # Backend-specific embed implementations
    # ------------------------------------------------------------------

    async def _embed_bge_m3(self, text: str) -> list[float]:
        loop = asyncio.get_running_loop()
        model = self._st_model

        def _encode() -> list[float]:
            vector = model.encode(text, normalize_embeddings=True)
            return [float(x) for x in vector]

        return await loop.run_in_executor(None, _encode)

    async def _embed_openai(self, text: str) -> list[float]:
        response = await self._openai_client.embeddings.create(
            model="text-embedding-3-large",
            input=text,
            dimensions=1024,
        )
        return response.data[0].embedding


# ---------------------------------------------------------------------------
# Module-level singleton — shared across QdrantService and the lifespan
# startup call so the model is only loaded once per process.
# Replace in tests: patch("app.services.embedder._embedder_svc", mock_svc)
# ---------------------------------------------------------------------------

_embedder_svc: EmbedderService | None = None


def _get_embedder() -> EmbedderService:
    """Return the shared EmbedderService instance, creating it on first call."""
    global _embedder_svc
    if _embedder_svc is None:
        _embedder_svc = EmbedderService()
    return _embedder_svc
