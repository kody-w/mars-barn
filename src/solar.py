"""Mars Barn — Solar Irradiance Calculator

Calculates solar energy reaching the Mars surface given latitude,
season (solar longitude), time of day, and atmospheric conditions.

Mars reference data:
  - Solar constant at Mars: ~590 W/m² (mean, varies 493-718 due to eccentricity)
  - Orbital eccentricity: 0.0934 (vs Earth's 0.017)
  - Axial tilt: 25.19°
  - Sol duration: 88775 seconds (24h 37m 22s)

Author: zion-coder-04 (claimed)
"""
import math
from typing import Optional

# Mars solar constants
SOLAR_CONSTANT_MEAN = 590.0  # W/m² at Mars mean distance
MARS_ECCENTRICITY = 0.0934
MARS_AXIAL_TILT = 25.19  # degrees
SOL_SECONDS = 88775
PERIHELION_LS = 251.0  # solar longitude of perihelion


def solar_distance_factor(solar_longitude: float) -> float:
    """Inverse-square distance factor due to Mars orbital eccentricity.

    Returns multiplier for solar flux (>1 near perihelion, <1 near aphelion).
    """
    e = MARS_ECCENTRICITY
    theta = math.radians(solar_longitude - PERIHELION_LS)
    r_ratio = (1 - e ** 2) / (1 + e * math.cos(theta))
    return 1.0 / (r_ratio ** 2)


def declination(solar_longitude: float) -> float:
    """Solar declination in degrees for given solar longitude."""
    return MARS_AXIAL_TILT * math.sin(math.radians(solar_longitude))


def hour_angle(hour: float) -> float:
    """Hour angle in degrees. 0 at solar noon, negative in morning."""
    return (hour - 12.0) * 15.0  # 15° per hour


def cos_solar_zenith(
    latitude_deg: float,
    solar_longitude: float,
    hour: float,
) -> float:
    """Cosine of solar zenith angle.

    Returns value between -1 (sun below horizon) and 1 (sun directly overhead).
    """
    lat = math.radians(latitude_deg)
    dec = math.radians(declination(solar_longitude))
    ha = math.radians(hour_angle(hour))
    return (math.sin(lat) * math.sin(dec) +
            math.cos(lat) * math.cos(dec) * math.cos(ha))


def surface_irradiance(
    latitude_deg: float = 0.0,
    solar_longitude: float = 0.0,
    hour: float = 12.0,
    atmospheric_opacity: float = 0.3,
    dust_storm: bool = False,
    solar_multiplier: float = 1.0,
) -> float:
    """Solar irradiance at the Mars surface in W/m².

    Accounts for:
    - Orbital distance variation (eccentricity)
    - Solar zenith angle (latitude, season, time of day)
    - Atmospheric attenuation (optical depth / opacity)
    - Dust storm opacity increase
    - Event system multiplier
    """
    cos_z = cos_solar_zenith(latitude_deg, solar_longitude, hour)
    if cos_z <= 0:
        return 0.0  # Sun below horizon

    # Top-of-atmosphere flux
    toa_flux = SOLAR_CONSTANT_MEAN * solar_distance_factor(solar_longitude)

    # Atmospheric attenuation (Beer-Lambert law)
    tau = atmospheric_opacity
    if dust_storm:
        tau *= 3.0  # dust storms dramatically increase optical depth
    air_mass = 1.0 / max(cos_z, 0.01)  # avoid division by zero at horizon
    transmission = math.exp(-tau * air_mass)

    surface_flux = toa_flux * cos_z * transmission * solar_multiplier
    return max(surface_flux, 0.0)


def daily_energy(
    latitude_deg: float = 0.0,
    solar_longitude: float = 0.0,
    panel_area_m2: float = 100.0,
    panel_efficiency: float = 0.22,
    atmospheric_opacity: float = 0.3,
    dust_storm: bool = False,
    solar_multiplier: float = 1.0,
) -> dict:
    """Calculate total solar energy collected over one sol.

    Returns dict with peak_w, total_kwh, daylight_hours, and hourly profile.
    """
    hours_per_sol = SOL_SECONDS / 3600
    step = 0.5  # half-hour resolution
    total_wh = 0.0
    peak_w = 0.0
    daylight = 0.0
    hourly = []

    hour = 0.0
    while hour < hours_per_sol:
        irr = surface_irradiance(
            latitude_deg, solar_longitude, hour,
            atmospheric_opacity, dust_storm, solar_multiplier,
        )
        power_w = irr * panel_area_m2 * panel_efficiency
        total_wh += power_w * step
        peak_w = max(peak_w, power_w)
        if irr > 0:
            daylight += step

        if hour % 1.0 < step:  # log hourly
            hourly.append({"hour": round(hour, 1), "irradiance_wm2": round(irr, 1),
                           "power_w": round(power_w, 1)})
        hour += step

    return {
        "peak_w": round(peak_w, 1),
        "total_kwh": round(total_wh / 1000, 2),
        "daylight_hours": round(daylight, 1),
        "hourly": hourly,
    }


if __name__ == "__main__":
    print("=== Mars Solar Irradiance ===")
    for ls in [0, 90, 180, 270]:
        energy = daily_energy(latitude_deg=-4.5, solar_longitude=ls)
        print(f"  Ls={ls:>3d}°: peak {energy['peak_w']:>7.1f}W, "
              f"daily {energy['total_kwh']:>6.2f} kWh, "
              f"daylight {energy['daylight_hours']:.1f}h")
    print()
    print("=== Dust Storm Impact (Ls=250, equator) ===")
    clear = daily_energy(solar_longitude=250)
    storm = daily_energy(solar_longitude=250, dust_storm=True)
    pct = (1 - storm["total_kwh"] / max(clear["total_kwh"], 0.01)) * 100
    print(f"  Clear: {clear['total_kwh']:.2f} kWh/sol")
    print(f"  Storm: {storm['total_kwh']:.2f} kWh/sol ({pct:.0f}% reduction)")
