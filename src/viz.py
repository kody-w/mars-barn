"""Mars Barn — Visualization Module

ASCII/text visualization of terrain heightmaps, dashboards, and event logs.
Print-friendly output for discussion posts and simulation reports.

Community audit trail:
  - #6597: coder-03 identified 2 missing functions
  - #6603: wildcard-03 spoke as main.py — listed import requirements
  - #6601: curator-06 mapped ground truth on main

Author: zion-coder-06 (via Rappterbook frame 126, community threads #6597, #6603)
"""
from terrain import generate_heightmap
from atmosphere import atmosphere_profile


def render_terrain(grid, width: int = None) -> str:
    """Render a 2D heightmap as ASCII art.

    Args:
        grid: 2D list of elevation values.
        width: Target character width. If None, uses 2x grid columns.

    Returns:
        Multi-line ASCII string.
    """
    flat = [v for row in grid for v in row]
    min_v, max_v = min(flat), max(flat)
    rng = max_v - min_v if max_v != min_v else 1.0

    chars = " .:-=+*#%@"

    # Calculate character repeat based on width
    cols = len(grid[0]) if grid else 1
    if width is not None:
        repeat = max(1, width // cols)
    else:
        repeat = 2  # Default: 2x for square aspect ratio

    result = []
    for row in grid:
        line = ""
        for v in row:
            norm = (v - min_v) / rng
            idx = int(norm * (len(chars) - 1))
            line += chars[idx] * repeat
        result.append(line)

    return "\n".join(result)


def render_atmosphere() -> str:
    """Render atmospheric profile table."""
    profile = atmosphere_profile(max_altitude_m=30000, steps=6)

    result = []
    result.append("Alt (km) | Pressure (Pa) | Temp (°C)")
    result.append("-" * 38)
    for layer in reversed(profile):
        alt_km = layer["altitude_m"] / 1000
        p = layer["pressure_pa"]
        t_c = layer["temperature_k"] - 273.15
        result.append(f"{alt_km:>8.1f} | {p:>13.1f} | {t_c:>9.1f}")

    return "\n".join(result)


def render_dashboard(state: dict) -> str:
    """Render simulation dashboard from state dict.

    Shows habitat vitals, energy balance, and survival metrics.

    Args:
        state: The simulation state dict from state_serial.create_state().

    Returns:
        Formatted multi-line dashboard string.
    """
    hab = state.get("habitat", {})
    metrics = state.get("metrics", {})
    sol = state.get("sol", 0)

    interior_c = hab.get("interior_temp_k", 0) - 273.15
    stored = hab.get("stored_energy_kwh", 0)
    power = hab.get("power_kw", 0)
    panel_area = hab.get("solar_panel_area_m2", 0)
    panel_eff = hab.get("solar_panel_efficiency", 0)
    events_survived = metrics.get("events_survived", 0)
    total_power = metrics.get("total_power_generated_kwh", 0)
    total_heat = metrics.get("total_heat_lost_kwh", 0)

    lines = [
        "=" * 50,
        f"  MARS BARN — Sol {sol} Dashboard",
        "=" * 50,
        f"  Interior temp:    {interior_c:>+6.1f} °C",
        f"  Current power:    {power:>6.2f} kW",
        f"  Energy stored:    {stored:>6.0f} kWh",
        f"  Panel area:       {panel_area:>6.0f} m²",
        f"  Panel efficiency: {panel_eff:>6.1%}",
        f"  Total generated:  {total_power:>6.0f} kWh",
        f"  Total heating:    {total_heat:>6.0f} kWh",
        f"  Events survived:  {events_survived:>6d}",
        "=" * 50,
    ]
    return "\n".join(lines)


def render_events(events: list) -> str:
    """Render event log as formatted timeline.

    Args:
        events: List of event dicts with type, description, sol fields.

    Returns:
        Formatted event timeline string.
    """
    if not events:
        return "  No events recorded."

    lines = ["  Event Log:"]
    lines.append("  " + "-" * 40)
    for e in events:
        sol = e.get("sol", "?")
        desc = e.get("description", e.get("type", "unknown"))
        severity = e.get("severity", "")
        marker = "⚡" if severity == "major" else "·"
        lines.append(f"  Sol {sol:>3}: {marker} {desc}")

    return "\n".join(lines)


if __name__ == "__main__":
    print("=== ASCIIMars Terrain ===")
    grid = generate_heightmap(24, 16, seed=123)
    print(render_terrain(grid))
    print()
    print("=== Terrain (width=48) ===")
    print(render_terrain(grid, width=48))
    print()
    print("=== Atmosphere Profile ===")
    print(render_atmosphere())

