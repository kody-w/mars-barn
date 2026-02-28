"""Mars Barn — Thermal Regulation System

Models heat flow in/out of the habitat given solar input and
atmospheric conditions. Balances heating, insulation, and radiative cooling.

Mars thermal challenges:
  - Exterior temp: -60°C mean, swings -140°C to +20°C
  - Interior target: 20°C (293 K)
  - Thin atmosphere = almost no convective insulation
  - Radiative losses dominate at night
  - Solar gain is the primary heat source

Author: unclaimed (open workstream)
"""
import math
from typing import Optional

# Physical constants
STEFAN_BOLTZMANN = 5.67e-8  # W/(m²·K⁴)
MARS_GROUND_TEMP_K = 210.0  # approximate ground temp

# Habitat defaults
HABITAT_SURFACE_AREA_M2 = 200.0  # exterior surface
HABITAT_VOLUME_M3 = 150.0
AIR_DENSITY_KG_M3 = 1.2  # pressurized interior at ~1 atm
AIR_SPECIFIC_HEAT = 1005  # J/(kg·K)
TARGET_TEMP_K = 293.0  # 20°C


def heat_loss_conduction(
    interior_temp_k: float,
    exterior_temp_k: float,
    r_value: float = 5.0,
    surface_area_m2: float = HABITAT_SURFACE_AREA_M2,
) -> float:
    """Conductive heat loss through habitat walls in watts.

    R-value is thermal resistance in m²·K/W.
    """
    delta_t = interior_temp_k - exterior_temp_k
    return surface_area_m2 * delta_t / max(r_value, 0.1)


def heat_loss_radiation(
    interior_temp_k: float,
    exterior_temp_k: float,
    emissivity: float = 0.9,
    surface_area_m2: float = HABITAT_SURFACE_AREA_M2,
) -> float:
    """Radiative heat loss in watts (Stefan-Boltzmann law).

    On Mars, the thin atmosphere means radiative loss is significant.
    """
    return (emissivity * STEFAN_BOLTZMANN * surface_area_m2 *
            (interior_temp_k ** 4 - exterior_temp_k ** 4))


def solar_heat_gain(
    irradiance_wm2: float,
    window_area_m2: float = 10.0,
    transmittance: float = 0.75,
) -> float:
    """Heat gained through habitat windows/solar collectors in watts."""
    return irradiance_wm2 * window_area_m2 * transmittance


def electrical_heating(
    available_power_w: float,
    efficiency: float = 0.95,
) -> float:
    """Heat from electrical heaters in watts."""
    return available_power_w * efficiency


def thermal_step(
    interior_temp_k: float,
    exterior_temp_k: float,
    solar_irradiance_wm2: float = 0.0,
    electrical_power_w: float = 0.0,
    r_value: float = 5.0,
    dt_seconds: float = 3600.0,
    surface_area_m2: float = HABITAT_SURFACE_AREA_M2,
    volume_m3: float = HABITAT_VOLUME_M3,
) -> dict:
    """Advance thermal state by one timestep.

    Returns dict with new interior temp and energy flows.
    """
    # Heat flows (positive = into habitat)
    q_solar = solar_heat_gain(solar_irradiance_wm2)
    q_electric = electrical_heating(electrical_power_w)
    q_cond_loss = heat_loss_conduction(interior_temp_k, exterior_temp_k, r_value, surface_area_m2)
    q_rad_loss = heat_loss_radiation(interior_temp_k, exterior_temp_k, surface_area_m2=surface_area_m2)

    # Net heat flow
    q_net = q_solar + q_electric - q_cond_loss - q_rad_loss

    # Temperature change: Q = m·c·ΔT
    thermal_mass = AIR_DENSITY_KG_M3 * volume_m3 * AIR_SPECIFIC_HEAT
    # Add habitat structure thermal mass (~5x air)
    thermal_mass *= 5.0
    delta_t = (q_net * dt_seconds) / thermal_mass

    new_temp = interior_temp_k + delta_t

    return {
        "interior_temp_k": round(new_temp, 2),
        "delta_t_k": round(delta_t, 3),
        "q_solar_w": round(q_solar, 1),
        "q_electric_w": round(q_electric, 1),
        "q_cond_loss_w": round(q_cond_loss, 1),
        "q_rad_loss_w": round(q_rad_loss, 1),
        "q_net_w": round(q_net, 1),
        "heating_required": q_net < 0,
    }


def simulate_sol(
    start_temp_k: float = TARGET_TEMP_K,
    latitude_deg: float = 0.0,
    solar_longitude: float = 0.0,
    r_value: float = 5.0,
    heater_power_w: float = 2000.0,
    dust_storm: bool = False,
) -> dict:
    """Simulate one sol of thermal behavior.

    Returns dict with min/max/mean temps, total energy used, and hourly profile.
    """
    from atmosphere import temperature_at_altitude
    from solar import surface_irradiance

    hours_per_sol = 24.616
    step_hours = 0.5
    step_seconds = step_hours * 3600

    temp = start_temp_k
    temps = []
    total_heating_kwh = 0.0
    hourly = []

    hour = 0.0
    while hour < hours_per_sol:
        ext_temp = temperature_at_altitude(0, latitude_deg, solar_longitude, hour, dust_storm)
        irr = surface_irradiance(latitude_deg, solar_longitude, hour, dust_storm=dust_storm)

        # Apply heating if below target
        heater = heater_power_w if temp < TARGET_TEMP_K else 0.0

        result = thermal_step(
            temp, ext_temp, irr, heater,
            r_value=r_value, dt_seconds=step_seconds,
        )

        temp = result["interior_temp_k"]
        temps.append(temp)
        if heater > 0:
            total_heating_kwh += heater * step_hours / 1000

        if hour % 2.0 < step_hours:
            hourly.append({
                "hour": round(hour, 1),
                "interior_k": round(temp, 1),
                "exterior_k": round(ext_temp, 1),
                "irradiance": round(irr, 1),
                "heating": heater > 0,
            })

        hour += step_hours

    return {
        "min_temp_k": round(min(temps), 1),
        "max_temp_k": round(max(temps), 1),
        "mean_temp_k": round(sum(temps) / len(temps), 1),
        "heating_kwh": round(total_heating_kwh, 2),
        "end_temp_k": round(temp, 1),
        "hourly": hourly,
    }


if __name__ == "__main__":
    print("=== Mars Habitat Thermal Simulation (1 sol) ===")
    result = simulate_sol(latitude_deg=-4.5, solar_longitude=250)
    print(f"  Interior temp: {result['min_temp_k']-273.15:+.1f}°C to {result['max_temp_k']-273.15:+.1f}°C "
          f"(mean {result['mean_temp_k']-273.15:+.1f}°C)")
    print(f"  Heating energy: {result['heating_kwh']:.2f} kWh/sol")
    print()
    print("=== Dust Storm Comparison ===")
    storm = simulate_sol(latitude_deg=-4.5, solar_longitude=250, dust_storm=True)
    print(f"  Storm heating: {storm['heating_kwh']:.2f} kWh/sol "
          f"({storm['heating_kwh']-result['heating_kwh']:+.2f} vs clear)")
