"""
Tool: Financial Data Fetcher
Uses yfinance to pull stock fundamentals and price data.
Returns structured FinancialMetrics or a graceful failure message.
"""

from __future__ import annotations

from typing import Optional

import yfinance as yf

from src.models.schemas import FinancialMetrics


class FinancialDataTool:
    """Fetches financial data for a given ticker symbol."""

    def run(self, ticker: str) -> FinancialMetrics:
        """
        Pull key metrics for *ticker*.

        Returns a FinancialMetrics object even if some fields are None.
        Never raises — failures are captured in partial results.
        """
        result = FinancialMetrics(ticker=ticker.upper())

        try:
            stock = yf.Ticker(ticker)
            info = stock.info or {}

            result.current_price = self._safe_float(info.get("currentPrice"))
            result.market_cap = self._safe_float(info.get("marketCap"))
            result.pe_ratio = self._safe_float(info.get("trailingPE"))
            result.pb_ratio = self._safe_float(info.get("priceToBook"))
            result.debt_to_equity = self._safe_float(info.get("debtToEquity"))
            result.roe = self._safe_float(info.get("returnOnEquity"))
            result.revenue_growth_yoy = self._safe_float(
                info.get("revenueGrowth")
            )
            result.profit_margin = self._safe_float(
                info.get("profitMargins")
            )
            result.fifty_two_week_high = self._safe_float(
                info.get("fiftyTwoWeekHigh")
            )
            result.fifty_two_week_low = self._safe_float(
                info.get("fiftyTwoWeekLow")
            )

        except Exception as e:
            # Graceful failure: return what we have with a note
            result.source = f"yfinance (partial: {e})"

        return result

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        """Defensive cast — yfinance sometimes returns None or 'NA'."""
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
