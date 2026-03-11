"""Qdrant service — hybrid dense+BM25 search over legal document chunks."""


class QdrantService:
    """Qdrant vector store client with hybrid retrieval."""

    async def search(
        self,
        query: str,
        procedure_id: str | None = None,
        top_k: int = 8,
    ) -> list[dict]:
        """Hybrid search: semantic (dense) + lexical (BM25), merged via RRF."""
        raise NotImplementedError

    async def upsert_chunks(self, chunks: list[dict]) -> None:
        raise NotImplementedError
