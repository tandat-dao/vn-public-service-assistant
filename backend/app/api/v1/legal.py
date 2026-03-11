"""Legal documents API routes."""

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/search")
async def search_legal(
    q: str = Query(..., description="Search query"),
    procedure_id: str | None = Query(None),
) -> list[dict]:
    """Hybrid search over legal document chunks."""
    raise NotImplementedError


@router.get("/documents")
async def list_legal_documents() -> list[dict]:
    """List ingested legal documents."""
    raise NotImplementedError


@router.get("/documents/{doc_id}")
async def get_legal_document(doc_id: str) -> dict:
    """Get a single legal document by ID."""
    raise NotImplementedError
