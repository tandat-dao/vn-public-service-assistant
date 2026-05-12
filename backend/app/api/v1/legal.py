"""Legal documents API routes."""

from fastapi import APIRouter, Query

from app.config import settings

router = APIRouter()

# Lazy singleton — same pattern as rag.py to share the embedder instance.
_qdrant_svc = None


def _get_qdrant():
    global _qdrant_svc
    if _qdrant_svc is None:
        from app.services.qdrant_service import QdrantService
        _qdrant_svc = QdrantService()
    return _qdrant_svc


@router.get("/search")
async def search_legal(
    q: str = Query(..., description="Search query"),
    procedure_id: str | None = Query(None, description="Filter by procedure tag"),
    top_k: int = Query(default=settings.RAG_TOP_K, ge=1, le=50),
) -> list[dict]:
    """Hybrid dense+BM25 search over active legal document chunks.

    Zero LLM calls — pure Qdrant retrieval. Used by the citation recall
    benchmark to measure retrieval quality without burning API tokens.

    Returns article_number, document_number, and rrf_score per chunk.
    Content is intentionally omitted to keep response size small.
    """
    qdrant = _get_qdrant()
    chunks = await qdrant.search(q, procedure_id=procedure_id, top_k=top_k)
    return [
        {
            "article_number": c.article_number,
            "document_number": c.document_number,
            "score": round(c.rrf_score, 6),
        }
        for c in chunks
    ]


@router.get("/documents")
async def list_legal_documents() -> list[dict]:
    """List ingested legal documents."""
    raise NotImplementedError


@router.get("/documents/{doc_id}")
async def get_legal_document(doc_id: str) -> dict:
    """Get a single legal document by ID."""
    raise NotImplementedError
