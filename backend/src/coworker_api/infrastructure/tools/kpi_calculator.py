"""
KPI Calculator Tool — Business Metrics.

Provides tools for computing common business KPIs during simulations.
"""

from __future__ import annotations

from typing import Any


class KPICalculator:
    """Calculates business key performance indicators."""

    def calculate(self, kpi_name: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        Calculate a named KPI from the given data.

        Supported KPIs: revenue_growth, profit_margin, market_share, cac, ltv.
        """
        calculators = {
            "revenue_growth": self._revenue_growth,
            "profit_margin": self._profit_margin,
            "market_share": self._market_share,
            "cac": self._customer_acquisition_cost,
            "ltv": self._customer_lifetime_value,
        }

        calc_fn = calculators.get(kpi_name)
        if calc_fn is None:
            return {"error": f"Unknown KPI: {kpi_name}", "available": list(calculators.keys())}

        return calc_fn(data)

    def _revenue_growth(self, data: dict[str, Any]) -> dict[str, Any]:
        current = data.get("current_revenue", 0)
        previous = data.get("previous_revenue", 0)
        if previous == 0:
            return {"kpi": "revenue_growth", "value": None, "error": "Previous revenue is zero"}
        growth = ((current - previous) / previous) * 100
        return {"kpi": "revenue_growth", "value": round(growth, 2), "unit": "%"}

    def _profit_margin(self, data: dict[str, Any]) -> dict[str, Any]:
        revenue = data.get("revenue", 0)
        costs = data.get("costs", 0)
        if revenue == 0:
            return {"kpi": "profit_margin", "value": None, "error": "Revenue is zero"}
        margin = ((revenue - costs) / revenue) * 100
        return {"kpi": "profit_margin", "value": round(margin, 2), "unit": "%"}

    def _market_share(self, data: dict[str, Any]) -> dict[str, Any]:
        company_revenue = data.get("company_revenue", 0)
        total_market = data.get("total_market", 0)
        if total_market == 0:
            return {"kpi": "market_share", "value": None, "error": "Total market is zero"}
        share = (company_revenue / total_market) * 100
        return {"kpi": "market_share", "value": round(share, 2), "unit": "%"}

    def _customer_acquisition_cost(self, data: dict[str, Any]) -> dict[str, Any]:
        spend = data.get("marketing_spend", 0)
        new_customers = data.get("new_customers", 0)
        if new_customers == 0:
            return {"kpi": "cac", "value": None, "error": "No new customers"}
        cac = spend / new_customers
        return {"kpi": "cac", "value": round(cac, 2), "unit": "currency"}

    def _customer_lifetime_value(self, data: dict[str, Any]) -> dict[str, Any]:
        avg_purchase = data.get("avg_purchase_value", 0)
        frequency = data.get("purchase_frequency", 0)
        lifespan = data.get("customer_lifespan_years", 0)
        ltv = avg_purchase * frequency * lifespan
        return {"kpi": "ltv", "value": round(ltv, 2), "unit": "currency"}
