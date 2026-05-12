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
from app.agents.prompts.router_prompt import (
    ROUTER_SYSTEM_PROMPT,
    RouterOutput,
    build_router_messages,
)
from app.agents.state import AgentState
from app.services.llm import LLMService

logger = logging.getLogger(__name__)

_FALLBACK: dict = {"execution_plan": ["rag_fn"], "entities": {}, "plan_cursor": 0}

# Lazy singleton — reads ROUTER_LLM_BACKEND at first call so the backend
# can be changed via env var without restarting the interpreter in tests.
_router_llm: LLMService | None = None


def _get_router_llm() -> LLMService:
    global _router_llm
    if _router_llm is None:
        from app.config import settings
        _router_llm = LLMService(backend=settings.ROUTER_LLM_BACKEND)
    return _router_llm

# Only these three city scope codes are accepted from the LLM.  Any other value
# (misspelling, hallucination, etc.) is silently coerced to None.
VALID_CITY_SCOPES: frozenset[str] = frozenset({"VN-HCM", "VN-HN", "VN-DN"})


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


_ALL_GUIDED_PROCEDURES = {
    "TTHC-001", "TTHC-002", "TTHC-003",       # housing
    "TTHC-CR-001", "TTHC-CR-002",               # civil_registration
    "TTHC-AD-001", "TTHC-AD-002",               # adoption
}
_NEW_GUIDED_PROCEDURES = {"TTHC-CR-001", "TTHC-CR-002", "TTHC-AD-001", "TTHC-AD-002"}
_EXIT_PHRASES = ["thoát", "hủy", "dừng lại", "thôi"]


def _domain_for_procedure(procedure_id: str) -> str:
    if procedure_id in {"TTHC-CR-001", "TTHC-CR-002"}:
        return "civil_registration"
    if procedure_id in {"TTHC-AD-001", "TTHC-AD-002"}:
        return "adoption"
    return "housing"


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
        domain = _domain_for_procedure(procedure_id)
        if procedure_id in _NEW_GUIDED_PROCEDURES:
            # New-domain procedures: OCR only — synthesizer handles State 2 response
            # without calling form_filler_fn (user fills form on the procedure page).
            return {
                "execution_plan": ["ocr_fn"],
                "plan_cursor": 0,
                "entities": {},
                "target_procedure_id": procedure_id,
                "guided_procedure_id": procedure_id,
                "guided_step": 2,
                "domain": domain,
            }
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

    # Extract the last user turn from history to resolve short-query pronouns
    # ("nó", "thủ tục này") via proportional context augmentation in
    # build_router_messages(). Mirrors the pattern in rag.py _build_search_query().
    history: list[dict] = state.get("conversation_history") or []
    prev_user_message: str | None = None
    for turn in reversed(history):
        if turn.get("role") == "user":
            prev_user_message = turn.get("content")
            break

    messages = build_router_messages(user_message, has_image, prev_user_message)

    try:
        raw = await _get_router_llm().async_invoke(
            system=ROUTER_SYSTEM_PROMPT,
            messages=messages,
            max_tokens=512,
            json_mode=True,
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
    # HANDLER: start_guided intent                                         #
    # ------------------------------------------------------------------ #
    if output.intent == "start_guided":
        procedure_id = output.procedure_id
        if procedure_id not in _ALL_GUIDED_PROCEDURES:
            # Unknown procedure ID — return unsupported message.
            return {
                "execution_plan": [],
                "plan_cursor": 0,
                "entities": output.entities,
                "guided_procedure_id": None,
                "guided_step": None,
                "final_response": (
                    "Tính năng hướng dẫn từng bước hiện chỉ hỗ trợ "
                    "các thủ tục nhà ở, hộ tịch và nuôi con nuôi. "
                    "Bạn có thể hỏi tôi về thủ tục bạn cần và tôi sẽ giải đáp."
                ),
            }
        # Supported procedure — enter guided mode at State 0 (INTRO).
        # rag_fn is included so synthesizer has required-documents context
        # to present during the intro (housing procedures only — new procedures
        # use hardcoded INTRO messages in synthesizer_node).
        domain = _domain_for_procedure(procedure_id)
        return {
            "execution_plan": ["rag_fn"],
            "plan_cursor": 0,
            "entities": output.entities,
            "target_procedure_id": procedure_id,
            "guided_procedure_id": procedure_id,
            "guided_step": 0,  # INTRO
            "domain": domain,
        }

    # ------------------------------------------------------------------ #
    # HANDLER: out_of_scope intent                                         #
    # ------------------------------------------------------------------ #
    if output.intent == "out_of_scope":
        return {
            "execution_plan": [],
            "plan_cursor": 0,
            "entities": output.entities,
            "out_of_scope": True,
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
    # Pass through rag_query intent + procedure_id for scoped RAG retrieval.
    # Only added when non-None so the 3-key contract holds for generic turns.
    if output.intent is not None:
        result["intent"] = output.intent
    if output.procedure_id is not None:
        result["procedure_id"] = output.procedure_id
        result["target_procedure_id"] = output.procedure_id

    # Extract city scope detected by the router LLM.  Validated against the
    # allow-list — any value outside VALID_CITY_SCOPES is silently set to None.
    location_scope = output.location_scope
    if location_scope not in VALID_CITY_SCOPES:
        location_scope = None
    if location_scope is not None:
        result["location_scope"] = location_scope

    # Preserve guided mode context across normal turns (e.g. State 1 user asks a question)
    if state.get("guided_procedure_id") is not None:
        result["guided_procedure_id"] = state["guided_procedure_id"]
        result["guided_step"] = state.get("guided_step")

    return result
