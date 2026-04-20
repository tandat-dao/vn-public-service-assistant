"""Router node — classifies user intent and produces an execution_plan.

This is a pure LLM classification step. It must never call a database,
Redis, Qdrant, or any other service. Its sole output is a routing decision.

Output contract:
    {
        "execution_plan": list[str],  # ordered worker function names
        "entities":       dict,       # extracted named entities (may be empty)
        "plan_cursor":    int,        # always 0 — reset on every invocation
    }
"""

from __future__ import annotations

import json
import logging

import re
from pydantic import ValidationError

from app.agents.node_registry import VALID_PLAN_STEPS
from app.agents.prompts.document_draft_prompt import DOCUMENT_TYPE_CONFIGS
from app.agents.prompts.router_prompt import (
    ROUTER_SYSTEM_PROMPT,
    RouterOutput,
    build_router_messages,
)
from app.agents.state import AgentState
from app.services.llm import LLMService

logger = logging.getLogger(__name__)

_FALLBACK: dict = {"execution_plan": ["rag_fn"], "entities": {}, "plan_cursor": 0}


def _enforce_ordering(plan: list[str]) -> list[str]:
    """Ensure ocr_fn always precedes form_filler_fn.

    If the LLM returns them in the wrong order, this silently fixes the
    ordering rather than failing — the ordering rule is a structural
    constraint, not a prompt error.
    """
    if "ocr_fn" in plan and "form_filler_fn" in plan:
        ocr_idx = plan.index("ocr_fn")
        fill_idx = plan.index("form_filler_fn")
        if ocr_idx > fill_idx:
            plan.remove("ocr_fn")
            plan.insert(fill_idx, "ocr_fn")
    return plan


_HOUSING_GUIDED_PROCEDURES = {"TTHC-001", "TTHC-002", "TTHC-003"}
_EXIT_PHRASES = ["thoát", "hủy", "dừng lại", "thôi"]


async def router_node(state: AgentState) -> dict:
    """Classify user intent and return execution_plan, entities, plan_cursor.

    Reads:
        state["user_message"]          — always present
        state["uploaded_image_path"]   — None when no image was uploaded
        state["guided_procedure_id"]   — non-None when in guided mode
        state["guided_step"]           — 0-3 when in guided mode

    Returns a partial AgentState dict that always includes:
        execution_plan, entities, plan_cursor
    May also include guided_procedure_id and guided_step when changing
    guided mode state.
    """
    user_message: str = state["user_message"]

    # ------------------------------------------------------------------ #
    # GUARD 1: Exit intent check — string match, zero LLM tokens.         #
    # Any message containing an exit phrase while in guided mode clears   #
    # the mode immediately without calling the LLM.                       #
    # ------------------------------------------------------------------ #
    if (
        state.get("guided_procedure_id") is not None
        and any(p in user_message.lower() for p in _EXIT_PHRASES)
    ):
        return {
            "execution_plan": [],
            "plan_cursor": 0,
            "entities": {},
            "guided_procedure_id": None,
            "guided_step": None,
            "domain": state.get("domain"),
            "final_response": (
                "Đã thoát khỏi chế độ hướng dẫn. Bạn có thể tiếp tục "
                "hỏi tôi bất kỳ câu hỏi nào về thủ tục hành chính."
            ),
        }

    # ------------------------------------------------------------------ #
    # GUARD 2: State 2 (FORM_FILLING) bypass — zero LLM tokens.           #
    # When the state machine is in State 2, the router always routes to   #
    # ["ocr_fn", "form_filler_fn"] regardless of what the user typed.     #
    # This prevents the LLM from re-classifying the intent mid-wizard.    #
    # ------------------------------------------------------------------ #
    if state.get("guided_step") == 2:
        procedure_id = state.get("guided_procedure_id", "TTHC-001")
        return {
            "execution_plan": ["ocr_fn", "form_filler_fn"],
            "plan_cursor": 0,
            "entities": {},
            "target_procedure_id": procedure_id,
            "guided_procedure_id": procedure_id,
            "guided_step": 2,
            "domain": "housing",
        }

    # ------------------------------------------------------------------ #
    # Normal LLM classification path.                                     #
    # ------------------------------------------------------------------ #
    has_image: bool = state.get("uploaded_image_path") is not None

    messages = build_router_messages(user_message, has_image)

    try:
        raw = await LLMService().async_invoke(
            system=ROUTER_SYSTEM_PROMPT,
            messages=messages,
            max_tokens=1024,
        )
    except Exception:
        # Network / API errors propagate — do not swallow infrastructure failures.
        raise

    # --- Parse JSON ---
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned.strip())
        data = json.loads(cleaned)
        output = RouterOutput.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning(
            "router_node: LLM returned unparseable output — using fallback. "
            "raw=%r error=%s",
            raw,
            exc,
        )
        return _FALLBACK.copy()

    # ------------------------------------------------------------------ #
    # HANDLER: draft_document intent                                       #
    # ------------------------------------------------------------------ #
    if output.intent == "draft_document":
        document_type = output.document_type
        if not document_type or document_type not in DOCUMENT_TYPE_CONFIGS:
            # Unsupported or missing document type — return helpful message listing
            # all supported types without routing to any worker functions.
            return {
                "execution_plan": [],
                "plan_cursor": 0,
                "entities": output.entities,
                "document_type": None,
                "domain": state.get("domain"),
                "final_response": (
                    "Xin lỗi, loại văn bản này chưa được hỗ trợ. "
                    "Các loại văn bản hiện hỗ trợ:\n"
                    "• Đơn xin xác nhận thông tin cư trú\n"
                    "• Đơn đề nghị đăng ký thường trú\n"
                    "• Đơn đề nghị đăng ký tạm trú\n"
                    "• Đơn khiếu nại\n"
                    "• Giấy cam kết cư trú"
                ),
            }
        return {
            "execution_plan": [],
            "plan_cursor": 0,
            "entities": output.entities,
            "document_type": document_type,
            "domain": output.entities.get("domain") or "housing",
        }

    # ------------------------------------------------------------------ #
    # HANDLER: start_guided intent                                         #
    # ------------------------------------------------------------------ #
    if output.intent == "start_guided":
        procedure_id = output.procedure_id
        if procedure_id not in _HOUSING_GUIDED_PROCEDURES:
            # Non-housing procedure or unknown ID — return unsupported message.
            return {
                "execution_plan": [],
                "plan_cursor": 0,
                "entities": output.entities,
                "guided_procedure_id": None,
                "guided_step": None,
                "final_response": (
                    "Tính năng hướng dẫn từng bước hiện chỉ hỗ trợ "
                    "các thủ tục cư trú (đăng ký thường trú, tạm trú, "
                    "xác nhận cư trú). Bạn có thể hỏi tôi về thủ tục "
                    "bạn cần và tôi sẽ giải đáp."
                ),
            }
        # Housing procedure — enter guided mode at State 0 (INTRO).
        # rag_fn is included so synthesizer has required-documents context
        # to present during the intro.
        return {
            "execution_plan": ["rag_fn"],
            "plan_cursor": 0,
            "entities": output.entities,
            "target_procedure_id": procedure_id,
            "guided_procedure_id": procedure_id,
            "guided_step": 0,  # INTRO
            "domain": "housing",
        }

    # --- Validate step names (prompt drift detection) ---
    invalid = set(output.execution_plan) - VALID_PLAN_STEPS
    if invalid:
        raise ValueError(
            f"router_node: LLM returned invalid plan steps {invalid}. "
            "This is a prompt drift bug. Valid steps: "
            f"{sorted(VALID_PLAN_STEPS)}"
        )

    # --- Enforce structural ordering ---
    plan = _enforce_ordering(list(output.execution_plan))

    result: dict = {
        "execution_plan": plan,
        "entities": output.entities,
        "plan_cursor": 0,
    }
    # Preserve guided mode context across normal turns (e.g. State 1 user asks a question)
    if state.get("guided_procedure_id") is not None:
        result["guided_procedure_id"] = state["guided_procedure_id"]
        result["guided_step"] = state.get("guided_step")

    return result
