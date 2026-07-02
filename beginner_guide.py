from pathlib import Path

import streamlit as st

from router import NODE_COLORS, NODE_LABELS

GRAPH_IMAGE = Path(__file__).parent / "graph.png"


def render_beginner_guide():
    st.title("Beginner Guide")
    st.markdown(
        "A simple explanation of how this chatbot uses **LangGraph** and where **AI** fits in."
    )

    st.info(
        "**One-line summary:** LangGraph runs the workflow; AI both performs each step "
        "and decides which step to run next (within allowed routes)."
    )

    st.header("Think of it like a small factory")
    st.markdown(
        """
| Concept | In this app |
|---------|-------------|
| **Factory layout** | LangGraph graph (nodes + edges) |
| **Whiteboard** | Shared state (`state["problem"]`, ideas, steps, answer) |
| **Workers** | Nodes like `brainstorm`, `action_plan`, `reflect` |
| **Manager** | `router` node that picks the next step |
| **AI** | Does the thinking inside workers **and** helps the manager choose |
        """
    )

    st.header("What LangGraph does")
    st.markdown(
        """
LangGraph does **not** answer in one shot. It runs a graph step by step:

```text
START → router → worker → router → worker → ... → finalize → END
```

When you send a chat message:

1. Your text becomes `state["problem"]`
2. LangGraph runs nodes one by one
3. Each node reads and updates shared state
4. The `finalize` node writes the answer you see in chat
        """
    )

    if GRAPH_IMAGE.exists():
        st.image(str(GRAPH_IMAGE), caption="Graph structure — dashed lines are AI-chosen paths")

    st.header("The two roles of AI")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. AI as workers")
        st.markdown(
            """
Each worker node calls the LLM for **one focused job**:

- **brainstorm** → generate ideas
- **prioritize** → pick the best ideas
- **action_plan** → turn ideas into steps
- **reflect** → check if the plan is realistic
- **finalize** → write the friendly chat reply
            """
        )

    with col2:
        st.subheader("2. AI as router (manager)")
        st.markdown(
            """
After most nodes, control returns to **router**.

The router:

1. Checks what is already done
2. Builds a list of **allowed next nodes**
3. Asks AI to pick **one** route from that list

AI never picks from infinite options — only from safe, valid paths.
            """
        )

    st.header("Example visit order")
    st.code(
        "router → brainstorm → router → prioritize → router → "
        "action_plan → router → reflect → router → finalize",
        language=None,
    )
    st.caption("You see one clean answer in chat, but many steps happened under the hood.")

    st.header("Why not one big AI prompt?")
    st.markdown(
        """
A single prompt asks one model to do everything at once. This design splits work:

- **Workers** = focused tasks (better quality, easier to debug)
- **Router** = dynamic flow based on current state
- **LangGraph** = reliable execution you can watch live

That is why the right panel can show visit order, per-step input/output, and token usage.
        """
    )

    st.header("Node reference")
    for node, label in NODE_LABELS.items():
        color = NODE_COLORS.get(node, "#64748b")
        st.markdown(
            f'<span style="color:{color};font-weight:600;">●</span> **{label}** (`{node}`)',
            unsafe_allow_html=True,
        )

    st.header("Files to explore")
    st.markdown(
        """
| File | Purpose |
|------|---------|
| `state.py` | Shared memory passed between nodes |
| `nodes.py` | Worker nodes (AI tasks) |
| `router.py` | Manager + allowed routes logic |
| `graph.py` | Wires nodes and conditional edges |
| `app.py` | Chat UI + live transparency panel |
        """
    )

    st.success("Tip: Send a message in **Chat**, then watch **Visit order** update on the right.")
