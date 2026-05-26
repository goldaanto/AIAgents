import sys
import argparse
from datetime import datetime
from pathlib import Path
from .graph import build_graph

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("topic", help="Video topic for thumbnail design")
    parser.add_argument("--stream", action="store_true", help="Stream node updates")
    parser.add_argument("--target", type=int, default=8)
    parser.add_argument("--max-iter", type=int, default=3)
    args = parser.parse_args()
    
    # Create output directory
    safe_topic = args.topic[:40].replace(" ", "_").replace("/", "-")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("outputs") / f"{timestamp}_{safe_topic}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    initial_state = {
        "topic": args.topic,
        "search_summary": "",
        "current_prompt": "",
        "current_image_path": "",
        "rating": 0,
        "critique": "",
        "iteration": 0,
        "history": [],
        "target_rating": args.target,
        "max_iterations": args.max_iter,
        "output_dir": str(output_dir),
    }
    
    graph = build_graph()
    
    if args.stream:
        for event in graph.stream(initial_state):
            node_name = list(event.keys())[0]
            print(f"\n--- Node: {node_name} ---")
    else:
        result = graph.invoke(initial_state)
        print(f"\n🎉 Done! Output in: {output_dir}")
        print(f"   Best rating: {result['rating']}/10")

if __name__ == "__main__":
    main()