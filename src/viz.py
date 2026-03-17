"""Mars Barn — Visualization Module

ASCII/text visualization of terrain heightmaps and atmosphere layers.
Print-friendly output for discussion posts.

Author: unclaimed (open workstream)
"""
from terrain import generate_heightmap
from atmosphere import atmosphere_profile

def render_terrain(grid, width: int = 0) -> str:
    """Render a 2D heightmap as ASCII art."""
    # Find min/max
    flat = [v for row in grid for v in row]
    min_v, max_v = min(flat), max(flat)
    rng = max_v - min_v if max_v != min_v else 1.0

    chars = " .:-=+*#%@"
    result = []
    
    for row in grid:
        line = ""
        for v in row:
            # Map value to 0-9 index
            norm = (v - min_v) / rng
            idx = int(norm * (len(chars) - 1))
            line += chars[idx] * 2  # * 2 to make it closer to square aspect ratio in monospaced fonts
        if width > 0:
            line = line[:width]
        result.append(line)
        
    return "\n".join(result)


def render_atmosphere() -> str:
    """Render atmospheric profile table."""
    profile = atmosphere_profile(max_altitude_m=30000, steps=6)
    
    result = []
    result.append("Alt (km) | Pressure (Pa) | Temp (°C)")
    result.append("-" * 38)
    for layer in reversed(profile):
        alt_km = layer['altitude_m'] / 1000
        p = layer['pressure_pa']
        t_c = layer['temperature_k'] - 273.15
        result.append(f"{alt_km:>8.1f} | {p:>13.1f} | {t_c:>9.1f}")
        
    return "\n".join(result)


def render_dashboard(state: dict) -> str:
    """Render an ASCII dashboard of current simulation state."""
    h = state.get("habitat", {})
    m = state.get("metrics", {})
    temp_c = h.get("interior_temp_k", 0) - 273.15
    lines = [
        "┌─────────────── HABITAT STATUS ───────────────┐",
        f"│  Sol:            {state.get('sol', '?'):>6}                     │",
        f"│  Interior temp:  {temp_c:>+6.1f} °C                   │",
        f"│  Stored energy:  {h.get('stored_energy_kwh', 0):>6.0f} kWh                 │",
        f"│  Power output:   {h.get('power_kw', 0):>6.2f} kW                  │",
        f"│  Active events:  {len(state.get('active_events', [])):>6}                     │",
        f"│  Events survived:{m.get('events_survived', 0):>6}                     │",
        "└──────────────────────────────────────────────┘",
    ]
    return "\n".join(lines)


def render_events(events: list) -> str:
    """Render a summary of active events."""
    if not events:
        return "  No active events."
    lines = []
    for e in events:
        lines.append(f"  ⚡ [{e.get('type', '?')}] {e.get('description', 'Unknown event')}")
    return "\n".join(lines)


if __name__ == "__main__":
    print("=== ASCIIMars Terrain ===")
    grid = generate_heightmap(24, 16, seed=123)
    print(render_terrain(grid))
    print("\n=== Atmosphere Profile ===")
    print(render_atmosphere())
