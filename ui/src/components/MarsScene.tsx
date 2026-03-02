import { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Sky, Stars, Text } from '@react-three/drei';
import * as THREE from 'three';
import { useColonyStore, ColonyState } from '../lib/colonyStore';

// Jezero Crater terrain parameters
const TERRAIN_SIZE = 400;
const TERRAIN_SEGMENTS = 128;
const CRATER_RIM_RADIUS = 120;
const CRATER_RIM_HEIGHT = 8;
const CRATER_RIM_SPREAD = 800;
const CRATER_BASIN_RADIUS = 100;
const CRATER_BASIN_DEPTH = 3;

// Sun position from solar longitude and assumed mid-sol
function sunPosition(ls: number): [number, number, number] {
  const hourAngle = ((ls % 360) / 360) * Math.PI * 2;
  const elevation = Math.max(0.1, Math.sin(hourAngle * 0.5 + 0.3));
  return [
    Math.cos(hourAngle) * 200,
    elevation * 150 + 20,
    Math.sin(hourAngle) * 200,
  ];
}

// ── Mars Terrain ───────────────────────────────────────────────────────
function MarsTerrain() {
  const mesh = useRef<THREE.Mesh>(null);

  const geometry = useMemo(() => {
    const geo = new THREE.PlaneGeometry(TERRAIN_SIZE, TERRAIN_SIZE, TERRAIN_SEGMENTS, TERRAIN_SEGMENTS);
    const pos = geo.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getY(i);
      const dist = Math.sqrt(x * x + z * z);
      const rim = Math.max(0, CRATER_RIM_HEIGHT * Math.exp(-((dist - CRATER_RIM_RADIUS) ** 2) / CRATER_RIM_SPREAD));
      const basin = dist < CRATER_BASIN_RADIUS ? -CRATER_BASIN_DEPTH * (1 - dist / CRATER_BASIN_RADIUS) : 0;
      const noise =
        Math.sin(x * 0.05) * Math.cos(z * 0.07) * 2 +
        Math.sin(x * 0.13 + z * 0.11) * 1.5 +
        Math.sin(x * 0.31 + z * 0.29) * 0.5;
      pos.setZ(i, rim + basin + noise);
    }
    geo.computeVertexNormals();
    return geo;
  }, []);

  return (
    <mesh ref={mesh} rotation={[-Math.PI / 2, 0, 0]} geometry={geometry} receiveShadow>
      <meshStandardMaterial color="#b5651d" roughness={0.95} metalness={0.05} flatShading />
    </mesh>
  );
}

// ── Habitat Dome ───────────────────────────────────────────────────────
function HabitatDome({ colony }: { colony: ColonyState }) {
  const tempK = colony.habitat.interior_temp_k;
  // Glow color: green if habitable, yellow if cool, red if critical
  const tempC = tempK - 273.15;
  const glowColor = tempC > 10 ? '#00ff88' : tempC > -10 ? '#ffaa00' : '#ff3333';

  return (
    <group position={[0, 0, 0]}>
      {/* Main dome */}
      <mesh position={[0, 4, 0]} castShadow>
        <sphereGeometry args={[6, 32, 24, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <meshStandardMaterial
          color="#d4d4d8"
          roughness={0.3}
          metalness={0.7}
          transparent
          opacity={0.85}
        />
      </mesh>
      {/* Interior glow */}
      <mesh position={[0, 3, 0]}>
        <sphereGeometry args={[5.5, 16, 12, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <meshBasicMaterial color={glowColor} transparent opacity={0.15} />
      </mesh>
      {/* Base ring */}
      <mesh position={[0, 0.2, 0]}>
        <cylinderGeometry args={[6.2, 6.5, 0.5, 32]} />
        <meshStandardMaterial color="#71717a" roughness={0.6} metalness={0.4} />
      </mesh>
      {/* Airlock */}
      <mesh position={[6, 1.5, 0]} castShadow>
        <boxGeometry args={[3, 3, 2.5]} />
        <meshStandardMaterial color="#a1a1aa" roughness={0.5} metalness={0.5} />
      </mesh>
      {/* Status light on airlock */}
      <mesh position={[7.6, 2.8, 0]}>
        <sphereGeometry args={[0.2, 8, 8]} />
        <meshBasicMaterial color={glowColor} />
      </mesh>
    </group>
  );
}

// ── Solar Panels ───────────────────────────────────────────────────────
function SolarPanel({ position, rotation, dustFactor }: {
  position: [number, number, number];
  rotation?: [number, number, number];
  dustFactor: number;
}) {
  const opacity = 0.5 + dustFactor * 0.5;
  return (
    <group position={position} rotation={rotation}>
      {/* Panel surface */}
      <mesh position={[0, 2, 0]} rotation={[-0.3, 0, 0]} castShadow>
        <boxGeometry args={[8, 0.1, 4]} />
        <meshStandardMaterial
          color={new THREE.Color(0.05, 0.05, 0.3).lerp(new THREE.Color(0.4, 0.3, 0.2), 1 - dustFactor)}
          roughness={0.2}
          metalness={0.8}
          transparent
          opacity={opacity}
        />
      </mesh>
      {/* Support pole */}
      <mesh position={[0, 1, 0]}>
        <cylinderGeometry args={[0.15, 0.15, 2, 8]} />
        <meshStandardMaterial color="#52525b" roughness={0.7} metalness={0.5} />
      </mesh>
    </group>
  );
}

function SolarArray({ colony }: { colony: ColonyState }) {
  const dust = colony.habitat.panel_dust_factor;
  const panelCount = Math.min(8, Math.ceil(colony.habitat.solar_panel_area_m2 / 50));
  const panels = [];
  for (let i = 0; i < panelCount; i++) {
    const angle = (i / panelCount) * Math.PI * 2;
    const r = 18 + (i % 2) * 5;
    panels.push(
      <SolarPanel
        key={i}
        position={[Math.cos(angle) * r, 0, Math.sin(angle) * r]}
        rotation={[0, -angle + Math.PI / 2, 0]}
        dustFactor={dust}
      />
    );
  }
  return <group>{panels}</group>;
}

// ── Crew figures ───────────────────────────────────────────────────────
function CrewFigure({ position }: { position: [number, number, number] }) {
  return (
    <group position={position}>
      {/* Body */}
      <mesh position={[0, 0.8, 0]}>
        <capsuleGeometry args={[0.25, 0.6, 4, 8]} />
        <meshStandardMaterial color="#f5f5f4" roughness={0.5} />
      </mesh>
      {/* Helmet */}
      <mesh position={[0, 1.5, 0]}>
        <sphereGeometry args={[0.3, 8, 8]} />
        <meshStandardMaterial color="#fbbf24" roughness={0.3} metalness={0.6} transparent opacity={0.7} />
      </mesh>
    </group>
  );
}

function Crew({ count }: { count: number }) {
  const figures = [];
  for (let i = 0; i < Math.min(count, 8); i++) {
    const angle = (i / count) * Math.PI * 1.5 - Math.PI / 4;
    figures.push(
      <CrewFigure key={i} position={[Math.cos(angle) * 9, 0, Math.sin(angle) * 9]} />
    );
  }
  return <group>{figures}</group>;
}

// ── Dust / Storm particles ─────────────────────────────────────────────
function DustParticles({ intensity }: { intensity: number }) {
  const count = Math.floor(intensity * 500);
  const ref = useRef<THREE.Points>(null);

  const positions = useMemo(() => {
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      arr[i * 3] = (Math.random() - 0.5) * 200;
      arr[i * 3 + 1] = Math.random() * 40;
      arr[i * 3 + 2] = (Math.random() - 0.5) * 200;
    }
    return arr;
  }, [count]);

  useFrame((_state, delta) => {
    if (!ref.current) return;
    ref.current.rotation.y += delta * 0.02 * intensity;
    const pos = ref.current.geometry.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i) + (Math.random() - 0.5) * intensity * 2;
      const y = pos.getY(i);
      pos.setX(i, x > 100 ? -100 : x < -100 ? 100 : x);
      pos.setY(i, y < 0 ? 40 : y - delta * intensity * 3);
    }
    pos.needsUpdate = true;
  });

  if (count === 0) return null;

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
          count={count}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial color="#d4a574" size={0.3} transparent opacity={0.6} />
    </points>
  );
}

// ── Location marker ────────────────────────────────────────────────────
function LocationMarker({ colony }: { colony: ColonyState }) {
  return (
    <group position={[0, 12, -15]}>
      <Text
        fontSize={1.2}
        color="#ffffff"
        anchorX="center"
        anchorY="middle"
        outlineWidth={0.05}
        outlineColor="#000000"
      >
        {`📍 ${colony.location.name}`}
      </Text>
      <Text
        position={[0, -1.5, 0]}
        fontSize={0.7}
        color="#a1a1aa"
        anchorX="center"
        anchorY="middle"
      >
        {`${colony.location.latitude}°N  ${colony.location.longitude}°E`}
      </Text>
    </group>
  );
}

// ── Main Scene ─────────────────────────────────────────────────────────
function SceneContents({ colony }: { colony: ColonyState }) {
  const stormActive = colony.active_events.some((e) => e.type === 'storm');
  const stormSev = colony.active_events
    .filter((e) => e.type === 'storm')
    .reduce((max, e) => Math.max(max, e.severity ?? 0), 0);
  const dustIntensity = stormActive ? 0.3 + stormSev * 0.7 : (1 - colony.habitat.panel_dust_factor) * 0.5;

  // Sky tint based on conditions
  const sunPos = sunPosition(colony.solar_longitude);
  const turbidity = stormActive ? 20 : 4;
  const rayleigh = stormActive ? 4 : 0.5;

  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={stormActive ? 0.15 : 0.3} color="#ffd4a0" />
      <directionalLight
        position={sunPos}
        intensity={stormActive ? 0.4 : 1.2}
        color="#fff5e6"
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
      />

      {/* Mars sky */}
      <Sky
        distance={450000}
        sunPosition={sunPos}
        turbidity={turbidity}
        rayleigh={rayleigh}
        mieCoefficient={stormActive ? 0.1 : 0.005}
        mieDirectionalG={0.8}
      />
      <Stars radius={300} depth={60} count={2000} factor={4} fade speed={0.5} />

      {/* Fog for atmosphere */}
      <fog attach="fog" args={[stormActive ? '#8b6914' : '#2d1b0e', 50, stormActive ? 150 : 400]} />

      {/* Terrain */}
      <MarsTerrain />

      {/* Colony structures */}
      <HabitatDome colony={colony} />
      <SolarArray colony={colony} />
      <Crew count={colony.habitat.crew_size} />
      <LocationMarker colony={colony} />

      {/* Weather */}
      <DustParticles intensity={dustIntensity} />

      {/* Camera controls */}
      <OrbitControls
        makeDefault
        enablePan
        enableZoom
        enableRotate
        minDistance={8}
        maxDistance={200}
        minPolarAngle={0.1}
        maxPolarAngle={Math.PI / 2 - 0.05}
        target={[0, 2, 0]}
      />
    </>
  );
}

export default function MarsScene() {
  const colony = useColonyStore((s) => s.colony);

  if (!colony) {
    return (
      <div className="w-full h-full flex items-center justify-center text-zinc-500 font-mono">
        Loading colony state...
      </div>
    );
  }

  // Detect WebGL support
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
    if (!gl) throw new Error('no WebGL');
  } catch {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center text-zinc-500 font-mono gap-2">
        <span className="text-rose-400 text-lg">⚠ WebGL Not Available</span>
        <span className="text-sm">Your browser or device doesn't support 3D rendering.</span>
      </div>
    );
  }

  return (
    <Canvas
      shadows
      camera={{ position: [25, 15, 30], fov: 60, near: 0.1, far: 1000 }}
      style={{ width: '100%', height: '100%' }}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping }}
    >
      <SceneContents colony={colony} />
    </Canvas>
  );
}
