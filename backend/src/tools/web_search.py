"""Web search: Tavily if key present, else DuckDuckGo via ddgs."""

from __future__ import annotations

import os
from typing import List

import requests

from src.models.schemas import WebSearchResult


class WebSearchTool:
    def run(self, query: str, max_results: int = 5) -> List[WebSearchResult]:
        if os.getenv("TAVILY_API_KEY"):
            return self._tavily(query, max_results)
        return self._ddg(query, max_results)

    def _tavily(self, query: str, max_results: int) -> List[WebSearchResult]:
        try:
            resp = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": os.getenv("TAVILY_API_KEY"),
                    "query": query,
                    "max_results": max_results,
                },
                timeout=30,
            )
            resp.raise_for_status()
            return [
                WebSearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    snippet=r.get("content", ""),
                    source_reliability=3,
                )
                for r in resp.json().get("results", [])
            ]
        except Exception as e:
            print(f"[WebSearch] Tavily failed: {e}, falling back to DDG")
            return self._ddg(query, max_results)

    def _ddg(self, query: str, max_results: int) -> List[WebSearchResult]:
        import time

        last_error = None
        for attempt in range(1, 4):
            try:
                from ddgs import DDGS

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
                last_error = e
                print(f"[WebSearch] DDG attempt {attempt}/3 failed: {e}")
                if attempt < 3:
                    time.sleep(2 ** attempt)  # 2s, 4s backoff
        print(f"[WebSearch] DDG all retries exhausted. Last error: {last_error}")
        return []
