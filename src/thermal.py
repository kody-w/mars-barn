"""Mars Barn — Thermal Regulation System

Model heat flow in/out of the habitat given solar input and atmospheric
conditions. Balance heating, insulation, and radiative cooling.

Author: unclaimed (open workstream)
"""
import math

from constants import (
    STEFAN_BOLTZMANN,
    HABITAT_SURFACE_AREA_M2,
    HABITAT_VOLUME_M3,
    HABITAT_EMISSIVITY,
    HABITAT_WINDOW_AREA_M2,
    HABITAT_WINDOW_TRANSMITTANCE,
    HABITAT_CREW_SIZE,
    HUMAN_METABOLIC_HEAT_W,
    AIR_DENSITY_KG_M3,
    AIR_SPECIFIC_HEAT_J_KGK,
    THERMAL_MASS_MULTIPLIER,
    HABITAT_GROUND_COUPLING,
    GROUND_COUPLING_U_VALUE,
    MARS_SURFACE_TEMP_K,
    HABITAT_TARGET_TEMP_K,
    HABITAT_INSULATION_R_VALUE,
    HABITAT_HEATER_POWER_W,
    HABITAT_SOLAR_PANEL_AREA_M2,
    HABITAT_SOLAR_PANEL_EFFICIENCY,
    MARS_SOL_HOURS,
)

HEAT_CAPACITY_AIR = 1005.0  # J/(kg*K) ~ Earth air inside


def habitat_thermal_balance(
    external_temp_k: float,
    internal_temp_k: float,
    solar_irradiance_w_m2: float,
    insulation_r_value: float = 5.0, # m²·K/W
    active_heating_w: float = 0.0,
) -> float:
    """Calculate net heat flow rate (Watts) for the habitat.
    
    Positive means habitat is gaining heat, negative means losing.
    """
    # 1. Heat loss through conduction/convection (simplified via R-value)
    # q = A * ΔT / R
    heat_loss = HABITAT_SURFACE_AREA_M2 * (internal_temp_k - external_temp_k) / insulation_r_value
    
    # 2. Solar gain (assuming 10% effective absorption through windows/surface)
    solar_gain = solar_irradiance_w_m2 * (HABITAT_SURFACE_AREA_M2 / 4) * 0.1
    
    # 3. Radiative loss to space (assuming thin atmosphere, effective emissivity)
    radiative_loss = STEFAN_BOLTZMANN * 0.8 * HABITAT_SURFACE_AREA_M2 * (internal_temp_k**4 - external_temp_k**4)
    
    # Net thermal power (Watts)
    net_power = active_heating_w + solar_gain - heat_loss - radiative_loss
    
    return net_power


def update_temperature(
    current_temp_k: float,
    net_power_w: float,
    time_step_s: float,
    internal_mass_kg: float = 2000.0,  # Air + equipment thermal mass
) -> float:
    """Update internal temperature over a time step based on net power."""
    # ΔT = Q / (m * c)
    energy_joules = net_power_w * time_step_s
    temp_change = energy_joules / (internal_mass_kg * HEAT_CAPACITY_AIR)
    return current_temp_k + temp_change


def calculate_required_heating(
    external_temp_k: float,
    solar_irradiance_w_m2: float,
    insulation_r_value: float = 5.0,
) -> float:
    """Calculate active heating watts needed to maintain target temperature."""
    loss = HABITAT_SURFACE_AREA_M2 * (HABITAT_TARGET_TEMP_K - external_temp_k) / insulation_r_value
    rad_loss = STEFAN_BOLTZMANN * 0.8 * HABITAT_SURFACE_AREA_M2 * (HABITAT_TARGET_TEMP_K**4 - external_temp_k**4)
    gain = solar_irradiance_w_m2 * (HABITAT_SURFACE_AREA_M2 / 4) * 0.1
    required = loss + rad_loss - gain
    return max(0.0, required)


def heat_loss_conduction(
    t_interior_k: float,
    t_exterior_k: float,
    r_value: float = 12.0,
    surface_area_m2: float = HABITAT_SURFACE_AREA_M2,
) -> float:
    """Conductive heat loss through habitat walls (Watts). Positive = heat leaving."""
    return surface_area_m2 * (t_interior_k - t_exterior_k) / r_value


def heat_loss_radiation(
    t_interior_k: float,
    t_exterior_k: float,
    emissivity: float = HABITAT_EMISSIVITY,
    surface_area_m2: float = HABITAT_SURFACE_AREA_M2,
) -> float:
    """Radiative heat loss from exterior surface (Watts). Uses series model: wall temp ≈ exterior."""
    t_wall_k = t_exterior_k + (t_interior_k - t_exterior_k) * 0.1
    return emissivity * STEFAN_BOLTZMANN * surface_area_m2 * (t_wall_k**4 - t_exterior_k**4)


def solar_heat_gain(
    irradiance_wm2: float,
    window_area_m2: float = HABITAT_WINDOW_AREA_M2,
    transmittance: float = HABITAT_WINDOW_TRANSMITTANCE,
) -> float:
    """Solar heat gain through windows/collectors (Watts)."""
    return irradiance_wm2 * window_area_m2 * transmittance


def electrical_heating(
    power_w: float,
    efficiency: float = 0.95,
) -> float:
    """Effective heating from electrical heater (Watts)."""
    return power_w * efficiency


def thermal_step(
    interior_temp_k: float,
    exterior_temp_k: float,
    solar_irradiance_wm2: float = 0.0,
    electrical_power_w: float = 0.0,
    r_value: float = 12.0,
    dt_seconds: float = 3600.0,
    emissivity: float = HABITAT_EMISSIVITY,
    surface_area_m2: float = HABITAT_SURFACE_AREA_M2,
) -> dict:
    """Advance the thermal model by one time step.

    Computes all heat flows and returns updated temperature + diagnostics.
    """
    # Heat losses
    q_cond = heat_loss_conduction(interior_temp_k, exterior_temp_k, r_value, surface_area_m2)
    q_rad = heat_loss_radiation(interior_temp_k, exterior_temp_k, emissivity, surface_area_m2)

    # Ground coupling
    q_ground = 0.0
    if HABITAT_GROUND_COUPLING:
        ground_temp_k = MARS_SURFACE_TEMP_K
        ground_area = surface_area_m2 * 0.25
        q_ground = GROUND_COUPLING_U_VALUE * ground_area * (interior_temp_k - ground_temp_k)

    # Heat gains
    q_solar = solar_heat_gain(solar_irradiance_wm2)
    q_electric = electrical_heating(electrical_power_w)
    q_metabolic = HUMAN_METABOLIC_HEAT_W * HABITAT_CREW_SIZE

    # Net heat flow
    q_net = q_solar + q_electric + q_metabolic - q_cond - q_rad - q_ground

    # Temperature change: ΔT = Q·dt / (m·c)
    thermal_mass_kg = AIR_DENSITY_KG_M3 * HABITAT_VOLUME_M3 * THERMAL_MASS_MULTIPLIER
    delta_t = (q_net * dt_seconds) / (thermal_mass_kg * AIR_SPECIFIC_HEAT_J_KGK)
    new_temp = interior_temp_k + delta_t

    return {
        "interior_temp_k": new_temp,
        "delta_t_k": delta_t,
        "q_solar_w": q_solar,
        "q_electric_w": q_electric,
        "q_cond_loss_w": q_cond,
        "q_rad_loss_w": q_rad,
        "q_ground_loss_w": q_ground,
        "q_metabolic_w": q_metabolic,
        "q_net_w": q_net,
        "heating_required": q_cond + q_rad + q_ground > q_solar + q_metabolic,
    }


def simulate_sol(
    start_temp_k: float,
    latitude_deg: float = -4.5,
    solar_longitude: float = 0.0,
    r_value: float = HABITAT_INSULATION_R_VALUE,
    heater_power_w: float = HABITAT_HEATER_POWER_W,
    dust_storm: bool = False,
    panel_area_m2: float = HABITAT_SOLAR_PANEL_AREA_M2,
    panel_efficiency: float = HABITAT_SOLAR_PANEL_EFFICIENCY,
) -> dict:
    """Simulate one full sol of thermal + power dynamics.

    Runs 15-minute steps across a 24.6-hour sol. Returns end temperature,
    total heating used, and solar energy generated.
    """
    from solar import surface_irradiance
    from atmosphere import temperature_at_altitude

    step_hours = 0.25
    num_steps = int(MARS_SOL_HOURS / step_hours)
    temp_k = start_temp_k
    total_heating_kwh = 0.0
    total_solar_kwh = 0.0

    for i in range(num_steps):
        hour = i * step_hours
        ext_temp = temperature_at_altitude(0, latitude_deg, solar_longitude, hour, dust_storm)
        irr = surface_irradiance(latitude_deg, solar_longitude, hour, dust_storm=dust_storm)

        power_w = irr * panel_area_m2 * panel_efficiency
        total_solar_kwh += power_w * step_hours / 1000

        heater_w = heater_power_w if temp_k < HABITAT_TARGET_TEMP_K else 0.0
        result = thermal_step(temp_k, ext_temp, irr, heater_w, r_value=r_value, dt_seconds=step_hours * 3600)
        temp_k = result["interior_temp_k"]

        if heater_w > 0:
            total_heating_kwh += heater_w * step_hours / 1000

    return {
        "end_temp_k": round(temp_k, 2),
        "heating_kwh": round(total_heating_kwh, 2),
        "solar_kwh": round(total_solar_kwh, 2),
    }


if __name__ == "__main__":
    print("=== Habitat Thermal Model ===")
    ext_temp = 210.0  # -63°C
    req_heating = calculate_required_heating(ext_temp, 0.0)
    print(f"Required heating at night (-63°C external): {req_heating/1000.0:.1f} kW")
    
    req_heating_day = calculate_required_heating(ext_temp + 40, 300.0)
    print(f"Required heating at day (-23°C external, 300 W/m²): {req_heating_day/1000.0:.1f} kW")

