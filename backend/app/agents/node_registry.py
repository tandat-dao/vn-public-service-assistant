"""NODE_REGISTRY — the single file that imports all worker functions.

Only plan_executor and the router prompt should import from this module.
No other file should import worker functions directly.

VALID_PLAN_STEPS is injected into the router system prompt at build time so
the prompt never hardcodes step names as string literals.
"""

from __future__ import annotations

from collections.abc import Callable

from app.agents.nodes.form_filler import form_filler_fn
from app.agents.nodes.ocr import ocr_fn
from app.agents.nodes.rag import rag_fn
from app.agents.state import AgentState

# ---------------------------------------------------------------------------
# Valid step names — single source of truth
# ---------------------------------------------------------------------------

VALID_PLAN_STEPS: frozenset[str] = frozenset({"rag_fn", "ocr_fn", "form_filler_fn"})

# NOTE: "procedure_planner_fn" is intentionally NOT a valid plan step.
# Procedure resolution runs in enrichment_node (a true graph node that executes
# before plan_executor) and is never scheduled as an execution_plan entry.

# ---------------------------------------------------------------------------
# Static dependency matrix — drives parallel wave execution in plan_executor
# ---------------------------------------------------------------------------

NODE_DEPENDENCIES: dict[str, list[str]] = {
    "rag_fn": [],
    "ocr_fn": [],
    "form_filler_fn": ["ocr_fn"],
}

# ---------------------------------------------------------------------------
# Worker function registry
# ---------------------------------------------------------------------------
# This is the ONLY file that imports all worker functions.
# graph.py and plan_executor must go through NODE_REGISTRY — never import
# worker functions directly elsewhere.

NODE_REGISTRY: dict[str, Callable[[AgentState], dict]] = {
    "rag_fn": rag_fn,
    "ocr_fn": ocr_fn,
    "form_filler_fn": form_filler_fn,
}
