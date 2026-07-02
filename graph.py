import uuid
from collections.abc import Iterator
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from nodes import (
    action_plan_node,
    brainstorm_node,
    clarify_node,
    finalize_node,
    prioritize_node,
    reflect_node,
)
from router import router_node
from state import AgentState, Route

MAX_STEPS = 12
_checkpointer = MemorySaver()
_compiled_graph = None


def pick_route(state: AgentState) -> Route:
    """Read the route chosen by the router node."""
    return state["next_route"]


def build_graph():
    """Build (or return cached) compiled LangGraph app."""
    global _compiled_graph
    if _compiled_graph is not None:
        return _compiled_graph

    graph = StateGraph(AgentState)

    graph.add_node("clarify", clarify_node)
    graph.add_node("brainstorm", brainstorm_node)
    graph.add_node("prioritize", prioritize_node)
    graph.add_node("action_plan", action_plan_node)
    graph.add_node("reflect", reflect_node)
    graph.add_node("finalize", finalize_node)
    graph.add_node("router", router_node)

    graph.add_edge(START, "router")

    for node_name in ["clarify", "brainstorm", "prioritize", "action_plan", "reflect"]:
        graph.add_edge(node_name, "router")

    graph.add_edge("finalize", END)

    graph.add_conditional_edges(
        "router",
        pick_route,
        {
            "clarify": "clarify",
            "brainstorm": "brainstorm",
            "prioritize": "prioritize",
            "action_plan": "action_plan",
            "reflect": "reflect",
            "finalize": "finalize",
            "end": END,
        },
    )

    _compiled_graph = graph.compile(checkpointer=_checkpointer)
    return _compiled_graph


def make_initial_state(problem: str) -> AgentState:
    return {
        "messages": [],
        "problem": problem,
        "next_route": "brainstorm",
        "brainstormed_ideas": [],
        "prioritized_ideas": [],
        "action_steps": [],
        "final_answer": "",
        "reflected": False,
        "execution_trace": [],
    }


def merge_state(current: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Merge a node update into a running state snapshot for the UI."""
    merged = dict(current)
    for key, value in update.items():
        if key == "messages":
            merged.setdefault("messages", [])
            merged["messages"] = [*merged["messages"], *value]
        elif key == "execution_trace":
            merged.setdefault("execution_trace", [])
            merged["execution_trace"] = [*merged["execution_trace"], *value]
        else:
            merged[key] = value
    return merged


def stream_agent(problem: str, thread_id: str | None = None) -> Iterator[dict[str, Any]]:
    """
    Stream graph execution events for live UI transparency.

    Yields:
        {"type": "node_start", "node": str, "state": dict}
        {"type": "node_end", "node": str, "update": dict, "trace": dict, "state": dict}
        {"type": "complete", "state": dict, "visited": list[str]}
    """
    app = build_graph()
    initial = make_initial_state(problem)
    thread_id = thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": MAX_STEPS}

    running_state = dict(initial)
    visited: list[str] = []

    for event in app.stream(initial, config=config, stream_mode="updates"):
        for node_name, update in event.items():
            visited.append(node_name)
            trace = update.get("execution_trace", [{}])[-1] if update.get("execution_trace") else {}

            yield {
                "type": "node_start",
                "node": node_name,
                "state": dict(running_state),
            }

            running_state = merge_state(running_state, update)

            yield {
                "type": "node_end",
                "node": node_name,
                "update": update,
                "trace": trace,
                "state": dict(running_state),
                "visited": list(visited),
            }

    final_state = app.get_state(config).values
    yield {
        "type": "complete",
        "state": final_state,
        "visited": visited,
    }


def run_agent(problem: str) -> AgentState:
    """Run the graph on one life problem."""
    final_state = None
    for event in stream_agent(problem):
        if event["type"] == "complete":
            final_state = event["state"]
    return final_state or make_initial_state(problem)
