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
LIGHT_SATURATION_KWH = 15.0  # Fixed: was 40.0, Mars greenhouse gets ~10-15 kWh
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
    if solar_energy_kwh <= MIN_SOLAR_KWH_FOR_GROWTH:
        return 0.0
    effective = solar_energy_kwh - MIN_SOLAR_KWH_FOR_GROWTH
    range_kwh = LIGHT_SATURATION_KWH - MIN_SOLAR_KWH_FOR_GROWTH
    return min(1.0, effective / range_kwh)


def step_food(
    population: int,
    water_available: float,
    solar_energy_kwh: float,
    sol: int,
) -> dict:
    """Advance food production by one sol.

    Args:
        population: Number of crew members to feed.
        water_available: Liters of water available for greenhouse.
        solar_energy_kwh: Solar energy generated this sol (kWh).
        sol: Current simulation sol (for maturity curve).

    Returns:
        dict with:
            food_produced_kcal: Total food produced this sol.
            water_consumed_l: Water used by greenhouse.
            growth_stage: Current crop maturity (0.0 to 1.0).
            fed_population: Number of crew fully fed.
            deficit_kcal: Calorie shortfall (0 if everyone fed).
    """
    maturity = crop_maturity_factor(sol)
    water_factor = water_availability_factor(water_available)
    solar_factor = solar_availability_factor(solar_energy_kwh)

    # Base production scaled by all factors
    food_produced = GREENHOUSE_KCAL_PER_SOL * maturity * water_factor * solar_factor
    food_produced = max(0.0, food_produced)

    # Water consumed by greenhouse (proportional to actual production)
    production_ratio = (maturity * water_factor * solar_factor)
    water_consumed = GREENHOUSE_WATER_L_PER_SOL * production_ratio
    water_consumed = min(water_consumed, water_available)
    water_consumed = max(0.0, water_consumed)

    # Feeding calculation
    demand = population * FOOD_KCAL_PER_PERSON_PER_SOL
    fed_population = min(population, int(food_produced / FOOD_KCAL_PER_PERSON_PER_SOL)) if FOOD_KCAL_PER_PERSON_PER_SOL > 0 else 0
    deficit = max(0.0, demand - food_produced)

    return {
        "food_produced_kcal": round(food_produced, 2),
        "water_consumed_l": round(water_consumed, 2),
        "growth_stage": round(maturity, 4),
        "fed_population": fed_population,
        "deficit_kcal": round(deficit, 2),
    }
