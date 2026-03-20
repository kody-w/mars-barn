"""Mars Barn — Solar Irradiance Calculator

Calculate solar energy reaching the Mars surface given latitude, season,
time of day, and atmospheric conditions from the atmosphere module.

Mars reference data:
  - Solar constant at Mars: ~589 W/m² (about 43% of Earth)
  - Axial tilt: ~25.19°
  - Eccentric orbit means irradiance varies from 492 to 715 W/m²

Author: zion-coder-04 (claimed)
"""
import math
from typing import Optional

# Mars solar constants
SOLAR_CONSTANT_MARS_W_M2 = 589.0
ORBIT_ECCENTRICITY = 0.0934
AXIAL_TILT_RAD = math.radians(25.19)


def distance_factor(solar_longitude_deg: float) -> float:
    """Factor modifying solar constant based on orbital position.
    
    Mars has a highly elliptical orbit. Solar longitude (Ls) 250 is near perihelion (closest).
    Returns a multiplier ~0.83 to 1.21.
    """
    ls_rad = math.radians(solar_longitude_deg)
    # Simplified orbital distance factor
    distance_au = 1.524 * (1 - ORBIT_ECCENTRICITY**2) / (1 + ORBIT_ECCENTRICITY * math.cos(ls_rad - math.radians(250)))
    return (1.524 / distance_au) ** 2


def surface_irradiance(
    latitude_deg: float = 0.0,
    solar_longitude_deg: float = 0.0,
    hour: float = 12.0,
    atmospheric_pressure_pa: float = 610.0,
    dust_storm: bool = False,
) -> float:
    """Calculate direct solar irradiance at the surface in W/m².
    
    Accounts for:
    - Distance from the sun (orbital eccentricity)
    - Latitude and time of day (incidence angle)
    - Atmospheric scattering (opacity, increased by dust storms)
    """
    # Incident angle
    lat_rad = math.radians(latitude_deg)
    declination = math.asin(math.sin(AXIAL_TILT_RAD) * math.sin(math.radians(solar_longitude_deg)))
    
    hour_angle = math.radians((hour - 12) * 15)
    
    cos_zenith = (math.sin(lat_rad) * math.sin(declination) +
                  math.cos(lat_rad) * math.cos(declination) * math.cos(hour_angle))
                  
    if cos_zenith <= 0:
        return 0.0  # Nighttime
        
    # Top of atmosphere irradiance
    toa_irradiance = SOLAR_CONSTANT_MARS_W_M2 * distance_factor(solar_longitude_deg)
    
    # Atmospheric transmission
    optical_depth = 0.5 * (atmospheric_pressure_pa / 610.0)
    if dust_storm:
        optical_depth *= 4.0  # Dust storms significantly block light
        
    # Beer-Lambert law for transmission
    transmission = math.exp(-optical_depth / cos_zenith)
    
    return toa_irradiance * cos_zenith * transmission


if __name__ == "__main__":
    print("=== Mars Solar Irradiance (equator, Ls=0, clear) ===")
    for h in range(6, 19, 2):
        irr = surface_irradiance(hour=h)
        print(f"  Hour {h:02d}:00 | {irr:5.1f} W/m²")
    print()
    print("=== Dust Storm Impact (noon) ===")
    print(f"  Clear: {surface_irradiance(hour=12):.1f} W/m²")
    print(f"  Storm: {surface_irradiance(hour=12, dust_storm=True):.1f} W/m²")



# Reference panel area for energy calculations (m²)
REFERENCE_PANEL_AREA_M2 = 100.0

# Mars sol length in hours (24h 39m 35s)
MARS_SOL_HOURS = 24.66


def daily_energy(
    latitude_deg: float = 0.0,
    solar_longitude: float = 0.0,
    dust_storm: bool = False,
    solar_multiplier: float = 1.0,
    panel_area_m2: float = REFERENCE_PANEL_AREA_M2,
) -> dict:
    """Calculate total solar energy generated over one Mars sol.

    Integrates surface_irradiance() over daylight hours for a flat
    panel array at the given latitude and season.

    Returns dict with:
        total_kwh: total energy in kWh for the panel area
        peak_irradiance_w_m2: max irradiance during the sol
        daylight_hours: number of hours with nonzero irradiance
    """
    total_wh = 0.0
    peak_irr = 0.0
    daylight_h = 0.0
    step_hours = 0.5  # 30-minute integration steps

    hour = 0.0
    while hour < MARS_SOL_HOURS:
        irr = surface_irradiance(
            latitude_deg=latitude_deg,
            solar_longitude_deg=solar_longitude,
            hour=hour,
            dust_storm=dust_storm,
        )
        irr *= solar_multiplier
        if irr > 0:
            daylight_h += step_hours
            peak_irr = max(peak_irr, irr)
        total_wh += irr * panel_area_m2 * step_hours
        hour += step_hours

    return {
        "total_kwh": round(total_wh / 1000.0, 2),
        "peak_irradiance_w_m2": round(peak_irr, 1),
        "daylight_hours": round(daylight_h, 1),
    }
