"""Router node — classifies user intent and routes to the appropriate node."""

from app.agents.state import AgentState


def router_node(state: AgentState) -> dict:
    """Classify user intent and populate the 'intent' and 'entities' fields."""
    raise NotImplementedError


def route_after_classification(state: AgentState) -> str:
    """Returns the name of the next node. Must be pure — no side effects."""
    intent = state.get("intent")
    has_image = state.get("uploaded_image_path") is not None

    if has_image and intent in ("document_ocr", "form_fill"):
        return "ocr_node"
    if intent in ("procedure_inquiry", "dependency_check"):
        return "procedure_planner_node"
    if intent == "legal_question":
        return "rag_node"
    return "rag_node"  # safe default
