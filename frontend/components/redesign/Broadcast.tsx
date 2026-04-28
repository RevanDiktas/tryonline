'use client';

import React, { createContext, useContext, useEffect, useRef, useState, ReactNode, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useIsMobile } from './useIsMobile';

const PAL = {
  light: {
    void: '#ffffff', ash: '#ffffff', steel: '#ffffff', iron: '#ffffff',
    bone: '#0A0A0A', dim: '#6E6E6E', faint: '#D8D4C9',
    slit: 'rgba(0,0,0,0.10)',
    cardBg: '#0A0A0A', cardInk: '#F2F1EC',
    cardHair: 'rgba(255,255,255,0.12)', cardDim: '#9A9A9A',
  },
  dark: {
    void: '#0A0A0A', ash: '#121212', steel: '#181818', iron: '#1F1F1F',
    bone: '#F2F1EC', dim: '#8A8A8A', faint: '#2A2A2A',
    slit: 'rgba(255,255,255,0.06)',
    cardBg: '#F2F1EC', cardInk: '#0A0A0A',
    cardHair: 'rgba(0,0,0,0.12)', cardDim: '#6E6E6E',
  },
};
type Palette = typeof PAL.light;
const ThemeCtx = createContext<Palette>(PAL.light);
const useC = () => useContext(ThemeCtx);

/* ─────── CountUp ─────── */
function useInView(ref: React.RefObject<HTMLElement>, threshold = 0.4) {
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || seen) return;
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) setSeen(true);
    }, { threshold });
    io.observe(el);
    return () => io.disconnect();
  }, [ref, seen, threshold]);
  return seen;
}

function CountUp({ to, suffix = '', duration = 1400, decimals = 0, style }: {
  to: number; suffix?: string; duration?: number; decimals?: number; style?: React.CSSProperties;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref as React.RefObject<HTMLElement>);
  const [v, setV] = useState(0);
  useEffect(() => {
    if (!inView) return;
    const start = performance.now();
    let raf: number;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setV(to * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [inView, to, duration]);
  const display = decimals > 0 ? v.toFixed(decimals) : Math.round(v).toString();
  return <span ref={ref} style={style}>{display}{suffix}</span>;
}

function SlitLight({ count = 48, opacity = 0.45 }: { count?: number; opacity?: number }) {
  const C = useC();
  return (
    <div aria-hidden style={{
      position: 'absolute', inset: 0, pointerEvents: 'none',
      backgroundImage: `linear-gradient(
        to right,
        transparent 0,
        transparent calc(100% / ${count} - 1px),
        ${C.slit} calc(100% / ${count} - 1px),
        ${C.slit} calc(100% / ${count})
      )`,
      maskImage: 'linear-gradient(to bottom, transparent 0%, #000 18%, #000 78%, transparent 100%)',
      WebkitMaskImage: 'linear-gradient(to bottom, transparent 0%, #000 18%, #000 78%, transparent 100%)',
      opacity,
    }} />
  );
}

function Stamp({ left, right, top }: { left: string; right: string; top?: string }) {
  const C = useC();
  return (
    <div style={{
      borderTop: `1px solid ${C.faint}`,
      borderBottom: `1px solid ${C.faint}`,
      padding: '14px 32px',
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
      textTransform: 'uppercase', color: C.dim,
      background: C.ash,
    }}>
      <span style={{ color: C.bone, opacity: 0.85 }}>{left}</span>
      {top && <span>{top}</span>}
      <span>{right}</span>
    </div>
  );
}

function MobileStamp({ left, right }: { left: string; right: string }) {
  const C = useC();
  return (
    <div style={{
      borderTop: `1px solid ${C.faint}`, borderBottom: `1px solid ${C.faint}`,
      padding: '10px 16px',
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.28em',
      textTransform: 'uppercase', color: C.dim, background: C.ash,
    }}>
      <span style={{ color: C.bone }}>{left}</span>
      <span>{right}</span>
    </div>
  );
}

/* Apple-style smart-nav: always visible near the top; any upward scroll
   instantly reveals; only hides after sustained downward scroll. */
function useSmartNav() {
  const [hidden, setHidden] = useState(false);
  useEffect(() => {
    let lastY = window.scrollY;
    let downAccum = 0;
    let raf = 0;
    const onScroll = () => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        const y = window.scrollY;
        const dy = y - lastY;
        lastY = y;
        raf = 0;

        // Within the top reveal zone, stay open and reset accumulator.
        if (y < 100) {
          downAccum = 0;
          setHidden(false);
          return;
        }
        // Any upward motion: show immediately and reset.
        if (dy < 0) {
          downAccum = 0;
          setHidden(false);
          return;
        }
        // Continued downward motion: accumulate; hide after a sustained run.
        downAccum += dy;
        if (downAccum > 60) setHidden(true);
      });
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  return hidden;
}

/* ─────── Desktop sections ─────── */
function DesktopNav() {
  const C = useC();
  const router = useRouter();
  const [active, setActive] = useState('index');
  const hidden = useSmartNav();

  useEffect(() => {
    const ids = ['index', 'product', 'brands'];
    const els = ids.map(id => document.getElementById(`tryon-section-${id}`)).filter(Boolean) as HTMLElement[];
    if (!els.length) return;
    const io = new IntersectionObserver(
      entries => {
        const visible = entries.filter(e => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]) setActive(visible[0].target.id.replace('tryon-section-', ''));
      },
      { threshold: [0.25, 0.5, 0.75] }
    );
    els.forEach(el => io.observe(el));
    return () => io.disconnect();
  }, []);

  const items = [
    { id: 'index', label: 'INDEX' },
    { id: 'product', label: 'PRODUCT' },
    { id: 'brands', label: 'BRANDS' },
    { id: 'deck', label: 'DECK' },
  ];

  const goto = (id: string) => {
    if (id === 'deck') {
      // Pitch deck is a standalone horizontal slide deck; open in a new tab.
      window.open('/pitch-deck.html', '_blank', 'noopener');
      return;
    }
    const el = document.getElementById(`tryon-section-${id}`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const cap: React.CSSProperties = {
    background: C.bone === '#0A0A0A' ? 'rgba(245,243,239,0.78)' : 'rgba(10,10,10,0.72)',
    border: `1px solid ${C.faint}`,
    boxShadow: '0 8px 24px rgba(10,10,10,0.06), 0 1px 3px rgba(10,10,10,0.04)',
    backdropFilter: 'saturate(180%) blur(20px)',
    WebkitBackdropFilter: 'saturate(180%) blur(20px)',
  };

  return (
    <div style={{
      position: 'sticky', top: 0, zIndex: 70,
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '14px 20px',
      pointerEvents: 'none',
      marginBottom: -68,
      transform: hidden ? 'translateY(-110%)' : 'translateY(0)',
      transition: 'transform 0.28s cubic-bezier(0.4, 0.0, 0.2, 1)',
    }}>
      <div style={{
        ...cap, pointerEvents: 'auto',
        display: 'inline-flex', alignItems: 'center',
        gap: 22, padding: '10px 18px 10px 14px', borderRadius: 999,
      }}>
        <button
          type="button"
          onClick={() => router.push('/')}
          style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', display: 'inline-flex' }}
          aria-label="TRYON home"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={C.bone === '#0A0A0A' ? '/redesign/wordmark.png' : '/redesign/wordmark-white.png'}
            alt="TRYON"
            style={{ height: 22, width: 'auto', display: 'block' }}
          />
        </button>
        <div style={{ width: 1, height: 18, background: C.faint }} />
        <div style={{ display: 'flex', gap: 18 }}>
          {items.map(it => {
            const isActive = active === it.id;
            return (
              <button
                key={it.id}
                onClick={() => goto(it.id)}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 8,
                  border: 0, padding: 0, background: 'transparent', cursor: 'pointer',
                  fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
                  color: isActive ? C.bone : C.dim,
                  textTransform: 'uppercase', fontWeight: isActive ? 700 : 500,
                }}
              >
                <span style={{
                  width: 7, height: 7,
                  background: isActive ? C.bone : 'transparent',
                  border: isActive ? 'none' : `1px solid ${C.dim}`,
                  display: 'inline-block',
                }} />
                {it.label}
              </button>
            );
          })}
        </div>
      </div>

      <div style={{
        ...cap, pointerEvents: 'auto',
        display: 'inline-flex', alignItems: 'stretch',
        padding: 4, gap: 4, borderRadius: 999,
      }}>
        <button
          onClick={() => router.push('/login')}
          style={{
            padding: '9px 16px', background: 'transparent', border: 'none', color: C.bone,
            fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
            textTransform: 'uppercase', fontWeight: 500, cursor: 'pointer',
          }}
        >SIGN IN</button>
        <button
          onClick={() => router.push('/signup')}
          style={{
            padding: '9px 16px',
            background: C.bone, color: C.void, border: 'none',
            fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
            textTransform: 'uppercase', fontWeight: 700, cursor: 'pointer',
            display: 'inline-flex', alignItems: 'center', gap: 8, borderRadius: 999,
          }}
        >ENTER<span style={{ fontSize: 12 }}>→</span></button>
      </div>
    </div>
  );
}

function DesktopHero() {
  const C = useC();
  const router = useRouter();

  const ctas = [
    { side: 'L', tag: 'FOR BRANDS', t: 'I AM A BRAND', sub: 'Ship the protocol. Cut returns.', href: '/signup?type=brand' },
    { side: 'R', tag: 'FOR SHOPPERS', t: 'I AM A SHOPPER', sub: 'Build your fit passport. Free, forever.', href: '/signup' },
  ];

  return (
    <section id="tryon-section-index" style={{
      background: `radial-gradient(ellipse at 50% 110%, ${C.iron} 0%, ${C.ash} 35%, ${C.void} 80%)`,
      color: C.bone, position: 'relative',
      minHeight: '100dvh', overflow: 'hidden',
      padding: '56px 32px 0',
      display: 'flex', flexDirection: 'column',
    }}>
      <SlitLight count={72} opacity={0.65} />

      <div style={{
        position: 'relative', zIndex: 4,
        marginTop: 'auto', marginBottom: 0, paddingBottom: 28,
      }}>
        <div style={{
          fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.4em',
          color: C.dim, textTransform: 'uppercase',
          marginBottom: 18, textAlign: 'center',
        }}>— A SINGLE PROTOCOL FOR FIT —</div>

        <h1 style={{
          fontFamily: 'var(--display)', fontWeight: 900,
          fontSize: 'clamp(72px, 11vw, 168px)',
          letterSpacing: '-0.055em', lineHeight: 0.86,
          margin: 0, textTransform: 'uppercase',
          textAlign: 'center', color: C.bone,
        }}>
          <span style={{ display: 'block' }}>TRYON</span>
          <span style={{ display: 'block', WebkitTextStroke: `2px ${C.bone}`, color: 'transparent' }}>BEFORE</span>
          <span style={{ display: 'block' }}>YOU BUY.</span>
        </h1>
      </div>

      <div style={{
        position: 'relative', zIndex: 5,
        borderTop: `1px solid ${C.faint}`,
        display: 'grid', gridTemplateColumns: '1fr 1fr',
        marginLeft: -32, marginRight: -32,
      }}>
        {ctas.map((c, i) => (
          <HeroCTA key={c.t} c={c} first={i === 0} onClick={() => router.push(c.href)} C={C} />
        ))}
      </div>
    </section>
  );
}

function HeroCTA({
  c, first, onClick, C,
}: {
  c: { side: string; tag: string; t: string; sub: string };
  first: boolean;
  onClick: () => void;
  C: Palette;
}) {
  const [hover, setHover] = useState(false);
  const ink = hover ? C.void : C.bone; // headline / arrow color
  const tagColor = hover ? C.void : C.dim;
  const subColor = ink;
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        padding: '22px 28px 20px',
        borderRight: first ? `1px solid ${C.faint}` : 'none',
        display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
        gap: 14, minHeight: 116,
        background: hover ? C.bone : 'transparent',
        cursor: 'pointer', border: 'none',
        textAlign: c.side === 'R' ? 'right' : 'left',
        color: ink,
        transition: 'background 0.18s ease, color 0.18s ease',
      }}
    >
      <div style={{
        fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.4em',
        color: tagColor, textTransform: 'uppercase',
        transition: 'color 0.18s ease',
      }}>{c.tag}</div>
      <div style={{
        display: 'flex', alignItems: 'baseline', justifyContent: 'space-between',
        flexDirection: c.side === 'R' ? 'row-reverse' : 'row', gap: 16,
      }}>
        <h3 style={{
          fontFamily: 'var(--display)', fontWeight: 900,
          fontSize: 'clamp(28px, 3.8vw, 56px)', letterSpacing: '-0.04em',
          lineHeight: 0.92, margin: 0, color: ink,
          textTransform: 'uppercase',
          transition: 'color 0.18s ease',
        }}>{c.t}</h3>
        <span style={{
          fontFamily: 'var(--display)', fontSize: 36, fontWeight: 900,
          color: ink, lineHeight: 1,
          transform: c.side === 'R' ? 'none' : 'rotate(180deg)',
          transition: 'color 0.18s ease',
        }}>→</span>
      </div>
      <div style={{
        fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.18em',
        color: subColor, opacity: 0.78, textTransform: 'uppercase',
        transition: 'color 0.18s ease',
      }}>{c.sub}</div>
    </button>
  );
}

function DesktopBigType() {
  const C = useC();
  const phrase = (key: number) => (
    <span key={key} style={{ display: 'inline-flex', alignItems: 'center' }}>
      <span>3D AVATAR</span>
      <span style={{ WebkitTextStroke: `2px ${C.bone}`, color: 'transparent', padding: '0 0.25em' }}>EVERY BRAND</span>
      <span>ONE FIT</span>
      <span style={{ padding: '0 0.25em', color: C.dim }}>·</span>
    </span>
  );

  return (
    <section style={{
      background: C.ash, color: C.bone, position: 'relative',
      minHeight: '100dvh', padding: '0 0 88px', overflow: 'hidden',
      display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
    }}>
      <Stamp left="002 / 07" right="THE PROTOCOL" top="WHAT IT IS" />

      <div style={{
        whiteSpace: 'nowrap',
        fontFamily: 'var(--display)',
        fontSize: 'clamp(80px, 12vw, 180px)',
        fontWeight: 900,
        letterSpacing: '-0.06em', lineHeight: 0.86,
        textTransform: 'uppercase',
        display: 'flex',
        marginTop: 40, marginBottom: 40,
        animation: 'tryon-bigtype-marquee 12s linear infinite',
      }}>
        {[0, 1, 2, 3, 4, 5].map(i => phrase(i))}
      </div>

      <div style={{
        padding: '0 32px',
        display: 'grid', gridTemplateColumns: '1fr 1fr 1fr',
        borderTop: `1px solid ${C.faint}`,
        borderBottom: `1px solid ${C.faint}`,
      }}>
        {[
          { k: 'SETUP', v: <CountUp to={90} suffix="s" /> },
          { k: 'BRANDS', v: '∞' as ReactNode },
          { k: 'RETURNS', v: <><span>−</span><CountUp to={40} suffix="%" /></> },
        ].map((c, i) => (
          <div key={c.k} style={{
            padding: '24px 24px',
            borderRight: i < 2 ? `1px solid ${C.faint}` : 'none',
            display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
            gap: 14, minHeight: 124,
          }}>
            <div style={{
              fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.4em',
              color: C.dim, textTransform: 'uppercase',
            }}>{c.k}</div>
            <div style={{
              fontFamily: 'var(--display)', fontWeight: 900,
              fontSize: 'clamp(48px, 6vw, 88px)', letterSpacing: '-0.04em',
              color: C.bone, lineHeight: 0.9,
            }}>{c.v}</div>
          </div>
        ))}
      </div>

      <div style={{
        padding: '0 32px',
        display: 'grid', gridTemplateColumns: '1fr 1fr 1fr',
      }}>
        {[
          { k: '001 / BUILD', t: 'Your fit passport. A rigged 3D avatar from 12 measurements. Built once. Yours forever.' },
          { k: '002 / REUSE', t: 'Drop into any TRYON brand. The avatar travels. Real cloth physics. Real photography.' },
          { k: '003 / BUY', t: 'Confidence per SKU. Returns drop ~40%. Overproduction ends.' },
        ].map((c, i) => (
          <div key={c.k} style={{
            padding: '24px 24px 0',
            borderRight: i < 2 ? `1px solid ${C.faint}` : 'none',
          }}>
            <div style={{
              fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
              color: C.dim, marginBottom: 10, textTransform: 'uppercase',
            }}>{c.k}</div>
            <p style={{ fontSize: 14, lineHeight: 1.45, margin: 0, color: C.bone, opacity: 0.92 }}>{c.t}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function DesktopProductGrid() {
  const C = useC();
  const items: { n: string; tag: string; desc: string; image?: string }[] = [
    { n: '01', tag: 'FIT PASSPORT', desc: 'A 3D avatar of you, rigged.', image: '/redesign/fit-passport.jpg' },
    { n: '02', tag: 'GARMENT BIND', desc: 'Real cloth physics, real product photography.', image: '/redesign/garment-bind.jpg' },
    { n: '03', tag: 'FIT REPORT', desc: 'Per-SKU confidence and size signal.' },
    { n: '04', tag: 'WIDGET', desc: '8 lines of code. Any brand. Any stack.' },
  ];
  return (
    <section id="tryon-section-product" style={{
      background: C.void, color: C.bone, position: 'relative',
      minHeight: '100dvh',
      display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
    }}>
      <Stamp left="003 / 07" right="COMPONENTS" top="THE BREAKDOWN" />
      <div style={{ padding: '72px 32px 88px', flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <h2 style={{
          fontFamily: 'var(--display)', fontWeight: 900, margin: '0 0 36px',
          fontSize: 'clamp(48px, 7vw, 112px)', letterSpacing: '-0.05em', lineHeight: 0.84,
          textTransform: 'uppercase', textAlign: 'center',
        }}>
          PRODUCT<br/>
          <span style={{ WebkitTextStroke: `2px ${C.bone}`, color: 'transparent' }}>BREAKDOWN</span>
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 0, border: `1px solid ${C.faint}` }}>
          {items.map((it, i) => (
            <div key={it.n} style={{
              borderRight: i < 3 ? `1px solid ${C.faint}` : 'none',
              display: 'flex', flexDirection: 'column', background: C.ash,
            }}>
              <div style={{
                borderBottom: `1px solid ${C.faint}`,
                padding: '14px 18px',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
                textTransform: 'uppercase', color: C.bone,
              }}>
                <span>{it.tag}</span>
                <span style={{ color: C.dim }}>{it.n}</span>
              </div>
              <div style={{
                aspectRatio: '4/5', background: C.steel, position: 'relative',
                display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
              }}>
                {it.image ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={it.image}
                    alt={it.tag}
                    style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                  />
                ) : (
                  <>
                    <SlitLight count={20} opacity={0.5} />
                    <span style={{
                      position: 'relative', zIndex: 2,
                      fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
                      color: C.dim, padding: '6px 10px', border: `1px solid ${C.faint}`,
                    }}>IMAGE TBD</span>
                  </>
                )}
              </div>
              <div style={{
                borderTop: `1px solid ${C.faint}`, padding: '18px 18px',
                fontSize: 13, lineHeight: 1.45, color: C.bone, opacity: 0.85,
              }}>{it.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function DesktopProofBig() {
  const C = useC();
  return (
    <section style={{
      background: C.ash, color: C.bone, position: 'relative', overflow: 'hidden',
      minHeight: '100dvh',
      display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
    }}>
      <Stamp left="004 / 07" right="LIVE TRACTION" top="RAMIN STUDIOS · AMSTERDAM · 14 DAYS" />
      <div style={{
        padding: '88px 32px',
        display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 48, alignItems: 'center',
        position: 'relative', flex: 1,
      }}>
        <SlitLight count={36} opacity={0.35} />
        <h2 style={{
          fontFamily: 'var(--display)', fontWeight: 900,
          fontSize: 'clamp(140px, 20vw, 320px)',
          letterSpacing: '-0.07em', lineHeight: 0.78, margin: 0,
          textTransform: 'uppercase', position: 'relative', zIndex: 2,
        }}>
          <CountUp to={94} duration={1800} /><span style={{ WebkitTextStroke: `3px ${C.bone}`, color: 'transparent' }}>%</span>
        </h2>
        <div style={{ position: 'relative', zIndex: 2 }}>
          <p style={{ fontSize: 18, fontWeight: 600, lineHeight: 1.3, margin: '0 0 20px', letterSpacing: '-0.02em' }}>
            of widget opens convert to a try-on.<br/>
            <span style={{ color: C.dim }}>Live data. Last 14 days.</span>
          </p>
          <div style={{ border: `1px solid ${C.faint}` }}>
            {[
              { k: 'OPENS', node: <CountUp to={100} /> },
              { k: 'TRY-ONS', node: <CountUp to={94} /> },
              { k: 'ATC', node: <CountUp to={34} /> },
              { k: 'AVG SESSION', node: <><CountUp to={38} />s</> },
            ].map((row, i, arr) => (
              <div key={row.k} style={{
                display: 'grid', gridTemplateColumns: '1fr 1fr',
                padding: '10px 16px', alignItems: 'baseline',
                borderBottom: i < arr.length - 1 ? `1px solid ${C.faint}` : 'none',
                background: C.steel,
              }}>
                <span style={{ fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.32em', color: C.dim }}>{row.k}</span>
                <span style={{ fontFamily: 'var(--display)', fontSize: 22, fontWeight: 800, letterSpacing: '-0.02em', textAlign: 'right', color: C.bone }}>{row.node}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function DesktopCarbon() {
  const C = useC();
  const rows = [
    { k: 'RETURNS AVOIDED', v: 40, suffix: '%', sub: 'less reverse logistics, less landfill.' },
    { k: 'OVERPRODUCTION CUT', v: 18, suffix: '%', sub: 'brands manufacture closer to real demand.' },
    { k: 'CO₂E PER ORDER', v: 2.4, suffix: 'kg', sub: 'avg saved when a return is prevented.', decimals: 1 },
  ];
  return (
    <section style={{
      background: C.void, color: C.bone, position: 'relative', overflow: 'hidden',
      minHeight: '100dvh',
      display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
    }}>
      <Stamp left="005 / 07" right="WASTE LEDGER" top="THE FOOTPRINT" />
      <SlitLight count={56} opacity={0.32} />
      <div style={{
        padding: '88px 32px',
        display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 56, alignItems: 'start',
        position: 'relative', zIndex: 2, flex: 1,
      }}>
        <div>
          <div style={{
            fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.4em',
            color: C.dim, textTransform: 'uppercase', marginBottom: 16,
          }}>— THE INDUSTRY&apos;S DIRTIEST SECRET —</div>
          <h2 style={{
            fontFamily: 'var(--display)', fontWeight: 900,
            fontSize: 'clamp(48px, 6.5vw, 112px)', letterSpacing: '-0.05em',
            lineHeight: 0.84, margin: '0 0 20px', textTransform: 'uppercase',
          }}>
            FIT IS A<br/>
            <span style={{ WebkitTextStroke: `2px ${C.bone}`, color: 'transparent' }}>CLIMATE</span><br/>
            PROBLEM.
          </h2>
          <p style={{ fontSize: 15, lineHeight: 1.5, margin: '0 0 14px', color: C.bone, opacity: 0.88, maxWidth: 520 }}>
            Online apparel returns over 30% of what ships. Most of that comes back because of fit. Most of that never gets resold.
          </p>
          <p style={{ fontSize: 15, lineHeight: 1.5, margin: 0, color: C.bone, opacity: 0.88, maxWidth: 520 }}>
            TRYON kills the return before the order. Fewer trucks. Less plastic. Less polyester pulled out of the ground for stock that nobody wears.
          </p>
        </div>
        <div style={{ border: `1px solid ${C.faint}`, background: C.steel }}>
          <div style={{
            borderBottom: `1px solid ${C.faint}`,
            padding: '14px 20px',
            display: 'flex', justifyContent: 'space-between',
            fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
            textTransform: 'uppercase', color: C.dim,
          }}>
            <span style={{ color: C.bone }}>WASTE LEDGER</span>
            <span>PER 1,000 ORDERS</span>
          </div>
          {rows.map((r, i) => (
            <div key={r.k} style={{
              padding: '18px 20px',
              borderBottom: i < rows.length - 1 ? `1px solid ${C.faint}` : 'none',
            }}>
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4,
              }}>
                <span style={{
                  fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em', color: C.dim,
                }}>{r.k}</span>
                <span style={{
                  fontFamily: 'var(--display)', fontSize: 36, fontWeight: 900,
                  letterSpacing: '-0.04em', color: C.bone, lineHeight: 1,
                }}>
                  <span>−</span><CountUp to={r.v} decimals={r.decimals || 0} />{r.suffix}
                </span>
              </div>
              <div style={{ fontSize: 13, lineHeight: 1.4, color: C.bone, opacity: 0.7 }}>{r.sub}</div>
            </div>
          ))}
          <div style={{
            padding: '14px 20px',
            borderTop: `1px solid ${C.faint}`,
            fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.28em',
            color: C.dim, textTransform: 'uppercase',
          }}>SOURCE · TRYON PILOT + INDUSTRY BENCHMARKS · 2026</div>
        </div>
      </div>
    </section>
  );
}

function DesktopBehind() {
  const C = useC();
  return (
    <section id="tryon-section-brands" style={{
      background: C.void, color: C.bone, position: 'relative',
      minHeight: '100dvh',
      display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
    }}>
      <Stamp left="006 / 07" right="BEHIND THE LOGIN" top="THE CLOSET" />
      <div style={{
        padding: '88px 32px',
        display: 'grid', gridTemplateColumns: '1fr 1.4fr', gap: 48, alignItems: 'center',
        flex: 1,
      }}>
        <div>
          <h2 style={{
            fontFamily: 'var(--display)', fontWeight: 900,
            fontSize: 'clamp(40px, 5vw, 80px)', letterSpacing: '-0.04em',
            lineHeight: 0.86, margin: '0 0 16px', textTransform: 'uppercase',
          }}>
            ONE LOGIN.<br/>
            <span style={{ WebkitTextStroke: `2px ${C.bone}`, color: 'transparent' }}>EVERY</span> BRAND.
          </h2>
          <p style={{ fontSize: 14, lineHeight: 1.5, margin: 0, color: C.bone, opacity: 0.78, maxWidth: 440 }}>
            Free for shoppers. Forever. Your fit passport, your closet, every garment you&apos;ve ever tried, synced across every TRYON brand.
          </p>
        </div>
        <div style={{
          border: `1px solid ${C.faint}`, background: C.steel,
          aspectRatio: '16/10', overflow: 'hidden', position: 'relative',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <SlitLight count={60} opacity={0.4} />
          <span style={{
            position: 'relative', zIndex: 2,
            fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.32em',
            color: C.dim, padding: '6px 10px', border: `1px solid ${C.faint}`,
          }}>IMAGE TBD</span>
          <div style={{
            position: 'absolute', top: 12, left: 12,
            background: C.bone, color: C.void,
            fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.28em',
            textTransform: 'uppercase', fontWeight: 700,
            padding: '6px 10px', zIndex: 3,
          }}>WISHLIST · DASHBOARD</div>
        </div>
      </div>
    </section>
  );
}

function DesktopCTA() {
  const C = useC();
  const router = useRouter();
  const [email, setEmail] = useState('');

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = email.trim();
    router.push(trimmed ? `/signup?email=${encodeURIComponent(trimmed)}` : '/signup');
  };

  return (
    <section id="tryon-section-enter" style={{
      background: C.ash, color: C.bone, position: 'relative', overflow: 'hidden',
      minHeight: '100dvh',
      display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
    }}>
      <Stamp left="007 / 07" right="ENTER" top="START" />
      <SlitLight count={64} opacity={0.4} />
      <div style={{ padding: '96px 32px 80px', position: 'relative', zIndex: 2, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <div style={{
          fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.4em',
          color: C.dim, textTransform: 'uppercase', textAlign: 'center', marginBottom: 16,
        }}>— FREE FOREVER · NO MEASUREMENT FORM —</div>

        <h2 style={{
          fontFamily: 'var(--display)', fontWeight: 900, margin: '0 0 14px',
          fontSize: 'clamp(72px, 11vw, 200px)', letterSpacing: '-0.06em',
          lineHeight: 0.84, textAlign: 'center', textTransform: 'uppercase',
        }}>
          BUILD YOUR<br/>
          <span style={{ WebkitTextStroke: `3px ${C.bone}`, color: 'transparent' }}>FIT PASSPORT.</span>
        </h2>

        <p style={{
          textAlign: 'center', fontSize: 16, lineHeight: 1.4,
          margin: '0 auto 28px', maxWidth: 620, color: C.dim, fontWeight: 500,
        }}>
          90 seconds. 12 measurements. One avatar that wears every TRYON brand on Earth.
        </p>

        <div style={{
          maxWidth: 720, margin: '0 auto',
          background: C.cardBg, color: C.cardInk,
          border: `1px solid ${C.bone}`,
          boxShadow: '0 32px 80px rgba(0,0,0,0.18)',
        }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '14px 20px',
            borderBottom: `1px solid ${C.cardHair}`,
            fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
            textTransform: 'uppercase', color: C.cardDim,
          }}>
            <span style={{ color: C.cardInk }}>SHOPPER · ENTRY</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              <span style={{
                width: 7, height: 7, borderRadius: '50%', background: '#7CFFA1',
                boxShadow: '0 0 12px #7CFFA1',
              }} />
              ACCEPTING
            </span>
          </div>
          <form onSubmit={submit} style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 0 }}>
            <input
              type="email"
              placeholder="you@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={{
                background: 'transparent', border: 'none', outline: 'none',
                padding: '18px 20px',
                fontFamily: 'var(--display)', fontSize: 18, fontWeight: 600,
                letterSpacing: '-0.01em', color: C.cardInk,
              }}
            />
            <button
              type="submit"
              style={{
                background: C.cardInk, color: C.cardBg,
                padding: '0 28px', minHeight: 60,
                fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.32em',
                textTransform: 'uppercase', fontWeight: 800, border: 'none',
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12,
              }}
            >
              GET MY PASSPORT
              <span style={{ fontSize: 16 }}>→</span>
            </button>
          </form>
          <div style={{
            display: 'grid', gridTemplateColumns: '1fr 1fr 1fr',
            borderTop: `1px solid ${C.cardHair}`,
          }}>
            {[['BUILD', '90s'], ['BRANDS', '∞'], ['COST', 'FREE']].map(([k, v], i) => (
              <div key={k} style={{
                padding: '16px 20px',
                borderRight: i < 2 ? `1px solid ${C.cardHair}` : 'none',
              }}>
                <div style={{
                  fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.32em',
                  color: C.cardDim, marginBottom: 4,
                }}>{k}</div>
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 22, fontWeight: 800,
                  letterSpacing: '-0.02em', color: C.cardInk,
                }}>{v}</div>
              </div>
            ))}
          </div>
        </div>

        <div style={{
          marginTop: 20, textAlign: 'center',
          fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.32em',
          color: C.dim, textTransform: 'uppercase',
        }}>
          ARE YOU A BRAND?{' '}
          <button
            onClick={() => router.push('/signup?type=brand')}
            style={{
              color: C.bone, borderBottom: `1px solid ${C.bone}`,
              paddingBottom: 2, background: 'none', border: 'none',
              borderBottomWidth: 1, borderBottomStyle: 'solid',
              fontFamily: 'inherit', fontSize: 'inherit', letterSpacing: 'inherit',
              textTransform: 'inherit', cursor: 'pointer',
            }}
          >BOOK A DEMO →</button>
        </div>

        <div style={{
          marginTop: 56,
          fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.4em',
          color: C.dim, textTransform: 'uppercase', textAlign: 'center',
          borderTop: `1px solid ${C.faint}`, paddingTop: 20,
        }}>FIT FOLLOWS · TRYON · MMXXVI</div>
      </div>
    </section>
  );
}

/* ─────── Mobile sections ─────── */
function MobileNav() {
  const C = useC();
  const router = useRouter();
  const hidden = useSmartNav();

  const cap: React.CSSProperties = {
    background: C.bone === '#0A0A0A' ? 'rgba(245,243,239,0.82)' : 'rgba(10,10,10,0.74)',
    border: `1px solid ${C.faint}`,
    boxShadow: '0 6px 18px rgba(10,10,10,0.08)',
    backdropFilter: 'saturate(180%) blur(18px)',
    WebkitBackdropFilter: 'saturate(180%) blur(18px)',
  };

  return (
    <div style={{
      position: 'sticky', top: 0, zIndex: 70,
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '10px 12px', pointerEvents: 'none',
      transform: hidden ? 'translateY(-110%)' : 'translateY(0)',
      transition: 'transform 0.28s cubic-bezier(0.4, 0.0, 0.2, 1)',
    }}>
      <div style={{
        ...cap, pointerEvents: 'auto',
        display: 'inline-flex', alignItems: 'center', gap: 10,
        padding: '7px 11px', borderRadius: 999,
      }}>
        <button
          type="button"
          onClick={() => router.push('/')}
          style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', display: 'inline-flex' }}
          aria-label="TRYON home"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={C.bone === '#0A0A0A' ? '/redesign/wordmark.png' : '/redesign/wordmark-white.png'}
            alt="TRYON"
            style={{ height: 18, width: 'auto', display: 'block' }}
          />
        </button>
      </div>

      <div style={{
        ...cap, pointerEvents: 'auto',
        display: 'inline-flex', alignItems: 'stretch',
        padding: 3, gap: 3, borderRadius: 999,
      }}>
        <button
          onClick={() => router.push('/login')}
          style={{
            padding: '7px 10px', background: 'transparent', border: 'none', color: C.bone,
            fontFamily: 'var(--mono)', fontSize: 8, letterSpacing: '0.28em',
            textTransform: 'uppercase', fontWeight: 500, cursor: 'pointer',
          }}
        >SIGN IN</button>
        <button
          onClick={() => router.push('/signup')}
          style={{
            padding: '7px 10px', background: C.bone, color: C.void, border: 'none',
            fontFamily: 'var(--mono)', fontSize: 8, letterSpacing: '0.28em',
            textTransform: 'uppercase', fontWeight: 700, cursor: 'pointer',
            borderRadius: 999,
          }}
        >ENTER →</button>
      </div>
    </div>
  );
}

function MobileHero() {
  const C = useC();
  const router = useRouter();
  const ctas = [
    { side: 'L', tag: 'FOR BRANDS', t: 'I AM A BRAND', sub: 'Ship the protocol.', href: '/signup?type=brand' },
    { side: 'R', tag: 'FOR SHOPPERS', t: 'I AM A SHOPPER', sub: 'Build your fit passport.', href: '/signup' },
  ];
  return (
    <section style={{
      background: `radial-gradient(ellipse at 50% 110%, ${C.iron} 0%, ${C.ash} 40%, ${C.void} 90%)`,
      color: C.bone, position: 'relative', overflow: 'hidden',
      minHeight: '100dvh',
      padding: '32px 16px 24px',
      display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
    }}>
      <SlitLight count={24} opacity={0.45} />
      <div style={{
        fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.32em',
        color: C.dim, textTransform: 'uppercase', marginBottom: 24,
        position: 'relative', zIndex: 2,
      }}>VOL.01 / FIT INFRASTRUCTURE</div>

      <div style={{ position: 'relative', zIndex: 2 }}>
        <h1 style={{
          fontFamily: 'var(--display)', fontWeight: 900,
          fontSize: 60, letterSpacing: '-0.05em', lineHeight: 0.86,
          margin: 0, textTransform: 'uppercase', color: C.bone,
        }}>
          <span style={{ display: 'block' }}>TRYON</span>
          <span style={{ display: 'block', WebkitTextStroke: `1.5px ${C.bone}`, color: 'transparent' }}>BEFORE</span>
          <span style={{ display: 'block' }}>YOU BUY.</span>
        </h1>
        <p style={{
          marginTop: 20, fontSize: 14, lineHeight: 1.45, color: C.bone, opacity: 0.78,
          fontWeight: 500, maxWidth: 320,
        }}>
          A single fit protocol. One avatar that wears every garment, every brand, every store.
        </p>
      </div>

      <div style={{
        marginTop: 28, position: 'relative', zIndex: 3,
        borderTop: `1px solid ${C.faint}`,
        marginLeft: -16, marginRight: -16,
        display: 'grid', gridTemplateColumns: '1fr 1fr',
      }}>
        {ctas.map((c, i) => (
          <button
            key={c.t}
            onClick={() => router.push(c.href)}
            style={{
              padding: '18px 14px 16px',
              borderRight: i === 0 ? `1px solid ${C.faint}` : 'none',
              display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
              gap: 10, minHeight: 124,
              background: 'transparent', cursor: 'pointer', border: 'none',
              textAlign: c.side === 'R' ? 'right' : 'left',
              color: C.bone,
            }}
          >
            <div style={{
              fontFamily: 'var(--mono)', fontSize: 8, letterSpacing: '0.32em',
              color: C.dim, textTransform: 'uppercase',
            }}>{c.tag}</div>
            <div style={{
              fontFamily: 'var(--display)', fontWeight: 900,
              fontSize: 22, letterSpacing: '-0.03em', lineHeight: 0.95,
              color: C.bone, textTransform: 'uppercase',
            }}>{c.t}</div>
            <div style={{
              fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.18em',
              color: C.bone, opacity: 0.78, textTransform: 'uppercase',
              display: 'flex', alignItems: 'center', gap: 6,
              justifyContent: c.side === 'R' ? 'flex-end' : 'flex-start',
            }}>
              {c.side === 'L' && <span style={{ fontSize: 12 }}>→</span>}
              <span>{c.sub}</span>
              {c.side === 'R' && <span style={{ fontSize: 12 }}>→</span>}
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}

function MobileBigType() {
  const C = useC();
  return (
    <section style={{
      background: C.ash, color: C.bone, position: 'relative', overflow: 'hidden',
      minHeight: '100dvh',
      display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
    }}>
      <MobileStamp left="002 / 07" right="WHAT IT IS" />
      <div style={{ padding: '40px 0' }}>
        <div style={{
          whiteSpace: 'nowrap', fontFamily: 'var(--display)',
          fontSize: 64, fontWeight: 900,
          letterSpacing: '-0.06em', lineHeight: 0.9,
          textTransform: 'uppercase', display: 'flex',
          animation: 'tryon-bigtype-marquee 8s linear infinite',
        }}>
          {[0, 1, 2, 3, 4, 5].map(i => (
            <span key={i} style={{ display: 'inline-flex', alignItems: 'center' }}>
              <span>3D AVATAR</span>
              <span style={{ WebkitTextStroke: `1.5px ${C.bone}`, color: 'transparent', padding: '0 0.25em' }}>EVERY BRAND</span>
              <span>ONE FIT</span>
              <span style={{ padding: '0 0.25em', color: C.dim }}>·</span>
            </span>
          ))}
        </div>
      </div>
      <div style={{
        borderTop: `1px solid ${C.faint}`, borderBottom: `1px solid ${C.faint}`,
        display: 'grid', gridTemplateColumns: '1fr 1fr 1fr',
      }}>
        {[
          { k: 'SETUP', v: <CountUp to={90} suffix="s" /> },
          { k: 'BRANDS', v: '∞' as ReactNode },
          { k: 'RETURNS', v: <><span>−</span><CountUp to={40} suffix="%" /></> },
        ].map((c, i) => (
          <div key={c.k} style={{
            padding: '20px 12px',
            borderRight: i < 2 ? `1px solid ${C.faint}` : 'none',
            display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
            gap: 12, minHeight: 110,
          }}>
            <div style={{
              fontFamily: 'var(--mono)', fontSize: 8, letterSpacing: '0.32em',
              color: C.dim, textTransform: 'uppercase',
            }}>{c.k}</div>
            <div style={{
              fontFamily: 'var(--display)', fontSize: 38, fontWeight: 900,
              letterSpacing: '-0.04em', color: C.bone, lineHeight: 0.9,
            }}>{c.v}</div>
          </div>
        ))}
      </div>
      <div style={{
        padding: '20px 16px 28px',
        display: 'grid', gridTemplateColumns: '1fr', gap: 14,
      }}>
        {[
          ['001 / BUILD', 'A rigged 3D avatar from 12 measurements. Built once. Yours forever.'],
          ['002 / REUSE', 'Drop into any TRYON brand. Real cloth physics. Real photography.'],
          ['003 / BUY', 'Confidence per SKU. Returns drop ~40%. Overproduction ends.'],
        ].map(([k, t]) => (
          <div key={k}>
            <div style={{
              fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.28em',
              color: C.dim, marginBottom: 6,
            }}>{k}</div>
            <p style={{ fontSize: 13, lineHeight: 1.45, margin: 0, color: C.bone, opacity: 0.92 }}>{t}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function MobileComponents() {
  const C = useC();
  const items: { n: string; tag: string; desc: string; image?: string }[] = [
    { n: '01', tag: 'FIT PASSPORT', desc: 'A 3D avatar of you, rigged.', image: '/redesign/fit-passport.jpg' },
    { n: '02', tag: 'GARMENT BIND', desc: 'Real cloth physics on real photography.', image: '/redesign/garment-bind.jpg' },
    { n: '03', tag: 'FIT REPORT', desc: 'Per-SKU confidence + size signal.' },
    { n: '04', tag: 'WIDGET', desc: '8 lines of code. Any brand.' },
  ];
  return (
    <section style={{
      background: C.void, color: C.bone,
      minHeight: '100dvh',
      display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
    }}>
      <MobileStamp left="003 / 07" right="COMPONENTS" />
      <div style={{ padding: '40px 16px 48px', flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <h2 style={{
          fontFamily: 'var(--display)', fontWeight: 900, margin: '0 0 24px',
          fontSize: 44, letterSpacing: '-0.04em', lineHeight: 0.86,
          textTransform: 'uppercase',
        }}>
          PRODUCT<br/>
          <span style={{ WebkitTextStroke: `1.5px ${C.bone}`, color: 'transparent' }}>BREAKDOWN</span>
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0, border: `1px solid ${C.faint}` }}>
          {items.map((it, i) => (
            <div key={it.n} style={{
              borderRight: i % 2 === 0 ? `1px solid ${C.faint}` : 'none',
              borderBottom: i < 2 ? `1px solid ${C.faint}` : 'none',
              background: C.ash,
            }}>
              <div style={{
                borderBottom: `1px solid ${C.faint}`,
                padding: '7px 9px',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                fontFamily: 'var(--mono)', fontSize: 8, letterSpacing: '0.24em',
                textTransform: 'uppercase', color: C.bone,
              }}>
                <span>{it.tag}</span>
                <span style={{ color: C.dim }}>{it.n}</span>
              </div>
              <div style={{
                aspectRatio: '4/5', background: C.steel, position: 'relative',
                display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
              }}>
                {it.image ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={it.image}
                    alt={it.tag}
                    style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                  />
                ) : (
                  <>
                    <SlitLight count={10} opacity={0.45} />
                    <span style={{
                      position: 'relative', zIndex: 2,
                      fontFamily: 'var(--mono)', fontSize: 8, letterSpacing: '0.24em',
                      color: C.dim, padding: '3px 6px', border: `1px solid ${C.faint}`,
                    }}>TBD</span>
                  </>
                )}
              </div>
              <div style={{
                borderTop: `1px solid ${C.faint}`, padding: '8px 9px',
                fontSize: 10.5, lineHeight: 1.4, color: C.bone, opacity: 0.85,
              }}>{it.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function MobileProof() {
  const C = useC();
  return (
    <section style={{
      background: C.ash, color: C.bone, position: 'relative', overflow: 'hidden',
      minHeight: '100dvh',
      display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
    }}>
      <MobileStamp left="004 / 07" right="LIVE TRACTION" />
      <div style={{ padding: '40px 16px 48px', position: 'relative', flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <SlitLight count={18} opacity={0.3} />
        <div style={{
          fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.24em',
          color: C.dim, marginBottom: 16, textTransform: 'uppercase',
          position: 'relative', zIndex: 2,
        }}>RAMIN STUDIOS · AMSTERDAM · 14 DAYS</div>

        <h2 style={{
          fontFamily: 'var(--display)', fontWeight: 900,
          fontSize: 160, letterSpacing: '-0.07em', lineHeight: 0.8, margin: 0,
          textTransform: 'uppercase', position: 'relative', zIndex: 2, color: C.bone,
        }}>
          <CountUp to={94} duration={1800} /><span style={{ WebkitTextStroke: `2px ${C.bone}`, color: 'transparent' }}>%</span>
        </h2>
        <p style={{
          fontSize: 15, fontWeight: 600, lineHeight: 1.3, margin: '12px 0 24px',
          letterSpacing: '-0.02em', position: 'relative', zIndex: 2, color: C.bone,
        }}>
          of widget opens convert to a try-on.<br/>
          <span style={{ color: C.dim }}>Live data. Last 14 days.</span>
        </p>
        <div style={{ border: `1px solid ${C.faint}`, position: 'relative', zIndex: 2 }}>
          {[
            { k: 'OPENS', node: <CountUp to={100} /> },
            { k: 'TRY-ONS', node: <CountUp to={94} /> },
            { k: 'ATC', node: <CountUp to={34} /> },
            { k: 'AVG SESSION', node: <><CountUp to={38} />s</> },
          ].map((row, i, arr) => (
            <div key={row.k} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
              padding: '10px 12px',
              borderBottom: i < arr.length - 1 ? `1px solid ${C.faint}` : 'none',
              background: C.steel,
            }}>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.24em', color: C.dim }}>{row.k}</span>
              <span style={{ fontFamily: 'var(--display)', fontSize: 18, fontWeight: 800, letterSpacing: '-0.02em', color: C.bone }}>{row.node}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function MobileCarbon() {
  const C = useC();
  const rows = [
    { k: 'RETURNS AVOIDED', v: 40, suffix: '%', sub: 'less reverse logistics, less landfill.' },
    { k: 'OVERPRODUCTION CUT', v: 18, suffix: '%', sub: 'closer to real demand.' },
    { k: 'CO₂E PER ORDER', v: 2.4, suffix: 'kg', sub: 'saved when a return is prevented.', decimals: 1 },
  ];
  return (
    <section style={{
      background: C.void, color: C.bone, position: 'relative', overflow: 'hidden',
      minHeight: '100dvh',
      display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
    }}>
      <MobileStamp left="005 / 07" right="WASTE LEDGER" />
      <SlitLight count={20} opacity={0.3} />
      <div style={{ padding: '40px 16px 48px', position: 'relative', zIndex: 2, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <div style={{
          fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.32em',
          color: C.dim, textTransform: 'uppercase', marginBottom: 16,
        }}>— THE INDUSTRY&apos;S DIRTIEST SECRET —</div>
        <h2 style={{
          fontFamily: 'var(--display)', fontWeight: 900,
          fontSize: 44, letterSpacing: '-0.04em',
          lineHeight: 0.86, margin: '0 0 16px', textTransform: 'uppercase',
        }}>
          FIT IS A<br/>
          <span style={{ WebkitTextStroke: `1.5px ${C.bone}`, color: 'transparent' }}>CLIMATE</span><br/>
          PROBLEM.
        </h2>
        <p style={{ fontSize: 13, lineHeight: 1.5, margin: '0 0 22px', color: C.bone, opacity: 0.85 }}>
          Online apparel returns over 30% of what ships — most because of fit, most never resold. TRYON kills the return before the order.
        </p>
        <div style={{ border: `1px solid ${C.faint}`, background: C.steel }}>
          <div style={{
            borderBottom: `1px solid ${C.faint}`,
            padding: '8px 12px',
            display: 'flex', justifyContent: 'space-between',
            fontFamily: 'var(--mono)', fontSize: 8, letterSpacing: '0.28em',
            textTransform: 'uppercase', color: C.dim,
          }}>
            <span style={{ color: C.bone }}>WASTE LEDGER</span>
            <span>PER 1,000 ORDERS</span>
          </div>
          {rows.map((r, i) => (
            <div key={r.k} style={{
              padding: '12px 12px',
              borderBottom: i < rows.length - 1 ? `1px solid ${C.faint}` : 'none',
            }}>
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4,
              }}>
                <span style={{ fontFamily: 'var(--mono)', fontSize: 8, letterSpacing: '0.24em', color: C.dim }}>{r.k}</span>
                <span style={{
                  fontFamily: 'var(--display)', fontSize: 22, fontWeight: 900,
                  letterSpacing: '-0.03em', color: C.bone, lineHeight: 1,
                }}>
                  <span>−</span><CountUp to={r.v} decimals={r.decimals || 0} />{r.suffix}
                </span>
              </div>
              <div style={{ fontSize: 10.5, lineHeight: 1.35, color: C.bone, opacity: 0.7 }}>{r.sub}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function MobileBehind() {
  const C = useC();
  return (
    <section style={{
      background: C.void, color: C.bone,
      minHeight: '100dvh',
      display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
    }}>
      <MobileStamp left="006 / 07" right="BEHIND THE LOGIN" />
      <div style={{ padding: '40px 16px 48px', flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <h2 style={{
          fontFamily: 'var(--display)', fontWeight: 900,
          fontSize: 44, letterSpacing: '-0.04em',
          lineHeight: 0.86, margin: '0 0 16px', textTransform: 'uppercase',
        }}>
          ONE LOGIN.<br/>
          <span style={{ WebkitTextStroke: `1.5px ${C.bone}`, color: 'transparent' }}>EVERY</span> BRAND.
        </h2>
        <p style={{ fontSize: 13, lineHeight: 1.5, margin: '0 0 20px', color: C.bone, opacity: 0.8 }}>
          Free for shoppers. Forever. Your fit passport, your closet, every garment you&apos;ve ever tried, synced across every TRYON brand.
        </p>
        <div style={{
          border: `1px solid ${C.faint}`, background: C.steel,
          aspectRatio: '4/5', position: 'relative',
          display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
        }}>
          <SlitLight count={22} opacity={0.4} />
          <span style={{
            position: 'relative', zIndex: 2,
            fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.24em',
            color: C.dim, padding: '4px 7px', border: `1px solid ${C.faint}`,
          }}>IMAGE TBD</span>
          <div style={{
            position: 'absolute', top: 8, left: 8, zIndex: 3,
            background: C.bone, color: C.void,
            fontFamily: 'var(--mono)', fontSize: 8, letterSpacing: '0.22em',
            textTransform: 'uppercase', fontWeight: 700,
            padding: '4px 6px',
          }}>WISHLIST</div>
        </div>
      </div>
    </section>
  );
}

function MobileCTA() {
  const C = useC();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const submit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = email.trim();
    router.push(trimmed ? `/signup?email=${encodeURIComponent(trimmed)}` : '/signup');
  };

  return (
    <section style={{
      background: C.ash, color: C.bone, position: 'relative', overflow: 'hidden',
      minHeight: '100dvh',
      display: 'flex', flexDirection: 'column',
    }}>
      <MobileStamp left="007 / 07" right="ENTER" />
      <SlitLight count={28} opacity={0.35} />
      <div style={{ padding: '48px 16px 96px', flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', position: 'relative' }}>

      <div style={{
        fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.32em',
        color: C.dim, textTransform: 'uppercase', textAlign: 'center',
        marginBottom: 16, position: 'relative', zIndex: 2,
      }}>FREE FOREVER · NO MEASUREMENT FORM</div>

      <h2 style={{
        fontFamily: 'var(--display)', fontWeight: 900,
        fontSize: 52, letterSpacing: '-0.05em',
        lineHeight: 0.86, margin: '0 0 14px', textAlign: 'center',
        textTransform: 'uppercase', position: 'relative', zIndex: 2,
      }}>
        BUILD YOUR<br/>
        <span style={{ WebkitTextStroke: `1.5px ${C.bone}`, color: 'transparent' }}>FIT PASSPORT.</span>
      </h2>

      <p style={{
        textAlign: 'center', fontSize: 14, lineHeight: 1.4,
        margin: '0 auto 28px', maxWidth: 320, color: C.dim, fontWeight: 500,
        position: 'relative', zIndex: 2,
      }}>
        90 seconds. 12 measurements. One avatar.
      </p>

      <div style={{
        background: C.cardBg, color: C.cardInk,
        border: `1px solid ${C.bone}`,
        boxShadow: '0 16px 40px rgba(0,0,0,0.18)',
        position: 'relative', zIndex: 2,
      }}>
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '10px 14px',
          borderBottom: `1px solid ${C.cardHair}`,
          fontFamily: 'var(--mono)', fontSize: 8, letterSpacing: '0.28em',
          textTransform: 'uppercase', color: C.cardDim,
        }}>
          <span style={{ color: C.cardInk }}>SHOPPER · ENTRY</span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <span style={{
              width: 6, height: 6, borderRadius: '50%', background: '#7CFFA1',
              boxShadow: '0 0 8px #7CFFA1',
            }} />
            ACCEPTING
          </span>
        </div>
        <form onSubmit={submit} style={{ display: 'grid', gridTemplateRows: 'auto auto', gap: 0 }}>
          <input
            type="email"
            placeholder="you@email.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{
              background: 'transparent', border: 'none', outline: 'none',
              padding: '18px 16px',
              fontFamily: 'var(--display)', fontSize: 18, fontWeight: 600,
              letterSpacing: '-0.01em', color: C.cardInk,
              borderBottom: `1px solid ${C.cardHair}`,
            }}
          />
          <button
            type="submit"
            style={{
              background: C.cardInk, color: C.cardBg,
              padding: '16px', minHeight: 52,
              fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.28em',
              textTransform: 'uppercase', fontWeight: 800, border: 'none',
              cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
            }}
          >
            GET MY PASSPORT
            <span style={{ fontSize: 14 }}>→</span>
          </button>
        </form>
      </div>

      <div style={{
        marginTop: 18, textAlign: 'center', position: 'relative', zIndex: 2,
        fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.28em',
        color: C.dim, textTransform: 'uppercase',
      }}>
        ARE YOU A BRAND?{' '}
        <button
          onClick={() => router.push('/signup?type=brand')}
          style={{
            color: C.bone, borderBottom: `1px solid ${C.bone}`,
            paddingBottom: 2, background: 'none', border: 'none',
            borderBottomWidth: 1, borderBottomStyle: 'solid',
            fontFamily: 'inherit', fontSize: 'inherit', letterSpacing: 'inherit',
            textTransform: 'inherit', cursor: 'pointer',
          }}
        >BOOK A DEMO →</button>
      </div>
      </div>
    </section>
  );
}

/* ─────── Root ─────── */
export function BroadcastLanding({ dark = false }: { dark?: boolean }) {
  const C = dark ? PAL.dark : PAL.light;
  const mobile = useIsMobile();
  return (
    <ThemeCtx.Provider value={C}>
      <div className="tryon-redesign-root" style={{
        width: '100%', minHeight: '100vh',
        background: C.void, color: C.bone, position: 'relative',
      }}>
        {mobile ? (
          <>
            <MobileNav />
            <MobileHero />
            <MobileBigType />
            <MobileComponents />
            <MobileProof />
            <MobileCarbon />
            <MobileBehind />
            <MobileCTA />
          </>
        ) : (
          <>
            <DesktopNav />
            <DesktopHero />
            <DesktopBigType />
            <DesktopProductGrid />
            <DesktopProofBig />
            <DesktopCarbon />
            <DesktopBehind />
            <DesktopCTA />
          </>
        )}
      </div>
    </ThemeCtx.Provider>
  );
}
