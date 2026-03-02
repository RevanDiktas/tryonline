'use client';

import { useRef, useMemo, useState, useCallback, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

const GLOBE_R = 2;

const CC: Record<string, [number, number]> = {
  'Netherlands': [52.3, 4.9], 'United States': [39.8, -98.6],
  'United Kingdom': [54.0, -2.0], 'Germany': [51.2, 10.4],
  'France': [46.6, 2.2], 'Spain': [40.5, -3.7],
  'Italy': [41.9, 12.5], 'Belgium': [50.8, 4.3],
  'Switzerland': [46.8, 8.2], 'Austria': [47.5, 14.6],
  'Denmark': [56.3, 9.5], 'Sweden': [60.1, 18.6],
  'Norway': [60.5, 8.5], 'Poland': [51.9, 19.1],
  'Portugal': [39.4, -8.2], 'Ireland': [53.1, -8.2],
  'Finland': [61.9, 25.7], 'Greece': [39.1, 21.8],
  'Canada': [56.1, -106.3], 'Australia': [-25.3, 133.8],
  'Japan': [36.2, 138.3], 'South Korea': [35.9, 128.0],
  'China': [35.9, 104.2], 'India': [20.6, 79.0],
  'Brazil': [-14.2, -51.9], 'Mexico': [23.6, -102.6],
  'Russia': [61.5, 105.3], 'Turkey': [39.0, 35.2],
  'South Africa': [-30.6, 22.9], 'UAE': [23.4, 53.8],
  'Singapore': [1.4, 103.8], 'New Zealand': [-40.9, 174.9],
  'Argentina': [-38.4, -63.6], 'Indonesia': [-0.8, 113.9],
  'Thailand': [15.9, 100.9], 'Malaysia': [4.2, 101.9],
  'Czech Republic': [49.8, 15.5], 'Hungary': [47.2, 19.5],
  'Saudi Arabia': [23.9, 45.1], 'Colombia': [4.6, -74.3],
  'Romania': [45.9, 24.9], 'Vietnam': [14.1, 108.3],
  'Philippines': [12.9, 121.8],
};

const SIZE_COLORS: Record<string, string> = {
  'XS': '#cbd5e1', 'S': '#94a3b8', 'M': '#64748b',
  'L': '#475569', 'XL': '#334155', 'XXL': '#1e293b',
};

function latLonToVec3(lat: number, lon: number, r: number): [number, number, number] {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  return [
    -(r * Math.sin(phi) * Math.cos(theta)),
    r * Math.cos(phi),
    r * Math.sin(phi) * Math.sin(theta),
  ];
}

// ─── Blue marble → land grid (channel-based detection) ─────────────────────
// Ocean is blue-dominant, land is green/red-dominant. This is far more
// reliable than brightness thresholding on a topology heightmap.
type EarthGrid = { land: boolean[][]; coast: boolean[][]; w: number; h: number };

function useEarthGrid(): EarthGrid | null {
  const [data, setData] = useState<EarthGrid | null>(null);

  useEffect(() => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      const W = 720, H = 360;
      const canvas = document.createElement('canvas');
      canvas.width = W; canvas.height = H;
      const ctx = canvas.getContext('2d')!;
      ctx.drawImage(img, 0, 0, W, H);
      const px = ctx.getImageData(0, 0, W, H).data;

      // Detect ocean first (blue-dominant) — everything else is land.
      // Much more reliable than trying to detect land colors directly.
      const land: boolean[][] = [];
      for (let y = 0; y < H; y++) {
        land[y] = [];
        for (let x = 0; x < W; x++) {
          const i = (y * W + x) * 4;
          const r = px[i], g = px[i + 1], b = px[i + 2];
          const isOcean = (b > 30 && b >= r) || (b > 30 && b >= g) || (r < 40 && g < 60 && b > 25);
          land[y][x] = !isOcean && (r + g + b) > 50;
        }
      }

      // Erode noise: two passes, require 3+ of 8 neighbors to survive
      for (let pass = 0; pass < 2; pass++) {
        for (let y = 1; y < H - 1; y++) {
          for (let x = 0; x < W; x++) {
            if (!land[y][x]) continue;
            let n = 0;
            for (const [dy, dx] of [[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]]) {
              const ny = y + dy, nx = (x + dx + W) % W;
              if (land[ny]?.[nx]) n++;
            }
            if (n < 3) land[y][x] = false;
          }
        }
      }

      // Pre-compute coastlines
      const coast: boolean[][] = [];
      for (let y = 0; y < H; y++) {
        coast[y] = [];
        for (let x = 0; x < W; x++) {
          if (!land[y][x]) { coast[y][x] = false; continue; }
          let isCoast = false;
          for (const [dy, dx] of [[-1,0],[1,0],[0,-1],[0,1],[-1,-1],[-1,1],[1,-1],[1,1]]) {
            const ny = y + dy, nx = (x + dx + W) % W;
            if (ny < 0 || ny >= H || !land[ny][nx]) { isCoast = true; break; }
          }
          coast[y][x] = isCoast;
        }
      }

      setData({ land, coast, w: W, h: H });
    };
    img.onerror = () => setData(null);
    img.src = '/earth-blue-marble.jpg';
  }, []);

  return data;
}

function gridLookup(grid: boolean[][], W: number, H: number, lat: number, lon: number): boolean {
  const x = Math.floor(((lon + 180) / 360) * W) % W;
  const y = Math.floor(((90 - lat) / 180) * H);
  if (y < 0 || y >= H || x < 0 || x >= W) return false;
  return grid[y][x];
}

// ─── Dot sprite ────────────────────────────────────────────────────────────
function createDotSprite(size = 64): THREE.Texture {
  const c = document.createElement('canvas');
  c.width = size; c.height = size;
  const ctx = c.getContext('2d')!;
  const h = size / 2;
  const g = ctx.createRadialGradient(h, h, 0, h, h, h);
  g.addColorStop(0, 'rgba(255,255,255,1)');
  g.addColorStop(0.3, 'rgba(255,255,255,0.9)');
  g.addColorStop(0.55, 'rgba(255,255,255,0.35)');
  g.addColorStop(0.8, 'rgba(255,255,255,0.05)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(c);
  tex.needsUpdate = true;
  return tex;
}

// ─── Earth dots — 55k Fibonacci points ─────────────────────────────────────
function EarthDots({ earth, dark }: { earth: EarthGrid; dark: boolean }) {
  const dotTex = useMemo(() => createDotSprite(), []);

  const geom = useMemo(() => {
    const pos: number[] = [];
    const col: number[] = [];
    const { land, coast, w: W, h: H } = earth;

    const landBase = dark ? new THREE.Color('#4fd1c5') : new THREE.Color('#7dd3fc');
    const landBright = dark ? new THREE.Color('#81e6d9') : new THREE.Color('#a5f3fc');
    const coastCol = dark ? new THREE.Color('#b2f5ea') : new THREE.Color('#e0f2fe');

    const N = 55000;
    const golden = Math.PI * (3 - Math.sqrt(5));

    for (let i = 0; i < N; i++) {
      const y = 1 - (i / (N - 1)) * 2;
      const rad = Math.sqrt(1 - y * y);
      const theta = golden * i;
      const x = Math.cos(theta) * rad;
      const z = Math.sin(theta) * rad;

      const lat = Math.asin(y) * (180 / Math.PI);
      let lon = Math.atan2(z, -x) * (180 / Math.PI) - 180;
      if (lon < -180) lon += 360;

      if (!gridLookup(land, W, H, lat, lon)) continue;

      pos.push(x * GLOBE_R, y * GLOBE_R, z * GLOBE_R);
      const onCoast = gridLookup(coast, W, H, lat, lon);
      if (onCoast) {
        col.push(coastCol.r, coastCol.g, coastCol.b);
      } else {
        const c = Math.random() > 0.5 ? landBright : landBase;
        const b = 0.65 + Math.random() * 0.35;
        col.push(c.r * b, c.g * b, c.b * b);
      }
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    return geometry;
  }, [earth, dark]);

  return (
    <points geometry={geom}>
      <pointsMaterial
        size={0.026}
        map={dotTex}
        vertexColors
        transparent
        opacity={0.9}
        depthWrite={false}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

// ─── Atmosphere (GlowMesh from three-globe) ────────────────────────────────
const GLOW_VERT = `
  uniform float hollowRadius;
  varying vec3 vVertexWorldPosition;
  varying vec3 vVertexNormal;
  varying float vCamDist;
  varying float vAngularDist;
  void main() {
    vVertexNormal = normalize(normalMatrix * normal);
    vVertexWorldPosition = (modelMatrix * vec4(position, 1.0)).xyz;
    vec4 center = modelViewMatrix * vec4(0.0, 0.0, 0.0, 1.0);
    vCamDist = length(center);
    float edgeAngle = atan(hollowRadius / vCamDist);
    float vertAngle = acos(dot(
      normalize(modelViewMatrix * vec4(position, 1.0)),
      normalize(center)
    ));
    vAngularDist = vertAngle - edgeAngle;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;
const GLOW_FRAG = `
  uniform vec3 glowColor;
  uniform float coefficient;
  uniform float power;
  uniform float hollowRadius;
  varying vec3 vVertexNormal;
  varying vec3 vVertexWorldPosition;
  varying float vCamDist;
  varying float vAngularDist;
  void main() {
    if (vCamDist < hollowRadius) discard;
    if (vAngularDist < 0.0) discard;
    vec3 worldCamToVert = vVertexWorldPosition - cameraPosition;
    vec3 viewCamToVert = normalize((viewMatrix * vec4(worldCamToVert, 0.0)).xyz);
    float intensity = pow(coefficient + dot(vVertexNormal, viewCamToVert), power);
    gl_FragColor = vec4(glowColor, intensity);
  }
`;

function GlobeAtmosphere({ dark }: { dark: boolean }) {
  const mat = useMemo(() => new THREE.ShaderMaterial({
    uniforms: {
      glowColor: { value: dark ? new THREE.Color('#14b8a6') : new THREE.Color('#38bdf8') },
      coefficient: { value: 0.08 },
      power: { value: 4.0 },
      hollowRadius: { value: GLOBE_R },
    },
    vertexShader: GLOW_VERT,
    fragmentShader: GLOW_FRAG,
    side: THREE.BackSide,
    transparent: true,
    depthWrite: false,
  }), [dark]);

  return <mesh material={mat}><sphereGeometry args={[GLOBE_R * 1.18, 64, 64]} /></mesh>;
}

function InnerGlow({ dark }: { dark: boolean }) {
  const mat = useMemo(() => new THREE.ShaderMaterial({
    uniforms: {
      glowColor: { value: dark ? new THREE.Color('#0d9488') : new THREE.Color('#7dd3fc') },
    },
    vertexShader: `
      varying vec3 vN; varying vec3 vP;
      void main() {
        vN = normalize(normalMatrix * normal);
        vP = (modelViewMatrix * vec4(position,1.0)).xyz;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0);
      }
    `,
    fragmentShader: `
      uniform vec3 glowColor; varying vec3 vN; varying vec3 vP;
      void main() {
        float rim = 1.0 - abs(dot(normalize(-vP), vN));
        gl_FragColor = vec4(glowColor, pow(rim, 6.0) * 0.25);
      }
    `,
    side: THREE.FrontSide,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  }), [dark]);

  return <mesh material={mat}><sphereGeometry args={[GLOBE_R + 0.005, 64, 64]} /></mesh>;
}

// ─── Data Point — small clean dot + pulsing ring ───────────────────────────
interface CountryData {
  country: string;
  lat: number;
  lon: number;
  topSize: string;
  totalCount: number;
  sizes: Record<string, number>;
}

function DataDot({ data, dark, onHover, hovered }: {
  data: CountryData; dark: boolean;
  onHover: (d: CountryData | null) => void; hovered: boolean;
}) {
  const dotRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const pos = useMemo(() => latLonToVec3(data.lat, data.lon, GLOBE_R + 0.01), [data.lat, data.lon]);

  useFrame((state) => {
    if (dotRef.current) {
      const target = hovered ? 0.035 : 0.018;
      const s = dotRef.current.scale.x;
      const ns = s + (target - s) * 0.15;
      dotRef.current.scale.setScalar(ns);
    }
    if (ringRef.current) {
      const pulse = 1 + Math.sin(state.clock.elapsedTime * 3 + data.lat) * 0.3;
      const rs = hovered ? 0.06 * pulse : 0.035 * pulse;
      ringRef.current.scale.setScalar(rs);
      const m = ringRef.current.material as THREE.MeshBasicMaterial;
      m.opacity = hovered ? 0.5 : 0.15;
    }
  });

  const dotColor = dark ? '#ffffff' : '#0f766e';
  const ringColor = dark ? '#5eead4' : '#14b8a6';

  return (
    <group position={pos}>
      {/* Core dot */}
      <mesh
        ref={dotRef}
        scale={0.018}
        onPointerEnter={(e) => { e.stopPropagation(); onHover(data); }}
        onPointerLeave={() => onHover(null)}
      >
        <sphereGeometry args={[1, 12, 12]} />
        <meshBasicMaterial color={dotColor} />
      </mesh>
      {/* Pulse ring */}
      <mesh ref={ringRef} scale={0.035}>
        <ringGeometry args={[0.6, 1, 32]} />
        <meshBasicMaterial color={ringColor} transparent opacity={0.15} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

// ─── Globe Scene ───────────────────────────────────────────────────────────
function GlobeScene({ earth, dataPoints, dark, onHover, hoveredCountry }: {
  earth: EarthGrid; dataPoints: CountryData[]; dark: boolean;
  onHover: (d: CountryData | null) => void; hoveredCountry: string | null;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const { gl } = useThree();
  const dragging = useRef(false);
  const dragTimer = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    const down = () => {
      dragging.current = true;
      if (dragTimer.current) clearTimeout(dragTimer.current);
    };
    const up = () => {
      dragTimer.current = setTimeout(() => { dragging.current = false; }, 4000);
    };
    gl.domElement.addEventListener('pointerdown', down);
    gl.domElement.addEventListener('pointerup', up);
    return () => {
      gl.domElement.removeEventListener('pointerdown', down);
      gl.domElement.removeEventListener('pointerup', up);
      if (dragTimer.current) clearTimeout(dragTimer.current);
    };
  }, [gl]);

  useFrame((_s, delta) => {
    if (groupRef.current && !dragging.current && !hoveredCountry) {
      groupRef.current.rotation.y += delta * 0.04;
    }
  });

  return (
    <group ref={groupRef} rotation={[0.15, -0.6, 0.05]}>
      <mesh>
        <sphereGeometry args={[GLOBE_R - 0.005, 64, 64]} />
        <meshBasicMaterial color={dark ? '#030712' : '#1e1b4b'} />
      </mesh>
      <EarthDots earth={earth} dark={dark} />
      <InnerGlow dark={dark} />
      <GlobeAtmosphere dark={dark} />
      {dataPoints.map((d) => (
        <DataDot
          key={d.country}
          data={d}
          dark={dark}
          onHover={onHover}
          hovered={hoveredCountry === d.country}
        />
      ))}
    </group>
  );
}

// ─── Orbit Controls ────────────────────────────────────────────────────────
function Orbit() {
  const { camera, gl } = useThree();
  const ctrl = useRef<{ update: () => void; dispose: () => void } | null>(null);

  useEffect(() => {
    let c: { enableZoom: boolean; enablePan: boolean; rotateSpeed: number; enableDamping: boolean; dampingFactor: number; update: () => void; dispose: () => void };
    import('three/addons/controls/OrbitControls.js').then(({ OrbitControls }) => {
      c = new OrbitControls(camera, gl.domElement) as typeof c;
      c.enableZoom = false;
      c.enablePan = false;
      c.rotateSpeed = 0.3;
      c.enableDamping = true;
      c.dampingFactor = 0.05;
      ctrl.current = c;
    });
    return () => { if (ctrl.current) ctrl.current.dispose(); };
  }, [camera, gl]);

  useFrame(() => { ctrl.current?.update(); });
  return null;
}

// ─── Main Component ────────────────────────────────────────────────────────
export default function RegionalSizeGlobe({
  by_country,
  raw_counts,
  top_size_by_country,
  dark = false,
}: {
  by_country: Record<string, Record<string, number>>;
  raw_counts?: Record<string, Record<string, number>>;
  top_size_by_country?: Record<string, string>;
  dark?: boolean;
}) {
  const [hovered, setHovered] = useState<CountryData | null>(null);
  const earth = useEarthGrid();

  const dataPoints: CountryData[] = useMemo(() => {
    return Object.entries(by_country)
      .filter(([c]) => c !== 'Unknown' && CC[c])
      .map(([country, sizes]) => {
        const [lat, lon] = CC[country];
        const counts = raw_counts?.[country] || {};
        const totalCount = Object.values(counts).reduce((a, b) => a + b, 0);
        const topSize = top_size_by_country?.[country] ||
          Object.entries(sizes).sort(([, a], [, b]) => b - a)[0]?.[0] || 'M';
        return { country, lat, lon, topSize, totalCount: totalCount || 1, sizes };
      });
  }, [by_country, raw_counts, top_size_by_country]);

  const handleHover = useCallback((d: CountryData | null) => setHovered(d), []);

  if (!earth) {
    return (
      <div className="absolute inset-0 flex items-center justify-center">
        <div className={`w-8 h-8 border-2 rounded-full animate-spin ${dark ? 'border-teal-900 border-t-teal-400' : 'border-teal-200 border-t-teal-500'}`} />
      </div>
    );
  }

  return (
    <div className="w-full h-full relative">
      <Canvas
        camera={{ position: [0, 0.2, 8.5], fov: 38 }}
        style={{ background: 'transparent' }}
        gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
        dpr={[1, 2]}
      >
        <GlobeScene
          earth={earth}
          dataPoints={dataPoints}
          dark={dark}
          onHover={handleHover}
          hoveredCountry={hovered?.country || null}
        />
        <Orbit />
      </Canvas>

      {/* Tooltip */}
      {hovered && (
        <div
          className={`absolute top-4 right-4 rounded-xl px-4 py-3 shadow-2xl border backdrop-blur-xl text-xs z-10 ${
            dark ? 'bg-black/80 border-white/10 text-white' : 'bg-white/90 border-gray-200 text-gray-900'
          }`}
          style={{ minWidth: 170, pointerEvents: 'none' }}
        >
          <div className="font-semibold text-sm mb-1">{hovered.country}</div>
          <div className={`text-[10px] mb-2 ${dark ? 'text-white/35' : 'text-gray-400'}`}>
            {hovered.totalCount} event{hovered.totalCount !== 1 ? 's' : ''}
          </div>
          <div className="space-y-1.5">
            {Object.entries(hovered.sizes)
              .sort(([, a], [, b]) => b - a)
              .map(([size, pct]) => (
                <div key={size} className="flex items-center gap-2">
                  <span className="font-medium w-6">{size}</span>
                  <div className={`flex-1 h-1 rounded-full overflow-hidden ${dark ? 'bg-white/10' : 'bg-gray-200'}`}>
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${Math.round(pct * 100)}%`, backgroundColor: SIZE_COLORS[size] || '#64748b' }}
                    />
                  </div>
                  <span className={`w-7 text-right tabular-nums text-[10px] ${dark ? 'text-white/45' : 'text-gray-500'}`}>
                    {Math.round(pct * 100)}%
                  </span>
                </div>
              ))}
          </div>
          <div className={`mt-2 pt-1.5 text-[10px] border-t ${dark ? 'border-white/8' : 'border-gray-100'}`}>
            Top size: <strong>{hovered.topSize}</strong>
          </div>
        </div>
      )}

      <div className={`absolute bottom-2 right-3 text-[9px] ${dark ? 'text-white/10' : 'text-gray-200'}`}>
        Drag to rotate
      </div>
    </div>
  );
}
