'use client';

import { useRef, useMemo, useState, useCallback, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

// ─── Compact land-mass data ────────────────────────────────────────────────
// Each row: [latitude, [lon_start, lon_end], ...]
// Covers -57 to +75 at 3-degree intervals. Approximates major continents.
const LAND: [number, number[][]][] = [
  [-57, [[-70,-64]]],
  [-54, [[-73,-63]]],
  [-51, [[-76,-64]]],
  [-48, [[-76,-65]]],
  [-45, [[-74,-65]]],
  [-42, [[-73,-63],[145,148]]],
  [-39, [[-72,-62],[141,149]]],
  [-36, [[-73,-57],[115,119],[136,151],[170,178]]],
  [-33, [[-72,-52],[115,121],[131,154],[170,178]]],
  [-30, [[-71,-49],[114,122],[129,154],[165,178]]],
  [-27, [[-70,-48],[113,123],[127,154]]],
  [-24, [[-68,-46],[113,135],[127,153]]],
  [-21, [[-65,-40],[115,152]]],
  [-18, [[-63,-39],[119,147]]],
  [-15, [[-76,-35],[121,145]]],
  [-12, [[-78,-35],[105,141]]],
  [-9, [[-79,-35],[96,141]]],
  [-6, [[-80,-35],[95,141]]],
  [-3, [[-80,-35],[-17,12],[29,52],[95,141]]],
  [0, [[-80,-35],[-17,11],[28,52],[95,141]]],
  [3, [[-80,-42],[-17,11],[25,52],[95,135]]],
  [6, [[-78,-50],[-17,11],[1,52],[95,128]]],
  [9, [[-78,-60],[-17,16],[0,52],[72,126]]],
  [12, [[-87,-62],[-17,17],[0,52],[72,123]]],
  [15, [[-100,-62],[-17,18],[0,52],[72,121]]],
  [18, [[-105,-66],[-17,19],[0,50],[68,120]]],
  [21, [[-108,-74],[-17,20],[33,50],[68,120]]],
  [24, [[-110,-77],[-15,25],[33,62],[68,120]]],
  [27, [[-113,-80],[-13,36],[33,72],[75,122]]],
  [30, [[-115,-80],[-10,37],[30,78],[80,122]]],
  [33, [[-118,-78],[-10,42],[26,82],[86,135]]],
  [36, [[-122,-75],[-10,45],[26,90],[100,140]]],
  [39, [[-124,-72],[-10,52],[25,100],[110,145]]],
  [42, [[-124,-68],[-10,55],[25,135],[140,145]]],
  [45, [[-125,-60],[-10,60],[25,145]]],
  [48, [[-126,-55],[-10,150]]],
  [51, [[-130,-55],[-10,150]]],
  [54, [[-135,-55],[-10,160]]],
  [57, [[-162,-50],[-10,172]]],
  [60, [[-166,-50],[-5,178]]],
  [63, [[-168,-52],[3,180]]],
  [66, [[-170,-54],[8,180]]],
  [69, [[-170,-55],[15,180]]],
  [72, [[-170,-58],[20,180]]],
  [75, [[-170,-62],[25,180]]],
];

function isLand(lat: number, lon: number): boolean {
  let bestRow: number[][] | null = null;
  let bestDist = Infinity;
  for (const [rlat, ranges] of LAND) {
    const d = Math.abs(lat - rlat);
    if (d < bestDist) { bestDist = d; bestRow = ranges; }
  }
  if (!bestRow || bestDist > 4) return false;
  for (const [s, e] of bestRow) {
    if (lon >= s && lon <= e) return true;
  }
  return false;
}

// ─── Country coordinates for data points ───────────────────────────────────
const COUNTRY_COORDS: Record<string, [number, number]> = {
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

// ─── Dot Texture ───────────────────────────────────────────────────────────
function createDotTexture(size = 64): THREE.Texture {
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d')!;
  const half = size / 2;
  const gradient = ctx.createRadialGradient(half, half, 0, half, half, half);
  gradient.addColorStop(0, 'rgba(255,255,255,1)');
  gradient.addColorStop(0.5, 'rgba(255,255,255,0.8)');
  gradient.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(canvas);
  tex.needsUpdate = true;
  return tex;
}

// ─── Earth Dots (the land mass point cloud) ────────────────────────────────
function EarthDots({ dark }: { dark: boolean }) {
  const pointsRef = useRef<THREE.Points>(null);
  const dotTex = useMemo(() => createDotTexture(), []);

  const { positions, colors } = useMemo(() => {
    const pos: number[] = [];
    const col: number[] = [];
    const R = 2;
    const landColor = dark
      ? new THREE.Color('#5eead4')  // teal-300
      : new THREE.Color('#5eead4');
    const faintColor = dark
      ? new THREE.Color('#1a1a2e')
      : new THREE.Color('#c8d6e0');

    // Fibonacci sphere for even distribution (~20000 points)
    const N = 22000;
    const golden = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < N; i++) {
      const y = 1 - (i / (N - 1)) * 2;
      const radius = Math.sqrt(1 - y * y);
      const theta = golden * i;
      const x = Math.cos(theta) * radius;
      const z = Math.sin(theta) * radius;

      // Convert to lat/lon
      const lat = Math.asin(y) * (180 / Math.PI);
      const lon = Math.atan2(z, -x) * (180 / Math.PI);

      const land = isLand(lat, lon);
      if (!land && Math.random() > 0.04) continue; // show ~4% ocean dots for subtle grid

      pos.push(x * R, y * R, z * R);
      if (land) {
        const brightness = 0.7 + Math.random() * 0.3;
        col.push(landColor.r * brightness, landColor.g * brightness, landColor.b * brightness);
      } else {
        col.push(faintColor.r, faintColor.g, faintColor.b);
      }
    }

    return {
      positions: new Float32Array(pos),
      colors: new Float32Array(col),
    };
  }, [dark, dotTex]);

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
        <bufferAttribute
          attach="attributes-color"
          args={[colors, 3]}
        />
      </bufferGeometry>
      <pointsMaterial
        size={dark ? 0.035 : 0.03}
        map={dotTex}
        vertexColors
        transparent
        opacity={dark ? 0.85 : 0.7}
        depthWrite={false}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

// ─── Atmosphere Glow ───────────────────────────────────────────────────────
function AtmosphereGlow({ dark }: { dark: boolean }) {
  const mat = useMemo(() => {
    return new THREE.ShaderMaterial({
      uniforms: {
        glowColor: { value: dark ? new THREE.Color('#134e4a') : new THREE.Color('#99f6e4') },
        viewVector: { value: new THREE.Vector3(0, 0, 5) },
      },
      vertexShader: `
        varying float intensity;
        void main() {
          vec3 vNormal = normalize(normalMatrix * normal);
          vec3 vNorml = normalize(normalMatrix * vec3(0.0, 0.0, 1.0));
          intensity = pow(0.65 - dot(vNormal, vNorml), 3.0);
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform vec3 glowColor;
        varying float intensity;
        void main() {
          gl_FragColor = vec4(glowColor, intensity * 0.4);
        }
      `,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending,
      transparent: true,
    });
  }, [dark]);

  return (
    <mesh material={mat}>
      <sphereGeometry args={[2.25, 64, 64]} />
    </mesh>
  );
}

// ─── Data Points (highlighted countries with analytics) ────────────────────
interface CountryData {
  country: string;
  lat: number;
  lon: number;
  topSize: string;
  totalCount: number;
  sizes: Record<string, number>;
}

function DataPoint({ data, dark, onHover, hovered }: {
  data: CountryData;
  dark: boolean;
  onHover: (d: CountryData | null) => void;
  hovered: boolean;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const pos = useMemo(() => latLonToVec3(data.lat, data.lon, 2.06), [data.lat, data.lon]);
  const scale = Math.max(0.04, Math.min(0.1, data.totalCount * 0.012));

  useFrame((state) => {
    if (meshRef.current) {
      const t = hovered ? scale * 2 : scale;
      meshRef.current.scale.lerp(new THREE.Vector3(t, t, t), 0.12);
    }
    if (ringRef.current) {
      const pulse = 1 + Math.sin(state.clock.elapsedTime * 3) * 0.15;
      const rs = hovered ? scale * 3.5 * pulse : scale * 2.5 * pulse;
      ringRef.current.scale.set(rs, rs, rs);
      (ringRef.current.material as THREE.MeshBasicMaterial).opacity = hovered ? 0.4 : 0.15;
    }
  });

  const color = dark ? '#f0fdfa' : '#0d9488';

  return (
    <group position={pos}>
      <mesh
        ref={meshRef}
        onPointerEnter={(e) => { e.stopPropagation(); onHover(data); }}
        onPointerLeave={() => onHover(null)}
      >
        <sphereGeometry args={[1, 16, 16]} />
        <meshBasicMaterial color={color} />
      </mesh>
      <mesh ref={ringRef}>
        <ringGeometry args={[0.8, 1, 32]} />
        <meshBasicMaterial color={color} transparent opacity={0.15} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

// ─── Scene: globe group that auto-rotates ──────────────────────────────────
function GlobeScene({ dataPoints, dark, onHover, hoveredCountry }: {
  dataPoints: CountryData[];
  dark: boolean;
  onHover: (d: CountryData | null) => void;
  hoveredCountry: string | null;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const { gl } = useThree();

  // Track drag state to pause rotation
  const dragging = useRef(false);
  useEffect(() => {
    const down = () => { dragging.current = true; };
    const up = () => { setTimeout(() => { dragging.current = false; }, 2000); };
    gl.domElement.addEventListener('pointerdown', down);
    gl.domElement.addEventListener('pointerup', up);
    return () => {
      gl.domElement.removeEventListener('pointerdown', down);
      gl.domElement.removeEventListener('pointerup', up);
    };
  }, [gl]);

  useFrame((_s, delta) => {
    if (groupRef.current && !dragging.current && !hoveredCountry) {
      groupRef.current.rotation.y += delta * 0.08;
    }
  });

  return (
    <group ref={groupRef} rotation={[0.15, -0.5, 0]}>
      {/* Subtle dark sphere base */}
      <mesh>
        <sphereGeometry args={[1.99, 64, 64]} />
        <meshBasicMaterial color={dark ? '#0a0a12' : '#e2e8f0'} />
      </mesh>
      <EarthDots dark={dark} />
      <AtmosphereGlow dark={dark} />
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

// ─── Controls (custom to allow rotation only) ─────────────────────────────
function RotateControls() {
  const { camera, gl } = useThree();
  const controlsRef = useRef<ReturnType<typeof import('@react-three/drei').OrbitControls> | null>(null);

  useEffect(() => {
    // Dynamic import to avoid SSR issues
    import('@react-three/drei').then(({ OrbitControls: OC }) => {
      // OrbitControls is a React component, we handle it differently
    });
  }, [camera, gl]);

  return null;
}

// ─── Main Export ───────────────────────────────────────────────────────────
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

  const dataPoints: CountryData[] = useMemo(() => {
    return Object.entries(by_country)
      .filter(([c]) => c !== 'Unknown' && COUNTRY_COORDS[c])
      .map(([country, sizes]) => {
        const [lat, lon] = COUNTRY_COORDS[country];
        const counts = raw_counts?.[country] || {};
        const totalCount = Object.values(counts).reduce((a, b) => a + b, 0);
        const topSize = top_size_by_country?.[country] ||
          Object.entries(sizes).sort(([, a], [, b]) => b - a)[0]?.[0] || 'M';
        return { country, lat, lon, topSize, totalCount: totalCount || 1, sizes };
      });
  }, [by_country, raw_counts, top_size_by_country]);

  const handleHover = useCallback((d: CountryData | null) => setHovered(d), []);

  return (
    <div className="relative w-full h-full" style={{ minHeight: 400 }}>
      <Canvas
        camera={{ position: [0, 0.5, 5], fov: 42 }}
        style={{ background: 'transparent' }}
        gl={{ antialias: true, alpha: true }}
        dpr={[1, 2]}
      >
        <GlobeScene
          dataPoints={dataPoints}
          dark={dark}
          onHover={handleHover}
          hoveredCountry={hovered?.country || null}
        />
        {/* Use drei OrbitControls inline */}
        <OrbitControlsInline />
      </Canvas>

      {/* Tooltip */}
      {hovered && (
        <div
          className={`absolute top-3 left-3 rounded-xl px-4 py-3 shadow-xl border backdrop-blur-md text-xs z-10 ${
            dark
              ? 'bg-black/80 border-white/10 text-white'
              : 'bg-white/95 border-gray-200 text-gray-900'
          }`}
          style={{ minWidth: 170, pointerEvents: 'none' }}
        >
          <div className="font-semibold text-sm mb-2">{hovered.country}</div>
          <div className={`text-[10px] mb-2 ${dark ? 'text-white/50' : 'text-gray-500'}`}>
            {hovered.totalCount} event{hovered.totalCount !== 1 ? 's' : ''}
          </div>
          <div className="space-y-1.5">
            {Object.entries(hovered.sizes)
              .sort(([, a], [, b]) => b - a)
              .map(([size, pct]) => (
                <div key={size} className="flex items-center gap-2">
                  <span className="font-medium w-7">{size}</span>
                  <div className={`flex-1 h-1.5 rounded-full overflow-hidden ${dark ? 'bg-white/10' : 'bg-gray-200'}`}>
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${Math.round(pct * 100)}%`,
                        backgroundColor: SIZE_COLORS[size] || '#64748b',
                      }}
                    />
                  </div>
                  <span className={`w-8 text-right tabular-nums ${dark ? 'text-white/60' : 'text-gray-500'}`}>
                    {Math.round(pct * 100)}%
                  </span>
                </div>
              ))}
          </div>
          <div className={`mt-2 pt-2 text-[10px] border-t ${dark ? 'border-white/10' : 'border-gray-100'}`}>
            Top size: <strong>{hovered.topSize}</strong>
          </div>
        </div>
      )}

      {/* Subtle instruction */}
      <div className={`absolute bottom-2 right-3 text-[10px] ${dark ? 'text-white/20' : 'text-gray-300'}`}>
        Drag to rotate
      </div>
    </div>
  );
}

// Separate component to use drei's OrbitControls inside Canvas
function OrbitControlsInline() {
  const { camera, gl } = useThree();
  const ref = useRef<unknown>(null);

  useEffect(() => {
    let controls: unknown;
    import('three/addons/controls/OrbitControls.js').then(({ OrbitControls }) => {
      controls = new OrbitControls(camera, gl.domElement);
      const c = controls as {
        enableZoom: boolean;
        enablePan: boolean;
        rotateSpeed: number;
        enableDamping: boolean;
        dampingFactor: number;
        update: () => void;
        dispose: () => void;
      };
      c.enableZoom = false;
      c.enablePan = false;
      c.rotateSpeed = 0.4;
      c.enableDamping = true;
      c.dampingFactor = 0.05;
      ref.current = c;
    });
    return () => {
      if (ref.current) (ref.current as { dispose: () => void }).dispose();
    };
  }, [camera, gl]);

  useFrame(() => {
    if (ref.current) (ref.current as { update: () => void }).update();
  });

  return null;
}
