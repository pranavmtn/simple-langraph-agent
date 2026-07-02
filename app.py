import html
import json
import os
import uuid
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from beginner_guide import render_beginner_guide
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
        margin-bottom: 4px;
        white-space: nowrap;
    }
    .trace-card {
        border-left: 4px solid #6366f1;
        padding: 0.75rem 1rem;
        margin-bottom: 0.75rem;
        background: #f8fafc;
        border-radius: 0 8px 8px 0;
    }
    .ai-flow-banner {
        background: #fff7ed;
        border: 1px solid #fdba74;
        color: #9a3412;
        padding: 0.55rem 0.8rem;
        border-radius: 8px;
        font-weight: 600;
        margin: 0.4rem 0 0.8rem 0;
    }
    .visit-flow-wrap {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.35rem;
        margin: 0.25rem 0 0.75rem 0;
    }
    .visit-arrow {
        color: #64748b;
        font-weight: 700;
        padding: 0 0.15rem;
    }
    .json-block {
        background: #0f172a;
        color: #e2e8f0;
        border-radius: 8px;
        padding: 0.75rem 0.9rem;
        font-size: 0.82rem;
        line-height: 1.45;
        overflow-x: auto;
        white-space: pre-wrap;
        word-break: break-word;
        margin-bottom: 0.75rem;
    }
    .json-label {
        font-weight: 600;
        margin: 0.35rem 0 0.25rem 0;
    }
    .live-pulse {
        animation: pulse 1.2s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.45; }
    }
    #visit-order-section {
        scroll-margin-top: 5rem;
    }
    .visit-order-highlight {
        animation: visit-order-glow 1.2s ease-in-out 2;
    }
    @keyframes visit-order-glow {
        0%, 100% { background: transparent; }
        50% { background: #eef2ff; border-radius: 8px; }
    }
    .desktop-hood {
        display: block;
    }
    .mobile-hood {
        display: none;
    }
    @media (max-width: 900px) {
        .desktop-hood {
            display: none;
        }
        .mobile-hood {
            display: block;
        }
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
    if "mobile_hood_open" not in st.session_state:
        st.session_state.mobile_hood_open = False


def badge(node: str, active: bool = False) -> str:
    color = NODE_COLORS.get(node, "#64748b")
    pulse = " live-pulse" if active else ""
    label = NODE_LABELS.get(node, node)
    return (
        f'<span class="node-badge{pulse}" style="background:{color};">{label}</span>'
    )


def scroll_to_visit_order(highlight: bool = False):
    """Smooth-scroll the main page to the Visit order section."""
    highlight_class = "visit-order-highlight" if highlight else ""
    components.html(
        f"""
        <script>
            (function() {{
                const doc = window.parent.document;
                const el = doc.getElementById("visit-order-section");
                if (!el) return;
                el.classList.add("{highlight_class}");
                el.scrollIntoView({{ behavior: "smooth", block: "start" }});
            }})();
        </script>
        """,
        height=0,
    )


def render_json_block(label: str, data: dict):
    """Full-width JSON block with wrapping (no cramped side-by-side columns)."""
    st.markdown(f'<div class="json-label">{label}</div>', unsafe_allow_html=True)
    payload = html.escape(json.dumps(data, indent=2, ensure_ascii=False))
    st.markdown(f'<pre class="json-block">{payload}</pre>', unsafe_allow_html=True)


def render_visit_order(visited: list[str]):
    """Render visit path as wrapping badges instead of one long horizontal line."""
    if not visited:
        st.write("—")
        return

    parts = []
    for index, node in enumerate(visited):
        parts.append(badge(node))
        if index < len(visited) - 1:
            parts.append('<span class="visit-arrow">→</span>')

    st.markdown(
        f'<div class="visit-flow-wrap">{"".join(parts)}</div>',
        unsafe_allow_html=True,
    )


def summarize_tokens(trace_steps: list[dict]) -> dict[str, int]:
    totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    for step in trace_steps:
        usage = step.get("token_usage", {}) or {}
        totals["input_tokens"] += int(usage.get("input_tokens", 0) or 0)
        totals["output_tokens"] += int(usage.get("output_tokens", 0) or 0)
        totals["total_tokens"] += int(usage.get("total_tokens", 0) or 0)
    return totals


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

        if ai:
            st.markdown(
                '<div class="ai-flow-banner">AI decided the flow → '
                f'<code>{chosen}</code></div>',
                unsafe_allow_html=True,
            )

        st.caption(
            f"Allowed edges: `{', '.join(allowed)}` · "
            f"Chosen: `{chosen}` · "
            f"{'AI decision' if ai else 'Only valid option'}"
        )
    else:
        st.caption(f"Worker node: `{node}`")

    usage = step.get("token_usage", {}) or {}
    st.caption(
        "Tokens — "
        f"input: `{usage.get('input_tokens', 0)}`, "
        f"output: `{usage.get('output_tokens', 0)}`, "
        f"total: `{usage.get('total_tokens', 0)}`"
    )

    render_json_block("Input (state read)", step.get("input", {}))
    render_json_block("Output (state written)", step.get("output", {}))


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

    highlight = "visit-order-highlight" if status.startswith(("Starting", "Running")) else ""
    st.markdown(
        f'<div id="visit-order-section" class="{highlight}"></div>',
        unsafe_allow_html=True,
    )
    st.markdown("**Visit order**")
    if visited:
        render_visit_order(visited)
    else:
        st.write("—")

    st.markdown("**Token usage (this run)**")
    run_tokens = summarize_tokens(trace_steps)
    tcol1, tcol2, tcol3 = st.columns(3)
    tcol1.metric("Input", f"{run_tokens['input_tokens']}")
    tcol2.metric("Output", f"{run_tokens['output_tokens']}")
    tcol3.metric("Total", f"{run_tokens['total_tokens']}")

    st.markdown("**Live shared state**")
    state_view = {
        "problem": running_state.get("problem", ""),
        "brainstormed_ideas": running_state.get("brainstormed_ideas", []),
        "prioritized_ideas": running_state.get("prioritized_ideas", []),
        "action_steps": running_state.get("action_steps", []),
        "reflected": running_state.get("reflected", False),
        "final_answer": running_state.get("final_answer", ""),
    }
    render_json_block("Current state snapshot", state_view)

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


def update_debug_panels(
    debug_placeholder,
    mobile_debug_placeholder,
    visited,
    trace_steps,
    running_state,
    status,
    active_node=None,
):
    save_debug(visited, trace_steps, running_state, status, active_node)
    with debug_placeholder.container():
        render_debug_panel(visited, trace_steps, active_node, running_state, status)
    with mobile_debug_placeholder.container():
        render_debug_panel(visited, trace_steps, active_node, running_state, status)


def run_chat_turn(prompt: str, chat_placeholder, debug_placeholder, mobile_debug_placeholder):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with chat_placeholder.container():
        render_messages()

    visited: list[str] = []
    trace_steps: list[dict] = []
    running_state: dict = {"problem": prompt}
    active_node: str | None = None
    final_answer = ""

    update_debug_panels(
        debug_placeholder,
        mobile_debug_placeholder,
        visited,
        trace_steps,
        running_state,
        "Starting graph...",
        active_node,
    )
    scroll_to_visit_order(highlight=True)

    for event in stream_agent(prompt, thread_id=str(uuid.uuid4())):
        if event["type"] == "node_start":
            active_node = event["node"]
            running_state = event["state"]
            status = f"Running `{active_node}`..."
            update_debug_panels(
                debug_placeholder,
                mobile_debug_placeholder,
                visited,
                trace_steps,
                running_state,
                status,
                active_node,
            )

        elif event["type"] == "node_end":
            active_node = None
            visited = event.get("visited", visited)
            running_state = event["state"]
            trace = event.get("trace")
            if trace:
                trace_steps.append(trace)

            status = f"Finished `{event['node']}`"
            update_debug_panels(
                debug_placeholder,
                mobile_debug_placeholder,
                visited,
                trace_steps,
                running_state,
                status,
                active_node,
            )
            if len(visited) == 1:
                scroll_to_visit_order(highlight=True)

        elif event["type"] == "complete":
            running_state = event["state"]
            visited = event.get("visited", visited)
            trace_steps = running_state.get("execution_trace", trace_steps)
            final_answer = running_state.get("final_answer", "")

            update_debug_panels(
                debug_placeholder,
                mobile_debug_placeholder,
                visited,
                trace_steps,
                running_state,
                "Graph complete",
                None,
            )

    if not final_answer:
        final_answer = "Sorry — the graph did not produce a final answer."

    st.session_state.messages.append({"role": "assistant", "content": final_answer})
    st.session_state.runs.append(
        {
            "problem": prompt,
            "visited": visited,
            "trace": trace_steps,
            "token_usage": summarize_tokens(trace_steps),
            "final_answer": final_answer,
        }
    )

    with chat_placeholder.container():
        render_messages()


def render_messages():
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def render_chat_page():
    st.title("LangGraph Transparent Chatbot")
    st.markdown(
        "Describe a simple life problem. Watch **every node**, **router decision**, "
        "and **state change** live in Under the Hood."
    )

    dbg = st.session_state.debug

    st.subheader("Chat")
    chat_placeholder = st.empty()
    with chat_placeholder.container():
        render_messages()

    if not st.session_state.messages:
        st.info("Try: *I keep forgetting to drink water during the day*")

    st.markdown('<div class="desktop-hood">', unsafe_allow_html=True)
    debug_placeholder = st.empty()
    with debug_placeholder.container():
        render_debug_panel(
            dbg["visited"],
            dbg["trace_steps"],
            dbg["active_node"],
            dbg["running_state"],
            dbg["status"],
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="mobile-hood">', unsafe_allow_html=True)
    with st.expander(
        "Under the Hood (tap to open)",
        expanded=st.session_state.mobile_hood_open,
    ):
        mobile_debug_placeholder = st.empty()
        with mobile_debug_placeholder.container():
            render_debug_panel(
                dbg["visited"],
                dbg["trace_steps"],
                dbg["active_node"],
                dbg["running_state"],
                dbg["status"],
            )
    st.markdown("</div>", unsafe_allow_html=True)

    prompt = st.chat_input("Describe a simple life problem...")
    if prompt:
        st.session_state.mobile_hood_open = True
        run_chat_turn(
            prompt,
            chat_placeholder,
            debug_placeholder,
            mobile_debug_placeholder,
        )
        st.rerun()


def main():
    init_session()

    with st.sidebar:
        st.header("Menu")
        page = st.radio(
            "Navigation",
            ["Chat", "Beginner Guide"],
            label_visibility="collapsed",
        )
        st.divider()

        if page == "Chat":
            st.markdown("**Quick steps**")
            st.markdown(
                """
                1. Your message becomes `state["problem"]`
                2. **Router** picks the next node
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
                st.session_state.debug = {
                    "visited": [],
                    "trace_steps": [],
                    "running_state": {},
                    "status": "Idle — waiting for your message.",
                    "active_node": None,
                }
                st.rerun()

            if st.session_state.runs:
                st.divider()
                st.markdown("**Token usage (full chat)**")
                chat_tokens = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
                for run in st.session_state.runs:
                    usage = run.get("token_usage", {}) or {}
                    chat_tokens["input_tokens"] += int(usage.get("input_tokens", 0) or 0)
                    chat_tokens["output_tokens"] += int(usage.get("output_tokens", 0) or 0)
                    chat_tokens["total_tokens"] += int(usage.get("total_tokens", 0) or 0)
                c1, c2, c3 = st.columns(3)
                c1.metric("Input", f"{chat_tokens['input_tokens']}")
                c2.metric("Output", f"{chat_tokens['output_tokens']}")
                c3.metric("Total", f"{chat_tokens['total_tokens']}")

            if st.session_state.runs:
                st.divider()
                st.markdown("**Last run export**")
                st.download_button(
                    "Download trace JSON",
                    data=json.dumps(st.session_state.runs[-1], indent=2),
                    file_name="langgraph_trace.json",
                    mime="application/json",
                )

        if page == "Beginner Guide":
            st.markdown("Read how LangGraph and AI routing work in this app.")
            st.markdown("Switch to **Chat** when you're ready to try it.")

    if page == "Beginner Guide":
        render_beginner_guide()
    else:
        render_chat_page()


if __name__ == "__main__":
    main()
