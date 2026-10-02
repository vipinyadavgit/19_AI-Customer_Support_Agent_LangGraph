"""
state.py
--------
The STATE is the shared "notebook" of the workflow.

Every node receives the current state, does its work, and returns ONLY the
fields it wants to change. LangGraph merges those changes into the state
and passes it to the next node.
"""

from typing import TypedDict


class AgentState(TypedDict):
    # --- Input (given by the user) ---
    customer_query: str

    # --- Written by the UNDERSTAND node ---
    issue_summary: str

    # --- Written by the CLASSIFY node ---
    category: str   # ORDER_STATUS, DAMAGED_PRODUCT, WRONG_PRODUCT, REFUND, PAYMENT, CANCELLATION, OTHER
    priority: str   # LOW, MEDIUM, HIGH

    # --- Written by the RESPONSE and FIX nodes ---
    generated_response: str

    # --- Written by the REVIEW node ---
    review_feedback: str
    approved: bool

    # --- Written by the FINAL node ---
    final_response: str

    # --- Counts how many times the FIX node has run (used to stop the loop) ---
    iteration_count: int


def create_initial_state(customer_query: str) -> AgentState:
    """Build the starting state: only the query is filled, everything else is empty."""
    return {
        "customer_query": customer_query,
        "issue_summary": "",
        "category": "",
        "priority": "",
        "generated_response": "",
        "review_feedback": "",
        "approved": False,
        "final_response": "",
        "iteration_count": 0,
    }
