'use client';

import { useRef, useMemo, useState, useCallback, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

const GLOBE_R = 2;

// ─── Country coordinates (lat, lon) — comprehensive global coverage ─────────
const CC: Record<string, [number, number]> = {
  // Europe
  'Netherlands': [52.3, 4.9], 'United Kingdom': [54.0, -2.0],
  'Germany': [51.2, 10.4], 'France': [46.6, 2.2],
  'Spain': [40.5, -3.7], 'Italy': [41.9, 12.5],
  'Belgium': [50.8, 4.3], 'Switzerland': [46.8, 8.2],
  'Austria': [47.5, 14.6], 'Denmark': [56.3, 9.5],
  'Sweden': [60.1, 18.6], 'Norway': [60.5, 8.5],
  'Poland': [51.9, 19.1], 'Portugal': [39.4, -8.2],
  'Ireland': [53.1, -8.2], 'Finland': [61.9, 25.7],
  'Greece': [39.1, 21.8], 'Czech Republic': [49.8, 15.5],
  'Hungary': [47.2, 19.5], 'Romania': [45.9, 24.9],
  'Bulgaria': [42.7, 25.5], 'Croatia': [45.1, 15.2],
  'Slovakia': [48.7, 19.7], 'Slovenia': [46.2, 14.8],
  'Serbia': [44.0, 21.0], 'Lithuania': [55.2, 23.9],
  'Latvia': [56.9, 24.1], 'Estonia': [58.6, 25.0],
  'Luxembourg': [49.8, 6.1], 'Iceland': [65.0, -18.0],
  'Malta': [35.9, 14.4], 'Cyprus': [35.1, 33.4],
  'Albania': [41.2, 20.2], 'North Macedonia': [41.5, 21.7],
  'Bosnia and Herzegovina': [43.9, 17.7], 'Montenegro': [42.7, 19.4],
  'Moldova': [47.4, 28.4], 'Belarus': [53.7, 27.9],
  'Ukraine': [48.4, 31.2], 'Kosovo': [42.6, 20.9],
  // North America
  'United States': [39.8, -98.6], 'Canada': [56.1, -106.3],
  'Mexico': [23.6, -102.6],
  // Central America & Caribbean
  'Guatemala': [15.8, -90.2], 'Honduras': [15.2, -86.2],
  'El Salvador': [13.8, -88.9], 'Nicaragua': [12.9, -85.2],
  'Costa Rica': [10.0, -84.0], 'Panama': [8.5, -80.8],
  'Cuba': [21.5, -79.9], 'Jamaica': [18.1, -77.3],
  'Dominican Republic': [18.7, -70.2], 'Haiti': [19.1, -72.3],
  'Trinidad and Tobago': [10.4, -61.2], 'Puerto Rico': [18.2, -66.6],
  // South America
  'Brazil': [-14.2, -51.9], 'Argentina': [-38.4, -63.6],
  'Colombia': [4.6, -74.3], 'Chile': [-35.7, -71.5],
  'Peru': [-9.2, -75.0], 'Venezuela': [6.4, -66.6],
  'Ecuador': [-1.8, -78.2], 'Bolivia': [-16.3, -63.6],
  'Paraguay': [-23.4, -58.4], 'Uruguay': [-32.5, -55.8],
  // Middle East
  'Turkey': [39.0, 35.2], 'UAE': [23.4, 53.8],
  'Saudi Arabia': [23.9, 45.1], 'Israel': [31.0, 34.9],
  'Jordan': [30.6, 36.2], 'Lebanon': [33.9, 35.9],
  'Iraq': [33.2, 43.7], 'Iran': [32.4, 53.7],
  'Kuwait': [29.3, 47.5], 'Qatar': [25.4, 51.2],
  'Bahrain': [26.0, 50.6], 'Oman': [21.5, 55.9],
  'Yemen': [15.6, 48.5],
  // Central Asia
  'Kazakhstan': [48.0, 68.0], 'Uzbekistan': [41.4, 64.6],
  'Turkmenistan': [39.0, 59.6], 'Kyrgyzstan': [41.2, 74.8],
  'Tajikistan': [38.9, 71.3], 'Afghanistan': [33.9, 67.7],
  'Pakistan': [30.4, 69.3],
  // South Asia
  'India': [20.6, 79.0], 'Bangladesh': [23.7, 90.4],
  'Sri Lanka': [7.9, 80.8], 'Nepal': [28.4, 84.1],
  // East Asia
  'Japan': [36.2, 138.3], 'South Korea': [35.9, 128.0],
  'China': [35.9, 104.2], 'Taiwan': [23.7, 121.0],
  'Mongolia': [46.9, 103.8], 'Hong Kong': [22.3, 114.2],
  // Southeast Asia
  'Singapore': [1.4, 103.8], 'Indonesia': [-0.8, 113.9],
  'Thailand': [15.9, 100.9], 'Malaysia': [4.2, 101.9],
  'Vietnam': [14.1, 108.3], 'Philippines': [12.9, 121.8],
  'Myanmar': [19.8, 96.0], 'Cambodia': [12.6, 104.9],
  'Laos': [19.9, 102.5],
  // Oceania
  'Australia': [-25.3, 133.8], 'New Zealand': [-40.9, 174.9],
  'Papua New Guinea': [-6.3, 143.9], 'Fiji': [-17.7, 178.0],
  // Russia / Eurasia
  'Russia': [61.5, 105.3], 'Georgia': [42.3, 43.4],
  'Armenia': [40.1, 45.0], 'Azerbaijan': [40.1, 47.6],
  // Africa — North
  'Morocco': [31.8, -7.1], 'Algeria': [28.0, 1.7],
  'Tunisia': [34.0, 9.5], 'Libya': [26.3, 17.2],
  'Egypt': [26.8, 30.8], 'Sudan': [12.9, 30.2],
  // Africa — West
  'Nigeria': [9.1, 8.7], 'Ghana': [7.9, -1.0],
  'Senegal': [14.5, -14.5], 'Ivory Coast': [7.5, -5.5],
  'Mali': [17.6, -4.0], 'Burkina Faso': [12.4, -1.6],
  'Guinea': [9.9, -11.6], 'Niger': [17.6, 8.1],
  'Sierra Leone': [8.5, -11.8], 'Togo': [8.6, 1.2],
  'Benin': [9.3, 2.3], 'Liberia': [6.4, -9.4],
  'Mauritania': [21.0, -10.9], 'Gambia': [13.4, -16.6],
  'Cape Verde': [16.0, -24.0], 'Guinea-Bissau': [12.0, -15.2],
  // Africa — East
  'Kenya': [-0.02, 37.9], 'Ethiopia': [9.1, 40.5],
  'Tanzania': [-6.4, 34.9], 'Uganda': [1.4, 32.3],
  'Rwanda': [-1.9, 29.9], 'Somalia': [5.2, 46.2],
  'Eritrea': [15.2, 39.8], 'Djibouti': [11.6, 43.2],
  'Madagascar': [-18.8, 46.9], 'Mauritius': [-20.3, 57.6],
  // Africa — Central
  'Democratic Republic of the Congo': [-4.0, 21.8],
  'Republic of the Congo': [-0.2, 15.8],
  'Cameroon': [7.4, 12.4], 'Gabon': [-0.8, 11.6],
  'Central African Republic': [6.6, 20.9], 'Chad': [15.5, 18.7],
  'Equatorial Guinea': [1.7, 10.3],
  // Africa — Southern
  'South Africa': [-30.6, 22.9], 'Namibia': [-22.6, 17.1],
  'Botswana': [-22.3, 24.7], 'Zimbabwe': [-19.0, 29.2],
  'Mozambique': [-18.7, 35.5], 'Zambia': [-13.1, 27.8],
  'Malawi': [-13.3, 34.3], 'Angola': [-11.2, 17.9],
  'Lesotho': [-29.6, 28.2], 'Eswatini': [-26.5, 31.5],
};

// ─── Major city coordinates for zoom detail ────────────────────────────────
const CITY_COORDS: Record<string, [number, number]> = {
  'Amsterdam': [52.37, 4.90], 'Rotterdam': [51.92, 4.48], 'The Hague': [52.08, 4.30],
  'Utrecht': [52.09, 5.11], 'Eindhoven': [51.44, 5.47], 'Zaandam': [52.44, 4.83],
  'Groningen': [53.22, 6.57], 'Tilburg': [51.56, 5.09], 'Almere': [52.35, 5.26],
  'Breda': [51.59, 4.78], 'Nijmegen': [51.84, 5.87], 'Haarlem': [52.38, 4.64],
  'Arnhem': [51.98, 5.91], 'Maastricht': [50.85, 5.69], 'Leiden': [52.16, 4.49],
  'Delft': [52.01, 4.36], 'Dordrecht': [51.81, 4.67], 'Amersfoort': [52.16, 5.39],
  'London': [51.51, -0.13], 'Manchester': [53.48, -2.24], 'Birmingham': [52.49, -1.89],
  'Edinburgh': [55.95, -3.19], 'Leeds': [53.80, -1.55], 'Glasgow': [55.86, -4.25],
  'Paris': [48.86, 2.35], 'Lyon': [45.76, 4.84], 'Marseille': [43.30, 5.37],
  'Toulouse': [43.60, 1.44], 'Nice': [43.71, 7.26], 'Bordeaux': [44.84, -0.58],
  'Berlin': [52.52, 13.41], 'Munich': [48.14, 11.58], 'Hamburg': [53.55, 9.99],
  'Frankfurt': [50.11, 8.68], 'Cologne': [50.94, 6.96], 'Stuttgart': [48.78, 9.18],
  'Düsseldorf': [51.23, 6.78],
  'Madrid': [40.42, -3.70], 'Barcelona': [41.39, 2.17], 'Valencia': [39.47, -0.38],
  'Seville': [37.39, -5.98], 'Bilbao': [43.26, -2.93],
  'Milan': [45.46, 9.19], 'Rome': [41.90, 12.50], 'Florence': [43.77, 11.25],
  'Naples': [40.85, 14.27], 'Turin': [45.07, 7.69], 'Venice': [45.44, 12.32],
  'Brussels': [50.85, 4.35], 'Antwerp': [51.22, 4.40],
  'Zurich': [47.38, 8.54], 'Geneva': [46.20, 6.14], 'Basel': [47.56, 7.59],
  'Vienna': [48.21, 16.37], 'Salzburg': [47.80, 13.04],
  'Copenhagen': [55.68, 12.57], 'Stockholm': [59.33, 18.07],
  'Oslo': [59.91, 10.75], 'Helsinki': [60.17, 24.94],
  'Warsaw': [52.23, 21.01], 'Krakow': [50.06, 19.95],
  'Lisbon': [38.72, -9.14], 'Porto': [41.16, -8.63],
  'Dublin': [53.35, -6.26], 'Athens': [37.98, 23.73],
  'Prague': [50.08, 14.44], 'Budapest': [47.50, 19.04],
  'Bucharest': [44.43, 26.10],
  'New York': [40.71, -74.01], 'Los Angeles': [34.05, -118.24],
  'Chicago': [41.88, -87.63], 'Houston': [29.76, -95.37],
  'San Francisco': [37.77, -122.42], 'Miami': [25.76, -80.19],
  'Seattle': [47.61, -122.33], 'Boston': [42.36, -71.06],
  'Dallas': [32.78, -96.80], 'Atlanta': [33.75, -84.39],
  'Denver': [39.74, -104.99], 'Austin': [30.27, -97.74],
  'Portland': [45.52, -122.68], 'Nashville': [36.16, -86.78],
  'Toronto': [43.65, -79.38], 'Vancouver': [49.28, -123.12],
  'Montreal': [45.50, -73.57], 'Calgary': [51.05, -114.07],
  'Mexico City': [19.43, -99.13], 'Guadalajara': [20.67, -103.35],
  'São Paulo': [-23.55, -46.63], 'Rio de Janeiro': [-22.91, -43.17],
  'Buenos Aires': [-34.60, -58.38], 'Bogotá': [4.71, -74.07],
  'Lima': [-12.05, -77.04], 'Santiago': [-33.45, -70.67],
  'Tokyo': [35.68, 139.69], 'Osaka': [34.69, 135.50], 'Kyoto': [35.01, 135.77],
  'Seoul': [37.57, 126.98], 'Busan': [35.18, 129.08],
  'Beijing': [39.90, 116.41], 'Shanghai': [31.23, 121.47],
  'Shenzhen': [22.54, 114.06], 'Guangzhou': [23.13, 113.26],
  'Hong Kong': [22.32, 114.17],
  'Mumbai': [19.08, 72.88], 'Delhi': [28.61, 77.23], 'Bangalore': [12.97, 77.59],
  'Singapore': [1.35, 103.82],
  'Bangkok': [13.76, 100.50], 'Ho Chi Minh City': [10.82, 106.63],
  'Kuala Lumpur': [3.14, 101.69], 'Jakarta': [-6.21, 106.85],
  'Manila': [14.60, 120.98],
  'Sydney': [-33.87, 151.21], 'Melbourne': [-37.81, 144.96],
  'Auckland': [-36.85, 174.76], 'Wellington': [-41.29, 174.78],
  'Dubai': [25.20, 55.27], 'Abu Dhabi': [24.45, 54.65],
  'Istanbul': [41.01, 28.98], 'Ankara': [39.93, 32.85],
  'Tel Aviv': [32.09, 34.78], 'Riyadh': [24.71, 46.67],
  'Doha': [25.29, 51.53], 'Muscat': [23.59, 58.54],
  'Moscow': [55.76, 37.62], 'Saint Petersburg': [59.93, 30.32],
  'Nairobi': [-1.29, 36.82], 'Lagos': [6.52, 3.38],
  'Cairo': [30.04, 31.24], 'Casablanca': [33.57, -7.59],
  'Cape Town': [-33.93, 18.42], 'Johannesburg': [-26.20, 28.05],
  'Accra': [5.56, -0.19], 'Addis Ababa': [9.02, 38.75],
  'Dar es Salaam': [-6.79, 39.28], 'Kampala': [0.35, 32.58],
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

// ─── Earth grid from blue marble image ─────────────────────────────────────
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

// ─── Dot sprite (smooth gaussian-like falloff) ─────────────────────────────
function createDotSprite(size = 128): THREE.Texture {
  const c = document.createElement('canvas');
  c.width = size; c.height = size;
  const ctx = c.getContext('2d')!;
  const h = size / 2;
  const g = ctx.createRadialGradient(h, h, 0, h, h, h);
  g.addColorStop(0, 'rgba(255,255,255,1)');
  g.addColorStop(0.15, 'rgba(255,255,255,0.85)');
  g.addColorStop(0.35, 'rgba(255,255,255,0.5)');
  g.addColorStop(0.55, 'rgba(255,255,255,0.2)');
  g.addColorStop(0.75, 'rgba(255,255,255,0.05)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(c);
  tex.needsUpdate = true;
  return tex;
}

// ─── Earth dots ────────────────────────────────────────────────────────────
function EarthDots({ earth, dark }: { earth: EarthGrid; dark: boolean }) {
  const dotTex = useMemo(() => createDotSprite(), []);

  const geom = useMemo(() => {
    const pos: number[] = [];
    const col: number[] = [];
    const { land, coast, w: W, h: H } = earth;

    const landBase  = dark ? new THREE.Color('#22d3ee') : new THREE.Color('#7dd3fc');
    const landBright = dark ? new THREE.Color('#67e8f9') : new THREE.Color('#a5f3fc');
    const coastCol  = dark ? new THREE.Color('#a5f3fc') : new THREE.Color('#e0f2fe');

    const N = 160000;
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
        const b = 0.7 + Math.random() * 0.3;
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
        size={0.024}
        map={dotTex}
        vertexColors
        transparent
        opacity={dark ? 1.0 : 0.9}
        depthWrite={false}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

// ─── Country border lines from TopoJSON ────────────────────────────────────
interface TopoGeom { type: string; arcs: number[][] | number[][][] }

function useBorderGeometry(): THREE.BufferGeometry | null {
  const [geom, setGeom] = useState<THREE.BufferGeometry | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json');
        const topo = await res.json();
        if (cancelled) return;

        const topoArcs: number[][][] = topo.arcs;
        const { scale, translate } = topo.transform;

        const decodeArc = (arcIdx: number): [number, number][] => {
          const isNeg = arcIdx < 0;
          const idx = isNeg ? ~arcIdx : arcIdx;
          const arc = topoArcs[idx];
          if (!arc) return [];
          const coords: [number, number][] = [];
          let x = 0, y = 0;
          for (const pt of arc) {
            x += pt[0]; y += pt[1];
            coords.push([
              x * scale[0] + translate[0],
              y * scale[1] + translate[1],
            ]);
          }
          if (isNeg) coords.reverse();
          return coords;
        };

        const positions: number[] = [];

        const addRing = (ring: number[]) => {
          const coords: [number, number][] = [];
          for (const arcIdx of ring) {
            coords.push(...decodeArc(arcIdx));
          }
          for (let i = 0; i < coords.length - 1; i++) {
            const [lon1, lat1] = coords[i];
            const [lon2, lat2] = coords[i + 1];
            positions.push(...latLonToVec3(lat1, lon1, GLOBE_R + 0.004));
            positions.push(...latLonToVec3(lat2, lon2, GLOBE_R + 0.004));
          }
        };

        const processGeometry = (g: TopoGeom) => {
          if (g.type === 'Polygon') {
            // arcs: [[arcIdx, arcIdx, ...], ...rings]
            for (const ring of g.arcs as number[][]) {
              addRing(ring);
            }
          } else if (g.type === 'MultiPolygon') {
            // arcs: [[[arcIdx, ...], ...rings], ...polygons]
            for (const polygon of g.arcs as number[][][]) {
              for (const ring of polygon) {
                addRing(ring);
              }
            }
          }
        };

        const countries = topo.objects?.countries;
        if (countries?.geometries) {
          for (const g of countries.geometries) {
            processGeometry(g as TopoGeom);
          }
        }

        const bg = new THREE.BufferGeometry();
        bg.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
        if (!cancelled) setGeom(bg);
      } catch (e) {
        console.warn('Failed to load country borders:', e);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return geom;
}

function CountryBorders({ dark, zoomLevel }: { dark: boolean; zoomLevel: number }) {
  const geom = useBorderGeometry();
  const matRef = useRef<THREE.LineBasicMaterial>(null);

  // Always slightly visible, much stronger when zoomed in
  const opacity = 0.15 + Math.min(0.85, Math.max(0, zoomLevel * 1.2));

  useFrame(() => {
    if (matRef.current) {
      matRef.current.opacity += (opacity - matRef.current.opacity) * 0.12;
    }
  });

  if (!geom) return null;

  return (
    <lineSegments geometry={geom}>
      <lineBasicMaterial
        ref={matRef}
        color={dark ? '#a5f3fc' : '#64748b'}
        transparent
        opacity={0.15}
        depthWrite={false}
        linewidth={1}
      />
    </lineSegments>
  );
}

// ─── Atmosphere ────────────────────────────────────────────────────────────
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
      glowColor: { value: dark ? new THREE.Color('#06b6d4') : new THREE.Color('#38bdf8') },
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
      glowColor: { value: dark ? new THREE.Color('#0891b2') : new THREE.Color('#7dd3fc') },
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

// ─── Data types ────────────────────────────────────────────────────────────
interface CountryData {
  country: string;
  lat: number;
  lon: number;
  topSize: string;
  totalCount: number;
  sizes: Record<string, number>;
}

interface CityData {
  city: string;
  country: string;
  lat: number;
  lon: number;
  total: number;
  topSize: string;
  sizes: Record<string, number>;
}

// ─── Data point dots ───────────────────────────────────────────────────────
function DataDot({ data, dark, onHover, hovered, selected, onClick }: {
  data: CountryData; dark: boolean;
  onHover: (d: CountryData | null) => void; hovered: boolean;
  selected: boolean; onClick: (d: CountryData) => void;
}) {
  const dotRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const pos = useMemo(() => latLonToVec3(data.lat, data.lon, GLOBE_R + 0.01), [data.lat, data.lon]);

  useFrame((state) => {
    if (dotRef.current) {
      const target = selected ? 0.045 : hovered ? 0.04 : 0.022;
      const s = dotRef.current.scale.x;
      dotRef.current.scale.setScalar(s + (target - s) * 0.15);
    }
    if (ringRef.current) {
      const pulse = 1 + Math.sin(state.clock.elapsedTime * 3 + data.lat) * 0.3;
      const base = selected ? 0.08 : hovered ? 0.065 : 0.04;
      ringRef.current.scale.setScalar(base * pulse);
      const m = ringRef.current.material as THREE.MeshBasicMaterial;
      m.opacity = selected ? 0.7 : hovered ? 0.6 : 0.2;
    }
  });

  const dotColor = selected ? (dark ? '#22d3ee' : '#0d9488') : dark ? '#f0fdfa' : '#0f766e';
  const ringColor = dark ? '#22d3ee' : '#14b8a6';

  return (
    <group position={pos}>
      <mesh
        ref={dotRef}
        scale={0.022}
        onPointerEnter={(e) => { e.stopPropagation(); onHover(data); }}
        onPointerLeave={() => onHover(null)}
        onClick={(e) => { e.stopPropagation(); onClick(data); }}
      >
        <sphereGeometry args={[1, 12, 12]} />
        <meshBasicMaterial color={dotColor} />
      </mesh>
      <mesh ref={ringRef} scale={0.04}>
        <ringGeometry args={[0.6, 1, 32]} />
        <meshBasicMaterial color={ringColor} transparent opacity={0.2} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

function CityDot({ data, dark, onHover, hovered }: {
  data: CityData; dark: boolean;
  onHover: (d: CityData | null) => void; hovered: boolean;
}) {
  const dotRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const pos = useMemo(() => latLonToVec3(data.lat, data.lon, GLOBE_R + 0.015), [data.lat, data.lon]);

  useFrame((state) => {
    if (dotRef.current) {
      const target = hovered ? 0.03 : 0.018;
      const s = dotRef.current.scale.x;
      dotRef.current.scale.setScalar(s + (target - s) * 0.15);
    }
    if (ringRef.current) {
      const pulse = 1 + Math.sin(state.clock.elapsedTime * 4 + data.lat * 10) * 0.25;
      ringRef.current.scale.setScalar((hovered ? 0.05 : 0.03) * pulse);
      const m = ringRef.current.material as THREE.MeshBasicMaterial;
      m.opacity = hovered ? 0.5 : 0.2;
    }
  });

  const dotColor = dark ? '#fbbf24' : '#d97706';
  const ringColor = dark ? '#fde68a' : '#f59e0b';

  return (
    <group position={pos}>
      <mesh
        ref={dotRef}
        scale={0.018}
        onPointerEnter={(e) => { e.stopPropagation(); onHover(data); }}
        onPointerLeave={() => onHover(null)}
      >
        <sphereGeometry args={[1, 12, 12]} />
        <meshBasicMaterial color={dotColor} />
      </mesh>
      <mesh ref={ringRef} scale={0.03}>
        <ringGeometry args={[0.6, 1, 32]} />
        <meshBasicMaterial color={ringColor} transparent opacity={0.2} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

// ─── Globe Scene ───────────────────────────────────────────────────────────
type OrbitCtrl = {
  enableZoom: boolean; enablePan: boolean; rotateSpeed: number;
  enableDamping: boolean; dampingFactor: number;
  minDistance: number; maxDistance: number;
  target: THREE.Vector3;
  update: () => void; dispose: () => void;
};

function GlobeScene({ earth, dataPoints, cityPoints, dark,
  onHoverCountry, onHoverCity, hoveredCountry, hoveredCity,
  selectedCountry, onSelectCountry, zoomLevel, onZoomChange,
}: {
  earth: EarthGrid; dataPoints: CountryData[]; cityPoints: CityData[];
  dark: boolean;
  onHoverCountry: (d: CountryData | null) => void;
  onHoverCity: (d: CityData | null) => void;
  hoveredCountry: string | null;
  hoveredCity: string | null;
  selectedCountry: string | null;
  onSelectCountry: (country: string | null) => void;
  zoomLevel: number;
  onZoomChange: (z: number) => void;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const { gl, camera } = useThree();
  const dragging = useRef(false);
  const dragTimer = useRef<ReturnType<typeof setTimeout>>();
  const ctrlRef = useRef<OrbitCtrl | null>(null);

  // Camera animation: store start + end so we can properly interpolate
  const animRef = useRef<{ start: THREE.Vector3; end: THREE.Vector3; progress: number } | null>(null);

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

  useEffect(() => {
    import('three/addons/controls/OrbitControls.js').then(({ OrbitControls }) => {
      const c = new OrbitControls(camera, gl.domElement);
      c.enableZoom = true;
      c.enablePan = false;
      c.rotateSpeed = 0.3;
      c.enableDamping = true;
      c.dampingFactor = 0.05;
      c.minDistance = 3.5;
      c.maxDistance = 12;
      ctrlRef.current = c as unknown as OrbitCtrl;
    });
    return () => { ctrlRef.current?.dispose(); };
  }, [camera, gl]);

  const handleCountryClick = useCallback((d: CountryData) => {
    if (selectedCountry === d.country) {
      onSelectCountry(null);
      animRef.current = {
        start: camera.position.clone(),
        end: new THREE.Vector3(0, 0.2, 8.5),
        progress: 0,
      };
      return;
    }

    onSelectCountry(d.country);

    // Get world position of the point, accounting for current globe rotation
    const localPos = new THREE.Vector3(...latLonToVec3(d.lat, d.lon, GLOBE_R));
    if (groupRef.current) {
      groupRef.current.updateMatrixWorld();
      localPos.applyMatrix4(groupRef.current.matrixWorld);
    }
    const dir = localPos.clone().normalize();
    const targetCamPos = dir.clone().multiplyScalar(4.0);
    targetCamPos.y += 0.1;

    animRef.current = {
      start: camera.position.clone(),
      end: targetCamPos,
      progress: 0,
    };
  }, [selectedCountry, onSelectCountry, camera]);

  useFrame((_s, delta) => {
    ctrlRef.current?.update();

    // Smooth camera animation: interpolate from start to end
    if (animRef.current && animRef.current.progress < 1) {
      animRef.current.progress = Math.min(1, animRef.current.progress + delta * 2.0);
      const t = 1 - Math.pow(1 - animRef.current.progress, 3); // ease-out cubic
      const { start, end } = animRef.current;
      camera.position.set(
        start.x + (end.x - start.x) * t,
        start.y + (end.y - start.y) * t,
        start.z + (end.z - start.z) * t,
      );
      camera.lookAt(0, 0, 0);
      if (animRef.current.progress >= 1) animRef.current = null;
    }

    const dist = camera.position.length();
    const maxDist = 12;
    const minDist = 3.5;
    const z = 1 - (dist - minDist) / (maxDist - minDist);
    onZoomChange(Math.max(0, Math.min(1, z)));

    if (groupRef.current && !dragging.current && !hoveredCountry && !hoveredCity && !selectedCountry) {
      groupRef.current.rotation.y += delta * 0.04;
    }
  });

  // Only show city dots for the selected country
  const visibleCities = selectedCountry
    ? cityPoints.filter((c) => c.country === selectedCountry)
    : [];

  return (
    <group ref={groupRef} rotation={[0.15, -0.6, 0.05]}>
      <mesh>
        <sphereGeometry args={[GLOBE_R - 0.005, 64, 64]} />
        <meshBasicMaterial color={dark ? '#020617' : '#1e1b4b'} />
      </mesh>
      <EarthDots earth={earth} dark={dark} />
      <CountryBorders dark={dark} zoomLevel={zoomLevel} />
      <InnerGlow dark={dark} />
      <GlobeAtmosphere dark={dark} />
      {dataPoints.map((d) => (
        <DataDot
          key={d.country}
          data={d}
          dark={dark}
          onHover={onHoverCountry}
          hovered={hoveredCountry === d.country}
          selected={selectedCountry === d.country}
          onClick={handleCountryClick}
        />
      ))}
      {visibleCities.map((d) => (
        <CityDot
          key={`${d.country}-${d.city}`}
          data={d}
          dark={dark}
          onHover={onHoverCity}
          hovered={hoveredCity === `${d.country}-${d.city}`}
        />
      ))}
    </group>
  );
}

// ─── Size bar colors ───────────────────────────────────────────────────────
const SIZE_COLORS: Record<string, string> = {
  'XS': '#cbd5e1', 'S': '#94a3b8', 'M': '#64748b',
  'L': '#475569', 'XL': '#334155', 'XXL': '#1e293b',
};

// ─── Main Component ────────────────────────────────────────────────────────
export default function RegionalSizeGlobe({
  by_country,
  raw_counts,
  top_size_by_country,
  by_city,
  dark = false,
}: {
  by_country: Record<string, Record<string, number>>;
  raw_counts?: Record<string, Record<string, number>>;
  top_size_by_country?: Record<string, string>;
  by_city?: Record<string, Record<string, { sizes: Record<string, number>; raw_counts: Record<string, number>; total: number; top_size: string }>>;
  dark?: boolean;
}) {
  const [hoveredCountry, setHoveredCountry] = useState<CountryData | null>(null);
  const [hoveredCity, setHoveredCity] = useState<CityData | null>(null);
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);
  const [zoomLevel, setZoomLevel] = useState(0);
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

  const cityPoints: CityData[] = useMemo(() => {
    // If backend returned city-level data, use it
    if (by_city && Object.keys(by_city).length > 0) {
      const pts: CityData[] = [];
      for (const [country, cities] of Object.entries(by_city)) {
        const countryCoord = CC[country];
        if (!countryCoord) continue;
        for (const [cityName, data] of Object.entries(cities)) {
          const coord = CITY_COORDS[cityName];
          if (!coord) {
            let hash = 0;
            for (let i = 0; i < cityName.length; i++) hash = ((hash << 5) - hash + cityName.charCodeAt(i)) | 0;
            const jLat = countryCoord[0] + ((hash % 100) / 100 - 0.5) * 2.5;
            const jLon = countryCoord[1] + (((hash >> 8) % 100) / 100 - 0.5) * 2.5;
            pts.push({ city: cityName, country, lat: jLat, lon: jLon,
              total: data.total, topSize: data.top_size, sizes: data.sizes });
          } else {
            pts.push({ city: cityName, country, lat: coord[0], lon: coord[1],
              total: data.total, topSize: data.top_size, sizes: data.sizes });
          }
        }
      }
      return pts;
    }

    // Fallback: generate city markers from CITY_COORDS for countries that have data
    const CITY_TO_COUNTRY: Record<string, string> = {};
    const countryCities: Record<string, string[]> = {
      'Netherlands': ['Amsterdam', 'Rotterdam', 'The Hague', 'Utrecht', 'Eindhoven', 'Zaandam', 'Groningen'],
      'United Kingdom': ['London', 'Manchester', 'Birmingham', 'Edinburgh', 'Leeds', 'Glasgow'],
      'France': ['Paris', 'Lyon', 'Marseille', 'Nice', 'Bordeaux', 'Toulouse'],
      'Germany': ['Berlin', 'Munich', 'Hamburg', 'Frankfurt', 'Cologne', 'Stuttgart'],
      'Spain': ['Madrid', 'Barcelona', 'Valencia', 'Seville', 'Bilbao'],
      'Italy': ['Milan', 'Rome', 'Florence', 'Naples', 'Turin', 'Venice'],
      'Belgium': ['Brussels', 'Antwerp'],
      'United States': ['New York', 'Los Angeles', 'Chicago', 'San Francisco', 'Miami', 'Seattle', 'Boston'],
      'Canada': ['Toronto', 'Vancouver', 'Montreal'],
      'Japan': ['Tokyo', 'Osaka', 'Kyoto'],
      'South Korea': ['Seoul', 'Busan'],
      'China': ['Beijing', 'Shanghai', 'Shenzhen', 'Guangzhou'],
      'India': ['Mumbai', 'Delhi', 'Bangalore'],
      'Australia': ['Sydney', 'Melbourne'],
      'Brazil': ['São Paulo', 'Rio de Janeiro'],
      'UAE': ['Dubai', 'Abu Dhabi'],
      'Turkey': ['Istanbul', 'Ankara'],
      'South Africa': ['Cape Town', 'Johannesburg'],
    };
    for (const [country, cities] of Object.entries(countryCities)) {
      for (const city of cities) CITY_TO_COUNTRY[city] = country;
    }

    const pts: CityData[] = [];
    for (const dp of dataPoints) {
      const cities = countryCities[dp.country];
      if (!cities) continue;
      for (const cityName of cities) {
        const coord = CITY_COORDS[cityName];
        if (!coord) continue;
        pts.push({
          city: cityName, country: dp.country,
          lat: coord[0], lon: coord[1],
          total: 0, topSize: dp.topSize, sizes: dp.sizes,
        });
      }
    }
    return pts;
  }, [by_city, dataPoints]);

  const handleHoverCountry = useCallback((d: CountryData | null) => { setHoveredCountry(d); setHoveredCity(null); }, []);
  const handleHoverCity = useCallback((d: CityData | null) => { setHoveredCity(d); setHoveredCountry(null); }, []);
  const handleSelectCountry = useCallback((country: string | null) => {
    setSelectedCountry(country);
    setHoveredCity(null);
  }, []);

  if (!earth) {
    return (
      <div className="absolute inset-0 flex items-center justify-center">
        <div className={`w-8 h-8 border-2 rounded-full animate-spin ${dark ? 'border-cyan-900 border-t-cyan-400' : 'border-teal-200 border-t-teal-500'}`} />
      </div>
    );
  }

  const tooltipData = hoveredCity
    ? { label: hoveredCity.city, sub: `${hoveredCity.country} — ${hoveredCity.total} event${hoveredCity.total !== 1 ? 's' : ''}`, sizes: hoveredCity.sizes, topSize: hoveredCity.topSize }
    : hoveredCountry
    ? { label: hoveredCountry.country, sub: `${hoveredCountry.totalCount} event${hoveredCountry.totalCount !== 1 ? 's' : ''}`, sizes: hoveredCountry.sizes, topSize: hoveredCountry.topSize }
    : null;

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
          cityPoints={cityPoints}
          dark={dark}
          onHoverCountry={handleHoverCountry}
          onHoverCity={handleHoverCity}
          hoveredCountry={hoveredCountry?.country || null}
          hoveredCity={hoveredCity ? `${hoveredCity.country}-${hoveredCity.city}` : null}
          selectedCountry={selectedCountry}
          onSelectCountry={handleSelectCountry}
          zoomLevel={zoomLevel}
          onZoomChange={setZoomLevel}
        />
      </Canvas>

      {tooltipData && (
        <div
          className={`absolute top-14 right-4 rounded-xl px-4 py-3 shadow-2xl border backdrop-blur-xl text-xs z-10 ${
            dark ? 'bg-black/80 border-white/10 text-white' : 'bg-white/90 border-gray-200 text-gray-900'
          }`}
          style={{ minWidth: 170, pointerEvents: 'none' }}
        >
          <div className="font-semibold text-sm mb-0.5">{tooltipData.label}</div>
          <div className={`text-[10px] mb-2 ${dark ? 'text-white/35' : 'text-gray-400'}`}>
            {tooltipData.sub}
          </div>
          <div className="space-y-1.5">
            {Object.entries(tooltipData.sizes)
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
            Top size: <strong>{tooltipData.topSize}</strong>
          </div>
        </div>
      )}

      {selectedCountry && (
        <button
          onClick={() => handleSelectCountry(null)}
          className={`absolute top-3 left-3 text-[10px] px-3 py-1.5 rounded-lg backdrop-blur-md cursor-pointer transition-colors ${
            dark
              ? 'bg-white/10 hover:bg-white/15 text-cyan-300 border border-white/10'
              : 'bg-black/5 hover:bg-black/10 text-teal-700 border border-black/10'
          }`}
        >
          ← Back to globe
        </button>
      )}

      <div className={`absolute bottom-2 right-3 text-[9px] ${dark ? 'text-white/15' : 'text-gray-300'}`}>
        {selectedCountry ? 'Click country dot again to zoom out' : 'Click a country dot to zoom in  ·  Drag to rotate'}
      </div>
    </div>
  );
}
