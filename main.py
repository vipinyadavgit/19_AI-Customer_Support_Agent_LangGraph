"""
main.py
-------
Entry point.  Run with:  uv run python main.py
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

OUTPUT_DIR = Path("output")


def save_output(result: dict) -> None:
    """Save the final reply and the full state to the output/ folder."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    (OUTPUT_DIR / "final_response.txt").write_text(result["final_response"], encoding="utf-8")
    (OUTPUT_DIR / "execution_result.json").write_text(
        json.dumps(result, indent=4, ensure_ascii=False), encoding="utf-8"
    )
    print("\nSaved: output/final_response.txt and output/execution_result.json")


def main() -> None:
    # Load GROQ_API_KEY (and optional settings) from the .env file.
    load_dotenv()

    if not os.getenv("GROQ_API_KEY"):
        print("Error: GROQ_API_KEY is missing. Copy .env.example to .env and add your key.")
        return

    # Imported after load_dotenv() so the environment is ready.
    from app.graph import build_graph
    from app.state import create_initial_state

    print("=" * 40)
    print("       AI CUSTOMER SUPPORT AGENT")
    print("=" * 40)
    print("\nEnter customer query:\n")
    customer_query = input("> ").strip()

    if not customer_query:
        print("Error: the query is empty. Please type a customer message.")
        return

    graph = build_graph()

    try:
        result = graph.invoke(create_initial_state(customer_query))
    except Exception as error:
        print(f"\nError: the workflow failed: {error}")
        return

    save_output(result)


if __name__ == "__main__":
    main()
