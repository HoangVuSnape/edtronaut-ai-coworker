"""
Portfolio Pack Tool — Portfolio Analysis Utility.

Provides portfolio management calculations for finance-related
NPC simulations.
"""

from __future__ import annotations

from typing import Any


class PortfolioPack:
    """Portfolio analysis and management utility."""

    def analyze(self, portfolio: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Analyze a portfolio of assets.

        Args:
            portfolio: List of dicts, each with:
                - name (str): Asset name.
                - value (float): Current value.
                - weight (float): Portfolio weight (0.0-1.0).
                - return_rate (float): Expected annual return.
                - risk (float): Risk/volatility score.

        Returns:
            Dict with total_value, weighted_return, risk_score, and diversification metrics.
        """
        if not portfolio:
            return {"error": "Empty portfolio"}

        total_value = sum(a.get("value", 0) for a in portfolio)
        if total_value == 0:
            return {"error": "Portfolio has zero value"}

        # Re-calculate weights based on actual values
        for asset in portfolio:
            asset["actual_weight"] = asset.get("value", 0) / total_value

        # Weighted return
        weighted_return = sum(
            a.get("actual_weight", 0) * a.get("return_rate", 0)
            for a in portfolio
        )

        # Weighted risk (simplified)
        weighted_risk = sum(
            a.get("actual_weight", 0) * a.get("risk", 0)
            for a in portfolio
        )

        # Concentration risk: Herfindahl-Hirschman Index
        hhi = sum(a.get("actual_weight", 0) ** 2 for a in portfolio)
        diversification = "well_diversified" if hhi < 0.2 else (
            "moderately_concentrated" if hhi < 0.5 else "highly_concentrated"
        )

        return {
            "total_value": round(total_value, 2),
            "asset_count": len(portfolio),
            "weighted_return": round(weighted_return * 100, 2),
            "weighted_risk": round(weighted_risk, 4),
            "hhi_index": round(hhi, 4),
            "diversification": diversification,
            "assets": [
                {
                    "name": a.get("name", ""),
                    "value": a.get("value", 0),
                    "weight": round(a.get("actual_weight", 0) * 100, 1),
                    "return": round(a.get("return_rate", 0) * 100, 2),
                }
                for a in portfolio
            ],
        }
