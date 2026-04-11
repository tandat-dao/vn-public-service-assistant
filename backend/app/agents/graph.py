"""LangGraph agent graph — wires all nodes together into the plan_executor topology.

Graph topology:
    Entry
      └─► router_node
            └─► enrichment_node
                  └─► plan_executor_node ◄─┐
                        │                  │ (loop back if plan not exhausted)
                        └─► (conditional) ─┘
                              │
                              └─► synthesizer_node
                                    └─► END

The compiled graph is exposed as `agent_graph` at module level.
Import this instance in the chat endpoint — do NOT call build_graph() per request.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.nodes.enrichment import enrichment_node
from app.agents.nodes.plan_executor import plan_executor_node, route_plan_executor
from app.agents.nodes.router import router_node
from app.agents.nodes.synthesizer import synthesizer_node
from app.agents.state import AgentState


def build_graph():
    """Assemble and compile the LangGraph agent graph.

    Returns a compiled graph with recursion_limit=10.
    GraphRecursionError is caught at the chat endpoint level — not here.
    """
    graph = StateGraph(AgentState)

    # ---- Nodes ----
    graph.add_node("router_node", router_node)
    graph.add_node("enrichment_node", enrichment_node)
    graph.add_node("plan_executor_node", plan_executor_node)
    graph.add_node("synthesizer_node", synthesizer_node)

    # ---- Entry point ----
    graph.set_entry_point("router_node")

    # ---- Linear edges ----
    graph.add_edge("router_node", "enrichment_node")
    graph.add_edge("enrichment_node", "plan_executor_node")

    # ---- plan_executor loop (conditional) ----
    graph.add_conditional_edges(
        "plan_executor_node",
        route_plan_executor,
        {
            "plan_executor_node": "plan_executor_node",
            "synthesizer_node": "synthesizer_node",
        },
    )

    # ---- Terminal edge ----
    graph.add_edge("synthesizer_node", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Module-level compiled graph instance.
# Imported by the chat endpoint — never rebuilt per request.
# ---------------------------------------------------------------------------

agent_graph = build_graph()
