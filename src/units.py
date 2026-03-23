"""Mars Barn — Unit conversion utilities.

One function per physical conversion. No classes. No state.
Import what you need, pipe the rest.
"""
from constants import MARS_SOL_SECONDS


def sol_to_hours(sols: float) -> float:
    """Convert Mars sols to Earth hours."""
    return sols * MARS_SOL_SECONDS / 3600


def hours_to_sols(hours: float) -> float:
    """Convert Earth hours to Mars sols."""
    return hours * 3600 / MARS_SOL_SECONDS


def sols_to_earth_days(sols: float) -> float:
    """Convert Mars sols to Earth days."""
    return sols * MARS_SOL_SECONDS / 86400

