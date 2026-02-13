"""
A/B Simulator Tool — Experiment Simulation.

Provides simple A/B test scenario simulation for use during
business simulations.
"""

from __future__ import annotations

import random
from typing import Any


class ABSimulator:
    """Simulates A/B testing scenarios with statistical estimates."""

    def simulate(
        self,
        variant_a: dict[str, Any],
        variant_b: dict[str, Any],
        sample_size: int = 1000,
        confidence_level: float = 0.95,
    ) -> dict[str, Any]:
        """
        Simulate an A/B test between two variants.

        Args:
            variant_a: Dict with 'name' and 'conversion_rate' (0.0-1.0).
            variant_b: Dict with 'name' and 'conversion_rate' (0.0-1.0).
            sample_size: Number of simulated users per variant.
            confidence_level: Statistical confidence threshold.

        Returns:
            Dict with results for each variant and a recommendation.
        """
        rate_a = variant_a.get("conversion_rate", 0.1)
        rate_b = variant_b.get("conversion_rate", 0.1)
        name_a = variant_a.get("name", "Variant A")
        name_b = variant_b.get("name", "Variant B")

        # Simulate conversions
        conversions_a = sum(1 for _ in range(sample_size) if random.random() < rate_a)
        conversions_b = sum(1 for _ in range(sample_size) if random.random() < rate_b)

        observed_rate_a = conversions_a / sample_size if sample_size > 0 else 0
        observed_rate_b = conversions_b / sample_size if sample_size > 0 else 0

        lift = 0.0
        if observed_rate_a > 0:
            lift = ((observed_rate_b - observed_rate_a) / observed_rate_a) * 100

        winner = name_a if observed_rate_a > observed_rate_b else name_b
        significant = abs(lift) > 5.0  # Simplified significance check

        return {
            "variant_a": {
                "name": name_a,
                "sample_size": sample_size,
                "conversions": conversions_a,
                "observed_rate": round(observed_rate_a, 4),
            },
            "variant_b": {
                "name": name_b,
                "sample_size": sample_size,
                "conversions": conversions_b,
                "observed_rate": round(observed_rate_b, 4),
            },
            "lift_percent": round(lift, 2),
            "is_significant": significant,
            "winner": winner,
            "recommendation": (
                f"{winner} is the winner with {abs(lift):.1f}% lift."
                if significant
                else "No statistically significant difference detected. Consider running longer."
            ),
        }
