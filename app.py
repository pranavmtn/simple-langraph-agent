import json
import os
import uuid
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from graph import stream_agent
from router import NODE_COLORS, NODE_LABELS

load_dotenv()

# Streamlit Community Cloud stores secrets in the dashboard (not .env).
if "OPENAI_API_KEY" not in os.environ:
    try:
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
    except (KeyError, FileNotFoundError):
        pass

GRAPH_IMAGE = Path(__file__).parent / "graph.png"

st.set_page_config(
    page_title="LangGraph Transparent Chat",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .node-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        color: white;
        font-weight: 600;
        font-size: 0.85rem;
        margin-right: 6px;
    }
    .trace-card {
        border-left: 4px solid #6366f1;
        padding: 0.75rem 1rem;
        margin-bottom: 0.75rem;
        background: #f8fafc;
        border-radius: 0 8px 8px 0;
    }
    .live-pulse {
        animation: pulse 1.2s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.45; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "runs" not in st.session_state:
        st.session_state.runs = []
    if "debug" not in st.session_state:
        st.session_state.debug = {
            "visited": [],
            "trace_steps": [],
            "running_state": {},
            "status": "Idle — waiting for your message.",
            "active_node": None,
        }


def badge(node: str, active: bool = False) -> str:
    color = NODE_COLORS.get(node, "#64748b")
    pulse = " live-pulse" if active else ""
    label = NODE_LABELS.get(node, node)
    return (
        f'<span class="node-badge{pulse}" style="background:{color};">{label}</span>'
    )


def render_trace_step(step: dict, step_num: int, active: bool = False):
    node = step.get("node", "unknown")
    color = NODE_COLORS.get(node, "#64748b")
    st.markdown(
        f'<div class="trace-card" style="border-left-color:{color};">'
        f"{badge(node, active=active)} <strong>Step {step_num}</strong>"
        f"</div>",
        unsafe_allow_html=True,
    )

    if step.get("type") == "routing":
        output = step.get("output", {})
        allowed = output.get("allowed_routes", [])
        chosen = output.get("chosen_route", "?")
        ai = output.get("ai_decision", False)

        st.caption(
            f"Allowed edges: `{', '.join(allowed)}`  →  "
            f"**Chosen:** `{chosen}` "
            f"({'AI decision' if ai else 'only option'})"
        )
    else:
        st.caption(f"Worker node: `{node}`")

    col_in, col_out = st.columns(2)
    with col_in:
        st.markdown("**Input (state read)**")
        st.json(step.get("input", {}))
    with col_out:
        st.markdown("**Output (state written)**")
        st.json(step.get("output", {}))


def render_debug_panel(
    visited: list[str],
    trace_steps: list[dict],
    active_node: str | None,
    running_state: dict,
    status: str,
):
    st.subheader("Under the Hood")
    st.caption(status)

    if GRAPH_IMAGE.exists():
        st.image(str(GRAPH_IMAGE), caption="Graph structure (dashed = AI-chosen edges)")

    st.markdown("**Active node**")
    if active_node:
        st.markdown(badge(active_node, active=True), unsafe_allow_html=True)
    else:
        st.write("Waiting...")

    st.markdown("**Visit order**")
    if visited:
        path = " → ".join(visited)
        st.code(path, language=None)
    else:
        st.write("—")

    st.markdown("**Live shared state**")
    state_view = {
        "problem": running_state.get("problem", ""),
        "brainstormed_ideas": running_state.get("brainstormed_ideas", []),
        "prioritized_ideas": running_state.get("prioritized_ideas", []),
        "action_steps": running_state.get("action_steps", []),
        "reflected": running_state.get("reflected", False),
        "final_answer": running_state.get("final_answer", ""),
    }
    st.json(state_view)

    st.markdown("**Step-by-step trace**")
    if not trace_steps:
        st.info("Send a message to watch nodes run live.")
    else:
        for i, step in enumerate(trace_steps, start=1):
            is_active = active_node == step.get("node") and status.startswith("Running")
            with st.expander(
                f"Step {i}: {NODE_LABELS.get(step.get('node', ''), step.get('node', '?'))}",
                expanded=is_active or i == len(trace_steps),
            ):
                render_trace_step(step, i, active=is_active)


def save_debug(visited, trace_steps, running_state, status, active_node=None):
    st.session_state.debug = {
        "visited": visited,
        "trace_steps": trace_steps,
        "running_state": running_state,
        "status": status,
        "active_node": active_node,
    }


def run_chat_turn(prompt: str, chat_placeholder, debug_placeholder):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with chat_placeholder.container():
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    visited: list[str] = []
    trace_steps: list[dict] = []
    running_state: dict = {"problem": prompt}
    active_node: str | None = None
    final_answer = ""

    save_debug(visited, trace_steps, running_state, "Starting graph...")
    with debug_placeholder.container():
        render_debug_panel(visited, trace_steps, active_node, running_state, "Starting graph...")

    for event in stream_agent(prompt, thread_id=str(uuid.uuid4())):
        if event["type"] == "node_start":
            active_node = event["node"]
            running_state = event["state"]
            status = f"Running `{active_node}`..."
            save_debug(visited, trace_steps, running_state, status, active_node)
            with debug_placeholder.container():
                render_debug_panel(visited, trace_steps, active_node, running_state, status)

        elif event["type"] == "node_end":
            active_node = None
            visited = event.get("visited", visited)
            running_state = event["state"]
            trace = event.get("trace")
            if trace:
                trace_steps.append(trace)

            status = f"Finished `{event['node']}`"
            save_debug(visited, trace_steps, running_state, status, active_node)
            with debug_placeholder.container():
                render_debug_panel(visited, trace_steps, active_node, running_state, status)

        elif event["type"] == "complete":
            running_state = event["state"]
            visited = event.get("visited", visited)
            trace_steps = running_state.get("execution_trace", trace_steps)
            final_answer = running_state.get("final_answer", "")

            save_debug(visited, trace_steps, running_state, "Graph complete")
            with debug_placeholder.container():
                render_debug_panel(visited, trace_steps, None, running_state, "Graph complete")

    if not final_answer:
        final_answer = "Sorry — the graph did not produce a final answer."

    st.session_state.messages.append({"role": "assistant", "content": final_answer})
    st.session_state.runs.append(
        {
            "problem": prompt,
            "visited": visited,
            "trace": trace_steps,
            "final_answer": final_answer,
        }
    )

    with chat_placeholder.container():
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])


def main():
    init_session()

    st.title("LangGraph Transparent Chatbot")
    st.markdown(
        "Describe a simple life problem. Watch **every node**, **router decision**, "
        "and **state change** live on the right."
    )

    with st.sidebar:
        st.header("How it works")
        st.markdown(
            """
            1. Your message becomes `state["problem"]`
            2. **Router** picks the next node (AI chooses from allowed edges)
            3. Worker nodes read/write shared state
            4. **Finalize** writes the chat reply
            """
        )
        st.markdown("**Nodes**")
        for node, label in NODE_LABELS.items():
            color = NODE_COLORS.get(node, "#64748b")
            st.markdown(
                f'<span style="color:{color};font-weight:600;">●</span> {label}',
                unsafe_allow_html=True,
            )

        if st.button("Clear chat"):
            st.session_state.messages = []
            st.session_state.runs = []
            st.rerun()

        if st.session_state.runs:
            st.divider()
            st.markdown("**Last run export**")
            st.download_button(
                "Download trace JSON",
                data=json.dumps(st.session_state.runs[-1], indent=2),
                file_name="langgraph_trace.json",
                mime="application/json",
            )

    chat_col, debug_col = st.columns([1, 1], gap="large")

    with chat_col:
        st.subheader("Chat")
        chat_placeholder = st.empty()
        with chat_placeholder.container():
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        if not st.session_state.messages:
            st.info("Try: *I keep forgetting to drink water during the day*")

    with debug_col:
        debug_placeholder = st.empty()
        dbg = st.session_state.debug
        with debug_placeholder.container():
            render_debug_panel(
                dbg["visited"],
                dbg["trace_steps"],
                dbg["active_node"],
                dbg["running_state"],
                dbg["status"],
            )

    prompt = st.chat_input("Describe a simple life problem...")
    if prompt:
        run_chat_turn(prompt, chat_placeholder, debug_placeholder)


if __name__ == "__main__":
    main()
