'use client';

import { useEffect, useState } from 'react';

/* Consumer, brand, factory, and the operating system that connects them. Ink line drawings with the
   moving parts in cobalt: a scan passes over the shopper, stitches run around the garment, units move
   along the factory line, and signals travel between all three through the Tryon OS rail.
   Horizontal on wide screens, vertical on phones. Still under prefers-reduced-motion. */

const INK = '#131519';
const MUTE = '#626A78';
const RULE = 'rgba(19,21,25,.2)';
const BLUE = '#0040FF';

const NODES = [
  { k: 'consumer', name: 'Consumer', cap: 'Fit and behaviour' },
  { k: 'brand', name: 'Brand', cap: 'Design stress tested' },
  { k: 'factory', name: 'Factory', cap: 'Made to demand' },
] as const;

type Kind = (typeof NODES)[number]['k'];

function Icon({ kind, motion }: { kind: Kind; motion: boolean }) {
  const ink = { fill: 'none', stroke: INK, strokeWidth: 1.7, strokeLinejoin: 'round' as const, strokeLinecap: 'round' as const };
  if (kind === 'consumer') {
    return (
      <g>
        <circle cx="0" cy="-22" r="10" {...ink} />
        <path d="M-24 34 C-24 6 -14 -4 0 -4 C14 -4 24 6 24 34" {...ink} />
        <line x1="-30" x2="30" y1="0" y2="0" stroke={BLUE} strokeWidth="1.9" strokeLinecap="round">
          {motion && <animate attributeName="y1" values="-36;34;-36" dur="3.2s" repeatCount="indefinite" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1" />}
          {motion && <animate attributeName="y2" values="-36;34;-36" dur="3.2s" repeatCount="indefinite" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1" />}
        </line>
      </g>
    );
  }
  if (kind === 'brand') {
    return (
      <g>
        <path d="M-13 -30 L-30 -24 L-40 28 L-30 31 L-21 -4 L-21 34 L21 34 L21 -4 L30 31 L40 28 L30 -24 L13 -30 C9 -22 -9 -22 -13 -30 Z" {...ink} />
        <path d="M-21 -4 L-21 34 L21 34 L21 -4" fill="none" stroke={BLUE} strokeWidth="1.9" strokeDasharray="4 5" strokeLinecap="round">
          {motion && <animate attributeName="stroke-dashoffset" values="0;-36" dur="1.6s" repeatCount="indefinite" />}
        </path>
      </g>
    );
  }
  return (
    <g>
      <path d="M-38 34 V-2 L-18 -14 V-2 L2 -14 V-2 L20 -14 V-32 H30 V34 Z" {...ink} />
      <line x1="-38" x2="30" y1="34" y2="34" stroke={INK} strokeWidth="1.7" />
      {[0, 1, 2].map((i) => (
        <rect key={i} x="-34" y="16" width="9" height="9" rx="1.5" fill={BLUE}>
          {motion && <animate attributeName="x" values="-34;22" dur="2.4s" begin={`${i * 0.8}s`} repeatCount="indefinite" />}
          {motion && <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.12;.85;1" dur="2.4s" begin={`${i * 0.8}s`} repeatCount="indefinite" />}
        </rect>
      ))}
    </g>
  );
}

function Spark({ path, begin, motion }: { path: string; begin: string; motion: boolean }) {
  if (!motion) return null;
  return (
    <circle r="4" fill={BLUE} opacity="0">
      <animateMotion path={path} dur="3.4s" begin={begin} repeatCount="indefinite" calcMode="linear" />
      <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.08;.9;1" dur="3.4s" begin={begin} repeatCount="indefinite" />
    </circle>
  );
}

function Horizontal({ motion }: { motion: boolean }) {
  const xs = [200, 600, 1000];
  const top = 292, rail = 450;
  const p = (a: number, b: number) => `M${a} ${top} V${rail} H${b} V${top}`;
  return (
    <svg viewBox="0 0 1200 500" width="100%" role="img" aria-label="Consumer, brand and factory connected by the Tryon operating system" style={{ display: 'block', overflow: 'visible' }}>
      <line x1="120" x2="1080" y1={rail} y2={rail} stroke={RULE} strokeWidth="1" />
      {xs.map((x) => <line key={x} x1={x} x2={x} y1={top} y2={rail} stroke={RULE} strokeWidth="1" strokeDasharray="3 5" />)}
      {NODES.map((n, i) => (
        <g key={n.k}>
          <text x={xs[i]} y="58" textAnchor="middle" style={{ fontFamily: 'var(--f-display)', fontSize: 24, fontWeight: 500, letterSpacing: '-.01em' }} fill={INK}>{n.name}</text>
          <text x={xs[i]} y="86" textAnchor="middle" style={{ fontFamily: 'var(--f-mono)', fontSize: 11, letterSpacing: '.14em', textTransform: 'uppercase' }} fill={MUTE}>{n.cap.toUpperCase()}</text>
          <rect x={xs[i] - 86} y="120" width="172" height="172" rx="14" fill="#fff" stroke="rgba(19,21,25,.11)" />
          <g transform={`translate(${xs[i]} 206) scale(1.35)`}><Icon kind={n.k} motion={motion} /></g>
        </g>
      ))}
      <Spark path={p(200, 600)} begin="0s" motion={motion} />
      <Spark path={p(600, 1000)} begin="1.1s" motion={motion} />
      <Spark path={p(1000, 200)} begin="2.2s" motion={motion} />
      <Spark path={p(600, 200)} begin="1.7s" motion={motion} />
      <rect x="520" y={rail - 17} width="160" height="34" rx="17" fill="#fff" stroke={BLUE} />
      <text x="600" y={rail + 4} textAnchor="middle" style={{ fontFamily: 'var(--f-mono)', fontSize: 12, letterSpacing: '.16em', fontWeight: 500 }} fill={BLUE}>TRYON OS</text>
    </svg>
  );
}

function Vertical({ motion }: { motion: boolean }) {
  const ys = [90, 330, 570];
  const left = 112, rail = 58;
  const p = (a: number, b: number) => `M${left} ${a} H${rail} V${b} H${left}`;
  return (
    <svg viewBox="0 0 390 720" width="100%" role="img" aria-label="Consumer, brand and factory connected by the Tryon operating system" style={{ display: 'block', overflow: 'visible', maxWidth: 420, margin: '0 auto' }}>
      <line x1={rail} x2={rail} y1="40" y2="640" stroke={RULE} strokeWidth="1" />
      {ys.map((y) => <line key={y} x1={rail} x2={left} y1={y} y2={y} stroke={RULE} strokeWidth="1" strokeDasharray="3 5" />)}
      {NODES.map((n, i) => (
        <g key={n.k}>
          <rect x={left} y={ys[i] - 52} width="104" height="104" rx="14" fill="#fff" stroke="rgba(19,21,25,.11)" />
          <g transform={`translate(${left + 52} ${ys[i]}) scale(.82)`}><Icon kind={n.k} motion={motion} /></g>
          <text x={left + 122} y={ys[i] - 2} style={{ fontFamily: 'var(--f-display)', fontSize: 21, fontWeight: 500, letterSpacing: '-.01em' }} fill={INK}>{n.name}</text>
          <text x={left + 122} y={ys[i] + 20} style={{ fontFamily: 'var(--f-mono)', fontSize: 9.5, letterSpacing: '.1em' }} fill={MUTE}>{n.cap.toUpperCase()}</text>
        </g>
      ))}
      <Spark path={p(90, 330)} begin="0s" motion={motion} />
      <Spark path={p(330, 570)} begin="1.1s" motion={motion} />
      <Spark path={p(570, 90)} begin="2.2s" motion={motion} />
      <rect x={rail - 52} y="660" width="104" height="32" rx="16" fill="#fff" stroke={BLUE} />
      <text x={rail} y="680" textAnchor="middle" style={{ fontFamily: 'var(--f-mono)', fontSize: 11, letterSpacing: '.16em', fontWeight: 500 }} fill={BLUE}>TRYON OS</text>
      <line x1={rail} x2={rail} y1="640" y2="660" stroke={RULE} strokeWidth="1" />
    </svg>
  );
}

export function OsDiagram() {
  const [motion, setMotion] = useState(true);
  useEffect(() => {
    const m = window.matchMedia('(prefers-reduced-motion: reduce)');
    const on = () => setMotion(!m.matches);
    on(); m.addEventListener('change', on);
    return () => m.removeEventListener('change', on);
  }, []);
  return (
    <div>
      <style>{`.osd-h{display:block}.osd-v{display:none}@media(max-width:760px){.osd-h{display:none}.osd-v{display:block}}`}</style>
      <div className="osd-h"><Horizontal motion={motion} /></div>
      <div className="osd-v"><Vertical motion={motion} /></div>
    </div>
  );
}
