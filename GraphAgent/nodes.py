import os
import base64
import shutil
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from openai import OpenAI

from .state import ThumbnailState, IterationRecord
from .prompts import PROMPT_WRITER_SYSTEM, PROMPT_WRITER_REVISION_SYSTEM, CRITIC_SYSTEM
from .tools import search_web


# ── Pydantic model for structured critic output ──────────────────────────────
class CriticOutput(BaseModel):
    rating: int
    critique: str


# ── Node 1: web_search ───────────────────────────────────────────────────────
def web_search(state: ThumbnailState) -> dict:
    print(f"\n🔍 [web_search] Searching for: {state['topic']}")
    query = f"YouTube thumbnail ideas hooks visual style for: {state['topic']}"
    summary = search_web(query)
    print(f"   Found {len(summary)} chars of context")
    return {"search_summary": summary}


# ── Node 2: prompt_writer ────────────────────────────────────────────────────
def prompt_writer(state: ThumbnailState) -> dict:
    print(f"\n✍️  [prompt_writer] Writing prompt (iteration {state.get('iteration', 0) + 1})")
    llm = ChatOpenAI(model="gpt-4o", temperature=0.9)
    
    is_revision = state.get("iteration", 0) > 0
    system = PROMPT_WRITER_REVISION_SYSTEM if is_revision else PROMPT_WRITER_SYSTEM
    
    user_content = f"Video topic: {state['topic']}\n\nWeb search context:\n{state.get('search_summary', '')}"
    
    if is_revision:
        user_content += f"\n\nPrevious prompt:\n{state.get('current_prompt', '')}"
        user_content += f"\n\nCritic's feedback (score {state.get('rating', 0)}/10):\n{state.get('critique', '')}"
        user_content += "\n\nRevise the prompt to fix every issue the critic mentioned."
    
    response = llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=user_content)
    ])
    
    prompt = response.content.strip()
    print(f"   Prompt: {prompt[:100]}...")
    return {"current_prompt": prompt}


# ── Node 3: generator ────────────────────────────────────────────────────────
def generator(state: ThumbnailState) -> dict:
    iteration = state.get("iteration", 0) + 1
    print(f"\n🎨 [generator] Generating image (iteration {iteration})")
    
    client = OpenAI()
    response = client.images.generate(
        model="gpt-image-1",
        prompt=state["current_prompt"],
        size="1024x1024",
        quality="medium",
        n=1,
    )
    
    # Download and save the image
    import requests
    
    
    b64 = response.data[0].b64_json
    img_data = base64.b64decode(b64)
    
    output_dir = state["output_dir"]
    image_path = str(Path(output_dir) / f"iter_{iteration}.png")
    Path(image_path).write_bytes(img_data)
    
    print(f"   Saved to: {image_path}")
    return {"current_image_path": image_path, "iteration": iteration}


# ── Node 4: critic ───────────────────────────────────────────────────────────
def critic(state: ThumbnailState) -> dict:
    print(f"\n🧐 [critic] Evaluating iteration {state['iteration']}")
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2)
    structured_llm = llm.with_structured_output(CriticOutput)
    
    # Read image as base64
    img_b64 = base64.b64encode(Path(state["current_image_path"]).read_bytes()).decode()
    
    response = structured_llm.invoke([
        SystemMessage(content=CRITIC_SYSTEM),
        HumanMessage(content=[
            {"type": "text", "text": f"Evaluate this YouTube thumbnail for the topic: '{state['topic']}'"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
        ])
    ])
    
    print(f"   Rating: {response.rating}/10")
    print(f"   Critique: {response.critique[:100]}...")
    
    # Append to history
    record: IterationRecord = {
        "iteration": state["iteration"],
        "prompt": state["current_prompt"],
        "image_path": state["current_image_path"],
        "rating": response.rating,
        "critique": response.critique,
    }
    
    return {
        "rating": response.rating,
        "critique": response.critique,
        "history": [record],  # The reducer will append this
    }


# ── Node 5: saver ────────────────────────────────────────────────────────────
def saver(state: ThumbnailState) -> dict:
    print(f"\n💾 [saver] Saving best result...")
    
    output_dir = Path(state["output_dir"])
    history = state["history"]
    
    # Find best rated iteration
    best = max(history, key=lambda r: r["rating"])
    
    # Copy best image as final.png
    final_path = output_dir / "final.png"
    shutil.copy(best["image_path"], final_path)
    
    # Write report.md
    report_lines = [
        f"# YouTube Thumbnail Design Report",
        f"\n**Topic:** {state['topic']}",
        f"\n**Total Iterations:** {state['iteration']}",
        f"\n**Best Rating:** {best['rating']}/10 (Iteration {best['iteration']})",
        f"\n---\n",
        f"## Iteration History\n",
    ]
    
    for record in history:
        report_lines += [
            f"### Iteration {record['iteration']}",
            f"**Rating:** {record['rating']}/10",
            f"\n**Prompt:**",
            f"```\n{record['prompt']}\n```",
            f"\n**Critique:** {record['critique']}",
            f"\n**Image:** `{Path(record['image_path']).name}`\n",
            "---\n",
        ]
    
    report_path = output_dir / "report.md"
    report_path.write_text("\n".join(report_lines))
    
    print(f"   Final image: {final_path}")
    print(f"   Report: {report_path}")
    return {}


# ── Conditional edge: should_continue ────────────────────────────────────────
def should_continue(state: ThumbnailState) -> str:
    rating = state.get("rating", 0)
    iteration = state.get("iteration", 0)
    target = state.get("target_rating", 8)
    max_iter = state.get("max_iterations", 4)
    
    if rating >= target:
        print(f"\n✅ Rating {rating} >= target {target}. Stopping.")
        return "saver"
    elif iteration >= max_iter:
        print(f"\n⏹️  Hit max iterations ({max_iter}). Stopping.")
        return "saver"
    else:
        print(f"\n🔁 Rating {rating} < target {target}. Looping back...")
        return "prompt_writer"