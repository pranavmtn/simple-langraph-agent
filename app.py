import json
import os
import uuid
from pathlib import Path

import streamlit as st
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
SESSION_TOKEN_LIMIT = int(os.getenv("SESSION_TOKEN_LIMIT", "10000"))

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
    .live-pulse {
        animation: pulse 1.2s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.45; }
    }
    .desktop-hood {
        display: block;
    }
    .mobile-hood {
        display: none;
    }
    .desktop-trace {
        display: block;
    }
    .mobile-trace {
        display: none;
    }
    @media (max-width: 900px) {
        .desktop-hood {
            display: none;
        }
        .mobile-hood {
            display: block;
        }
        .desktop-trace {
            display: none;
        }
        .mobile-trace {
            display: block;
        }
    }
    .sidebar-erase-wrap {
        margin-top: 1.5rem;
        padding-top: 1rem;
        border-top: 1px solid #e2e8f0;
    }
    .sidebar-token-line {
        font-size: 0.78rem;
        color: #64748b;
        line-height: 1.4;
        margin: 0;
    }
    .under-hood-highlight {
        background: #f0fdf4;
        border: 1px solid #dcfce7;
        border-radius: 10px;
        padding: 0.65rem 0.75rem;
    }
    .mobile-hood div[data-testid="stExpander"] {
        background: #f0fdf4;
        border: 1px solid #dcfce7;
        border-radius: 10px;
        overflow: hidden;
    }
    .mobile-hood div[data-testid="stExpander"] details {
        background: #f0fdf4;
        border: none;
    }
    .mobile-hood div[data-testid="stExpander"] summary {
        background: #f0fdf4;
        border-radius: 10px;
        font-weight: 600;
    }
    .mobile-hood div[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        background: #f7fef9;
        border-top: 1px solid #dcfce7;
        padding-top: 0.5rem;
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


def session_tokens_remaining() -> int:
    return max(0, SESSION_TOKEN_LIMIT - get_session_token_usage()["total_tokens"])


def session_limit_reached() -> bool:
    return get_session_token_usage()["total_tokens"] >= SESSION_TOKEN_LIMIT


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
    st.session_state.mobile_hood_open = False


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
        st.warning(f"{session_tokens_remaining():,} tokens left this session.")


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

    render_json_expander("Input (state read)", step.get("input", {}))
    render_json_expander("Output (state written)", step.get("output", {}))


def render_debug_summary(
    trace_steps: list[dict],
    running_state: dict,
    status: str,
):
    """Compact right-column panel: tokens + live state only."""
    st.subheader("Under the Hood")
    st.caption(status)

    st.markdown("**Token usage (this run)**")
    run_tokens = summarize_tokens(trace_steps)
    tcol1, tcol2, tcol3 = st.columns(3)
    tcol1.metric("Input", f"{run_tokens['input_tokens']}")
    tcol2.metric("Output", f"{run_tokens['output_tokens']}")
    tcol3.metric("Total", f"{run_tokens['total_tokens']}")

    session_used = get_session_token_usage()["total_tokens"]
    st.caption(
        f"Session total: `{session_used:,}` / `{SESSION_TOKEN_LIMIT:,}` tokens"
    )

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


def render_step_trace(
    trace_steps: list[dict],
    active_node: str | None,
    status: str,
):
    """Full-width step-by-step trace shown below the chat area."""
    st.markdown("**Step-by-step trace**")
    if not trace_steps:
        st.info("Send a message to watch nodes run live.")
        return

    for i, step in enumerate(trace_steps, start=1):
        is_active = active_node == step.get("node") and status.startswith("Running")
        with st.expander(
            f"Step {i}: {NODE_LABELS.get(step.get('node', ''), step.get('node', '?'))}",
            expanded=is_active,
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


def update_chat_placeholders(*placeholders):
    for placeholder in placeholders:
        with placeholder.container():
            render_messages()


def update_debug_panels(
    debug_placeholder,
    mobile_debug_placeholder,
    desktop_trace_placeholder,
    mobile_trace_placeholder,
    visited,
    trace_steps,
    running_state,
    status,
    active_node=None,
):
    save_debug(visited, trace_steps, running_state, status, active_node)
    with debug_placeholder.container():
        render_debug_summary(trace_steps, running_state, status)
    with mobile_debug_placeholder.container():
        render_debug_summary(trace_steps, running_state, status)
    with desktop_trace_placeholder.container():
        render_step_trace(trace_steps, active_node, status)
    with mobile_trace_placeholder.container():
        render_step_trace(trace_steps, active_node, status)


def run_chat_turn(
    prompt: str,
    chat_placeholders: list,
    debug_placeholder,
    mobile_debug_placeholder,
    desktop_trace_placeholder,
    mobile_trace_placeholder,
):
    st.session_state.messages.append({"role": "user", "content": prompt})
    update_chat_placeholders(*chat_placeholders)

    visited: list[str] = []
    trace_steps: list[dict] = []
    running_state: dict = {"problem": prompt}
    active_node: str | None = None
    final_answer = ""

    update_debug_panels(
        debug_placeholder,
        mobile_debug_placeholder,
        desktop_trace_placeholder,
        mobile_trace_placeholder,
        visited,
        trace_steps,
        running_state,
        "Starting graph...",
        active_node,
    )

    for event in stream_agent(prompt, thread_id=str(uuid.uuid4())):
        if event["type"] == "node_start":
            active_node = event["node"]
            running_state = event["state"]
            status = f"Running `{active_node}`..."
            update_debug_panels(
                debug_placeholder,
                mobile_debug_placeholder,
                desktop_trace_placeholder,
                mobile_trace_placeholder,
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
                desktop_trace_placeholder,
                mobile_trace_placeholder,
                visited,
                trace_steps,
                running_state,
                status,
                active_node,
            )

        elif event["type"] == "complete":
            running_state = event["state"]
            visited = event.get("visited", visited)
            trace_steps = running_state.get("execution_trace", trace_steps)
            final_answer = running_state.get("final_answer", "")

            update_debug_panels(
                debug_placeholder,
                mobile_debug_placeholder,
                desktop_trace_placeholder,
                mobile_trace_placeholder,
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

    update_chat_placeholders(*chat_placeholders)


def render_messages():
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def render_chat_page():
    st.title("LangGraph Transparent Chatbot")
    st.markdown(
        "Describe a simple life problem. Watch **every node**, **router decision**, "
        "and **state change** live on the right."
    )

    dbg = st.session_state.debug

    st.markdown('<div class="desktop-hood">', unsafe_allow_html=True)
    chat_col, debug_col = st.columns([1, 1], gap="large")

    with chat_col:
        st.subheader("Chat")
        desktop_chat_placeholder = st.empty()
        with desktop_chat_placeholder.container():
            render_messages()
        if not st.session_state.messages:
            st.info("Try: *I keep forgetting to drink water during the day*")

    with debug_col:
        st.markdown('<div class="under-hood-highlight">', unsafe_allow_html=True)
        debug_placeholder = st.empty()
        with debug_placeholder.container():
            render_debug_summary(
                dbg["trace_steps"],
                dbg["running_state"],
                dbg["status"],
            )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="desktop-trace">', unsafe_allow_html=True)
    desktop_trace_placeholder = st.empty()
    with desktop_trace_placeholder.container():
        render_step_trace(
            dbg["trace_steps"],
            dbg["active_node"],
            dbg["status"],
        )
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="mobile-hood">', unsafe_allow_html=True)
    st.subheader("Chat")
    mobile_chat_placeholder = st.empty()
    with mobile_chat_placeholder.container():
        render_messages()
    if not st.session_state.messages:
        st.info("Try: *I keep forgetting to drink water during the day*")

    with st.expander(
        "Under the Hood",
        expanded=st.session_state.mobile_hood_open,
    ):
        mobile_debug_placeholder = st.empty()
        with mobile_debug_placeholder.container():
            render_debug_summary(
                dbg["trace_steps"],
                dbg["running_state"],
                dbg["status"],
            )

    st.markdown('<div class="mobile-trace">', unsafe_allow_html=True)
    mobile_trace_placeholder = st.empty()
    with mobile_trace_placeholder.container():
        render_step_trace(
            dbg["trace_steps"],
            dbg["active_node"],
            dbg["status"],
        )
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if session_limit_reached():
        st.error(
            f"Session token limit reached ({SESSION_TOKEN_LIMIT:,} tokens). "
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
                        f"This session has reached the {SESSION_TOKEN_LIMIT:,} token limit. "
                        "Tap the erase button at the bottom of the sidebar to reset."
                    ),
                }
            )
            update_chat_placeholders(desktop_chat_placeholder, mobile_chat_placeholder)
            st.rerun()
            return

        st.session_state.mobile_hood_open = True
        run_chat_turn(
            prompt,
            [desktop_chat_placeholder, mobile_chat_placeholder],
            debug_placeholder,
            mobile_debug_placeholder,
            desktop_trace_placeholder,
            mobile_trace_placeholder,
        )
        st.rerun()


def main():
    init_session()

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
