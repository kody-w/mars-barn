"""Tests for water_recycling module."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from water_recycling import (
    water_consumed,
    recovery_efficiency,
    water_recovered,
    water_balance,
    tick_water,
    isru_production,
)


def test_consumption_scales_with_crew():
    """Consumption should be linear in crew size."""
    solo = water_consumed(1)
    quad = water_consumed(4)
    assert abs(quad - 4 * solo) < 0.01, f"Expected {4*solo}, got {quad}"


def test_recovery_degrades_when_overdue():
    """Efficiency drops when maintenance is overdue."""
    fresh = recovery_efficiency(0)
    overdue = recovery_efficiency(50)  # 20 sols past due
    assert fresh > overdue, f"Fresh {fresh} should beat overdue {overdue}"
    assert overdue >= 0.50, f"Efficiency floor is 50%, got {overdue}"


def test_recovery_floor():
    """Efficiency should never drop below 50%."""
    ancient = recovery_efficiency(1000)
    assert ancient == 0.50, f"Expected 0.50, got {ancient}"


def test_balance_sustainable_small_crew():
    """With ISRU and fresh maintenance, small crew is sustainable."""
    b = water_balance(crew_size=1, sols_since_maintenance=0, isru_active=True)
    assert b["sustainable"], f"1-crew should be sustainable, got net={b['net_l']}"


def test_balance_knife_edge_at_four_crew():
    """Four crew is near the sustainability boundary — design tension."""
    b = water_balance(crew_size=4, sols_since_maintenance=0, isru_active=True)
    # Net should be close to zero (within a few liters either way)
    assert abs(b["net_l"]) < 2.0, f"4-crew net should be near zero, got {b['net_l']}"


def test_balance_unsustainable_no_isru_degraded():
    """Without ISRU and degraded recycling, water should be negative."""
    b = water_balance(crew_size=4, sols_since_maintenance=100, isru_active=False)
    assert not b["sustainable"], f"Expected unsustainable, got net={b['net_l']}"


def test_isru_scales_with_crew():
    """More crew means more ISRU units deployed."""
    small = isru_production(1)
    large = isru_production(6)
    assert large > small, f"6-crew ISRU ({large}) should exceed 1-crew ({small})"


def test_tick_depletes_reservoir():
    """tick_water should deplete reservoir when balance is negative."""
    result = tick_water(10.0, crew_size=4, sols_since_maintenance=100, isru_active=False)
    assert result["reservoir_l"] < 10.0, "Reservoir should decrease"


def test_tick_reservoir_never_negative():
    """Reservoir should floor at zero."""
    result = tick_water(0.1, crew_size=4, sols_since_maintenance=100, isru_active=False)
    assert result["reservoir_l"] >= 0.0, "Reservoir must not go negative"


def test_tick_critical_flag():
    """Critical flag when reservoir < 3 days of drinking water."""
    result = tick_water(5.0, crew_size=4)
    assert result["critical"], "5L for 4 crew should be critical"


if __name__ == "__main__":
    tests = [f for f in sorted(dir()) if f.startswith("test_")]
    passed = 0
    for t in tests:
        try:
            eval(f"{t}()")
            print(f"  PASS  {t}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t}: {e}")
        except Exception as e:
            print(f"  ERROR {t}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
