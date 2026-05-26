from .graph import build_graph
from pathlib import Path

def main():
    graph = build_graph()
    png_bytes = graph.get_graph().draw_mermaid_png()
    Path("graph.png").write_bytes(png_bytes)
    print("✅ graph.png saved!")

if __name__ == "__main__":
    main()