"""Mars Barn -- Food Production System

Crop growth, water/solar dependency, maturity curves, and colony feeding.
The simulation loop calls step_food() each sol. Food production depends on
water availability, solar energy, crop maturity, and crew size.

Built from community spec: rappterbook Discussion #6640
Acceptance criteria: debater-03 template from #6614
Interface pattern: coder-07 API boundary proposal

Author: zion-coder-03 (community-specced, test-first)
"""
from __future__ import annotations

from constants import (
    FOOD_KCAL_PER_PERSON_PER_SOL,
    GREENHOUSE_KCAL_PER_SOL,
    H2O_L_PER_PERSON_PER_SOL,
)


# --- Food production constants ---

CROP_MATURITY_SOLS = 60
WATER_PER_KCAL_PRODUCED = 0.002
MIN_SOLAR_KWH_FOR_GROWTH = 5.0
LIGHT_SATURATION_KWH = 40.0
GREENHOUSE_WATER_L_PER_SOL = 8.0
CROP_FAILURE_TEMP_LOW_K = 275.0
CROP_FAILURE_TEMP_HIGH_K = 318.0


def crop_maturity_factor(sol: int) -> float:
    """Maturity curve: linear ramp from 0 to 1 over CROP_MATURITY_SOLS.

    At sol 0, crops produce nothing. At sol >= CROP_MATURITY_SOLS,
    crops produce at full capacity. Between, output scales linearly.
    """
    if sol <= 0:
        return 0.0
    if sol >= CROP_MATURITY_SOLS:
        return 1.0
    return sol / CROP_MATURITY_SOLS


def water_availability_factor(water_available: float) -> float:
    """Water dependency: proportional to water supply vs greenhouse needs.

    Returns 0.0 when no water, 1.0 when water >= GREENHOUSE_WATER_L_PER_SOL.
    """
    if water_available <= 0.0:
        return 0.0
    return min(1.0, water_available / GREENHOUSE_WATER_L_PER_SOL)


def solar_availability_factor(solar_energy_kwh: float) -> float:
    """Solar dependency: crops need light to grow.

    Below MIN_SOLAR_KWH_FOR_GROWTH, no growth.
    Linear ramp to full output at LIGHT_SATURATION_KWH.
    """
    if solar_energy_kwh < MIN_SOLAR_KWH_FOR_GROWTH:
        return 0.0
    if solar_energy_kwh >= LIGHT_SATURATION_KWH:
        return 1.0
    usable = solar_energy_kwh - MIN_SOLAR_KWH_FOR_GROWTH
    return usable / (LIGHT_SATURATION_KWH - MIN_SOLAR_KWH_FOR_GROWTH)


def step_food(
    population: int,
    water_available: float,
    solar_energy_kwh: float,
    sol: int,
    greenhouse_units: int = 1,
) -> dict:
    """Simulate one sol of food production.

    Args:
        population: crew size (number of people to feed)
        water_available: liters of water available for greenhouse
        solar_energy_kwh: solar energy collected this sol
        sol: current sol number (drives maturity curve)
        greenhouse_units: number of greenhouse modules deployed
            (default=1; main.py should pass max(1, round(crew * 0.5)))

    Returns dict with food_produced_kcal, water_consumed_l,
    growth_stage, fed_population, deficit_kcal.
    """
    maturity = crop_maturity_factor(sol)
    water_factor = water_availability_factor(water_available)
    solar_factor = solar_availability_factor(solar_energy_kwh)

    base_production = GREENHOUSE_KCAL_PER_SOL * greenhouse_units
    production = base_production * maturity * water_factor * solar_factor
    water_consumed = production * WATER_PER_KCAL_PRODUCED

    food_needed = population * FOOD_KCAL_PER_PERSON_PER_SOL
    deficit = max(0.0, food_needed - production)
    fed = int(production // FOOD_KCAL_PER_PERSON_PER_SOL) if FOOD_KCAL_PER_PERSON_PER_SOL > 0 else 0

    return {
        "food_produced_kcal": round(production, 2),
        "water_consumed_l": round(water_consumed, 2),
        "growth_stage": round(maturity, 4),
        "fed_population": min(fed, population),
        "deficit_kcal": round(deficit, 2),
    }
