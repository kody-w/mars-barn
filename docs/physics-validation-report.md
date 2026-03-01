---
layout: default
title: Physics Validation Report
---

# Physics Validation Report — Mars Barn

[← Back to Home](./)


**Date:** 2026-03-01  
**Method:** Cross-reference of every physical constant and formula in the codebase against NASA/JPL Mars reference data  
**References:**
- NASA Mars Fact Sheet (nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html)
- JPL Planetary Physical Parameters (ssd.jpl.nasa.gov/planets/phys_par.html)
- NASA Mars Exploration (mars.nasa.gov)
- NIST CODATA 2018 (for universal constants)
- Mars Climate Database (www-mars.lmd.jussieu.fr)

---

## Summary

| Status | Count |
|--------|-------|
| ✅ Correct | 14 |
| ⚠️ Suspiciously rounded / minor discrepancy | 4 |
| ❌ Wrong | 0 |
| 🔇 Dead code (defined but unused) | 1 |
| 📐 No uncertainty bounds | All constants |

---

## Detailed Findings

### Previously Reported Errors (All Fixed)

#### 1. Sol duration in hours — ✅ FIXED
- **Files:** `thermal.py`, `main.py`
- **Was:** `hours_per_sol = 24.616` (hardcoded)
- **Now:** Uses `MARS_SOL_HOURS` from `constants.py` (88,775 s ÷ 3600 = 24.6597h)

#### 2. Sol duration docstring comment — ✅ FIXED
- **File:** `solar.py:10`
- **Now:** `"Sol duration: 88775 seconds (24h 39m 35s)"` — correct.

#### 3. Solar longitude advance rate — ✅ FIXED
- **File:** `main.py:66`
- **Was:** hardcoded `0.524`
- **Now:** Uses `MARS_LS_PER_SOL` from `constants.py` (0.5385°/sol)

---

### ⚠️ SUSPICIOUSLY ROUNDED / MINOR DISCREPANCIES

#### 4. Surface pressure
- **File:** `atmosphere.py:20`
- **Code:** `SURFACE_PRESSURE_PA = 610.0`
- **NASA Fact Sheet:** 636 Pa (at mean radius)
- **Discussion:** 610 Pa is the commonly-cited "triple point of water" approximation, and real pressure ranges 400–900 Pa by location/season. However, NASA's reference value at mean radius is 636 Pa (~4% higher). The code should either use 636 Pa or document why 610 Pa was chosen.
- **Severity:** Low — within natural variability, but not the canonical reference value.

#### 5. Mean solar constant
- **File:** `solar.py:18`
- **Code:** `SOLAR_CONSTANT_MEAN = 590.0  # W/m²`
- **Calculated:** Solar constant at Earth (1361 W/m²) ÷ 1.524² AU = **586.2 W/m²**
- **Discrepancy:** +0.65% (3.8 W/m²). Commonly cited as "~590" in popular sources, but precise inverse-square law gives 586.
- **Severity:** Low — within the range of literature values (some sources cite 589–595).

#### 6. Gravity
- **File:** `atmosphere.py:24`
- **Code:** `GRAVITY_M_S2 = 3.721`
- **NASA/JPL:** 3.72076 m/s² (surface equatorial)
- **Discrepancy:** +0.006% — essentially correct. Most sources round to 3.71 m/s²; the code uses 3.721 which is slightly more precise than necessary but accurate.
- **Severity:** Negligible.

#### 7. CO₂ fraction
- **File:** `atmosphere.py:23`
- **Code:** `CO2_FRACTION = 0.953`
- **NASA:** 95.32% → 0.9532
- **Discrepancy:** Rounded from 0.9532 to 0.953 (−0.02%).
- **Severity:** Negligible.

---

### ✅ CORRECT

| # | Constant | File:Line | Code Value | Reference Value | Status |
|---|----------|-----------|------------|-----------------|--------|
| 8 | Surface temp (mean) | `atmosphere.py:21` | 210.0 K | ~210 K (−63°C) | ✅ |
| 9 | Scale height | `atmosphere.py:22` | 11,100 m | 11.1 km | ✅ |
| 10 | Molar mass (weighted) | `atmosphere.py:25` | 0.04334 kg/mol | 0.953×44.01 + 0.027×28.01 + 0.016×39.95 = 43.34 g/mol | ✅ |
| 11 | Boltzmann constant | `atmosphere.py:87` | 1.381×10⁻²³ J/K | NIST: 1.380649×10⁻²³ (exact) | ✅ |
| 12 | Orbital eccentricity | `solar.py:19` | 0.0934 | JPL: 0.09341233 | ✅ |
| 13 | Axial tilt | `solar.py:20` | 25.19° | NASA: 25.19° | ✅ |
| 14 | Sol duration (seconds) | `solar.py:21` | 88,775 s | 88,775.245 s | ✅ |
| 15 | Perihelion Ls | `solar.py:22` | 251.0° | ~251° | ✅ |
| 16 | Stefan-Boltzmann const | `thermal.py:19` | 5.67×10⁻⁸ W/(m²·K⁴) | NIST: 5.670374×10⁻⁸ | ✅ |
| 17 | Lapse rate | `atmosphere.py:57` | 1.5 K/km | Literature: 1.5–2.5 K/km | ✅ |
| 18 | Atmospheric composition | `atmosphere.py:9` | 95.3% CO₂, 2.7% N₂, 1.6% Ar | NASA: 95.32%, 2.7%, 1.6% | ✅ |

---

### 🔇 DEAD CODE

#### 19. MOLAR_MASS_KG is defined but never used
- **File:** `atmosphere.py:25`
- **Code:** `MOLAR_MASS_KG = 0.04334`
- **Issue:** This constant is never referenced anywhere in the codebase. The `co2_density()` function uses the Boltzmann constant (per-molecule ideal gas law: n = P/kT) rather than the molar gas constant form (n = P/RT). The value itself is correct, but it's dead code.

---

### 📐 MISSING UNCERTAINTY BOUNDS

No constant in the codebase includes uncertainty information. For a habitat survival simulation, this means:

- **No error bars** on any physical parameter
- **No sensitivity analysis** possible without manual perturbation
- **No way to distinguish** between "this constant is known to ±0.01%" vs "this is a rough estimate ±20%"

Constants with significant real-world uncertainty that should be annotated:
| Constant | Typical uncertainty |
|----------|-------------------|
| Surface pressure | ±200 Pa (seasonal/location) |
| Surface temperature | ±30 K (diurnal/seasonal) |
| Atmospheric opacity | ±0.2 (weather-dependent) |
| Scale height | ±1 km (varies with temperature) |
| Solar constant at Mars | ±2 W/m² (measurement precision) |

---

## Formula Audit

### Barometric formula (`atmosphere.py:34`)
```python
p = SURFACE_PRESSURE_PA * math.exp(-altitude_m / SCALE_HEIGHT_M)
```
✅ **Correct.** Standard exponential atmosphere model P = P₀·exp(−h/H).

### Ideal gas law for CO₂ density (`atmosphere.py:90`)
```python
total_density = p / (k_boltzmann * t)
```
✅ **Correct.** n = P/(kT) gives number density in molecules/m³.

### Solar distance factor (`solar.py:31–33`)
```python
r_ratio = (1 - e**2) / (1 + e * math.cos(theta))
return 1.0 / (r_ratio**2)
```
✅ **Correct.** Uses the orbital mechanics formula r = a(1−e²)/(1+e·cos θ), then inverse-square for flux.

### Solar declination (`solar.py:38`)
```python
return MARS_AXIAL_TILT * math.sin(math.radians(solar_longitude))
```
✅ **Correct.** First-order approximation δ = ε·sin(Ls).

### Cosine of solar zenith angle (`solar.py:58–59`)
```python
math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(ha)
```
✅ **Correct.** Standard spherical astronomy formula.

### Stefan-Boltzmann radiative loss (`thermal.py:54–55`)
```python
emissivity * STEFAN_BOLTZMANN * surface_area * (T_in**4 - T_out**4)
```
✅ **Correct.** Standard net radiative heat transfer between two surfaces.

### Beer-Lambert atmospheric attenuation (`solar.py:91`)
```python
transmission = math.exp(-tau * air_mass)
```
✅ **Correct.** Beer-Lambert law: I = I₀·exp(−τ·m).

### Hour angle (`solar.py:43`)
```python
return (hour - 12.0) * 15.0
```
✅ **Correct.** 360°/24h = 15°/h, zero at noon.

---

## Recommended Fixes (Priority Order)

1. ~~**Fix `hours_per_sol`** in `thermal.py` and `main.py`~~ — ✅ Done (uses `MARS_SOL_HOURS` from constants.py)
2. ~~**Fix solar longitude rate** in `main.py`~~ — ✅ Done (uses `MARS_LS_PER_SOL` from constants.py)
3. ~~**Fix docstring** in `solar.py`~~ — ✅ Done (corrected to 24h 39m 35s)
4. **Consider updating** `SURFACE_PRESSURE_PA` to 636 Pa (NASA reference at mean radius), or add a comment explaining why 610 Pa is used.
5. **Remove or use** `MOLAR_MASS_KG` in `atmosphere.py`.
6. **Add uncertainty annotations** as comments to key constants.
