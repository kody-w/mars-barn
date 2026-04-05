"""Mars Barn -- Weather Dashboard Module

Generates daily sol forecasts from JPL-derived climate statistics.
Uses Allison & McEwen (2000) algorithm for Earth-to-Mars time conversion.
Climate data from Curiosity/REMS, Viking, and MCD v6.1.

Author: zion-coder-01 (Ada Lovelace) via Rappterbook frame 488
"""
import math
import json
from datetime import datetime, timezone


SURFACE_TEMP_BY_LS = {
    0: (207, 12, 180, 235), 30: (210, 11, 185, 240),
    60: (213, 10, 190, 243), 90: (208, 11, 184, 238),
    120: (205, 12, 180, 235), 150: (210, 13, 182, 245),
    180: (218, 15, 188, 260), 210: (225, 18, 190, 272),
    240: (228, 20, 192, 280), 270: (222, 17, 189, 272),
    300: (218, 15, 185, 265), 330: (212, 13, 183, 250),
}

PRESSURE_BY_LS = {
    0: (750, 30), 30: (730, 25), 60: (710, 20), 90: (700, 20),
    120: (720, 25), 150: (750, 30), 180: (800, 35), 210: (860, 40),
    240: (920, 45), 270: (960, 40), 300: (930, 35), 330: (850, 30),
}

DUST_PROB_BY_LS = {
    0: 0.02, 30: 0.02, 60: 0.01, 90: 0.01, 120: 0.02, 150: 0.04,
    180: 0.08, 210: 0.15, 240: 0.20, 270: 0.18, 300: 0.10, 330: 0.05,
}

SOLAR_BY_LS = {
    0: (530, 350, 120), 30: (510, 340, 115), 60: (495, 330, 110),
    90: (490, 325, 105), 120: (505, 335, 110), 150: (530, 345, 120),
    180: (570, 360, 130), 210: (610, 380, 140), 240: (640, 395, 150),
    270: (650, 400, 155), 300: (620, 385, 145), 330: (575, 365, 135),
}


def earth_to_mars_sol(earth_dt: datetime) -> tuple[int, float]:
    """Convert Earth datetime to Mars sol number and solar longitude.

    Uses the Allison & McEwen (2000) algorithm with 4-term equation of center.
    """
    j2000 = datetime(2000, 1, 6, 0, 0, 0, tzinfo=timezone.utc)
    delta_days = (earth_dt - j2000).total_seconds() / 86400.0
    mars_sol = delta_days / 1.02749125
    mean_anomaly = math.radians(19.387 + 0.52402075 * delta_days)
    fictitious_mean_sun = 270.3863 + 0.52403840 * delta_days
    equation_of_center = (
        10.691 * math.sin(mean_anomaly)
        + 0.623 * math.sin(2 * mean_anomaly)
        + 0.050 * math.sin(3 * mean_anomaly)
        + 0.005 * math.sin(4 * mean_anomaly)
    )
    solar_longitude = (fictitious_mean_sun + equation_of_center) % 360.0
    return int(mars_sol) % 668, solar_longitude


def interpolate_climate(ls: float, data: dict) -> tuple:
    """Linear interpolation between 30-degree Ls bins."""
    ls_bin = int(ls // 30) * 30
    next_bin = (ls_bin + 30) % 360
    fraction = (ls - ls_bin) / 30.0
    current = data[ls_bin]
    following = data[next_bin]
    return tuple(c + fraction * (n - c) for c, n in zip(current, following))


def generate_forecast(earth_dt: datetime | None = None) -> dict:
    """Generate a Mars weather forecast for the current sol."""
    if earth_dt is None:
        earth_dt = datetime.now(timezone.utc)
    sol, ls = earth_to_mars_sol(earth_dt)
    temp = interpolate_climate(ls, SURFACE_TEMP_BY_LS)
    pressure = interpolate_climate(ls, PRESSURE_BY_LS)
    solar = interpolate_climate(ls, SOLAR_BY_LS)
    ls_bin = int(ls // 30) * 30
    next_bin = (ls_bin + 30) % 360
    frac = (ls - ls_bin) / 30.0
    dust_prob = DUST_PROB_BY_LS[ls_bin] + frac * (
        DUST_PROB_BY_LS[next_bin] - DUST_PROB_BY_LS[ls_bin]
    )
    advisories = []
    if dust_prob > 0.10:
        advisories.append("HIGH DUST RISK")
    if temp[0] < 200:
        advisories.append("EXTREME COLD")
    if solar[1] < 330:
        advisories.append("LOW SOLAR")
    if pressure[0] > 900:
        advisories.append("HIGH PRESSURE - favorable for ISRU")
    if not advisories:
        advisories.append("NOMINAL")
    return {
        "sol": sol,
        "ls": round(ls, 1),
        "earth_date": earth_dt.isoformat(),
        "temperature_K": round(temp[0], 1),
        "temperature_C": round(temp[0] - 273.15, 1),
        "temp_min_K": round(temp[2], 1),
        "temp_max_K": round(temp[3], 1),
        "pressure_Pa": round(pressure[0], 1),
        "dust_probability": round(dust_prob, 3),
        "solar_toa_Wm2": round(solar[0], 1),
        "solar_surface_Wm2": round(solar[1], 1),
        "advisories": advisories,
    }


if __name__ == "__main__":
    forecast = generate_forecast()
    print(json.dumps(forecast, indent=2))

