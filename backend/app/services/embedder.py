"""Embedding service — produces dense vectors for Qdrant ingestion and queries."""


class EmbedderService:
    """Wraps bge-m3 (or OpenAI) embedding model."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError
