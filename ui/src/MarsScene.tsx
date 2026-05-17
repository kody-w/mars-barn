import { useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Stars } from '@react-three/drei';
import * as THREE from 'three';
import { Mountain, Sun, Wind, MapPin } from 'lucide-react';

const RAW = 'https://raw.githubusercontent.com/kody-w/mars-barn/main';

// ---------- terrain ----------
// Domain: ~1200km square centered on (18.65°N, 226.2°E) — the Olympus Mons summit.
// World units: 1 unit = 1 km. Height exaggeration ×2 for visibility.
const DOMAIN_KM = 1200;
const RES = 256;
const HEIGHT_SCALE = 2;

// Olympus Mons parameters (real-world figures)
const OLYMPUS = {
  cx: 0, cy: 0,             // centered in the panel
  radiusKm: 312,            // base radius
  heightKm: 21.9,           // summit height above mean
  calderaRadiusKm: 40,      // central caldera
  calderaDepthKm: 2.5,
  scarpRadiusKm: 320,       // basal scarp
  scarpHeightKm: 5,
};

// cheap deterministic hash noise for terrain texture
function hash(x: number, y: number, seed = 1): number {
  const s = Math.sin(x * 127.1 + y * 311.7 + seed * 74.7) * 43758.5453;
  return s - Math.floor(s);
}
function smoothNoise(x: number, y: number, seed = 1): number {
  const xi = Math.floor(x), yi = Math.floor(y);
  const xf = x - xi, yf = y - yi;
  const a = hash(xi, yi, seed), b = hash(xi + 1, yi, seed);
  const c = hash(xi, yi + 1, seed), d = hash(xi + 1, yi + 1, seed);
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  return a * (1 - u) * (1 - v) + b * u * (1 - v) + c * (1 - u) * v + d * u * v;
}
function fbm(x: number, y: number, octaves = 5): number {
  let sum = 0, amp = 1, freq = 1, norm = 0;
  for (let i = 0; i < octaves; i++) {
    sum += smoothNoise(x * freq, y * freq, i + 1) * amp;
    norm += amp;
    amp *= 0.5;
    freq *= 2;
  }
  return sum / norm;
}

function elevation(xKm: number, yKm: number): number {
  const dx = xKm - OLYMPUS.cx, dy = yKm - OLYMPUS.cy;
  const r = Math.sqrt(dx * dx + dy * dy);

  // shield volcano: gentle dome, power-law falloff
  let h = 0;
  if (r < OLYMPUS.radiusKm) {
    const t = 1 - r / OLYMPUS.radiusKm;
    h = OLYMPUS.heightKm * Math.pow(t, 1.5);
  }

  // central caldera: depression at summit
  if (r < OLYMPUS.calderaRadiusKm) {
    const t = 1 - r / OLYMPUS.calderaRadiusKm;
    h -= OLYMPUS.calderaDepthKm * Math.pow(t, 0.7);
  }

  // basal scarp: cliff that defines Olympus Mons's edge
  if (r > OLYMPUS.radiusKm && r < OLYMPUS.scarpRadiusKm) {
    const t = (OLYMPUS.scarpRadiusKm - r) / (OLYMPUS.scarpRadiusKm - OLYMPUS.radiusKm);
    h += OLYMPUS.scarpHeightKm * 0.6 * t;
  }

  // multi-scale noise: large undulations + fine roughness
  const macro = (fbm(xKm * 0.003, yKm * 0.003, 4) - 0.5) * 1.2;
  const micro = (fbm(xKm * 0.02, yKm * 0.02, 3) - 0.5) * 0.25;
  h += macro + micro;

  return h * HEIGHT_SCALE;
}

function useTerrainGeometry() {
  return useMemo(() => {
    const geo = new THREE.PlaneGeometry(DOMAIN_KM, DOMAIN_KM, RES - 1, RES - 1);
    geo.rotateX(-Math.PI / 2);
    const pos = geo.attributes.position as THREE.BufferAttribute;
    const colors = new Float32Array(pos.count * 3);
    const COLD = new THREE.Color('#3a1d0f');
    const MID  = new THREE.Color('#a64a26');
    const HIGH = new THREE.Color('#e8b48a');
    const DUST = new THREE.Color('#c97a3f');
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i), z = pos.getZ(i);
      const h = elevation(x, z);
      pos.setY(i, h);
      const t = THREE.MathUtils.clamp((h / HEIGHT_SCALE + 2) / 24, 0, 1);
      const c = new THREE.Color();
      if (t < 0.4) c.lerpColors(COLD, MID, t / 0.4);
      else if (t < 0.75) c.lerpColors(MID, DUST, (t - 0.4) / 0.35);
      else c.lerpColors(DUST, HIGH, (t - 0.75) / 0.25);
      colors[i * 3] = c.r; colors[i * 3 + 1] = c.g; colors[i * 3 + 2] = c.b;
    }
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geo.computeVertexNormals();
    return geo;
  }, []);
}

// Habitat sits at panel-center (the summit) — clamp to local terrain height.
function habitatHeight(): number {
  return elevation(0, 0);
}

// ---------- sun from areocentric longitude L_s ----------
// Mars axial tilt ≈ 25.19°. solar declination ≈ tilt × sin(L_s).
// Sun elevation at local noon for habitat latitude:
function sunDirectionFromLs(lsDeg: number, timeOfDay: number, latDeg = 18.65): THREE.Vector3 {
  const lsRad = (lsDeg * Math.PI) / 180;
  const decl = (25.19 * Math.PI / 180) * Math.sin(lsRad);
  const lat = (latDeg * Math.PI) / 180;
  // hour angle: -π at midnight, 0 at noon, +π again at midnight
  const H = (timeOfDay - 0.5) * 2 * Math.PI;
  const sinAlt = Math.sin(lat) * Math.sin(decl) + Math.cos(lat) * Math.cos(decl) * Math.cos(H);
  const alt = Math.asin(THREE.MathUtils.clamp(sinAlt, -1, 1));
  const cosAz = (Math.sin(decl) - Math.sin(alt) * Math.sin(lat)) / (Math.cos(alt) * Math.cos(lat) + 1e-9);
  const az = Math.acos(THREE.MathUtils.clamp(cosAz, -1, 1)) * (H > 0 ? 1 : -1);
  // sky-dome direction (y up, +z south)
  return new THREE.Vector3(
    Math.cos(alt) * Math.sin(az),
    Math.sin(alt),
    -Math.cos(alt) * Math.cos(az),
  ).normalize();
}

function Sky({ sunDir, dustOpacity }: { sunDir: THREE.Vector3; dustOpacity: number }) {
  const { scene } = useThree();
  useEffect(() => {
    const base = new THREE.Color('#1a0a05');         // night
    const day = new THREE.Color('#d68a52');           // mars peach
    const dusty = new THREE.Color('#6b3a1f');         // dust-laden
    const dayFactor = THREE.MathUtils.clamp(sunDir.y * 1.5 + 0.1, 0, 1);
    const target = day.clone().lerp(base, 1 - dayFactor).lerp(dusty, dustOpacity * 0.6);
    scene.background = target;
    scene.fog = new THREE.FogExp2(target.getHex(), 0.0006 + dustOpacity * 0.0035);
  }, [scene, sunDir, dustOpacity]);
  return null;
}

function SunSphere({ sunDir, dustOpacity }: { sunDir: THREE.Vector3; dustOpacity: number }) {
  const r = 800;
  const pos = sunDir.clone().multiplyScalar(r);
  const colorHex = dustOpacity > 0.3 ? '#ffb27a' : '#fff1d1';
  return (
    <mesh position={pos.toArray()}>
      <sphereGeometry args={[18, 24, 24]} />
      <meshBasicMaterial color={colorHex} />
    </mesh>
  );
}

// ---------- dust storm particles ----------
function DustStorm({ active, sunDir }: { active: boolean; sunDir: THREE.Vector3 }) {
  const ref = useRef<THREE.Points>(null);
  const COUNT = 4000;

  const { positions, velocities } = useMemo(() => {
    const p = new Float32Array(COUNT * 3);
    const v = new Float32Array(COUNT * 3);
    for (let i = 0; i < COUNT; i++) {
      p[i * 3]     = (Math.random() - 0.5) * DOMAIN_KM * 1.2;
      p[i * 3 + 1] = Math.random() * 12 + 1;
      p[i * 3 + 2] = (Math.random() - 0.5) * DOMAIN_KM * 1.2;
      v[i * 3]     = 0.4 + Math.random() * 0.8;
      v[i * 3 + 1] = (Math.random() - 0.5) * 0.05;
      v[i * 3 + 2] = (Math.random() - 0.5) * 0.4;
    }
    return { positions: p, velocities: v };
  }, []);

  useFrame((_, delta) => {
    if (!ref.current) return;
    const target = active ? 1 : 0;
    const mat = ref.current.material as THREE.PointsMaterial;
    mat.opacity = THREE.MathUtils.lerp(mat.opacity, target * 0.55, Math.min(1, delta * 1.2));
    if (mat.opacity < 0.01) return;
    const arr = ref.current.geometry.attributes.position.array as Float32Array;
    const half = DOMAIN_KM * 0.6;
    for (let i = 0; i < COUNT; i++) {
      arr[i * 3]     += velocities[i * 3]     * delta * 60;
      arr[i * 3 + 1] += velocities[i * 3 + 1] * delta * 60;
      arr[i * 3 + 2] += velocities[i * 3 + 2] * delta * 60;
      if (arr[i * 3] > half) arr[i * 3] = -half;
      if (arr[i * 3 + 2] > half) arr[i * 3 + 2] = -half;
      if (arr[i * 3 + 2] < -half) arr[i * 3 + 2] = half;
    }
    ref.current.geometry.attributes.position.needsUpdate = true;
  });

  const dustColor = sunDir.y > 0 ? '#d08050' : '#5a2812';

  return (
    <points ref={ref} frustumCulled={false}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} count={COUNT} />
      </bufferGeometry>
      <pointsMaterial size={2.5} color={dustColor} transparent opacity={0} depthWrite={false} sizeAttenuation />
    </points>
  );
}

// ---------- habitat marker ----------
function Habitat({ y, alive }: { y: number; alive: boolean }) {
  const beamRef = useRef<THREE.Mesh>(null);
  useFrame((state) => {
    if (beamRef.current) {
      const t = state.clock.getElapsedTime();
      (beamRef.current.material as THREE.MeshBasicMaterial).opacity = 0.35 + Math.sin(t * 2) * 0.15;
    }
  });
  const color = alive ? '#34d399' : '#f43f5e';
  return (
    <group position={[0, y, 0]}>
      {/* dome */}
      <mesh position={[0, 1.2, 0]}>
        <sphereGeometry args={[2.5, 16, 12, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <meshStandardMaterial color="#e2e8f0" metalness={0.7} roughness={0.25} />
      </mesh>
      {/* base */}
      <mesh position={[0, 0.6, 0]}>
        <cylinderGeometry args={[3, 3.2, 1.2, 16]} />
        <meshStandardMaterial color="#94a3b8" metalness={0.4} roughness={0.6} />
      </mesh>
      {/* status beam */}
      <mesh ref={beamRef} position={[0, 30, 0]}>
        <cylinderGeometry args={[0.4, 0.4, 60, 8, 1, true]} />
        <meshBasicMaterial color={color} transparent opacity={0.4} depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      {/* glow disc */}
      <mesh position={[0, 0.05, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[3.5, 5, 32]} />
        <meshBasicMaterial color={color} transparent opacity={0.5} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

// ---------- main scene ----------
interface SceneState {
  sol: number;
  solar_longitude: number;
  dust_storm_active: boolean;
  alive: boolean;
  population: number;
}

function TerrainMesh() {
  const geo = useTerrainGeometry();
  return (
    <mesh geometry={geo} receiveShadow>
      <meshStandardMaterial vertexColors roughness={0.95} metalness={0.02} flatShading={false} />
    </mesh>
  );
}

function SceneContents({ state, timeOfDay }: { state: SceneState; timeOfDay: number }) {
  const sunDir = useMemo(
    () => sunDirectionFromLs(state.solar_longitude, timeOfDay),
    [state.solar_longitude, timeOfDay],
  );
  const dustOpacity = state.dust_storm_active ? 1 : 0;
  const sunIntensity = THREE.MathUtils.clamp(sunDir.y * 1.8, 0, 1.5) * (1 - dustOpacity * 0.5);
  const habY = habitatHeight();

  return (
    <>
      <Sky sunDir={sunDir} dustOpacity={dustOpacity} />
      <Stars radius={2000} depth={200} count={3000} factor={6} fade speed={0.5} />
      <ambientLight intensity={0.18 + dustOpacity * 0.05} color="#ffd6b0" />
      <directionalLight
        position={sunDir.clone().multiplyScalar(500).toArray()}
        intensity={sunIntensity}
        color={dustOpacity > 0.2 ? '#ffb27a' : '#fff0d8'}
      />
      <SunSphere sunDir={sunDir} dustOpacity={dustOpacity} />
      <TerrainMesh />
      <Habitat y={habY} alive={state.alive} />
      <DustStorm active={state.dust_storm_active} sunDir={sunDir} />
    </>
  );
}

function CameraRig() {
  const { camera } = useThree();
  useEffect(() => {
    camera.position.set(120, 80, 180);
    camera.lookAt(0, 30, 0);
  }, [camera]);
  return null;
}

export default function MarsScene() {
  const [state, setState] = useState<SceneState>({
    sol: 0, solar_longitude: 0, dust_storm_active: false, alive: true, population: 6,
  });
  const [timeOfDay, setTimeOfDay] = useState(0.5);
  const [autoTime, setAutoTime] = useState(true);

  useEffect(() => {
    fetch(`${RAW}/state/colony.json`)
      .then((r) => r.ok ? r.json() : null)
      .then((d) => {
        if (!d) return;
        setState({
          sol: d.sol ?? 0,
          solar_longitude: d.solar_longitude ?? 0,
          dust_storm_active: !!d.dust_storm_active,
          alive: (d.alive !== false) && (d.population ?? 1) > 0,
          population: d.population ?? 0,
        });
      })
      .catch(() => { /* keep defaults */ });
  }, []);

  useEffect(() => {
    if (!autoTime) return;
    const id = setInterval(() => {
      setTimeOfDay((t) => (t + 0.0025) % 1);
    }, 80);
    return () => clearInterval(id);
  }, [autoTime]);

  const lsForLabel = state.solar_longitude.toFixed(1);
  const hour = (timeOfDay * 24.66) % 24.66;
  const hh = Math.floor(hour).toString().padStart(2, '0');
  const mm = Math.floor((hour - Math.floor(hour)) * 60).toString().padStart(2, '0');

  return (
    <div className="relative w-full h-[560px] rounded-2xl overflow-hidden border border-stone-800 bg-black">
      <Canvas
        camera={{ fov: 55, near: 0.5, far: 5000 }}
        dpr={[1, 2]}
        gl={{ antialias: true, powerPreference: 'high-performance' }}
      >
        <CameraRig />
        <SceneContents state={state} timeOfDay={timeOfDay} />
        <OrbitControls
          enablePan
          minDistance={20}
          maxDistance={800}
          maxPolarAngle={Math.PI / 2.05}
          target={[0, 30, 0]}
        />
      </Canvas>

      {/* HUD */}
      <div className="absolute top-4 left-4 flex flex-col gap-2 text-xs font-mono pointer-events-none">
        <div className="bg-black/60 backdrop-blur border border-white/10 rounded-lg px-3 py-2 text-zinc-200">
          <div className="flex items-center gap-2"><Mountain size={12} className="text-orange-400" /> Olympus Mons · 18.65°N 226.2°E</div>
          <div className="flex items-center gap-2 mt-1"><MapPin size={12} className="text-emerald-400" /> Habitat · summit caldera rim</div>
        </div>
        <div className="bg-black/60 backdrop-blur border border-white/10 rounded-lg px-3 py-2 text-zinc-200">
          <div className="flex items-center gap-2"><Sun size={12} className="text-amber-400" /> L<sub>s</sub> = {lsForLabel}° · local {hh}:{mm}</div>
          <div className="flex items-center gap-2 mt-1">
            <Wind size={12} className={state.dust_storm_active ? 'text-orange-400 animate-pulse' : 'text-zinc-500'} />
            {state.dust_storm_active ? 'Dust storm active' : 'Clear skies'}
          </div>
          <div className="mt-1 text-zinc-500">Sol {state.sol} · pop {state.population}</div>
        </div>
      </div>

      <div className="absolute bottom-4 left-4 flex items-center gap-3 text-xs font-mono pointer-events-auto">
        <label className="flex items-center gap-2 bg-black/60 backdrop-blur border border-white/10 rounded-lg px-3 py-2 text-zinc-300 cursor-pointer">
          <input
            type="checkbox"
            checked={autoTime}
            onChange={(e) => setAutoTime(e.target.checked)}
            className="accent-orange-500"
          />
          auto day/night
        </label>
        <div className="bg-black/60 backdrop-blur border border-white/10 rounded-lg px-3 py-2 text-zinc-300 flex items-center gap-2">
          <span className="text-zinc-500">time</span>
          <input
            type="range" min={0} max={1} step={0.005}
            value={timeOfDay}
            onChange={(e) => { setAutoTime(false); setTimeOfDay(parseFloat(e.target.value)); }}
            className="w-40 accent-orange-500"
          />
        </div>
      </div>

      <div className="absolute bottom-4 right-4 text-[10px] text-zinc-500 bg-black/40 rounded px-2 py-1 font-mono">
        drag · scroll · right-drag to pan
      </div>
    </div>
  );
}
