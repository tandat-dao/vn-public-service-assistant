"""Chat API route — functional streaming SSE endpoint with pipeline event emission.

POST /api/v1/chat

Runs the LangGraph agent pipeline, emits pipeline_event SSE lines for each
node as it completes (TASK-SHOWCASE), then streams the final_response word-
by-word and saves the updated session to Redis.

SSE event types emitted:
    event: pipeline_event    — agent activity events (plan_decided, worker_complete, …)
    (no event field)         — text chunks   {"content": "..."}  (backward compat)
    (no event field)         — metadata      {"metadata": {...}} (backward compat)
    (no event field)         — terminator    [DONE]              (backward compat)

Architecture rules (CLAUDE.md §2, §4):
  - This handler is thin: validate input → invoke agent → stream response.
  - No business logic, no direct DB queries, no LLM calls in this file.
  - agent_graph is compiled once at module level in graph.py, not here.
  - GraphRecursionError is caught here and returned as HTTP 500 JSON.
  - Redis save failure must never fail the user request.

Hard constraints (TASK-SHOWCASE):
  - Pipeline events are emitted as they arrive — NOT buffered and emitted at end.
  - Text stream begins immediately after the graph completes — never blocked.
  - PII (raw PersonalData fields) must never appear in pipeline event payloads.
  - Both SSE connections (text + pipeline) share the same SSE stream.
"""

import asyncio
import json
import logging
import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import agent_graph
from app.agents.nodes.plan_executor import _compute_wave
from app.agents.node_registry import NODE_DEPENDENCIES
from app.config import settings
from app.dependencies import get_db
from app.rate_limit import limiter
from app.schemas.chat import ChatRequest
from app.schemas.pipeline_events import (
    ENRICHMENT_RESULT,
    FORM_RESULT,
    OCR_RESULT,
    PARALLEL_WAVE_START,
    PIPELINE_COMPLETE,
    PIPELINE_START,
    PLAN_DECIDED,
    RAG_RESULT,
    WORKER_COMPLETE,
    WORKER_START,
)
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
# Pipeline event helpers — safe payload builders
# ---------------------------------------------------------------------------

def _sse_pipeline(payload: dict) -> str:
    """Format a pipeline event as an SSE message with explicit event type."""
    return f"event: pipeline_event\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _sse_data(payload: dict) -> str:
    """Format a data-only SSE line (backward-compat text/metadata events)."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _count_pd_fields(personal_data: dict | None) -> int:
    """Count non-None fields in a PersonalData-shaped dict. Never exposes values."""
    if not personal_data or not isinstance(personal_data, dict):
        return 0
    # Field names from PersonalData schema that carry citizen data
    _DATA_FIELDS = {
        "full_name", "full_name_latin", "date_of_birth", "gender",
        "nationality", "id_number", "id_issue_date", "id_issue_place",
        "permanent_address", "temporary_address",
    }
    return sum(1 for k, v in personal_data.items() if k in _DATA_FIELDS and v is not None)


def _pd_confidence(personal_data: dict | None) -> float:
    """Extract overall extraction_confidence from PersonalData dict."""
    if not personal_data or not isinstance(personal_data, dict):
        return 0.0
    return float(personal_data.get("extraction_confidence", 0.0))


def _get_top_article(retrieved_chunks: list) -> str | None:
    """Return the top-ranked chunk's article+document identifier (no content)."""
    if not retrieved_chunks:
        return None
    chunk = retrieved_chunks[0]
    if isinstance(chunk, dict):
        article = chunk.get("article_number", "")
        doc = chunk.get("document_number", "")
    else:
        article = getattr(chunk, "article_number", "")
        doc = getattr(chunk, "document_number", "")
    if article and doc:
        return f"Điều {article}, {doc}" if not str(article).startswith("Điều") else f"{article}, {doc}"
    return None


# ---------------------------------------------------------------------------
# Known graph node names (as registered in graph.py)
# ---------------------------------------------------------------------------

_GRAPH_NODE_NAMES = frozenset({
    "router_node",
    "enrichment_node",
    "plan_executor_node",
    "synthesizer_node",
})


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

    Pipeline events:    event: pipeline_event\\ndata: {"type": "..."}\\n\\n
    Text chunk:         data: {"content": "<word> "}\\n\\n
    Metadata event:     data: {"metadata": {...}}\\n\\n
    Termination signal: data: [DONE]\\n\\n
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
    if body.citizen_id and session.extracted_personal_data is None:
        try:
            citizen_pd = await redis.get_citizen_personal_data(body.citizen_id)
            if citizen_pd is not None:
                session = session.model_copy(update={"extracted_personal_data": citizen_pd})
        except Exception as exc:
            logger.warning("chat: citizen personal data load failed: %s", exc)

    # ---- Step 2: Build initial AgentState ----
    capped_history = (session.conversation_history or [])[-6:]

    # Guided mode State 1 → State 2 auto-advance
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
        "uploaded_image_path": body.image_path or session.uploaded_document_path,
        # Guided procedure wizard
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

    # ---- Step 3+4+5: Run graph, accumulate state, stream events ----
    async def generate():  # noqa: C901 (complexity acceptable for SSE generator)
        nonlocal session

        # Accumulate state from all node outputs.
        # Start with a copy of initial_state so we can read execution_plan etc.
        accumulated: dict = dict(initial_state)

        pipeline_start_time = time.monotonic()

        # Per-wave tracking: cursor before the wave started
        pre_wave_cursor: int = 0
        # Wall-clock time when the current plan_executor_node wave began
        wave_start_time: float = pipeline_start_time

        # Whether the graph produced a valid response (guards session save)
        graph_completed = False

        try:
            from langgraph.errors import GraphRecursionError
        except ImportError:
            GraphRecursionError = RecursionError  # type: ignore[misc,assignment]

        try:
            async for event in agent_graph.astream_events(
                initial_state,
                config={"recursion_limit": 10},
                version="v2",
            ):
                event_type: str = event.get("event", "")
                event_name: str = event.get("name", "")
                event_data: dict = event.get("data") or {}

                # ── Only process events from known graph nodes ──────────────
                if event_name not in _GRAPH_NODE_NAMES:
                    continue

                # ── router_node ─────────────────────────────────────────────

                if event_type == "on_chain_start" and event_name == "router_node":
                    yield _sse_pipeline({"type": PIPELINE_START})

                elif event_type == "on_chain_end" and event_name == "router_node":
                    output: dict = event_data.get("output") or {}
                    if isinstance(output, dict):
                        accumulated.update(output)
                    plan = accumulated.get("execution_plan") or []
                    yield _sse_pipeline({
                        "type": PLAN_DECIDED,
                        "execution_plan": plan,
                        "domain": accumulated.get("domain"),
                        "location_scope": accumulated.get("location_scope"),
                        "procedure_id": accumulated.get("target_procedure_id"),
                    })

                # ── enrichment_node ─────────────────────────────────────────

                elif event_type == "on_chain_end" and event_name == "enrichment_node":
                    output = event_data.get("output") or {}
                    if isinstance(output, dict):
                        accumulated.update(output)
                    proc_plan = accumulated.get("procedure_execution_plan") or []
                    if proc_plan:
                        yield _sse_pipeline({
                            "type": ENRICHMENT_RESULT,
                            "step_count": len(proc_plan),
                        })

                # ── plan_executor_node ──────────────────────────────────────

                elif event_type == "on_chain_start" and event_name == "plan_executor_node":
                    # Read the cursor from the node's input (full state snapshot)
                    node_input: dict = event_data.get("input") or {}
                    if isinstance(node_input, dict):
                        pre_wave_cursor = int(node_input.get("plan_cursor") or 0)
                    else:
                        pre_wave_cursor = accumulated.get("plan_cursor", 0)
                    wave_start_time = time.monotonic()

                    # Compute the wave that is about to run
                    plan = accumulated.get("execution_plan") or []
                    wave = _compute_wave(plan, pre_wave_cursor, NODE_DEPENDENCIES)

                    if wave:
                        if len(wave) > 1:
                            yield _sse_pipeline({
                                "type": PARALLEL_WAVE_START,
                                "workers": wave,
                                "wave_index": pre_wave_cursor,
                            })
                        for worker in wave:
                            yield _sse_pipeline({
                                "type": WORKER_START,
                                "worker": worker,
                            })

                elif event_type == "on_chain_end" and event_name == "plan_executor_node":
                    output = event_data.get("output") or {}
                    if isinstance(output, dict):
                        accumulated.update(output)

                    new_cursor = accumulated.get("plan_cursor", pre_wave_cursor)
                    plan = accumulated.get("execution_plan") or []
                    wave = plan[pre_wave_cursor:new_cursor]
                    duration_ms = int((time.monotonic() - wave_start_time) * 1000)

                    for worker in wave:
                        yield _sse_pipeline({
                            "type": WORKER_COMPLETE,
                            "worker": worker,
                            "duration_ms": duration_ms,
                        })

                    # ── Detailed result events per worker type ──────────────

                    if "rag_fn" in wave:
                        chunks = accumulated.get("retrieved_chunks") or []
                        rag_meta = accumulated.get("response_metadata") or {}
                        if chunks:
                            yield _sse_pipeline({
                                "type": RAG_RESULT,
                                "chunk_count": len(chunks),
                                "scope_used": accumulated.get("scope_used") or "VN",
                                "confidence_tier": rag_meta.get("rag_confidence", "low"),
                                "top_article": _get_top_article(chunks),
                            })

                    if "ocr_fn" in wave:
                        # Use extracted_personal_data (most recent OCR result, not merged)
                        pd_raw = output.get("personal_data") if isinstance(output, dict) else None
                        if pd_raw is None:
                            pd_raw = accumulated.get("personal_data")
                        # Convert Pydantic model to dict for field counting
                        pd_dict = (
                            pd_raw.model_dump() if hasattr(pd_raw, "model_dump")
                            else (pd_raw if isinstance(pd_raw, dict) else None)
                        )
                        doc_type = accumulated.get("document_type") or "unknown"
                        yield _sse_pipeline({
                            "type": OCR_RESULT,
                            "document_type": doc_type,
                            "field_count": _count_pd_fields(pd_dict),
                            "confidence": _pd_confidence(pd_dict),
                        })

                    if "form_filler_fn" in wave:
                        filled = accumulated.get("filled_fields") or {}
                        unfilled = accumulated.get("unfilled_required_fields") or []
                        yield _sse_pipeline({
                            "type": FORM_RESULT,
                            "filled_count": len(filled),
                            "unfilled_required": list(unfilled),
                        })

                # ── synthesizer_node ────────────────────────────────────────

                elif event_type == "on_chain_end" and event_name == "synthesizer_node":
                    output = event_data.get("output") or {}
                    if isinstance(output, dict):
                        accumulated.update(output)
                    graph_completed = True
                    total_ms = int((time.monotonic() - pipeline_start_time) * 1000)
                    synth_meta = accumulated.get("response_metadata") or {}
                    yield _sse_pipeline({
                        "type": PIPELINE_COMPLETE,
                        "total_ms": total_ms,
                        "synthesizer_mode": synth_meta.get("mode", "unknown"),
                    })

        except GraphRecursionError:
            logger.error("chat: GraphRecursionError for session=%s", body.session_id)
            yield _sse_data({"content": "Yêu cầu quá phức tạp để xử lý. Vui lòng thử lại."})
            yield "data: [DONE]\n\n"
            return

        except Exception as exc:
            logger.error("chat: astream_events error: %s", exc, exc_info=True)
            yield _sse_data({"content": "Xin lỗi, đã có lỗi xảy ra."})
            yield _sse_data({"metadata": {"mode": "error"}})
            yield "data: [DONE]\n\n"
            return

        # ---- Step 4: Extract final response and metadata ----
        final_response: str = accumulated.get("final_response") or "Xin lỗi, đã có lỗi xảy ra."
        response_metadata: dict = accumulated.get("response_metadata") or {}

        # ---- Step 5: Save session ----
        updated_history = capped_history + [
            {"role": "user", "content": body.message},
            {"role": "assistant", "content": final_response},
        ]
        session_updates: dict = {
            "conversation_history": updated_history,
            "guided_procedure_id": accumulated.get("guided_procedure_id"),
            "guided_step": accumulated.get("guided_step"),
        }
        updated_session = session.model_copy(update=session_updates)
        try:
            await redis.save_session(body.session_id, updated_session)
        except Exception as exc:
            logger.warning(
                "chat: Redis session save failed — response will still be returned: %s", exc
            )

        # ---- Step 6: Stream text response (backward-compat data: format) ----
        chunks = [final_response[i:i+3] for i in range(0, len(final_response), 3)]
        for chunk in chunks:
            yield _sse_data({"content": chunk})
            await asyncio.sleep(0.008)

        # Send metadata before [DONE]
        yield _sse_data({"metadata": response_metadata})
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# POST /classify — router-only classification, zero downstream LLM calls.
# Used by the benchmark --metric router to measure intent accuracy without
# triggering RAG generation (saves API cost + ~10× faster per case).
# ---------------------------------------------------------------------------

class _ClassifyRequest(BaseModel):
    message: str
    session_id: str | None = None


def _derive_mode(result: dict) -> str:
    """Map router_node output to the synthesizer mode the full pipeline would produce."""
    if result.get("out_of_scope"):
        return "out_of_scope"
    if result.get("guided_procedure_id") is not None:
        return "guided_step"
    plan = result.get("execution_plan") or []
    if not plan:
        return "fallback"
    if "rag_fn" in plan or "ocr_fn" in plan:
        return "rag_only"
    return "fallback"


@router.post("/classify")
async def classify_intent(body: _ClassifyRequest):
    """Run router_node only — returns intent, domain, procedure_id, location_scope, mode.

    No plan execution, no RAG, no generation LLM call. For benchmark use only.
    """
    from app.agents.nodes.router import router_node

    state: dict = {
        "user_message": body.message,
        "session_id": body.session_id or "benchmark",
        "iteration_count": 0,
        "uploaded_image_path": None,
        "guided_procedure_id": None,
        "guided_step": None,
        "conversation_history": [],
        "entities": {},
        "errors": [],
    }

    result = await router_node(state)

    return {
        "intent": result.get("intent"),
        "execution_plan": result.get("execution_plan", []),
        "domain": result.get("domain"),
        "procedure_id": result.get("procedure_id") or result.get("target_procedure_id"),
        "location_scope": result.get("location_scope"),
        "mode": _derive_mode(result),
    }
