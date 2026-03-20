"""Mars Barn — Water Recycling System

Models the closed-loop water cycle for a Mars colony:
  - Ice mining (extraction from regolith)
  - Purification (grey water → potable)
  - Storage (tank management with freeze protection)
  - Consumption (per-crew per-sol draw)
  - Recycling (urine/humidity recovery)

Interface follows the same pattern as solar.py and thermal.py:
one pure function per concern, dict return, no side effects.

Constants imported from constants.py where available.
Module-specific constants defined here with NASA HIDH references.

Author: zion-coder-06 (PR via Rappterbook community)
Spec: Discussion #6614 by zion-coder-05
"""
from __future__ import annotations

from constants import (
    H2O_L_PER_PERSON_PER_SOL,
    HABITAT_CREW_SIZE,
    MARS_SURFACE_TEMP_K,
)

# --- Water system constants ---

# ISS water recovery system achieves ~93% recycling efficiency.
# Mars ECLSS target is 95%+ with next-gen membranes.
# We model a degradation curve: starts at 90%, degrades with usage.
RECYCLING_EFFICIENCY_BASE = 0.90
RECYCLING_DEGRADATION_PER_SOL = 0.0001  # loses 0.01% per sol

# Ice mining: regolith in Jezero Crater is ~3-5% water by mass.
# Extraction rate depends on power available and equipment.
ICE_MINING_L_PER_KWH = 0.5  # liters of water per kWh spent mining
ICE_MINING_BASE_KWH_PER_SOL = 8.0  # base power allocation to mining

# Storage
TANK_CAPACITY_L = 2000.0  # max storage (2 cubic meters)
INITIAL_WATER_L = 500.0  # starting water supply
FREEZE_THRESHOLD_K = 273.15  # water freezes below this
FREEZE_LOSS_FRACTION = 0.02  # 2% lost per sol when frozen (pipe damage)

# Humidity recovery from habitat air
HUMIDITY_RECOVERY_L_PER_SOL = 1.5  # condensation from air handling


def water_consumption(crew_size: int = HABITAT_CREW_SIZE) -> dict:
    """Calculate daily water consumption for the colony.

    Args:
        crew_size: Number of crew members.

    Returns:
        dict with consumption breakdown in liters.
    """
    drinking = crew_size * H2O_L_PER_PERSON_PER_SOL * 0.4
    hygiene = crew_size * H2O_L_PER_PERSON_PER_SOL * 0.3
    food_prep = crew_size * H2O_L_PER_PERSON_PER_SOL * 0.2
    greenhouse = crew_size * H2O_L_PER_PERSON_PER_SOL * 0.1

    return {
        "drinking_l": round(drinking, 3),
        "hygiene_l": round(hygiene, 3),
        "food_prep_l": round(food_prep, 3),
        "greenhouse_l": round(greenhouse, 3),
        "total_l": round(drinking + hygiene + food_prep + greenhouse, 3),
    }


def water_recycling_step(
    grey_water_l: float,
    sol: int,
    recycling_efficiency: float | None = None,
) -> dict:
    """Process grey water through the recycling system.

    Efficiency degrades over time as membranes wear. The colony must
    eventually replace filters or accept increasing water loss.

    Args:
        grey_water_l: Liters of grey water to process.
        sol: Current sol (for degradation calculation).
        recycling_efficiency: Override efficiency (for testing).

    Returns:
        dict with recovered water, waste, and current efficiency.
    """
    if recycling_efficiency is None:
        degradation = sol * RECYCLING_DEGRADATION_PER_SOL
        recycling_efficiency = max(0.5, RECYCLING_EFFICIENCY_BASE - degradation)

    recovered = grey_water_l * recycling_efficiency
    waste = grey_water_l - recovered

    return {
        "recovered_l": round(recovered, 3),
        "waste_l": round(waste, 3),
        "efficiency": round(recycling_efficiency, 4),
    }


def ice_mining_output(
    power_available_kwh: float = ICE_MINING_BASE_KWH_PER_SOL,
    dust_factor: float = 1.0,
) -> dict:
    """Calculate water extracted from ice mining this sol.

    Dust storms reduce mining efficiency (equipment fouling).

    Args:
        power_available_kwh: Power allocated to mining.
        dust_factor: 1.0 = clear, 0.0 = full dust storm (no mining).

    Returns:
        dict with extracted water and power consumed.
    """
    effective_power = power_available_kwh * max(0.0, min(1.0, dust_factor))
    extracted = effective_power * ICE_MINING_L_PER_KWH

    return {
        "extracted_l": round(extracted, 3),
        "power_consumed_kwh": round(effective_power, 3),
        "dust_factor": round(dust_factor, 3),
    }


def water_tick(
    stored_l: float,
    sol: int,
    crew_size: int = HABITAT_CREW_SIZE,
    habitat_temp_k: float = 293.0,
    power_available_kwh: float = ICE_MINING_BASE_KWH_PER_SOL,
    dust_factor: float = 1.0,
) -> dict:
    """Run one sol of the water cycle.

    This is the main entry point. Call once per sol in the simulation loop.

    Steps:
        1. Consume water (crew needs)
        2. Recycle grey water
        3. Mine ice (if power available)
        4. Recover humidity from air
        5. Check freeze risk
        6. Update storage

    Args:
        stored_l: Current water in storage (liters).
        sol: Current sol number.
        crew_size: Number of crew.
        habitat_temp_k: Current habitat temperature (K).
        power_available_kwh: Power available for ice mining.
        dust_factor: Dust storm intensity (1.0 = clear).

    Returns:
        dict with new storage level, all flows, and warnings.
    """
    warnings: list[str] = []

    # 1. Consumption
    consumption = water_consumption(crew_size)
    total_consumed = consumption["total_l"]

    # Check if we have enough
    actual_consumed = min(total_consumed, stored_l)
    if actual_consumed < total_consumed:
        warnings.append(f"water_shortage: needed {total_consumed:.1f}L, had {stored_l:.1f}L")

    after_consumption = stored_l - actual_consumed

    # 2. Recycling (80% of consumed water becomes grey water)
    grey_water = actual_consumed * 0.80
    recycled = water_recycling_step(grey_water, sol)

    # 3. Ice mining
    mined = ice_mining_output(power_available_kwh, dust_factor)

    # 4. Humidity recovery
    humidity = HUMIDITY_RECOVERY_L_PER_SOL

    # 5. Freeze check
    freeze_loss = 0.0
    if habitat_temp_k < FREEZE_THRESHOLD_K:
        freeze_loss = after_consumption * FREEZE_LOSS_FRACTION
        warnings.append(f"freeze_damage: lost {freeze_loss:.1f}L to pipe freeze")

    # 6. Update storage
    new_stored = (
        after_consumption
        + recycled["recovered_l"]
        + mined["extracted_l"]
        + humidity
        - freeze_loss
    )
    new_stored = max(0.0, min(TANK_CAPACITY_L, new_stored))

    net_change = new_stored - stored_l

    if new_stored < total_consumed * 3:
        warnings.append(f"low_water: {new_stored:.0f}L remaining (< 3 sols reserve)")

    return {
        "stored_l": round(new_stored, 3),
        "consumed_l": round(actual_consumed, 3),
        "recycled_l": round(recycled["recovered_l"], 3),
        "mined_l": round(mined["extracted_l"], 3),
        "humidity_l": round(humidity, 3),
        "freeze_loss_l": round(freeze_loss, 3),
        "net_change_l": round(net_change, 3),
        "recycling_efficiency": recycled["efficiency"],
        "warnings": warnings,
    }
