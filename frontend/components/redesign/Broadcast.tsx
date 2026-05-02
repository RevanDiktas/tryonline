'use client';

import React, { createContext, useContext, useEffect, useRef, useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useIsMobile } from './useIsMobile';

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

/* shared style helpers */
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

/* ─── Nav ─── */
function DesktopNav() {
  const C = useC();
  const router = useRouter();
  const hidden = useSmartNav();

  return (
    <div style={{
      position: 'sticky', top: 0, zIndex: 70,
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '20px 32px',
      pointerEvents: 'none',
      marginBottom: -76,
      transform: hidden ? 'translateY(-110%)' : 'translateY(0)',
      transition: 'transform 0.28s cubic-bezier(0.4, 0.0, 0.2, 1)',
    }}>
      <div style={{
        pointerEvents: 'auto',
        display: 'inline-flex', alignItems: 'center', gap: 28,
      }}>
        <button
          type="button"
          onClick={() => router.push('/')}
          style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', display: 'inline-flex' }}
          aria-label="TryOn home"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={C.ink === '#0A0A0A' ? '/redesign/wordmark.png' : '/redesign/wordmark-white.png'}
            alt="TryOn"
            style={{ height: 20, width: 'auto', display: 'block' }}
          />
        </button>
        <div style={{ display: 'flex', gap: 22 }}>
          {[
            { label: 'Pricing', href: '/pricing' },
            { label: 'Demo', href: '/demo' },
            { label: 'Shoppers', href: '/signup' },
          ].map(it => (
            <button
              key={it.label}
              onClick={() => router.push(it.href)}
              style={{
                border: 0, padding: 0, background: 'transparent', cursor: 'pointer',
                fontFamily: 'var(--display)', fontSize: 14,
                color: C.mute, fontWeight: 500,
              }}
            >{it.label}</button>
          ))}
        </div>
      </div>

      <div style={{
        pointerEvents: 'auto',
        display: 'inline-flex', alignItems: 'center', gap: 8,
      }}>
        <button
          onClick={() => router.push('/login')}
          style={{
            padding: '8px 14px', background: 'transparent', border: 'none', color: C.ink,
            fontFamily: 'var(--display)', fontSize: 14, fontWeight: 500, cursor: 'pointer',
          }}
        >Sign in</button>
        <button
          onClick={() => router.push('/demo')}
          style={{
            padding: '10px 18px',
            background: C.ink, color: C.bg, border: 'none',
            fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600, cursor: 'pointer',
            display: 'inline-flex', alignItems: 'center', gap: 8, borderRadius: 999,
          }}
        >Try the demo<span style={{ fontSize: 14 }}>→</span></button>
      </div>
    </div>
  );
}

/* ─── Hero ─── */
function DesktopHero() {
  const C = useC();
  const router = useRouter();

  return (
    <section style={{
      background: C.bg, color: C.ink,
      minHeight: '100dvh',
      padding: '120px 32px 80px',
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
    }}>
      <h1 style={{
        ...headingStyle('clamp(56px, 8vw, 120px)'),
        textAlign: 'center', maxWidth: 1100,
      }}>
        Try on before you buy.
      </h1>

      <p style={{
        ...bodyStyle,
        fontSize: 19, marginTop: 28, marginBottom: 40,
        maxWidth: 620, textAlign: 'center', color: C.mute,
      }}>
        One avatar. Every brand. Real cloth, real measurements, real fit.
        Built for the 2026 EU fashion rulebook.
      </p>

      <button
        onClick={() => router.push('/demo')}
        style={{
          background: C.ink, color: C.bg, border: 'none',
          padding: '16px 28px',
          fontFamily: 'var(--display)', fontSize: 15, fontWeight: 600, cursor: 'pointer',
          display: 'inline-flex', alignItems: 'center', gap: 10,
          borderRadius: 999,
        }}
      >
        Try the demo
        <span style={{ fontSize: 16 }}>→</span>
      </button>

      <div style={{
        marginTop: 24,
        display: 'flex', gap: 18, alignItems: 'center',
        fontFamily: 'var(--display)', fontSize: 14, color: C.mute,
      }}>
        <button
          onClick={() => router.push('/pricing')}
          style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', color: C.ink, fontFamily: 'inherit', fontSize: 'inherit', fontWeight: 500 }}
        >For brands →</button>
        <span style={{ width: 3, height: 3, borderRadius: '50%', background: C.line }} />
        <button
          onClick={() => router.push('/signup')}
          style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', color: C.ink, fontFamily: 'inherit', fontSize: 'inherit', fontWeight: 500 }}
        >For shoppers →</button>
      </div>
    </section>
  );
}

/* ─── Components grid ─── */
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
      padding: '120px 32px',
      borderTop: `1px solid ${C.line}`,
    }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <h2 style={{
          ...headingStyle('clamp(40px, 5vw, 72px)'),
          marginBottom: 56, maxWidth: 760,
        }}>
          The protocol. Three pieces.
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 28 }}>
          {items.map(it => (
            <div key={it.tag} style={{
              border: `1px solid ${C.line}`,
              borderRadius: 14,
              background: C.bg,
              overflow: 'hidden',
              display: 'flex', flexDirection: 'column',
            }}>
              <div style={{
                aspectRatio: '4/5', background: '#ffffff',
                display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
                padding: 24, boxSizing: 'border-box',
                borderBottom: `1px solid ${C.line}`,
              }}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={it.image} alt={it.tag} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
              </div>
              <div style={{ padding: '22px 24px 26px' }}>
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 18, fontWeight: 600,
                  color: C.ink, marginBottom: 8,
                }}>{it.tag}</div>
                <div style={{
                  ...bodyStyle, fontSize: 14.5, color: C.mute,
                }}>{it.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── Evidence: pilot + climate + EU rulebook ─── */
function DesktopEvidence() {
  const C = useC();
  const wasteRows = [
    { k: 'Returns avoided', v: 40, suffix: '%', sub: 'less reverse logistics, less landfill.' },
    { k: 'Overproduction cut', v: 18, suffix: '%', sub: 'brands manufacture closer to real demand.' },
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
      padding: '120px 32px',
      borderTop: `1px solid ${C.line}`,
    }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <h2 style={{
          ...headingStyle('clamp(40px, 5vw, 72px)'),
          marginBottom: 24, maxWidth: 920,
        }}>
          Fit is a climate problem.
        </h2>
        <p style={{
          ...bodyStyle, color: C.mute, maxWidth: 720, marginBottom: 64,
        }}>
          70% of fashion returns are caused by fit (McKinsey, 2024). In 2022, 9.5 billion pounds of US returns went to landfill, emitting 24 million tonnes of CO₂ (Optoro). TryOn kills the return before the order. Fewer trucks. Less plastic. Less polyester pulled out of the ground for stock that nobody wears.
        </p>

        <div style={{
          display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 32, alignItems: 'start',
        }}>
          {/* Left: pilot + waste ledger */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            <div style={{
              border: `1px solid ${C.line}`, borderRadius: 14,
              background: C.surface, padding: 32,
            }}>
              <div style={{
                fontFamily: 'var(--display)', fontSize: 13, color: C.mute,
                fontWeight: 500, marginBottom: 12,
              }}>Ramin Studios pilot, Amsterdam</div>
              <div style={{
                fontFamily: 'var(--display)', fontWeight: 700,
                fontSize: 96, letterSpacing: '-0.04em', lineHeight: 1,
                color: C.ink,
              }}>
                <CountUp to={94} />%
              </div>
              <div style={{ ...bodyStyle, fontSize: 14, color: C.mute, marginTop: 12 }}>
                of widget opens convert to a try-on. Live data, last 14 days.
              </div>
              <div style={{
                marginTop: 20, paddingTop: 20,
                borderTop: `1px solid ${C.line}`,
                display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16,
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
                      fontFamily: 'var(--display)', fontSize: 22, fontWeight: 600,
                      color: C.ink, letterSpacing: '-0.01em',
                    }}>
                      {typeof row.v === 'number' ? <CountUp to={row.v} /> : row.v}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{
              border: `1px solid ${C.line}`, borderRadius: 14,
              background: C.surface,
            }}>
              <div style={{
                padding: '18px 28px', borderBottom: `1px solid ${C.line}`,
                display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
              }}>
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600, color: C.ink,
                }}>Waste ledger</div>
                <div style={{ fontFamily: 'var(--display)', fontSize: 13, color: C.mute }}>
                  per 1,000 orders
                </div>
              </div>
              {wasteRows.map((r, i) => (
                <div key={r.k} style={{
                  padding: '18px 28px',
                  borderBottom: i < wasteRows.length - 1 ? `1px solid ${C.line}` : 'none',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 16,
                }}>
                  <div>
                    <div style={{
                      fontFamily: 'var(--display)', fontSize: 15, fontWeight: 500, color: C.ink,
                    }}>{r.k}</div>
                    <div style={{
                      fontFamily: 'var(--display)', fontSize: 13, color: C.mute, marginTop: 2,
                    }}>{r.sub}</div>
                  </div>
                  <div style={{
                    fontFamily: 'var(--display)', fontSize: 28, fontWeight: 600,
                    letterSpacing: '-0.02em', color: C.ink, whiteSpace: 'nowrap',
                  }}>
                    −<CountUp to={r.v} decimals={r.decimals || 0} />{r.suffix}
                  </div>
                </div>
              ))}
              <div style={{
                padding: '14px 28px', borderTop: `1px solid ${C.line}`,
                fontFamily: 'var(--display)', fontSize: 12, color: C.mute,
              }}>
                Sources: McKinsey 2024, Optoro 2022, TryOn Ramin pilot 2026.
              </div>
            </div>
          </div>

          {/* Right: EU rulebook */}
          <div>
            <div style={{
              fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600, color: C.ink, marginBottom: 16,
            }}>The EU rulebook, 2026 to 2028.</div>
            <div style={{
              border: `1px solid ${C.line}`, borderRadius: 14,
              background: C.surface,
            }}>
              {rulebook.map((r, i) => (
                <div key={r.date} style={{
                  padding: '24px 28px',
                  borderBottom: i < rulebook.length - 1 ? `1px solid ${C.line}` : 'none',
                }}>
                  <div style={{
                    fontFamily: 'var(--display)', fontSize: 13, color: C.mute, fontWeight: 500, marginBottom: 8,
                  }}>{r.date}</div>
                  <div style={{
                    fontFamily: 'var(--display)', fontSize: 19, fontWeight: 600,
                    color: C.ink, lineHeight: 1.3, letterSpacing: '-0.01em',
                  }}>{r.title}</div>
                  <div style={{
                    ...bodyStyle, fontSize: 14, color: C.mute, marginTop: 6,
                  }}>{r.sub}</div>
                </div>
              ))}
            </div>
            <p style={{
              ...bodyStyle, fontSize: 14, color: C.mute, marginTop: 16,
            }}>
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
      padding: '120px 32px',
      borderTop: `1px solid ${C.line}`,
    }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <h2 style={{
          ...headingStyle('clamp(40px, 5vw, 72px)'),
          marginBottom: 16, maxWidth: 920,
        }}>
          Pay less than the cost of one return per day.
        </h2>
        <p style={{
          ...bodyStyle, color: C.mute, maxWidth: 720, marginBottom: 64,
        }}>
          Built for Shopify Plus fashion brands losing six figures a month to returns. Save tens of thousands per month, charged less than the cost of one return per day.
        </p>

        <div style={{ marginBottom: 72 }}>
          <div style={{
            fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600, color: C.ink, marginBottom: 16,
          }}>Why TryOn</div>
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 0,
            border: `1px solid ${C.line}`, borderRadius: 14, overflow: 'hidden',
          }}>
            {cmp.map((col, i) => (
              <div key={col.name} style={{
                background: col.muted ? C.bg : C.cardBg,
                color: col.muted ? C.ink : C.cardInk,
                padding: '32px 28px',
                borderRight: i < cmp.length - 1 ? `1px solid ${C.line}` : 'none',
                display: 'flex', flexDirection: 'column', gap: 18,
              }}>
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600,
                  color: col.muted ? C.mute : C.cardMute,
                }}>{col.name}</div>
                <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {col.bullets.map(b => (
                    <li key={b} style={{
                      fontFamily: 'var(--display)', fontSize: 15, lineHeight: 1.5,
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
          display: 'grid', gridTemplateColumns: '1fr 1.4fr', gap: 56, alignItems: 'center',
          marginBottom: 72,
        }}>
          <div>
            <div style={{
              fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600, color: C.ink, marginBottom: 12,
            }}>Shopify integration</div>
            <h3 style={{
              ...headingStyle('clamp(28px, 3.5vw, 48px)'),
              marginBottom: 14,
            }}>
              8 lines. Live in a week.
            </h3>
            <p style={{
              ...bodyStyle, color: C.mute, maxWidth: 380,
            }}>
              Drop the theme block onto any Shopify store. Embed the widget on your PDP. The widget fetches a fit report from our API. No SDK install, no model upload, no agency.
            </p>
          </div>
          <pre style={{
            background: C.cardBg, color: C.cardInk,
            padding: '28px 32px',
            fontFamily: 'var(--mono)', fontSize: 13, lineHeight: 1.6,
            border: `1px solid ${C.cardBg}`, borderRadius: 14,
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
            display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 16,
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
            border: `1px solid ${C.line}`, borderRadius: 14, overflow: 'hidden',
          }}>
            {tiers.map((t, i) => (
              <button
                key={t.name}
                onClick={() => router.push('/pricing')}
                style={{
                  background: C.bg,
                  borderRight: i < tiers.length - 1 ? `1px solid ${C.line}` : 'none',
                  border: 'none',
                  padding: '28px 24px',
                  textAlign: 'left',
                  cursor: 'pointer',
                  display: 'flex', flexDirection: 'column', gap: 10,
                  color: C.ink,
                }}
              >
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 13, color: C.mute, fontWeight: 600,
                }}>{t.name}</div>
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 30, fontWeight: 700,
                  letterSpacing: '-0.02em', lineHeight: 1, color: C.ink,
                }}>{t.price}</div>
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 13, color: C.mute,
                }}>{t.sub}</div>
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
      padding: '120px 32px',
      borderTop: `1px solid ${C.line}`,
    }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 56, alignItems: 'center' }}>
          <div>
            <h2 style={{
              ...headingStyle('clamp(40px, 5vw, 72px)'),
              marginBottom: 20,
            }}>
              One login. Every brand.
            </h2>
            <p style={{
              ...bodyStyle, color: C.mute, maxWidth: 480, marginBottom: 32,
            }}>
              Free, forever. Build your fit passport once. Wear every garment we host across every brand on Earth. Build outfits, save what you love, see what fits before you check out.
            </p>

            <form onSubmit={submit} style={{
              display: 'flex', alignItems: 'stretch',
              border: `1px solid ${C.ink}`, borderRadius: 999,
              maxWidth: 480, overflow: 'hidden',
              background: C.surface,
            }}>
              <input
                type="email"
                placeholder="you@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{
                  background: 'transparent', border: 'none', outline: 'none',
                  padding: '14px 22px', flex: 1,
                  fontFamily: 'var(--display)', fontSize: 16, fontWeight: 500,
                  color: C.ink,
                }}
              />
              <button
                type="submit"
                style={{
                  background: C.ink, color: C.bg,
                  padding: '0 24px', border: 'none',
                  fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600,
                  cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10,
                }}
              >Get my passport <span>→</span></button>
            </form>
          </div>

          <div style={{
            border: `1px solid ${C.line}`, borderRadius: 14,
            background: '#ffffff',
            aspectRatio: '4/5', overflow: 'hidden', position: 'relative',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: 24, boxSizing: 'border-box',
          }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/redesign/wishlist.png"
              alt="Closet and wishlist"
              style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
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
      background: C.bg, color: C.ink, padding: '48px 32px 56px',
      borderTop: `1px solid ${C.line}`,
    }}>
      <div style={{
        maxWidth: 1280, margin: '0 auto',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 24,
        flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={C.ink === '#0A0A0A' ? '/redesign/wordmark.png' : '/redesign/wordmark-white.png'}
            alt="TryOn"
            style={{ height: 16, width: 'auto', display: 'block' }}
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

/* ─── Mobile ─── */
function MobileNav() {
  const C = useC();
  const router = useRouter();
  const hidden = useSmartNav();
  return (
    <div style={{
      position: 'sticky', top: 0, zIndex: 70,
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '14px 16px', pointerEvents: 'none',
      background: C.bg + 'cc', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
      borderBottom: `1px solid ${C.line}`,
      transform: hidden ? 'translateY(-110%)' : 'translateY(0)',
      transition: 'transform 0.28s cubic-bezier(0.4, 0.0, 0.2, 1)',
    }}>
      <button
        type="button"
        onClick={() => router.push('/')}
        style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', display: 'inline-flex', pointerEvents: 'auto' }}
        aria-label="TryOn home"
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={C.ink === '#0A0A0A' ? '/redesign/wordmark.png' : '/redesign/wordmark-white.png'}
          alt="TryOn"
          style={{ height: 16, width: 'auto', display: 'block' }}
        />
      </button>
      <button
        onClick={() => router.push('/demo')}
        style={{
          padding: '8px 14px', background: C.ink, color: C.bg, border: 'none',
          fontFamily: 'var(--display)', fontSize: 12, fontWeight: 600, cursor: 'pointer',
          borderRadius: 999, pointerEvents: 'auto',
        }}
      >Try the demo →</button>
    </div>
  );
}

function MobileHero() {
  const C = useC();
  const router = useRouter();
  return (
    <section style={{
      background: C.bg, color: C.ink,
      minHeight: 'calc(100dvh - 60px)',
      padding: '64px 20px 40px',
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
    }}>
      <h1 style={{
        ...headingStyle('44px'),
        textAlign: 'center', maxWidth: 520,
      }}>
        Try on before you buy.
      </h1>
      <p style={{
        ...bodyStyle, fontSize: 15, marginTop: 18, marginBottom: 28,
        maxWidth: 360, textAlign: 'center', color: C.mute,
      }}>
        One avatar. Every brand. Real cloth, real measurements, real fit. Built for the 2026 EU fashion rulebook.
      </p>
      <button
        onClick={() => router.push('/demo')}
        style={{
          background: C.ink, color: C.bg, border: 'none',
          padding: '14px 24px',
          fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600, cursor: 'pointer',
          display: 'inline-flex', alignItems: 'center', gap: 10,
          borderRadius: 999,
        }}
      >Try the demo <span>→</span></button>
      <div style={{
        marginTop: 18,
        display: 'flex', gap: 14, alignItems: 'center',
        fontFamily: 'var(--display)', fontSize: 13, color: C.mute,
      }}>
        <button onClick={() => router.push('/pricing')}
          style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', color: C.ink, fontFamily: 'inherit', fontSize: 'inherit', fontWeight: 500 }}
        >For brands →</button>
        <span style={{ width: 3, height: 3, borderRadius: '50%', background: C.line }} />
        <button onClick={() => router.push('/signup')}
          style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', color: C.ink, fontFamily: 'inherit', fontSize: 'inherit', fontWeight: 500 }}
        >For shoppers →</button>
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
      padding: '64px 20px',
      borderTop: `1px solid ${C.line}`,
    }}>
      <h2 style={{ ...headingStyle('32px'), marginBottom: 28 }}>
        The protocol. Three pieces.
      </h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {items.map(it => (
          <div key={it.tag} style={{
            border: `1px solid ${C.line}`, borderRadius: 12, background: C.bg,
            overflow: 'hidden',
          }}>
            <div style={{
              aspectRatio: '4/3', background: '#ffffff',
              display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
              padding: 16, boxSizing: 'border-box',
              borderBottom: `1px solid ${C.line}`,
            }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={it.image} alt={it.tag} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
            </div>
            <div style={{ padding: '18px 18px 22px' }}>
              <div style={{
                fontFamily: 'var(--display)', fontSize: 16, fontWeight: 600, color: C.ink, marginBottom: 6,
              }}>{it.tag}</div>
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
      background: C.bg, color: C.ink, padding: '64px 20px',
      borderTop: `1px solid ${C.line}`,
    }}>
      <h2 style={{ ...headingStyle('32px'), marginBottom: 16 }}>
        Fit is a climate problem.
      </h2>
      <p style={{ ...bodyStyle, fontSize: 14, color: C.mute, marginBottom: 28 }}>
        70% of fashion returns are caused by fit (McKinsey). In 2022, 9.5 billion pounds of US returns went to landfill, emitting 24 million tonnes of CO₂ (Optoro). TryOn kills the return before the order.
      </p>

      <div style={{
        border: `1px solid ${C.line}`, borderRadius: 12, background: C.surface,
        padding: 24, marginBottom: 18,
      }}>
        <div style={{
          fontFamily: 'var(--display)', fontSize: 12, color: C.mute, fontWeight: 500, marginBottom: 8,
        }}>Ramin pilot, 14 days</div>
        <div style={{
          fontFamily: 'var(--display)', fontSize: 64, fontWeight: 700,
          letterSpacing: '-0.04em', lineHeight: 1, color: C.ink,
        }}>
          <CountUp to={94} />%
        </div>
        <div style={{ ...bodyStyle, fontSize: 13, color: C.mute, marginTop: 8 }}>
          of widget opens convert to a try-on.
        </div>
      </div>

      <div style={{
        border: `1px solid ${C.line}`, borderRadius: 12, background: C.surface, marginBottom: 24,
      }}>
        <div style={{
          padding: '14px 18px', borderBottom: `1px solid ${C.line}`,
          display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
        }}>
          <div style={{ fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600, color: C.ink }}>
            Waste ledger
          </div>
          <div style={{ fontFamily: 'var(--display)', fontSize: 12, color: C.mute }}>
            per 1,000 orders
          </div>
        </div>
        {wasteRows.map((r, i) => (
          <div key={r.k} style={{
            padding: '14px 18px',
            borderBottom: i < wasteRows.length - 1 ? `1px solid ${C.line}` : 'none',
          }}>
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4, gap: 12,
            }}>
              <div style={{
                fontFamily: 'var(--display)', fontSize: 13, fontWeight: 500, color: C.ink,
              }}>{r.k}</div>
              <div style={{
                fontFamily: 'var(--display)', fontSize: 22, fontWeight: 600,
                letterSpacing: '-0.02em', color: C.ink,
              }}>
                −<CountUp to={r.v} decimals={r.decimals || 0} />{r.suffix}
              </div>
            </div>
            <div style={{ fontFamily: 'var(--display)', fontSize: 12, color: C.mute }}>{r.sub}</div>
          </div>
        ))}
        <div style={{
          padding: '12px 18px', borderTop: `1px solid ${C.line}`,
          fontFamily: 'var(--display)', fontSize: 11, color: C.mute,
        }}>Sources: McKinsey, Optoro, TryOn pilot 2026.</div>
      </div>

      <div style={{
        fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600, color: C.ink, marginBottom: 12,
      }}>EU rulebook, 2026 to 2028</div>
      <div style={{ border: `1px solid ${C.line}`, borderRadius: 12, background: C.surface }}>
        {rulebook.map((r, i) => (
          <div key={r.date} style={{
            padding: '16px 18px',
            borderBottom: i < rulebook.length - 1 ? `1px solid ${C.line}` : 'none',
          }}>
            <div style={{
              fontFamily: 'var(--display)', fontSize: 12, color: C.mute, fontWeight: 500, marginBottom: 4,
            }}>{r.date}</div>
            <div style={{
              fontFamily: 'var(--display)', fontSize: 15, fontWeight: 600, color: C.ink, lineHeight: 1.3,
            }}>{r.title}</div>
          </div>
        ))}
      </div>
      <p style={{ ...bodyStyle, fontSize: 13, color: C.mute, marginTop: 14 }}>
        Every garment we render is already a 3D digital twin. DPP-ready by design.
      </p>
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
    <section style={{ background: C.surface, color: C.ink, padding: '64px 20px', borderTop: `1px solid ${C.line}` }}>
      <h2 style={{ ...headingStyle('32px'), marginBottom: 14 }}>
        Pay less than one return per day.
      </h2>
      <p style={{ ...bodyStyle, fontSize: 14, color: C.mute, marginBottom: 28 }}>
        Built for Shopify Plus brands losing six figures a month to returns. Save tens of thousands per month.
      </p>

      <div style={{
        border: `1px solid ${C.line}`, borderRadius: 12, marginBottom: 20, background: C.bg, overflow: 'hidden',
      }}>
        {tiers.map((t, i) => (
          <button
            key={t.name}
            onClick={() => router.push('/pricing')}
            style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              width: '100%', padding: '18px 18px',
              borderBottom: i < tiers.length - 1 ? `1px solid ${C.line}` : 'none',
              background: 'transparent', border: 'none', cursor: 'pointer',
              color: C.ink, textAlign: 'left',
            }}
          >
            <div>
              <div style={{ fontFamily: 'var(--display)', fontSize: 13, color: C.mute, fontWeight: 600, marginBottom: 4 }}>
                {t.name}
              </div>
              <div style={{ fontFamily: 'var(--display)', fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em' }}>
                {t.price}
              </div>
            </div>
            <div style={{ fontFamily: 'var(--display)', fontSize: 13, color: C.mute }}>{t.sub} →</div>
          </button>
        ))}
      </div>

      <button
        onClick={() => router.push('/pricing')}
        style={{
          background: C.ink, color: C.bg, border: 'none',
          padding: '14px 22px', width: '100%',
          fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600, cursor: 'pointer',
          borderRadius: 999, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 10,
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
    <section style={{ background: C.bg, color: C.ink, padding: '64px 20px', borderTop: `1px solid ${C.line}` }}>
      <h2 style={{ ...headingStyle('32px'), marginBottom: 14 }}>
        One login. Every brand.
      </h2>
      <p style={{ ...bodyStyle, fontSize: 14, color: C.mute, marginBottom: 24 }}>
        Free, forever. Build your fit passport once. Wear every brand on Earth.
      </p>

      <div style={{
        border: `1px solid ${C.line}`, borderRadius: 12, background: '#ffffff',
        aspectRatio: '4/5', overflow: 'hidden',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 16, boxSizing: 'border-box', marginBottom: 22,
      }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/redesign/wishlist.png" alt="Closet and wishlist"
          style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
        />
      </div>

      <form onSubmit={submit} style={{
        display: 'flex', alignItems: 'stretch',
        border: `1px solid ${C.ink}`, borderRadius: 999,
        overflow: 'hidden', background: C.surface,
      }}>
        <input
          type="email"
          placeholder="you@email.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{
            background: 'transparent', border: 'none', outline: 'none',
            padding: '12px 18px', flex: 1,
            fontFamily: 'var(--display)', fontSize: 15, fontWeight: 500, color: C.ink, minWidth: 0,
          }}
        />
        <button
          type="submit"
          style={{
            background: C.ink, color: C.bg, padding: '0 18px', border: 'none',
            fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600, cursor: 'pointer',
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
      background: C.bg, color: C.ink, padding: '32px 20px 48px',
      borderTop: `1px solid ${C.line}`,
      display: 'flex', flexDirection: 'column', gap: 14, alignItems: 'flex-start',
    }}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={C.ink === '#0A0A0A' ? '/redesign/wordmark.png' : '/redesign/wordmark-white.png'}
        alt="TryOn"
        style={{ height: 14, width: 'auto', display: 'block' }}
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
  return (
    <ThemeCtx.Provider value={C}>
      <div className="tryon-redesign-root" style={{
        width: '100%', minHeight: '100vh',
        background: C.bg, color: C.ink, position: 'relative',
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
