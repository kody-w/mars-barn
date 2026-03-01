"""Mars Barn — ASCII Visualization

Text-based visualization of terrain heightmaps and atmosphere layers.
Print-friendly output for Discussion posts and terminal display.

Author: unclaimed (open workstream)
"""
from typing import List


# Elevation to character mapping (low → high)
TERRAIN_CHARS = " .:-=+*#%@"
ATMOSPHERE_CHARS = " ·∙●"


def render_terrain(grid: List[List[float]], width: int = 64) -> str:
    """Render a terrain heightmap as ASCII art.

    Maps elevation values to characters. Scales to fit terminal width.
    """
    if not grid or not grid[0]:
        return "(empty terrain)"

    flat = [v for row in grid for v in row]
    vmin, vmax = min(flat), max(flat)
    rng = vmax - vmin if vmax != vmin else 1.0

    # Subsample if grid is wider than display width
    grid_w = len(grid[0])
    grid_h = len(grid)
    x_step = max(1, grid_w // width)
    y_step = max(1, grid_h // (width // 2))

    lines = []
    chars = TERRAIN_CHARS

    for y in range(0, grid_h, y_step):
        row = ""
        for x in range(0, grid_w, x_step):
            normalized = (grid[y][x] - vmin) / rng
            idx = min(int(normalized * (len(chars) - 1)), len(chars) - 1)
            row += chars[idx]
        lines.append(row)

    # Add elevation legend
    legend = f"  [{vmin:+.0f}m {''.join(chars)} {vmax:+.0f}m]"
    lines.append(legend)

    return "\n".join(lines)


def render_atmosphere_profile(profile: list) -> str:
    """Render an atmospheric profile as a vertical bar chart.

    Input: list of dicts with altitude_m, pressure_pa, temperature_k.
    """
    if not profile:
        return "(no data)"

    lines = []
    max_p = max(l["pressure_pa"] for l in profile)

    lines.append("  Alt(km)  Pressure(Pa)  Temp(°C)  Bar")
    lines.append("  " + "-" * 50)

    for layer in reversed(profile):
        alt_km = layer["altitude_m"] / 1000
        p = layer["pressure_pa"]
        t_c = layer["temperature_k"] - 273.15
        bar_len = int(p / max(max_p, 1) * 30)
        bar = "█" * bar_len
        lines.append(f"  {alt_km:>5.0f}  {p:>10.1f}  {t_c:>+7.1f}°C  {bar}")

    return "\n".join(lines)


def render_energy_profile(hourly: list) -> str:
    """Render a daily solar energy profile as an ASCII sparkline.

    Input: list of dicts with hour, irradiance_wm2 or power_w.
    """
    if not hourly:
        return "(no data)"

    key = "power_w" if "power_w" in hourly[0] else "irradiance_wm2"
    values = [h.get(key, 0) for h in hourly]
    max_v = max(values) if values else 1

    lines = []
    bar_chars = " ▁▂▃▄▅▆▇█"

    # Sparkline
    spark = ""
    for v in values:
        idx = min(int(v / max(max_v, 1) * (len(bar_chars) - 1)), len(bar_chars) - 1)
        spark += bar_chars[idx]

    lines.append(f"  Solar: {spark}")
    lines.append(f"  Peak: {max_v:.0f} W | Hours: {len([v for v in values if v > 0])}")

    return "\n".join(lines)


def render_thermal_day(hourly: list) -> str:
    """Render interior vs exterior temperature over one sol."""
    if not hourly:
        return "(no data)"

    lines = []
    lines.append("  Hour  Interior  Exterior  ΔT     Status")
    lines.append("  " + "-" * 48)

    for h in hourly:
        int_c = h["interior_k"] - 273.15
        ext_c = h["exterior_k"] - 273.15
        delta = int_c - ext_c
        status = "🔥" if h.get("heating") else "☀️" if h.get("irradiance", 0) > 10 else "🌙"
        lines.append(f"  {h['hour']:>4.0f}h  {int_c:>+6.1f}°C  {ext_c:>+6.1f}°C  {delta:>+5.0f}K  {status}")

    return "\n".join(lines)


def render_events(events: list) -> str:
    """Render active events as a status panel."""
    if not events:
        return "  No active events"

    lines = []
    icons = {
        "dust_storm_local": "🌪️",
        "dust_storm_global": "🌫️",
        "meteorite_small": "☄️",
        "meteorite_large": "💥",
        "equipment_failure": "⚠️",
        "solar_flare": "☀️",
        "dust_devil": "🌀",
    }

    for e in events:
        icon = icons.get(e["type"], "❓")
        sev = f"{e['severity']:.0%}"
        remaining = e["duration_sols"] - 1  # approximate
        lines.append(f"  {icon} {e['description']} (severity: {sev}, {remaining} sols remaining)")

    return "\n".join(lines)


def render_dashboard(state: dict) -> str:
    """Render a full simulation dashboard."""
    lines = []
    lines.append("╔══════════════════════════════════════════════════════╗")
    lines.append("║           MARS BARN — Habitat Dashboard             ║")
    lines.append("╚══════════════════════════════════════════════════════╝")
    lines.append("")

    hab = state.get("habitat", {})
    met = state.get("metrics", {})
    loc = state.get("location", {})

    hour = state.get('hour', 0)
    hh = int(hour)
    mm = int((hour % 1) * 60)
    lines.append(f"  Sol: {state.get('sol', 0):>4d}  |  Time: {hh:02d}:{mm:02d}  |  "
                 f"Lat: {loc.get('latitude_deg', 0):+.1f}°  Lon: {loc.get('longitude_deg', 0):.1f}°")
    lines.append(f"  Interior: {hab.get('interior_temp_k', 0)-273.15:+.1f}°C  |  "
                 f"Power: {hab.get('power_kw', 0):.1f} kW  |  "
                 f"Stored: {hab.get('stored_energy_kwh', 0):.0f} kWh")
    lines.append(f"  Crew: {hab.get('crew_size', 0)}  |  "
                 f"Sols survived: {met.get('sols_survived', 0)}  |  "
                 f"Events survived: {met.get('events_survived', 0)}")
    lines.append("")
    lines.append("  Events:")
    lines.append(render_events(state.get("active_events", [])))

    return "\n".join(lines)


if __name__ == "__main__":
    # Demo with sample data
    from terrain import generate_heightmap, elevation_stats
    from atmosphere import atmosphere_profile

    print("=== Terrain ===")
    grid = generate_heightmap(48, 24, seed=42)
    print(render_terrain(grid, width=48))
    stats = elevation_stats(grid)
    print(f"  Stats: {stats}")

    print("\n=== Atmosphere ===")
    profile = atmosphere_profile(50000, 10)
    print(render_atmosphere_profile(profile))
