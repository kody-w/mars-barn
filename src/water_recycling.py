"""Mars Barn — Water Recycling Module

Closed-loop water recovery for a pressurized Mars habitat.
Models greywater/condensate recycling, ISRU makeup water, and
crew consumption.  Tracks reservoir levels sol-over-sol.

Recovery rates based on ISS ECLSS data (93% nominal).
Degradation modeled as linear efficiency loss when maintenance
is deferred.  ISRU production scales with deployed extraction
units (1 per 2 crew members, minimum 1).

Author: zion-coder-10 + zion-wildcard-04 (Frame 123)
"""
from __future__ import annotations

from constants import HABITAT_CREW_SIZE


# --- Water budget constants (liters per person per sol) ---

DRINKING_L_PER_PERSON_SOL = 2.5
HYGIENE_L_PER_PERSON_SOL = 6.0
CROP_L_PER_PERSON_SOL = 4.0
TOTAL_CONSUMPTION_L_PER_PERSON_SOL = (
    DRINKING_L_PER_PERSON_SOL + HYGIENE_L_PER_PERSON_SOL + CROP_L_PER_PERSON_SOL
)

# --- Recovery system ---

BASE_RECOVERY_RATE = 0.93          # ISS ECLSS baseline
CONDENSATE_RECOVERY_RATE = 0.98    # humidity condensate — easy to reclaim
GREYWATER_RECOVERY_RATE = 0.90     # wash/hygiene water
CROP_TRANSPIRATION_RECLAIM = 0.75  # greenhouse humidity capture
MAINTENANCE_INTERVAL_SOLS = 30     # filter replacement cycle
DEGRADATION_PER_SOL = 0.002        # efficiency loss when overdue

# --- ISRU makeup ---

ISRU_WATER_L_PER_UNIT_SOL = 8.0   # liters per extraction unit per sol
ISRU_UNITS_PER_CREW = 0.5         # 1 unit per 2 crew, minimum 1


def _isru_units(crew_size: int) -> int:
    """Number of ISRU water extraction units deployed."""
    return max(1, round(crew_size * ISRU_UNITS_PER_CREW))


def water_consumed(crew_size: int = HABITAT_CREW_SIZE) -> float:
    """Total water consumed per sol (liters)."""
    return TOTAL_CONSUMPTION_L_PER_PERSON_SOL * crew_size


def recovery_efficiency(
    sols_since_maintenance: int,
    maintenance_interval: int = MAINTENANCE_INTERVAL_SOLS,
) -> float:
    """Current recycling efficiency (0.0–1.0).

    Degrades linearly when maintenance is overdue.
    """
    if sols_since_maintenance <= maintenance_interval:
        return BASE_RECOVERY_RATE
    overdue = sols_since_maintenance - maintenance_interval
    degraded = BASE_RECOVERY_RATE - (overdue * DEGRADATION_PER_SOL)
    return max(degraded, 0.50)  # floor at 50% — hardware minimum


def water_recovered(
    crew_size: int = HABITAT_CREW_SIZE,
    sols_since_maintenance: int = 0,
) -> float:
    """Liters of water recovered per sol from all recycling streams."""
    eff = recovery_efficiency(sols_since_maintenance)
    hygiene_recovered = HYGIENE_L_PER_PERSON_SOL * crew_size * GREYWATER_RECOVERY_RATE * eff
    condensate = DRINKING_L_PER_PERSON_SOL * crew_size * CONDENSATE_RECOVERY_RATE * eff * 0.3
    crop = CROP_L_PER_PERSON_SOL * crew_size * CROP_TRANSPIRATION_RECLAIM * eff
    return hygiene_recovered + condensate + crop


def isru_production(crew_size: int = HABITAT_CREW_SIZE) -> float:
    """ISRU water extraction per sol (liters)."""
    return _isru_units(crew_size) * ISRU_WATER_L_PER_UNIT_SOL


def water_balance(
    crew_size: int = HABITAT_CREW_SIZE,
    sols_since_maintenance: int = 0,
    isru_active: bool = True,
) -> dict:
    """Net water balance for one sol.

    Returns dict with consumed, recovered, isru, net, and sustainable flag.
    """
    consumed = water_consumed(crew_size)
    recovered = water_recovered(crew_size, sols_since_maintenance)
    isru = isru_production(crew_size) if isru_active else 0.0
    net = recovered + isru - consumed
    return {
        "consumed_l": round(consumed, 2),
        "recovered_l": round(recovered, 2),
        "isru_l": round(isru, 2),
        "net_l": round(net, 2),
        "sustainable": net >= 0,
    }


def tick_water(
    reservoir_l: float,
    crew_size: int = HABITAT_CREW_SIZE,
    sols_since_maintenance: int = 0,
    isru_active: bool = True,
) -> dict:
    """Advance water system one sol.  Returns updated reservoir and status."""
    balance = water_balance(crew_size, sols_since_maintenance, isru_active)
    new_reservoir = max(reservoir_l + balance["net_l"], 0.0)
    return {
        "reservoir_l": round(new_reservoir, 2),
        "balance": balance,
        "critical": new_reservoir < crew_size * DRINKING_L_PER_PERSON_SOL * 3,
        "depleted": new_reservoir <= 0.0,
    }
