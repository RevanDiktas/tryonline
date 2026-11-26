'use client';

import { useEffect, useRef, useState } from 'react';

/* Consumer, brand, factory, connected by one line: the Tryon OS. A single soft light glides along the
   line from consumer to factory and back. As it passes, each icon and its connector fade to cobalt.
   Nothing else moves. Horizontal on wide screens, vertical on phones. Still under reduced motion. */

const INK = '#131519';
const MUTE = '#626A78';
const RULE = 'rgba(19,21,25,.14)';
const BLUE = '#0040FF';
const MONO = 'var(--f-mono), ui-monospace, monospace';
const DISPLAY = 'var(--f-display), system-ui, sans-serif';
const DUR = '9s';
const EASE = '.42 0 .58 1';

type Kind = 'consumer' | 'brand' | 'factory';
const NODES: { k: Kind; name: string; cap: string }[] = [
  { k: 'consumer', name: 'Consumer', cap: 'FIT AND BEHAVIOUR' },
  { k: 'brand', name: 'Brand', cap: 'DESIGN STRESS TESTED' },
  { k: 'factory', name: 'Factory', cap: 'MADE TO DEMAND' },
];

/* The light: out to the factory, a pause, back to the consumer, a pause. */
const TRACK = { keyTimes: '0;.42;.5;.92;1', keySplines: `${EASE};0 0 1 1;${EASE};0 0 1 1` };
/* When each node is lit, in the same timeline. */
const LIT: Record<Kind, { values: string; keyTimes: string }> = {
  consumer: { values: '1;0;0;1;1', keyTimes: '0;.07;.86;.93;1' },
  brand: { values: '0;0;1;0;0;1;0;0', keyTimes: '0;.14;.21;.28;.64;.71;.78;1' },
  factory: { values: '0;0;1;1;0;0', keyTimes: '0;.35;.42;.5;.57;1' },
};

function Glyph({ k, stroke }: { k: Kind; stroke: string }) {
  const p = { fill: 'none', stroke, strokeWidth: 1.6, strokeLinejoin: 'round' as const, strokeLinecap: 'round' as const };
  if (k === 'consumer') return <g {...p}><circle cx="0" cy="-12" r="8" /><path d="M-17 20 C-17 3 -9 -2 0 -2 C9 -2 17 3 17 20" /></g>;
  if (k === 'brand') return <g {...p}><path d="M-9 -18 L-20 -14 L-26 16 L-20 18 L-14 -1 L-14 20 L14 20 L14 -1 L20 18 L26 16 L20 -14 L9 -18 C6 -13 -6 -13 -9 -18 Z" /></g>;
  return <g {...p}><path d="M-22 20 V-1 L-10 -8 V-1 L2 -8 V-1 L12 -8 V-19 H18 V20 Z" /></g>;
}

function Node({ k, x, y, m }: { k: Kind; x: number; y: number; m: boolean }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <circle r="52" fill="#fff" stroke={RULE} />
      <Glyph k={k} stroke={INK} />
      <g opacity={m ? 0 : k === 'consumer' ? 1 : 0}>
        <circle r="52" fill="none" stroke={BLUE} strokeOpacity=".5" />
        <Glyph k={k} stroke={BLUE} />
        {m && <animate attributeName="opacity" {...LIT[k]} dur={DUR} repeatCount="indefinite" />}
      </g>
    </g>
  );
}

function Light({ attr, from, to, fixed, m }: { attr: 'cx' | 'cy'; from: number; to: number; fixed: number; m: boolean }) {
  const pos = attr === 'cx' ? { cx: from, cy: fixed } : { cx: fixed, cy: from };
  return (
    <g>
      <circle {...pos} r="16" fill={BLUE} opacity=".16" filter="url(#osd-blur)">
        {m && <animate attributeName={attr} values={`${from};${to};${to};${from};${from}`} {...TRACK} calcMode="spline" dur={DUR} repeatCount="indefinite" />}
      </circle>
      <circle {...pos} r="4" fill={BLUE}>
        {m && <animate attributeName={attr} values={`${from};${to};${to};${from};${from}`} {...TRACK} calcMode="spline" dur={DUR} repeatCount="indefinite" />}
      </circle>
    </g>
  );
}

function Connector({ k, d, m }: { k: Kind; d: string; m: boolean }) {
  return (
    <g>
      <path d={d} stroke={RULE} strokeWidth="1" />
      <path d={d} stroke={BLUE} strokeWidth="1.2" opacity={m ? 0 : k === 'consumer' ? 1 : 0}>
        {m && <animate attributeName="opacity" {...LIT[k]} dur={DUR} repeatCount="indefinite" />}
      </path>
    </g>
  );
}

const Blur = () => (
  <defs><filter id="osd-blur" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="6" /></filter></defs>
);

function Horizontal({ m }: { m: boolean }) {
  const xs = [200, 600, 1000], ny = 140, rail = 270;
  return (
    <svg viewBox="0 0 1200 330" width="100%" role="img" aria-label="Consumer, brand and factory connected by the Tryon operating system" style={{ display: 'block', overflow: 'visible' }}>
      <Blur />
      <line x1="140" x2="1060" y1={rail} y2={rail} stroke={RULE} strokeWidth="1" strokeLinecap="round" />
      {NODES.map((n, i) => <Connector key={n.k} k={n.k} d={`M${xs[i]} ${ny + 52} V${rail}`} m={m} />)}
      <Light attr="cx" from={200} to={1000} fixed={rail} m={m} />
      {NODES.map((n, i) => (
        <g key={n.k}>
          <text x={xs[i]} y="30" textAnchor="middle" style={{ fontFamily: DISPLAY, fontSize: 24, fontWeight: 500, letterSpacing: '-.015em' }} fill={INK}>{n.name}</text>
          <text x={xs[i]} y="56" textAnchor="middle" style={{ fontFamily: MONO, fontSize: 11, letterSpacing: '.14em' }} fill={MUTE}>{n.cap}</text>
          <Node k={n.k} x={xs[i]} y={ny} m={m} />
        </g>
      ))}
      <text x="600" y="312" textAnchor="middle" style={{ fontFamily: MONO, fontSize: 11.5, letterSpacing: '.2em', fontWeight: 500 }} fill={BLUE}>TRYON OS</text>
    </svg>
  );
}

function Vertical({ m }: { m: boolean }) {
  const ys = [80, 300, 520], nx = 150, rail = 48;
  return (
    <svg viewBox="0 0 390 640" width="100%" role="img" aria-label="Consumer, brand and factory connected by the Tryon operating system" style={{ display: 'block', overflow: 'visible', maxWidth: 420, margin: '0 auto' }}>
      <Blur />
      <line x1={rail} x2={rail} y1="40" y2="560" stroke={RULE} strokeWidth="1" strokeLinecap="round" />
      {NODES.map((n, i) => <Connector key={n.k} k={n.k} d={`M${rail} ${ys[i]} H${nx - 52}`} m={m} />)}
      <Light attr="cy" from={ys[0]} to={ys[2]} fixed={rail} m={m} />
      {NODES.map((n, i) => (
        <g key={n.k}>
          <Node k={n.k} x={nx} y={ys[i]} m={m} />
          <text x={nx + 70} y={ys[i] - 2} style={{ fontFamily: DISPLAY, fontSize: 21, fontWeight: 500, letterSpacing: '-.015em' }} fill={INK}>{n.name}</text>
          <text x={nx + 70} y={ys[i] + 20} style={{ fontFamily: MONO, fontSize: 9, letterSpacing: '.1em' }} fill={MUTE}>{n.cap}</text>
        </g>
      ))}
      <text x={rail} y="590" textAnchor="middle" style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: '.2em', fontWeight: 500 }} fill={BLUE}>TRYON OS</text>
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
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setSeen(true); io.disconnect(); } }, { threshold: 0.25 });
    io.observe(el);
    return () => { io.disconnect(); mq.removeEventListener('change', on); };
  }, []);
  return (
    <div ref={ref} className={`osd${seen || !motion ? ' in' : ''}`}>
      <style>{`
.osd{opacity:0;transform:translateY(12px);transition:opacity 1.2s cubic-bezier(.22,1,.36,1),transform 1.2s cubic-bezier(.22,1,.36,1)}
.osd.in{opacity:1;transform:none}
.osd-h{display:block}.osd-v{display:none}
@media(max-width:760px){.osd-h{display:none}.osd-v{display:block}}
@media (prefers-reduced-motion: reduce){.osd{opacity:1;transform:none;transition:none}}
`}</style>
      <div className="osd-h"><Horizontal m={motion} /></div>
      <div className="osd-v"><Vertical m={motion} /></div>
    </div>
  );
}
