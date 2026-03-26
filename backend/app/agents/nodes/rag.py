"""RAG worker function — retrieves relevant legal document chunks from Qdrant."""

from app.agents.state import AgentState


def rag_fn(state: AgentState) -> dict:
    """Search Qdrant with hybrid retrieval and populate retrieved_chunks and citations."""
    raise NotImplementedError
