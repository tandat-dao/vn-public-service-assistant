"""Chat API route — functional streaming SSE endpoint.

POST /api/v1/chat

Runs the LangGraph agent pipeline, streams final_response word-by-word,
and saves the updated session to Redis.

Architecture rules (CLAUDE.md §2, §4):
  - This handler is thin: validate input → invoke agent → stream response.
  - No business logic, no direct DB queries, no LLM calls in this file.
  - agent_graph is compiled once at module level in graph.py, not here.
  - GraphRecursionError is caught here and returned as HTTP 500 JSON.
  - Redis save failure must never fail the user request.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import agent_graph
from app.config import settings
from app.dependencies import get_db
from app.rate_limit import limiter
from app.schemas.chat import ChatRequest
from app.schemas.session import SessionData
from app.services.redis_service import RedisService

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Lazy Redis singleton — avoids connecting at import time.
# Replace in tests: patch("app.api.v1.chat._get_redis", return_value=mock)
# ---------------------------------------------------------------------------

_redis_svc: RedisService | None = None


def _get_redis() -> RedisService:
    global _redis_svc
    if _redis_svc is None:
        _redis_svc = RedisService()
    return _redis_svc


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("")
@limiter.limit(settings.CHAT_RATE_LIMIT)
async def chat(
    request: Request,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Stream the agent response as Server-Sent Events.

    SSE format per chunk:   data: {"content": "<word> "}\n\n
    Metadata event:         data: {"metadata": {...}}\n\n
    Termination signal:     data: [DONE]\n\n
    """
    # ---- Step 1: Load session from Redis ----
    redis = _get_redis()
    session: SessionData | None = None
    try:
        session = await redis.get_session(body.session_id)
    except Exception as exc:
        logger.warning("chat: Redis session load failed — starting fresh: %s", exc)

    if session is None:
        session = SessionData(session_id=body.session_id)

    # ---- Carry-forward: load citizen PersonalData when session has none ----
    # If the client provides a citizen_id and this session has no extracted
    # personal data yet, try to load previously saved PersonalData from the
    # citizen key (24-hour TTL, cross-session). This lets citizens skip
    # re-uploading their CCCD on a new session if they uploaded before.
    if body.citizen_id and session.extracted_personal_data is None:
        try:
            citizen_pd = await redis.get_citizen_personal_data(body.citizen_id)
            if citizen_pd is not None:
                session = session.model_copy(update={"extracted_personal_data": citizen_pd})
        except Exception as exc:
            logger.warning("chat: citizen personal data load failed: %s", exc)

    # ---- Step 2: Build initial AgentState ----
    # Conversation history is trimmed to 6 turns at save time by RedisService,
    # but slice here as a defensive guard (CLAUDE.md Rule §4).
    capped_history = (session.conversation_history or [])[-6:]

    # Guided mode State 1 → State 2 auto-advance:
    # If we were waiting for a CCCD upload (State 1) and the upload has now
    # happened (uploaded_document_path set in session), advance to FORM_FILLING.
    # This must happen BEFORE building initial_state so the correct guided_step
    # is hydrated into the graph from the start of this turn.
    # NOTE: guided mode state is lost on page navigation until TASK-APP-20
    # (sessionStorage persistence) is implemented.
    if (
        session.guided_procedure_id is not None
        and session.guided_step == 1
        and session.uploaded_document_path is not None
    ):
        session = session.model_copy(update={"guided_step": 2})

    initial_state: dict = {
        # Required
        "user_message": body.message,
        "session_id": body.session_id,
        "iteration_count": 0,
        # From session
        "conversation_history": capped_history,
        "filing_jurisdiction": session.filing_jurisdiction,
        "domain": session.domain,
        "personal_data": session.personal_data,
        "completed_procedures": list(session.completed_procedure_ids),
        # Upload (optional) — prefer explicit path from request body;
        # fall back to the last uploaded document stored in the session so
        # ocr_fn can process a document uploaded via /documents/upload in a
        # prior HTTP request without the client re-sending the file.
        "uploaded_image_path": body.image_path or session.uploaded_document_path,
        # Guided procedure wizard — hydrated from session (TASK-APP-18)
        "guided_procedure_id": session.guided_procedure_id,
        "guided_step": session.guided_step,
        # Routing defaults
        "execution_plan": [],
        "plan_cursor": 0,
        "entities": {},
        # Worker output defaults
        "retrieved_chunks": [],
        "citations": [],
        "extracted_personal_data": None,
        "document_type": None,
        "target_procedure_id": None,
        "procedure_execution_plan": [],
        "scope_used": None,
        "form_id": None,
        "filled_fields": {},
        "unfilled_required_fields": [],
        "filled_form_path": None,
        "form_fill_complete": False,
        # Output defaults
        "final_response": "",
        "response_metadata": {},
        # Control defaults
        "errors": [],
    }

    # ---- Step 3: Run the graph ----
    try:
        result: dict = await agent_graph.ainvoke(
            initial_state,
            config={"recursion_limit": 10},
        )
    except Exception as exc:
        # Import here to avoid circular imports at module level.
        try:
            from langgraph.errors import GraphRecursionError
        except ImportError:
            GraphRecursionError = RecursionError  # type: ignore[misc,assignment]

        if isinstance(exc, GraphRecursionError):
            logger.error("chat: GraphRecursionError for session=%s", body.session_id)
            return JSONResponse(
                status_code=500,
                content={"error": "Yêu cầu quá phức tạp để xử lý. Vui lòng thử lại."},
            )
        raise

    # ---- Step 4: Extract final response ----
    final_response: str = result.get("final_response") or "Xin lỗi, đã có lỗi xảy ra."
    response_metadata: dict = result.get("response_metadata") or {}

    # ---- Step 5: Update and save session ----
    updated_history = capped_history + [
        {"role": "user", "content": body.message},
        {"role": "assistant", "content": final_response},
    ]
    # Write back guided mode state from the final graph result so the next
    # turn starts with the correct wizard step.  synthesizer_node writes the
    # updated guided_step into both response_metadata AND the result dict —
    # read from result dict for session persistence.
    session_updates: dict = {
        "conversation_history": updated_history,
        "guided_procedure_id": result.get("guided_procedure_id"),
        "guided_step": result.get("guided_step"),
    }
    updated_session = session.model_copy(update=session_updates)
    try:
        await redis.save_session(body.session_id, updated_session)
    except Exception as exc:
        # Redis save failure must not fail the user request — log and continue.
        logger.warning(
            "chat: Redis session save failed — response will still be returned: %s", exc
        )

    # ---- Step 6 + 7: Stream SSE response ----
    async def generate():
        # Split into 3-char Unicode code-point groups.
        # Python str slicing is by code point, not byte — Vietnamese diacritics
        # (e.g. ữ = U+1EEF) are single code points and will not be split mid-character.
        # Last group may be 1–2 chars if len(final_response) is not divisible by 3.
        chunks = [final_response[i:i+3] for i in range(0, len(final_response), 3)]
        for chunk in chunks:
            yield f"data: {json.dumps({'content': chunk})}\n\n"
            await asyncio.sleep(0.008)
        # Send metadata before [DONE]
        yield f"data: {json.dumps({'metadata': response_metadata})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
