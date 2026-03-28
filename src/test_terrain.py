"""Tests for terrain.py — Mars heightmap generation.

Validates the diamond-square terrain generator produces correct
dimensions, deterministic output, and Mars-range elevations.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from terrain import generate_heightmap, elevation_stats

MARS_MIN = -2000
MARS_MAX = 5000


def test_heightmap_dimensions():
    """Generated heightmap has requested width and height."""
    grid = generate_heightmap(16, 16, seed=1)
    assert len(grid) == 16
    assert all(len(row) == 16 for row in grid)


def test_heightmap_deterministic():
    """Same seed produces identical terrain."""
    a = generate_heightmap(32, 32, seed=42)
    b = generate_heightmap(32, 32, seed=42)
    assert a == b


def test_heightmap_different_seeds():
    """Different seeds produce different terrain."""
    a = generate_heightmap(32, 32, seed=1)
    b = generate_heightmap(32, 32, seed=2)
    assert a != b


def test_elevation_range():
    """All elevations fall within Mars datum range."""
    grid = generate_heightmap(64, 64, seed=99)
    for row in grid:
        for val in row:
            assert MARS_MIN <= val <= MARS_MAX, f"Elevation {val} out of range"


def test_elevation_stats_valid():
    """elevation_stats returns sensible min/max/mean."""
    grid = generate_heightmap(32, 32, seed=7)
    stats = elevation_stats(grid)
    assert stats["min_m"] <= stats["max_m"]
    assert stats["min_m"] >= MARS_MIN
    assert stats["max_m"] <= MARS_MAX
    assert "size" in stats


def test_small_grid():
    """Edge case: 1x1 grid does not crash."""
    grid = generate_heightmap(1, 1, seed=0)
    assert len(grid) >= 1
    assert len(grid[0]) >= 1

