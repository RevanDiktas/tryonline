'use client';

import { useRef, useMemo, useState, useCallback } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';

const COUNTRY_COORDS: Record<string, [number, number]> = {
  'Netherlands': [52.3, 4.9],
  'United States': [39.8, -98.6],
  'United Kingdom': [54.0, -2.0],
  'Germany': [51.2, 10.4],
  'France': [46.6, 2.2],
  'Spain': [40.5, -3.7],
  'Italy': [41.9, 12.5],
  'Belgium': [50.8, 4.3],
  'Switzerland': [46.8, 8.2],
  'Austria': [47.5, 14.6],
  'Denmark': [56.3, 9.5],
  'Sweden': [60.1, 18.6],
  'Norway': [60.5, 8.5],
  'Poland': [51.9, 19.1],
  'Portugal': [39.4, -8.2],
  'Ireland': [53.1, -8.2],
  'Finland': [61.9, 25.7],
  'Greece': [39.1, 21.8],
  'Canada': [56.1, -106.3],
  'Australia': [-25.3, 133.8],
  'Japan': [36.2, 138.3],
  'South Korea': [35.9, 128.0],
  'China': [35.9, 104.2],
  'India': [20.6, 79.0],
  'Brazil': [-14.2, -51.9],
  'Mexico': [23.6, -102.6],
  'Russia': [61.5, 105.3],
  'Turkey': [39.0, 35.2],
  'South Africa': [-30.6, 22.9],
  'UAE': [23.4, 53.8],
  'Saudi Arabia': [23.9, 45.1],
  'Singapore': [1.4, 103.8],
  'New Zealand': [-40.9, 174.9],
  'Argentina': [-38.4, -63.6],
  'Colombia': [4.6, -74.3],
  'Czech Republic': [49.8, 15.5],
  'Hungary': [47.2, 19.5],
  'Romania': [45.9, 24.9],
  'Thailand': [15.9, 100.9],
  'Indonesia': [-0.8, 113.9],
  'Vietnam': [14.1, 108.3],
  'Philippines': [12.9, 121.8],
  'Malaysia': [4.2, 101.9],
  'Unknown': [0, 0],
};

const SIZE_COLORS: Record<string, string> = {
  'XS': '#cbd5e1',
  'S': '#94a3b8',
  'M': '#64748b',
  'L': '#475569',
  'XL': '#334155',
  'XXL': '#1e293b',
};

function latLonToVec3(lat: number, lon: number, radius: number): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -(radius * Math.sin(phi) * Math.cos(theta)),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta),
  );
}

interface CountryData {
  country: string;
  lat: number;
  lon: number;
  topSize: string;
  totalCount: number;
  sizes: Record<string, number>;
}

interface GlobePoint {
  position: THREE.Vector3;
  data: CountryData;
}

function GlobeMesh({ dark }: { dark: boolean }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const glowRef = useRef<THREE.Mesh>(null);

  const globeColor = dark ? '#0a0a0f' : '#e8ecf0';
  const wireColor = dark ? 'rgba(100,200,255,0.08)' : 'rgba(0,0,0,0.06)';

  return (
    <group>
      <mesh ref={meshRef}>
        <sphereGeometry args={[2, 64, 64]} />
        <meshStandardMaterial
          color={globeColor}
          roughness={0.9}
          metalness={0.1}
        />
      </mesh>
      <mesh ref={glowRef}>
        <sphereGeometry args={[2.003, 64, 64]} />
        <meshBasicMaterial
          color={wireColor}
          wireframe
          transparent
          opacity={dark ? 0.15 : 0.2}
        />
      </mesh>
    </group>
  );
}

function CountryDot({ point, dark, onHover, isHovered }: {
  point: GlobePoint;
  dark: boolean;
  onHover: (data: CountryData | null) => void;
  isHovered: boolean;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const scale = Math.max(0.04, Math.min(0.12, point.data.totalCount * 0.015));
  const sizeColor = SIZE_COLORS[point.data.topSize] || (dark ? '#64748b' : '#475569');

  useFrame(() => {
    if (meshRef.current) {
      const target = isHovered ? scale * 1.8 : scale;
      meshRef.current.scale.lerp(new THREE.Vector3(target, target, target), 0.1);
    }
  });

  return (
    <group position={point.position}>
      <mesh
        ref={meshRef}
        onPointerEnter={(e) => { e.stopPropagation(); onHover(point.data); }}
        onPointerLeave={() => onHover(null)}
      >
        <sphereGeometry args={[1, 16, 16]} />
        <meshStandardMaterial
          color={sizeColor}
          emissive={sizeColor}
          emissiveIntensity={isHovered ? 0.8 : 0.4}
          roughness={0.3}
        />
      </mesh>
      {/* Pulse ring */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[1.2, 1.5, 32]} />
        <meshBasicMaterial
          color={sizeColor}
          transparent
          opacity={isHovered ? 0.3 : 0.1}
          side={THREE.DoubleSide}
        />
      </mesh>
    </group>
  );
}

function GlobeScene({ points, dark, onHover, hoveredCountry }: {
  points: GlobePoint[];
  dark: boolean;
  onHover: (data: CountryData | null) => void;
  hoveredCountry: string | null;
}) {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((_state, delta) => {
    if (groupRef.current && !hoveredCountry) {
      groupRef.current.rotation.y += delta * 0.05;
    }
  });

  return (
    <group ref={groupRef}>
      <GlobeMesh dark={dark} />
      {points.map((p) => (
        <CountryDot
          key={p.data.country}
          point={p}
          dark={dark}
          onHover={onHover}
          isHovered={hoveredCountry === p.data.country}
        />
      ))}
    </group>
  );
}

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

  const points: GlobePoint[] = useMemo(() => {
    return Object.entries(by_country)
      .filter(([country]) => country !== 'Unknown')
      .map(([country, sizes]) => {
        const [lat, lon] = COUNTRY_COORDS[country] || [0, 0];
        const counts = raw_counts?.[country] || {};
        const totalCount = Object.values(counts).reduce((a, b) => a + b, 0);
        const topSize = top_size_by_country?.[country] || Object.entries(sizes).sort(([, a], [, b]) => b - a)[0]?.[0] || 'M';

        return {
          position: latLonToVec3(lat, lon, 2.05),
          data: { country, lat, lon, topSize, totalCount: totalCount || 1, sizes },
        };
      });
  }, [by_country, raw_counts, top_size_by_country]);

  const handleHover = useCallback((data: CountryData | null) => {
    setHovered(data);
  }, []);

  const bgColor = dark ? '#08080c' : '#f8fafc';

  return (
    <div className="relative w-full" style={{ height: 340 }}>
      <Canvas
        camera={{ position: [0, 0, 5.5], fov: 45 }}
        style={{ background: bgColor, borderRadius: 12 }}
        gl={{ antialias: true, alpha: true }}
      >
        <ambientLight intensity={dark ? 0.3 : 0.5} />
        <directionalLight position={[5, 3, 5]} intensity={dark ? 0.8 : 1} />
        <directionalLight position={[-5, -3, -5]} intensity={dark ? 0.2 : 0.3} />
        <GlobeScene
          points={points}
          dark={dark}
          onHover={handleHover}
          hoveredCountry={hovered?.country || null}
        />
        <OrbitControls
          enableZoom={true}
          enablePan={false}
          minDistance={3.5}
          maxDistance={8}
          rotateSpeed={0.5}
          zoomSpeed={0.5}
        />
      </Canvas>

      {/* Tooltip */}
      {hovered && (
        <div
          className={`absolute top-4 right-4 rounded-xl px-4 py-3 shadow-lg border backdrop-blur-sm text-xs z-10 ${
            dark
              ? 'bg-black/80 border-white/10 text-white'
              : 'bg-white/90 border-gray-200 text-gray-900'
          }`}
          style={{ minWidth: 160 }}
        >
          <div className="font-semibold text-sm mb-2">{hovered.country}</div>
          <div className={`text-[10px] mb-2 ${dark ? 'text-white/50' : 'text-gray-500'}`}>
            {hovered.totalCount} event{hovered.totalCount !== 1 ? 's' : ''}
          </div>
          <div className="space-y-1">
            {Object.entries(hovered.sizes)
              .sort(([, a], [, b]) => b - a)
              .map(([size, pct]) => (
                <div key={size} className="flex items-center gap-2">
                  <div
                    className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{ backgroundColor: SIZE_COLORS[size] || '#64748b' }}
                  />
                  <span className="font-medium w-8">{size}</span>
                  <div className={`flex-1 h-1.5 rounded-full ${dark ? 'bg-white/10' : 'bg-gray-200'}`}>
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${Math.round(pct * 100)}%`,
                        backgroundColor: SIZE_COLORS[size] || '#64748b',
                      }}
                    />
                  </div>
                  <span className={`w-8 text-right ${dark ? 'text-white/60' : 'text-gray-500'}`}>
                    {Math.round(pct * 100)}%
                  </span>
                </div>
              ))}
          </div>
          <div className={`mt-2 pt-2 border-t ${dark ? 'border-white/10' : 'border-gray-200'}`}>
            <span className={dark ? 'text-white/40' : 'text-gray-400'}>Top size: </span>
            <span className="font-semibold">{hovered.topSize}</span>
          </div>
        </div>
      )}

      {/* Size legend */}
      <div className={`absolute bottom-3 left-3 flex gap-2 flex-wrap text-[10px] ${dark ? 'text-white/50' : 'text-gray-500'}`}>
        {['XS', 'S', 'M', 'L', 'XL', 'XXL'].map((s) => (
          <div key={s} className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: SIZE_COLORS[s] }} />
            {s}
          </div>
        ))}
      </div>

      {/* Instruction text */}
      <div className={`absolute bottom-3 right-3 text-[10px] ${dark ? 'text-white/30' : 'text-gray-400'}`}>
        Drag to rotate &middot; Scroll to zoom
      </div>
    </div>
  );
}
