'use client';

import React, { createContext, useContext, useEffect, useRef, useState, ReactNode, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useIsMobile } from './useIsMobile';

const PAL = {
  light: {
    void: '#ffffff', ash: '#fafafa', steel: '#f5f4ef', iron: '#ebebe5',
    bone: '#0A0A0A', dim: '#6E6E6E', faint: '#D8D4C9',
    slit: 'rgba(0,0,0,0.07)',
    cardBg: '#0A0A0A', cardInk: '#F2F1EC',
    cardHair: 'rgba(255,255,255,0.12)', cardDim: '#9A9A9A',
    accent: '#0A0A0A',
  },
  dark: {
    void: '#0A0A0A', ash: '#0E0E0E', steel: '#141414', iron: '#1A1A1A',
    bone: '#F2F1EC', dim: '#8A8A8A', faint: '#252525',
    slit: 'rgba(255,255,255,0.05)',
    cardBg: '#F2F1EC', cardInk: '#0A0A0A',
    cardHair: 'rgba(0,0,0,0.12)', cardDim: '#6E6E6E',
    accent: '#F2F1EC',
  },
};
type Palette = typeof PAL.light;
const ThemeCtx = createContext<Palette>(PAL.light);
const useC = () => useContext(ThemeCtx);

/* ─── helpers ─── */
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
        if (y < 100) { downAccum = 0; setHidden(false); return; }
        if (dy < 0) { downAccum = 0; setHidden(false); return; }
        downAccum += dy;
        if (downAccum > 60) setHidden(true);
      });
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  return hidden;
}

/* ─── Nav ─── */
function DesktopNav() {
  const C = useC();
  const router = useRouter();
  const hidden = useSmartNav();

  const cap: React.CSSProperties = {
    background: C.bone === '#0A0A0A' ? 'rgba(255,255,255,0.78)' : 'rgba(10,10,10,0.72)',
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
        <div style={{ display: 'flex', gap: 22 }}>
          {[
            { label: 'PRICING', href: '/pricing' },
            { label: 'FOR SHOPPERS', href: '/signup' },
            { label: 'DECK', href: '/pitch-deck.html', external: true },
          ].map(it => (
            <button
              key={it.label}
              onClick={() => {
                if (it.external) window.open(it.href, '_blank', 'noopener');
                else router.push(it.href);
              }}
              style={{
                border: 0, padding: 0, background: 'transparent', cursor: 'pointer',
                fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
                color: C.dim, textTransform: 'uppercase', fontWeight: 500,
              }}
            >{it.label}</button>
          ))}
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
          onClick={() => router.push('/demo')}
          style={{
            padding: '9px 16px',
            background: C.bone, color: C.void, border: 'none',
            fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
            textTransform: 'uppercase', fontWeight: 700, cursor: 'pointer',
            display: 'inline-flex', alignItems: 'center', gap: 8, borderRadius: 999,
          }}
        >TRY IT NOW<span style={{ fontSize: 12 }}>→</span></button>
      </div>
    </div>
  );
}

/* ─── Hero: massive headline + immediate CTA + path split ─── */
function DesktopHero() {
  const C = useC();
  const router = useRouter();

  return (
    <section style={{
      background: `radial-gradient(ellipse at 50% 110%, ${C.iron} 0%, ${C.ash} 35%, ${C.void} 80%)`,
      color: C.bone, position: 'relative',
      minHeight: '100dvh', overflow: 'hidden',
      padding: '56px 32px 0',
      display: 'flex', flexDirection: 'column',
    }}>
      <SlitLight count={56} opacity={0.5} />

      <div style={{
        position: 'relative', zIndex: 4,
        marginTop: 'auto', marginBottom: 0, paddingBottom: 48,
        display: 'flex', flexDirection: 'column', alignItems: 'center',
      }}>
        <div style={{
          fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.4em',
          color: C.dim, textTransform: 'uppercase',
          marginBottom: 18, textAlign: 'center',
        }}>BUILT FOR THE 2026 EU FASHION RULEBOOK.</div>

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

        <p style={{
          marginTop: 28, marginBottom: 36,
          fontSize: 17, lineHeight: 1.45, maxWidth: 560,
          textAlign: 'center', color: C.bone, opacity: 0.78, fontWeight: 500,
        }}>
          One avatar. Every brand. Real cloth, real measurements, real fit. The first virtual try-on built for the 2026 to 2028 EU regulatory wave.
        </p>

        <button
          onClick={() => router.push('/demo')}
          style={{
            background: C.bone, color: C.void, border: 'none',
            padding: '22px 36px',
            fontFamily: 'var(--mono)', fontSize: 13, letterSpacing: '0.32em',
            textTransform: 'uppercase', fontWeight: 800, cursor: 'pointer',
            display: 'inline-flex', alignItems: 'center', gap: 14,
            borderRadius: 999,
            boxShadow: '0 24px 64px rgba(10,10,10,0.18)',
          }}
        >
          TRY THE DEMO
          <span style={{ fontSize: 18 }}>→</span>
        </button>

        <div style={{
          marginTop: 24,
          fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.28em',
          color: C.dim, textTransform: 'uppercase', textAlign: 'center',
        }}>
          NO SIGNUP. NO MEASUREMENT. INSTANT.
        </div>
      </div>

      <div style={{
        position: 'relative', zIndex: 5,
        borderTop: `1px solid ${C.faint}`,
        display: 'grid', gridTemplateColumns: '1fr 1fr',
        marginLeft: -32, marginRight: -32,
      }}>
        <HeroPath
          tag="FOR BRANDS"
          title="I AM A BRAND"
          sub="See pricing. Cut returns."
          onClick={() => router.push('/pricing')}
          align="left"
          C={C}
        />
        <HeroPath
          tag="FOR SHOPPERS"
          title="I AM A SHOPPER"
          sub="Build your fit passport. Free, forever."
          onClick={() => router.push('/signup')}
          align="right"
          C={C}
          first
        />
      </div>
    </section>
  );
}

function HeroPath({ tag, title, sub, onClick, align, C, first }: {
  tag: string; title: string; sub: string; onClick: () => void;
  align: 'left' | 'right'; C: Palette; first?: boolean;
}) {
  const [hover, setHover] = useState(false);
  const ink = hover ? C.void : C.bone;
  const tagColor = hover ? C.void : C.dim;
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        padding: '22px 28px 20px',
        borderRight: !first ? `1px solid ${C.faint}` : 'none',
        display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
        gap: 14, minHeight: 116,
        background: hover ? C.bone : 'transparent',
        cursor: 'pointer', border: 'none',
        textAlign: align,
        color: ink,
        transition: 'background 0.18s ease, color 0.18s ease',
      }}
    >
      <div style={{
        fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.4em',
        color: tagColor, textTransform: 'uppercase',
        transition: 'color 0.18s ease',
      }}>{tag}</div>
      <div style={{
        display: 'flex', alignItems: 'baseline', justifyContent: 'space-between',
        flexDirection: align === 'right' ? 'row-reverse' : 'row', gap: 16,
      }}>
        <h3 style={{
          fontFamily: 'var(--display)', fontWeight: 900,
          fontSize: 'clamp(28px, 3.8vw, 56px)', letterSpacing: '-0.04em',
          lineHeight: 0.92, margin: 0, color: ink,
          textTransform: 'uppercase',
        }}>{title}</h3>
        <span style={{
          fontFamily: 'var(--display)', fontSize: 36, fontWeight: 900,
          color: ink, lineHeight: 1,
          transform: align === 'right' ? 'none' : 'rotate(180deg)',
        }}>→</span>
      </div>
      <div style={{
        fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.18em',
        color: ink, opacity: 0.78, textTransform: 'uppercase',
      }}>{sub}</div>
    </button>
  );
}

/* ─── Components: 3 pieces of the protocol ─── */
function DesktopComponents() {
  const C = useC();
  const items = [
    { n: '01', tag: 'FIT PASSPORT', desc: 'A 3D avatar of you, rigged from 12 measurements. Built once. Yours forever.', image: '/redesign/fit-passport.jpg' },
    { n: '02', tag: 'GARMENT BIND', desc: 'Real cloth physics on real product photography. Every body shape, not just sample size.', image: '/redesign/garment-bind.jpg' },
    { n: '03', tag: 'FIT REPORT', desc: 'Per-SKU confidence and size signal. The brand knows what fits and what does not.', image: '/redesign/fit-report.jpg' },
  ];
  return (
    <section style={{
      background: C.void, color: C.bone, position: 'relative',
      padding: '120px 32px',
    }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <div style={{
          fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.4em',
          color: C.dim, textTransform: 'uppercase', marginBottom: 24,
        }}>THE PROTOCOL</div>
        <h2 style={{
          fontFamily: 'var(--display)', fontWeight: 900, margin: '0 0 64px',
          fontSize: 'clamp(56px, 8vw, 128px)', letterSpacing: '-0.05em', lineHeight: 0.84,
          textTransform: 'uppercase', maxWidth: 980,
        }}>
          ONE PROTOCOL.<br/>
          <span style={{ WebkitTextStroke: `2px ${C.bone}`, color: 'transparent' }}>THREE PIECES.</span>
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24 }}>
          {items.map(it => (
            <div key={it.n} style={{
              border: `1px solid ${C.faint}`,
              background: C.ash,
              display: 'flex', flexDirection: 'column',
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
                aspectRatio: '4/5', background: '#ffffff',
                display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
                padding: 24, boxSizing: 'border-box',
              }}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={it.image} alt={it.tag} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', display: 'block' }} />
              </div>
              <div style={{
                borderTop: `1px solid ${C.faint}`, padding: '20px 20px',
                fontSize: 14, lineHeight: 1.5, color: C.bone, opacity: 0.85,
              }}>{it.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── Evidence: pilot proof + climate stats + EU rulebook ─── */
function DesktopEvidence() {
  const C = useC();
  const wasteRows = [
    { k: 'RETURNS AVOIDED', v: 40, suffix: '%', sub: 'less reverse logistics, less landfill.' },
    { k: 'OVERPRODUCTION CUT', v: 18, suffix: '%', sub: 'brands manufacture closer to real demand.' },
    { k: 'CO₂E PER ORDER', v: 2.4, suffix: 'kg', sub: 'avg saved when a return is prevented.', decimals: 1 },
  ];
  const rulebook = [
    { date: 'JUL 2026', title: 'EU bans destruction of unsold apparel.', sub: 'Central Digital Product Passport registry goes live.' },
    { date: 'SEP 2026', title: 'ECGT applies. Anti-greenwashing.', sub: 'Words like "sustainable" become regulated. Claims need proof.' },
    { date: '2028', title: 'DPP mandatory for textiles.', sub: 'Every garment sold in the EU carries a digital twin.' },
  ];
  return (
    <section style={{
      background: C.ash, color: C.bone, position: 'relative', overflow: 'hidden',
      padding: '120px 32px',
    }}>
      <SlitLight count={56} opacity={0.32} />
      <div style={{ position: 'relative', zIndex: 2, maxWidth: 1280, margin: '0 auto' }}>
        <div style={{
          fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.4em',
          color: C.dim, textTransform: 'uppercase', marginBottom: 24,
        }}>WHY NOW</div>

        <h2 style={{
          fontFamily: 'var(--display)', fontWeight: 900,
          fontSize: 'clamp(56px, 8vw, 128px)', letterSpacing: '-0.05em',
          lineHeight: 0.84, margin: '0 0 56px', textTransform: 'uppercase', maxWidth: 980,
        }}>
          FIT IS A<br/>
          <span style={{ WebkitTextStroke: `2px ${C.bone}`, color: 'transparent' }}>CLIMATE</span>{' '}
          PROBLEM.
        </h2>

        <div style={{
          display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 56, alignItems: 'start',
        }}>
          <div>
            <p style={{ fontSize: 17, lineHeight: 1.55, margin: '0 0 18px', color: C.bone, opacity: 0.92, maxWidth: 560 }}>
              70% of fashion returns are caused by fit. (McKinsey, 2024.) In 2022, 9.5 billion pounds of US returns went to landfill, emitting 24 million tonnes of CO₂. (Optoro.)
            </p>
            <p style={{ fontSize: 17, lineHeight: 1.55, margin: '0 0 36px', color: C.bone, opacity: 0.92, maxWidth: 560 }}>
              TRYON kills the return before the order. Fewer trucks. Less plastic. Less polyester pulled out of the ground for stock that nobody wears.
            </p>

            <div style={{
              display: 'grid', gridTemplateColumns: '1.2fr 1fr',
              border: `1px solid ${C.faint}`, background: C.steel, marginBottom: 36,
            }}>
              <div style={{
                padding: '32px 28px',
                borderRight: `1px solid ${C.faint}`,
                display: 'flex', flexDirection: 'column', justifyContent: 'center',
              }}>
                <div style={{
                  fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
                  color: C.dim, textTransform: 'uppercase', marginBottom: 8,
                }}>RAMIN STUDIOS PILOT, AMSTERDAM</div>
                <h3 style={{
                  fontFamily: 'var(--display)', fontWeight: 900,
                  fontSize: 96, letterSpacing: '-0.05em', lineHeight: 0.85,
                  margin: 0, color: C.bone,
                }}>
                  <CountUp to={94} />
                  <span style={{ WebkitTextStroke: `2px ${C.bone}`, color: 'transparent' }}>%</span>
                </h3>
                <div style={{ fontSize: 13, lineHeight: 1.4, color: C.dim, marginTop: 8 }}>
                  of widget opens convert to a try-on.<br/>
                  Live data, last 14 days.
                </div>
              </div>
              <div>
                {[
                  { k: 'OPENS', node: <CountUp to={100} /> },
                  { k: 'TRY-ONS', node: <CountUp to={94} /> },
                  { k: 'ATC', node: <CountUp to={34} /> },
                  { k: 'AVG SESSION', node: <><CountUp to={38} />s</> },
                ].map((row, i, arr) => (
                  <div key={row.k} style={{
                    display: 'grid', gridTemplateColumns: '1fr 1fr',
                    padding: '12px 18px', alignItems: 'baseline',
                    borderBottom: i < arr.length - 1 ? `1px solid ${C.faint}` : 'none',
                  }}>
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em', color: C.dim }}>{row.k}</span>
                    <span style={{ fontFamily: 'var(--display)', fontSize: 20, fontWeight: 800, letterSpacing: '-0.02em', textAlign: 'right', color: C.bone }}>{row.node}</span>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ border: `1px solid ${C.faint}`, background: C.steel }}>
              <div style={{
                borderBottom: `1px solid ${C.faint}`, padding: '14px 20px',
                display: 'flex', justifyContent: 'space-between',
                fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
                textTransform: 'uppercase', color: C.dim,
              }}>
                <span style={{ color: C.bone }}>WASTE LEDGER</span>
                <span>PER 1,000 ORDERS</span>
              </div>
              {wasteRows.map((r, i) => (
                <div key={r.k} style={{
                  padding: '18px 20px',
                  borderBottom: i < wasteRows.length - 1 ? `1px solid ${C.faint}` : 'none',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4 }}>
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em', color: C.dim }}>{r.k}</span>
                    <span style={{
                      fontFamily: 'var(--display)', fontSize: 32, fontWeight: 900,
                      letterSpacing: '-0.04em', color: C.bone, lineHeight: 1,
                    }}>
                      <span>−</span><CountUp to={r.v} decimals={r.decimals || 0} />{r.suffix}
                    </span>
                  </div>
                  <div style={{ fontSize: 13, lineHeight: 1.4, color: C.bone, opacity: 0.7 }}>{r.sub}</div>
                </div>
              ))}
              <div style={{
                padding: '12px 20px',
                borderTop: `1px solid ${C.faint}`,
                fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.28em',
                color: C.dim, textTransform: 'uppercase',
              }}>SOURCES · MCKINSEY 2024 · OPTORO 2022 · TRYON RAMIN PILOT 2026</div>
            </div>
          </div>

          <div>
            <div style={{
              fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.32em',
              color: C.dim, textTransform: 'uppercase', marginBottom: 18,
            }}>THE EU RULEBOOK · 2026 TO 2028</div>
            <div style={{ border: `1px solid ${C.faint}`, background: C.steel }}>
              {rulebook.map((r, i) => (
                <div key={r.date} style={{
                  padding: '24px 24px',
                  borderBottom: i < rulebook.length - 1 ? `1px solid ${C.faint}` : 'none',
                }}>
                  <div style={{
                    fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.32em',
                    color: C.bone, textTransform: 'uppercase', marginBottom: 8, fontWeight: 700,
                  }}>{r.date}</div>
                  <div style={{
                    fontFamily: 'var(--display)', fontSize: 22, fontWeight: 800,
                    letterSpacing: '-0.02em', color: C.bone, lineHeight: 1.2, marginBottom: 6,
                  }}>{r.title}</div>
                  <div style={{ fontSize: 13, lineHeight: 1.5, color: C.bone, opacity: 0.7 }}>{r.sub}</div>
                </div>
              ))}
            </div>
            <p style={{
              fontSize: 14, lineHeight: 1.55, marginTop: 20, color: C.bone, opacity: 0.78,
            }}>
              Every garment we render is already a 3D digital twin. DPP-ready by design. While other VTO vendors will be deleting "sustainable" from their landing pages in September, we will be quoting the regulation.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── For Brands: comparison + integration code + pricing teaser ─── */
function DesktopBrands() {
  const C = useC();
  const router = useRouter();
  const cmp = [
    {
      name: 'GOOGLE VTO',
      bullets: ['Flat 2D image generation.', 'No body measurements.', 'Happens on Google. Brand loses the data.'],
      muted: true,
    },
    {
      name: 'TRUE FIT',
      bullets: ['Size recommendation only.', 'No 3D, no avatar.', '$10K to $50K/mo enterprise.'],
      muted: true,
    },
    {
      name: 'TRYON',
      bullets: ['Real 3D avatar, real cloth physics.', 'Per-SKU fit confidence.', 'Brand keeps the data and the PDP.'],
      muted: false,
    },
  ];
  const tiers = [
    { name: 'FREE', price: '$0', sub: '200 sessions', cta: 'Start free' },
    { name: 'STUDIO', price: '$149', sub: '2,500 sessions', cta: 'Start' },
    { name: 'BRAND', price: '$2,490', sub: '40,000 sessions', cta: 'Start' },
    { name: 'SCALE', price: 'Talk to us', sub: 'Multi-brand, custom', cta: 'Book a call' },
  ];
  return (
    <section style={{
      background: C.void, color: C.bone, padding: '120px 32px',
    }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <div style={{
          fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.4em',
          color: C.dim, textTransform: 'uppercase', marginBottom: 24,
        }}>FOR BRANDS</div>
        <h2 style={{
          fontFamily: 'var(--display)', fontWeight: 900, margin: '0 0 24px',
          fontSize: 'clamp(56px, 8vw, 128px)', letterSpacing: '-0.05em', lineHeight: 0.84,
          textTransform: 'uppercase', maxWidth: 1100,
        }}>
          PAY LESS THAN<br/>
          <span style={{ WebkitTextStroke: `2px ${C.bone}`, color: 'transparent' }}>ONE RETURN</span> A DAY.
        </h2>
        <p style={{ fontSize: 17, lineHeight: 1.55, margin: '0 0 64px', color: C.bone, opacity: 0.78, maxWidth: 720 }}>
          Built for Shopify Plus fashion brands losing six figures a month to returns. Save tens of thousands per month, charged less than the cost of one return per day.
        </p>

        {/* Comparison */}
        <div style={{ marginBottom: 80 }}>
          <div style={{
            fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
            color: C.dim, textTransform: 'uppercase', marginBottom: 16,
          }}>WHY TRYON</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 0, border: `1px solid ${C.faint}` }}>
            {cmp.map((col, i) => (
              <div key={col.name} style={{
                background: col.muted ? C.steel : C.bone,
                color: col.muted ? C.bone : C.void,
                padding: '32px 28px',
                borderRight: i < cmp.length - 1 ? `1px solid ${C.faint}` : 'none',
                display: 'flex', flexDirection: 'column', gap: 18,
              }}>
                <div style={{
                  fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.32em',
                  textTransform: 'uppercase', fontWeight: 700,
                  color: col.muted ? C.dim : C.void, opacity: col.muted ? 1 : 0.65,
                }}>{col.name}</div>
                <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {col.bullets.map(b => (
                    <li key={b} style={{
                      fontSize: 14, lineHeight: 1.45, fontWeight: col.muted ? 400 : 600,
                      color: col.muted ? C.bone : C.void, opacity: col.muted ? 0.8 : 1,
                    }}>{b}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Integration */}
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1.4fr', gap: 56, alignItems: 'center',
          marginBottom: 80,
        }}>
          <div>
            <div style={{
              fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
              color: C.dim, textTransform: 'uppercase', marginBottom: 12,
            }}>SHOPIFY INTEGRATION</div>
            <h3 style={{
              fontFamily: 'var(--display)', fontWeight: 900, margin: '0 0 14px',
              fontSize: 'clamp(36px, 4.5vw, 64px)', letterSpacing: '-0.04em', lineHeight: 0.9,
              textTransform: 'uppercase',
            }}>
              8 LINES.<br/>LIVE IN A WEEK.
            </h3>
            <p style={{ fontSize: 14, lineHeight: 1.55, margin: 0, color: C.bone, opacity: 0.78, maxWidth: 380 }}>
              Drop the theme block onto any Shopify store. Embed the widget on your PDP. The widget fetches a fit report from our API. No SDK install, no model upload, no agency.
            </p>
          </div>
          <pre style={{
            background: C.cardBg, color: C.cardInk,
            padding: '28px 32px',
            fontFamily: 'var(--mono)', fontSize: 13, lineHeight: 1.6,
            border: `1px solid ${C.bone}`,
            margin: 0, overflowX: 'auto',
            boxShadow: '0 24px 64px rgba(10,10,10,0.18)',
          }}>{`{% comment %} TryOn widget block {% endcomment %}
<div id="tryon-widget"
     data-shop="{{ shop.permanent_domain }}"
     data-product="{{ product.id }}"
     data-variant="{{ product.selected_variant.id }}">
</div>
<script src="https://cdn.tryon.global/v1/widget.js" defer>
</script>`}</pre>
        </div>

        {/* Pricing teaser */}
        <div>
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
            marginBottom: 18,
          }}>
            <div style={{
              fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
              color: C.dim, textTransform: 'uppercase',
            }}>PRICING</div>
            <button
              onClick={() => router.push('/pricing')}
              style={{
                background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.32em',
                color: C.bone, textTransform: 'uppercase', fontWeight: 700,
                borderBottom: `1px solid ${C.bone}`, paddingBottom: 2,
              }}
            >SEE FULL PRICING →</button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 0, border: `1px solid ${C.faint}` }}>
            {tiers.map((t, i) => (
              <button
                key={t.name}
                onClick={() => router.push('/pricing')}
                style={{
                  background: C.ash,
                  borderRight: i < tiers.length - 1 ? `1px solid ${C.faint}` : 'none',
                  border: 'none',
                  padding: '32px 24px',
                  textAlign: 'left',
                  cursor: 'pointer',
                  display: 'flex', flexDirection: 'column', gap: 14,
                  color: C.bone,
                }}
              >
                <div style={{
                  fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
                  color: C.dim, textTransform: 'uppercase', fontWeight: 700,
                }}>{t.name}</div>
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 36, fontWeight: 900,
                  letterSpacing: '-0.03em', lineHeight: 1, color: C.bone,
                }}>{t.price}</div>
                <div style={{
                  fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.18em',
                  color: C.dim, textTransform: 'uppercase',
                }}>{t.sub}</div>
                <div style={{
                  marginTop: 'auto',
                  fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.28em',
                  color: C.bone, textTransform: 'uppercase', fontWeight: 700,
                  display: 'flex', alignItems: 'center', gap: 6,
                }}>{t.cta} <span>→</span></div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── For Shoppers: closet + email CTA ─── */
function DesktopShoppers() {
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
      background: C.ash, color: C.bone, padding: '120px 32px', position: 'relative', overflow: 'hidden',
    }}>
      <SlitLight count={56} opacity={0.32} />
      <div style={{ maxWidth: 1280, margin: '0 auto', position: 'relative', zIndex: 2 }}>
        <div style={{
          fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.4em',
          color: C.dim, textTransform: 'uppercase', marginBottom: 24,
        }}>FOR SHOPPERS</div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 56, alignItems: 'center' }}>
          <div>
            <h2 style={{
              fontFamily: 'var(--display)', fontWeight: 900, margin: '0 0 20px',
              fontSize: 'clamp(56px, 7vw, 112px)', letterSpacing: '-0.05em', lineHeight: 0.86,
              textTransform: 'uppercase',
            }}>
              ONE LOGIN.<br/>
              <span style={{ WebkitTextStroke: `2px ${C.bone}`, color: 'transparent' }}>EVERY</span> BRAND.
            </h2>
            <p style={{ fontSize: 16, lineHeight: 1.55, margin: '0 0 32px', color: C.bone, opacity: 0.85, maxWidth: 480 }}>
              Free, forever. Build your fit passport once. Wear every garment we host across every brand on Earth. Build outfits, save what you love, see what fits before you check out.
            </p>

            <div style={{
              background: C.cardBg, color: C.cardInk,
              border: `1px solid ${C.bone}`,
              boxShadow: '0 24px 64px rgba(0,0,0,0.18)',
              maxWidth: 520,
            }}>
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '14px 20px',
                borderBottom: `1px solid ${C.cardHair}`,
                fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
                textTransform: 'uppercase', color: C.cardDim,
              }}>
                <span style={{ color: C.cardInk }}>SHOPPER ENTRY</span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#7CFFA1', boxShadow: '0 0 12px #7CFFA1' }} />
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
                >GET MY PASSPORT <span style={{ fontSize: 16 }}>→</span></button>
              </form>
            </div>
          </div>

          <div style={{
            border: `1px solid ${C.faint}`, background: '#ffffff',
            aspectRatio: '4/5', overflow: 'hidden', position: 'relative',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: 24, boxSizing: 'border-box',
          }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/redesign/wishlist.png"
              alt="Closet and wishlist"
              style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', display: 'block' }}
            />
            <div style={{
              position: 'absolute', top: 12, left: 12,
              background: C.bone, color: C.void,
              fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.28em',
              textTransform: 'uppercase', fontWeight: 700,
              padding: '6px 10px', zIndex: 3,
            }}>WISHLIST · CLOSET</div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── Footer ─── */
function DesktopFooter() {
  const C = useC();
  const router = useRouter();
  return (
    <section style={{
      background: C.void, color: C.bone, padding: '64px 32px 48px',
      borderTop: `1px solid ${C.faint}`,
    }}>
      <div style={{
        maxWidth: 1280, margin: '0 auto',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 32,
        flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', gap: 18, alignItems: 'center' }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={C.bone === '#0A0A0A' ? '/redesign/wordmark.png' : '/redesign/wordmark-white.png'}
            alt="TRYON"
            style={{ height: 18, width: 'auto', display: 'block' }}
          />
          <div style={{ width: 1, height: 14, background: C.faint }} />
          <div style={{
            fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
            color: C.dim, textTransform: 'uppercase',
          }}>FIT FOLLOWS · TRYON · MMXXVI</div>
        </div>
        <div style={{ display: 'flex', gap: 22 }}>
          {[
            { label: 'PRICING', href: '/pricing' },
            { label: 'PRIVACY', href: '/privacy' },
            { label: 'DEMO', href: '/demo' },
            { label: 'SIGN IN', href: '/login' },
          ].map(it => (
            <button
              key={it.label}
              onClick={() => router.push(it.href)}
              style={{
                background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
                color: C.dim, textTransform: 'uppercase', fontWeight: 500,
              }}
            >{it.label}</button>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── Mobile ─── */
function MobileNav() {
  const C = useC();
  const router = useRouter();
  const hidden = useSmartNav();
  const cap: React.CSSProperties = {
    background: C.bone === '#0A0A0A' ? 'rgba(255,255,255,0.82)' : 'rgba(10,10,10,0.74)',
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
            style={{ height: 16, width: 'auto', display: 'block' }}
          />
        </button>
      </div>
      <div style={{
        ...cap, pointerEvents: 'auto',
        display: 'inline-flex', alignItems: 'stretch',
        padding: 3, gap: 3, borderRadius: 999,
      }}>
        <button
          onClick={() => router.push('/pricing')}
          style={{
            padding: '7px 10px', background: 'transparent', border: 'none', color: C.bone,
            fontFamily: 'var(--mono)', fontSize: 8, letterSpacing: '0.28em',
            textTransform: 'uppercase', fontWeight: 500, cursor: 'pointer',
          }}
        >PRICING</button>
        <button
          onClick={() => router.push('/demo')}
          style={{
            padding: '7px 10px', background: C.bone, color: C.void, border: 'none',
            fontFamily: 'var(--mono)', fontSize: 8, letterSpacing: '0.28em',
            textTransform: 'uppercase', fontWeight: 700, cursor: 'pointer',
            borderRadius: 999,
          }}
        >TRY IT NOW →</button>
      </div>
    </div>
  );
}

function MobileHero() {
  const C = useC();
  const router = useRouter();
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
        fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.28em',
        color: C.dim, textTransform: 'uppercase', marginBottom: 20,
        position: 'relative', zIndex: 2,
      }}>BUILT FOR THE 2026 EU FASHION RULEBOOK.</div>

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
          marginTop: 18, fontSize: 14, lineHeight: 1.45, color: C.bone, opacity: 0.78,
          fontWeight: 500, maxWidth: 320,
        }}>
          One avatar. Every brand. Real cloth, real measurements, real fit.
        </p>

        <button
          onClick={() => router.push('/demo')}
          style={{
            marginTop: 28,
            background: C.bone, color: C.void, border: 'none',
            padding: '16px 24px',
            fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.28em',
            textTransform: 'uppercase', fontWeight: 800, cursor: 'pointer',
            display: 'inline-flex', alignItems: 'center', gap: 10,
            borderRadius: 999,
            boxShadow: '0 16px 40px rgba(10,10,10,0.18)',
          }}
        >
          TRY THE DEMO
          <span style={{ fontSize: 14 }}>→</span>
        </button>
      </div>

      <div style={{
        marginTop: 28, position: 'relative', zIndex: 3,
        borderTop: `1px solid ${C.faint}`,
        marginLeft: -16, marginRight: -16,
        display: 'grid', gridTemplateColumns: '1fr 1fr',
      }}>
        {[
          { tag: 'FOR BRANDS', t: 'PRICING', href: '/pricing', side: 'L' as const },
          { tag: 'FOR SHOPPERS', t: 'SIGN UP', href: '/signup', side: 'R' as const },
        ].map((c, i) => (
          <button
            key={c.t}
            onClick={() => router.push(c.href)}
            style={{
              padding: '18px 14px 16px',
              borderRight: i === 0 ? `1px solid ${C.faint}` : 'none',
              display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
              gap: 10, minHeight: 96,
              background: 'transparent', cursor: 'pointer', border: 'none',
              textAlign: c.side === 'R' ? 'right' : 'left',
              color: C.bone,
            }}
          >
            <div style={{
              fontFamily: 'var(--mono)', fontSize: 8, letterSpacing: '0.28em',
              color: C.dim, textTransform: 'uppercase',
            }}>{c.tag}</div>
            <div style={{
              fontFamily: 'var(--display)', fontWeight: 900,
              fontSize: 22, letterSpacing: '-0.03em', lineHeight: 0.95,
              color: C.bone, textTransform: 'uppercase',
            }}>{c.t} →</div>
          </button>
        ))}
      </div>
    </section>
  );
}

function MobileComponents() {
  const C = useC();
  const items = [
    { n: '01', tag: 'FIT PASSPORT', desc: 'A 3D avatar of you, rigged.', image: '/redesign/fit-passport.jpg' },
    { n: '02', tag: 'GARMENT BIND', desc: 'Real cloth on real photography.', image: '/redesign/garment-bind.jpg' },
    { n: '03', tag: 'FIT REPORT', desc: 'Per-SKU confidence + size signal.', image: '/redesign/fit-report.jpg' },
  ];
  return (
    <section style={{
      background: C.void, color: C.bone,
      padding: '64px 16px',
    }}>
      <div style={{
        fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.32em',
        color: C.dim, textTransform: 'uppercase', marginBottom: 16,
      }}>THE PROTOCOL</div>
      <h2 style={{
        fontFamily: 'var(--display)', fontWeight: 900, margin: '0 0 28px',
        fontSize: 44, letterSpacing: '-0.04em', lineHeight: 0.86,
        textTransform: 'uppercase',
      }}>
        ONE PROTOCOL.<br/>
        <span style={{ WebkitTextStroke: `1.5px ${C.bone}`, color: 'transparent' }}>THREE PIECES.</span>
      </h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {items.map(it => (
          <div key={it.n} style={{
            border: `1px solid ${C.faint}`, background: C.ash,
          }}>
            <div style={{
              borderBottom: `1px solid ${C.faint}`,
              padding: '10px 14px',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.28em',
              textTransform: 'uppercase', color: C.bone,
            }}>
              <span>{it.tag}</span>
              <span style={{ color: C.dim }}>{it.n}</span>
            </div>
            <div style={{
              aspectRatio: '4/3', background: '#ffffff',
              display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
              padding: 16, boxSizing: 'border-box',
            }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={it.image} alt={it.tag} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', display: 'block' }} />
            </div>
            <div style={{
              borderTop: `1px solid ${C.faint}`, padding: '14px',
              fontSize: 13, lineHeight: 1.5, color: C.bone, opacity: 0.85,
            }}>{it.desc}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function MobileEvidence() {
  const C = useC();
  const wasteRows = [
    { k: 'RETURNS AVOIDED', v: 40, suffix: '%', sub: 'less reverse logistics, less landfill.' },
    { k: 'OVERPRODUCTION CUT', v: 18, suffix: '%', sub: 'closer to real demand.' },
    { k: 'CO₂E PER ORDER', v: 2.4, suffix: 'kg', sub: 'saved per prevented return.', decimals: 1 },
  ];
  const rulebook = [
    { date: 'JUL 2026', title: 'EU bans destruction of unsold apparel.' },
    { date: 'SEP 2026', title: 'ECGT applies. Anti-greenwashing.' },
    { date: '2028', title: 'DPP mandatory for textiles.' },
  ];
  return (
    <section style={{
      background: C.ash, color: C.bone, padding: '64px 16px', position: 'relative', overflow: 'hidden',
    }}>
      <SlitLight count={20} opacity={0.3} />
      <div style={{ position: 'relative', zIndex: 2 }}>
        <div style={{
          fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.32em',
          color: C.dim, textTransform: 'uppercase', marginBottom: 16,
        }}>WHY NOW</div>
        <h2 style={{
          fontFamily: 'var(--display)', fontWeight: 900,
          fontSize: 44, letterSpacing: '-0.04em',
          lineHeight: 0.86, margin: '0 0 16px', textTransform: 'uppercase',
        }}>
          FIT IS A<br/>
          <span style={{ WebkitTextStroke: `1.5px ${C.bone}`, color: 'transparent' }}>CLIMATE</span><br/>
          PROBLEM.
        </h2>
        <p style={{ fontSize: 13, lineHeight: 1.55, margin: '0 0 22px', color: C.bone, opacity: 0.85 }}>
          70% of fashion returns are caused by fit. (McKinsey.) In 2022, 9.5 billion pounds of US returns went to landfill, emitting 24 million tonnes of CO₂. (Optoro.) TRYON kills the return before the order.
        </p>

        <div style={{
          background: C.steel, border: `1px solid ${C.faint}`,
          padding: '20px 18px', marginBottom: 20,
        }}>
          <div style={{
            fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.28em',
            color: C.dim, textTransform: 'uppercase', marginBottom: 6,
          }}>RAMIN PILOT, 14 DAYS</div>
          <div style={{
            fontFamily: 'var(--display)', fontSize: 80, fontWeight: 900,
            letterSpacing: '-0.05em', lineHeight: 0.85, color: C.bone, margin: 0,
          }}>
            <CountUp to={94} />
            <span style={{ WebkitTextStroke: `1.5px ${C.bone}`, color: 'transparent' }}>%</span>
          </div>
          <div style={{ fontSize: 12, lineHeight: 1.4, color: C.dim, marginTop: 4 }}>
            of widget opens convert to a try-on.
          </div>
        </div>

        <div style={{ border: `1px solid ${C.faint}`, background: C.steel, marginBottom: 20 }}>
          <div style={{
            borderBottom: `1px solid ${C.faint}`, padding: '8px 12px',
            display: 'flex', justifyContent: 'space-between',
            fontFamily: 'var(--mono)', fontSize: 8, letterSpacing: '0.28em',
            textTransform: 'uppercase', color: C.dim,
          }}>
            <span style={{ color: C.bone }}>WASTE LEDGER</span>
            <span>PER 1,000 ORDERS</span>
          </div>
          {wasteRows.map((r, i) => (
            <div key={r.k} style={{
              padding: '12px 12px',
              borderBottom: i < wasteRows.length - 1 ? `1px solid ${C.faint}` : 'none',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4 }}>
                <span style={{ fontFamily: 'var(--mono)', fontSize: 8, letterSpacing: '0.24em', color: C.dim }}>{r.k}</span>
                <span style={{
                  fontFamily: 'var(--display)', fontSize: 22, fontWeight: 900,
                  letterSpacing: '-0.03em', color: C.bone, lineHeight: 1,
                }}>
                  <span>−</span><CountUp to={r.v} decimals={r.decimals || 0} />{r.suffix}
                </span>
              </div>
              <div style={{ fontSize: 11, lineHeight: 1.4, color: C.bone, opacity: 0.7 }}>{r.sub}</div>
            </div>
          ))}
          <div style={{
            padding: '8px 12px', borderTop: `1px solid ${C.faint}`,
            fontFamily: 'var(--mono)', fontSize: 8, letterSpacing: '0.24em',
            color: C.dim, textTransform: 'uppercase',
          }}>SOURCES · MCKINSEY · OPTORO · TRYON PILOT 2026</div>
        </div>

        <div style={{
          fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.28em',
          color: C.dim, textTransform: 'uppercase', marginBottom: 12,
        }}>EU RULEBOOK · 2026 TO 2028</div>
        <div style={{ border: `1px solid ${C.faint}`, background: C.steel }}>
          {rulebook.map((r, i) => (
            <div key={r.date} style={{
              padding: '14px 14px',
              borderBottom: i < rulebook.length - 1 ? `1px solid ${C.faint}` : 'none',
            }}>
              <div style={{
                fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.28em',
                color: C.bone, fontWeight: 700, marginBottom: 4,
              }}>{r.date}</div>
              <div style={{ fontSize: 13, lineHeight: 1.45, color: C.bone, fontWeight: 600 }}>{r.title}</div>
            </div>
          ))}
        </div>
        <p style={{ fontSize: 12, lineHeight: 1.5, marginTop: 14, color: C.bone, opacity: 0.78 }}>
          Every garment we render is already a 3D digital twin. DPP-ready by design.
        </p>
      </div>
    </section>
  );
}

function MobileBrands() {
  const C = useC();
  const router = useRouter();
  const tiers = [
    { name: 'FREE', price: '$0', sub: '200 sessions' },
    { name: 'STUDIO', price: '$149', sub: '2,500 sessions' },
    { name: 'BRAND', price: '$2,490', sub: '40,000 sessions' },
    { name: 'SCALE', price: 'Talk to us', sub: 'Multi-brand, custom' },
  ];
  return (
    <section style={{ background: C.void, color: C.bone, padding: '64px 16px' }}>
      <div style={{
        fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.32em',
        color: C.dim, textTransform: 'uppercase', marginBottom: 16,
      }}>FOR BRANDS</div>
      <h2 style={{
        fontFamily: 'var(--display)', fontWeight: 900, margin: '0 0 14px',
        fontSize: 44, letterSpacing: '-0.04em', lineHeight: 0.86,
        textTransform: 'uppercase',
      }}>
        PAY LESS THAN<br/>
        <span style={{ WebkitTextStroke: `1.5px ${C.bone}`, color: 'transparent' }}>ONE RETURN</span> A DAY.
      </h2>
      <p style={{ fontSize: 13, lineHeight: 1.5, margin: '0 0 28px', color: C.bone, opacity: 0.78 }}>
        Built for Shopify Plus fashion brands losing six figures a month to returns. Save tens of thousands per month.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 0, border: `1px solid ${C.faint}`, marginBottom: 22 }}>
        {tiers.map((t, i) => (
          <button
            key={t.name}
            onClick={() => router.push('/pricing')}
            style={{
              background: C.ash,
              borderBottom: i < tiers.length - 1 ? `1px solid ${C.faint}` : 'none',
              border: 'none',
              padding: '18px 16px',
              textAlign: 'left',
              cursor: 'pointer',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              color: C.bone,
            }}
          >
            <div>
              <div style={{
                fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.32em',
                color: C.dim, textTransform: 'uppercase', fontWeight: 700, marginBottom: 4,
              }}>{t.name}</div>
              <div style={{
                fontFamily: 'var(--display)', fontSize: 26, fontWeight: 900,
                letterSpacing: '-0.03em', color: C.bone,
              }}>{t.price}</div>
            </div>
            <div style={{
              fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.18em',
              color: C.dim, textTransform: 'uppercase',
            }}>{t.sub} →</div>
          </button>
        ))}
      </div>

      <button
        onClick={() => router.push('/pricing')}
        style={{
          background: C.bone, color: C.void, border: 'none',
          padding: '16px 24px', width: '100%',
          fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.28em',
          textTransform: 'uppercase', fontWeight: 800, cursor: 'pointer',
          borderRadius: 999,
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 10,
        }}
      >SEE FULL PRICING <span style={{ fontSize: 14 }}>→</span></button>
    </section>
  );
}

function MobileShoppers() {
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
      background: C.ash, color: C.bone, padding: '64px 16px', position: 'relative', overflow: 'hidden',
    }}>
      <SlitLight count={22} opacity={0.32} />
      <div style={{ position: 'relative', zIndex: 2 }}>
        <div style={{
          fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.32em',
          color: C.dim, textTransform: 'uppercase', marginBottom: 16,
        }}>FOR SHOPPERS</div>
        <h2 style={{
          fontFamily: 'var(--display)', fontWeight: 900,
          fontSize: 44, letterSpacing: '-0.04em',
          lineHeight: 0.86, margin: '0 0 14px', textTransform: 'uppercase',
        }}>
          ONE LOGIN.<br/>
          <span style={{ WebkitTextStroke: `1.5px ${C.bone}`, color: 'transparent' }}>EVERY</span> BRAND.
        </h2>
        <p style={{ fontSize: 13, lineHeight: 1.55, margin: '0 0 22px', color: C.bone, opacity: 0.85 }}>
          Free, forever. Build your fit passport once. Wear every garment we host across every brand on Earth.
        </p>

        <div style={{
          border: `1px solid ${C.faint}`, background: '#ffffff',
          aspectRatio: '4/5', position: 'relative',
          display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
          padding: 16, boxSizing: 'border-box', marginBottom: 22,
        }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/redesign/wishlist.png" alt="Closet and wishlist"
            style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', display: 'block' }}
          />
          <div style={{
            position: 'absolute', top: 8, left: 8, zIndex: 3,
            background: C.bone, color: C.void,
            fontFamily: 'var(--mono)', fontSize: 8, letterSpacing: '0.22em',
            textTransform: 'uppercase', fontWeight: 700,
            padding: '4px 6px',
          }}>WISHLIST · CLOSET</div>
        </div>

        <div style={{
          background: C.cardBg, color: C.cardInk,
          border: `1px solid ${C.bone}`,
          boxShadow: '0 16px 40px rgba(0,0,0,0.18)',
        }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '10px 14px',
            borderBottom: `1px solid ${C.cardHair}`,
            fontFamily: 'var(--mono)', fontSize: 8, letterSpacing: '0.28em',
            textTransform: 'uppercase', color: C.cardDim,
          }}>
            <span style={{ color: C.cardInk }}>SHOPPER ENTRY</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#7CFFA1', boxShadow: '0 0 8px #7CFFA1' }} />
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
                padding: '16px 14px',
                fontFamily: 'var(--display)', fontSize: 17, fontWeight: 600,
                letterSpacing: '-0.01em', color: C.cardInk,
                borderBottom: `1px solid ${C.cardHair}`,
              }}
            />
            <button
              type="submit"
              style={{
                background: C.cardInk, color: C.cardBg,
                padding: '14px', minHeight: 50,
                fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.28em',
                textTransform: 'uppercase', fontWeight: 800, border: 'none',
                cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
              }}
            >GET MY PASSPORT <span style={{ fontSize: 14 }}>→</span></button>
          </form>
        </div>
      </div>
    </section>
  );
}

function MobileFooter() {
  const C = useC();
  const router = useRouter();
  return (
    <section style={{
      background: C.void, color: C.bone, padding: '40px 16px 56px',
      borderTop: `1px solid ${C.faint}`,
      display: 'flex', flexDirection: 'column', gap: 18, alignItems: 'flex-start',
    }}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={C.bone === '#0A0A0A' ? '/redesign/wordmark.png' : '/redesign/wordmark-white.png'}
        alt="TRYON"
        style={{ height: 16, width: 'auto', display: 'block' }}
      />
      <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap' }}>
        {[
          { label: 'PRICING', href: '/pricing' },
          { label: 'PRIVACY', href: '/privacy' },
          { label: 'DEMO', href: '/demo' },
          { label: 'SIGN IN', href: '/login' },
        ].map(it => (
          <button
            key={it.label}
            onClick={() => router.push(it.href)}
            style={{
              background: 'none', border: 'none', padding: 0, cursor: 'pointer',
              fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.32em',
              color: C.dim, textTransform: 'uppercase', fontWeight: 500,
            }}
          >{it.label}</button>
        ))}
      </div>
      <div style={{
        fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.32em',
        color: C.dim, textTransform: 'uppercase',
      }}>FIT FOLLOWS · TRYON · MMXXVI</div>
    </section>
  );
}

/* ─── Root ─── */
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
            <MobileComponents />
            <MobileEvidence />
            <MobileBrands />
            <MobileShoppers />
            <MobileFooter />
          </>
        ) : (
          <>
            <DesktopNav />
            <DesktopHero />
            <DesktopComponents />
            <DesktopEvidence />
            <DesktopBrands />
            <DesktopShoppers />
            <DesktopFooter />
          </>
        )}
      </div>
    </ThemeCtx.Provider>
  );
}
