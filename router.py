from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from state import AgentState, Route
from token_usage import extract_token_usage

ROUTER_SYSTEM = """You are the orchestrator for a simple life-problem solver.

You will be given the current state and a list of ALLOWED next routes.
Pick exactly ONE route from that allowed list only.

Route meanings:
- clarify: problem is vague; ask one short clarifying question
- brainstorm: generate practical ideas
- prioritize: narrow a long brainstorm list to the best options
- action_plan: turn ideas into concrete, doable steps
- reflect: sanity-check the plan before finishing
- finalize: write the final answer

Reply with ONLY the route name from the allowed list."""


NODE_LABELS = {
    "router": "Router (AI picks next step)",
    "clarify": "Clarify",
    "brainstorm": "Brainstorm",
    "prioritize": "Prioritize",
    "action_plan": "Action Plan",
    "reflect": "Reflect",
    "finalize": "Finalize",
}

NODE_COLORS = {
    "router": "#f59e0b",
    "clarify": "#8b5cf6",
    "brainstorm": "#3b82f6",
    "prioritize": "#06b6d4",
    "action_plan": "#10b981",
    "reflect": "#f97316",
    "finalize": "#22c55e",
}


def create_router():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)


def node_was_executed(state: AgentState, node_name: str) -> bool:
    return any(
        step.get("node") == node_name
        for step in state.get("execution_trace", [])
    )


def allowed_routes(state: AgentState) -> list[Route]:
    """Compute which edges are valid from the current node."""
    if state.get("final_answer"):
        return ["end"]

    if not state.get("brainstormed_ideas"):
        routes: list[Route] = ["brainstorm"]
        if not node_was_executed(state, "clarify"):
            routes.append("clarify")
        return routes

    if state.get("action_steps"):
        if state.get("reflected"):
            return ["finalize"]
        return ["reflect"]

    if len(state.get("brainstormed_ideas", [])) >= 4 and not state.get("prioritized_ideas"):
        return ["prioritize", "action_plan"]

    return ["action_plan"]


def decide_next_route(state: AgentState, llm=None) -> tuple[Route, dict[str, int]]:
    """Ask the LLM which allowed node should run next."""
    options = allowed_routes(state)
    if len(options) == 1:
        return options[0], {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    llm = llm or create_router()
    context = f"""Problem: {state["problem"]}

Brainstorm ideas ({len(state.get("brainstormed_ideas", []))}):
{state.get("brainstormed_ideas", []) or "none yet"}

Prioritized ideas:
{state.get("prioritized_ideas", []) or "none yet"}

Action steps:
{state.get("action_steps", []) or "none yet"}

Reflected already: {"yes" if state.get("reflected") else "no"}

ALLOWED next routes (pick one): {", ".join(options)}
"""

    response = llm.invoke(
        [
            SystemMessage(content=ROUTER_SYSTEM),
            HumanMessage(content=context),
        ]
    )
    token_usage = extract_token_usage(response)

    route = response.content.strip().lower().replace('"', "").replace("'", "")
    if route in options:
        return route, token_usage  # type: ignore[return-value]

    return options[0], token_usage


def router_node(state: AgentState) -> dict:
    """Orchestrator node: decide and record the next route."""
    options = allowed_routes(state)
    chosen, token_usage = decide_next_route(state)
    ai_decision = len(options) > 1

    return {
        "next_route": chosen,
        "execution_trace": [
            {
                "node": "router",
                "type": "routing",
                "input": {
                    "problem": state["problem"],
                    "brainstormed_ideas": state.get("brainstormed_ideas", []),
                    "prioritized_ideas": state.get("prioritized_ideas", []),
                    "action_steps": state.get("action_steps", []),
                    "reflected": state.get("reflected", False),
                },
                "output": {
                    "allowed_routes": options,
                    "chosen_route": chosen,
                    "ai_decision": ai_decision,
                },
                "token_usage": token_usage,
            }
        ],
    }
