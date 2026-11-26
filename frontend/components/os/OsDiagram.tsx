'use client';

import { useEffect, useRef, useState } from 'react';

/* Consumer, brand, factory, and the operating system between them, as one running loop.
   Each card shows its own job: the shopper is scanned and measured, the long sleeve is tested at three
   sizes, the factory runs garments and grows the size run. Labelled signals travel through the Tryon OS
   hub in sequence: fit, demand, design, size run, stock, right size. Ink drawings, every moving part in
   cobalt. Wires draw in and cards rise when the diagram enters the screen. Still under reduced motion.
   The readouts are an illustration of one shopper and one garment, not live data. */

const INK = '#131519';
const MUTE = '#626A78';
const FAINT = 'rgba(19,21,25,.16)';
const RULE = 'rgba(19,21,25,.2)';
const BLUE = '#0040FF';
const MONO = 'var(--f-mono), ui-monospace, monospace';
const DISPLAY = 'var(--f-display), system-ui, sans-serif';
const LOOP = 6; // seconds for one full trip of the six signals

type Kind = 'consumer' | 'brand' | 'factory';
const NAMES: Record<Kind, [string, string]> = {
  consumer: ['Consumer', 'FIT AND BEHAVIOUR'],
  brand: ['Brand', 'DESIGN STRESS TESTED'],
  factory: ['Factory', 'MADE TO DEMAND'],
};
/** Opacity keyframes that show item i of n only during its own slot, with a short fade at each edge. */
function slot(i: number, n: number) {
  const a = i / n, b = (i + 1) / n, e = 0.02, f = (x: number) => Math.min(1, Math.max(0, x)).toFixed(3);
  if (i === 0) return { values: '1;1;0;0;1', keyTimes: `0;${f(b - e)};${f(b)};${f(1 - e)};1` };
  return { values: '0;0;1;1;0;0', keyTimes: `0;${f(a)};${f(a + e)};${f(b - e)};${f(b)};1` };
}
const ink = { fill: 'none', stroke: INK, strokeWidth: 1.8, strokeLinejoin: 'round' as const, strokeLinecap: 'round' as const };

/* ---------- card contents, in a 200 x 200 box ---------- */

const BODY = 'M64 152 C64 108 81 92 100 92 C119 92 136 108 136 152';
function Consumer({ m }: { m: boolean }) {
  const read = [['C', '102', 0.32], ['W', '88', 0.52], ['H', '99', 0.72]] as const;
  return (
    <g>
      {[0.84, 1.16].map((k, i) => (
        <g key={k} transform={`translate(100 120) scale(${k}) translate(-100 -120)`} opacity={m ? 0 : 0.5}>
          <circle cx="100" cy="64" r="14" fill="none" stroke={FAINT} strokeWidth="1.4" />
          <path d={BODY} fill="none" stroke={FAINT} strokeWidth="1.4" />
          {m && <animate attributeName="opacity" values="0;1;0" dur="4s" begin={`${i * 2}s`} repeatCount="indefinite" />}
        </g>
      ))}
      <circle cx="100" cy="64" r="14" {...ink} />
      <path d={BODY} {...ink} />
      <line x1="54" x2="146" y1="50" y2="50" stroke={BLUE} strokeWidth="2" strokeLinecap="round">
        {m && <animate attributeName="y1" values="46;154;46" dur="3s" repeatCount="indefinite" calcMode="spline" keyTimes="0;.5;1" keySplines=".45 0 .55 1;.45 0 .55 1" />}
        {m && <animate attributeName="y2" values="46;154;46" dur="3s" repeatCount="indefinite" calcMode="spline" keyTimes="0;.5;1" keySplines=".45 0 .55 1;.45 0 .55 1" />}
      </line>
      {read.map(([k, v, t], i) => (
        <text key={k} x={58 + i * 42} y="182" textAnchor="middle" style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: '.06em' }} fill={INK} opacity={m ? 0 : 1}>
          <tspan fill={MUTE}>{k} </tspan>{v}
          {m && <animate attributeName="opacity" values="0;0;1;1;0" keyTimes={`0;${t * 0.5};${t * 0.5 + 0.06};.92;1`} dur="6s" repeatCount="indefinite" />}
        </text>
      ))}
    </g>
  );
}

const SLEEVE = 'M-13 -30 L-30 -24 L-40 28 L-30 31 L-21 -4 L-21 34 L21 34 L21 -4 L30 31 L40 28 L30 -24 L13 -30 C9 -22 -9 -22 -13 -30 Z';
function Brand({ m }: { m: boolean }) {
  const sizes = [['S', 0.82, '71'], ['M', 1, '96'], ['L', 1.18, '84']] as const;
  return (
    <g>
      {sizes.map(([s, k], i) => (
        <path key={s} d={SLEEVE} transform={`translate(100 96) scale(${1.15 * k})`} fill="none" strokeWidth={1.8 / (1.15 * k)} strokeLinejoin="round"
          stroke={s === 'M' ? INK : FAINT}>
          {m && (() => { const base = s === 'M' ? INK : FAINT, k = slot(i, 3); return (
            <animate attributeName="stroke" values={k.values.split(';').map((v) => (v === '1' ? BLUE : base)).join(';')} keyTimes={k.keyTimes} dur="4.5s" repeatCount="indefinite" calcMode="discrete" />); })()}
        </path>
      ))}
      <circle cx="100" cy="80" r="8" fill={BLUE} opacity={m ? 0 : 0.2}>
        {m && <animate attributeName="r" values="6;24" dur="1.8s" repeatCount="indefinite" />}
        {m && <animate attributeName="opacity" values=".32;0" dur="1.8s" repeatCount="indefinite" />}
      </circle>
      {sizes.map(([s, , fit], i) => (
        <text key={s} x="100" y="182" textAnchor="middle" style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: '.08em' }} fill={INK} opacity={m ? 0 : s === 'M' ? 1 : 0}>
          <tspan fill={MUTE}>SIZE </tspan>{s}<tspan fill={MUTE}>  FIT </tspan><tspan fill={BLUE}>{fit}</tspan>
          {m && <animate attributeName="opacity" {...slot(i, 3)} dur="4.5s" repeatCount="indefinite" />}
        </text>
      ))}
    </g>
  );
}

const MILL = 'M-38 34 V-2 L-18 -14 V-2 L2 -14 V-2 L20 -14 V-32 H30 V34 Z';
const TEE = 'M-5 -5 L-2 -6 C-1 -4 1 -4 2 -6 L5 -5 L6 -1 L4 0 L4 6 L-4 6 L-4 0 L-6 -1 Z';
function Factory({ m }: { m: boolean }) {
  const run = [['S', 12], ['M', 41], ['L', 35], ['XL', 12]] as const;
  return (
    <g>
      <path d={MILL} transform="translate(100 66) scale(1.05)" {...ink} strokeWidth={1.7} />
      <line x1="40" x2="160" y1="118" y2="118" stroke={INK} strokeWidth="1.4" />
      {[0, 1, 2, 3].map((i) => (
        <path key={i} d={TEE} fill={BLUE} transform={`translate(${52 + i * 30} 110)`} opacity={m ? 0 : 1}>
          {m && <animateTransform attributeName="transform" type="translate" values="44 110;156 110" dur="3.2s" begin={`${i * 0.8}s`} repeatCount="indefinite" />}
          {m && <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.1;.88;1" dur="3.2s" begin={`${i * 0.8}s`} repeatCount="indefinite" />}
        </path>
      ))}
      {run.map(([s, v], i) => {
        const h = v * 0.9, x = 63 + i * 20;
        return (
          <g key={s}>
            <rect x={x} width="12" y={174 - h} height={h} fill={i === 1 ? BLUE : 'rgba(0,64,255,.35)'}>
              {m && <animate attributeName="height" values={`0;${h};${h};0`} keyTimes="0;.3;.9;1" dur="6s" begin={`${i * 0.15}s`} repeatCount="indefinite" calcMode="spline" keySplines=".22 1 .36 1;0 0 1 1;.4 0 1 1" />}
              {m && <animate attributeName="y" values={`174;${174 - h};${174 - h};174`} keyTimes="0;.3;.9;1" dur="6s" begin={`${i * 0.15}s`} repeatCount="indefinite" calcMode="spline" keySplines=".22 1 .36 1;0 0 1 1;.4 0 1 1" />}
            </rect>
            <text x={x + 6} y="190" textAnchor="middle" style={{ fontFamily: MONO, fontSize: 9, letterSpacing: '.04em' }} fill={MUTE}>{s}</text>
          </g>
        );
      })}
    </g>
  );
}

const CONTENT: Record<Kind, (p: { m: boolean }) => JSX.Element> = { consumer: Consumer, brand: Brand, factory: Factory };

/* ---------- the hub ---------- */

const STATUS = ['READING FIT', 'TESTING DESIGN', 'SIZING THE RUN', 'RESTOCKING'];
function Hub({ x, y, s, m }: { x: number; y: number; s: number; m: boolean }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      {m && [0, 1.2].map((b) => (
        <circle key={b} r="58" fill="none" stroke={BLUE} strokeWidth="1" opacity="0">
          <animate attributeName="r" values="58;118" dur="2.4s" begin={`${b}s`} repeatCount="indefinite" calcMode="spline" keyTimes="0;1" keySplines=".22 1 .36 1" />
          <animate attributeName="opacity" values=".45;0" dur="2.4s" begin={`${b}s`} repeatCount="indefinite" />
        </circle>
      ))}
      <g>
        <circle r="76" fill="none" stroke={BLUE} strokeWidth="1" strokeDasharray="2 9" opacity=".55" />
        {m && <animateTransform attributeName="transform" type="rotate" values="0;360" dur="30s" repeatCount="indefinite" />}
      </g>
      <circle r="58" fill="#fff" stroke={BLUE} strokeWidth="1.4" />
      <circle r="4" cy="-30" fill={BLUE}>
        {m && <animate attributeName="opacity" values="1;.25;1" dur="1.6s" repeatCount="indefinite" />}
      </circle>
      <text y="2" textAnchor="middle" style={{ fontFamily: MONO, fontSize: 14, letterSpacing: '.18em', fontWeight: 500 }} fill={BLUE}>TRYON OS</text>
      {STATUS.map((t, i) => (
        <text key={t} y="24" textAnchor="middle" style={{ fontFamily: MONO, fontSize: 8.5, letterSpacing: '.12em' }} fill={MUTE} opacity={m ? 0 : i === 0 ? 1 : 0}>
          {t}
          {m && <animate attributeName="opacity" {...slot(i, 4)} dur={`${LOOP}s`} repeatCount="indefinite" />}
        </text>
      ))}
    </g>
  );
}

/* ---------- signals ---------- */

function Signal({ path, label, slot, m }: { path: string; label: string; slot: number; m: boolean }) {
  if (!m) return null;
  const begin = `${slot}s`;
  return (
    <g opacity="0">
      <animateMotion path={path} dur={`${LOOP}s`} begin={begin} repeatCount="indefinite" keyPoints="0;1;1" keyTimes="0;.16;1" calcMode="linear" />
      <animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;.02;.14;.16;1" dur={`${LOOP}s`} begin={begin} repeatCount="indefinite" />
      <circle r="9" fill={BLUE} opacity=".14" />
      <circle r="4.5" fill={BLUE} />
      <text x="12" y="-8" style={{ fontFamily: MONO, fontSize: 10, letterSpacing: '.14em', fontWeight: 500 }} fill={BLUE}>{label}</text>
    </g>
  );
}

/* ---------- layouts ---------- */

type Node = { k: Kind; x: number; y: number; s: number; name: [number, number]; cap: [number, number] };
type Layout = { vb: [number, number]; nodes: Node[]; hub: { x: number; y: number; s: number };
  wires: Record<Kind, [string, string]>; nameSize: number; capSize: number };

const DESK: Layout = {
  vb: [1200, 720], nameSize: 26, capSize: 11.5,
  nodes: [
    { k: 'consumer', x: 100, y: 120, s: 1, name: [200, 60], cap: [200, 90] },
    { k: 'brand', x: 500, y: 120, s: 1, name: [600, 60], cap: [600, 90] },
    { k: 'factory', x: 900, y: 120, s: 1, name: [1000, 60], cap: [1000, 90] },
  ],
  hub: { x: 600, y: 560, s: 1 },
  wires: {
    consumer: ['M200 320 C200 450 380 560 524 560', 'M524 560 C380 560 200 450 200 320'],
    brand: ['M600 320 L600 484', 'M600 484 L600 320'],
    factory: ['M1000 320 C1000 450 820 560 676 560', 'M676 560 C820 560 1000 450 1000 320'],
  },
};

const PHONE: Layout = {
  vb: [390, 900], nameSize: 22, capSize: 9.5,
  nodes: [
    { k: 'consumer', x: 110, y: 74, s: 0.85, name: [195, 32], cap: [195, 56] },
    { k: 'brand', x: 14, y: 640, s: 0.8, name: [94, 828], cap: [94, 850] },
    { k: 'factory', x: 216, y: 640, s: 0.8, name: [296, 828], cap: [296, 850] },
  ],
  hub: { x: 195, y: 440, s: 0.8 },
  wires: {
    consumer: ['M195 244 L195 379', 'M195 379 L195 244'],
    brand: ['M94 640 C94 540 120 440 134 440', 'M134 440 C120 440 94 540 94 640'],
    factory: ['M296 640 C296 540 270 440 256 440', 'M256 440 C270 440 296 540 296 640'],
  },
};

function Diagram({ L, m }: { L: Layout; m: boolean }) {
  const [W, H] = L.vb;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Consumer, brand and factory connected by the Tryon operating system"
      style={{ display: 'block', overflow: 'visible', maxWidth: W, margin: '0 auto' }}>
      {(Object.keys(L.wires) as Kind[]).map((k, i) => (
        <g key={k}>
          <path d={L.wires[k][0]} fill="none" stroke={RULE} strokeWidth="1" className="osd-wire" pathLength={1} style={{ transitionDelay: `${300 + i * 120}ms` }} />
          <path d={L.wires[k][0]} fill="none" stroke={BLUE} strokeWidth="1.2" strokeDasharray="1.5 10" opacity=".45" strokeLinecap="round">
            {m && <animate attributeName="stroke-dashoffset" values="0;-23" dur="1.2s" repeatCount="indefinite" />}
          </path>
        </g>
      ))}
      {L.nodes.map((n, i) => {
        const C = CONTENT[n.k];
        return (
          <g key={n.k} className="osd-card" style={{ transitionDelay: `${i * 140}ms` }}>
            <text x={n.name[0]} y={n.name[1]} textAnchor="middle" style={{ fontFamily: DISPLAY, fontSize: L.nameSize, fontWeight: 500, letterSpacing: '-.015em' }} fill={INK}>{NAMES[n.k][0]}</text>
            <text x={n.cap[0]} y={n.cap[1]} textAnchor="middle" style={{ fontFamily: MONO, fontSize: L.capSize, letterSpacing: '.14em' }} fill={MUTE}>{NAMES[n.k][1]}</text>
            <g transform={`translate(${n.x} ${n.y}) scale(${n.s})`}>
              <rect width="200" height="200" rx="16" fill="#fff" stroke="rgba(19,21,25,.11)" />
              <C m={m} />
            </g>
          </g>
        );
      })}
      <g className="osd-card" style={{ transitionDelay: '420ms' }}><Hub {...L.hub} m={m} /></g>
      <Signal path={L.wires.consumer[0]} label="FIT" slot={0} m={m} />
      <Signal path={L.wires.brand[1]} label="DEMAND" slot={1} m={m} />
      <Signal path={L.wires.brand[0]} label="DESIGN" slot={2} m={m} />
      <Signal path={L.wires.factory[1]} label="SIZE RUN" slot={3} m={m} />
      <Signal path={L.wires.factory[0]} label="STOCK" slot={4} m={m} />
      <Signal path={L.wires.consumer[1]} label="RIGHT SIZE" slot={5} m={m} />
    </svg>
  );
}

export function OsDiagram() {
  const [motion, setMotion] = useState(true);
  const [seen, setSeen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const on = () => setMotion(!mq.matches);
    on(); mq.addEventListener('change', on);
    const el = ref.current;
    if (!el || !('IntersectionObserver' in window)) { setSeen(true); return () => mq.removeEventListener('change', on); }
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setSeen(true); io.disconnect(); } }, { threshold: 0.2 });
    io.observe(el);
    return () => { io.disconnect(); mq.removeEventListener('change', on); };
  }, []);
  return (
    <div ref={ref} className={`osd${seen || !motion ? ' in' : ''}`}>
      <style>{`
.osd .osd-card{opacity:0;transform:translateY(16px);transition:opacity .76s cubic-bezier(.22,1,.36,1),transform .76s cubic-bezier(.22,1,.36,1);transform-box:fill-box}
.osd.in .osd-card{opacity:1;transform:none}
.osd .osd-wire{stroke-dasharray:1;stroke-dashoffset:1;transition:stroke-dashoffset 1.4s cubic-bezier(.22,1,.36,1)}
.osd.in .osd-wire{stroke-dashoffset:0}
.osd-h{display:block}.osd-v{display:none}
@media(max-width:760px){.osd-h{display:none}.osd-v{display:block}}
@media (prefers-reduced-motion: reduce){.osd .osd-card{opacity:1;transform:none;transition:none}.osd .osd-wire{stroke-dashoffset:0;transition:none}}
`}</style>
      <div className="osd-h"><Diagram L={DESK} m={motion} /></div>
      <div className="osd-v"><Diagram L={PHONE} m={motion} /></div>
    </div>
  );
}
