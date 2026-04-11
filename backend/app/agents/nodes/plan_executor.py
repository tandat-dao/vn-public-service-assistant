"""Plan executor node — loop node that drives all worker functions.

This is a TRUE LangGraph graph node. It reads execution_plan[plan_cursor:],
groups ready steps into an execution wave based on NODE_DEPENDENCIES, runs
them concurrently via asyncio.gather(), then routes back to itself or to
synthesizer_node via route_plan_executor.

Architecture rules:
  - This is a graph node, not a worker function.
  - It calls workers through NODE_REGISTRY — never imports them directly.
  - Only this node may write to execution_plan or plan_cursor.
  - Worker functions must never mutate execution_plan or plan_cursor.

Circuit-breaker: if plan_cursor >= MAX_PLAN_STEPS, appends a Vietnamese
error message to errors[] and returns without executing any workers.
"""

from __future__ import annotations

import asyncio
import logging
import os

from app.agents.node_registry import NODE_DEPENDENCIES, NODE_REGISTRY
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Circuit-breaker limit — reads env var so it is testable and configurable.
# Never hardcode 8 as a magic number inside function bodies.
# ---------------------------------------------------------------------------

MAX_PLAN_STEPS: int = int(os.environ.get("MAX_PLAN_STEPS", 8))

_CIRCUIT_BREAKER_MSG = "Giới hạn thực thi kế hoạch đã đạt tới."


# ---------------------------------------------------------------------------
# Wave computation helper
# ---------------------------------------------------------------------------

def _compute_wave(
    execution_plan: list[str],
    plan_cursor: int,
    node_dependencies: dict[str, list[str]],
) -> list[str]:
    """Return the next parallel execution wave from the remaining plan.

    A step belongs to the current wave if ALL of its dependencies appear
    in execution_plan[:plan_cursor] (i.e. have already run this invocation).

    Steps with no dependencies always belong to the first available wave.

    Args:
        execution_plan:   Full ordered plan list.
        plan_cursor:      Index of the first step not yet executed.
        node_dependencies: Static dependency matrix from NODE_REGISTRY.

    Returns:
        List of step names that are ready to run now.
    """
    already_run: set[str] = set(execution_plan[:plan_cursor])
    wave: list[str] = []

    for step in execution_plan[plan_cursor:]:
        deps = node_dependencies.get(step, [])
        if all(dep in already_run for dep in deps):
            wave.append(step)
        else:
            # Stop at the first step whose dependencies are not yet satisfied.
            # Steps after this point may depend on the current wave — we will
            # compute the next wave on the next plan_executor invocation.
            break

    return wave


# ---------------------------------------------------------------------------
# Routing function — exported for graph.py add_conditional_edges()
# ---------------------------------------------------------------------------

def route_plan_executor(state: AgentState) -> str:
    """Determine the next node after plan_executor_node completes a wave.

    Called by LangGraph after state has been updated with the node's return dict.

    Routes to "synthesizer_node" when:
      - plan_cursor >= len(execution_plan)  (plan exhausted)
      - plan_cursor >= MAX_PLAN_STEPS       (circuit-breaker)

    Routes to "plan_executor_node" (loop) otherwise.
    """
    plan_cursor: int = state.get("plan_cursor", 0)
    execution_plan: list[str] = state.get("execution_plan") or []

    if plan_cursor >= len(execution_plan) or plan_cursor >= MAX_PLAN_STEPS:
        return "synthesizer_node"
    return "plan_executor_node"


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

async def plan_executor_node(state: AgentState) -> dict:
    """Execute the next wave of worker functions from execution_plan.

    Reads:
        state["execution_plan"]   — ordered list of worker function names
        state["plan_cursor"]      — index of the next step to execute
        state["errors"]           — accumulated errors list

    Returns partial AgentState dict with:
        - All keys returned by worker functions in this wave (merged)
        - Updated "plan_cursor"
        - Possibly updated "errors" on circuit-breaker or worker exception

    Never raises — all exceptions from workers are caught and appended to errors[].
    """
    plan_cursor: int = state.get("plan_cursor", 0)
    execution_plan: list[str] = state.get("execution_plan") or []
    current_errors: list[str] = list(state.get("errors") or [])

    # ---- Step 1: Circuit-breaker ----
    if plan_cursor >= MAX_PLAN_STEPS:
        logger.warning(
            "plan_executor: circuit-breaker fired at cursor=%d", plan_cursor
        )
        return {"errors": current_errors + [_CIRCUIT_BREAKER_MSG]}

    # ---- Step 2: Compute the next wave ----
    wave = _compute_wave(execution_plan, plan_cursor, NODE_DEPENDENCIES)

    if not wave:
        # No ready steps — execution_plan may be empty or cursor past the end.
        # Route to synthesizer by returning the cursor unchanged so
        # route_plan_executor can detect plan exhaustion.
        logger.debug("plan_executor: no steps in wave — plan may be exhausted")
        return {"plan_cursor": plan_cursor}

    logger.debug(
        "plan_executor: executing wave=%s cursor=%d", wave, plan_cursor
    )

    # ---- Step 3: Execute wave concurrently ----
    results = await asyncio.gather(
        *[NODE_REGISTRY[step](state) for step in wave],
        return_exceptions=True,
    )

    # ---- Step 4: Merge results and collect errors ----
    merged: dict = {}
    extra_errors: list[str] = []

    for step, result in zip(wave, results):
        if isinstance(result, Exception):
            msg = f"Lỗi khi thực thi bước {step}: {result}"
            logger.error("plan_executor: step %s raised %r", step, result)
            extra_errors.append(msg)
        elif isinstance(result, dict):
            merged.update(result)

    if extra_errors:
        # Preserve any errors already in merged results (worker may have added some)
        existing_in_merged = list(merged.get("errors") or [])
        merged["errors"] = current_errors + existing_in_merged + extra_errors
    elif "errors" in merged:
        # Worker returned its own errors — prepend accumulated current errors
        merged["errors"] = current_errors + list(merged["errors"])

    # ---- Step 5: Advance cursor ----
    new_cursor = plan_cursor + len(wave)
    merged["plan_cursor"] = new_cursor

    return merged
