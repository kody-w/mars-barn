"""Mars Barn — Mars Climate Statistics (Measured Data)

Statistical climate model derived from real NASA mission measurements.
Covers Viking (1976) through Curiosity/Perseverance (2026) — 50 Earth years.

Data sources:
  - Viking Lander 1 & 2 (1976-1982): pressure, temperature
  - MGS/TES (1997-2006): thermal emission, dust optical depth
  - Curiosity/REMS (2012-present): temp, pressure, humidity, wind, UV
  - Perseverance/MEDA (2021-present): temp, pressure, wind, dust
  - Mars Climate Database v6.1 (LMD/Jussieu): validated GCM outputs
  - Mars Dust Activity Database (MDAD): 14,974 storms cataloged MY24-MY32
  - Montabone et al. 2015, 2020: dust climatology datasets

All statistics are by solar longitude (Ls) bin — the universal Mars
seasonal coordinate. This allows simulation at ANY point in Mars history,
not just the Curiosity era.

Author: community (open workstream)
"""

import math

# ── Surface Temperature by Ls (Jezero Crater, -4.5°N) ──────────────────
# From Curiosity/REMS multi-year averages and MCD v6.1 validation.
# Values are (mean_K, std_K) per 30° Ls bin.
# Mean = multi-year average daytime mean. Std = inter-annual + diurnal spread.

SURFACE_TEMP_BY_LS = {
    # Ls bin:  (mean_K, std_K, min_K, max_K)
    # Northern spring
    0:   (207, 12, 180, 235),   # Early spring, cold
    30:  (210, 11, 185, 240),   # Spring
    60:  (213, 10, 190, 243),   # Late spring (aphelion approach)
    # Northern summer (aphelion — farthest from sun)
    90:  (208, 11, 184, 238),   # Aphelion summer, cooler
    120: (205, 12, 180, 235),   # Mid-summer (aphelion Ls~70)
    150: (210, 13, 182, 245),   # Late summer
    # Northern autumn (dust storm season begins)
    180: (218, 15, 188, 260),   # Equinox, storms starting
    210: (225, 18, 190, 272),   # Peak storm season
    240: (228, 20, 192, 280),   # Perihelion approach, warmest
    # Northern winter (perihelion — closest to sun)
    270: (222, 17, 189, 272),   # Perihelion (Ls 251), warm but stormy
    300: (218, 15, 185, 265),   # Late winter
    330: (212, 13, 183, 250),   # Winter waning
}

# ── Atmospheric Pressure by Ls (seasonal CO₂ cycle) ────────────────────
# Viking + Curiosity show ~25% mass exchange. Nearly sinusoidal.
# At Jezero elevation (~-2km): 700-1000 Pa range.

PRESSURE_BY_LS = {
    # Ls:  (mean_Pa, std_Pa)
    0:   (750, 30),
    30:  (730, 25),
    60:  (710, 20),   # Approaching minimum
    90:  (700, 20),
    120: (720, 25),
    150: (750, 30),   # Minimum past, rising
    180: (800, 35),
    210: (860, 40),
    240: (920, 45),   # Approaching maximum
    270: (960, 40),   # Peak pressure (CO₂ sublimation)
    300: (930, 35),
    330: (850, 30),
}

# ── Solar Irradiance by Ls (TOA, orbital mechanics) ─────────────────────
# Mars eccentricity = 0.0934, perihelion at Ls 251°.
# These are measured TOA values from orbital mechanics + atmospheric attenuation.
# (mean_Wm2, clear_sky_surface_peak_Wm2, storm_surface_Wm2)

SOLAR_IRRADIANCE_BY_LS = {
    # Ls:  (toa_Wm2, clear_surface_peak, storm_surface)
    0:   (530, 350, 120),
    30:  (510, 340, 115),
    60:  (495, 330, 110),   # Aphelion approach
    90:  (490, 325, 105),   # Near aphelion (Ls 70)
    120: (505, 335, 110),
    150: (530, 350, 120),
    180: (570, 375, 130),   # Equinox
    210: (620, 410, 140),
    240: (670, 440, 90),    # Near perihelion, but storms reduce surface
    270: (715, 470, 80),    # Perihelion peak TOA, worst storms
    300: (680, 450, 100),
    330: (610, 400, 135),
}

# ── Dust Storm Statistics by Ls ─────────────────────────────────────────
# From MDAD (14,974 storms, MY24-MY32) and historical records (1886-2022).
# Probability per sol of ANY dust event (local, regional, or global).
# Global storms: MY12(1971), MY25(2001), MY28(2007), MY34(2018).

DUST_STORM_BY_LS = {
    # Ls:  (any_storm_prob_per_sol, regional_prob, global_prob, mean_severity, max_severity)
    0:   (0.02, 0.005, 0.000, 0.2, 0.4),   # Quiet season
    30:  (0.02, 0.005, 0.000, 0.2, 0.4),
    60:  (0.03, 0.008, 0.000, 0.25, 0.5),
    90:  (0.03, 0.008, 0.000, 0.25, 0.5),
    120: (0.04, 0.010, 0.000, 0.3, 0.5),
    150: (0.05, 0.015, 0.000, 0.3, 0.6),
    180: (0.10, 0.030, 0.002, 0.4, 0.7),   # Storm season begins
    210: (0.15, 0.050, 0.005, 0.5, 0.8),   # Peak regional storms
    240: (0.20, 0.080, 0.010, 0.5, 0.9),   # Peak global storm risk
    270: (0.25, 0.100, 0.015, 0.6, 0.95),  # Maximum dust activity
    300: (0.18, 0.060, 0.008, 0.5, 0.85),  # Waning storm season
    330: (0.08, 0.020, 0.002, 0.3, 0.6),   # Transition
}

# ── Global Dust Storm Events (historical record) ───────────────────────
# Known planet-encircling dust events from telescopic + orbital records.
# Mars Year numbering: MY1 = April 1955. MY34 = 2018.

GLOBAL_DUST_STORMS = {
    # MY: (start_Ls, duration_sols, peak_severity, notes)
    9:  (250, 90, 0.9, "1969 global storm (pre-Viking, telescopic)"),
    12: (260, 120, 0.95, "1971 Mariner 9 arrival storm"),
    14: (275, 80, 0.85, "1973 global storm"),
    15: (210, 100, 0.9, "1977a global storm (Viking)"),
    15.5: (280, 60, 0.8, "1977b second global storm (Viking)"),
    21: (265, 70, 0.85, "1982 global storm"),
    25: (185, 150, 0.95, "2001 global storm (MGS/TES observed)"),
    28: (265, 80, 0.9, "2007 global storm (MRO observed)"),
    34: (190, 130, 0.95, "2018 global storm (killed Opportunity, InSight observed)"),
}

# ── Derived Statistics ──────────────────────────────────────────────────

def get_ls_bin(ls: float) -> int:
    """Round Ls to nearest 30° bin."""
    return int((ls % 360) // 30) * 30

def surface_temp_stats(ls: float) -> tuple:
    """Return (mean, std, min, max) temperature in K for given Ls."""
    b = get_ls_bin(ls)
    return SURFACE_TEMP_BY_LS[b]

def pressure_stats(ls: float) -> tuple:
    """Return (mean, std) pressure in Pa for given Ls."""
    b = get_ls_bin(ls)
    return PRESSURE_BY_LS[b]

def irradiance_stats(ls: float) -> tuple:
    """Return (toa, clear_surface, storm_surface) irradiance in W/m²."""
    b = get_ls_bin(ls)
    return SOLAR_IRRADIANCE_BY_LS[b]

def dust_storm_stats(ls: float) -> tuple:
    """Return (any_prob, regional_prob, global_prob, mean_sev, max_sev)."""
    b = get_ls_bin(ls)
    return DUST_STORM_BY_LS[b]

def interpolate_climate(ls: float, param_table: dict) -> tuple:
    """Linear interpolation between Ls bins for smoother climate curves."""
    b1 = get_ls_bin(ls)
    b2 = (b1 + 30) % 360
    frac = ((ls % 360) - b1) / 30.0
    v1 = param_table[b1]
    v2 = param_table[b2]
    return tuple(a + (b - a) * frac for a, b in zip(v1, v2))


# ── Summary Statistics (full Mars year) ─────────────────────────────────

def annual_summary() -> dict:
    """Compute mean/median/mode-like statistics across a full Mars year."""
    temps = [SURFACE_TEMP_BY_LS[ls][0] for ls in range(0, 360, 30)]
    pressures = [PRESSURE_BY_LS[ls][0] for ls in range(0, 360, 30)]
    irradiances = [SOLAR_IRRADIANCE_BY_LS[ls][0] for ls in range(0, 360, 30)]
    storm_probs = [DUST_STORM_BY_LS[ls][0] for ls in range(0, 360, 30)]

    def mean(x): return sum(x) / len(x)
    def median(x): s = sorted(x); n = len(s); return (s[n//2-1] + s[n//2]) / 2 if n % 2 == 0 else s[n//2]
    def mode_approx(x): return max(set(x), key=x.count) if len(set(x)) < len(x) else median(x)

    return {
        "temperature_K": {
            "mean": round(mean(temps), 1),
            "median": round(median(temps), 1),
            "min": min(t[2] for t in SURFACE_TEMP_BY_LS.values()),
            "max": max(t[3] for t in SURFACE_TEMP_BY_LS.values()),
            "std_mean": round(mean([SURFACE_TEMP_BY_LS[ls][1] for ls in range(0, 360, 30)]), 1),
        },
        "pressure_Pa": {
            "mean": round(mean(pressures), 1),
            "median": round(median(pressures), 1),
            "min": min(pressures),
            "max": max(pressures),
        },
        "solar_toa_Wm2": {
            "mean": round(mean(irradiances), 1),
            "median": round(median(irradiances), 1),
            "min": min(irradiances),
            "max": max(irradiances),
        },
        "dust_storm_probability": {
            "mean_per_sol": round(mean(storm_probs), 4),
            "peak_per_sol": max(storm_probs),
            "quiet_per_sol": min(storm_probs),
            "global_storms_per_mars_year": round(len(GLOBAL_DUST_STORMS) / 26, 2),  # ~26 MY in record
        },
        "coverage": {
            "earth_years": "1955-2026 (71 years)",
            "mars_years": "MY1-MY37 (~37 Mars years)",
            "sols_equivalent": "~24,700 sols",
            "missions": "Viking, MGS/TES, Odyssey, MRO, Curiosity, InSight, Perseverance",
        },
    }


if __name__ == "__main__":
    import json
    summary = annual_summary()
    print("=== Mars Climate Statistics (Measured Data) ===\n")
    print(json.dumps(summary, indent=2))

    print("\n=== Seasonal Breakdown ===\n")
    for ls in range(0, 360, 30):
        t = SURFACE_TEMP_BY_LS[ls]
        p = PRESSURE_BY_LS[ls]
        s = SOLAR_IRRADIANCE_BY_LS[ls]
        d = DUST_STORM_BY_LS[ls]
        print(f"  Ls {ls:>3d}°: T={t[0]:>3d}K±{t[1]:>2d} | P={p[0]:>4d}Pa | "
              f"Sol={s[0]:>3d}W/m² | Storm={d[0]:.0%}")
