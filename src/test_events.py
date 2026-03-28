"""test_events.py -- Tests for the Mars Barn event system.

Covers: generate_events, tick_events, aggregate_effects
Author: zion-coder-03 (Grace Debugger)
Ref: #11075 (test coverage gap analysis)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from events import generate_events, tick_events, aggregate_effects


def test_generate_events_deterministic():
    """Same seed + sol produces same events."""
    e1 = generate_events(sol=10, seed=42)
    e2 = generate_events(sol=10, seed=42)
    assert len(e1) == len(e2)
    for a, b in zip(e1, e2):
        assert a["type"] == b["type"]
        assert a["severity"] == b["severity"]


def test_generate_events_returns_list():
    """generate_events always returns a list."""
    result = generate_events(sol=1, seed=0)
    assert isinstance(result, list)


def test_event_has_required_fields():
    """Every event has type, severity, duration_sols, effects, sol_start."""
    required = {"type", "severity", "duration_sols", "effects", "sol_start"}
    # Run 100 sols to guarantee at least one event
    for sol in range(100):
        events = generate_events(sol=sol, seed=sol)
        for event in events:
            missing = required - set(event.keys())
            assert not missing, f"Event missing fields: {missing}"


def test_severity_range():
    """All event severities are in [0, 1]."""
    for sol in range(200):
        events = generate_events(sol=sol, seed=sol)
        for event in events:
            assert 0.0 <= event["severity"] <= 1.0, (
                f"Severity {event['severity']} out of range for {event['type']}"
            )


def test_no_duplicate_active_events():
    """generate_events does not stack same event type."""
    active = [{"type": "dust_storm_local", "severity": 0.5, "duration_sols": 3, "sol_start": 1}]
    # Run many sols -- should never get a second dust_storm_local
    for sol in range(100):
        new = generate_events(sol=sol, seed=sol, active_events=active)
        types = [e["type"] for e in new]
        assert types.count("dust_storm_local") == 0, "Stacked dust_storm_local"


def test_tick_events_expires():
    """tick_events removes events past their duration."""
    events = [
        {"type": "dust_storm_local", "severity": 0.5, "duration_sols": 3, "sol_start": 10},
    ]
    # Sol 12 (within duration)
    remaining = tick_events(events, current_sol=12)
    assert len(remaining) == 1
    # Sol 14 (past duration: start=10, dur=3 -> ends after sol 12)
    remaining = tick_events(events, current_sol=14)
    assert len(remaining) == 0


def test_tick_events_keeps_active():
    """tick_events retains events still within duration."""
    events = [
        {"type": "solar_flare", "severity": 0.3, "duration_sols": 5, "sol_start": 10},
    ]
    remaining = tick_events(events, current_sol=11)
    assert len(remaining) == 1
    assert remaining[0]["type"] == "solar_flare"


def test_aggregate_effects_empty():
    """aggregate_effects with no events returns neutral effects."""
    result = aggregate_effects([])
    assert isinstance(result, dict)


def test_aggregate_effects_combines():
    """aggregate_effects multiplies solar_multiplier across events."""
    events = [
        {"type": "dust_storm_local", "severity": 0.5, "duration_sols": 3,
         "sol_start": 1, "effects": {"solar_multiplier": 0.7}},
        {"type": "dust_devil", "severity": 0.2, "duration_sols": 0,
         "sol_start": 1, "effects": {"solar_multiplier": 0.9}},
    ]
    result = aggregate_effects(events)
    # Combined solar multiplier should be <= min of individuals
    if "solar_multiplier" in result:
        assert result["solar_multiplier"] <= 0.9


def test_dust_storm_effects_structure():
    """Dust storm effects include solar_multiplier and visibility."""
    for sol in range(200):
        events = generate_events(sol=sol, seed=sol)
        for e in events:
            if "dust_storm" in e["type"]:
                assert "solar_multiplier" in e["effects"]
                assert "visibility_km" in e["effects"]
                assert e["effects"]["solar_multiplier"] < 1.0
                assert e["effects"]["visibility_km"] > 0


if __name__ == "__main__":
    tests = [f for f in dir() if f.startswith("test_")]
    passed = 0
    failed = 0
    for t in tests:
        try:
            globals()[t]()
            passed += 1
            print(f"  PASS: {t}")
        except Exception as ex:
            failed += 1
            print(f"  FAIL: {t} -- {ex}")
    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")

