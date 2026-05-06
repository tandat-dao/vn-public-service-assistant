"""Synthesizer node — final response assembly from accumulated AgentState.

This is a TRUE LangGraph graph node, always the last node before END.
It is NOT a worker function and NOT in NODE_REGISTRY.

Eight response modes (evaluated in priority order):
  0. out_of_scope       — state["out_of_scope"] is True (highest priority)
  1. rag_empty          — rag_returned_empty True + intent not form/guided
  2. error              — state["errors"] is non-empty
  3. circuit_breaker    — plan stalled (plan_cursor >= MAX_PLAN_STEPS), no errors
  4. guided_step        — state["guided_step"] is not None (TASK-APP-18)
  5. form_fill_complete — state["form_fill_complete"] is True
  6. form_fill_partial  — state["unfilled_required_fields"] is non-empty
  7. rag_only           — state["retrieved_chunks"] is non-empty
  8. fallback           — none of the above

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

from app.agents.prompts.synthesis_prompt import (
    _scope_level_name,
    build_guided_prompt,
    build_synthesis_prompt,
)
from app.agents.state import AgentState
from app.core.text_utils import strip_markdown

logger = logging.getLogger(__name__)

# Must match plan_executor.py — kept in sync manually.
MAX_PLAN_STEPS = 8

# Procedures whose guided wizard uses the interactive page form (State 2) and
# hardcoded INTRO messages (State 0) instead of the LLM-driven form_filler_fn
# pipeline used by housing procedures.
_NEW_GUIDED_PROCEDURE_IDS = {"TTHC-CR-001", "TTHC-CR-002", "TTHC-AD-001", "TTHC-AD-002"}

_GUIDED_INTRO_MESSAGES: dict[str, str] = {
    "TTHC-CR-001": (
        "Tôi sẽ hỗ trợ bạn thực hiện thủ tục Đăng ký khai sinh "
        "tại UBND cấp xã. Để bắt đầu, vui lòng tải lên ảnh CCCD của "
        "bạn — hệ thống sẽ tự động đọc thông tin cá nhân để điền vào "
        "mẫu tờ khai. Bạn có thể tải lên CCCD ngay bây giờ không?"
    ),
    "TTHC-CR-002": (
        "Tôi sẽ hỗ trợ bạn thực hiện thủ tục Cấp bản sao Trích lục "
        "hộ tịch. Lưu ý rằng thủ tục này yêu cầu bạn đã hoàn thành "
        "Đăng ký khai sinh trước đó. Vui lòng tải lên ảnh CCCD để hệ "
        "thống tự động điền thông tin vào tờ khai yêu cầu."
    ),
    "TTHC-AD-001": (
        "Tôi sẽ hỗ trợ bạn thực hiện thủ tục Đăng ký việc nuôi con "
        "nuôi trong nước tại UBND cấp xã. Đây là thủ tục có thời hạn "
        "giải quyết 30 ngày làm việc và yêu cầu nhiều giấy tờ — hãy chuẩn "
        "bị đầy đủ hồ sơ theo danh sách trên trang này. Vui lòng tải lên "
        "ảnh CCCD của bạn để bắt đầu."
    ),
    "TTHC-AD-002": (
        "Tôi sẽ hỗ trợ bạn thực hiện thủ tục Đăng ký lại việc nuôi "
        "con nuôi trong nước. Lưu ý rằng thủ tục này yêu cầu bạn đã "
        "hoàn thành Đăng ký việc nuôi con nuôi trước đó. Vui lòng tải lên "
        "ảnh CCCD để hệ thống tự động điền thông tin vào tờ khai."
    ),
}

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
# Retrieved sources builder — for response_metadata passthrough to frontend
# ---------------------------------------------------------------------------

def _build_retrieved_sources(state: AgentState) -> list[dict]:
    """Build a list of source dicts from retrieved_chunks for the SSE metadata event.

    Only chunks where both article_number and document_number are non-empty are
    included. Content is capped at 1200 characters (backend enforcement — the
    frontend must not truncate further). Returns [] when no chunks are present.
    """
    chunks = state.get("retrieved_chunks") or []
    sources: list[dict] = []
    for chunk in chunks:
        if isinstance(chunk, dict):
            article_number = chunk.get("article_number", "") or ""
            document_number = chunk.get("document_number", "") or ""
            content = chunk.get("content", "") or ""
        else:
            article_number = getattr(chunk, "article_number", "") or ""
            document_number = getattr(chunk, "document_number", "") or ""
            content = getattr(chunk, "content", "") or ""
        if article_number and document_number:
            # Prefix numeric article numbers with "Điều " so the frontend
            # substring matcher does not false-positive against digits in
            # years or document numbers. "0" (preamble marker) is excluded.
            if article_number.isdigit() and article_number != "0":
                normalized_article = f"Điều {article_number}"
            elif article_number.startswith("Điều "):
                normalized_article = article_number
            else:
                normalized_article = article_number
            sources.append({
                "article_number": normalized_article,
                "document_number": document_number,
                "content": content[:1200],
            })
    return sources


# ---------------------------------------------------------------------------
# Mode determination
# ---------------------------------------------------------------------------

def _determine_mode(state: AgentState) -> str:
    """Return the response mode string based on accumulated state.

    Priority order — use the FIRST matching condition:
      1. "error"              — errors list is non-empty
      2. "circuit_breaker"   — plan_cursor >= MAX_PLAN_STEPS AND errors empty
      3. "guided_step"       — guided_step is not None (TASK-APP-18 wizard)
      4. "form_fill_complete" — form_fill_complete is True
      5. "form_fill_partial"  — unfilled_required_fields is non-empty
      6. "rag_only"           — retrieved_chunks is non-empty
      7. "fallback"           — none of the above
    """
    if state.get("out_of_scope"):
        return "out_of_scope"

    if state.get("rag_returned_empty") and \
       state.get("intent") not in (
           "form_fill", "start_guided", "continue_guided"
       ):
        return "rag_empty"

    errors = state.get("errors") or []
    if errors:
        return "error"

    plan_cursor = state.get("plan_cursor", 0)
    if plan_cursor >= MAX_PLAN_STEPS:
        return "circuit_breaker"

    # guided_step check has priority over all form/RAG modes.
    # NOTE: The first entry may be a compaction summary (role "assistant",
    # content prefixed with "Tóm tắt trước đó: ") — this is intentional.
    if state.get("guided_step") is not None:
        return "guided_step"

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

    # ---- Out-of-scope guard: fixed response, zero LLM calls ----
    if mode == "out_of_scope":
        return {
            "final_response": "Xin lỗi, tôi chỉ có thể hỗ trợ các câu hỏi liên quan đến thủ tục hành chính. Bạn có câu hỏi nào về đăng ký cư trú, hộ tịch, hoặc nuôi con nuôi không?",
            "response_metadata": {
                "mode": "out_of_scope",
                "guided_procedure_id": None,
                "guided_step": None,
                "scope_used": None,
                "scope_notice_included": False,
                "rag_confidence": None,
                "filled_form_path": None,
                "retrieved_sources": [],
                "document_type": None,
            },
        }

    # ---- RAG empty guard: fixed response, zero LLM calls ----
    if mode == "rag_empty":
        return {
            "final_response": (
                "Xin lỗi, tôi chưa tìm thấy thông tin pháp "
                "lý liên quan đến câu hỏi của bạn trong cơ sở "
                "dữ liệu hiện tại. Điều này có thể do câu hỏi "
                "nằm ngoài phạm vi các thủ tục hành chính đang "
                "được hỗ trợ, hoặc dữ liệu pháp lý cho lĩnh "
                "vực này chưa được cập nhật. Bạn có thể thử "
                "hỏi về đăng ký cư trú, hộ tịch, hoặc nuôi "
                "con nuôi."
            ),
            "response_metadata": {
                "mode": "rag_empty",
                "guided_procedure_id": None,
                "guided_step": None,
                "scope_used": state.get("scope_used"),
                "scope_notice_included": False,
                "rag_confidence": 0.0,
                "filled_form_path": None,
                "retrieved_sources": [],
                "document_type": None,
            },
        }

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
                "retrieved_sources": _build_retrieved_sources(state),
            },
        }

    # ---- Guided procedure wizard mode (TASK-APP-18) ----
    if mode == "guided_step":
        current_step_early = state.get("guided_step", 0)
        guided_procedure_id_early = state.get("guided_procedure_id")

        # --- State 0 early return for new-domain procedures ---
        # Skip the LLM call entirely and return a hardcoded INTRO message.
        # This saves tokens and produces a consistent, controlled response.
        if current_step_early == 0 and guided_procedure_id_early in _NEW_GUIDED_PROCEDURE_IDS:
            intro_text = _GUIDED_INTRO_MESSAGES.get(
                guided_procedure_id_early,
                "Vui lòng tải lên ảnh CCCD của bạn để bắt đầu.",
            )
            return {
                "final_response": intro_text,
                "response_metadata": {
                    "mode": "guided_step",
                    "guided_procedure_id": guided_procedure_id_early,
                    "guided_step": 1,  # advance to AWAIT_CCCD
                    "scope_used": state.get("scope_used"),
                    "scope_notice_included": False,
                    "rag_confidence": None,
                    "filled_form_path": None,
                    "retrieved_sources": [],
                    "document_type": None,
                },
                # Write back so chat.py persists the advanced step to Redis.
                "guided_procedure_id": guided_procedure_id_early,
                "guided_step": 1,
            }

        # --- State 2 early return for new-domain procedures ---
        # Direct the user to the interactive form on the procedure page.
        # form_filler_fn is NOT called for these procedures (router excluded it).
        if current_step_early == 2 and guided_procedure_id_early in _NEW_GUIDED_PROCEDURE_IDS:
            page_form_response = (
                "Thông tin cá nhân từ giấy tờ của bạn đã được trích xuất thành công. "
                "Vui lòng chuyển sang trang thủ tục tương ứng, chọn tab mẫu đơn cần điền, "
                "kiểm tra lại thông tin đã được tự động điền, sau đó nhấn "
                "\"Tải xuống tờ khai đã điền\" để tải PDF về máy."
            )
            return {
                "final_response": page_form_response,
                "response_metadata": {
                    "mode": "guided_step",
                    "guided_procedure_id": guided_procedure_id_early,
                    "guided_step": 2,
                    "scope_used": state.get("scope_used"),
                    "scope_notice_included": False,
                    "rag_confidence": None,
                    "filled_form_path": None,
                    "retrieved_sources": [],
                    "document_type": None,
                },
                # Exit guided mode after showing the page-form guidance.
                "guided_procedure_id": None,
                "guided_step": None,
            }

        try:
            llm = _get_llm()
            prompt = build_guided_prompt(state)
            # First entry may be a compaction summary — see synthesizer_node comment below.
            conv_history: list[dict] = list(state.get("conversation_history") or [])
            user_msg = state.get("user_message") or ""
            messages = conv_history + [{"role": "user", "content": user_msg}]

            guided_response: str = strip_markdown(await llm.async_invoke(
                system=prompt,
                messages=messages,
                max_tokens=1024,
            ))
        except Exception as exc:
            logger.error(
                "synthesizer_node: guided_step LLM call failed — returning fallback: %s",
                exc,
                exc_info=True,
            )
            guided_response = _HARDCODED_FALLBACK

        # Determine next guided_step
        current_step = state.get("guided_step", 0)
        if current_step == 0:
            next_step: int | None = 1
        elif current_step == 2 and state.get("form_fill_complete", False):
            next_step = 3
        elif current_step == 3:
            next_step = None  # end guided mode
        else:
            next_step = current_step  # stay in current step (e.g. step 1 awaiting CCCD)

        next_guided_id = (
            state.get("guided_procedure_id") if next_step is not None else None
        )

        metadata: dict = {
            "mode": "guided_step",
            "guided_procedure_id": next_guided_id,
            "guided_step": next_step,
            "scope_used": state.get("scope_used"),
            "scope_notice_included": False,
            "rag_confidence": None,
            "retrieved_sources": _build_retrieved_sources(state),
        }
        # Include filled_form_path when form fill completed within guided flow
        if state.get("form_fill_complete") and state.get("filled_form_path"):
            metadata["filled_form_path"] = state.get("filled_form_path") or ""

        return {
            "final_response": guided_response,
            "response_metadata": metadata,
            # Write back updated guided state so chat.py can persist it to Redis
            "guided_procedure_id": next_guided_id,
            "guided_step": next_step,
        }

    # ---- Build context and call LLM ----
    ctx = _build_context(
        mode, state, include_scope_notice, scope_used_level, filing_jurisdiction_level
    )

    try:
        llm = _get_llm()
        system_prompt = build_synthesis_prompt(mode, ctx)

        # Messages: windowed conversation history + current user turn.
        # The first entry may be a compaction summary (role="assistant",
        # content prefixed "Tóm tắt trước đó: ") written by RedisService._compact_history
        # when the session exceeded 6 turns. This is intentional — "assistant" role is
        # universally supported in the messages array by both Anthropic and Gemini.
        conv_history: list[dict] = list(state.get("conversation_history") or [])
        user_msg = state.get("user_message") or ""
        messages = conv_history + [{"role": "user", "content": user_msg}]

        llm_response: str = strip_markdown(await llm.async_invoke(
            system=system_prompt,
            messages=messages,
            max_tokens=1024,
        ))
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

    metadata: dict = {
        "mode": mode,
        "scope_used": state.get("scope_used"),
        "scope_notice_included": include_scope_notice,
        "rag_confidence": (state.get("response_metadata") or {}).get(
            "rag_confidence"
        ),
    }
    # Surface filled_form_path only for form_fill_complete so the frontend
    # can render a download button.  Never include it for other modes —
    # the path is a MinIO-internal string and must not leak unnecessarily.
    if mode == "form_fill_complete":
        metadata["filled_form_path"] = state.get("filled_form_path") or ""
    # Include retrieved_sources for all content modes so the frontend can
    # show chunk content on citation hover. Omitted for error/circuit_breaker —
    # those have no retrieved chunks to surface.
    if mode not in ("error", "circuit_breaker"):
        metadata["retrieved_sources"] = _build_retrieved_sources(state)

    return {
        "final_response": llm_response,
        "response_metadata": metadata,
    }
