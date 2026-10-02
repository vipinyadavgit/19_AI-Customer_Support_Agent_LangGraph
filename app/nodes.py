"""
nodes.py
--------
A NODE is just a Python function:
    input  -> the current state
    output -> a dict with ONLY the state fields it wants to update

LangGraph merges that dict into the state automatically.
"""

import os
from typing import Literal

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from app.prompts import (
    CLASSIFY_PROMPT,
    FIX_PROMPT,
    RESPONSE_PROMPT,
    REVIEW_PROMPT,
    UNDERSTAND_PROMPT,
)
from app.state import AgentState


# ---------------------------------------------------------------------------
# Structured output models
# The LLM is forced to answer in these shapes, so we never have to parse
# free text. That is why the router can safely use state["approved"].
# ---------------------------------------------------------------------------
class ClassificationResult(BaseModel):
    category: Literal[
        "ORDER_STATUS",
        "DAMAGED_PRODUCT",
        "WRONG_PRODUCT",
        "REFUND",
        "PAYMENT",
        "CANCELLATION",
        "OTHER",
    ] = Field(description="Category of the customer request")
    priority: Literal["LOW", "MEDIUM", "HIGH"] = Field(description="Priority of the request")


class ReviewResult(BaseModel):
    approved: bool = Field(description="True if the reply is good enough to send")
    feedback: str = Field(description="Short feedback explaining what to improve")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_llm() -> ChatGroq:
    """Create the LLM client. The API key is read from the .env file (GROQ_API_KEY)."""
    model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    return ChatGroq(model=model_name, temperature=0)


def print_header(title: str) -> None:
    print("\n" + "=" * 40)
    print(title)
    print("=" * 40)


# ---------------------------------------------------------------------------
# Node 1: UNDERSTAND  ->  writes issue_summary
# ---------------------------------------------------------------------------
def understand_node(state: AgentState) -> dict:
    print_header("UNDERSTANDING CUSTOMER QUERY")

    prompt = UNDERSTAND_PROMPT.format(customer_query=state["customer_query"])
    try:
        summary = get_llm().invoke(prompt).content.strip()
    except Exception as error:
        print(f"[warning] LLM call failed: {error}")
        summary = state["customer_query"]  # fallback: use the original message

    print("\nIssue:\n" + summary)
    return {"issue_summary": summary}


# ---------------------------------------------------------------------------
# Node 2: CLASSIFY  ->  writes category and priority (structured output)
# ---------------------------------------------------------------------------
def classify_node(state: AgentState) -> dict:
    print_header("CLASSIFICATION")

    prompt = CLASSIFY_PROMPT.format(
        customer_query=state["customer_query"],
        issue_summary=state["issue_summary"],
    )
    try:
        structured_llm = get_llm().with_structured_output(ClassificationResult)
        result = structured_llm.invoke(prompt)
        category, priority = result.category, result.priority
    except Exception as error:
        print(f"[warning] Classification failed, using defaults: {error}")
        category, priority = "OTHER", "MEDIUM"

    print(f"\nCategory:\n{category}\n\nPriority:\n{priority}")
    return {"category": category, "priority": priority}


# ---------------------------------------------------------------------------
# Node 3: RESPONSE  ->  writes generated_response (first draft)
# ---------------------------------------------------------------------------
def response_node(state: AgentState) -> dict:
    print_header("GENERATING RESPONSE")

    prompt = RESPONSE_PROMPT.format(
        customer_query=state["customer_query"],
        issue_summary=state["issue_summary"],
        category=state["category"],
        priority=state["priority"],
    )
    try:
        draft = get_llm().invoke(prompt).content.strip()
    except Exception as error:
        print(f"[warning] LLM call failed: {error}")
        draft = (
            "Thank you for contacting us. Please share your order number and "
            "more details about the problem so our support team can help you."
        )

    print("\n" + draft)
    return {"generated_response": draft}


# ---------------------------------------------------------------------------
# Node 4: REVIEW  ->  writes approved and review_feedback (structured output)
# ---------------------------------------------------------------------------
def review_node(state: AgentState) -> dict:
    print_header("REVIEW")

    prompt = REVIEW_PROMPT.format(
        customer_query=state["customer_query"],
        category=state["category"],
        generated_response=state["generated_response"],
    )
    try:
        structured_llm = get_llm().with_structured_output(ReviewResult)
        result = structured_llm.invoke(prompt)
        approved, feedback = result.approved, result.feedback
    except Exception as error:
        # If the review itself fails we stop looping and flag it for a human.
        print(f"[warning] Review failed: {error}")
        approved, feedback = True, "Automatic review failed - a human must check this reply."

    print(f"\nApproved:\n{approved}\n\nFeedback:\n{feedback}")
    return {"approved": approved, "review_feedback": feedback}


# ---------------------------------------------------------------------------
# Node 5: FIX  ->  improves generated_response and counts the attempt
# ---------------------------------------------------------------------------
def fix_node(state: AgentState) -> dict:
    print_header("FIX")
    print("\nImproving response...")

    prompt = FIX_PROMPT.format(
        customer_query=state["customer_query"],
        category=state["category"],
        priority=state["priority"],
        generated_response=state["generated_response"],
        review_feedback=state["review_feedback"],
    )
    try:
        improved = get_llm().invoke(prompt).content.strip()
    except Exception as error:
        print(f"[warning] LLM call failed, keeping the old response: {error}")
        improved = state["generated_response"]

    return {
        "generated_response": improved,
        "iteration_count": state["iteration_count"] + 1,  # one more fix cycle used
    }


# ---------------------------------------------------------------------------
# Node 6: FINAL  ->  writes final_response
# ---------------------------------------------------------------------------
def final_node(state: AgentState) -> dict:
    print_header("FINAL RESPONSE")

    final_text = state["generated_response"]
    print("\n" + final_text)
    return {"final_response": final_text}
