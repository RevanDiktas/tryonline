'use client';

import React, { createContext, useContext, useEffect, useRef, useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { useIsMobile } from './useIsMobile';
import { SharedNav, NavLink, NavCta, AuthAwareSignInLink } from './SharedNav';

// Lazy-load AvatarHero so the Three.js bundle doesn't block first paint of the
// home page. ssr:false because the Canvas needs WebGL.
const AvatarHero = dynamic(
  () => import('./AvatarHero').then(m => m.AvatarHero),
  {
    ssr: false,
    loading: () => (
      <div style={{
        width: '100%', height: '60vh',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: 'rgba(10,10,10,0.32)', fontFamily: 'var(--display)', fontSize: 13,
      }}>Loading try-on…</div>
    ),
  },
);

const COBALT = '#0040FF';
const COBALT_HOVER = '#0030CC';

const PROBLEM_VIGNETTES: string[] = [
  'A shopper bought size M, returned it, then bought L. You paid for two shipments and a return label.',
  'She measured small once, ordered medium, swam in it, returned. Two days later, ordered small. Two parcels, one customer.',
  '70% of fashion returns are caused by fit. Solve fit, recover the margin.',
];

const PAL = {
  light: {
    bg: '#FAFAF8',
    surface: '#FFFFFF',
    ink: '#0A0A0A',
    mute: '#6E6E6E',
    line: 'rgba(10,10,10,0.10)',
    cardBg: '#0A0A0A',
    cardInk: '#FAFAF8',
    cardLine: 'rgba(255,255,255,0.14)',
    cardMute: '#9A9A9A',
  },
  dark: {
    bg: '#0A0A0A',
    surface: '#121212',
    ink: '#F2F1EC',
    mute: '#8A8A8A',
    line: 'rgba(255,255,255,0.10)',
    cardBg: '#F2F1EC',
    cardInk: '#0A0A0A',
    cardLine: 'rgba(0,0,0,0.10)',
    cardMute: '#6E6E6E',
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

function CountUp({ to, suffix = '', duration = 1200, decimals = 0, style }: {
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

const headingStyle = (px: string): React.CSSProperties => ({
  fontFamily: 'var(--display)',
  fontWeight: 700,
  fontSize: px,
  letterSpacing: '-0.022em',
  lineHeight: 1.04,
  margin: 0,
});

const bodyStyle: React.CSSProperties = {
  fontFamily: 'var(--display)',
  fontWeight: 400,
  fontSize: 16,
  lineHeight: 1.6,
};

/* ─── Hero: avatar centerpiece + rotating problem vignette ─── */
function DesktopHero() {
  const C = useC();
  const router = useRouter();
  const [vignetteIdx, setVignetteIdx] = useState(0);
  const [hovered, setHovered] = useState<'primary' | 'ghost' | null>(null);

  useEffect(() => {
    const id = setInterval(() => {
      setVignetteIdx((i) => (i + 1) % PROBLEM_VIGNETTES.length);
    }, 5500);
    return () => clearInterval(id);
  }, []);

  return (
    <section style={{
      background: C.bg, color: C.ink,
      padding: '40px 32px 56px',
      borderBottom: `1px solid ${C.line}`,
      minHeight: 'min(96vh, 1000px)',
      display: 'flex', flexDirection: 'column', justifyContent: 'center',
      position: 'relative',
      overflow: 'hidden',
    }}>
      <div style={{ maxWidth: 1280, margin: '0 auto', width: '100%' }}>
        <div style={{
          fontFamily: 'var(--mono)', fontSize: 12, color: C.mute,
          letterSpacing: '0.08em', textTransform: 'uppercase', fontWeight: 500,
          marginBottom: 28,
        }}>
          TryOn — Fit before you buy
        </div>

        <h1 style={{
          fontFamily: 'var(--display)', fontWeight: 900,
          fontSize: 'clamp(64px, 9vw, 128px)',
          letterSpacing: '-0.045em', lineHeight: 0.88,
          margin: '0 0 28px', maxWidth: 1180,
        }}>
          Try clothes on yourself. Before you buy.
        </h1>

        <div style={{
          display: 'grid', gridTemplateColumns: '1.05fr 1fr', gap: 48,
          alignItems: 'center', marginTop: 12,
        }}>
          {/* Left: rotating vignette + CTAs */}
          <div style={{ minWidth: 0 }}>
            <div style={{
              minHeight: 168,
              display: 'flex', alignItems: 'flex-start',
              fontFamily: 'var(--display)', fontSize: 22, lineHeight: 1.45,
              color: C.mute, fontWeight: 400, letterSpacing: '-0.005em',
              maxWidth: 560,
            }}>
              <span
                key={vignetteIdx}
                style={{
                  animation: 'ds-fade-in 0.6s cubic-bezier(0.22, 0.61, 0.36, 1)',
                  display: 'inline-block',
                }}
              >
                {PROBLEM_VIGNETTES[vignetteIdx]}
              </span>
            </div>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 8 }}>
              <button
                onClick={() => router.push('/demo')}
                onMouseEnter={() => setHovered('primary')}
                onMouseLeave={() => setHovered(null)}
                style={{
                  background: hovered === 'primary' ? COBALT_HOVER : COBALT,
                  color: '#FFFFFF', border: 'none',
                  padding: '15px 28px', borderRadius: 9999,
                  fontFamily: 'var(--display)', fontSize: 15, fontWeight: 600,
                  letterSpacing: '-0.005em',
                  cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 10,
                  transform: hovered === 'primary' ? 'translateY(-1px)' : 'translateY(0)',
                  transition: 'all 180ms cubic-bezier(0.4, 0, 0.2, 1)',
                }}
              >
                Try the demo <span>→</span>
              </button>
              <button
                onClick={() => router.push('/signup')}
                onMouseEnter={() => setHovered('ghost')}
                onMouseLeave={() => setHovered(null)}
                style={{
                  background: hovered === 'ghost' ? 'rgba(0, 64, 255, 0.08)' : 'transparent',
                  color: hovered === 'ghost' ? COBALT : C.ink,
                  border: `1px solid ${hovered === 'ghost' ? COBALT : C.ink}`,
                  padding: '15px 28px', borderRadius: 9999,
                  fontFamily: 'var(--display)', fontSize: 15, fontWeight: 600,
                  letterSpacing: '-0.005em',
                  cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 8,
                  transition: 'all 180ms cubic-bezier(0.4, 0, 0.2, 1)',
                }}
              >
                Build your passport
              </button>
            </div>
            <div style={{
              marginTop: 28,
              display: 'flex', alignItems: 'center', gap: 10,
              fontFamily: 'var(--mono)', fontSize: 11, color: C.mute,
              letterSpacing: '0.08em', textTransform: 'uppercase',
            }}>
              {PROBLEM_VIGNETTES.map((_, i) => (
                <span
                  key={i}
                  aria-hidden
                  style={{
                    width: i === vignetteIdx ? 22 : 6, height: 2,
                    background: i === vignetteIdx ? COBALT : C.line,
                    transition: 'all 400ms cubic-bezier(0.22, 0.61, 0.36, 1)',
                    display: 'inline-block',
                  }}
                />
              ))}
            </div>
          </div>

          {/* Right: avatar centerpiece */}
          <div style={{
            position: 'relative',
            borderRadius: 32,
            overflow: 'hidden',
            background: C.surface,
            border: `1px solid ${C.line}`,
            minHeight: 520,
          }}>
            <AvatarHero height="58vh" interactive={true} rotateSpeed={0.7} />
            <div style={{
              position: 'absolute', bottom: 16, left: 16,
              fontFamily: 'var(--mono)', fontSize: 11, color: C.mute,
              letterSpacing: '0.08em', textTransform: 'uppercase',
              background: C.bg, padding: '6px 12px', borderRadius: 9999,
              border: `1px solid ${C.line}`,
            }}>
              Ramin Studios — Size M
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── Brand/Shopper tiles, moved out of the hero into their own section ─── */
function DesktopBrandShopperTiles() {
  const C = useC();
  const router = useRouter();
  return (
    <section style={{
      background: C.bg, color: C.ink,
      padding: '88px 32px',
      borderBottom: `1px solid ${C.line}`,
    }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <h2 style={{
          ...headingStyle('clamp(36px, 4.5vw, 64px)'),
          marginBottom: 14, maxWidth: 920,
        }}>
          Built for both sides.
        </h2>
        <p style={{
          ...bodyStyle, color: C.mute, maxWidth: 720, marginBottom: 40,
        }}>
          Brands cut returns and lift conversion. Shoppers wear every brand without ever guessing a size again.
        </p>
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20,
        }}>
          <PathTile
            tag="For brands"
            title="I am a brand"
            sub="Cut returns. Lift conversion. Pay less than the cost of one return per day."
            cta="See pricing →"
            onClick={() => router.push('/pricing')}
            C={C}
          />
          <PathTile
            tag="For shoppers"
            title="I am a shopper"
            sub="Build your fit passport once. Wear every brand on Earth. Free, forever."
            cta="Sign up free →"
            onClick={() => router.push('/signup')}
            C={C}
          />
        </div>
      </div>
    </section>
  );
}

function PathTile({
  tag, title, sub, cta, onClick, C, border,
}: {
  tag: string; title: string; sub: string; cta: string;
  onClick: () => void; C: Palette; border?: 'right' | 'none';
}) {
  const [hover, setHover] = useState(false);
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        background: C.surface,
        border: `1px solid ${hover ? COBALT : C.line}`,
        borderRadius: 24,
        padding: '40px 36px',
        display: 'flex', flexDirection: 'column', gap: 16,
        textAlign: 'left',
        cursor: 'pointer',
        color: C.ink,
        transition: 'border-color 220ms cubic-bezier(0.22, 0.61, 0.36, 1), transform 220ms cubic-bezier(0.22, 0.61, 0.36, 1)',
        transform: hover ? 'translateY(-2px)' : 'translateY(0)',
        minHeight: 220,
      }}
    >
      <div style={{
        fontFamily: 'var(--mono)', fontSize: 11, fontWeight: 500,
        color: hover ? COBALT : C.mute,
        letterSpacing: '0.08em', textTransform: 'uppercase',
        transition: 'color 220ms cubic-bezier(0.22, 0.61, 0.36, 1)',
      }}>{tag}</div>
      <div style={{
        fontFamily: 'var(--display)', fontSize: 'clamp(28px, 3vw, 44px)',
        fontWeight: 700, letterSpacing: '-0.02em', lineHeight: 1.05,
        color: C.ink,
      }}>{title}</div>
      <div style={{
        ...bodyStyle, fontSize: 15, color: C.mute, maxWidth: 420,
      }}>{sub}</div>
      <div style={{
        marginTop: 'auto', display: 'inline-flex', alignItems: 'center', gap: 8,
        fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600,
        color: hover ? COBALT : C.ink,
        transition: 'color 220ms cubic-bezier(0.22, 0.61, 0.36, 1)',
      }}>{cta}</div>
    </button>
  );
}

/* ─── Components grid: 3 pieces of the protocol ─── */
function DesktopComponents() {
  const C = useC();
  const items = [
    {
      tag: 'Fit Passport',
      desc: 'A 3D avatar of you, rigged from 12 measurements. Built once. Yours forever.',
      image: '/redesign/fit-passport.jpg',
    },
    {
      tag: 'Garment Bind',
      desc: 'Real cloth physics on real product photography. Every body shape, not just sample size.',
      image: '/redesign/garment-bind.jpg',
    },
    {
      tag: 'Fit Report',
      desc: 'Per-SKU confidence and size signal. The brand knows what fits and what does not.',
      image: '/redesign/fit-report.jpg',
    },
  ];
  return (
    <section style={{
      background: C.surface, color: C.ink,
      padding: '88px 32px',
      borderBottom: `1px solid ${C.line}`,
    }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <h2 style={{
          ...headingStyle('clamp(36px, 4.5vw, 64px)'),
          marginBottom: 40, maxWidth: 760,
        }}>
          The protocol. Three pieces.
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }}>
          {items.map(it => (
            <div key={it.tag} style={{
              border: `1px solid ${C.line}`,
              borderRadius: 16,
              background: C.bg,
              overflow: 'hidden',
              display: 'flex', flexDirection: 'column',
            }}>
              <div style={{
                aspectRatio: '4/5', background: '#ffffff',
                display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
                padding: 20, boxSizing: 'border-box',
                borderBottom: `1px solid ${C.line}`,
              }}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={it.image} alt={it.tag} style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }} />
              </div>
              <div style={{ padding: '20px 22px 24px' }}>
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 17, fontWeight: 600,
                  color: C.ink, marginBottom: 6,
                }}>{it.tag}</div>
                <div style={{ ...bodyStyle, fontSize: 14, color: C.mute }}>{it.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── Evidence: pilot + waste ledger + EU rulebook ─── */
function DesktopEvidence() {
  const C = useC();
  const wasteRows = [
    { k: 'Returns avoided', v: 40, suffix: '%', sub: 'less reverse logistics, less landfill.' },
    { k: 'Overproduction cut', v: 18, suffix: '%', sub: 'closer to real demand.' },
    { k: 'CO₂e saved per order', v: 2.4, suffix: 'kg', sub: 'when a return is prevented.', decimals: 1 },
  ];
  const rulebook = [
    { date: 'Jul 2026', title: 'EU bans destruction of unsold apparel.', sub: 'Central Digital Product Passport registry goes live.' },
    { date: 'Sep 2026', title: 'ECGT applies. Anti-greenwashing.', sub: 'Words like "sustainable" become regulated. Claims need proof.' },
    { date: '2028', title: 'DPP mandatory for textiles.', sub: 'Every garment sold in the EU carries a digital twin.' },
  ];

  return (
    <section style={{
      background: C.bg, color: C.ink,
      padding: '88px 32px',
      borderBottom: `1px solid ${C.line}`,
    }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <h2 style={{
          ...headingStyle('clamp(36px, 4.5vw, 64px)'),
          marginBottom: 18, maxWidth: 920,
        }}>
          Fit is a climate problem.
        </h2>
        <p style={{
          ...bodyStyle, color: C.mute, maxWidth: 720, marginBottom: 48,
        }}>
          70% of fashion returns are caused by fit (McKinsey, 2024). In 2022, 9.5 billion pounds of US returns went to landfill, emitting 24 million tonnes of CO₂ (Optoro). TryOn kills the return before the order. Fewer trucks. Less plastic. Less polyester pulled out of the ground for stock that nobody wears.
        </p>

        <div style={{
          display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 24, alignItems: 'start',
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div style={{
              border: `1px solid ${C.line}`, borderRadius: 16,
              background: C.surface, padding: 28,
            }}>
              <div style={{
                fontFamily: 'var(--display)', fontSize: 13, color: C.mute, fontWeight: 500, marginBottom: 10,
              }}>Ramin Studios pilot, Amsterdam</div>
              <div style={{
                fontFamily: 'var(--display)', fontWeight: 700,
                fontSize: 80, letterSpacing: '-0.04em', lineHeight: 1, color: C.ink,
              }}>
                <CountUp to={94} />%
              </div>
              <div style={{ ...bodyStyle, fontSize: 14, color: C.mute, marginTop: 10 }}>
                of widget opens convert to a try-on. Live data, last 14 days.
              </div>
              <div style={{
                marginTop: 18, paddingTop: 18,
                borderTop: `1px solid ${C.line}`,
                display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14,
              }}>
                {[
                  { k: 'Opens', v: 100 },
                  { k: 'Try-ons', v: 94 },
                  { k: 'ATC', v: 34 },
                  { k: 'Avg session', v: '38s' },
                ].map(row => (
                  <div key={row.k}>
                    <div style={{
                      fontFamily: 'var(--display)', fontSize: 12, color: C.mute, fontWeight: 500,
                    }}>{row.k}</div>
                    <div style={{
                      fontFamily: 'var(--display)', fontSize: 20, fontWeight: 600,
                      color: C.ink, letterSpacing: '-0.01em',
                    }}>
                      {typeof row.v === 'number' ? <CountUp to={row.v} /> : row.v}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{
              border: `1px solid ${C.line}`, borderRadius: 16,
              background: C.surface,
            }}>
              <div style={{
                padding: '14px 24px', borderBottom: `1px solid ${C.line}`,
                display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
              }}>
                <div style={{ fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600, color: C.ink }}>
                  Waste ledger
                </div>
                <div style={{ fontFamily: 'var(--display)', fontSize: 13, color: C.mute }}>
                  per 1,000 orders
                </div>
              </div>
              {wasteRows.map((r, i) => (
                <div key={r.k} style={{
                  padding: '16px 24px',
                  borderBottom: i < wasteRows.length - 1 ? `1px solid ${C.line}` : 'none',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 16,
                }}>
                  <div>
                    <div style={{ fontFamily: 'var(--display)', fontSize: 15, fontWeight: 500, color: C.ink }}>{r.k}</div>
                    <div style={{ fontFamily: 'var(--display)', fontSize: 13, color: C.mute, marginTop: 2 }}>{r.sub}</div>
                  </div>
                  <div style={{
                    fontFamily: 'var(--display)', fontSize: 26, fontWeight: 600,
                    letterSpacing: '-0.02em', color: C.ink, whiteSpace: 'nowrap',
                  }}>
                    −<CountUp to={r.v} decimals={r.decimals || 0} />{r.suffix}
                  </div>
                </div>
              ))}
              <div style={{
                padding: '12px 24px', borderTop: `1px solid ${C.line}`,
                fontFamily: 'var(--display)', fontSize: 12, color: C.mute,
              }}>Sources: McKinsey 2024, Optoro 2022, TryOn Ramin pilot 2026.</div>
            </div>
          </div>

          <div>
            <div style={{
              fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600, color: C.ink, marginBottom: 14,
            }}>The EU rulebook, 2026 to 2028.</div>
            <div style={{
              border: `1px solid ${C.line}`, borderRadius: 16,
              background: C.surface,
            }}>
              {rulebook.map((r, i) => (
                <div key={r.date} style={{
                  padding: '20px 24px',
                  borderBottom: i < rulebook.length - 1 ? `1px solid ${C.line}` : 'none',
                }}>
                  <div style={{
                    fontFamily: 'var(--display)', fontSize: 13, color: C.mute, fontWeight: 500, marginBottom: 8,
                  }}>{r.date}</div>
                  <div style={{
                    fontFamily: 'var(--display)', fontSize: 18, fontWeight: 600,
                    color: C.ink, lineHeight: 1.3, letterSpacing: '-0.01em',
                  }}>{r.title}</div>
                  <div style={{ ...bodyStyle, fontSize: 13.5, color: C.mute, marginTop: 6 }}>{r.sub}</div>
                </div>
              ))}
            </div>
            <p style={{ ...bodyStyle, fontSize: 14, color: C.mute, marginTop: 14 }}>
              Every garment we render is already a 3D digital twin. DPP-ready by design. While other VTO vendors will be deleting "sustainable" from their landing pages in September, we will be quoting the regulation.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── For Brands ─── */
function DesktopBrands() {
  const C = useC();
  const router = useRouter();
  const cmp = [
    {
      name: 'Google VTO',
      bullets: ['Flat 2D image generation.', 'No body measurements.', 'Happens on Google. Brand loses the data.'],
      muted: true,
    },
    {
      name: 'True Fit',
      bullets: ['Size recommendation only.', 'No 3D, no avatar.', '$10K to $50K/mo enterprise.'],
      muted: true,
    },
    {
      name: 'TryOn',
      bullets: ['Real 3D avatar, real cloth physics.', 'Per-SKU fit confidence.', 'Brand keeps the data and the PDP.'],
      muted: false,
    },
  ];
  const tiers = [
    { name: 'Free', price: '$0', sub: '200 sessions' },
    { name: 'Studio', price: '$149', sub: '2,500 sessions' },
    { name: 'Brand', price: '$2,490', sub: '40,000 sessions' },
    { name: 'Scale', price: 'Talk to us', sub: 'Multi-brand' },
  ];

  return (
    <section style={{
      background: C.surface, color: C.ink,
      padding: '88px 32px',
      borderBottom: `1px solid ${C.line}`,
    }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <h2 style={{
          ...headingStyle('clamp(36px, 4.5vw, 64px)'),
          marginBottom: 14, maxWidth: 920,
        }}>
          Pay less than the cost of one return per day.
        </h2>
        <p style={{
          ...bodyStyle, color: C.mute, maxWidth: 720, marginBottom: 48,
        }}>
          Built for Shopify Plus fashion brands losing six figures a month to returns. Save tens of thousands per month, charged less than the cost of one return per day.
        </p>

        <div style={{ marginBottom: 56 }}>
          <div style={{
            fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600, color: C.ink, marginBottom: 14,
          }}>Why TryOn</div>
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 0,
            border: `1px solid ${C.line}`,
          }}>
            {cmp.map((col, i) => (
              <div key={col.name} style={{
                background: col.muted ? C.bg : C.cardBg,
                color: col.muted ? C.ink : C.cardInk,
                padding: '28px 24px',
                borderRight: i < cmp.length - 1 ? `1px solid ${C.line}` : 'none',
                display: 'flex', flexDirection: 'column', gap: 16,
              }}>
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600,
                  color: col.muted ? C.mute : C.cardMute,
                }}>{col.name}</div>
                <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {col.bullets.map(b => (
                    <li key={b} style={{
                      fontFamily: 'var(--display)', fontSize: 14, lineHeight: 1.5,
                      color: col.muted ? C.ink : C.cardInk,
                      fontWeight: col.muted ? 400 : 500,
                    }}>{b}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1.4fr', gap: 40, alignItems: 'center',
          marginBottom: 56,
        }}>
          <div>
            <div style={{
              fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600, color: C.ink, marginBottom: 10,
            }}>Shopify integration</div>
            <h3 style={{ ...headingStyle('clamp(26px, 3vw, 40px)'), marginBottom: 12 }}>
              8 lines. Live in a week.
            </h3>
            <p style={{ ...bodyStyle, fontSize: 15, color: C.mute, maxWidth: 380 }}>
              Drop the theme block onto any Shopify store. Embed the widget on your PDP. The widget fetches a fit report from our API. No SDK install, no model upload, no agency.
            </p>
          </div>
          <pre style={{
            background: C.cardBg, color: C.cardInk,
            padding: '24px 28px',
            fontFamily: 'var(--mono)', fontSize: 12.5, lineHeight: 1.6,
            border: `1px solid ${C.cardBg}`, borderRadius: 16,
            margin: 0, overflowX: 'auto',
          }}>{`{% comment %} TryOn widget block {% endcomment %}
<div id="tryon-widget"
     data-shop="{{ shop.permanent_domain }}"
     data-product="{{ product.id }}"
     data-variant="{{ product.selected_variant.id }}">
</div>
<script src="https://cdn.tryon.global/v1/widget.js" defer>
</script>`}</pre>
        </div>

        <div>
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 14,
          }}>
            <div style={{ fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600, color: C.ink }}>
              Pricing
            </div>
            <button
              onClick={() => router.push('/pricing')}
              style={{
                background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                fontFamily: 'var(--display)', fontSize: 14, color: C.ink, fontWeight: 600,
              }}
            >See full pricing →</button>
          </div>
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 0,
            border: `1px solid ${C.line}`,
          }}>
            {tiers.map((t, i) => (
              <button
                key={t.name}
                onClick={() => router.push('/pricing')}
                style={{
                  background: C.bg,
                  borderRight: i < tiers.length - 1 ? `1px solid ${C.line}` : 'none',
                  border: 'none',
                  padding: '24px 22px',
                  textAlign: 'left',
                  cursor: 'pointer',
                  display: 'flex', flexDirection: 'column', gap: 8,
                  color: C.ink,
                }}
              >
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 13, color: C.mute, fontWeight: 600,
                }}>{t.name}</div>
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 28, fontWeight: 700,
                  letterSpacing: '-0.02em', lineHeight: 1, color: C.ink,
                }}>{t.price}</div>
                <div style={{ fontFamily: 'var(--display)', fontSize: 13, color: C.mute }}>{t.sub}</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── For Shoppers ─── */
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
      background: C.bg, color: C.ink,
      padding: '88px 32px',
      borderBottom: `1px solid ${C.line}`,
    }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 40, alignItems: 'center' }}>
          <div>
            <h2 style={{
              ...headingStyle('clamp(36px, 4.5vw, 64px)'),
              marginBottom: 18,
            }}>
              One login. Every brand.
            </h2>
            <p style={{
              ...bodyStyle, color: C.mute, maxWidth: 480, marginBottom: 26,
            }}>
              Free, forever. Build your fit passport once. Wear every garment we host across every brand on Earth. Build outfits, save what you love, see what fits before you check out.
            </p>

            <form onSubmit={submit} style={{
              display: 'flex', alignItems: 'stretch',
              border: `1px solid ${C.line}`,
              borderRadius: 9999,
              overflow: 'hidden',
              maxWidth: 520,
              background: C.surface,
              padding: 4,
            }}>
              <input
                type="email"
                placeholder="you@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{
                  background: 'transparent', border: 'none', outline: 'none',
                  padding: '10px 18px', flex: 1,
                  fontFamily: 'var(--display)', fontSize: 15, fontWeight: 500,
                  color: C.ink,
                }}
              />
              <button
                type="submit"
                style={{
                  background: COBALT, color: '#FFFFFF',
                  padding: '0 22px', border: 'none', borderRadius: 9999,
                  fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600,
                  letterSpacing: '-0.005em',
                  cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10,
                }}
              >Get my passport <span>→</span></button>
            </form>
          </div>

          <div style={{
            border: `1px solid ${C.line}`,
            background: '#ffffff',
            aspectRatio: '4/3', overflow: 'hidden',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: 20, boxSizing: 'border-box',
          }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/redesign/wishlist.png"
              alt="Closet and wishlist"
              style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
            />
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
      background: C.bg, color: C.ink, padding: '40px 32px 48px',
    }}>
      <div style={{
        maxWidth: 1280, margin: '0 auto',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 24,
        flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={C.ink === '#0A0A0A' ? '/redesign/wordmark.png' : '/redesign/wordmark-white.png'}
            alt="TryOn"
            style={{ height: 14, width: 'auto', display: 'block' }}
          />
          <div style={{ fontFamily: 'var(--display)', fontSize: 13, color: C.mute }}>
            TryOn, 2026
          </div>
        </div>
        <div style={{ display: 'flex', gap: 22 }}>
          {[
            { label: 'Pricing', href: '/pricing' },
            { label: 'Demo', href: '/demo' },
            { label: 'Privacy', href: '/privacy' },
            { label: 'Sign in', href: '/login' },
          ].map(it => (
            <button
              key={it.label}
              onClick={() => router.push(it.href)}
              style={{
                background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                fontFamily: 'var(--display)', fontSize: 13, color: C.mute, fontWeight: 500,
              }}
            >{it.label}</button>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── Mobile sections (compressed but same content) ─── */
function MobileHero() {
  const C = useC();
  const router = useRouter();
  const [vignetteIdx, setVignetteIdx] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setVignetteIdx((i) => (i + 1) % PROBLEM_VIGNETTES.length);
    }, 5500);
    return () => clearInterval(id);
  }, []);

  return (
    <section style={{
      background: C.bg, color: C.ink,
      padding: '32px 18px 36px',
      borderBottom: `1px solid ${C.line}`,
    }}>
      <div style={{
        fontFamily: 'var(--mono)', fontSize: 11, color: C.mute,
        letterSpacing: '0.08em', textTransform: 'uppercase', fontWeight: 500,
        marginBottom: 18,
      }}>
        TryOn — Fit before you buy
      </div>
      <h1 style={{
        fontFamily: 'var(--display)', fontWeight: 900,
        fontSize: 'clamp(40px, 11vw, 64px)',
        letterSpacing: '-0.04em', lineHeight: 0.92,
        margin: '0 0 22px',
      }}>
        Try clothes on yourself. Before you buy.
      </h1>

      <div style={{
        position: 'relative',
        borderRadius: 24, overflow: 'hidden',
        background: C.surface, border: `1px solid ${C.line}`,
        marginBottom: 22,
        minHeight: 360,
      }}>
        <AvatarHero height="48vh" interactive={true} rotateSpeed={0.7} />
        <div style={{
          position: 'absolute', bottom: 12, left: 12,
          fontFamily: 'var(--mono)', fontSize: 10, color: C.mute,
          letterSpacing: '0.08em', textTransform: 'uppercase',
          background: C.bg, padding: '5px 10px', borderRadius: 9999,
          border: `1px solid ${C.line}`,
        }}>
          Ramin Studios — Size M
        </div>
      </div>

      <div style={{
        minHeight: 100,
        fontFamily: 'var(--display)', fontSize: 16, lineHeight: 1.45,
        color: C.mute, fontWeight: 400, letterSpacing: '-0.005em',
        marginBottom: 22,
      }}>
        <span
          key={vignetteIdx}
          style={{
            animation: 'ds-fade-in 0.6s cubic-bezier(0.22, 0.61, 0.36, 1)',
            display: 'inline-block',
          }}
        >
          {PROBLEM_VIGNETTES[vignetteIdx]}
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <button
          onClick={() => router.push('/demo')}
          style={{
            background: COBALT, color: '#FFFFFF', border: 'none',
            padding: '14px 22px', borderRadius: 9999,
            fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600,
            letterSpacing: '-0.005em',
            cursor: 'pointer',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          }}
        >Try the demo <span>→</span></button>
        <button
          onClick={() => router.push('/signup')}
          style={{
            background: 'transparent', color: C.ink,
            border: `1px solid ${C.ink}`,
            padding: '14px 22px', borderRadius: 9999,
            fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600,
            letterSpacing: '-0.005em',
            cursor: 'pointer',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          }}
        >Build your passport</button>
      </div>
    </section>
  );
}

function MobileBrandShopperTiles() {
  const C = useC();
  const router = useRouter();
  return (
    <section style={{
      background: C.bg, color: C.ink, padding: '52px 18px',
      borderBottom: `1px solid ${C.line}`,
    }}>
      <h2 style={{ ...headingStyle('30px'), marginBottom: 14 }}>
        Built for both sides.
      </h2>
      <p style={{ ...bodyStyle, fontSize: 14, color: C.mute, marginBottom: 22 }}>
        Brands cut returns. Shoppers wear every brand without guessing a size.
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <PathTile
          tag="For brands"
          title="I am a brand"
          sub="Cut returns. Lift conversion."
          cta="See pricing →"
          onClick={() => router.push('/pricing')}
          C={C}
        />
        <PathTile
          tag="For shoppers"
          title="I am a shopper"
          sub="Free, forever. One passport, every brand."
          cta="Sign up free →"
          onClick={() => router.push('/signup')}
          C={C}
        />
      </div>
    </section>
  );
}

function MobileComponents() {
  const C = useC();
  const items = [
    { tag: 'Fit Passport', desc: 'A 3D avatar of you, rigged from 12 measurements.', image: '/redesign/fit-passport.jpg' },
    { tag: 'Garment Bind', desc: 'Real cloth physics on real photography.', image: '/redesign/garment-bind.jpg' },
    { tag: 'Fit Report', desc: 'Per-SKU confidence and size signal.', image: '/redesign/fit-report.jpg' },
  ];
  return (
    <section style={{
      background: C.surface, color: C.ink,
      padding: '52px 18px',
      borderBottom: `1px solid ${C.line}`,
    }}>
      <h2 style={{ ...headingStyle('30px'), marginBottom: 22 }}>
        The protocol. Three pieces.
      </h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {items.map(it => (
          <div key={it.tag} style={{
            border: `1px solid ${C.line}`, borderRadius: 16, background: C.bg, overflow: 'hidden',
          }}>
            <div style={{
              aspectRatio: '4/5', background: '#ffffff',
              display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
              padding: 14, boxSizing: 'border-box',
              borderBottom: `1px solid ${C.line}`,
            }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={it.image} alt={it.tag} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
            </div>
            <div style={{ padding: '16px 18px 20px' }}>
              <div style={{ fontFamily: 'var(--display)', fontSize: 16, fontWeight: 600, color: C.ink, marginBottom: 4 }}>
                {it.tag}
              </div>
              <div style={{ ...bodyStyle, fontSize: 13.5, color: C.mute }}>{it.desc}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function MobileEvidence() {
  const C = useC();
  const wasteRows = [
    { k: 'Returns avoided', v: 40, suffix: '%', sub: 'less landfill, less reverse logistics.' },
    { k: 'Overproduction cut', v: 18, suffix: '%', sub: 'closer to real demand.' },
    { k: 'CO₂e per order', v: 2.4, suffix: 'kg', sub: 'when a return is prevented.', decimals: 1 },
  ];
  const rulebook = [
    { date: 'Jul 2026', title: 'EU bans destruction of unsold apparel.' },
    { date: 'Sep 2026', title: 'ECGT applies. Anti-greenwashing.' },
    { date: '2028', title: 'DPP mandatory for textiles.' },
  ];
  return (
    <section style={{
      background: C.bg, color: C.ink, padding: '52px 18px',
      borderBottom: `1px solid ${C.line}`,
    }}>
      <h2 style={{ ...headingStyle('30px'), marginBottom: 14 }}>
        Fit is a climate problem.
      </h2>
      <p style={{ ...bodyStyle, fontSize: 14, color: C.mute, marginBottom: 22 }}>
        70% of fashion returns are caused by fit (McKinsey). In 2022, 9.5 billion pounds of US returns went to landfill, emitting 24 million tonnes of CO₂ (Optoro).
      </p>

      <div style={{
        border: `1px solid ${C.line}`, borderRadius: 16, background: C.surface,
        padding: 22, marginBottom: 16,
      }}>
        <div style={{
          fontFamily: 'var(--display)', fontSize: 12, color: C.mute, fontWeight: 500, marginBottom: 6,
        }}>Ramin pilot, 14 days</div>
        <div style={{
          fontFamily: 'var(--display)', fontSize: 56, fontWeight: 700,
          letterSpacing: '-0.04em', lineHeight: 1, color: C.ink,
        }}>
          <CountUp to={94} />%
        </div>
        <div style={{ ...bodyStyle, fontSize: 13, color: C.mute, marginTop: 6 }}>
          of widget opens convert to a try-on.
        </div>
      </div>

      <div style={{ border: `1px solid ${C.line}`, borderRadius: 16, background: C.surface, marginBottom: 22 }}>
        <div style={{
          padding: '12px 16px', borderBottom: `1px solid ${C.line}`,
          display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
        }}>
          <div style={{ fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600, color: C.ink }}>
            Waste ledger
          </div>
          <div style={{ fontFamily: 'var(--display)', fontSize: 12, color: C.mute }}>per 1,000 orders</div>
        </div>
        {wasteRows.map((r, i) => (
          <div key={r.k} style={{
            padding: '12px 16px',
            borderBottom: i < wasteRows.length - 1 ? `1px solid ${C.line}` : 'none',
          }}>
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4, gap: 12,
            }}>
              <div style={{ fontFamily: 'var(--display)', fontSize: 13, fontWeight: 500, color: C.ink }}>{r.k}</div>
              <div style={{
                fontFamily: 'var(--display)', fontSize: 20, fontWeight: 600,
                letterSpacing: '-0.02em', color: C.ink,
              }}>
                −<CountUp to={r.v} decimals={r.decimals || 0} />{r.suffix}
              </div>
            </div>
            <div style={{ fontFamily: 'var(--display)', fontSize: 12, color: C.mute }}>{r.sub}</div>
          </div>
        ))}
        <div style={{
          padding: '10px 16px', borderTop: `1px solid ${C.line}`,
          fontFamily: 'var(--display)', fontSize: 11, color: C.mute,
        }}>Sources: McKinsey, Optoro, TryOn pilot 2026.</div>
      </div>

      <div style={{
        fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600, color: C.ink, marginBottom: 10,
      }}>EU rulebook, 2026 to 2028</div>
      <div style={{ border: `1px solid ${C.line}`, borderRadius: 16, background: C.surface }}>
        {rulebook.map((r, i) => (
          <div key={r.date} style={{
            padding: '14px 16px',
            borderBottom: i < rulebook.length - 1 ? `1px solid ${C.line}` : 'none',
          }}>
            <div style={{
              fontFamily: 'var(--display)', fontSize: 12, color: C.mute, fontWeight: 500, marginBottom: 4,
            }}>{r.date}</div>
            <div style={{
              fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600, color: C.ink, lineHeight: 1.3,
            }}>{r.title}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function MobileBrands() {
  const C = useC();
  const router = useRouter();
  const tiers = [
    { name: 'Free', price: '$0', sub: '200 sessions' },
    { name: 'Studio', price: '$149', sub: '2,500 sessions' },
    { name: 'Brand', price: '$2,490', sub: '40,000 sessions' },
    { name: 'Scale', price: 'Talk to us', sub: 'Multi-brand' },
  ];
  return (
    <section style={{ background: C.surface, color: C.ink, padding: '52px 18px', borderBottom: `1px solid ${C.line}` }}>
      <h2 style={{ ...headingStyle('30px'), marginBottom: 12 }}>
        Pay less than one return per day.
      </h2>
      <p style={{ ...bodyStyle, fontSize: 13.5, color: C.mute, marginBottom: 22 }}>
        Built for Shopify Plus brands losing six figures a month to returns.
      </p>

      <div style={{
        border: `1px solid ${C.line}`, marginBottom: 18, background: C.bg,
      }}>
        {tiers.map((t, i) => (
          <button
            key={t.name}
            onClick={() => router.push('/pricing')}
            style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              width: '100%', padding: '16px 18px',
              borderBottom: i < tiers.length - 1 ? `1px solid ${C.line}` : 'none',
              background: 'transparent', border: 'none', cursor: 'pointer',
              color: C.ink, textAlign: 'left',
            }}
          >
            <div>
              <div style={{ fontFamily: 'var(--display)', fontSize: 12.5, color: C.mute, fontWeight: 600, marginBottom: 4 }}>
                {t.name}
              </div>
              <div style={{ fontFamily: 'var(--display)', fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em' }}>
                {t.price}
              </div>
            </div>
            <div style={{ fontFamily: 'var(--display)', fontSize: 12.5, color: C.mute }}>{t.sub} →</div>
          </button>
        ))}
      </div>

      <button
        onClick={() => router.push('/pricing')}
        style={{
          background: COBALT, color: '#FFFFFF', border: 'none',
          padding: '14px 20px', width: '100%',
          fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600,
          letterSpacing: '-0.005em', cursor: 'pointer',
          borderRadius: 9999,
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 10,
        }}
      >See full pricing <span>→</span></button>
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
    <section style={{ background: C.bg, color: C.ink, padding: '52px 18px', borderBottom: `1px solid ${C.line}` }}>
      <h2 style={{ ...headingStyle('30px'), marginBottom: 12 }}>
        One login. Every brand.
      </h2>
      <p style={{ ...bodyStyle, fontSize: 13.5, color: C.mute, marginBottom: 18 }}>
        Free, forever. Build your fit passport once.
      </p>

      <div style={{
        border: `1px solid ${C.line}`, background: '#ffffff',
        aspectRatio: '4/3',
        display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
        padding: 14, boxSizing: 'border-box', marginBottom: 18,
      }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/redesign/wishlist.png" alt="Closet and wishlist"
          style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
        />
      </div>

      <form onSubmit={submit} style={{
        display: 'flex', alignItems: 'stretch',
        border: `1px solid ${C.line}`,
        borderRadius: 9999,
        overflow: 'hidden',
        background: C.surface,
        padding: 4,
      }}>
        <input
          type="email"
          placeholder="you@email.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{
            background: 'transparent', border: 'none', outline: 'none',
            padding: '10px 16px', flex: 1,
            fontFamily: 'var(--display)', fontSize: 14, fontWeight: 500, color: C.ink, minWidth: 0,
          }}
        />
        <button
          type="submit"
          style={{
            background: COBALT, color: '#FFFFFF',
            padding: '0 16px', border: 'none', borderRadius: 9999,
            fontFamily: 'var(--display)', fontSize: 12.5, fontWeight: 600,
            letterSpacing: '-0.005em',
            cursor: 'pointer', whiteSpace: 'nowrap',
          }}
        >Get my passport</button>
      </form>
    </section>
  );
}

function MobileFooter() {
  const C = useC();
  const router = useRouter();
  return (
    <section style={{
      background: C.bg, color: C.ink, padding: '24px 18px 36px',
      display: 'flex', flexDirection: 'column', gap: 12, alignItems: 'flex-start',
    }}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={C.ink === '#0A0A0A' ? '/redesign/wordmark.png' : '/redesign/wordmark-white.png'}
        alt="TryOn"
        style={{ height: 13, width: 'auto', display: 'block' }}
      />
      <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap' }}>
        {[
          { label: 'Pricing', href: '/pricing' },
          { label: 'Demo', href: '/demo' },
          { label: 'Privacy', href: '/privacy' },
          { label: 'Sign in', href: '/login' },
        ].map(it => (
          <button
            key={it.label}
            onClick={() => router.push(it.href)}
            style={{
              background: 'none', border: 'none', padding: 0, cursor: 'pointer',
              fontFamily: 'var(--display)', fontSize: 13, color: C.mute, fontWeight: 500,
            }}
          >{it.label}</button>
        ))}
      </div>
      <div style={{ fontFamily: 'var(--display)', fontSize: 12, color: C.mute }}>TryOn, 2026</div>
    </section>
  );
}

/* ─── Root ─── */
export function BroadcastLanding({ dark = false }: { dark?: boolean }) {
  const C = dark ? PAL.dark : PAL.light;
  const mobile = useIsMobile();
  const router = useRouter();

  const navLinks = [
    { label: 'Pricing', href: '/pricing' },
    { label: 'Demo', href: '/demo' },
    { label: 'Shoppers', href: '/signup' },
    { label: 'Deck', href: '/pitch-deck.html', external: true },
  ];

  return (
    <ThemeCtx.Provider value={C}>
      <div className="tryon-redesign-root" style={{
        width: '100%', minHeight: '100vh',
        background: C.bg, color: C.ink, position: 'relative',
      }}>
        <SharedNav
          dark={dark}
          links={navLinks}
          rightSlot={mobile ? (
            <NavCta dark={dark} label="Try demo" onClick={() => router.push('/demo')} />
          ) : (
            <>
              <AuthAwareSignInLink dark={dark} />
              <NavCta dark={dark} label="Try the demo →" onClick={() => router.push('/demo')} />
            </>
          )}
        />
        {mobile ? (
          <>
            <MobileHero />
            <MobileComponents />
            <MobileBrandShopperTiles />
            <MobileEvidence />
            <MobileBrands />
            <MobileShoppers />
            <MobileFooter />
          </>
        ) : (
          <>
            <DesktopHero />
            <DesktopComponents />
            <DesktopBrandShopperTiles />
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
