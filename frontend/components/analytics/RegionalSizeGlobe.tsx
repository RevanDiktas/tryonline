'use client';

import { useRef, useMemo, useState, useCallback, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

// ─── Country coordinates ───────────────────────────────────────────────────
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

// ─── Earth texture → land grid ─────────────────────────────────────────────
function useEarthGrid(): boolean[][] | null {
  const [grid, setGrid] = useState<boolean[][] | null>(null);

  useEffect(() => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      const W = 360, H = 180;
      const canvas = document.createElement('canvas');
      canvas.width = W;
      canvas.height = H;
      const ctx = canvas.getContext('2d')!;
      ctx.drawImage(img, 0, 0, W, H);
      const px = ctx.getImageData(0, 0, W, H).data;
      const g: boolean[][] = [];
      for (let y = 0; y < H; y++) {
        g[y] = [];
        for (let x = 0; x < W; x++) {
          const i = (y * W + x) * 4;
          const brightness = (px[i] + px[i + 1] + px[i + 2]) / 3;
          g[y][x] = brightness > 28;
        }
      }
      setGrid(g);
    };
    img.onerror = () => setGrid(null);
    img.src = '/earth-topology.png';
  }, []);

  return grid;
}

function isLandFromGrid(grid: boolean[][], lat: number, lon: number): boolean {
  const x = Math.floor(((lon + 180) / 360) * 360) % 360;
  const y = Math.floor(((90 - lat) / 180) * 180);
  if (y < 0 || y >= 180 || x < 0 || x >= 360) return false;
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
  g.addColorStop(0.4, 'rgba(255,255,255,0.9)');
  g.addColorStop(0.7, 'rgba(255,255,255,0.3)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(c);
  tex.needsUpdate = true;
  return tex;
}

// ─── Dot cloud — the earth ─────────────────────────────────────────────────
function EarthDots({ grid, dark }: { grid: boolean[][]; dark: boolean }) {
  const dotTex = useMemo(() => createDotSprite(), []);

  const geom = useMemo(() => {
    const pos: number[] = [];
    const col: number[] = [];
    const R = 2;

    const landBase = dark ? new THREE.Color('#5eead4') : new THREE.Color('#2dd4bf');
    const landBright = dark ? new THREE.Color('#99f6e4') : new THREE.Color('#5eead4');
    const oceanCol = dark ? new THREE.Color('#0f172a') : new THREE.Color('#94a3b8');

    // Fibonacci sphere: ~40k points gives dense coverage
    const N = 42000;
    const golden = Math.PI * (3 - Math.sqrt(5));

    for (let i = 0; i < N; i++) {
      const y = 1 - (i / (N - 1)) * 2;
      const rad = Math.sqrt(1 - y * y);
      const theta = golden * i;
      const x = Math.cos(theta) * rad;
      const z = Math.sin(theta) * rad;

      const lat = Math.asin(y) * (180 / Math.PI);
      const lon = Math.atan2(z, -x) * (180 / Math.PI);

      const land = isLandFromGrid(grid, lat, lon);

      // Skip most ocean points for clean look
      if (!land) {
        if (Math.random() > 0.015) continue;
        pos.push(x * R, y * R, z * R);
        col.push(oceanCol.r, oceanCol.g, oceanCol.b);
      } else {
        pos.push(x * R, y * R, z * R);
        const t = Math.random();
        const c = t > 0.7 ? landBright : landBase;
        const b = 0.6 + Math.random() * 0.4;
        col.push(c.r * b, c.g * b, c.b * b);
      }
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    return geometry;
  }, [grid, dark]);

  return (
    <points geometry={geom}>
      <pointsMaterial
        size={0.025}
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

// ─── Atmosphere ────────────────────────────────────────────────────────────
const ATMO_VERT = `
  varying vec3 vNormal;
  varying vec3 vPosition;
  void main() {
    vNormal = normalize(normalMatrix * normal);
    vPosition = (modelViewMatrix * vec4(position, 1.0)).xyz;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const ATMO_FRAG = `
  uniform vec3 glowColor;
  uniform float intensity;
  varying vec3 vNormal;
  varying vec3 vPosition;
  void main() {
    vec3 viewDir = normalize(-vPosition);
    float rim = 1.0 - max(0.0, dot(viewDir, vNormal));
    float glow = pow(rim, 3.0) * intensity;
    gl_FragColor = vec4(glowColor, glow * 0.6);
  }
`;

function Atmosphere({ dark }: { dark: boolean }) {
  const mat = useMemo(() => new THREE.ShaderMaterial({
    uniforms: {
      glowColor: { value: dark ? new THREE.Color('#0d9488') : new THREE.Color('#99f6e4') },
      intensity: { value: dark ? 1.5 : 1.0 },
    },
    vertexShader: ATMO_VERT,
    fragmentShader: ATMO_FRAG,
    side: THREE.BackSide,
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  }), [dark]);

  return <mesh material={mat}><sphereGeometry args={[2.4, 64, 64]} /></mesh>;
}

// Inner glow (subtle horizon line)
function InnerGlow({ dark }: { dark: boolean }) {
  const mat = useMemo(() => new THREE.ShaderMaterial({
    uniforms: {
      glowColor: { value: dark ? new THREE.Color('#134e4a') : new THREE.Color('#ccfbf1') },
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
        float g = pow(rim, 5.0) * 0.35;
        gl_FragColor = vec4(glowColor, g);
      }
    `,
    side: THREE.FrontSide,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  }), [dark]);

  return <mesh material={mat}><sphereGeometry args={[2.01, 64, 64]} /></mesh>;
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
  const pos = useMemo(() => latLonToVec3(data.lat, data.lon, 2.04), [data.lat, data.lon]);
  const sc = Math.max(0.03, Math.min(0.08, data.totalCount * 0.01));

  useFrame((state) => {
    if (ref.current) {
      const t = hovered ? sc * 2.5 : sc;
      ref.current.scale.lerp(new THREE.Vector3(t, t, t), 0.1);
    }
    if (ringRef.current) {
      const pulse = 1 + Math.sin(state.clock.elapsedTime * 2.5 + data.lat) * 0.2;
      const rs = (hovered ? sc * 4 : sc * 2.8) * pulse;
      ringRef.current.scale.set(rs, rs, rs);
      (ringRef.current.material as THREE.MeshBasicMaterial).opacity = hovered ? 0.5 : 0.2;
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
        <ringGeometry args={[0.6, 1, 32]} />
        <meshBasicMaterial color={color} transparent opacity={0.2} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

// ─── Globe Scene ───────────────────────────────────────────────────────────
function GlobeScene({ grid, dataPoints, dark, onHover, hoveredCountry }: {
  grid: boolean[][]; dataPoints: CountryData[]; dark: boolean;
  onHover: (d: CountryData | null) => void; hoveredCountry: string | null;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const { gl } = useThree();
  const dragging = useRef(false);

  useEffect(() => {
    const down = () => { dragging.current = true; };
    const up = () => { setTimeout(() => { dragging.current = false; }, 3000); };
    gl.domElement.addEventListener('pointerdown', down);
    gl.domElement.addEventListener('pointerup', up);
    return () => {
      gl.domElement.removeEventListener('pointerdown', down);
      gl.domElement.removeEventListener('pointerup', up);
    };
  }, [gl]);

  useFrame((_s, delta) => {
    if (groupRef.current && !dragging.current && !hoveredCountry) {
      groupRef.current.rotation.y += delta * 0.06;
    }
  });

  return (
    <group ref={groupRef} rotation={[0.2, -0.8, 0.05]}>
      {/* Dark sphere core */}
      <mesh>
        <sphereGeometry args={[1.995, 64, 64]} />
        <meshBasicMaterial color={dark ? '#050510' : '#dbeafe'} />
      </mesh>
      <EarthDots grid={grid} dark={dark} />
      <InnerGlow dark={dark} />
      <Atmosphere dark={dark} />
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

// ─── Orbit Controls (runtime import) ──────────────────────────────────────
function Orbit() {
  const { camera, gl } = useThree();
  const ctrl = useRef<{ update: () => void; dispose: () => void } | null>(null);

  useEffect(() => {
    let c: { enableZoom: boolean; enablePan: boolean; rotateSpeed: number; enableDamping: boolean; dampingFactor: number; update: () => void; dispose: () => void };
    import('three/addons/controls/OrbitControls.js').then(({ OrbitControls }) => {
      c = new OrbitControls(camera, gl.domElement) as typeof c;
      c.enableZoom = false;
      c.enablePan = false;
      c.rotateSpeed = 0.35;
      c.enableDamping = true;
      c.dampingFactor = 0.06;
      ctrl.current = c;
    });
    return () => { if (ctrl.current) ctrl.current.dispose(); };
  }, [camera, gl]);

  useFrame(() => { ctrl.current?.update(); });
  return null;
}

// ─── Loading Spinner ───────────────────────────────────────────────────────
function LoadingGlobe({ dark }: { dark: boolean }) {
  return (
    <div className="absolute inset-0 flex items-center justify-center">
      <div className="text-center">
        <div className={`w-10 h-10 border-2 rounded-full animate-spin mx-auto mb-3 ${dark ? 'border-teal-900 border-t-teal-400' : 'border-teal-200 border-t-teal-500'}`} />
        <p className={`text-xs ${dark ? 'text-white/30' : 'text-gray-400'}`}>Loading globe...</p>
      </div>
    </div>
  );
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
  const grid = useEarthGrid();

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

  return (
    <div className="relative w-full h-full" style={{ minHeight: 480 }}>
      {!grid && <LoadingGlobe dark={dark} />}
      {grid && (
        <Canvas
          camera={{ position: [0, 0.3, 4.8], fov: 45 }}
          style={{ background: 'transparent' }}
          gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
          dpr={[1, 2]}
        >
          <GlobeScene
            grid={grid}
            dataPoints={dataPoints}
            dark={dark}
            onHover={handleHover}
            hoveredCountry={hovered?.country || null}
          />
          <Orbit />
        </Canvas>
      )}

      {/* Tooltip */}
      {hovered && (
        <div
          className={`absolute top-4 left-4 rounded-xl px-4 py-3 shadow-2xl border backdrop-blur-md text-xs z-10 ${
            dark ? 'bg-black/85 border-white/10 text-white' : 'bg-white/95 border-gray-200 text-gray-900'
          }`}
          style={{ minWidth: 180, pointerEvents: 'none' }}
        >
          <div className="font-semibold text-sm mb-1.5">{hovered.country}</div>
          <div className={`text-[10px] mb-2 ${dark ? 'text-white/40' : 'text-gray-400'}`}>
            {hovered.totalCount} event{hovered.totalCount !== 1 ? 's' : ''}
          </div>
          <div className="space-y-1.5">
            {Object.entries(hovered.sizes)
              .sort(([, a], [, b]) => b - a)
              .map(([size, pct]) => (
                <div key={size} className="flex items-center gap-2">
                  <span className="font-medium w-7">{size}</span>
                  <div className={`flex-1 h-1 rounded-full overflow-hidden ${dark ? 'bg-white/10' : 'bg-gray-200'}`}>
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${Math.round(pct * 100)}%`, backgroundColor: SIZE_COLORS[size] || '#64748b' }}
                    />
                  </div>
                  <span className={`w-8 text-right tabular-nums ${dark ? 'text-white/50' : 'text-gray-500'}`}>
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

      {/* Instruction */}
      <div className={`absolute bottom-2 right-3 text-[9px] ${dark ? 'text-white/15' : 'text-gray-300'}`}>
        Drag to rotate
      </div>
    </div>
  );
}
