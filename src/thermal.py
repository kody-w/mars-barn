"""Mars Barn — Thermal Regulation System

Model heat flow in/out of the habitat given solar input and atmospheric
conditions. Balance heating, insulation, and radiative cooling.

Fixed: import constants from constants.py instead of hardcoding.
Added: thermal_step() function used by main.py simulation loop.
"""
from constants import (
    STEFAN_BOLTZMANN,
    HABITAT_SURFACE_AREA_M2,
    HABITAT_VOLUME_M3,
    HABITAT_TARGET_TEMP_K,
    AIR_SPECIFIC_HEAT_J_KGK as HEAT_CAPACITY_AIR,
    HABITAT_EMISSIVITY,
    HABITAT_INSULATION_R_VALUE,
    HABITAT_HEATER_POWER_W,
    THERMAL_MASS_MULTIPLIER,
    AIR_DENSITY_KG_M3,
    HABITAT_CREW_SIZE,
    HUMAN_METABOLIC_HEAT_W,
    HABITAT_HUMAN_METABOLIC_HEAT,
    HABITAT_GROUND_COUPLING,
    GROUND_COUPLING_U_VALUE,
)


# Thermal mass: air + structure
_air_mass = AIR_DENSITY_KG_M3 * HABITAT_VOLUME_M3
_thermal_mass_kg = _air_mass * THERMAL_MASS_MULTIPLIER


def habitat_thermal_balance(
    external_temp_k: float,
    internal_temp_k: float,
    solar_irradiance_w_m2: float,
    insulation_r_value: float = HABITAT_INSULATION_R_VALUE,
    active_heating_w: float = 0.0,
    emissivity: float = HABITAT_EMISSIVITY,
) -> float:
    """Calculate net heat flow rate (Watts) for the habitat.

    Positive means habitat is gaining heat, negative means losing.
    """
    # 1. Conductive/convective loss through walls
    heat_loss = HABITAT_SURFACE_AREA_M2 * (internal_temp_k - external_temp_k) / insulation_r_value

    # 2. Solar gain (10% effective absorption through windows/surface)
    solar_gain = solar_irradiance_w_m2 * (HABITAT_SURFACE_AREA_M2 / 4) * 0.1

    # 3. Radiative loss to space (low-e coating: ε=0.05 per constants.py)
    radiative_loss = STEFAN_BOLTZMANN * emissivity * HABITAT_SURFACE_AREA_M2 * (
        internal_temp_k**4 - external_temp_k**4
    )

    # 4. Crew metabolic heat (4 crew × 120 W = 480 W free heating)
    metabolic_w = 0.0
    if HABITAT_HUMAN_METABOLIC_HEAT:
        metabolic_w = HABITAT_CREW_SIZE * HUMAN_METABOLIC_HEAT_W

    # 5. Ground coupling (regolith at ~210K stabilizes temperature)
    ground_loss = 0.0
    if HABITAT_GROUND_COUPLING:
        ground_temp_k = 210.0  # Mars subsurface approximation
        ground_area = HABITAT_SURFACE_AREA_M2 * 0.3  # ~30% floor contact
        ground_loss = GROUND_COUPLING_U_VALUE * ground_area * (internal_temp_k - ground_temp_k)

    net_power = active_heating_w + solar_gain + metabolic_w - heat_loss - radiative_loss - ground_loss
    return net_power


def update_temperature(
    current_temp_k: float,
    net_power_w: float,
    time_step_s: float,
    internal_mass_kg: float = _thermal_mass_kg,
) -> float:
    """Update internal temperature over a time step based on net power."""
    energy_joules = net_power_w * time_step_s
    temp_change = energy_joules / (internal_mass_kg * HEAT_CAPACITY_AIR)
    return current_temp_k + temp_change


def thermal_step(
    internal_temp_k: float,
    external_temp_k: float,
    solar_irradiance_w_m2: float,
    active_heating_w: float,
    r_value: float = HABITAT_INSULATION_R_VALUE,
    dt_seconds: float = 900.0,
) -> dict:
    """Run one thermal simulation step. Used by main.py simulation loop.

    Returns dict with updated temperature and diagnostic info.
    """
    net_power = habitat_thermal_balance(
        external_temp_k=external_temp_k,
        internal_temp_k=internal_temp_k,
        solar_irradiance_w_m2=solar_irradiance_w_m2,
        insulation_r_value=r_value,
        active_heating_w=active_heating_w,
    )

    new_temp = update_temperature(internal_temp_k, net_power, dt_seconds)

    return {
        "interior_temp_k": new_temp,
        "net_power_w": net_power,
        "heating_w": active_heating_w,
    }


def calculate_required_heating(
    external_temp_k: float,
    solar_irradiance_w_m2: float,
    insulation_r_value: float = HABITAT_INSULATION_R_VALUE,
    emissivity: float = HABITAT_EMISSIVITY,
) -> float:
    """Calculate active heating watts needed to maintain target temperature."""
    loss = HABITAT_SURFACE_AREA_M2 * (HABITAT_TARGET_TEMP_K - external_temp_k) / insulation_r_value
    rad_loss = STEFAN_BOLTZMANN * emissivity * HABITAT_SURFACE_AREA_M2 * (
        HABITAT_TARGET_TEMP_K**4 - external_temp_k**4
    )
    gain = solar_irradiance_w_m2 * (HABITAT_SURFACE_AREA_M2 / 4) * 0.1

    metabolic = 0.0
    if HABITAT_HUMAN_METABOLIC_HEAT:
        metabolic = HABITAT_CREW_SIZE * HUMAN_METABOLIC_HEAT_W

    required = loss + rad_loss - gain - metabolic
    return max(0.0, required)


if __name__ == "__main__":
    print("=== Habitat Thermal Model (constants.py integrated) ===")
    ext_temp = 210.0  # -63°C
    print(f"Emissivity: {HABITAT_EMISSIVITY} (low-e coating)")
    print(f"R-value: {HABITAT_INSULATION_R_VALUE} m²·K/W")
    print(f"Crew metabolic: {HABITAT_CREW_SIZE * HUMAN_METABOLIC_HEAT_W} W")
    print()
    req_heating = calculate_required_heating(ext_temp, 0.0)
    print(f"Required heating at night (-63°C external): {req_heating/1000.0:.1f} kW")

    req_heating_day = calculate_required_heating(ext_temp + 40, 300.0)
    print(f"Required heating at day (-23°C external, 300 W/m²): {req_heating_day/1000.0:.1f} kW")

    # Demo thermal_step
    result = thermal_step(293.0, 210.0, 0.0, 8000.0)
    print(f"\nThermal step (night, 8kW heater): {result['interior_temp_k']:.1f}K, net={result['net_power_w']:.0f}W")
