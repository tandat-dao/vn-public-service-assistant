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

from app.agents.prompts.rag_prompt import RAG_SYSTEM_PROMPT, build_rag_user_message
from app.agents.state import AgentState
from app.core.citation_formatter import verify_citations
from app.core.jurisdiction import expand_scope_hierarchy
from app.core.text_utils import strip_markdown
from app.schemas.chat import Citation
from app.schemas.rag import DocumentChunk

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Query augmentation for short follow-up messages
# ---------------------------------------------------------------------------

_AUGMENT_WORD_THRESHOLD = 10   # queries at or above this word count get no augmentation
_AUGMENT_MAX_CHARS = 500       # context chars prepended for a 0-word query
_AUGMENT_MIN_CHARS = 50        # context chars prepended for a 9-word query (just below threshold)


def _build_search_query(state: AgentState) -> str:
    """Build the Qdrant search query, augmenting short queries with prior context.

    Short queries (< _AUGMENT_WORD_THRESHOLD words) are prepended with a
    truncated excerpt of the last assistant response. The amount of context
    scales linearly with query length: shorter queries get more context
    (up to _AUGMENT_MAX_CHARS), longer queries get less (down to
    _AUGMENT_MIN_CHARS), queries at or above the threshold get none.

    This augmentation targets the Qdrant search query only — the raw
    user_message is always passed unchanged to the LLM generation call.
    """
    user_msg: str = state["user_message"]
    word_count = len(user_msg.split())

    if word_count >= _AUGMENT_WORD_THRESHOLD:
        return user_msg

    history: list[dict] = state.get("conversation_history") or []
    last_assistant: str | None = None
    for turn in reversed(history):
        if turn.get("role") == "assistant":
            last_assistant = turn.get("content", "")
            break

    if not last_assistant:
        return user_msg

    ratio = word_count / _AUGMENT_WORD_THRESHOLD
    context_chars = int(
        _AUGMENT_MAX_CHARS * (1 - ratio) + _AUGMENT_MIN_CHARS * ratio
    )
    context = last_assistant[:context_chars]
    return f"{context} {user_msg}"


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

    # Build augmented query for Qdrant retrieval. Short follow-up messages
    # get context prepended from the last assistant turn. The LLM generation
    # step (Step 4) always uses user_message directly — not the augmented query.
    search_query: str = _build_search_query(state)

    # ---- Step 1: Build scope list, most-specific first ----
    # expand_scope_hierarchy returns most-general first (e.g. ["VN", "VN-HCM", "VN-HCM-070"])
    # Reverse so cascade attempts the narrowest jurisdiction first.
    if filing_jurisdiction is not None:
        scope_list = list(reversed(expand_scope_hierarchy(filing_jurisdiction)))
    else:
        scope_list = ["VN"]

    # Prepend city-level scope when the router LLM detected a city in the query.
    # The router classifies city scope as part of its existing LLM call — zero
    # extra tokens. Handles all Vietnamese name variants and diacritics naturally.
    router_location_scope = state.get("location_scope")
    if router_location_scope and router_location_scope not in scope_list:
        scope_list = [router_location_scope] + scope_list

    # ---- Step 2: Jurisdiction cascade retrieval ----
    raw_chunks: list[DocumentChunk] = []
    scope_used: str | None = None

    try:
        for scope in scope_list:
            chunks = await qdrant.search(
                query=search_query,
                procedure_id=target_procedure_id,
                scope=scope,
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
            "rag_returned_empty": True,
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

    # If all chunks were below threshold, return without calling LLM.
    # Must set rag_returned_empty=True so synthesizer uses the rag_empty mode
    # (not fallback) — prevents the fallback LLM from hallucinating constraints.
    if not final_chunks:
        error_msg = (
            "Không tìm thấy văn bản pháp lý phù hợp cho thủ tục và địa bàn này."
        )
        return {
            "retrieved_chunks": [],
            "citations": [],
            "scope_used": None,
            "rag_returned_empty": True,
            "errors": list(state.get("errors") or []) + [error_msg],
        }

    # ---- Step 4: Build LLM context and call ----
    context_parts = [
        f"[{chunk.article_number}, {chunk.document_number}]\n{text}"
        for chunk, text in budget_chunks_with_text
    ]
    context = "\n\n---\n\n".join(context_parts)

    user_prompt = build_rag_user_message(context, user_message)

    llm_response: str = await llm.async_invoke(
        system=RAG_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=1024,
    )

    # ---- Step 5: verify_citations + strip markdown ----
    verified_response = strip_markdown(verify_citations(llm_response, final_chunks))

    # ---- Step 6: Confidence scoring ----
    # RRF scores top out at ~0.033 (1/(1+60) from each of dense + BM25).
    # Thresholds are calibrated to that range, not to cosine similarity [0,1].
    top_score = final_chunks[0].rrf_score
    if top_score > 0.025 and len(final_chunks) >= 3:
        confidence = "high"
    elif top_score > 0.016:
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
