"""Synthesizer node — final response assembly from accumulated AgentState.

This is a TRUE LangGraph graph node, always the last node before END.
It is NOT a worker function and NOT in NODE_REGISTRY.

Six response modes (evaluated in priority order):
  1. error              — state["errors"] is non-empty
  2. circuit_breaker    — plan stalled (plan_cursor >= MAX_PLAN_STEPS), no errors
  3. form_fill_complete — state["form_fill_complete"] is True
  4. form_fill_partial  — state["unfilled_required_fields"] is non-empty
  5. rag_only           — state["retrieved_chunks"] is non-empty
  6. fallback           — none of the above

RAG-only optimisation: when no scope notice is needed (filing_jurisdiction ==
scope_used or either is None), the LLM call is skipped entirely and
state["final_response"] is returned directly. Only calls the LLM in RAG mode
when a scope notice must be woven into the output.

LLM failure handling: if the LLM call raises any exception, a hardcoded
Vietnamese fallback string is returned without re-raising. The node never
propagates exceptions.
"""

from __future__ import annotations

import logging

from app.agents.prompts.synthesis_prompt import _scope_level_name, build_synthesis_prompt
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

# Must match plan_executor.py — kept in sync manually.
MAX_PLAN_STEPS = 8

_HARDCODED_FALLBACK = (
    "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau."
)

# ---------------------------------------------------------------------------
# Lazy singleton — replace in tests via patch("app.agents.nodes.synthesizer._get_llm")
# ---------------------------------------------------------------------------

_llm_svc = None


def _get_llm():
    global _llm_svc
    if _llm_svc is None:
        from app.services.llm import LLMService
        _llm_svc = LLMService()
    return _llm_svc


# ---------------------------------------------------------------------------
# Mode determination
# ---------------------------------------------------------------------------

def _determine_mode(state: AgentState) -> str:
    """Return the response mode string based on accumulated state.

    Priority order — use the FIRST matching condition:
      1. "error"              — errors list is non-empty
      2. "circuit_breaker"   — plan_cursor >= MAX_PLAN_STEPS AND errors empty
      3. "form_fill_complete" — form_fill_complete is True
      4. "form_fill_partial"  — unfilled_required_fields is non-empty
      5. "rag_only"           — retrieved_chunks is non-empty
      6. "fallback"           — none of the above
    """
    errors = state.get("errors") or []
    if errors:
        return "error"

    plan_cursor = state.get("plan_cursor", 0)
    if plan_cursor >= MAX_PLAN_STEPS:
        return "circuit_breaker"

    if state.get("form_fill_complete", False):
        return "form_fill_complete"

    if state.get("unfilled_required_fields"):
        return "form_fill_partial"

    if state.get("retrieved_chunks"):
        return "rag_only"

    return "fallback"


# ---------------------------------------------------------------------------
# Scope fallback check
# ---------------------------------------------------------------------------

def _check_scope_fallback(state: AgentState) -> tuple[bool, str, str]:
    """Check whether a jurisdiction scope fallback occurred.

    A fallback occurred when:
      - scope_used is not None
      - filing_jurisdiction is not None
      - scope_used != filing_jurisdiction

    Returns:
        (include_scope_notice, scope_used_level_name, filing_jurisdiction_level_name)
        All three are empty/False when no fallback occurred.
    """
    scope_used: str | None = state.get("scope_used")
    filing_jurisdiction: str | None = state.get("filing_jurisdiction")

    if (
        scope_used is not None
        and filing_jurisdiction is not None
        and scope_used != filing_jurisdiction
    ):
        return (
            True,
            _scope_level_name(scope_used),
            _scope_level_name(filing_jurisdiction),
        )
    return False, "", ""


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------

def _build_context(
    mode: str,
    state: AgentState,
    include_scope_notice: bool,
    scope_used_level: str,
    filing_jurisdiction_level: str,
) -> dict:
    """Assemble the context dict for build_synthesis_prompt().

    Only includes what is relevant to the determined mode.
    Never dumps raw AgentState into the context.
    """
    ctx: dict = {
        "include_scope_notice": include_scope_notice,
        "scope_used_level": scope_used_level,
        "filing_jurisdiction_level": filing_jurisdiction_level,
        # Conversation history — already capped to 6 turns by RedisService
        "conversation_history": list(state.get("conversation_history") or []),
    }

    if mode == "error":
        ctx["errors"] = list(state.get("errors") or [])

    elif mode == "circuit_breaker":
        pass  # no additional context needed

    elif mode == "form_fill_complete":
        # Attempt to derive a human-readable procedure name from the plan
        proc_plan = state.get("procedure_execution_plan") or []
        procedure_name = "thủ tục đăng ký cư trú"
        if proc_plan:
            first_step = proc_plan[0]
            name_attr = getattr(first_step, "procedure_name", None)
            if name_attr:
                procedure_name = name_attr
            else:
                pid_attr = getattr(first_step, "procedure_id", None)
                if pid_attr:
                    procedure_name = str(pid_attr)
        ctx["procedure_name"] = procedure_name

    elif mode == "form_fill_partial":
        ctx["unfilled_required_fields"] = list(
            state.get("unfilled_required_fields") or []
        )
        ctx["filled_form_path"] = state.get("filled_form_path") or ""

    elif mode == "rag_only":
        ctx["final_response"] = state.get("final_response") or ""
        rag_meta = state.get("response_metadata") or {}
        ctx["rag_confidence"] = rag_meta.get("rag_confidence")

    elif mode == "fallback":
        ctx["user_message"] = state.get("user_message") or ""

    return ctx


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

async def synthesizer_node(state: AgentState) -> dict:
    """Assemble final_response from all accumulated AgentState fields.

    True LangGraph graph node — NOT a worker function, NOT in NODE_REGISTRY.

    Reads:
        Entire accumulated AgentState after all worker functions have run.

    Returns partial AgentState dict with ONLY:
        final_response:     str — complete user-facing message
        response_metadata:  dict — {mode, scope_used, scope_notice_included,
                                     rag_confidence}

    Never raises — all exceptions are caught and produce the hardcoded fallback.
    """
    mode = _determine_mode(state)

    include_scope_notice, scope_used_level, filing_jurisdiction_level = (
        _check_scope_fallback(state)
    )

    # Scope notice only applies to RAG-related modes (3, 4, 5)
    if mode not in ("form_fill_complete", "form_fill_partial", "rag_only"):
        include_scope_notice = False
        scope_used_level = ""
        filing_jurisdiction_level = ""

    # ---- RAG-only optimisation: skip LLM when no scope notice needed ----
    if mode == "rag_only" and not include_scope_notice:
        rag_response = state.get("final_response") or ""
        return {
            "final_response": rag_response,
            "response_metadata": {
                "mode": "rag_only",
                "scope_used": state.get("scope_used"),
                "scope_notice_included": False,
                "rag_confidence": (state.get("response_metadata") or {}).get(
                    "rag_confidence"
                ),
            },
        }

    # ---- Build context and call LLM ----
    ctx = _build_context(
        mode, state, include_scope_notice, scope_used_level, filing_jurisdiction_level
    )

    try:
        llm = _get_llm()
        system_prompt = build_synthesis_prompt(mode, ctx)

        # Messages: windowed conversation history + current user turn
        conv_history: list[dict] = list(state.get("conversation_history") or [])
        user_msg = state.get("user_message") or ""
        messages = conv_history + [{"role": "user", "content": user_msg}]

        llm_response: str = await llm.async_invoke(
            system=system_prompt,
            messages=messages,
            max_tokens=1024,
        )
    except Exception as exc:
        logger.error(
            "synthesizer_node: LLM call failed — returning hardcoded fallback: %s",
            exc,
            exc_info=True,
        )
        return {
            "final_response": _HARDCODED_FALLBACK,
            "response_metadata": {
                "mode": "error",
                "scope_used": state.get("scope_used"),
                "scope_notice_included": False,
                "rag_confidence": None,
            },
        }

    return {
        "final_response": llm_response,
        "response_metadata": {
            "mode": mode,
            "scope_used": state.get("scope_used"),
            "scope_notice_included": include_scope_notice,
            "rag_confidence": (state.get("response_metadata") or {}).get(
                "rag_confidence"
            ),
        },
    }
