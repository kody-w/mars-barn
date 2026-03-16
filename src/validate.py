"""Mars Barn — Validation Suite

Cross-check simulation outputs against known Mars data. Validate terrain
elevation ranges, atmospheric pressure, solar flux, and thermal bounds.

Author: zion-researcher-01 (claimed)
"""
from terrain import generate_heightmap, elevation_stats
from atmosphere import pressure_at_altitude, temperature_at_altitude
from solar import surface_irradiance
from thermal import calculate_required_heating

def validate_terrain():
    """Validate terrain elevation bounds."""
    print("Validating Terrain...")
    grid = generate_heightmap(32, 32)
    stats = elevation_stats(grid)
    assert -8200 <= stats["min_m"], "Elevation too low"
    assert stats["max_m"] <= 21229, "Elevation too high"
    print("  ✓ Terrain bounds within Mars extremes limits.")

def validate_atmosphere():
    """Validate atmospheric pressure and temperature."""
    print("Validating Atmosphere...")
    p_surf = pressure_at_altitude(0)
    assert 500 <= p_surf <= 700, f"Surface pressure anomaly: {p_surf}"
    t_surf = temperature_at_altitude(0)
    assert 130 <= t_surf <= 300, f"Surface temperature anomaly: {t_surf}"
    print("  ✓ Atmosphere values within nominal limits.")

def validate_solar():
    """Validate solar irradiance."""
    print("Validating Solar Irradiance...")
    irr_max = surface_irradiance(hour=12)
    assert 0 < irr_max <= 715, f"Solar max anomaly: {irr_max}"
    irr_night = surface_irradiance(hour=0)
    assert irr_night == 0, f"Solar night anomaly: {irr_night}"
    print("  ✓ Solar irradiance within nominal Mars limits.")

def validate_thermal():
    """Validate thermal subsystem bounds."""
    print("Validating Thermal System...")
    heat_night = calculate_required_heating(external_temp_k=150.0, solar_irradiance_w_m2=0.0)
    assert heat_night > 1000, f"Thermal night heating too low: {heat_night}"
    heat_day = calculate_required_heating(external_temp_k=290.0, solar_irradiance_w_m2=500.0)
    assert heat_day < heat_night, "Day heating should be less than night heating"
    print("  ✓ Thermal heating bounds match expected dynamics.")


def run_all_validations(terrain_grid=None, atm_profile=None, solar_energy=None) -> dict:
    """Run all validation checks and return results dict."""
    results = []

    # Terrain
    try:
        if terrain_grid:
            stats = elevation_stats(terrain_grid)
            ok = -8200 <= stats["min_m"] and stats["max_m"] <= 21229
            results.append({"check": "terrain_bounds", "passed": ok, "detail": f"[{stats['min_m']}m, {stats['max_m']}m]"})
        else:
            validate_terrain()
            results.append({"check": "terrain_bounds", "passed": True, "detail": "OK"})
    except Exception as e:
        results.append({"check": "terrain_bounds", "passed": False, "detail": str(e)})

    # Atmosphere
    try:
        validate_atmosphere()
        results.append({"check": "atmosphere", "passed": True, "detail": "OK"})
    except Exception as e:
        results.append({"check": "atmosphere", "passed": False, "detail": str(e)})

    # Solar
    try:
        validate_solar()
        results.append({"check": "solar", "passed": True, "detail": "OK"})
    except Exception as e:
        results.append({"check": "solar", "passed": False, "detail": str(e)})

    # Thermal
    try:
        validate_thermal()
        results.append({"check": "thermal", "passed": True, "detail": "OK"})
    except Exception as e:
        results.append({"check": "thermal", "passed": False, "detail": str(e)})

    passed = sum(1 for r in results if r["passed"])
    return {"passed": passed, "total": len(results), "results": results}


if __name__ == "__main__":
    print("=== Mars Barn Validation Suite ===")
    validate_terrain()
    validate_atmosphere()
    validate_solar()
    validate_thermal()
    print("All subsystems passed validation.")

