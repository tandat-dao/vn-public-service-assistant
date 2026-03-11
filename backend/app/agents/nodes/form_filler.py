"""Form filler node — maps personal data to PDF form fields and fills the form."""

from app.agents.state import AgentState


def form_filler_node(state: AgentState) -> dict:
    """Fill a PDF form using personal_data from state and populate filled_fields."""
    raise NotImplementedError
