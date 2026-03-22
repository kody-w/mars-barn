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


def heat_loss_conduction(
    internal_temp_k: float,
    external_temp_k: float,
    r_value: float = HABITAT_INSULATION_R_VALUE,
    surface_area_m2: float = HABITAT_SURFACE_AREA_M2,
) -> float:
    """Conductive/convective heat loss through walls (Watts)."""
    return surface_area_m2 * (internal_temp_k - external_temp_k) / r_value


def heat_loss_radiation(
    internal_temp_k: float,
    external_temp_k: float,
    emissivity: float = HABITAT_EMISSIVITY,
    surface_area_m2: float = HABITAT_SURFACE_AREA_M2,
) -> float:
    """Radiative heat loss to space (Watts)."""
    return STEFAN_BOLTZMANN * emissivity * surface_area_m2 * (
        internal_temp_k**4 - external_temp_k**4
    )


def solar_heat_gain(
    irradiance_w_m2: float,
    window_area_m2: float = 10.0,
    transmittance: float = 0.75,
) -> float:
    """Solar heat gain through windows (Watts)."""
    return irradiance_w_m2 * window_area_m2 * transmittance


def electrical_heating(
    power_w: float,
    efficiency: float = 1.0,
) -> float:
    """Electrical heater output (Watts) given input power and efficiency."""
    return power_w * efficiency


def thermal_step(
    internal_temp_k: float,
    external_temp_k: float,
    solar_irradiance_w_m2: float = 0.0,
    active_heating_w: float = 0.0,
    r_value: float = HABITAT_INSULATION_R_VALUE,
    dt_seconds: float = 900.0,
    # Keyword aliases used by tests
    solar_irradiance_wm2: float = None,
    electrical_power_w: float = None,
) -> dict:
    """Run one thermal simulation step. Used by main.py simulation loop.

    Returns dict with updated temperature and detailed diagnostic info.
    Accepts both positional args (main.py) and keyword aliases (tests).
    """
    # Resolve keyword aliases (test compat)
    if solar_irradiance_wm2 is not None:
        solar_irradiance_w_m2 = solar_irradiance_wm2
    if electrical_power_w is not None:
        active_heating_w = electrical_power_w

    # Individual heat flow components
    q_cond = heat_loss_conduction(internal_temp_k, external_temp_k, r_value)
    q_rad = heat_loss_radiation(internal_temp_k, external_temp_k)
    q_solar = solar_irradiance_w_m2 * (HABITAT_SURFACE_AREA_M2 / 4) * 0.1

    # Crew metabolic heat
    q_metabolic = 0.0
    if HABITAT_HUMAN_METABOLIC_HEAT:
        q_metabolic = HABITAT_CREW_SIZE * HUMAN_METABOLIC_HEAT_W

    # Ground coupling
    q_ground = 0.0
    if HABITAT_GROUND_COUPLING:
        ground_temp_k = 210.0
        ground_area = HABITAT_SURFACE_AREA_M2 * 0.3
        q_ground = GROUND_COUPLING_U_VALUE * ground_area * (internal_temp_k - ground_temp_k)

    net_power = active_heating_w + q_solar + q_metabolic - q_cond - q_rad - q_ground

    new_temp = update_temperature(internal_temp_k, net_power, dt_seconds)
    delta_t = new_temp - internal_temp_k

    # Heating required to maintain target
    heating_needed = calculate_required_heating(external_temp_k, solar_irradiance_w_m2, r_value)

    return {
        "interior_temp_k": new_temp,
        "delta_t_k": delta_t,
        "q_solar_w": q_solar,
        "q_electric_w": active_heating_w,
        "q_cond_loss_w": q_cond,
        "q_rad_loss_w": q_rad,
        "q_ground_loss_w": q_ground,
        "q_metabolic_w": q_metabolic,
        "q_net_w": net_power,
        "heating_required": heating_needed,
        # Backward compat keys for main.py
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


def simulate_sol(
    solar_longitude: float = 0.0,
    r_value: float = HABITAT_INSULATION_R_VALUE,
    dust_storm: bool = False,
    rtg_power_w: float = 0.0,
    latitude_deg: float = -4.5,
) -> dict:
    """Simulate thermal regulation for a full Mars sol.

    Integrates heating requirements over 24.6 hours in 15-min steps.
    Used by tick_engine.py for colony persistence.

    Returns dict with:
        heating_kwh: total electrical heating energy consumed (kWh)
        min_temp_k: minimum interior temperature during the sol
        max_temp_k: maximum interior temperature during the sol
    """
    from solar import surface_irradiance
    from atmosphere import temperature_at_altitude

    sol_hours = 24.66
    step_hours = 0.25
    num_steps = int(sol_hours / step_hours)

    interior_temp = HABITAT_TARGET_TEMP_K
    total_heating_wh = 0.0
    min_temp = interior_temp
    max_temp = interior_temp

    for step_idx in range(num_steps):
        hour = step_idx * step_hours
        ext_temp = temperature_at_altitude(0, latitude_deg, solar_longitude, hour, dust_storm)
        irr = surface_irradiance(
            latitude_deg=latitude_deg,
            solar_longitude_deg=solar_longitude,
            hour=hour,
            dust_storm=dust_storm,
        )

        # Proportional heater control
        temp_deficit = HABITAT_TARGET_TEMP_K - interior_temp
        heater_fraction = max(0.0, min(1.0, temp_deficit / 5.0))
        heater_w = HABITAT_HEATER_POWER_W * heater_fraction + rtg_power_w

        result = thermal_step(
            interior_temp, ext_temp, irr, heater_w,
            r_value=r_value, dt_seconds=step_hours * 3600,
        )
        interior_temp = result["interior_temp_k"]
        min_temp = min(min_temp, interior_temp)
        max_temp = max(max_temp, interior_temp)

        if heater_w > 0:
            total_heating_wh += heater_w * step_hours

    return {
        "heating_kwh": round(total_heating_wh / 1000.0, 2),
        "min_temp_k": round(min_temp, 2),
        "max_temp_k": round(max_temp, 2),
    }


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
