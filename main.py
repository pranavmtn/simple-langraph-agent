import random
import sys

from dotenv import load_dotenv

from graph import MAX_STEPS, build_graph, make_initial_state

load_dotenv()

# Windows terminals may default to cp1252; UTF-8 avoids emoji/unicode crashes.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Small built-in problems so the agent runs automatically without input.
SAMPLE_PROBLEMS = [
    "I keep forgetting to drink water during the day.",
    "My desk gets messy by Friday and I waste time looking for things.",
    "I want to read more but always end up scrolling my phone at night.",
    "I feel rushed every morning and leave the house stressed.",
    "I never know what to cook for dinner and order takeout too often.",
]


def run_agent_with_trace(problem: str):
    """Run the graph and return final state plus the node visit order."""
    app = build_graph()
    initial = make_initial_state(problem)

    config = {"configurable": {"thread_id": "demo"}, "recursion_limit": MAX_STEPS}
    visited: list[str] = []

    for event in app.stream(initial, config=config):
        for node_name in event:
            visited.append(node_name)

    result = app.get_state(config).values
    return result, visited


def main():
    if len(sys.argv) > 1:
        problem = " ".join(sys.argv[1:])
    else:
        problem = random.choice(SAMPLE_PROBLEMS)

    print("=" * 60)
    print("Simple LangGraph Life Problem Solver")
    print("AI chooses which node runs next (orchestration demo)")
    print("=" * 60)
    print(f"\nInput (state['problem']): {problem}\n")
    print("Running graph...\n")

    result, visited = run_agent_with_trace(problem)

    print("-" * 60)
    print("NODE PATH (order the graph visited)")
    print("-" * 60)
    print(" -> ".join(visited))
    print()

    print("-" * 60)
    print("GRAPH TRACE (each node's output)")
    print("-" * 60)
    for message in result["messages"]:
        print(message.content)
        print()

    print("-" * 60)
    print("FINAL ANSWER (from finalize node -> state['final_answer'])")
    print("-" * 60)
    if result.get("final_answer"):
        print(result["final_answer"])
    else:
        print("No final answer produced within step limit.")


if __name__ == "__main__":
    main()
