from pathlib import Path

import streamlit as st

from router import NODE_COLORS, NODE_LABELS

GRAPH_IMAGE = Path(__file__).parent / "graph.png"


def render_beginner_guide():
    st.title("The Story Behind It")
    st.markdown(
        "Why this app exists, what problem it solves, and how LangGraph + AI work together."
    )

    st.markdown(
        """
### The problem

Most chatbots feel like a black box. You type a question, wait, and get an answer —
but you never see *how* the AI got there.

I built this app to **learn LangGraph** in a hands-on way: a simple life-problem solver
where you can watch every step live.
        """
    )

    st.markdown(
        """
### The idea

Instead of one giant AI prompt doing everything, imagine a **small team**:

- A **manager** (`router`) who decides what happens next
- **Specialists** (`brainstorm`, `action_plan`, `reflect`, …) who each do one job well
- A shared **whiteboard** (`state`) everyone reads and updates

That team is LangGraph. The intelligence inside each person is AI.
        """
    )

    st.info(
        "**In one sentence:** LangGraph runs the workflow; AI does the work inside each step "
        "and helps the manager choose the next step."
    )

    st.header("How a message travels")

    st.markdown(
        """
1. You describe a small everyday problem in **Chat**
2. Your words land on the whiteboard as `state["problem"]`
3. The **router** looks at the board and picks the next move
4. A **worker node** does its job and updates the board
5. Back to the router — repeat until **finalize** writes your answer

```text
START → router → worker → router → worker → ... → finalize → END
```
        """
    )

    if GRAPH_IMAGE.exists():
        st.image(
            str(GRAPH_IMAGE),
            caption="The graph — solid lines are fixed; dashed lines are where AI chooses the path",
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
The **router** asks AI: *given what we know so far, what should we do next?*

It only chooses from **allowed routes** — never random jumps.
That is the orchestration pattern LangGraph is great at teaching.
            """
        )

    st.header("A real path through the graph")
    st.code(
        "router → brainstorm → router → prioritize → router → "
        "action_plan → router → reflect → router → finalize",
        language=None,
    )
    st.caption(
        "You see one friendly answer in chat. Under the Hood shows the full journey."
    )

    st.header("Why transparency matters")

    st.markdown(
        """
This app is a **learning lab**, not just a chatbot.

The right panel shows:

- **Visit order** — which nodes ran, in sequence
- **AI decided the flow** — when the router chose the path
- **Input / output JSON** — what each node read and wrote
- **Token usage** — cost of each step and the whole session (10K limit)

You are not meant to trust the answer blindly. You are meant to **see the machinery**.
        """
    )

    st.header("Meet the nodes")
    for node, label in NODE_LABELS.items():
        color = NODE_COLORS.get(node, "#64748b")
        st.markdown(
            f'<span style="color:{color};font-weight:600;">●</span> **{label}** (`{node}`)',
            unsafe_allow_html=True,
        )

    st.header("Under the hood in code")
    st.markdown(
        """
| File | Role in the story |
|------|-------------------|
| `state.py` | The shared whiteboard |
| `nodes.py` | The specialists |
| `router.py` | The manager + routing rules |
| `graph.py` | The factory floor plan |
| `app.py` | What you see — chat + live trace |
        """
    )

    st.success(
        "Ready? Go to **Chat**, ask something like *I keep forgetting to drink water*, "
        "and watch the story unfold on the right."
    )
