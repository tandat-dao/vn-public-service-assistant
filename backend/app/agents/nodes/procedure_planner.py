"""Procedure planner node — resolves the execution plan for a target procedure."""

from app.agents.state import AgentState


def procedure_planner_node(state: AgentState) -> dict:
    """Resolve procedure dependencies and populate procedure_execution_plan."""
    raise NotImplementedError
