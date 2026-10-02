# AI Customer Support Resolution Agent (LangGraph)

An agentic workflow that prepares a reply to a customer message. A human support representative reviews the reply before it is sent.

## Workflow

```
CUSTOMER QUERY
     |
  understand -> classify -> response -> review -> router
                                           ^        |
                                           |   approved / max cycles -> final -> END
                                           |        |
                                           +-- fix <-+ not approved
```

| Node | What it does | State fields written |
|------|--------------|----------------------|
| understand | Summarises the issue | `issue_summary` |
| classify | Picks category and priority (structured output) | `category`, `priority` |
| response | Writes the first draft | `generated_response` |
| review | Checks accuracy, completeness, tone, safety, relevance (structured output) | `approved`, `review_feedback` |
| fix | Rewrites the draft using the reviewer feedback | `generated_response`, `iteration_count` |
| final | Stores the final reply | `final_response` |

The loop review -> fix -> review runs at most **2 times** (`MAX_ITERATIONS` in `app/graph.py`).

## Project structure

```
main.py            entry point (input, run graph, save output)
app/
  state.py         AgentState (shared data of the workflow)
  prompts.py       one prompt per node
  nodes.py         node functions + structured output models
  graph.py         StateGraph, edges, conditional router
output/            created at runtime
  final_response.txt
  execution_result.json
```

Read the files in this order: `state.py` -> `prompts.py` -> `nodes.py` -> `graph.py` -> `main.py`.

## Setup

The project requires Python 3.10 or newer (Python 3.12 is used by the project).
Add your Groq API key to a `.env` file in the project root:

```dotenv
GROQ_API_KEY=your_groq_api_key
```

### Using uv

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run these commands from the project root. `uv sync` creates `.venv` if needed and installs the dependencies:

```powershell
uv sync
uv run python main.py
```

To activate the environment first, use `.\.venv\Scripts\Activate.ps1` in PowerShell, or `.\.venv\Scripts\activate.bat` in Command Prompt. Then you can run `python main.py`.

### Using Python and pip

From the project root, create and activate a virtual environment, then install the dependencies:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

On macOS or Linux, use these activation commands instead:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

## Test queries

| # | Query | Expected category |
|---|-------|-------------------|
| 1 | Where is my order? It was supposed to arrive yesterday. | ORDER_STATUS |
| 2 | My headphones arrived broken. | DAMAGED_PRODUCT |
| 3 | I ordered a blue shirt but received a red shirt. | WRONG_PRODUCT |
| 4 | I was charged twice for my order. | PAYMENT |
| 5 | I have a problem with my order. | OTHER (the reply should ask for more details) |

## Key LangGraph ideas used

- **State**: `AgentState` is shared by all nodes.
- **Node**: a function that returns only the fields it changes.
- **Edge**: `add_edge` always goes from A to B.
- **Conditional edge**: `add_conditional_edges` lets `route_after_review` choose `fix` or `final` based on `state["approved"]` and `state["iteration_count"]`.
- **Loop with a limit**: `iteration_count` stops the review/fix cycle.