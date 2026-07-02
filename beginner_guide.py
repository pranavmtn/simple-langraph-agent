from pathlib import Path

import streamlit as st

from router import NODE_COLORS, NODE_LABELS

GRAPH_IMAGE = Path(__file__).parent / "graph.png"


def render_beginner_guide():
    st.title("The Story Behind It")
    st.markdown("See how **LangGraph orchestration** works.")

    st.markdown(
        """
### Why this exists

The goal is to understand:

- how graphs connect nodes and edges
- how shared state flows between steps
- how AI can **orchestrate** which node runs next

A simple life-problem solver makes the graph easy to follow step by step.
        """
    )

    st.markdown(
        """
### The mental model

Instead of one giant AI prompt, imagine a **small team**:

- A **manager** (`router`) who decides what happens next
- **Specialists** (`brainstorm`, `action_plan`, `reflect`, …) who each do one job
- A shared **whiteboard** (`state`) everyone reads and updates

LangGraph is the factory floor plan. AI is the brain inside each worker — and the manager.
        """
    )

    st.info(
        "**In one sentence:** LangGraph runs the workflow; AI does the work inside each step "
        "and helps pick the next step from allowed routes."
    )

    st.header("How a message travels")

    st.markdown(
        """
1. You type a problem in **Chat**
2. It becomes `state["problem"]` on the shared whiteboard
3. The **router** picks the next node
4. A **worker** runs, then updates state
5. Repeat until **finalize** writes the answer

```text
START → router → worker → router → worker → ... → finalize → END
```
        """
    )

    if GRAPH_IMAGE.exists():
        st.image(
            str(GRAPH_IMAGE),
            caption="The graph — solid lines are fixed; dashed lines are AI-chosen paths",
        )

    st.header("Why AI shows up twice")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("As a worker")
        st.markdown(
            """
Each node asks AI for **one focused task**:

- brainstorm ideas
- pick the best ones
- turn them into steps
- sanity-check the plan
- write the final reply
            """
        )

    with col2:
        st.subheader("As the manager")
        st.markdown(
            """
The **router** asks AI: *given the current state, what should we do next?*

It only chooses from **allowed routes** — never random jumps.
That is the orchestration pattern this sandbox is built to teach.
            """
        )

    st.header("A real path through the graph")
    st.code(
        "router → brainstorm → router → prioritize → router → "
        "action_plan → router → reflect → router → finalize",
        language=None,
    )
    st.caption(
        "One answer in chat — but many steps you can inspect in Under the Hood."
    )

    st.header("What to watch while learning")

    st.markdown(
        """
Use the UI as a **debug window**:

- **Under the Hood** — token usage and live shared state
- **Step-by-step trace** — each node's input/output JSON
- **AI decided the flow** — when the router chose the path

The 10K session token cap keeps experiments cheap while you iterate.
        """
    )

    st.header("Meet the nodes")
    for node, label in NODE_LABELS.items():
        color = NODE_COLORS.get(node, "#64748b")
        st.markdown(
            f'<span style="color:{color};font-weight:600;">●</span> **{label}** (`{node}`)',
            unsafe_allow_html=True,
        )

    st.header("Files to explore")
    st.markdown(
        """
| File | What to learn from it |
|------|------------------------|
| `state.py` | Shared memory between nodes |
| `nodes.py` | Worker nodes (AI tasks) |
| `router.py` | Orchestrator + allowed routes |
| `graph.py` | Wiring nodes and conditional edges |
| `app.py` | Chat UI + live transparency |
        """
    )

    st.success(
        "Go to **Chat**, try a small life problem, and watch the graph work in real time."
    )
