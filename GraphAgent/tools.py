from tavily import TavilyClient
import os

def search_web(query: str) -> str:
    """Search the web and return a summary string."""
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    results = client.search(query=query, max_results=5)
    
    summaries = []
    for r in results.get("results", []):
        summaries.append(f"- {r['title']}: {r['content'][:200]}")
    
    return "\n".join(summaries) if summaries else "No results found."