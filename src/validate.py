"""Mars Barn — Validation Suite

Cross-checks simulation outputs against known Mars data.
Validates terrain, atmosphere, solar, and thermal values.

Real Mars data sources:
  - NASA Mars Fact Sheet: https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html
  - Mars Climate Database: http://www-mars.lmd.jussieu.fr/mcd_python/
  - InSight weather data: https://mars.nasa.gov/insight/weather/

Author: zion-researcher-01 (claimed)
"""
from typing import List, Tuple


# Known Mars bounds (with generous margins for simulation)
VALIDATION_RULES = {
    "terrain": {
        "elevation_min_m": (-9000, "Below Hellas Planitia floor"),
        "elevation_max_m": (22000, "Above Olympus Mons summit"),
        "typical_range_m": (-2000, 5000),
    },
    "atmosphere": {
        "surface_pressure_pa": (400, 900, "Mars surface pressure range"),
        "surface_temp_k": (130, 310, "Mars surface temperature range"),
        "scale_height_m": (8000, 15000, "Atmospheric scale height"),
    },
    "solar": {
        "toa_irradiance_wm2": (450, 750, "Top-of-atmosphere solar flux at Mars"),
        "surface_peak_wm2": (0, 600, "Peak surface irradiance"),
        "daily_energy_kwh_100m2": (0.5, 80, "Daily energy from 100m² panels"),
    },
    "thermal": {
        "interior_temp_k": (260, 310, "Habitable interior range"),
        "heating_kwh_per_sol": (0, 200, "Daily heating energy budget"),
    },
}


def validate_terrain(grid: list) -> List[Tuple[str, bool, str]]:
    """Validate terrain heightmap against Mars bounds."""
    results = []
    if not grid or not grid[0]:
        results.append(("terrain_exists", False, "No terrain data"))
        return results

    flat = [v for row in grid for v in row]
    elev_min = min(flat)
    elev_max = max(flat)
    elev_mean = sum(flat) / len(flat)

    rules = VALIDATION_RULES["terrain"]

    results.append((
        "elevation_floor",
        elev_min >= rules["elevation_min_m"][0],
        f"Min elevation {elev_min:.0f}m >= {rules['elevation_min_m'][0]}m (Hellas floor)",
    ))
    results.append((
        "elevation_ceiling",
        elev_max <= rules["elevation_max_m"][0],
        f"Max elevation {elev_max:.0f}m <= {rules['elevation_max_m'][0]}m (Olympus summit)",
    ))
    results.append((
        "terrain_has_relief",
        elev_max - elev_min > 100,
        f"Relief {elev_max - elev_min:.0f}m > 100m minimum",
    ))
    results.append((
        "terrain_size",
        len(grid) >= 8 and len(grid[0]) >= 8,
        f"Grid size {len(grid[0])}x{len(grid)} >= 8x8 minimum",
    ))

    return results


def validate_atmosphere(profile: list) -> List[Tuple[str, bool, str]]:
    """Validate atmosphere profile against known Mars data."""
    results = []
    if not profile:
        results.append(("atmosphere_exists", False, "No profile data"))
        return results

    surface = profile[0]
    rules = VALIDATION_RULES["atmosphere"]

    p = surface.get("pressure_pa", 0)
    t = surface.get("temperature_k", 0)

    p_min, p_max = rules["surface_pressure_pa"][:2]
    results.append((
        "surface_pressure",
        p_min <= p <= p_max,
        f"Surface pressure {p:.1f} Pa in [{p_min}, {p_max}]",
    ))

    t_min, t_max = rules["surface_temp_k"][:2]
    results.append((
        "surface_temperature",
        t_min <= t <= t_max,
        f"Surface temp {t:.1f} K in [{t_min}, {t_max}]",
    ))

    # Pressure should decrease with altitude
    if len(profile) > 1:
        decreasing = all(
            profile[i]["pressure_pa"] >= profile[i + 1]["pressure_pa"]
            for i in range(len(profile) - 1)
        )
        results.append((
            "pressure_decreases",
            decreasing,
            "Pressure monotonically decreases with altitude",
        ))

    return results


def validate_solar(daily_energy: dict) -> List[Tuple[str, bool, str]]:
    """Validate solar energy calculations."""
    results = []
    rules = VALIDATION_RULES["solar"]

    peak = daily_energy.get("peak_w", 0)
    # Convert peak panel power back to irradiance (assume 100m² @ 22%)
    peak_irr = peak / (100 * 0.22) if peak > 0 else 0
    irr_min, irr_max = rules["surface_peak_wm2"][:2]
    results.append((
        "peak_irradiance",
        irr_min <= peak_irr <= irr_max,
        f"Peak irradiance ~{peak_irr:.0f} W/m² in [{irr_min}, {irr_max}]",
    ))

    total_kwh = daily_energy.get("total_kwh", 0)
    e_min, e_max = rules["daily_energy_kwh_100m2"][:2]
    results.append((
        "daily_energy",
        e_min <= total_kwh <= e_max,
        f"Daily energy {total_kwh:.2f} kWh in [{e_min}, {e_max}]",
    ))

    daylight = daily_energy.get("daylight_hours", 0)
    results.append((
        "daylight_hours",
        6 <= daylight <= 16,
        f"Daylight {daylight:.1f}h in [6, 16] (Mars range)",
    ))

    return results


def validate_thermal(thermal_result: dict) -> List[Tuple[str, bool, str]]:
    """Validate thermal simulation results."""
    results = []
    rules = VALIDATION_RULES["thermal"]

    min_t = thermal_result.get("min_temp_k", 0)
    max_t = thermal_result.get("max_temp_k", 0)
    t_lo, t_hi = rules["interior_temp_k"][:2]
    results.append((
        "interior_temp_range",
        t_lo <= min_t and max_t <= t_hi,
        f"Interior {min_t:.0f}-{max_t:.0f} K in [{t_lo}, {t_hi}]",
    ))

    heating = thermal_result.get("heating_kwh", 0)
    h_lo, h_hi = rules["heating_kwh_per_sol"][:2]
    results.append((
        "heating_budget",
        h_lo <= heating <= h_hi,
        f"Heating {heating:.1f} kWh/sol in [{h_lo}, {h_hi}]",
    ))

    return results


def run_all_validations(terrain_grid=None, atm_profile=None,
                         solar_energy=None, thermal_result=None) -> dict:
    """Run all available validations and return summary."""
    all_results = []

    if terrain_grid is not None:
        all_results.extend(validate_terrain(terrain_grid))
    if atm_profile is not None:
        all_results.extend(validate_atmosphere(atm_profile))
    if solar_energy is not None:
        all_results.extend(validate_solar(solar_energy))
    if thermal_result is not None:
        all_results.extend(validate_thermal(thermal_result))

    passed = sum(1 for _, ok, _ in all_results if ok)
    failed = sum(1 for _, ok, _ in all_results if not ok)

    return {
        "total": len(all_results),
        "passed": passed,
        "failed": failed,
        "results": [{"check": name, "passed": ok, "detail": detail}
                     for name, ok, detail in all_results],
    }


if __name__ == "__main__":
    from terrain import generate_heightmap
    from atmosphere import atmosphere_profile
    from solar import daily_energy

    print("=== Mars Barn Validation Suite ===\n")

    grid = generate_heightmap(32, 32, seed=42)
    profile = atmosphere_profile(50000, 10)
    energy = daily_energy(latitude_deg=-4.5, solar_longitude=250)

    report = run_all_validations(
        terrain_grid=grid,
        atm_profile=profile,
        solar_energy=energy,
    )

    for r in report["results"]:
        icon = "✅" if r["passed"] else "❌"
        print(f"  {icon} {r['check']}: {r['detail']}")

    print(f"\n  {report['passed']}/{report['total']} checks passed")
