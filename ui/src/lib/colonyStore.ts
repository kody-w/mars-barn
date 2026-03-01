import { create } from 'zustand';

const GITHUB_RAW_URL =
  'https://raw.githubusercontent.com/kody-w/mars-barn/main/state/colony.json';

export interface ColonyHabitat {
  interior_temp_k: number;
  stored_energy_kwh: number;
  solar_panel_area_m2: number;
  panel_efficiency: number;
  panel_dust_factor: number;
  insulation_r_value: number;
  heater_power_w: number;
  ground_coupling_depth_m: number;
  crew_size: number;
  water_reserves_l: number;
  food_reserves_kg: number;
  harvest_total_kg: number;
}

export interface ColonyEvent {
  type: string;
  severity?: number;
  end_sol?: number;
  description?: string;
}

export interface LogEntry {
  sol: number;
  ls: number;
  int_c: number;
  ext_c: number;
  solar_kwh: number;
  heat_kwh: number;
  stored_kwh: number;
  dust: number;
  food_kg: number;
  events: string[];
  storm: boolean;
}

export interface ColonyState {
  name: string;
  launch_date: string;
  sol: number;
  solar_longitude: number;
  location: {
    latitude: number;
    longitude: number;
    name: string;
  };
  habitat: ColonyHabitat;
  active_events: ColonyEvent[];
  log: LogEntry[];
  stats: {
    sols_survived: number;
    total_power_kwh: number;
    total_heating_kwh: number;
    dust_devils: number;
    storms_survived: number;
    meteorites: number;
    min_temp_k: number;
    max_temp_k: number;
    harvests: number;
  };
  _meta: {
    version: number;
    created: string;
    updated: string;
    engine: string;
  };
}

interface ColonyStore {
  colony: ColonyState | null;
  loading: boolean;
  error: string | null;
  lastFetchedAt: string | null; // real time (Earth UTC)

  // Composite key: real time + virtual time
  stateKey: () => string;

  fetchColony: () => Promise<void>;
  importState: (json: string) => void;
  exportState: () => string | null;
}

export const useColonyStore = create<ColonyStore>((set, get) => ({
  colony: null,
  loading: false,
  error: null,
  lastFetchedAt: null,

  stateKey: () => {
    const { colony, lastFetchedAt } = get();
    if (!colony) return 'no-state';
    const realTime = lastFetchedAt ?? new Date().toISOString();
    const virtualTime = `sol${colony.sol}-ls${colony.solar_longitude}`;
    return `${realTime}::${virtualTime}`;
  },

  fetchColony: async () => {
    set({ loading: true, error: null });
    try {
      const res = await fetch(GITHUB_RAW_URL + `?t=${Date.now()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: ColonyState = await res.json();
      set({
        colony: data,
        loading: false,
        lastFetchedAt: new Date().toISOString(),
      });
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  importState: (json: string) => {
    try {
      const data: ColonyState = JSON.parse(json);
      if (!data.sol && data.sol !== 0) throw new Error('Invalid colony state: missing sol');
      if (!data.habitat) throw new Error('Invalid colony state: missing habitat');
      set({
        colony: data,
        lastFetchedAt: new Date().toISOString(),
        error: null,
      });
    } catch (err: any) {
      set({ error: `Import failed: ${err.message}` });
    }
  },

  exportState: () => {
    const { colony } = get();
    if (!colony) return null;
    return JSON.stringify(colony, null, 2);
  },
}));
