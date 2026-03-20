"""Mars Barn — Physical Constants (Single Source of Truth)

All Mars planetary data, universal physics constants, and habitat
design parameters live here.  Every other module imports from this
file — never re-defines its own copy.

References:
  - NASA Mars Fact Sheet (nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html)
  - JPL Planetary Physical Parameters (ssd.jpl.nasa.gov/planets/phys_par.html)
  - NIST CODATA 2018 (universal constants)
  - Mars Climate Database (www-mars.lmd.jussieu.fr)
"""

# ── Universal Physics Constants ─────────────────────────────────────────
STEFAN_BOLTZMANN = 5.67e-8       # W/(m²·K⁴), NIST: 5.670374419e-8
BOLTZMANN = 1.381e-23            # J/K, NIST: 1.380649e-23 (exact since 2019)

# ── Mars Planetary Constants ────────────────────────────────────────────
# Uncertainty notes:
#   Pressure varies ±200 Pa by season/location; 636 Pa is NASA ref at mean radius.
#   Temperature varies ±30 K diurnally/seasonally.
#   Scale height varies ±1 km with temperature.
MARS_SURFACE_PRESSURE_PA = 636.0    # Pa, NASA Fact Sheet mean at mean radius
MARS_SURFACE_TEMP_K = 210.0         # K, −63°C mean (range ~145–300 K)
MARS_SCALE_HEIGHT_M = 11100.0       # m, ±~1000 m depending on temperature
MARS_GRAVITY_M_S2 = 3.721           # m/s², JPL: 3.72076 ± 0.0001
MARS_CO2_FRACTION = 0.9532          # NASA: 95.32% CO₂

# ── Mars Orbital Constants ──────────────────────────────────────────────
MARS_ECCENTRICITY = 0.0934          # JPL: 0.09341233
MARS_AXIAL_TILT_DEG = 25.19         # degrees, NASA
MARS_SOL_SECONDS = 88775            # seconds, precise: 88775.245 s (24h 39m 35s)
MARS_SOL_HOURS = MARS_SOL_SECONDS / 3600  # 24.6597… hours
MARS_PERIHELION_LS = 251.0          # solar longitude of perihelion, degrees
MARS_LS_PER_SOL = 0.5385            # degrees of Ls per sol (360° / 668.6 sols)

# ── Solar Constants ─────────────────────────────────────────────────────
SOLAR_CONSTANT_MARS = 586.2         # W/m² at Mars mean distance (1361 / 1.524²), ±2

# ── Habitat Design Defaults ─────────────────────────────────────────────
HABITAT_SURFACE_AREA_M2 = 200.0     # exterior surface area
HABITAT_VOLUME_M3 = 150.0           # pressurized interior volume
HABITAT_TARGET_TEMP_K = 293.0       # 20°C interior target
HABITAT_CREW_SIZE = 4
HABITAT_HUMAN_METABOLIC_HEAT = True
HUMAN_METABOLIC_HEAT_W = 120.0
HABITAT_INTERIOR_PRESSURE_PA = 101325.0  # 1 atm
HABITAT_SOLAR_PANEL_AREA_M2 = 400.0
HABITAT_SOLAR_PANEL_EFFICIENCY = 0.22
HABITAT_INSULATION_R_VALUE = 12.0   # m²·K/W (aerogel + regolith sandwich)
HABITAT_HEATER_POWER_W = 8000.0     # watts
HABITAT_STORED_ENERGY_KWH = 500.0   # initial battery reserve
HABITAT_EMISSIVITY = 0.05           # exterior surface (low-e coating)
HABITAT_WINDOW_AREA_M2 = 10.0       # window / solar collector area
HABITAT_WINDOW_TRANSMITTANCE = 0.75
HABITAT_GROUND_COUPLING = True      # thermal contact with mars regolith
GROUND_COUPLING_U_VALUE = 0.5       # W/m²·K (approximate)

# ── Interior Air Properties (pressurized at ~1 atm) ────────────────────
AIR_DENSITY_KG_M3 = 1.2             # kg/m³ at ~1 atm, ~20°C
AIR_SPECIFIC_HEAT_J_KGK = 1005      # J/(kg·K), dry air at ~20°C
THERMAL_MASS_MULTIPLIER = 20.0      # habitat structure ≈ 20× air thermal mass

# ── Life Support Power Budget ───────────────────────────────────────────
# Base electrical power for life support systems (ECLSS, lighting, comms,
# computers) excluding active heating.  30 kWh/sol matches ISS-class
# estimates scaled to a 4-crew Mars habitat.
# Reference: survival.py POWER_BASE_KWH_PER_SOL (was 30.0 inline)
LIFE_SUPPORT_BASE_KWH_PER_SOL = 30.0
