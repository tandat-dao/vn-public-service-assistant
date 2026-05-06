"""Qdrant service — hybrid dense+BM25 search over legal document chunks.

Chunk payload schema
--------------------
Every point stored in Qdrant must carry the following payload fields:

    {
        "legal_document_id": str,        # UUID of the PostgreSQL legal_documents row
        "document_number": str,          # e.g. "123/2021/NĐ-CP"
        "article_number":  str,          # e.g. "Điều 15"
        "content":         str,          # chunk text
        "procedure_tags":  list[str],    # procedure IDs this chunk is tagged to
        "status":          "active" | "superseded",
    }

Search always filters on status == "active" so superseded chunks are never
returned to the LLM or cited.  Use _active_filter() to obtain the filter
object — do NOT inline the filter condition in search paths.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    VectorParams,
)
from rank_bm25 import BM25Okapi

from app.config import settings
from app.schemas.rag import DocumentChunk
from app.services.embedder import _get_embedder

logger = logging.getLogger(__name__)

_BATCH_SIZE = 100


class QdrantService:
    """Qdrant vector store client with hybrid dense+BM25 retrieval."""

    def __init__(self) -> None:
        self._client = AsyncQdrantClient(url=settings.QDRANT_URL)
        self.embedder = _get_embedder()

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    async def create_collection(self) -> None:
        """Create the legal_documents collection if it does not already exist.

        Idempotent — silently returns if the collection already exists.
        """
        try:
            await self._client.create_collection(
                collection_name=settings.QDRANT_COLLECTION,
                vectors_config=VectorParams(
                    size=settings.QDRANT_VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(
                "QdrantService: collection '%s' created.", settings.QDRANT_COLLECTION
            )
        except UnexpectedResponse as exc:
            if "already exists" in str(exc).lower():
                logger.debug(
                    "QdrantService: collection '%s' already exists — skipping creation.",
                    settings.QDRANT_COLLECTION,
                )
            else:
                raise

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def upsert(self, chunks: list[dict[str, Any]]) -> None:
        """Batch-upsert raw chunk dicts into Qdrant.

        Each dict must contain all payload fields listed in the module docstring.
        The ``status`` field is forced to ``"active"`` on every upserted point.

        Args:
            chunks: List of chunk dicts produced by the ingestion script.
                    Each must include ``content`` (used for embedding) plus
                    all required payload fields.
        """
        total = len(chunks)
        for batch_start in range(0, total, _BATCH_SIZE):
            batch = chunks[batch_start : batch_start + _BATCH_SIZE]
            points: list[PointStruct] = []

            for chunk in batch:
                embedding = await self.embedder.embed(chunk["content"])
                payload = {k: v for k, v in chunk.items() if k != "content"}
                payload["content"] = chunk["content"]
                payload["status"] = "active"  # always force active on upsert

                point_id = chunk.get("point_id") or str(uuid.uuid4())
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload,
                    )
                )

            await self._client.upsert(
                collection_name=settings.QDRANT_COLLECTION,
                points=points,
            )
            logger.info(
                "QdrantService: upserted batch %d-%d of %d points.",
                batch_start + 1,
                batch_start + len(batch),
                total,
            )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        procedure_id: str | None = None,
        top_k: int | None = None,
        scope: str | None = None,
    ) -> list[DocumentChunk]:
        """Hybrid search: semantic (dense) + lexical (BM25), merged via RRF.

        Both search stages apply _active_filter() so that superseded chunks
        are excluded from all result sets before RRF merging.

        Args:
            query:        User query string.
            procedure_id: Optional — restrict results to chunks tagged with
                          this procedure ID in their payload.
            top_k:        Maximum chunks to return (defaults to settings.RAG_TOP_K).
            scope:        Optional — restrict results to chunks whose payload
                          ``scope`` field exactly matches this scope code
                          (e.g. "VN", "VN-HCM", "VN-HCM-26968"). Stacks with
                          the status and procedure_id filters. When None, no
                          scope filter is applied.

        Returns:
            List of DocumentChunk objects ordered by descending RRF score,
            capped at ``top_k`` and the 6,000-token budget.
        """
        if top_k is None:
            top_k = settings.RAG_TOP_K

        search_filter = self._build_filter(procedure_id, scope=scope)

        # ---- Stage 1: Dense semantic search ----
        embedding = await self.embedder.embed(query)
        _query_response = await self._client.query_points(
            collection_name=settings.QDRANT_COLLECTION,
            query=embedding,
            limit=top_k * 2,
            query_filter=search_filter,
            with_payload=True,
        )
        dense_results = _query_response.points

        # ---- Stage 2: BM25 over active corpus ----
        scroll_results, _ = await self._client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            scroll_filter=search_filter,
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )

        bm25_ids: list[str] = []
        payload_lookup: dict[str, dict[str, Any]] = {}

        # Collect payloads from scroll (covers full active corpus)
        for point in scroll_results:
            payload_lookup[str(point.id)] = point.payload or {}

        # Supplement with dense result payloads (in case scroll limit was hit)
        for result in dense_results:
            pid = str(result.id)
            if pid not in payload_lookup:
                payload_lookup[pid] = result.payload or {}

        if scroll_results:
            id_content_pairs = [
                (str(p.id), (p.payload or {}).get("content", ""))
                for p in scroll_results
            ]
            corpus = [content.split() for _, content in id_content_pairs]
            bm25 = BM25Okapi(corpus)
            scores = bm25.get_scores(query.split())

            # Get top top_k*2 indices by BM25 score
            top_indices = sorted(
                range(len(scores)), key=lambda i: scores[i], reverse=True
            )[: top_k * 2]
            bm25_ids = [id_content_pairs[i][0] for i in top_indices]

        # ---- Stage 3: Reciprocal Rank Fusion ----
        dense_ranks: dict[str, int] = {
            str(r.id): i + 1 for i, r in enumerate(dense_results)
        }
        bm25_ranks: dict[str, int] = {
            pid: i + 1 for i, pid in enumerate(bm25_ids)
        }

        all_ids = set(dense_ranks.keys()) | set(bm25_ranks.keys())
        rrf_scores: dict[str, float] = {}
        for pid in all_ids:
            score = 0.0
            if pid in dense_ranks:
                score += 1.0 / (dense_ranks[pid] + 60)
            if pid in bm25_ranks:
                score += 1.0 / (bm25_ranks[pid] + 60)
            rrf_scores[pid] = score

        sorted_ids = sorted(all_ids, key=lambda pid: rrf_scores[pid], reverse=True)

        # ---- Token budget enforcement ----
        # Iterate sorted_ids without a top_k cap here — dedup+slice below.
        result: list[DocumentChunk] = []
        used_tokens = 0

        for pid in sorted_ids:
            payload = payload_lookup.get(pid, {})
            content = payload.get("content", "")
            chunk_tokens = len(content) // 4

            if used_tokens + chunk_tokens > settings.RAG_TOKEN_BUDGET:
                break

            used_tokens += chunk_tokens

            # structured_summary may be stored as dict/list (ingestion) or str — normalise to str
            raw_summary = payload.get("structured_summary")
            if raw_summary is None or isinstance(raw_summary, str):
                structured_summary: str | None = raw_summary
            else:
                import json as _json
                structured_summary = _json.dumps(raw_summary, ensure_ascii=False)

            result.append(
                DocumentChunk(
                    point_id=pid,
                    legal_document_id=payload.get("legal_document_id", ""),
                    document_number=payload.get("document_number", ""),
                    article_number=payload.get("article_number", ""),
                    content=content,
                    procedure_tags=payload.get("procedure_tags", []),
                    status=payload.get("status", "active"),
                    rrf_score=rrf_scores[pid],
                    structured_summary=structured_summary,
                )
            )

        deduplicated = self._deduplicate_by_article(result)
        logger.debug(
            "RAG token budget: %d/%d tokens, %d chunks after dedup (from %d)",
            used_tokens,
            settings.RAG_TOKEN_BUDGET,
            len(deduplicated),
            len(result),
        )
        return deduplicated[:top_k]

    # ------------------------------------------------------------------
    # Status management
    # ------------------------------------------------------------------

    async def update_status(self, document_number: str, new_status: str) -> int:
        """Soft-update the status of all chunks with the given document number.

        Used by the re-ingestion flow to mark old chunks as "superseded"
        before upserting the new version.

        Args:
            document_number: e.g. "123/2021/NĐ-CP"
            new_status:      "active" or "superseded"

        Returns:
            Number of points updated.
        """
        point_ids = await self.scroll_by_document_number(document_number)
        if not point_ids:
            return 0
        await self.batch_set_status(point_ids, new_status)
        return len(point_ids)

    async def scroll_by_document_number(
        self, document_number: str, domain: str | None = None
    ) -> list[str]:
        """Return all point IDs whose payload.document_number matches.

        Used by the re-ingestion path to find existing chunks before
        superseding them. Returns an empty list when the document has never
        been ingested before.

        Args:
            document_number: e.g. "123/2021/NĐ-CP"
            domain:          When provided, only chunks whose payload.domain
                             matches are returned.  This prevents a shared
                             document (e.g. 120/2025/NĐ-CP used by both
                             housing and adoption) from superseding another
                             domain's chunks during re-ingestion.

        Returns:
            List of Qdrant point UUID strings.
        """
        conditions: list[FieldCondition] = [
            FieldCondition(
                key="document_number",
                match=MatchValue(value=document_number),
            )
        ]
        if domain is not None:
            conditions.append(
                FieldCondition(
                    key="domain",
                    match=MatchValue(value=domain),
                )
            )
        doc_filter = Filter(must=conditions)
        results, _ = await self._client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            scroll_filter=doc_filter,
            limit=10000,
            with_payload=False,
            with_vectors=False,
        )
        return [str(p.id) for p in results]

    async def batch_set_status(self, point_ids: list[str], status: str) -> None:
        """Overwrite the ``status`` payload field on a set of existing points.

        Used by the re-ingestion path to mark old chunks as ``"superseded"``
        before upserting the new version.

        Args:
            point_ids: List of Qdrant point UUIDs to update.
            status:    New status value — ``"active"`` or ``"superseded"``.
        """
        if not point_ids:
            return
        from qdrant_client.models import SetPayload  # import here to keep top-level clean

        for batch_start in range(0, len(point_ids), _BATCH_SIZE):
            batch = point_ids[batch_start : batch_start + _BATCH_SIZE]
            await self._client.set_payload(
                collection_name=settings.QDRANT_COLLECTION,
                payload={"status": status},
                points=batch,
            )
        logger.info(
            "QdrantService: set status='%s' on %d points.", status, len(point_ids)
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _active_filter() -> Filter:
        """Return a Qdrant Filter that restricts results to active chunks.

        Both the dense and BM25 search paths MUST pass this filter so that
        superseded chunks are never surfaced to the LLM or included in
        citations. Kept for backwards compatibility with ingestion scripts.
        """
        return Filter(
            must=[FieldCondition(key="status", match=MatchValue(value="active"))]
        )

    def _deduplicate_by_article(
        self, chunks: list[DocumentChunk]
    ) -> list[DocumentChunk]:
        """Keep only the highest-scoring chunk per (article_number, document_number).

        Prevents paragraph-fallback chunks from the same article flooding the
        top-K results.  Chunks are assumed to be pre-sorted descending by
        rrf_score — the first chunk seen for each (article, doc) pair is the
        winner.

        Khoản-split chunks ("Điều 20 Khoản 1", "Điều 20 Khoản 2") have
        distinct article_number strings and are NOT collapsed — only plain
        numeric/string duplicates ("13", "13", "13") are collapsed.
        """
        seen: set[tuple[str, str]] = set()
        deduplicated: list[DocumentChunk] = []

        for chunk in chunks:
            key = (
                chunk.article_number or "",
                chunk.document_number or "",
            )
            if key not in seen:
                seen.add(key)
                deduplicated.append(chunk)

        return deduplicated

    def _build_filter(
        self,
        procedure_id: str | None,
        scope: str | None = None,
    ) -> Filter:
        """Build a Qdrant Filter combining status=active with optional filters.

        Args:
            procedure_id: When set, adds a procedure_tags filter.
            scope:        When set, adds an exact-match filter on payload["scope"].
        """
        conditions: list[FieldCondition] = [
            FieldCondition(key="status", match=MatchValue(value="active"))
        ]
        if procedure_id is not None:
            conditions.append(
                FieldCondition(
                    key="procedure_tags",
                    match=MatchAny(any=[procedure_id]),
                )
            )
        if scope is not None:
            conditions.append(
                FieldCondition(
                    key="location_scope",
                    match=MatchValue(value=scope),
                )
            )
        return Filter(must=conditions)
