from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from state import AgentState


def create_llm():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.4)


def clarify_node(state: AgentState) -> dict:
    """Ask one short question when the problem is too vague."""
    llm = create_llm()
    response = llm.invoke(
        f"The user said: '{state['problem']}'\n"
        "Ask ONE short clarifying question to understand the real issue."
    )
    return {
        "messages": [AIMessage(content=f"[Clarify] {response.content}")],
        "execution_trace": [
            {
                "node": "clarify",
                "type": "worker",
                "input": {"problem": state["problem"]},
                "output": {"question": response.content},
            }
        ],
    }


def brainstorm_node(state: AgentState) -> dict:
    """Generate practical ideas for the life problem."""
    llm = create_llm()
    response = llm.invoke(
        f"Life problem: {state['problem']}\n\n"
        "List 3 to 5 simple, practical ideas. "
        "Return one idea per line, no numbering."
    )
    ideas = [line.strip("- ").strip() for line in response.content.splitlines() if line.strip()]
    return {
        "brainstormed_ideas": ideas,
        "messages": [AIMessage(content=f"[Brainstorm]\n" + "\n".join(f"- {i}" for i in ideas))],
        "execution_trace": [
            {
                "node": "brainstorm",
                "type": "worker",
                "input": {"problem": state["problem"]},
                "output": {"brainstormed_ideas": ideas},
            }
        ],
    }


def prioritize_node(state: AgentState) -> dict:
    """Pick the best 1-2 ideas from the brainstorm."""
    llm = create_llm()
    ideas = "\n".join(f"- {idea}" for idea in state["brainstormed_ideas"])
    response = llm.invoke(
        f"Problem: {state['problem']}\n\nIdeas:\n{ideas}\n\n"
        "Pick the best 1-2 ideas for a busy person. One per line."
    )
    picked = [line.strip("- ").strip() for line in response.content.splitlines() if line.strip()]
    return {
        "prioritized_ideas": picked,
        "messages": [AIMessage(content=f"[Prioritize]\n" + "\n".join(f"- {i}" for i in picked))],
        "execution_trace": [
            {
                "node": "prioritize",
                "type": "worker",
                "input": {"brainstormed_ideas": state["brainstormed_ideas"]},
                "output": {"prioritized_ideas": picked},
            }
        ],
    }


def action_plan_node(state: AgentState) -> dict:
    """Turn ideas into concrete next steps."""
    llm = create_llm()
    source = state.get("prioritized_ideas") or state.get("brainstormed_ideas") or []
    ideas = "\n".join(f"- {idea}" for idea in source)
    response = llm.invoke(
        f"Problem: {state['problem']}\n\nWorking ideas:\n{ideas}\n\n"
        "Write 3 small action steps the person can do today or this week. "
        "One step per line."
    )
    steps = [line.strip("- ").strip() for line in response.content.splitlines() if line.strip()]
    return {
        "action_steps": steps,
        "messages": [AIMessage(content=f"[Action Plan]\n" + "\n".join(f"- {s}" for s in steps))],
        "execution_trace": [
            {
                "node": "action_plan",
                "type": "worker",
                "input": {
                    "problem": state["problem"],
                    "ideas": source,
                },
                "output": {"action_steps": steps},
            }
        ],
    }


def reflect_node(state: AgentState) -> dict:
    """Quick sanity check on the plan."""
    llm = create_llm()
    steps = "\n".join(f"- {s}" for s in state["action_steps"])
    response = llm.invoke(
        f"Problem: {state['problem']}\n\nPlan:\n{steps}\n\n"
        "In 2-3 short sentences, say if this plan is realistic. "
        "Suggest one tiny improvement if needed."
    )
    return {
        "messages": [AIMessage(content=f"[Reflect] {response.content}")],
        "reflected": True,
        "execution_trace": [
            {
                "node": "reflect",
                "type": "worker",
                "input": {"action_steps": state["action_steps"]},
                "output": {"reflection": response.content, "reflected": True},
            }
        ],
    }


def finalize_node(state: AgentState) -> dict:
    """Package the final helpful answer."""
    llm = create_llm()
    steps = "\n".join(f"- {s}" for s in state["action_steps"])
    response = llm.invoke(
        f"Problem: {state['problem']}\n\nAction steps:\n{steps}\n\n"
        "Write a friendly final answer in under 120 words. "
        "Include the steps and one encouraging line."
    )
    return {
        "final_answer": response.content,
        "messages": [AIMessage(content=f"[Final Answer]\n{response.content}")],
        "execution_trace": [
            {
                "node": "finalize",
                "type": "worker",
                "input": {"action_steps": state["action_steps"]},
                "output": {"final_answer": response.content},
            }
        ],
    }
