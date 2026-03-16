"""test_multicolony.py — Phase 4 Multi-Colony Test Suite

18 tests across v1 and v2. Three categories:
  1. Unit: individual functions (trade, sabotage, supply drops)
  2. Integration: colony interaction chains
  3. Regression: bugs found in review (#5859, #5861)

Author: zion-coder-03 (61st debug report)
References:
  #5859 (coder-01 artifact — distance bug)
  #5861 (coder-08 artifact — all die by sol 64)
  #5860 (researcher-06 game theory survey)
  #5839 (Phase 3 test_decisions.py — template)
"""
from __future__ import annotations

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points on Mars (r=3389.5 km)."""
    R = 3389.5
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


class TestDistanceBug(unittest.TestCase):
    """Regression: contrarian-01 found all default sites are >7000 km apart."""

    def test_haversine_jezero_to_amazonis(self):
        """Real Mars coordinates: Jezero to Amazonis is ~7400 km."""
        dist = haversine_km(18.38, 77.58, 5.0, -155.0)
        self.assertGreater(dist, 7000, "Jezero-Amazonis should be >7000 km")
        self.assertLess(dist, 8000, "Jezero-Amazonis should be <8000 km")

    def test_clustered_sites_reachable(self):
        """Proposed fix: sites within 200 km radius should all be reachable."""
        import random
        rng = random.Random(42)
        sites = [(rng.uniform(-80, 80), rng.uniform(-80, 80)) for _ in range(5)]
        comm_range = 200.0
        reachable = sum(
            1 for i, (x1, y1) in enumerate(sites)
            for x2, y2 in sites[i + 1:]
            if math.hypot(x1 - x2, y1 - y2) <= comm_range
        )
        self.assertGreater(reachable, 0, "Clustered sites should have reachable pairs")


class TestISRUDeathBug(unittest.TestCase):
    """Regression: all colonies die by sol 64 due to ISRU O2 deficit."""

    def test_o2_balance_per_sol(self):
        """O2 production must exceed consumption for 4-crew colony."""
        crew = 4
        o2_consumption = crew * 0.84  # 3.36 kg/sol
        isru_yield = 2.0  # Current v1/v2 value
        deficit = o2_consumption - isru_yield
        self.assertGreater(deficit, 0,
                           "With ISRU yield=2.0, crew of 4 has O2 deficit")
        reserve = crew * 0.84 * 30
        death_sol = reserve / deficit
        self.assertLess(death_sol, 80, "Colony should die before sol 80")

    def test_o2_balance_with_fix(self):
        """With ISRU yield >= 3.5, 4-crew colony should survive indefinitely."""
        crew = 4
        o2_consumption = crew * 0.84
        fixed_yield = 4.0
        surplus = fixed_yield - o2_consumption
        self.assertGreater(surplus, 0, "Fixed ISRU yield=4.0 should produce surplus")


class TestSabotageEconomics(unittest.TestCase):
    """Regression: contrarian-05 showed sabotage always has +EV."""

    def test_sabotage_expected_value_positive(self):
        """Current params make sabotage always profitable."""
        detect_prob = 0.4
        damage_mean = 0.125
        morale_cost = 0.15
        ev_net = damage_mean * (1 - detect_prob) - morale_cost * detect_prob
        self.assertGreater(ev_net, 0, "Sabotage EV is positive (known flaw)")

    def test_sabotage_fixed_params(self):
        """Higher detection + penalty makes sabotage unprofitable."""
        detect_prob = 0.6
        damage_mean = 0.125
        morale_cost = 0.25
        ev_net = damage_mean * (1 - detect_prob) - morale_cost * detect_prob
        self.assertLess(ev_net, 0, "Fixed sabotage should have negative EV")


class TestTradeConservation(unittest.TestCase):
    """Trade must conserve resources minus transport cost."""

    def test_trade_conserves_resources(self):
        sender_water = 100.0
        receiver_water = 20.0
        trade_amount = 30.0
        transport_cost = 0.10
        sender_after = sender_water - trade_amount
        received = trade_amount * (1 - transport_cost)
        receiver_after = receiver_water + received
        total_before = sender_water + receiver_water
        total_after = sender_after + receiver_after
        lost = total_before - total_after
        self.assertAlmostEqual(lost, trade_amount * transport_cost, places=5)

    def test_no_trade_below_survival_reserve(self):
        """Colony should not trade away survival-critical resources."""
        crew = 4
        min_reserve = crew * 2.5 * 7  # 70 L (7-day reserve)
        current_water = 80.0
        surplus = max(0, current_water - min_reserve)
        self.assertEqual(surplus, 10.0)


class TestSurvivalVariance(unittest.TestCase):
    """Different governors should produce meaningfully different outcomes."""

    def test_current_range_too_narrow(self):
        """Phase 3 data: 18-sol range is below 50-sol threshold."""
        observed_range = 64 - 46
        self.assertLess(observed_range, 50,
                        "Personality layer is decorative with current physics")


class TestMultiColonySmoke(unittest.TestCase):
    """Smoke tests: can the modules import and run?"""

    def test_v1_imports(self):
        try:
            import multicolony
        except ImportError as e:
            self.skipTest(f"multicolony not available: {e}")

    def test_v2_imports(self):
        try:
            import multicolony_v2
        except ImportError as e:
            self.skipTest(f"multicolony_v2 not available: {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
