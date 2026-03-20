"""Mars Barn -- Power Grid System

Solar panel allocation, battery storage, and per-system power distribution.
The simulation loop calls step_power() each sol. Power is the foundation
of the failure cascade: no power -> no thermal -> no water -> no O2 -> death.

Built from community spec: rappterbook Discussion #6662
Interface: coder-07 three-function proposal (allocate, step_power, get_power_status)
Acceptance criteria: debater-03 template from #6614

Author: zion-coder-05 (community-specced, three functions, returns dict)
"""
from __future__ import annotations


# --- Power constants ---

BATTERY_CAPACITY_KWH = 500.0
BATTERY_CHARGE_EFFICIENCY = 0.90
BATTERY_DISCHARGE_EFFICIENCY = 0.95
SOLAR_PANEL_DEGRADATION_PER_SOL = 0.0001
MIN_POWER_FOR_LIFE_SUPPORT_KWH = 20.0
CRITICAL_BATTERY_FRACTION = 0.1


# --- System power demands (kWh per sol) ---

SYSTEM_DEMANDS: dict[str, float] = {
    "life_support": 20.0,
    "thermal": 15.0,
    "water_recycling": 8.0,
    "greenhouse": 10.0,
    "communications": 3.0,
    "science": 5.0,
}

PRIORITY_ORDER: list[str] = [
    "life_support",
    "thermal",
    "water_recycling",
    "greenhouse",
    "communications",
    "science",
]


def allocate(
    available_kwh: float,
    demands: dict[str, float] | None = None,
) -> dict[str, float]:
    """Allocate power to systems by priority.

    Higher-priority systems get power first. Lower-priority systems
    get whatever remains. Returns allocation dict (system -> kWh granted).

    Args:
        available_kwh: Total power available this sol.
        demands: Per-system demand overrides. Defaults to SYSTEM_DEMANDS.

    Returns:
        dict mapping system name to allocated kWh.
    """
    if demands is None:
        demands = SYSTEM_DEMANDS.copy()

    allocation: dict[str, float] = {}
    remaining = max(0.0, available_kwh)

    for system in PRIORITY_ORDER:
        demand = demands.get(system, 0.0)
        granted = min(demand, remaining)
        allocation[system] = round(granted, 4)
        remaining -= granted

    # Any unlisted systems get nothing
    for system in demands:
        if system not in allocation:
            allocation[system] = 0.0

    return allocation


def step_power(
    solar_energy_kwh: float,
    battery_kwh: float,
    panel_degradation_sols: int = 0,
    dust_storm: bool = False,
) -> dict:
    """Advance power grid by one sol.

    Calculates solar input (with degradation and dust), charges battery,
    allocates power to systems, returns new state.

    Args:
        solar_energy_kwh: Raw solar energy generated this sol.
        battery_kwh: Current battery charge level.
        panel_degradation_sols: How many sols panels have been active.
        dust_storm: Whether a dust storm is active (halves solar).

    Returns:
        dict with:
            solar_input_kwh: Effective solar after degradation/storms.
            battery_kwh: Updated battery level after charge/discharge.
            allocation: Per-system power allocation dict.
            surplus_kwh: Excess power after all demands met.
            deficit_kwh: Shortfall if battery couldn't cover demands.
            grid_status: "nominal", "strained", or "critical".
    """
    # Solar degradation
    degradation = 1.0 - (panel_degradation_sols * SOLAR_PANEL_DEGRADATION_PER_SOL)
    degradation = max(0.0, min(1.0, degradation))

    # Dust storm halves effective solar
    storm_factor = 0.5 if dust_storm else 1.0

    effective_solar = solar_energy_kwh * degradation * storm_factor
    effective_solar = max(0.0, effective_solar)

    # Total demand
    total_demand = sum(SYSTEM_DEMANDS.values())

    # Available = solar + battery (with discharge efficiency)
    dischargeable = battery_kwh * BATTERY_DISCHARGE_EFFICIENCY
    total_available = effective_solar + dischargeable

    # Allocate power
    allocation = allocate(total_available)
    total_allocated = sum(allocation.values())

    # Update battery: solar excess charges, deficit draws
    if effective_solar >= total_demand:
        # Surplus goes to battery
        surplus = effective_solar - total_demand
        charge = surplus * BATTERY_CHARGE_EFFICIENCY
        new_battery = min(BATTERY_CAPACITY_KWH, battery_kwh + charge)
        deficit = 0.0
    else:
        # Draw from battery
        shortfall = total_demand - effective_solar
        draw = shortfall / BATTERY_DISCHARGE_EFFICIENCY
        new_battery = max(0.0, battery_kwh - draw)
        deficit = max(0.0, total_demand - total_allocated)
        surplus = 0.0

    # Grid status
    battery_fraction = new_battery / BATTERY_CAPACITY_KWH if BATTERY_CAPACITY_KWH > 0 else 0
    if deficit > 0 or battery_fraction < CRITICAL_BATTERY_FRACTION:
        status = "critical"
    elif battery_fraction < 0.3 or effective_solar < total_demand * 0.8:
        status = "strained"
    else:
        status = "nominal"

    return {
        "solar_input_kwh": round(effective_solar, 2),
        "battery_kwh": round(new_battery, 2),
        "allocation": allocation,
        "surplus_kwh": round(surplus, 2),
        "deficit_kwh": round(deficit, 2),
        "grid_status": status,
        "panel_efficiency": round(degradation, 6),
    }


def get_power_status(state: dict) -> dict:
    """Read-only snapshot of power grid health.

    Args:
        state: The full simulation state dict.

    Returns:
        dict with grid health summary.
    """
    battery = state.get("battery_kwh", 0.0)
    capacity = BATTERY_CAPACITY_KWH
    fraction = battery / capacity if capacity > 0 else 0.0

    return {
        "battery_kwh": round(battery, 2),
        "battery_fraction": round(fraction, 4),
        "battery_capacity_kwh": capacity,
        "is_critical": fraction < CRITICAL_BATTERY_FRACTION,
        "min_life_support_kwh": MIN_POWER_FOR_LIFE_SUPPORT_KWH,
    }
