import json
import os
import time
import uuid
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from beginner_guide import render_beginner_guide
from graph import stream_agent
from router import NODE_COLORS, NODE_LABELS
from ui_styles import inject_layout_css

load_dotenv()

# Streamlit Community Cloud stores secrets in the dashboard (not .env).
if "OPENAI_API_KEY" not in os.environ:
    try:
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
    except (KeyError, FileNotFoundError):
        pass

GRAPH_IMAGE = Path(__file__).parent / "graph.png"
SESSION_TOKEN_LIMIT = int(os.getenv("SESSION_TOKEN_LIMIT", "10000"))
STEP_RUNNING_PAUSE_SEC = float(os.getenv("STEP_RUNNING_PAUSE_SEC", "0.65"))
STEP_FINISHED_PAUSE_SEC = float(os.getenv("STEP_FINISHED_PAUSE_SEC", "0.25"))

st.set_page_config(
    page_title="LangGraph Transparent Chat",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
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
    color = NODE_COLORS.get(node, "#94a3b8")
    pulse = " live-pulse" if active else ""
    label = NODE_LABELS.get(node, node)
    return (
        f'<span class="node-badge{pulse}" '
        f'style="color:{color};border-color:{color};">{label}</span>'
    )


def render_page_header(title: str, subtitle: str):
    st.markdown(
        f"""
        <div class="page-header">
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_under_hood_divider():
    st.markdown('<hr class="under-hood-divider">', unsafe_allow_html=True)


def render_running_banner(status: str):
    if not status.startswith(("Starting", "Running")):
        return
    st.markdown(
        f"""
        <div class="graph-running-banner">
          <span class="graph-running-dot"></span>
          <span>{status}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_step_running_placeholder(node: str):
    label = NODE_LABELS.get(node, node)
    st.markdown(
        f"""
        <div class="step-running-label">
          {badge(node, active=True)}
          <span>Running <strong>{label}</strong>…</span>
        </div>
        <div class="step-running-bar">
          <div class="step-running-bar-fill"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_thinking_message():
    with st.chat_message("assistant"):
        st.markdown(
            """
            <div class="assistant-thinking">
              <span class="thinking-dot"></span>
              <span class="thinking-dot"></span>
              <span class="thinking-dot"></span>
              <span class="thinking-label">Running the graph…</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_json_expander(label: str, data: dict, expanded: bool = False):
    """Proper formatted JSON inside a collapsible expander."""
    with st.expander(label, expanded=expanded):
        st.json(data)


def summarize_tokens(trace_steps: list[dict]) -> dict[str, int]:
    totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    for step in trace_steps:
        usage = step.get("token_usage", {}) or {}
        totals["input_tokens"] += int(usage.get("input_tokens", 0) or 0)
        totals["output_tokens"] += int(usage.get("output_tokens", 0) or 0)
        totals["total_tokens"] += int(usage.get("total_tokens", 0) or 0)
    return totals


def get_session_token_usage() -> dict[str, int]:
    """Total token usage across all runs in this browser session."""
    totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    for run in st.session_state.runs:
        usage = run.get("token_usage", {}) or {}
        totals["input_tokens"] += int(usage.get("input_tokens", 0) or 0)
        totals["output_tokens"] += int(usage.get("output_tokens", 0) or 0)
        totals["total_tokens"] += int(usage.get("total_tokens", 0) or 0)
    return totals


def session_limit_reached() -> bool:
    return get_session_token_usage()["total_tokens"] >= SESSION_TOKEN_LIMIT


def session_depth_label() -> str:
    """Opaque session load hint — no token counts exposed to users."""
    used = get_session_token_usage()["total_tokens"]
    ratio = used / SESSION_TOKEN_LIMIT if SESSION_TOKEN_LIMIT else 0
    if ratio >= 1:
        return "trace depth · saturated"
    if ratio >= 0.8:
        return "trace depth · thinning"
    if ratio >= 0.5:
        return "trace depth · warming"
    if ratio > 0:
        return "trace depth · active"
    return "trace depth · idle"


def erase_session():
    st.session_state.messages = []
    st.session_state.runs = []
    st.session_state.debug = {
        "visited": [],
        "trace_steps": [],
        "running_state": {},
        "status": "Idle — waiting for your message.",
        "active_node": None,
    }


def render_sidebar_erase_button():
    st.markdown('<div class="sidebar-erase-wrap">', unsafe_allow_html=True)
    if st.button("🗑️", key="erase_session", help="Erase session", use_container_width=True):
        erase_session()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_session_limit_warning():
    """Show limit warnings only when needed (no budget progress bar)."""
    if session_limit_reached():
        st.error("Session limit reached. Use erase below to reset.")
    elif get_session_token_usage()["total_tokens"] >= SESSION_TOKEN_LIMIT * 0.8:
        st.warning("Pipeline headroom is getting low — consider erasing the session soon.")


def render_compact_token_breakdown():
    """Small one-line token summary for the sidebar."""
    if not st.session_state.runs:
        return

    tokens = get_session_token_usage()
    st.markdown(
        f'<p class="sidebar-token-line">'
        f"In <b>{tokens['input_tokens']}</b> · "
        f"Out <b>{tokens['output_tokens']}</b> · "
        f"Total <b>{tokens['total_tokens']}</b>"
        f"</p>",
        unsafe_allow_html=True,
    )


def render_trace_step(step: dict, step_num: int, active: bool = False):
    node = step.get("node", "unknown")
    st.markdown(
        f'<div class="trace-step-header">'
        f"{badge(node, active=active)}"
        f'<span class="trace-step-num">----- step {step_num}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )

    if step.get("type") == "routing":
        output = step.get("output", {})
        allowed = output.get("allowed_routes", [])
        chosen = output.get("chosen_route", "?")
        ai = output.get("ai_decision", False)

        if ai:
            chosen_color = NODE_COLORS.get(chosen, "#94a3b8")
            chosen_label = NODE_LABELS.get(chosen, chosen)
            st.markdown(
                '<div class="ai-flow-line">'
                "<span>AI decided the flow</span>"
                '<span class="ai-flow-arrow">→</span>'
                f'<span class="node-badge" style="color:{chosen_color};'
                f'border-color:{chosen_color};">{chosen_label}</span>'
                "</div>",
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

    render_json_expander("Input (state read)", step.get("input", {}))
    render_json_expander("Output (state written)", step.get("output", {}))


def render_debug_summary(
    trace_steps: list[dict],
    running_state: dict,
    status: str,
    active_node: str | None = None,
):
    """Under the Hood panel: tokens, live state, and step-by-step trace."""
    st.subheader("Under the Hood")
    render_running_banner(status)
    if not status.startswith(("Starting", "Running")):
        st.caption(status)

    st.markdown("**Token usage (this run)**")
    run_tokens = summarize_tokens(trace_steps)
    tcol1, tcol2, tcol3 = st.columns(3)
    tcol1.metric("Input", f"{run_tokens['input_tokens']}")
    tcol2.metric("Output", f"{run_tokens['output_tokens']}")
    tcol3.metric("Total", f"{run_tokens['total_tokens']}")

    st.caption(f"Pipeline status · `{session_depth_label()}`")

    st.markdown("**Live shared state**")
    state_view = {
        "problem": running_state.get("problem", ""),
        "brainstormed_ideas": running_state.get("brainstormed_ideas", []),
        "prioritized_ideas": running_state.get("prioritized_ideas", []),
        "action_steps": running_state.get("action_steps", []),
        "reflected": running_state.get("reflected", False),
        "final_answer": running_state.get("final_answer", ""),
    }
    render_json_expander(
        "Current state snapshot",
        state_view,
        expanded=status.startswith(("Starting", "Running")),
    )

    render_step_trace(trace_steps, active_node, status)


def render_step_trace(
    trace_steps: list[dict],
    active_node: str | None,
    status: str,
):
    """Step-by-step trace inside the Under the Hood panel."""
    st.markdown("**Step-by-step trace**")
    running = bool(active_node and status.startswith("Running"))

    if not trace_steps and not running:
        st.info("Send a message to watch nodes run live.")
        return

    for i, step in enumerate(trace_steps, start=1):
        is_active = running and active_node == step.get("node")
        marker_class = (
            "trace-step-marker trace-step-running"
            if is_active
            else "trace-step-marker trace-step-done"
        )
        st.markdown(f'<div class="{marker_class}"></div>', unsafe_allow_html=True)
        with st.expander(
            f"Step {i}: {NODE_LABELS.get(step.get('node', ''), step.get('node', '?'))}",
            expanded=is_active,
        ):
            render_trace_step(step, i, active=is_active)

    if running and (
        not trace_steps or trace_steps[-1].get("node") != active_node
    ):
        step_num = len(trace_steps) + 1
        label = NODE_LABELS.get(active_node or "", active_node or "?")
        st.markdown(
            '<div class="trace-step-marker trace-step-running"></div>',
            unsafe_allow_html=True,
        )
        with st.expander(f"Step {step_num}: {label} — running…", expanded=True):
            render_step_running_placeholder(active_node or "")


def save_debug(visited, trace_steps, running_state, status, active_node=None):
    st.session_state.debug = {
        "visited": visited,
        "trace_steps": trace_steps,
        "running_state": running_state,
        "status": status,
        "active_node": active_node,
    }


def update_debug_panel(
    debug_placeholder,
    visited,
    trace_steps,
    running_state,
    status,
    active_node=None,
):
    save_debug(visited, trace_steps, running_state, status, active_node)
    with debug_placeholder.container():
        render_debug_summary(
            trace_steps, running_state, status, active_node=active_node
        )


def run_chat_turn(
    prompt: str,
    chat_placeholder,
    debug_placeholder,
):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with chat_placeholder.container():
        render_messages()
        render_thinking_message()

    visited: list[str] = []
    trace_steps: list[dict] = []
    running_state: dict = {"problem": prompt}
    active_node: str | None = None
    final_answer = ""

    update_debug_panel(
        debug_placeholder,
        visited,
        trace_steps,
        running_state,
        "Starting graph...",
        active_node,
    )
    time.sleep(0.3)

    for event in stream_agent(prompt, thread_id=str(uuid.uuid4())):
        if event["type"] == "node_start":
            active_node = event["node"]
            running_state = event["state"]
            status = f"Running {NODE_LABELS.get(active_node, active_node)}…"
            update_debug_panel(
                debug_placeholder,
                visited,
                trace_steps,
                running_state,
                status,
                active_node,
            )
            time.sleep(STEP_RUNNING_PAUSE_SEC)

        elif event["type"] == "node_end":
            visited = event.get("visited", visited)
            running_state = event["state"]
            trace = event.get("trace")
            if trace:
                trace_steps.append(trace)

            status = f"Finished {NODE_LABELS.get(event['node'], event['node'])}"
            update_debug_panel(
                debug_placeholder,
                visited,
                trace_steps,
                running_state,
                status,
                None,
            )
            time.sleep(STEP_FINISHED_PAUSE_SEC)
            active_node = None

        elif event["type"] == "complete":
            running_state = event["state"]
            visited = event.get("visited", visited)
            trace_steps = running_state.get("execution_trace", trace_steps)
            final_answer = running_state.get("final_answer", "")

            update_debug_panel(
                debug_placeholder,
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
    render_page_header(
        "LangGraph Transparent Chatbot",
        "Describe a simple life problem. Watch every node, router decision, "
        "and state change live on the right.",
    )

    dbg = st.session_state.debug

    chat_col, debug_col = st.columns([1, 1], gap="large")

    with chat_col:
        st.subheader("Chat")
        chat_placeholder = st.empty()
        with chat_placeholder.container():
            render_messages()
        if not st.session_state.messages:
            st.info("Try: *I keep forgetting to drink water during the day*")

    with debug_col:
        render_under_hood_divider()
        debug_placeholder = st.empty()
        with debug_placeholder.container():
            render_debug_summary(
                dbg["trace_steps"],
                dbg["running_state"],
                dbg["status"],
                active_node=dbg["active_node"],
            )

    if session_limit_reached():
        st.error(
            "Pipeline headroom exhausted. "
            "Use the erase button in the sidebar to start a new session."
        )

    prompt = st.chat_input(
        "Describe a simple life problem..."
        if not session_limit_reached()
        else "Session limit reached — erase session to continue"
    )
    if prompt:
        if session_limit_reached():
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": (
                        "This session has reached its pipeline limit. "
                        "Tap the erase button at the bottom of the sidebar to reset."
                    ),
                }
            )
            with chat_placeholder.container():
                render_messages()
            st.rerun()
            return

        run_chat_turn(
            prompt,
            chat_placeholder,
            debug_placeholder,
        )
        st.rerun()


def main():
    init_session()
    inject_layout_css()

    with st.sidebar:
        st.header("Menu")
        page = st.radio(
            "Navigation",
            ["Chat", "The Story Behind It"],
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

            st.divider()
            render_session_limit_warning()
            render_compact_token_breakdown()

            if st.session_state.runs:
                st.divider()
                st.markdown("**Last run export**")
                st.download_button(
                    "Download trace JSON",
                    data=json.dumps(st.session_state.runs[-1], indent=2),
                    file_name="langgraph_trace.json",
                    mime="application/json",
                )

        if page == "The Story Behind It":
            st.markdown("See how **LangGraph orchestration** works.")
            st.markdown("Switch to **Chat** when you're ready to experiment.")

        render_sidebar_erase_button()

    if page == "The Story Behind It":
        render_beginner_guide()
    else:
        render_chat_page()


if __name__ == "__main__":
    main()
