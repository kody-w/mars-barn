import { useState, useEffect, useRef } from 'react';

export interface PlanetTelemetry {
  surfaceTemp: number;
  atmosphericPressure: number;
  windSpeed: number;
  radiation: number;
  gravity: number;
  activeExperiments: number;
  missionDay: number;
  crewCount: number;
  powerOutput: number;
  commsLatency: number;
  status: 'nominal' | 'warning' | 'critical';
  lastEvent: string;
}

interface PlanetBaseline {
  surfaceTemp: [number, number];
  atmosphericPressure: [number, number];
  windSpeed: [number, number];
  radiation: [number, number];
  gravity: number;
  crewCount: number;
  commsLatency: [number, number];
  powerOutput: [number, number];
  events: string[];
}

const PLANET_BASELINES: Record<string, PlanetBaseline> = {
  mercury: {
    surfaceTemp: [100, 430],
    atmosphericPressure: [0, 0.001],
    windSpeed: [0, 5],
    radiation: [8, 14],
    gravity: 3.7,
    crewCount: 0,
    commsLatency: [300, 690],
    powerOutput: [800, 1200],
    events: [
      'Solar flare detected — shields nominal',
      'Surface probe alpha collecting regolith',
      'Thermal cycling test in progress',
      'Orbit insertion maneuver complete',
      'Magnetometer readings anomalous',
    ],
  },
  venus: {
    surfaceTemp: [450, 480],
    atmosphericPressure: [9000, 9300],
    windSpeed: [300, 360],
    radiation: [0.5, 2],
    gravity: 8.87,
    crewCount: 0,
    commsLatency: [120, 900],
    powerOutput: [200, 400],
    events: [
      'Atmospheric balloon stable at 55km',
      'Sulfuric acid concentrations rising',
      'Cloud-layer probe transmitting',
      'Surface lander signal lost — retrying',
      'Wind shear event at 48km altitude',
    ],
  },
  mars: {
    surfaceTemp: [-80, 20],
    atmosphericPressure: [0.4, 0.9],
    windSpeed: [10, 100],
    radiation: [0.2, 0.7],
    gravity: 3.72,
    crewCount: 6,
    commsLatency: [180, 1440],
    powerOutput: [300, 600],
    events: [
      'Dust storm approaching Olympus base',
      'Greenhouse module O₂ output +12%',
      'Rover Pathfinder-7 reached Valles sector',
      'Water extraction rate stable',
      'EVA crew returned safely',
      'Habitat pressure holding at 101.3 kPa',
    ],
  },
  jupiter: {
    surfaceTemp: [-145, -110],
    atmosphericPressure: [20, 1000],
    windSpeed: [400, 620],
    radiation: [20, 50],
    gravity: 24.79,
    crewCount: 0,
    commsLatency: [2000, 3200],
    powerOutput: [150, 300],
    events: [
      'Great Red Spot probe at 200km depth',
      'Europa relay satellite nominal',
      'Magnetosphere fluctuations detected',
      'Io volcanic activity increasing',
      'Radiation spike — instruments shielded',
    ],
  },
  saturn: {
    surfaceTemp: [-178, -140],
    atmosphericPressure: [10, 500],
    windSpeed: [500, 1800],
    radiation: [1, 5],
    gravity: 10.44,
    crewCount: 0,
    commsLatency: [4000, 5400],
    powerOutput: [80, 180],
    events: [
      'Ring particle analysis in progress',
      'Titan lander collecting methane samples',
      'Enceladus plume flythrough scheduled',
      'Orbital resonance mapping active',
      'Hexagonal polar vortex imaging complete',
    ],
  },
  moon: {
    surfaceTemp: [-173, 127],
    atmosphericPressure: [0, 0.0001],
    windSpeed: [0, 0],
    radiation: [0.4, 1.2],
    gravity: 1.62,
    crewCount: 12,
    commsLatency: [1.3, 1.3],
    powerOutput: [500, 900],
    events: [
      'Artemis base solar array tracking',
      'Regolith 3D-printing test successful',
      'Crew rotation shuttle en route',
      'Lava tube survey drone deployed',
      'Water ice mining ops steady',
      'South pole relay tower online',
    ],
  },
  titan: {
    surfaceTemp: [-179, -175],
    atmosphericPressure: [145, 150],
    windSpeed: [0.5, 5],
    radiation: [0.01, 0.05],
    gravity: 1.35,
    crewCount: 0,
    commsLatency: [4500, 5500],
    powerOutput: [40, 90],
    events: [
      'Methane lake sonar mapping active',
      'Surface drone navigating dunes',
      'Atmospheric nitrogen analysis complete',
      'Huygens-2 relay link stable',
      'Cryovolcanic activity detected',
    ],
  },
  europa: {
    surfaceTemp: [-220, -160],
    atmosphericPressure: [0, 0.001],
    windSpeed: [0, 2],
    radiation: [5, 20],
    gravity: 1.31,
    crewCount: 0,
    commsLatency: [2100, 3300],
    powerOutput: [60, 120],
    events: [
      'Ice penetrator drilling at 4.2km',
      'Subsurface ocean detected via radar',
      'Surface ice fracture expanding',
      'Radiation-hardened sensors nominal',
      'Tidal flexing measurements recorded',
    ],
  },
};

function randomInRange(min: number, max: number): number {
  return min + (max - min) * Math.random();
}

function generateTelemetry(planetId: string, prev?: PlanetTelemetry): PlanetTelemetry {
  const baseline = PLANET_BASELINES[planetId] ?? PLANET_BASELINES.mars;

  const surfaceTemp = prev
    ? Math.max(baseline.surfaceTemp[0], Math.min(baseline.surfaceTemp[1],
        prev.surfaceTemp + (Math.random() - 0.5) * 4))
    : randomInRange(...baseline.surfaceTemp);

  const atmosphericPressure = baseline.atmosphericPressure[1] < 0.01
    ? baseline.atmosphericPressure[0]
    : prev
      ? Math.max(0, prev.atmosphericPressure + (Math.random() - 0.5) * (baseline.atmosphericPressure[1] * 0.01))
      : randomInRange(...baseline.atmosphericPressure);

  const windSpeed = baseline.windSpeed[1] === 0
    ? 0
    : prev
      ? Math.max(0, Math.min(baseline.windSpeed[1] * 1.15,
          prev.windSpeed + (Math.random() - 0.5) * 10))
      : randomInRange(...baseline.windSpeed);

  const radiation = prev
    ? Math.max(baseline.radiation[0] * 0.5, Math.min(baseline.radiation[1] * 1.2,
        prev.radiation + (Math.random() - 0.5) * 0.3))
    : randomInRange(...baseline.radiation);

  const powerOutput = prev
    ? Math.max(baseline.powerOutput[0] * 0.1, Math.min(baseline.powerOutput[1] * 1.1,
        prev.powerOutput + (Math.random() - 0.5) * 20))
    : randomInRange(...baseline.powerOutput);

  const commsLatency = prev
    ? Math.max(baseline.commsLatency[0], Math.min(baseline.commsLatency[1],
        prev.commsLatency + (Math.random() - 0.5) * (baseline.commsLatency[1] - baseline.commsLatency[0]) * 0.05))
    : randomInRange(...baseline.commsLatency);

  const activeExperiments = prev
    ? prev.activeExperiments + (Math.random() > 0.9 ? (Math.random() > 0.5 ? 1 : -1) : 0)
    : Math.floor(Math.random() * 8) + 2;

  const missionDay = prev
    ? prev.missionDay + (Math.random() > 0.7 ? 1 : 0)
    : Math.floor(Math.random() * 800) + 30;

  let status: PlanetTelemetry['status'] = 'nominal';
  if (radiation > baseline.radiation[1] * 0.9 || powerOutput < baseline.powerOutput[0] * 0.3) {
    status = 'critical';
  } else if (windSpeed > baseline.windSpeed[1] * 0.8 || radiation > baseline.radiation[1] * 0.7) {
    status = 'warning';
  }

  const shouldNewEvent = !prev || Math.random() > 0.85;
  const lastEvent = shouldNewEvent
    ? baseline.events[Math.floor(Math.random() * baseline.events.length)]
    : prev?.lastEvent ?? baseline.events[0];

  return {
    surfaceTemp: +surfaceTemp.toFixed(1),
    atmosphericPressure: +atmosphericPressure.toFixed(2),
    windSpeed: +Math.max(0, windSpeed).toFixed(1),
    radiation: +Math.max(0, radiation).toFixed(3),
    gravity: baseline.gravity,
    activeExperiments: Math.max(0, Math.min(20, activeExperiments)),
    missionDay,
    crewCount: baseline.crewCount,
    powerOutput: +Math.max(0, powerOutput).toFixed(1),
    commsLatency: +commsLatency.toFixed(1),
    status,
    lastEvent,
  };
}

export function useSimulationData(planetId: string, intervalMs = 2000) {
  const [telemetry, setTelemetry] = useState<PlanetTelemetry>(() => generateTelemetry(planetId));
  const prevRef = useRef<PlanetTelemetry>(telemetry);

  useEffect(() => {
    const timer = setInterval(() => {
      const next = generateTelemetry(planetId, prevRef.current);
      prevRef.current = next;
      setTelemetry(next);
    }, intervalMs);
    return () => clearInterval(timer);
  }, [planetId, intervalMs]);

  return telemetry;
}
