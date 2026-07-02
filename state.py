import operator
from typing import Annotated, Literal, TypedDict

from langgraph.graph.message import add_messages


Route = Literal[
    "clarify",
    "brainstorm",
    "prioritize",
    "action_plan",
    "reflect",
    "finalize",
    "end",
]


class AgentState(TypedDict):
    """Shared state passed between every node in the graph."""

    messages: Annotated[list, add_messages]
    problem: str
    next_route: Route
    brainstormed_ideas: list[str]
    prioritized_ideas: list[str]
    action_steps: list[str]
    final_answer: str
    reflected: bool
    execution_trace: Annotated[list[dict], operator.add]
