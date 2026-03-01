export default async function handler(request, response) {
  try {
    const res = await fetch('https://raw.githubusercontent.com/kody-w/mars-barn/main/data/state.json');
    if (!res.ok) {
      if (res.status === 404) {
         return response.status(200).json([]);
      }
      throw new Error(`Failed to fetch state: ${res.status}`);
    }
    const state = await res.json();
    
    // Transform single state into array format expected by frontend
    const colony = {
      id: "Alpha Base",
      status: state.habitat.interior_temp_k > 200 ? 'ALIVE' : 'DEAD',
      age_sols: state.sol,
      last_event: state.active_events.length > 0 ? state.active_events[state.active_events.length-1].description : "Nominal operations",
      stats: {
        solar_efficiency: Math.max(0.1, 1.0 - (state.active_events.filter(e => e.type.startsWith('dust_')).length * 0.4)),
        battery_reserves_kwh: state.habitat.stored_energy_kwh,
        supply_reserves_tons: 15.0 - (state.sol * 0.05) // Fake burn rate for visual
      }
    };
    
    response.status(200).json([colony]);
  } catch (error) {
    response.status(500).json({ error: error.message });
  }
}
