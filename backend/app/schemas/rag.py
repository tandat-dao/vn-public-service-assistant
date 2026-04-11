"""RAG-related Pydantic schemas — service output types for the vector search pipeline."""

from pydantic import BaseModel


class DocumentChunk(BaseModel):
    """A single retrieved chunk from Qdrant.

    This is the Pydantic service-output model used by QdrantService.search().
    It is distinct from the DocumentChunk TypedDict in app.agents.state, which
    represents the same data inside the LangGraph AgentState. Both co-exist and
    must not be merged.
    """

    point_id: str
    legal_document_id: str
    document_number: str
    article_number: str
    content: str
    procedure_tags: list[str]
    status: str
    rrf_score: float = 0.0
    structured_summary: str | None = None
