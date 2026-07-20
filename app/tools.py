"""
The web-search tool the agent can call during research.

Design choice: if no TAVILY_API_KEY is set, we return a clear "search unavailable"
message instead of crashing. Graceful degradation is a real engineering habit:
the demo must still run on a laptop that only has an Anthropic key.
"""

import os
import requests


def search_web(query: str) -> str:
    """Return a short text digest of web results for `query`."""
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        return ("[web search unavailable: no TAVILY_API_KEY configured. "
                "Proceeding using the model's own knowledge.]")

    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "max_results": 4,
                "search_depth": "basic",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return f"[no results for '{query}']"
        # Compress results into a compact digest to save tokens.
        lines = [f"- {r.get('title', '')}: {r.get('content', '')[:200]}" for r in results]
        return f"Search results for '{query}':\n" + "\n".join(lines)
    except Exception as e:
        # Never let a tool failure kill the whole request.
        return f"[web search failed: {e}]"
