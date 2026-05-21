"""
Tool: Web Search
Pluggable search backend. Defaults to Tavily if API key is present,
falls back to a simple DuckDuckGo scrape if not.
"""

from __future__ import annotations

import os
from typing import List

import requests

from src.models.schemas import WebSearchResult


class WebSearchTool:
    """Search the web for recent news and analysis about a company/theme."""

    def run(self, query: str, max_results: int = 5) -> List[WebSearchResult]:
        """
        Execute web search for *query*.

        Prefers Tavily API if TAVILY_API_KEY is set.
        Falls back to DuckDuckGo HTML scraping (no API key needed).
        """
        if os.getenv("TAVILY_API_KEY"):
            return self._search_tavily(query, max_results)
        return self._search_duckduckgo(query, max_results)

    def _search_tavily(
        self, query: str, max_results: int
    ) -> List[WebSearchResult]:
        """Tavily API search — higher quality results."""
        url = "https://api.tavily.com/search"
        headers = {"Content-Type": "application/json"}
        payload = {
            "api_key": os.getenv("TAVILY_API_KEY"),
            "query": query,
            "max_results": max_results,
            "include_answer": False,
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            results = []
            for r in data.get("results", []):
                results.append(
                    WebSearchResult(
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        snippet=r.get("content", ""),
                        source_reliability=3,  # Default: news site
                    )
                )
            return results
        except Exception as e:
            # Graceful fallback
            print(f"[WebSearch] Tavily failed ({e}), falling back to DDG...")
            return self._search_duckduckgo(query, max_results)

    def _search_duckduckgo(
        self, query: str, max_results: int
    ) -> List[WebSearchResult]:
        """
        DuckDuckGo Lite HTML scraping — no API key required.
        Less reliable but works out of the box.
        """
        try:
            from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                raw = list(ddgs.text(query, max_results=max_results))

            return [
                WebSearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                    source_reliability=2,
                )
                for r in raw
            ]
        except Exception as e:
            print(f"[WebSearch] DDG also failed: {e}")
            return []
