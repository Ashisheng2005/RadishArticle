import os
from typing import Literal

from langchain.tools import tool

from app.config import get_settings


@tool
def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news"] = "general",
) -> str:
    """Search the web for background research. Returns summarized results."""
    settings = get_settings()
    if settings.tavily_api_key:
        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=settings.tavily_api_key)
            resp = client.search(query, max_results=max_results)
            return str(resp)
        except Exception as e:
            return f"Tavily search failed: {e}"

    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r.get('title', '')}\n   {r.get('body', '')}\n   {r.get('href', '')}")
        return "\n".join(lines)
    except Exception as e:
        return f"Search unavailable: {e}. Set TAVILY_API_KEY or check network."
