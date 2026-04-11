"""RAG worker function — hybrid retrieval + cited LLM generation + citation verification.

This is a plain async function called by plan_executor via NODE_REGISTRY["rag_fn"].
It is NOT a LangGraph graph node and must NOT import from graph.py.

Pipeline
--------
  1. Build scope list from filing_jurisdiction (most-specific → broadest).
  2. Cascade: try each scope in order, stop at first scope that returns chunks.
  3. Token-budget enforcement + threshold-based stopping (RAG_MIN_SCORE_THRESHOLD).
  4. LLM cited generation using RAG_SYSTEM_PROMPT.
  5. verify_citations() — flag unverified citations in the response.
  6. Confidence scoring from top RRF score.
"""

from __future__ import annotations

import logging

from app.agents.prompts.rag_prompt import RAG_SYSTEM_PROMPT
from app.agents.state import AgentState
from app.core.citation_formatter import verify_citations
from app.core.jurisdiction import expand_scope_hierarchy
from app.schemas.chat import Citation
from app.schemas.rag import DocumentChunk

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy singletons — created on first call.
# Replace in tests: patch("app.agents.nodes.rag._get_qdrant", return_value=mock)
# ---------------------------------------------------------------------------

_qdrant_svc = None
_llm_svc = None


def _get_qdrant():
    global _qdrant_svc
    if _qdrant_svc is None:
        from app.services.qdrant_service import QdrantService
        _qdrant_svc = QdrantService()
    return _qdrant_svc


def _get_llm():
    global _llm_svc
    if _llm_svc is None:
        from app.services.llm import LLMService
        _llm_svc = LLMService()
    return _llm_svc


def _min_score_threshold() -> float:
    from app.config import settings
    return settings.RAG_MIN_SCORE_THRESHOLD


# ---------------------------------------------------------------------------
# Worker function
# ---------------------------------------------------------------------------

async def rag_fn(state: AgentState) -> dict:
    """Hybrid retrieval from Qdrant + cited LLM generation + verify_citations.

    Reads:
        state["user_message"]
        state["target_procedure_id"]  (may be None)
        state["filing_jurisdiction"]  (may be None — never read from raw OCR)
        state["entities"]

    Returns partial AgentState dict with keys:
        retrieved_chunks, citations, final_response, scope_used, response_metadata

    Never raises — exceptions are caught and appended to state["errors"].
    """
    qdrant = _get_qdrant()
    llm = _get_llm()

    user_message: str = state["user_message"]
    target_procedure_id: str | None = state.get("target_procedure_id")
    filing_jurisdiction: str | None = state.get("filing_jurisdiction")

    # ---- Step 1: Build scope list, most-specific first ----
    # expand_scope_hierarchy returns most-general first (e.g. ["VN", "VN-HCM", "VN-HCM-070"])
    # Reverse so cascade attempts the narrowest jurisdiction first.
    if filing_jurisdiction is not None:
        scope_list = list(reversed(expand_scope_hierarchy(filing_jurisdiction)))
    else:
        scope_list = ["VN"]

    # ---- Step 2: Jurisdiction cascade retrieval ----
    raw_chunks: list[DocumentChunk] = []
    scope_used: str | None = None

    try:
        for scope in scope_list:
            chunks = await qdrant.search(
                query=user_message,
                procedure_id=target_procedure_id,
                scope=scope,
                top_k=8,
            )
            if chunks:
                raw_chunks = chunks
                scope_used = scope
                break
    except Exception as exc:
        error_msg = f"Lỗi khi truy xuất văn bản pháp lý: {exc}"
        logger.error("rag_fn Qdrant exception: %s", exc, exc_info=True)
        return {
            "retrieved_chunks": [],
            "citations": [],
            "scope_used": None,
            "errors": list(state.get("errors") or []) + [error_msg],
        }

    # All scopes returned zero chunks — do NOT call LLM
    if not raw_chunks:
        error_msg = (
            "Không tìm thấy văn bản pháp lý phù hợp cho thủ tục và địa bàn này."
        )
        return {
            "retrieved_chunks": [],
            "citations": [],
            "scope_used": None,
            "errors": list(state.get("errors") or []) + [error_msg],
        }

    # ---- Step 3: Token budget enforcement + threshold-based stopping ----
    max_tokens: int = 6000
    threshold: float = _min_score_threshold()

    # Sort descending by RRF score (QdrantService already sorts, but re-sort
    # here as a defensive measure since budget filtering may reorder).
    sorted_chunks = sorted(raw_chunks, key=lambda c: c.rrf_score, reverse=True)

    # Accumulate chunks; track which text was decided for each chunk.
    budget_chunks_with_text: list[tuple[DocumentChunk, str]] = []
    used_tokens: float = 0.0

    for chunk in sorted_chunks:
        # Threshold-based stopping — drop all chunks below the threshold
        if chunk.rrf_score < threshold:
            break

        # Structured summary fallback: once we have used > 80% of the budget,
        # use the pre-generated summary instead of full content.
        if used_tokens > max_tokens * 0.8:
            text = chunk.structured_summary
            if not text:
                # No summary available — skip this chunk in high-budget regime
                continue
        else:
            text = chunk.content

        chunk_tokens: float = len(text.split()) * 1.3
        if used_tokens + chunk_tokens > max_tokens:
            break

        used_tokens += chunk_tokens
        budget_chunks_with_text.append((chunk, text))

    final_chunks = [c for c, _ in budget_chunks_with_text]

    # If all chunks were below threshold, return without calling LLM
    if not final_chunks:
        error_msg = (
            "Không tìm thấy văn bản pháp lý phù hợp cho thủ tục và địa bàn này."
        )
        return {
            "retrieved_chunks": [],
            "citations": [],
            "scope_used": None,
            "errors": list(state.get("errors") or []) + [error_msg],
        }

    # ---- Step 4: Build LLM context and call ----
    context_parts = [
        f"[{chunk.article_number}, {chunk.document_number}]\n{text}"
        for chunk, text in budget_chunks_with_text
    ]
    context = "\n\n---\n\n".join(context_parts)

    user_prompt = (
        f"Câu hỏi: {user_message}\n\n"
        f"Văn bản pháp lý được truy xuất:\n\n{context}"
    )

    llm_response: str = await llm.async_invoke(
        system=RAG_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=1024,
    )

    # ---- Step 5: verify_citations ----
    verified_response = verify_citations(llm_response, final_chunks)

    # ---- Step 6: Confidence scoring ----
    top_score = final_chunks[0].rrf_score
    if top_score > 0.85 and len(final_chunks) >= 3:
        confidence = "high"
    elif top_score > 0.65:
        confidence = "medium"
    else:
        confidence = "low"

    # Build structured Citation objects
    citations = [
        Citation(
            doc_id=chunk.legal_document_id,
            document_number=chunk.document_number,
            article=chunk.article_number,
            excerpt=chunk.content[:200],
        )
        for chunk in final_chunks
    ]

    logger.debug(
        "rag_fn: scope=%s chunks=%d confidence=%s tokens=%.0f",
        scope_used,
        len(final_chunks),
        confidence,
        used_tokens,
    )

    return {
        "retrieved_chunks": final_chunks,
        "citations": citations,
        "final_response": verified_response,
        "scope_used": scope_used,
        "response_metadata": {
            "rag_confidence": confidence,
        },
    }
