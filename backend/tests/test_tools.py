"""Unit tests for infrastructure tools: ABSimulator and PortfolioPack."""

from __future__ import annotations

import random

from coworker_api.infrastructure.tools.ab_simulator import ABSimulator
from coworker_api.infrastructure.tools.portfolio_pack import PortfolioPack


# ── ABSimulator Tests ──


class TestABSimulator:
    def test_simulate_returns_expected_structure(self):
        sim = ABSimulator()
        random.seed(42)
        result = sim.simulate(
            variant_a={"name": "Control", "conversion_rate": 0.10},
            variant_b={"name": "Experiment", "conversion_rate": 0.15},
            sample_size=500,
        )
        assert "variant_a" in result
        assert "variant_b" in result
        assert result["variant_a"]["name"] == "Control"
        assert result["variant_b"]["name"] == "Experiment"
        assert result["variant_a"]["sample_size"] == 500
        assert "lift_percent" in result
        assert "is_significant" in result
        assert "winner" in result
        assert "recommendation" in result

    def test_simulate_identical_rates_not_significant(self):
        sim = ABSimulator()
        random.seed(0)
        result = sim.simulate(
            variant_a={"name": "A", "conversion_rate": 0.5},
            variant_b={"name": "B", "conversion_rate": 0.5},
            sample_size=10000,
        )
        # With identical rates and large sample, lift should be small
        assert abs(result["lift_percent"]) < 10

    def test_simulate_uses_defaults(self):
        sim = ABSimulator()
        random.seed(1)
        result = sim.simulate(variant_a={}, variant_b={})
        assert result["variant_a"]["name"] == "Variant A"
        assert result["variant_b"]["name"] == "Variant B"
        assert result["variant_a"]["sample_size"] == 1000  # default

    def test_simulate_zero_sample_size(self):
        sim = ABSimulator()
        result = sim.simulate(
            variant_a={"conversion_rate": 0.1},
            variant_b={"conversion_rate": 0.2},
            sample_size=0,
        )
        assert result["variant_a"]["observed_rate"] == 0
        assert result["variant_b"]["observed_rate"] == 0


# ── PortfolioPack Tests ──


class TestPortfolioPack:
    def test_analyze_multi_asset_portfolio(self):
        pack = PortfolioPack()
        portfolio = [
            {"name": "Stocks", "value": 6000, "weight": 0.6, "return_rate": 0.10, "risk": 0.15},
            {"name": "Bonds", "value": 3000, "weight": 0.3, "return_rate": 0.04, "risk": 0.05},
            {"name": "Cash", "value": 1000, "weight": 0.1, "return_rate": 0.01, "risk": 0.01},
        ]
        result = pack.analyze(portfolio)

        assert result["total_value"] == 10000.0
        assert result["asset_count"] == 3
        assert "weighted_return" in result
        assert "weighted_risk" in result
        assert "hhi_index" in result
        assert result["diversification"] in ("well_diversified", "moderately_concentrated", "highly_concentrated")
        assert len(result["assets"]) == 3

    def test_analyze_empty_portfolio(self):
        pack = PortfolioPack()
        result = pack.analyze([])
        assert result == {"error": "Empty portfolio"}

    def test_analyze_zero_value_portfolio(self):
        pack = PortfolioPack()
        result = pack.analyze([{"name": "Nothing", "value": 0}])
        assert result == {"error": "Portfolio has zero value"}

    def test_analyze_single_asset_highly_concentrated(self):
        pack = PortfolioPack()
        result = pack.analyze([
            {"name": "All-In", "value": 10000, "return_rate": 0.12, "risk": 0.20},
        ])
        assert result["hhi_index"] == 1.0
        assert result["diversification"] == "highly_concentrated"

    def test_analyze_well_diversified(self):
        pack = PortfolioPack()
        # 10 equal-weighted assets → HHI = 10 × (0.1)² = 0.1
        portfolio = [
            {"name": f"Asset{i}", "value": 1000, "return_rate": 0.05, "risk": 0.10}
            for i in range(10)
        ]
        result = pack.analyze(portfolio)
        assert result["diversification"] == "well_diversified"
        assert result["hhi_index"] < 0.2
