"""Synthesizer node — produces the final user-facing response string."""

from app.agents.state import AgentState


def synthesizer_node(state: AgentState) -> dict:
    """Synthesize retrieved_chunks and procedure plan into a final_response string."""
    raise NotImplementedError
