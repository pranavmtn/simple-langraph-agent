# Simple LangGraph Agent

A small learning project that solves everyday life problems using **LangGraph orchestration**.

The interesting part: an LLM **router** decides which node runs next from a set of allowed edges. The graph is not a fixed pipeline — the AI chooses the path through nodes like `brainstorm`, `prioritize`, `action_plan`, and `reflect`.

## Graph idea

```text
START → router → (AI picks next node) → router → ... → finalize → END
```

Nodes:

- **clarify** — ask a short question if the problem is vague
- **brainstorm** — generate practical ideas
- **prioritize** — pick the best 1–2 ideas
- **action_plan** — turn ideas into small steps
- **reflect** — sanity-check the plan
- **finalize** — write the final answer

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file:

```env
OPENAI_API_KEY=your-key-here
```

## Visualize the graph

Generate `graph.png` and `graph.mmd`:

```bash
python visualize.py
```

Open `graph.png` to see nodes and edges. Dashed lines from `router` are **conditional edges** (AI picks the path).

## How input and output work

You do **not** type into each node separately. LangGraph uses **shared state**:

```text
YOUR INPUT  -->  state["problem"]  -->  nodes read & update state  -->  state["final_answer"]
```

1. **Input**: pass your problem once when starting the graph (`main.py` or `run_agent("...")`).
2. **Nodes**: each node reads `state["problem"]` and other fields, then writes back (ideas, steps, messages).
3. **Router**: after most nodes, the AI picks the next edge.
4. **Output**: the `finalize` node writes `state["final_answer"]` — that is your answer.

Example node path:

```text
router -> brainstorm -> router -> prioritize -> router -> action_plan -> router -> reflect -> router -> finalize -> END
```

## Transparent chat UI (recommended)

Run locally:

```bash
streamlit run app.py
```

Or:

```bash
streamlit run streamlit_app.py
```

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub (`pranavmtn/simple-langraph-agent`).
2. Go to [share.streamlit.io](https://share.streamlit.io) and deploy.
3. Use these settings:

| Field | Value |
|-------|-------|
| Repository | `pranavmtn/simple-langraph-agent` |
| Branch | `main` (not `master`) |
| Main file path | `streamlit_app.py` |

4. Add your API key under **App settings → Secrets**:

```toml
OPENAI_API_KEY = "sk-your-key-here"
```

5. Reboot the app after saving secrets.

## CLI

```bash
python main.py
```

Or pass your own:

```bash
python main.py I always forget my lunch at home
```

## Files

- `state.py` — shared graph state
- `nodes.py` — node functions (the "workers")
- `router.py` — AI routing logic (the "orchestrator")
- `graph.py` — wires nodes + conditional edges + streaming
- `app.py` — transparent Streamlit chat UI
- `main.py` — CLI entry point

## What to learn

1. **StateGraph** — define nodes and state
2. **Conditional edges** — route based on AI decisions (from allowed options)
3. **Orchestration** — separate "what to do" (nodes) from "what next" (router in `router.py`)

Try changing the router prompt in `router.py` or adding a new node in `graph.py` to experiment.
