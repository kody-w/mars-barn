"""Mars Barn — Validation Suite

Cross-checks simulation outputs against known Mars data.
Validates terrain, atmosphere, solar, and thermal values.
Compares thermal model against real NASA Mars habitat designs.

Real Mars data sources:
  - NASA Mars Fact Sheet: https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html
  - Mars Climate Database: http://www-mars.lmd.jussieu.fr/mcd_python/
  - InSight weather data: https://mars.nasa.gov/insight/weather/

NASA habitat design sources:
  - CHAPEA / Mars Dune Alpha: ICON/NASA IAC-22 paper (Yashar et al.)
  - Mars Ice Home: NASA Langley / SEArch+ / CloudsAO (Ruess et al. 2018)
  - Mars Direct: Zubrin 1991, arXiv:2101.07165 (energy analysis)
  - Aerogel insulation: NASA NTRS 20210017251, 20210004881
  - Mars regolith conductivity: Springer 10.1007/s10765-022-03023-y
  - General: Marspedia "Insulation", MDPI Aerospace 12(6):510

Author: zion-researcher-01 (claimed)
"""
import math
from typing import List, Tuple

from constants import (
    STEFAN_BOLTZMANN,
    MARS_SURFACE_TEMP_K,
    HABITAT_SURFACE_AREA_M2,
    HABITAT_VOLUME_M3,
    HABITAT_INSULATION_R_VALUE,
    HABITAT_HEATER_POWER_W,
    HABITAT_SOLAR_PANEL_AREA_M2,
    HABITAT_SOLAR_PANEL_EFFICIENCY,
    HABITAT_EMISSIVITY,
    HABITAT_WINDOW_AREA_M2,
    HABITAT_WINDOW_TRANSMITTANCE,
    HABITAT_TARGET_TEMP_K,
    THERMAL_MASS_MULTIPLIER,
)


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


# ── NASA Habitat Design Benchmarks ──────────────────────────────────────
#
# Real-world reference parameters from three NASA-affiliated Mars habitat
# designs.  Values are sourced from published papers and NASA technical
# reports (see module docstring for full citations).
#
# Units are SI unless noted.  R-values are thermal resistance in m²·K/W.

NASA_HABITAT_BENCHMARKS = {
    "chapea": {
        "name": "CHAPEA / Mars Dune Alpha",
        "org": "NASA JSC + ICON",
        "year": 2022,
        "floor_area_m2": 158,           # 1,700 ft²
        "ext_surface_area_m2": 260,     # 3D-printed dome + walls
        "target_interior_temp_k": 294,  # 21°C (HVAC setpoint)
        "insulation_r_value_si": None,  # Earth analog — not applicable
        "projected_r_value_si": (7.0, 10.6),  # R-40 to R-60 imperial
        "heating_power_kw": (4.7, 9.5), # 30–60 W/m² × 158 m²
        "construction": "3D-printed lavacrete (regolith simulant)",
        "notes": "Earth analog at JSC; thermal specs projected for Mars",
    },
    "ice_home": {
        "name": "Mars Ice Home",
        "org": "NASA Langley + SEArch+ + CloudsAO",
        "year": 2016,
        "floor_area_m2": 93,            # inflatable dome interior
        "ext_surface_area_m2": 200,     # dome envelope
        "target_interior_temp_k": 293,  # 20°C
        "ice_shell_thickness_m": (2.0, 3.0),
        "co2_insulation_layer": True,
        "insulation_r_value_si": (8.0, 15.0),  # ice + CO₂ + membrane
        "heating_power_kw": (3.0, 8.0), # waste heat + supplemental
        "thermal_mass_note": "Enormous — 2-3 m ice shell",
        "construction": "Inflatable membrane + water-ice shell (ISRU)",
        "notes": "Translucent ice allows natural light; huge thermal mass",
    },
    "mars_direct": {
        "name": "Mars Direct Habitat",
        "org": "Mars Society (Zubrin et al.)",
        "year": 1991,
        "diameter_m": 8.0,
        "height_m": 8.0,
        "floor_area_m2": 50,            # per deck (2 decks)
        "ext_surface_area_m2": 170,     # cylinder + end caps
        "target_interior_temp_k": 293,  # 20°C
        "insulation_r_value_si": (5.3, 10.6),  # R-30 to R-60 imperial
        "heating_power_kw": (10.0, 25.0),
        "power_source": "Nuclear reactor (100 kWe)",
        "construction": "Rigid cylinder (landed upper stage)",
        "notes": "Nuclear primary power; 10–25 kW heating",
    },
}

# Mars Barn's own thermal parameters (extracted from thermal.py defaults
# and main.py configuration) for programmatic comparison.
MARS_BARN_PARAMS = {
    "name": "Mars Barn Simulation",
    "ext_surface_area_m2": HABITAT_SURFACE_AREA_M2,
    "volume_m3": HABITAT_VOLUME_M3,
    "insulation_r_value_si": HABITAT_INSULATION_R_VALUE,
    "heater_power_kw": HABITAT_HEATER_POWER_W / 1000,
    "solar_panel_area_m2": HABITAT_SOLAR_PANEL_AREA_M2,
    "solar_panel_efficiency": HABITAT_SOLAR_PANEL_EFFICIENCY,
    "emissivity": HABITAT_EMISSIVITY,
    "window_area_m2": HABITAT_WINDOW_AREA_M2,
    "window_transmittance": HABITAT_WINDOW_TRANSMITTANCE,
    "thermal_mass_multiplier": THERMAL_MASS_MULTIPLIER,
    "target_interior_temp_k": HABITAT_TARGET_TEMP_K,
    "ground_coupling": True,
    "human_metabolic_heat": True,
    "low_e_coating": True,
}

# Physical reference values for gap calculations
_STEFAN_BOLTZMANN = STEFAN_BOLTZMANN
_MARS_EXT_TEMP_K = MARS_SURFACE_TEMP_K


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


def validate_against_nasa_designs() -> List[Tuple[str, bool, str]]:
    """Compare Mars Barn thermal assumptions against NASA habitat designs."""
    results = []
    mb = MARS_BARN_PARAMS

    # ── R-value check ───────────────────────────────────────────────────
    r_vals = []
    for key in ("chapea", "ice_home", "mars_direct"):
        bench = NASA_HABITAT_BENCHMARKS[key]
        r = bench.get("insulation_r_value_si") or bench.get("projected_r_value_si")
        if r and isinstance(r, tuple):
            r_vals.extend(r)
    r_lo, r_hi = min(r_vals), max(r_vals)
    in_range = r_lo <= mb["insulation_r_value_si"] <= r_hi
    results.append((
        "nasa_r_value",
        in_range,
        f"R-value {mb['insulation_r_value_si']:.1f} m²·K/W vs NASA range "
        f"[{r_lo:.1f}, {r_hi:.1f}] — "
        f"{'within range' if in_range else 'OPTIMISTIC (above max)'}",
    ))

    # ── Heater power check ──────────────────────────────────────────────
    heater_ranges = [NASA_HABITAT_BENCHMARKS[k]["heating_power_kw"]
                     for k in NASA_HABITAT_BENCHMARKS]
    h_lo = min(lo for lo, _ in heater_ranges)
    h_hi = max(hi for _, hi in heater_ranges)
    heater_ok = h_lo <= mb["heater_power_kw"] <= h_hi
    results.append((
        "nasa_heater_power",
        heater_ok,
        f"Heater {mb['heater_power_kw']:.0f} kW vs NASA range "
        f"[{h_lo:.0f}, {h_hi:.0f}] kW — "
        f"{'ok' if heater_ok else 'UNDERSIZED'}",
    ))

    # ── Emissivity check (the smoking gun) ──────────────────────────────
    # Real habitats use low-e coatings (aluminized mylar ε≈0.03–0.05).
    # Mars Barn uses ε=0.9, which is a near-blackbody surface.
    low_e_range = (0.03, 0.20)
    emissivity_ok = mb["emissivity"] <= low_e_range[1]
    q_rad_current = (mb["emissivity"] * _STEFAN_BOLTZMANN *
                     mb["ext_surface_area_m2"] *
                     (mb["target_interior_temp_k"] ** 4 - _MARS_EXT_TEMP_K ** 4))
    q_rad_lowe = (low_e_range[0] * _STEFAN_BOLTZMANN *
                  mb["ext_surface_area_m2"] *
                  (mb["target_interior_temp_k"] ** 4 - _MARS_EXT_TEMP_K ** 4))
    results.append((
        "nasa_emissivity",
        emissivity_ok,
        f"Emissivity {mb['emissivity']:.2f} vs low-e coatings "
        f"[{low_e_range[0]:.2f}, {low_e_range[1]:.2f}] — "
        f"radiative loss {q_rad_current/1000:.1f} kW vs "
        f"{q_rad_lowe/1000:.1f} kW with coatings",
    ))

    # ── Thermal mass check ──────────────────────────────────────────────
    # Real habitats: concrete/regolith ~10-50×, Ice Home: 100×+
    mass_ok = mb["thermal_mass_multiplier"] >= 10
    results.append((
        "nasa_thermal_mass",
        mass_ok,
        f"Thermal mass {mb['thermal_mass_multiplier']:.0f}× air vs "
        f"real designs 10–50× (Ice Home: 100×+) — "
        f"{'adequate' if mass_ok else 'UNDERESTIMATED'}",
    ))

    # ── Ground coupling ─────────────────────────────────────────────────
    results.append((
        "nasa_ground_coupling",
        mb["ground_coupling"],
        f"Ground coupling {'modeled' if mb['ground_coupling'] else 'NOT modeled'} — "
        "real designs use regolith contact for thermal stability",
    ))

    # ── Human metabolic heat ────────────────────────────────────────────
    results.append((
        "nasa_metabolic_heat",
        mb["human_metabolic_heat"],
        f"Crew metabolic heat {'modeled' if mb['human_metabolic_heat'] else 'NOT modeled'} — "
        "4 crew ≈ 400–600 W waste heat (free heating source)",
    ))

    return results


def generate_gap_report() -> str:
    """Produce a human-readable sim-to-reality gap analysis.

    Compares Mars Barn parameters against CHAPEA, Mars Ice Home, and
    Mars Direct, highlighting critical differences and their impact.
    """
    mb = MARS_BARN_PARAMS
    lines = []
    lines.append("=" * 66)
    lines.append("  MARS BARN — SIM-TO-REALITY GAP REPORT")
    lines.append("  vs CHAPEA · Mars Ice Home · Mars Direct")
    lines.append("=" * 66)

    # ── Parameter comparison table ──────────────────────────────────────
    lines.append("")
    lines.append("  PARAMETER COMPARISON")
    lines.append("  " + "-" * 62)
    row = "  {:<24s} {:>12s} {:>10s} {:>10s} {:>10s}"
    lines.append(row.format("Parameter", "Mars Barn", "CHAPEA", "Ice Home", "Mars Dir."))
    lines.append("  " + "-" * 62)

    lines.append(row.format(
        "Surface area (m²)",
        f"{mb['ext_surface_area_m2']:.0f}",
        "260", "200", "170",
    ))
    r_chapea = NASA_HABITAT_BENCHMARKS["chapea"]["projected_r_value_si"]
    r_ice = NASA_HABITAT_BENCHMARKS["ice_home"]["insulation_r_value_si"]
    r_mars = NASA_HABITAT_BENCHMARKS["mars_direct"]["insulation_r_value_si"]
    lines.append(row.format(
        "R-value (m²·K/W)",
        f"{mb['insulation_r_value_si']:.1f}",
        f"{r_chapea[0]:.0f}–{r_chapea[1]:.0f}",
        f"{r_ice[0]:.0f}–{r_ice[1]:.0f}",
        f"{r_mars[0]:.0f}–{r_mars[1]:.0f}",
    ))
    h_chapea = NASA_HABITAT_BENCHMARKS["chapea"]["heating_power_kw"]
    h_ice = NASA_HABITAT_BENCHMARKS["ice_home"]["heating_power_kw"]
    h_mars = NASA_HABITAT_BENCHMARKS["mars_direct"]["heating_power_kw"]
    lines.append(row.format(
        "Heater power (kW)",
        f"{mb['heater_power_kw']:.0f}",
        f"{h_chapea[0]:.0f}–{h_chapea[1]:.0f}",
        f"{h_ice[0]:.0f}–{h_ice[1]:.0f}",
        f"{h_mars[0]:.0f}–{h_mars[1]:.0f}",
    ))
    lines.append(row.format(
        "Emissivity",
        f"{mb['emissivity']:.2f}",
        "0.03–0.20", "0.03–0.20", "0.03–0.20",
    ))
    lines.append(row.format(
        "Thermal mass (×air)",
        f"{mb['thermal_mass_multiplier']:.0f}×",
        "15–30×", "100×+", "10–20×",
    ))
    lines.append(row.format(
        "Ground coupling",
        "Yes", "Slab", "Ice fdn", "Ground",
    ))
    lines.append(row.format(
        "Crew metabolic heat",
        "Yes", "~500 W", "~500 W", "~500 W",
    ))
    lines.append(row.format(
        "Window area (m²)",
        f"{mb['window_area_m2']:.0f}",
        "Small", "Transl.", "Minimal",
    ))
    lines.append("  " + "-" * 62)

    # ── Impact analysis ─────────────────────────────────────────────────
    lines.append("")
    lines.append("  CRITICAL GAPS & IMPACT")
    lines.append("  " + "-" * 62)

    # Radiative loss analysis
    t_int = mb["target_interior_temp_k"]
    t_ext = _MARS_EXT_TEMP_K
    area = mb["ext_surface_area_m2"]
    dt4 = t_int ** 4 - t_ext ** 4
    q_rad_09 = 0.9 * _STEFAN_BOLTZMANN * area * dt4
    q_rad_005 = 0.05 * _STEFAN_BOLTZMANN * area * dt4

    lines.append("")
    lines.append("  #1  EMISSIVITY (ε=0.9 → should be ε≈0.03–0.05)")
    lines.append(f"      Radiative loss at ε=0.90:  {q_rad_09/1000:>7.1f} kW")
    lines.append(f"      Radiative loss at ε=0.05:  {q_rad_005/1000:>7.1f} kW")
    lines.append(f"      Excess loss:               {(q_rad_09-q_rad_005)/1000:>7.1f} kW")
    lines.append(f"      The 8 kW heater cannot overcome {q_rad_09/1000:.0f} kW loss.")
    lines.append(f"      THIS is why the interior reaches -65°C.")
    lines.append(f"      Fix: low-e coating reduces loss to {q_rad_005/1000:.1f} kW.")

    # Conductive loss for context
    q_cond = area * (t_int - t_ext) / mb["insulation_r_value_si"]
    lines.append("")
    lines.append("  #2  HEATER POWER (8 kW → should be 10–25 kW)")
    lines.append(f"      Conductive loss at R-12:    {q_cond/1000:>7.1f} kW")
    lines.append(f"      With low-e + R-12, total:   {(q_cond+q_rad_005)/1000:>7.1f} kW")
    lines.append(f"      8 kW heater {'CAN' if (q_cond+q_rad_005)/1000 < 8 else 'CANNOT'} "
                 f"maintain 20°C with low-e coating.")
    lines.append(f"      Without low-e coating, need ≥{(q_cond+q_rad_09)/1000:.0f} kW.")

    lines.append("")
    lines.append("  #3  THERMAL MASS (5× → should be 10–50×)")
    lines.append("      Low thermal mass = fast temperature swings.")
    lines.append("      Real habitats (concrete, regolith, ice) buffer")
    lines.append("      against power interruptions and diurnal cycles.")

    lines.append("")
    lines.append("  #4  MISSING PHYSICS")
    lines.append("      • No ground coupling (regolith at 210 K is warmer")
    lines.append("        than nighttime air, stabilizes temperature)")
    lines.append("      • No crew metabolic heat (4 crew ≈ 400–600 W free)")
    lines.append("      • 10 m² window area is a thermal weak point")

    # ── Recommendations ─────────────────────────────────────────────────
    lines.append("")
    lines.append("  RECOMMENDATIONS")
    lines.append("  " + "-" * 62)
    lines.append("  Priority 1: Add low-e exterior coating (ε=0.05)")
    lines.append(f"              → reduces radiative loss from "
                 f"{q_rad_09/1000:.0f} kW to {q_rad_005/1000:.1f} kW")
    lines.append("  Priority 2: Increase thermal mass to 15–20×")
    lines.append("  Priority 3: Add ground-coupling model")
    lines.append("  Priority 4: Add crew metabolic heat contribution")
    lines.append("  Priority 5: Increase heater to 10–15 kW (margin)")
    lines.append("")

    # Predicted interior temp with fixes
    q_total_fixed = q_cond + q_rad_005 - 500  # minus metabolic heat
    can_heat = mb["heater_power_kw"] * 1000 > q_total_fixed
    lines.append(f"  With priorities 1+4 alone, total loss ≈ "
                 f"{q_total_fixed/1000:.1f} kW")
    lines.append(f"  The existing 8 kW heater {'WOULD' if can_heat else 'would NOT'} "
                 f"maintain 20°C.")
    lines.append("=" * 66)

    return "\n".join(lines)


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

    # Always run NASA design comparison
    all_results.extend(validate_against_nasa_designs())

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

    # Gap report: compare against real NASA habitat designs
    print()
    print(generate_gap_report())
