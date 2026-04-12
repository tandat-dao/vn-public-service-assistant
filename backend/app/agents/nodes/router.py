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


async def router_node(state: AgentState) -> dict:
    """Classify user intent and return execution_plan, entities, plan_cursor.

    Reads:
        state["user_message"]          — always present
        state["uploaded_image_path"]   — None when no image was uploaded

    Returns a partial AgentState dict with exactly:
        execution_plan, entities, plan_cursor
    """
    user_message: str = state["user_message"]
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

    return {
        "execution_plan": plan,
        "entities": output.entities,
        "plan_cursor": 0,
    }
