"""Mars Barn - Physical Constants (Single Source of Truth)

All Mars planetary data, universal physics constants, and habitat
design parameters live here.  Every other module imports from this
file - never re-defines its own copy.

References:
  - NASA Mars Fact Sheet (nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html)
  - JPL Planetary Physical Parameters (ssd.jpl.nasa.gov/planets/phys_par.html)
  - NIST CODATA 2018 (universal constants)
  - Mars Climate Database (www-mars.lmd.jussieu.fr)
"""

# -- Universal Physics Constants --
STEFAN_BOLTZMANN = 5.67e-8       # W/(m2 K4), NIST: 5.670374419e-8
BOLTZMANN = 1.381e-23            # J/K, NIST: 1.380649e-23 (exact since 2019)

# -- Mars Planetary Constants --
MARS_SURFACE_PRESSURE_PA = 636.0
MARS_SURFACE_TEMP_K = 210.0
MARS_SCALE_HEIGHT_M = 11100.0
MARS_GRAVITY_M_S2 = 3.721
MARS_CO2_FRACTION = 0.9532

# -- Mars Orbital Constants --
MARS_ECCENTRICITY = 0.0934
MARS_AXIAL_TILT_DEG = 25.19
MARS_SOL_SECONDS = 88775
MARS_SOL_HOURS = MARS_SOL_SECONDS / 3600
MARS_PERIHELION_LS = 251.0
MARS_LS_PER_SOL = 0.5385

# -- Solar Constants --
SOLAR_CONSTANT_MARS = 586.2

# -- Habitat Design Defaults --
HABITAT_SURFACE_AREA_M2 = 200.0
HABITAT_VOLUME_M3 = 150.0
HABITAT_TARGET_TEMP_K = 293.0
HABITAT_CREW_SIZE = 4
HABITAT_HUMAN_METABOLIC_HEAT = True
HUMAN_METABOLIC_HEAT_W = 120.0
HABITAT_INTERIOR_PRESSURE_PA = 101325.0
HABITAT_SOLAR_PANEL_AREA_M2 = 400.0
HABITAT_SOLAR_PANEL_EFFICIENCY = 0.22
HABITAT_INSULATION_R_VALUE = 12.0
HABITAT_HEATER_POWER_W = 8000.0
HABITAT_STORED_ENERGY_KWH = 500.0
HABITAT_EMISSIVITY = 0.05
HABITAT_WINDOW_AREA_M2 = 10.0
HABITAT_WINDOW_TRANSMITTANCE = 0.75
HABITAT_GROUND_COUPLING = True
GROUND_COUPLING_U_VALUE = 0.5

# -- Interior Air Properties (pressurized at ~1 atm) --
AIR_DENSITY_KG_M3 = 1.2
AIR_SPECIFIC_HEAT_J_KGK = 1005
THERMAL_MASS_MULTIPLIER = 20.0

# -- Life Support Power Budget --
LIFE_SUPPORT_BASE_KWH_PER_SOL = 30.0

# -- Life Support Consumption Rates (per crew-member, per sol) --
# Metabolic and environmental baselines used by survival.py and decisions.py.
# Defined here so both modules share one source of truth.
# Reference: NASA HIDH (Human Integration Design Handbook) Ch. 6
O2_KG_PER_PERSON_PER_SOL = 0.84
H2O_L_PER_PERSON_PER_SOL = 2.5
FOOD_KCAL_PER_PERSON_PER_SOL = 2500
POWER_BASE_KWH_PER_SOL = LIFE_SUPPORT_BASE_KWH_PER_SOL  # alias for compat

# -- Critical Thresholds --
POWER_CRITICAL_KWH = 50.0
# -- Mortality Thresholds --
# Colony death conditions used by survival.py and test_mortality.py.
# A colony dies when stored energy drops below MORTALITY_POWER_KWH for
# MORTALITY_GRACE_SOLS consecutive sols with zero solar input.
MORTALITY_POWER_KWH = 10.0
MORTALITY_GRACE_SOLS = 3
MIN_POPULATION_VIABLE = 2           # below this, colony cannot sustain itself


# -- Production Rates (base, before efficiency modifiers) --
ISRU_O2_KG_PER_SOL = 2.0
ISRU_H2O_L_PER_SOL = 4.0
GREENHOUSE_KCAL_PER_SOL = 6000.0
SOLAR_HOURS_PER_SOL = 12.0
