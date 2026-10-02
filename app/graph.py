"""
graph.py
--------
Here we connect the nodes into a workflow (a graph).

    START -> understand -> classify -> response -> review -> router
                                                              |
                              approved OR max cycles reached -> final -> END
                              not approved and cycles left   -> fix -> review (loop)
"""

from langgraph.graph import END, StateGraph

from app.nodes import (
    classify_node,
    final_node,
    fix_node,
    response_node,
    review_node,
    understand_node,
)
from app.state import AgentState

# Maximum number of fix cycles, so the loop can never run forever.
MAX_ITERATIONS = 2


def route_after_review(state: AgentState) -> str:
    """
    Router used by the conditional edge.
    It returns the NAME of the next step; LangGraph looks it up in the mapping below.
    """
    if state["approved"]:
        return "final"

    if state["iteration_count"] >= MAX_ITERATIONS:
        print("\n[info] Maximum fix cycles reached. Moving to the final response.")
        return "final"

    return "fix"


def build_graph():
    # 1. Create the graph and tell it which state to use.
    workflow = StateGraph(AgentState)

    # 2. Add nodes (name, function).
    workflow.add_node("understand", understand_node)
    workflow.add_node("classify", classify_node)
    workflow.add_node("response", response_node)
    workflow.add_node("review", review_node)
    workflow.add_node("fix", fix_node)
    workflow.add_node("final", final_node)

    # 3. Set where the workflow starts.
    workflow.set_entry_point("understand")

    # 4. Normal edges: always go from A to B.
    workflow.add_edge("understand", "classify")
    workflow.add_edge("classify", "response")
    workflow.add_edge("response", "review")

    # 5. Conditional edge: after "review", the router decides where to go.
    workflow.add_conditional_edges(
        "review",
        route_after_review,
        {
            "fix": "fix",
            "final": "final",
        },
    )

    # 6. The fix node loops back to review; final ends the workflow.
    workflow.add_edge("fix", "review")
    workflow.add_edge("final", END)

    # 7. Compile into a runnable graph.
    return workflow.compile()
