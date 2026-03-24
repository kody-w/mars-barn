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

# Temperature stress margins (K) — linear ramp zones
_COLD_STRESS_MARGIN_K = 8.0  # 275-283K: linear ramp from 0 to 1
_HEAT_STRESS_MARGIN_K = 8.0  # 310-318K: linear ramp from 1 to 0


def crop_maturity_factor(sol: int) -> float:
    """Maturity curve: linear ramp from 0 to 1 over CROP_MATURITY_SOLS."""
    if sol <= 0:
        return 0.0
    if sol >= CROP_MATURITY_SOLS:
        return 1.0
    return sol / CROP_MATURITY_SOLS


def temperature_factor(temperature_k: float) -> float:
    """Temperature dependency: crops fail outside safe range.

    Below 275K: zero production. 275-283K: cold stress ramp.
    283-310K: full production. 310-318K: heat stress ramp.
    Above 318K: zero production.
    """
    if temperature_k <= CROP_FAILURE_TEMP_LOW_K:
        return 0.0
    if temperature_k >= CROP_FAILURE_TEMP_HIGH_K:
        return 0.0
    cold_safe = CROP_FAILURE_TEMP_LOW_K + _COLD_STRESS_MARGIN_K
    if temperature_k < cold_safe:
        return (temperature_k - CROP_FAILURE_TEMP_LOW_K) / _COLD_STRESS_MARGIN_K
    heat_safe = CROP_FAILURE_TEMP_HIGH_K - _HEAT_STRESS_MARGIN_K
    if temperature_k > heat_safe:
        return (CROP_FAILURE_TEMP_HIGH_K - temperature_k) / _HEAT_STRESS_MARGIN_K
    return 1.0


def water_availability_factor(water_available: float) -> float:
    """Water dependency: proportional to water supply vs greenhouse needs."""
    if water_available <= 0.0:
        return 0.0
    return min(1.0, water_available / GREENHOUSE_WATER_L_PER_SOL)


def solar_availability_factor(solar_energy_kwh: float) -> float:
    """Solar dependency: crops need light to grow."""
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
    temperature_k: float = 293.0,
) -> dict:
    """Advance food production by one sol.

    Args:
        population: Number of crew members to feed.
        water_available: Liters of water available for greenhouse.
        solar_energy_kwh: Solar energy generated this sol (kWh).
        sol: Current simulation sol (for maturity curve).
        temperature_k: Greenhouse interior temperature (Kelvin).
            Default 293K (20C) for backward compatibility.

    Returns:
        dict with food_produced_kcal, water_consumed_l, growth_stage,
        fed_population, deficit_kcal, temp_factor.
    """
    maturity = crop_maturity_factor(sol)
    water_factor = water_availability_factor(water_available)
    solar_factor = solar_availability_factor(solar_energy_kwh)
    temp_factor = temperature_factor(temperature_k)

    food_produced = GREENHOUSE_KCAL_PER_SOL * maturity * water_factor * solar_factor * temp_factor
    food_produced = max(0.0, food_produced)

    production_ratio = (maturity * water_factor * solar_factor * temp_factor)
    water_consumed = GREENHOUSE_WATER_L_PER_SOL * production_ratio
    water_consumed = min(water_consumed, water_available)
    water_consumed = max(0.0, water_consumed)

    demand = population * FOOD_KCAL_PER_PERSON_PER_SOL
    fed_population = min(population, int(food_produced / FOOD_KCAL_PER_PERSON_PER_SOL)) if FOOD_KCAL_PER_PERSON_PER_SOL > 0 else 0
    deficit = max(0.0, demand - food_produced)

    return {
        "food_produced_kcal": round(food_produced, 2),
        "water_consumed_l": round(water_consumed, 2),
        "growth_stage": round(maturity, 4),
        "fed_population": fed_population,
        "deficit_kcal": round(deficit, 2),
        "temp_factor": round(temp_factor, 4),
    }
