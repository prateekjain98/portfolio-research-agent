"""
Tool: Thesis Synthesizer
Takes raw financial data + web search results and produces a
structured InvestmentThesis via an LLM call.
"""

from __future__ import annotations

import json
import os
from typing import List

from openai import OpenAI

from src.models.schemas import (
    FinancialMetrics,
    InvestmentThesis,
    WebSearchResult,
)


class ThesisBuilderTool:
    """Generates a structured investment thesis from research data."""

    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    def run(
        self,
        query: str,
        financials: FinancialMetrics | None,
        web_results: List[WebSearchResult],
    ) -> InvestmentThesis:
        """
        Synthesize a thesis.

        Uses structured output (response_format) to guarantee schema compliance.
        """
        # Build the context block
        context_parts = [f"User Query: {query}"]

        if financials:
            context_parts.append(
                f"\nFinancial Data for {financials.ticker}:\n"
                + json.dumps(financials.model_dump(exclude_none=True), indent=2)
            )

        if web_results:
            context_parts.append("\nWeb Search Findings:")
            for i, r in enumerate(web_results[:5], 1):
                context_parts.append(
                    f"  {i}. {r.title} ({r.url})\n     {r.snippet[:300]}"
                )

        context = "\n".join(context_parts)

        system_prompt = (
            "You are a senior equity research analyst at a top Indian institutional "
            "investment firm. Your job is to produce a structured investment thesis "
            "based on the financial data and web research provided.\n\n"
            "Rules:\n"
            "1. Every claim must be grounded in the provided data.\n"
            "2. If data is missing, acknowledge the gap — do not invent numbers.\n"
            "3. Conviction level should reflect data quality and consistency.\n"
            "4. Target price range is optional — only provide if you have enough data.\n"
            "5. Keep the executive summary under 3 sentences.\n"
            "6. Rationale and risks should be specific, not generic."
        )

        response = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context},
            ],
            response_format=InvestmentThesis,
            temperature=0.3,  # Lower = more deterministic / reliable
        )

        thesis: InvestmentThesis = response.choices[0].message.parsed

        # Stamp which sources were used
        sources = []
        if financials:
            sources.append(f"financial_data ({financials.ticker})")
        if web_results:
            sources.append(f"web_search ({len(web_results)} results)")
        thesis.data_sources_used = sources

        return thesis
