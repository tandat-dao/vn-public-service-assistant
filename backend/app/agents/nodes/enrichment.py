"""Enrichment node — pre-flight procedure plan resolution.

This is a TRUE LangGraph graph node wired between router_node and
plan_executor_node. It runs unconditionally after the Router on every
invocation.

Two-condition guard (see CLAUDE.md "LangGraph Node Conventions"):
  Condition 1: state["target_procedure_id"] is not None
  Condition 2: "form_filler_fn" is present in state["execution_plan"]

BOTH conditions must be true or the node returns {} immediately (no-op).

Rationale for Condition 2:
  A user asking a legal question that mentions a procedure does NOT need
  the full DAG injected into the Synthesizer prompt. Condition 2 is the
  primary token-saving mechanism — only inject the plan when the user is
  actually going to fill a form.

No LLM call is ever made by this node. If you find yourself adding one,
stop — the logic belongs in the Synthesizer or a worker function instead.
"""

from app.agents.nodes.procedure_planner import procedure_planner_fn
from app.agents.state import AgentState


async def enrichment_node(state: AgentState) -> dict:
    """Pre-flight enrichment: resolve procedure execution plan if needed.

    Two-condition guard — returns {} immediately unless BOTH are true:
      1. target_procedure_id is set (not None, not empty string)
      2. "form_filler_fn" is present in execution_plan

    When both conditions are met, delegates to procedure_planner_fn and
    returns its result dict (which contains "procedure_execution_plan").
    """
    # Condition 1: target_procedure_id must be set
    if not state.get("target_procedure_id"):
        return {}

    # Condition 2: form_filler_fn must be in the execution_plan
    if "form_filler_fn" not in state.get("execution_plan", []):
        return {}

    # Both conditions satisfied — resolve the procedure execution plan
    return await procedure_planner_fn(state)
