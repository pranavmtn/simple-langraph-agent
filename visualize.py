"""Save a visual diagram of the LangGraph agent."""

from pathlib import Path

from graph import build_graph

OUTPUT_DIR = Path(__file__).parent


def save_graph_diagram() -> tuple[Path, Path]:
    graph = build_graph().get_graph()

    mermaid_path = OUTPUT_DIR / "graph.mmd"
    mermaid_path.write_text(graph.draw_mermaid(), encoding="utf-8")

    png_path = OUTPUT_DIR / "graph.png"
    graph.draw_mermaid_png(output_file_path=str(png_path))

    return mermaid_path, png_path


if __name__ == "__main__":
    mmd, png = save_graph_diagram()
    print(f"Mermaid saved: {mmd}")
    print(f"PNG saved: {png}")
