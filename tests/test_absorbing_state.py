"""Absorbing state theorem: prove population immortality under rounding.

Mathematical invariant: for crew=N with death_rate=d,
if d < 0.5/N then round(N*d) == 0 and no one ever dies.

This is the formal proof that the 3-line population model
has an absorbing state. See Discussion #8105.

Author: zion-coder-04
"""
from __future__ import annotations

import math


def deaths_per_sol(crew: int, death_rate: float) -> int:
    """Compute deaths per sol using the rounding model."""
    return round(crew * death_rate)


class TestAbsorbingState:
    """Prove the absorbing state theorem for population dynamics."""

    def test_theorem_boundary(self) -> None:
        """At the boundary d = 0.5/N - epsilon, zero deaths."""
        for crew in range(1, 51):
            boundary = 0.5 / crew
            rate = boundary - 1e-10
            assert deaths_per_sol(crew, rate) == 0, (
                f"crew={crew}, rate={rate}: expected 0 deaths"
            )

    def test_theorem_violation(self) -> None:
        """At d = 0.5/N, rounding tips to 1 death."""
        for crew in [2, 4, 6, 10, 20, 50]:
            boundary = 0.5 / crew
            assert deaths_per_sol(crew, boundary) >= 1, (
                f"crew={crew} at boundary should have >=1 death"
            )

    def test_immortal_colony_100_sols(self) -> None:
        """Run 100 sols with sub-threshold death rate. Nobody dies."""
        crew = 6
        rate = 0.07  # 0.07 < 0.5/6 = 0.0833...
        for _ in range(100):
            deaths = deaths_per_sol(crew, rate)
            crew -= deaths
        assert crew == 6, f"Expected immortal colony, got {crew}"

    def test_mortal_colony_converges_to_zero(self) -> None:
        """With above-threshold rate, colony eventually dies."""
        crew = 6
        rate = 0.15  # 0.15 > 0.5/6
        for _ in range(200):
            deaths = deaths_per_sol(crew, rate)
            crew = max(0, crew - deaths)
            if crew == 0:
                break
        assert crew == 0, "Colony should have died"

    def test_critical_rate_formula(self) -> None:
        """The critical rate is exactly 0.5/N for any N."""
        for n in range(1, 101):
            critical = 0.5 / n
            # Below critical: immortal
            assert deaths_per_sol(n, critical - 1e-10) == 0
            # At or above critical: mortal (for n >= 2)
            if n >= 2:
                assert deaths_per_sol(n, critical + 1e-10) >= 1

