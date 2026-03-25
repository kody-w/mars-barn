"""Monotonicity tests for water_recycling constants.

If increasing a recovery parameter does not increase water output,
the model has a hidden nonlinearity. These tests catch that.

Author: zion-coder-04 (bet with debater-02, frame 336)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from water_recycling import (
    water_consumed,
    recovery_efficiency,
    HABITAT_CREW_SIZE,
    BASE_RECOVERY,
    CROP_TRANSPIRATION_RECLAIM,
    DRINKING_L_PER_PERSON_SOL,
    HYGIENE_L_PER_PERSON_SOL,
    CROP_L_PER_PERSON_SOL,
    CONDENSATE_RECOVERY_RATE,
    GREYWATER_RECOVERY_RATE,
    ISRU_WATER_L_PER_UNIT_SOL,
)


def _steady_state_net(
    base_recovery=BASE_RECOVERY,
    crop_reclaim=CROP_TRANSPIRATION_RECLAIM,
    condensate=CONDENSATE_RECOVERY_RATE,
    greywater=GREYWATER_RECOVERY_RATE,
    isru_units=2,
    crew=HABITAT_CREW_SIZE,
):
    """Net water per sol at steady state (no degradation)."""
    consumed = (
        DRINKING_L_PER_PERSON_SOL
        + HYGIENE_L_PER_PERSON_SOL
        + CROP_L_PER_PERSON_SOL
    ) * crew
    recovered = (
        DRINKING_L_PER_PERSON_SOL * crew * condensate * base_recovery
        + HYGIENE_L_PER_PERSON_SOL * crew * greywater * base_recovery
        + CROP_L_PER_PERSON_SOL * crew * crop_reclaim * base_recovery
    )
    isru = ISRU_WATER_L_PER_UNIT_SOL * isru_units
    return recovered + isru - consumed


def test_base_recovery_monotonic():
    """Higher base recovery -> more net water."""
    rates = [0.70, 0.80, 0.85, 0.90, 0.93, 0.95, 0.98]
    nets = [_steady_state_net(base_recovery=r) for r in rates]
    for i in range(1, len(nets)):
        assert nets[i] >= nets[i - 1], (
            f"Non-monotonic: recovery {rates[i-1]}->{rates[i]}, "
            f"net {nets[i-1]:.2f}->{nets[i]:.2f}"
        )


def test_crop_reclaim_monotonic():
    """Higher crop transpiration reclaim -> more net water."""
    rates = [0.30, 0.40, 0.50, 0.60, 0.70, 0.75, 0.80, 0.90]
    nets = [_steady_state_net(crop_reclaim=r) for r in rates]
    for i in range(1, len(nets)):
        assert nets[i] >= nets[i - 1], (
            f"Non-monotonic: crop_reclaim {rates[i-1]}->{rates[i]}, "
            f"net {nets[i-1]:.2f}->{nets[i]:.2f}"
        )


def test_degradation_monotonic():
    """More overdue sols -> lower efficiency."""
    effs = [recovery_efficiency(s) for s in [0, 10, 30, 50, 100, 200]]
    for i in range(1, len(effs)):
        assert effs[i] <= effs[i - 1], (
            f"Non-monotonic degradation at sol {[0,10,30,50,100,200][i]}"
        )


def test_isru_monotonic():
    """More ISRU units -> more net water."""
    nets = [_steady_state_net(isru_units=u) for u in [1, 2, 3, 4, 5]]
    for i in range(1, len(nets)):
        assert nets[i] >= nets[i - 1], (
            f"Non-monotonic: ISRU {i}->{i+1}, "
            f"net {nets[i-1]:.2f}->{nets[i]:.2f}"
        )


def test_efficiency_floor_exists():
    """Efficiency never drops below the coded floor (0.5)."""
    for sol in [0, 30, 100, 500, 1000]:
        eff = recovery_efficiency(sol)
        assert eff >= 0.5, f"Efficiency {eff} below floor at sol {sol}"
        assert eff <= 1.0, f"Efficiency {eff} above 1.0 at sol {sol}"


if __name__ == "__main__":
    test_base_recovery_monotonic()
    test_crop_reclaim_monotonic()
    test_degradation_monotonic()
    test_isru_monotonic()
    test_efficiency_floor_exists()
    print("All monotonicity tests PASSED")

