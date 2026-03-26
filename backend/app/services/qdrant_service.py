"""Qdrant service — hybrid dense+BM25 search over legal document chunks.

Chunk payload schema
--------------------
Every point stored in Qdrant must carry the following payload fields:

    {
        "document_number": str,          # e.g. "123/2021/NĐ-CP"
        "article_number":  str,          # e.g. "Điều 15"
        "title":           str,          # chunk heading
        "procedure_tags":  list[str],    # procedure IDs this chunk is tagged to
        "status":          "active" | "superseded",
    }

Search always filters on status == "active" so superseded chunks are never
returned to the LLM or cited.  Use _active_filter() to obtain the filter
object — do NOT inline the filter condition in search paths.
"""

from __future__ import annotations


class QdrantService:
    """Qdrant vector store client with hybrid retrieval."""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _active_filter():
        """Return a Qdrant Filter that restricts results to active chunks.

        Both the dense and BM25 search paths MUST pass this filter so that
        superseded chunks are never surfaced to the LLM or included in
        citations.

        Real implementation (TASK-02) will look like:
            from qdrant_client.models import FieldCondition, Filter, MatchValue
            return Filter(
                must=[FieldCondition(key="status", match=MatchValue(value="active"))]
            )
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        procedure_id: str | None = None,
        top_k: int = 8,
    ) -> list[dict]:
        """Hybrid search: semantic (dense) + lexical (BM25), merged via RRF.

        Both search stages MUST include _active_filter() so that superseded
        chunks are excluded from all result sets before RRF merging.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def upsert_chunks(self, chunks: list[dict]) -> None:
        """Upsert a batch of chunks.  Each chunk dict must include all payload
        fields listed in the module docstring, including ``status: "active"``.
        """
        raise NotImplementedError

    async def batch_set_status(self, point_ids: list[str], status: str) -> None:
        """Overwrite the ``status`` payload field on a set of existing points.

        Used by the re-ingestion path to mark old chunks as ``"superseded"``
        before upserting the new version.

        Args:
            point_ids: List of Qdrant point UUIDs to update.
            status:    New status value — ``"active"`` or ``"superseded"``.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Re-ingestion helpers
    # ------------------------------------------------------------------

    async def scroll_by_document_number(self, document_number: str) -> list[str]:
        """Return all point IDs whose payload.document_number matches.

        Used by the re-ingestion path to find existing chunks before
        superseding them.  Returns an empty list when the document has never
        been ingested before.

        Args:
            document_number: e.g. ``"123/2021/NĐ-CP"``

        Returns:
            List of Qdrant point UUID strings.
        """
        raise NotImplementedError
