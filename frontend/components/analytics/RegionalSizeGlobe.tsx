'use client';

import { useRef, useMemo, useState, useCallback, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

const GLOBE_R = 2;
const ATMO_ALT = 0.18;

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

// ─── Earth texture → high-res land grid ────────────────────────────────────
function useEarthGrid(): { grid: boolean[][]; w: number; h: number } | null {
  const [data, setData] = useState<{ grid: boolean[][]; w: number; h: number } | null>(null);

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
      const g: boolean[][] = [];
      for (let y = 0; y < H; y++) {
        g[y] = [];
        for (let x = 0; x < W; x++) {
          const i = (y * W + x) * 4;
          g[y][x] = (px[i] + px[i + 1] + px[i + 2]) / 3 > 30;
        }
      }
      setData({ grid: g, w: W, h: H });
    };
    img.onerror = () => setData(null);
    img.src = '/earth-topology.png';
  }, []);

  return data;
}

function isLand(grid: boolean[][], W: number, H: number, lat: number, lon: number): boolean {
  const x = Math.floor(((lon + 180) / 360) * W) % W;
  const y = Math.floor(((90 - lat) / 180) * H);
  if (y < 0 || y >= H || x < 0 || x >= W) return false;
  return grid[y][x];
}

function isCoast(grid: boolean[][], W: number, H: number, lat: number, lon: number): boolean {
  const x = Math.floor(((lon + 180) / 360) * W) % W;
  const y = Math.floor(((90 - lat) / 180) * H);
  if (y < 0 || y >= H || x < 0 || x >= W || !grid[y][x]) return false;
  for (const [dy, dx] of [[-1,0],[1,0],[0,-1],[0,1]]) {
    const ny = y + dy, nx = (x + dx + W) % W;
    if (ny < 0 || ny >= H || !grid[ny][nx]) return true;
  }
  return false;
}

// ─── Dot sprite (sharp center, soft glow edge) ────────────────────────────
function createDotSprite(size = 64): THREE.Texture {
  const c = document.createElement('canvas');
  c.width = size; c.height = size;
  const ctx = c.getContext('2d')!;
  const h = size / 2;
  const g = ctx.createRadialGradient(h, h, 0, h, h, h);
  g.addColorStop(0, 'rgba(255,255,255,1)');
  g.addColorStop(0.35, 'rgba(255,255,255,0.95)');
  g.addColorStop(0.55, 'rgba(255,255,255,0.4)');
  g.addColorStop(0.75, 'rgba(255,255,255,0.08)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(c);
  tex.needsUpdate = true;
  return tex;
}

// ─── Dot cloud — 55k Fibonacci points ──────────────────────────────────────
function EarthDots({ earthData, dark }: { earthData: { grid: boolean[][]; w: number; h: number }; dark: boolean }) {
  const dotTex = useMemo(() => createDotSprite(), []);
  const { grid, w: W, h: H } = earthData;

  const geom = useMemo(() => {
    const pos: number[] = [];
    const col: number[] = [];

    const landBase = dark ? new THREE.Color('#5eead4') : new THREE.Color('#2dd4bf');
    const landBright = dark ? new THREE.Color('#99f6e4') : new THREE.Color('#5eead4');
    const coastCol = dark ? new THREE.Color('#ccfbf1') : new THREE.Color('#6ee7b7');
    const oceanCol = dark ? new THREE.Color('#0a0f1e') : new THREE.Color('#93c5fd');

    const N = 55000;
    const golden = Math.PI * (3 - Math.sqrt(5));

    for (let i = 0; i < N; i++) {
      const y = 1 - (i / (N - 1)) * 2;
      const rad = Math.sqrt(1 - y * y);
      const theta = golden * i;
      const x = Math.cos(theta) * rad;
      const z = Math.sin(theta) * rad;

      const lat = Math.asin(y) * (180 / Math.PI);
      const lon = Math.atan2(z, -x) * (180 / Math.PI);

      const onLand = isLand(grid, W, H, lat, lon);

      if (!onLand) {
        if (Math.random() > 0.018) continue;
        pos.push(x * GLOBE_R, y * GLOBE_R, z * GLOBE_R);
        col.push(oceanCol.r, oceanCol.g, oceanCol.b);
      } else {
        pos.push(x * GLOBE_R, y * GLOBE_R, z * GLOBE_R);
        const onCoast = isCoast(grid, W, H, lat, lon);
        if (onCoast) {
          col.push(coastCol.r, coastCol.g, coastCol.b);
        } else {
          const t = Math.random();
          const c = t > 0.6 ? landBright : landBase;
          const b = 0.6 + Math.random() * 0.4;
          col.push(c.r * b, c.g * b, c.b * b);
        }
      }
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    return geometry;
  }, [grid, W, H, dark]);

  return (
    <points geometry={geom}>
      <pointsMaterial
        size={dark ? 0.028 : 0.024}
        map={dotTex}
        vertexColors
        transparent
        opacity={dark ? 0.92 : 0.75}
        depthWrite={false}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

// ─── Atmosphere (GlowMesh approach from three-globe) ───────────────────────
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
    float intensity = pow(
      coefficient + dot(vVertexNormal, viewCamToVert),
      power
    );
    gl_FragColor = vec4(glowColor, intensity);
  }
`;

function GlobeAtmosphere({ dark }: { dark: boolean }) {
  const mat = useMemo(() => new THREE.ShaderMaterial({
    uniforms: {
      glowColor: { value: dark ? new THREE.Color('#14b8a6') : new THREE.Color('#99f6e4') },
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

  return <mesh material={mat}><sphereGeometry args={[GLOBE_R * (1 + ATMO_ALT), 64, 64]} /></mesh>;
}

// Subtle inner horizon rim
function InnerGlow({ dark }: { dark: boolean }) {
  const mat = useMemo(() => new THREE.ShaderMaterial({
    uniforms: {
      glowColor: { value: dark ? new THREE.Color('#0d9488') : new THREE.Color('#ccfbf1') },
    },
    vertexShader: `
      varying vec3 vNormal;
      varying vec3 vPos;
      void main() {
        vNormal = normalize(normalMatrix * normal);
        vPos = (modelViewMatrix * vec4(position,1.0)).xyz;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0);
      }
    `,
    fragmentShader: `
      uniform vec3 glowColor;
      varying vec3 vNormal;
      varying vec3 vPos;
      void main() {
        float rim = 1.0 - abs(dot(normalize(-vPos), vNormal));
        float g = pow(rim, 6.0) * 0.25;
        gl_FragColor = vec4(glowColor, g);
      }
    `,
    side: THREE.FrontSide,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  }), [dark]);

  return <mesh material={mat}><sphereGeometry args={[GLOBE_R + 0.005, 64, 64]} /></mesh>;
}

// ─── Data Point (country highlight) ────────────────────────────────────────
interface CountryData {
  country: string;
  lat: number;
  lon: number;
  topSize: string;
  totalCount: number;
  sizes: Record<string, number>;
}

function DataPoint({ data, dark, onHover, hovered }: {
  data: CountryData; dark: boolean;
  onHover: (d: CountryData | null) => void; hovered: boolean;
}) {
  const ref = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const pos = useMemo(() => latLonToVec3(data.lat, data.lon, GLOBE_R + 0.03), [data.lat, data.lon]);
  const sc = Math.max(0.035, Math.min(0.09, data.totalCount * 0.012));

  useFrame((state) => {
    if (ref.current) {
      const t = hovered ? sc * 2.2 : sc;
      ref.current.scale.lerp(new THREE.Vector3(t, t, t), 0.12);
    }
    if (ringRef.current) {
      const pulse = 1 + Math.sin(state.clock.elapsedTime * 2 + data.lat) * 0.25;
      const rs = (hovered ? sc * 4.5 : sc * 3) * pulse;
      ringRef.current.scale.set(rs, rs, rs);
      const m = ringRef.current.material as THREE.MeshBasicMaterial;
      m.opacity = THREE.MathUtils.lerp(m.opacity, hovered ? 0.6 : 0.15, 0.1);
    }
  });

  const color = dark ? '#f0fdfa' : '#0f766e';

  return (
    <group position={pos}>
      <mesh
        ref={ref}
        onPointerEnter={(e) => { e.stopPropagation(); onHover(data); }}
        onPointerLeave={() => onHover(null)}
      >
        <sphereGeometry args={[1, 16, 16]} />
        <meshBasicMaterial color={color} />
      </mesh>
      <mesh ref={ringRef}>
        <ringGeometry args={[0.5, 1, 32]} />
        <meshBasicMaterial color={color} transparent opacity={0.15} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

// ─── Globe Scene ───────────────────────────────────────────────────────────
function GlobeScene({ earthData, dataPoints, dark, onHover, hoveredCountry }: {
  earthData: { grid: boolean[][]; w: number; h: number };
  dataPoints: CountryData[]; dark: boolean;
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
        <meshBasicMaterial color={dark ? '#030712' : '#eff6ff'} />
      </mesh>
      <EarthDots earthData={earthData} dark={dark} />
      <InnerGlow dark={dark} />
      <GlobeAtmosphere dark={dark} />
      {dataPoints.map((d) => (
        <DataPoint
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
  const earthData = useEarthGrid();

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

  if (!earthData) {
    return (
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="text-center">
          <div className={`w-8 h-8 border-2 rounded-full animate-spin mx-auto mb-2 ${dark ? 'border-teal-900 border-t-teal-400' : 'border-teal-200 border-t-teal-500'}`} />
          <p className={`text-[10px] ${dark ? 'text-white/20' : 'text-gray-300'}`}>Loading globe...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full relative">
      <Canvas
        camera={{ position: [0, 0.4, 5.0], fov: 42 }}
        style={{ background: 'transparent' }}
        gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
        dpr={[1, 2]}
      >
        <GlobeScene
          earthData={earthData}
          dataPoints={dataPoints}
          dark={dark}
          onHover={handleHover}
          hoveredCountry={hovered?.country || null}
        />
        <Orbit />
      </Canvas>

      {hovered && (
        <div
          className={`absolute top-4 left-4 rounded-xl px-4 py-3 shadow-2xl border backdrop-blur-xl text-xs z-10 ${
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
