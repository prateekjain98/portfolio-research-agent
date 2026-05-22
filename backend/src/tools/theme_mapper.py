"""Theme-to-company mapper.

Takes investment themes extracted from a thesis and maps each to
specific public companies using web search. This separates
theme extraction (LLM) from company identification (search + parsing).
"""

from __future__ import annotations

import re
from typing import Dict, List, Set

from src.tools.web_search import WebSearchTool


# Known theme → ticker mappings for common AI infrastructure bottlenecks.
# These are used as anchors; web search expands beyond them.
THEME_ANCHORS: Dict[str, List[str]] = {
    "fuel cell": ["BE", "PLUG", "FCEL"],
    "data center power": ["BE", "VST", "CEG"],
    "gpu cloud": ["CRWV"],
    "optical interconnect": ["LITE", "COHR"],
    "memory storage": ["SNDK", "WDC", "MU"],
    "bitcoin miner": ["IREN", "CORZ", "CLSK", "RIOT"],
    "data center operator": ["APLD", "DLR", "EQIX"],
    "nuclear power": ["CEG", "BWXT", "CCJ"],
    "semiconductor foundry": ["INTC", "TSM", "GFS"],
}


class ThemeMapper:
    """Maps abstract investment themes to specific public company tickers."""

    def __init__(self) -> None:
        self.search = WebSearchTool()

    def map_themes(self, themes: List[str], max_results_per_theme: int = 3) -> List[dict]:
        """
        For each theme, search for public companies and return tickers.
        Deduplicates across themes.
        """
        seen_tickers: Set[str] = set()
        mappings = []

        for theme in themes:
            tickers = self._tickers_for_theme(theme, max_results_per_theme)
            for t in tickers:
                t_upper = t.upper()
                if t_upper in seen_tickers:
                    continue
                seen_tickers.add(t_upper)
                mappings.append({
                    "ticker": t_upper,
                    "theme": theme,
                })
        return mappings

    def _tickers_for_theme(self, theme: str, max_results: int) -> List[str]:
        """Search web for companies matching a theme and extract tickers."""
        # 1. Check anchor mappings first
        anchors = self._anchor_tickers(theme)

        # 2. Web search for additional companies
        query = f'public companies {theme} stock ticker'
        try:
            results = self.search.run(query, max_results=max_results)
        except Exception:
            results = []

        extracted = self._extract_tickers_from_results(results)

        # Merge anchors + extracted, prefer anchors
        combined = anchors + [t for t in extracted if t not in anchors]
        return combined[:max_results]

    def _anchor_tickers(self, theme: str) -> List[str]:
        """Return known tickers for a theme keyword."""
        theme_lower = theme.lower()
        tickers = []
        for keyword, tickers_list in THEME_ANCHORS.items():
            if keyword in theme_lower:
                tickers.extend(tickers_list)
        return tickers

    @staticmethod
    def _extract_tickers_from_results(results) -> List[str]:
        """Extract ticker symbols from search result snippets."""
        tickers = []
        ticker_pattern = re.compile(r'\b([A-Z]{1,5})\b')
        for r in results:
            text = f"{r.title} {r.snippet}"
            found = ticker_pattern.findall(text)
            # Filter out common false positives
            filtered = [t for t in found if t not in {"AI", "CEO", "USA", "NYSE", "NASDAQ", "ETF", "IPO", "GDP", "FED", "SEC"}]
            tickers.extend(filtered)
        return tickers
