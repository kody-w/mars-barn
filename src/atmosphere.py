"""Mars Barn — Atmosphere Model

Models Mars atmospheric pressure, temperature, and CO2 density
at varying altitudes, with dust storm event support.

Mars reference data (from constants.py — single source of truth):
  - Surface pressure: ~636 Pa (NASA global mean at areoid)
  - Surface temp: -63°C mean (range ~145–300 K)
  - Composition: 95.32% CO2, 2.7% N2, 1.6% Ar
  - Scale height: ~11.1 km
  - Dust storm: pressure can drop 10-25%, temp swings ±30°C

Author: zion-coder-06 (via Rappterbook frame 109, community audit #6484)
"""
import math
from typing import Optional

from constants import (
    BOLTZMANN,
    MARS_CO2_FRACTION,
    MARS_GRAVITY_M_S2,
    MARS_SCALE_HEIGHT_M,
    MARS_SURFACE_PRESSURE_PA,
    MARS_SURFACE_TEMP_K,
)

# CO2-dominated atmosphere molar mass (not in constants.py)
MOLAR_MASS_KG = 0.04334


def pressure_at_altitude(altitude_m: float, dust_storm: bool = False) -> float:
    """Atmospheric pressure in Pascals at given altitude.

    Uses barometric formula with Mars-specific scale height.
    Dust storms reduce effective pressure by ~15%.
    """
    p = MARS_SURFACE_PRESSURE_PA * math.exp(-altitude_m / MARS_SCALE_HEIGHT_M)
    if dust_storm:
        p *= 0.85  # pressure drop during dust storms
    return p


def temperature_at_altitude(
    altitude_m: float,
    latitude_deg: float = 0.0,
    solar_longitude: float = 0.0,
    hour: float = 12.0,
    dust_storm: bool = False,
) -> float:
    """Atmospheric temperature in Kelvin at given altitude.

    Accounts for:
    - Altitude lapse rate (~1.5 K/km on Mars)
    - Latitude variation (poles are colder)
    - Diurnal cycle (day/night swing ~40K at surface)
    - Seasonal variation via solar longitude
    - Dust storm thermal blanketing (+20K at night, -10K at day)
    """
    # Base: surface temperature with altitude lapse
    lapse_rate = 1.5e-3  # K per meter
    t = MARS_SURFACE_TEMP_K - lapse_rate * altitude_m

    # Latitude effect: poles are ~40K colder
    lat_factor = math.cos(math.radians(latitude_deg))
    t -= 40 * (1 - lat_factor)

    # Diurnal cycle: ±20K swing centered on local noon
    diurnal = 20 * math.cos(2 * math.pi * (hour - 14) / 24)
    t += diurnal

    # Seasonal: solar longitude 0-360°, warmest at Ls=250 (southern summer)
    seasonal = 15 * math.cos(math.radians(solar_longitude - 250))
    t += seasonal

    # Dust storm: thermal blanketing reduces diurnal swing
    if dust_storm:
        if 6 < hour < 18:  # daytime
            t -= 10
        else:  # nighttime
            t += 20

    return max(t, 100.0)  # physical floor


def co2_density(altitude_m: float, dust_storm: bool = False) -> float:
    """CO2 number density in molecules/m³ at given altitude.

    Derived from ideal gas law: n = P / (kT)
    """
    p = pressure_at_altitude(altitude_m, dust_storm)
    t = temperature_at_altitude(altitude_m)
    total_density = p / (BOLTZMANN * t)
    return total_density * MARS_CO2_FRACTION


def atmosphere_profile(
    max_altitude_m: float = 50000,
    steps: int = 20,
    latitude_deg: float = 0.0,
    hour: float = 12.0,
    dust_storm: bool = False,
) -> list:
    """Generate atmospheric profile at evenly spaced altitudes.

    Returns list of dicts with altitude, pressure, temperature, co2_density.
    """
    profile = []
    for i in range(steps + 1):
        alt = max_altitude_m * i / steps
        profile.append({
            "altitude_m": round(alt, 0),
            "pressure_pa": round(pressure_at_altitude(alt, dust_storm), 2),
            "temperature_k": round(temperature_at_altitude(alt, latitude_deg, hour=hour, dust_storm=dust_storm), 1),
            "co2_density_m3": round(co2_density(alt, dust_storm), 2),
        })
    return profile


if __name__ == "__main__":
    print("=== Mars Atmosphere Profile (equator, noon, clear) ===")
    for layer in atmosphere_profile(50000, 10):
        print(f"  {layer['altitude_m']:>7.0f}m | {layer['pressure_pa']:>7.1f} Pa | "
              f"{layer['temperature_k']:>5.1f} K ({layer['temperature_k']-273.15:>+6.1f}°C)")
    print()
    print("=== Dust Storm Comparison (surface) ===")
    print(f"  Clear: {pressure_at_altitude(0):.1f} Pa, {temperature_at_altitude(0)-273.15:.1f}°C")
    print(f"  Storm: {pressure_at_altitude(0, True):.1f} Pa, {temperature_at_altitude(0, dust_storm=True)-273.15:.1f}°C")
