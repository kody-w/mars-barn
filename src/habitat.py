"""Mars Barn — Habitat Module

Thin wrapper providing a typed interface over the simulation state dict.
Keeps JSON serialization compatibility while adding property-based access.

Author: zion-coder-05 (Kay OOP)
"""
from typing import Optional


class Habitat:
    """Typed interface to the habitat state dictionary."""
    
    def __init__(self, state: dict):
        self._state = state
        self._hab = state.get("habitat", {})
    
    @property
    def crew_size(self) -> int:
        return self._hab.get("crew_size", 0)
    
    @property
    def interior_temp_c(self) -> float:
        return round(self._hab.get("interior_temp_k", 0) - 273.15, 1)
    
    @interior_temp_c.setter
    def interior_temp_c(self, value: float):
        self._hab["interior_temp_k"] = value + 273.15
    
    @property
    def power_kw(self) -> float:
        return self._hab.get("power_kw", 0)
    
    @property
    def stored_energy_kwh(self) -> float:
        return self._hab.get("stored_energy_kwh", 0)
    
    @stored_energy_kwh.setter
    def stored_energy_kwh(self, value: float):
        self._hab["stored_energy_kwh"] = max(0, value)
    
    @property
    def solar_panel_area_m2(self) -> float:
        return self._hab.get("solar_panel_area_m2", 0)
    
    @property
    def is_habitable(self) -> bool:
        """Interior above -10°C and energy reserves positive."""
        return self.interior_temp_c > -10 and self.stored_energy_kwh > 0
    
    @property
    def sol(self) -> int:
        return self._state.get("sol", 0)
    
    @property
    def active_events(self) -> list:
        return self._state.get("active_events", [])
    
    @property
    def has_dust_storm(self) -> bool:
        return any(e["type"].startswith("dust_storm") for e in self.active_events)
    
    def status_line(self) -> str:
        storm = " 🌪️" if self.has_dust_storm else ""
        hab = "🟢" if self.is_habitable else "🔴"
        return (f"Sol {self.sol}: {hab} {self.interior_temp_c:+.1f}°C | "
                f"{self.power_kw:.1f}kW | {self.stored_energy_kwh:.0f}kWh{storm}")
    
    def to_dict(self) -> dict:
        """Return the underlying state dict (JSON-serializable)."""
        return self._state


if __name__ == "__main__":
    from state_serial import create_state
    state = create_state(sol=42, latitude=-4.5)
    h = Habitat(state)
    print(h.status_line())
    print(f"Habitable: {h.is_habitable}")
    print(f"Crew: {h.crew_size}")
