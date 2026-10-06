'use client';

import React, { createContext, useContext, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { useIsMobile } from './useIsMobile';
import { SharedNav, NavCta, AuthAwareSignInLink } from './SharedNav';
import { siteLinks } from './siteLinks';
import { SiteFooter } from './SiteFooter';
import { PLANS, TRIAL_DAYS } from '@/lib/plans';

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


/* ─── The example result every section points at: one size, every size scored ─── */
const EXAMPLE_SCORES = [
  { size: 'M', score: 31 },
  { size: 'L', score: 96, best: true },
  { size: 'XL', score: 23 },
];

function MatchStrip({ compact }: { compact?: boolean }) {
  const C = useC();
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: compact ? 8 : 10, flexWrap: 'wrap' }}>
      <span style={{
        fontFamily: 'var(--mono)', fontSize: compact ? 10 : 11, color: C.mute,
        letterSpacing: '0.08em', textTransform: 'uppercase', fontWeight: 500, marginRight: 4,
      }}>Example result</span>
      {EXAMPLE_SCORES.map(s => (
        <span key={s.size} style={{
          fontFamily: 'var(--display)', fontSize: compact ? 13 : 14, fontWeight: s.best ? 700 : 500,
          color: s.best ? C.ink : C.mute,
          border: `1px solid ${s.best ? C.ink : C.line}`,
          borderRadius: 9999, padding: compact ? '5px 11px' : '6px 13px',
          fontVariantNumeric: 'tabular-nums',
        }}>{s.size} · {s.score}%</span>
      ))}
    </div>
  );
}

/* A drawn copy of the size card's result, so the card shows the real thing, not a stock photo. */
function SizeResultMock() {
  const C = useC();
  return (
    <div style={{
      width: '100%', maxWidth: 300, background: C.surface, color: C.ink,
      border: `1px solid ${C.line}`, borderRadius: 18, padding: '20px 20px 18px',
      boxShadow: '0 12px 40px rgba(0,0,0,0.08)',
    }}>
      <div style={{
        fontFamily: 'var(--mono)', fontSize: 10, color: C.mute,
        letterSpacing: '0.08em', textTransform: 'uppercase', fontWeight: 500,
      }}>Your size</div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, margin: '6px 0 16px' }}>
        <span style={{ fontFamily: 'var(--display)', fontSize: 44, fontWeight: 800, letterSpacing: '-0.03em', lineHeight: 1 }}>L</span>
        <span style={{ fontFamily: 'var(--display)', fontSize: 14, color: C.mute, fontWeight: 500 }}>96% match</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
        {EXAMPLE_SCORES.map(s => (
          <div key={s.size} style={{ display: 'grid', gridTemplateColumns: '28px 1fr 36px', alignItems: 'center', gap: 10 }}>
            <span style={{ fontFamily: 'var(--display)', fontSize: 13, fontWeight: s.best ? 700 : 500 }}>{s.size}</span>
            <span style={{ height: 6, borderRadius: 3, background: C.line, overflow: 'hidden' }}>
              <span style={{
                display: 'block', height: '100%', width: `${s.score}%`,
                background: s.best ? C.ink : C.mute, borderRadius: 3,
              }} />
            </span>
            <span style={{
              fontFamily: 'var(--display)', fontSize: 13, color: s.best ? C.ink : C.mute,
              textAlign: 'right', fontVariantNumeric: 'tabular-nums',
            }}>{s.score}%</span>
          </div>
        ))}
      </div>
      <div style={{
        marginTop: 16, paddingTop: 12, borderTop: `1px solid ${C.line}`,
        fontFamily: 'var(--display)', fontSize: 12, color: C.mute, lineHeight: 1.45,
      }}>Sold out in your size? You see the next best, and how it will fit.</div>
    </div>
  );
}

/* ─── Hero: lead with the size, the 3D avatar on the right ─── */
function DesktopHero() {
  const C = useC();
  const router = useRouter();
  const [hovered, setHovered] = useState<'primary' | 'ghost' | null>(null);

  return (
    <section style={{
      background: C.bg, color: C.ink,
      padding: '0 48px',
      borderBottom: `1px solid ${C.line}`,
      height: 'calc(100vh - 64px)',
      minHeight: 640,
      maxHeight: 920,
      display: 'flex', alignItems: 'center',
      position: 'relative',
      overflow: 'hidden',
    }}>
      <div style={{
        maxWidth: 1320, margin: '0 auto', width: '100%',
        display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 48,
        alignItems: 'center',
      }}>
        {/* Left column: copy stack */}
        <div style={{ minWidth: 0, paddingRight: 12 }}>
          <div style={{
            fontFamily: 'var(--mono)', fontSize: 12, color: C.mute,
            letterSpacing: '0.08em', textTransform: 'uppercase', fontWeight: 500,
            marginBottom: 28,
          }}>
            TryOn · Size and 3D try-on for Shopify
          </div>

          <h1 style={{
            fontFamily: 'var(--display)', fontWeight: 900,
            fontSize: 'clamp(48px, 6.4vw, 88px)',
            letterSpacing: '-0.04em', lineHeight: 0.94,
            margin: '0 0 24px',
          }}>
            Your size in 30&nbsp;seconds.
          </h1>

          <p style={{
            fontFamily: 'var(--display)', fontSize: 20, lineHeight: 1.45,
            color: C.mute, fontWeight: 400, letterSpacing: '-0.005em',
            maxWidth: 520, margin: '0 0 32px',
          }}>
            On every product. No account. Try it on in 3D where you can.
          </p>

          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 32 }}>
            <button
              onClick={() => router.push('/start')}
              onMouseEnter={() => setHovered('primary')}
              onMouseLeave={() => setHovered(null)}
              style={{
                background: hovered === 'primary' ? COBALT_HOVER : COBALT,
                color: '#FFFFFF', border: 'none',
                padding: '14px 26px', borderRadius: 9999,
                fontFamily: 'var(--display)', fontSize: 15, fontWeight: 600,
                letterSpacing: '-0.005em',
                cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 10,
                transform: hovered === 'primary' ? 'translateY(-1px)' : 'translateY(0)',
                transition: 'all 180ms cubic-bezier(0.4, 0, 0.2, 1)',
              }}
            >
              Start free <span>→</span>
            </button>
            <button
              onClick={() => router.push('/product')}
              onMouseEnter={() => setHovered('ghost')}
              onMouseLeave={() => setHovered(null)}
              style={{
                background: hovered === 'ghost' ? (C.ink === '#0A0A0A' ? 'rgba(10,10,10,0.05)' : 'rgba(255,255,255,0.08)') : 'transparent',
                color: C.ink,
                border: `1px solid ${C.ink}`,
                padding: '14px 26px', borderRadius: 9999,
                fontFamily: 'var(--display)', fontSize: 15, fontWeight: 600,
                letterSpacing: '-0.005em',
                cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 8,
                transition: 'all 180ms cubic-bezier(0.4, 0, 0.2, 1)',
              }}
            >
              See how it works
            </button>
          </div>

          <MatchStrip />
        </div>

        {/* Right column: avatar bleeds onto the page, no card, no border */}
        <div style={{
          position: 'relative',
          height: '100%', minHeight: 560,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <AvatarHero height="100%" interactive={false} rotateSpeed={0.6} />
          <div
            aria-hidden
            style={{
              position: 'absolute', bottom: 24, left: 0, right: 0,
              textAlign: 'center',
              fontFamily: 'var(--mono)', fontSize: 11, color: C.mute,
              letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 500,
              pointerEvents: 'none',
            }}
          >
            Your shopper · Size M
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── Brand/Shopper tiles ─── */
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
          Brands cut returns and lift conversion. Shoppers get their size on every product without guessing.
        </p>
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20,
        }}>
          <PathTile
            tag="For brands"
            title="I am a brand"
            sub="One button for every product, added in your Shopify theme editor. Free to start."
            cta="Start free →"
            onClick={() => router.push('/start')}
            C={C}
          />
          <PathTile
            tag="For shoppers"
            title="I am a shopper"
            sub="Get your size free, no account. Seven quick questions, about 30 seconds."
            cta="Try Find my size →"
            onClick={() => router.push('/demo')}
            C={C}
          />
        </div>
      </div>
    </section>
  );
}

/* ─── One button, three pieces ─── */
const PIECES = [
  {
    tag: 'Find my size',
    desc: 'Seven quick questions, no account. Every size scored as a % match. Sold out in yours? The next best, and how it will fit.',
    visual: 'mock' as const,
  },
  {
    tag: 'Fit passport',
    desc: 'The upgrade. One photo gives a measured size, not an estimate, and a photoreal 3D avatar to try clothes on.',
    image: '/redesign/fit-passport.jpg',
  },
  {
    tag: 'Insights for brands',
    desc: 'ROI and attribution, fit intelligence, the size finder funnel and returns by size, in one dashboard.',
    image: '/redesign/fit-report.jpg',
  },
];

function PieceVisual({ piece, pad }: { piece: typeof PIECES[number]; pad: number }) {
  const C = useC();
  return (
    <div style={{
      aspectRatio: '4/5',
      background: 'visual' in piece ? C.bg : '#ffffff',
      display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
      padding: pad, boxSizing: 'border-box',
      borderBottom: `1px solid ${C.line}`,
    }}>
      {'visual' in piece ? (
        <SizeResultMock />
      ) : (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={piece.image} alt={piece.tag} style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }} />
      )}
    </div>
  );
}

function DesktopComponents() {
  const C = useC();
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
          One button. Every product.
        </h2>
        <p style={{ ...bodyStyle, color: C.mute, maxWidth: 720, marginBottom: 40 }}>
          On products with a 3D garment the button reads Try On. On every other product with sizes it reads Find my size. One install covers the whole catalogue.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }}>
          {PIECES.map(it => (
            <div key={it.tag} style={{
              border: `1px solid ${C.line}`,
              borderRadius: 16,
              background: C.bg,
              overflow: 'hidden',
              display: 'flex', flexDirection: 'column',
            }}>
              <PieceVisual piece={it} pad={20} />
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

/* ─── Pricing summary: straight from lib/plans, never hard-coded here ─── */
function PlanSummary({ mobile }: { mobile?: boolean }) {
  const C = useC();
  const router = useRouter();
  return (
    <div>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 14, gap: 12,
      }}>
        <div style={{ fontFamily: 'var(--display)', fontSize: mobile ? 13 : 14, fontWeight: 600, color: C.ink }}>
          Pricing
        </div>
        <Link href="/pricing" style={{
          fontFamily: 'var(--display)', fontSize: mobile ? 13 : 14, color: C.ink, fontWeight: 600, textDecoration: 'none',
        }}>See full pricing →</Link>
      </div>
      <div style={{
        display: mobile ? 'flex' : 'grid',
        flexDirection: mobile ? 'column' : undefined,
        gridTemplateColumns: mobile ? undefined : `repeat(${PLANS.length}, 1fr)`,
        border: `1px solid ${C.line}`,
        background: C.bg,
      }}>
        {PLANS.map((p, i) => (
          <button
            key={p.id}
            onClick={() => router.push('/pricing')}
            style={{
              background: p.highlight ? C.cardBg : 'transparent',
              color: p.highlight ? C.cardInk : C.ink,
              border: 'none',
              borderRight: !mobile && i < PLANS.length - 1 ? `1px solid ${C.line}` : 'none',
              borderBottom: mobile && i < PLANS.length - 1 ? `1px solid ${C.line}` : 'none',
              padding: mobile ? '16px 18px' : '24px 20px',
              textAlign: 'left', cursor: 'pointer',
              display: 'flex', flexDirection: 'column', gap: mobile ? 4 : 8,
            }}
          >
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 8, width: '100%',
            }}>
              <span style={{
                fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600,
                color: p.highlight ? C.cardMute : C.mute,
              }}>{p.name}</span>
              {mobile && (
                <span style={{ fontFamily: 'var(--display)', fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em' }}>
                  {p.price}{p.period === 'per month' ? <span style={{ fontSize: 12, fontWeight: 500 }}>/mo</span> : null}
                </span>
              )}
            </div>
            {!mobile && (
              <div style={{
                fontFamily: 'var(--display)', fontSize: 28, fontWeight: 700,
                letterSpacing: '-0.02em', lineHeight: 1,
              }}>
                {p.price}
                {p.period === 'per month' && (
                  <span style={{ fontSize: 13, fontWeight: 500, color: p.highlight ? C.cardMute : C.mute }}> /mo</span>
                )}
              </div>
            )}
            <div style={{
              fontFamily: 'var(--display)', fontSize: 13, lineHeight: 1.45,
              color: p.highlight ? C.cardMute : C.mute,
            }}>{p.pitch}</div>
          </button>
        ))}
      </div>
      <div style={{ fontFamily: 'var(--display)', fontSize: 13, color: C.mute, marginTop: 12 }}>
        {TRIAL_DAYS}-day free trial on every paid plan. Prices in USD.
      </div>
    </div>
  );
}

/* ─── For Brands ─── */
function DesktopBrands() {
  const C = useC();
  const cmp = [
    {
      name: 'Google VTO',
      bullets: ['Flat 2D image generation.', 'No body measurements.', 'Happens on Google. Brand loses the data.'],
      muted: true,
    },
    {
      name: 'True Fit',
      bullets: ['Size recommendation only.', 'No 3D, no avatar.', 'Enterprise pricing, sold by order volume.'],
      muted: true,
    },
    {
      name: 'TryOn',
      bullets: ['A size on every product, 3D try-on where you have it.', 'Every size scored as a % match.', 'Brand keeps the data and the PDP.'],
      muted: false,
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
          marginBottom: 14, maxWidth: 920,
        }}>
          Pay less than the cost of one return per day.
        </h2>
        <p style={{
          ...bodyStyle, color: C.mute, maxWidth: 720, marginBottom: 48,
        }}>
          Built for Shopify fashion brands. Start free with Find my size on every product. Add measured sizes and 3D try-on when you are ready.
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

        <div style={{ marginBottom: 56, maxWidth: 720 }}>
          <div style={{
            fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600, color: C.ink, marginBottom: 10,
          }}>Shopify integration</div>
          <h3 style={{ ...headingStyle('clamp(26px, 3vw, 40px)'), marginBottom: 12 }}>
            One button, added in your Shopify theme editor.
          </h3>
          <p style={{ ...bodyStyle, fontSize: 15, color: C.mute, maxWidth: 560 }}>
            Install the app and drop the TryOn block onto your product page. It reads Try On on products with a 3D garment and Find my size on the rest. No code, no SDK, no agency.
          </p>
        </div>

        <PlanSummary />
      </div>
    </section>
  );
}

/* ─── For Shoppers: a size needs no account; the passport is the upgrade ─── */
const PASSPORT_STEPS = [
  { k: '30 seconds', title: 'Seven questions, your size.', sub: 'Who for, height, weight, age, two body-shape drawings, fit preference. No account.' },
  { k: 'One photo', title: 'Your size, measured.', sub: 'The fit passport measures you from one photo, so the size is measured, not estimated.' },
  { k: 'In 3D', title: 'See it on your own body.', sub: 'A photoreal avatar of you, with real cloth simulation on products in 3D.' },
];

function DesktopShoppers() {
  const C = useC();
  const router = useRouter();

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
              No account for your size. One passport for every brand.
            </h2>
            <p style={{
              ...bodyStyle, color: C.mute, maxWidth: 480, marginBottom: 26,
            }}>
              Find my size is free and needs no sign-up. Your answers are remembered on every product and every TryOn store. Want more? The fit passport measures you from one photo and builds your 3D avatar.
            </p>

            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <button
                onClick={() => router.push('/demo')}
                style={{
                  background: COBALT, color: '#FFFFFF', border: 'none',
                  padding: '14px 24px', borderRadius: 9999,
                  fontFamily: 'var(--display)', fontSize: 15, fontWeight: 600,
                  letterSpacing: '-0.005em', cursor: 'pointer',
                  display: 'inline-flex', alignItems: 'center', gap: 10,
                }}
              >Get your size free <span>→</span></button>
              <button
                onClick={() => router.push('/signup')}
                style={{
                  background: 'transparent', color: C.ink, border: `1px solid ${C.ink}`,
                  padding: '14px 24px', borderRadius: 9999,
                  fontFamily: 'var(--display)', fontSize: 15, fontWeight: 600,
                  letterSpacing: '-0.005em', cursor: 'pointer',
                }}
              >Build a fit passport</button>
            </div>
          </div>

          <div style={{ border: `1px solid ${C.line}`, borderRadius: 16, background: C.surface }}>
            {PASSPORT_STEPS.map((s, i) => (
              <div key={s.k} style={{
                padding: '22px 26px',
                borderBottom: i < PASSPORT_STEPS.length - 1 ? `1px solid ${C.line}` : 'none',
              }}>
                <div style={{
                  fontFamily: 'var(--mono)', fontSize: 11, color: C.mute, fontWeight: 500,
                  letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 8,
                }}>{s.k}</div>
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 19, fontWeight: 600,
                  color: C.ink, lineHeight: 1.3, letterSpacing: '-0.01em',
                }}>{s.title}</div>
                <div style={{ ...bodyStyle, fontSize: 14, color: C.mute, marginTop: 6 }}>{s.sub}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── Mobile sections (compressed but same content) ─── */
function MobileHero() {
  const C = useC();
  const router = useRouter();

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
        TryOn · Size and 3D try-on
      </div>
      <h1 style={{
        fontFamily: 'var(--display)', fontWeight: 900,
        fontSize: 'clamp(40px, 11vw, 64px)',
        letterSpacing: '-0.04em', lineHeight: 0.92,
        margin: '0 0 16px',
      }}>
        Your size in 30&nbsp;seconds.
      </h1>
      <p style={{
        fontFamily: 'var(--display)', fontSize: 17, lineHeight: 1.45,
        color: C.mute, fontWeight: 400, letterSpacing: '-0.005em',
        margin: '0 0 6px',
      }}>
        On every product. No account. Try it on in 3D where you can.
      </p>

      <div style={{
        position: 'relative',
        marginBottom: 18,
        minHeight: 380,
      }}>
        <AvatarHero height="52vh" interactive={false} rotateSpeed={0.7} />
        <div
          aria-hidden
          style={{
            position: 'absolute', bottom: 6, left: 0, right: 0,
            textAlign: 'center',
            fontFamily: 'var(--mono)', fontSize: 10, color: C.mute,
            letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 500,
            pointerEvents: 'none',
          }}
        >
          Your shopper · Size M
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
        <button
          onClick={() => router.push('/start')}
          style={{
            background: COBALT, color: '#FFFFFF', border: 'none',
            padding: '14px 22px', borderRadius: 9999,
            fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600,
            letterSpacing: '-0.005em',
            cursor: 'pointer',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          }}
        >Start free <span>→</span></button>
        <button
          onClick={() => router.push('/product')}
          style={{
            background: 'transparent', color: C.ink,
            border: `1px solid ${C.ink}`,
            padding: '14px 22px', borderRadius: 9999,
            fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600,
            letterSpacing: '-0.005em',
            cursor: 'pointer',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          }}
        >See how it works</button>
      </div>

      <MatchStrip compact />
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
        Brands cut returns. Shoppers get their size without guessing.
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <PathTile
          tag="For brands"
          title="I am a brand"
          sub="One button for every product. Free to start."
          cta="Start free →"
          onClick={() => router.push('/start')}
          C={C}
        />
        <PathTile
          tag="For shoppers"
          title="I am a shopper"
          sub="Get your size free, no account."
          cta="Try Find my size →"
          onClick={() => router.push('/demo')}
          C={C}
        />
      </div>
    </section>
  );
}

function MobileComponents() {
  const C = useC();
  return (
    <section style={{
      background: C.surface, color: C.ink,
      padding: '52px 18px',
      borderBottom: `1px solid ${C.line}`,
    }}>
      <h2 style={{ ...headingStyle('30px'), marginBottom: 12 }}>
        One button. Every product.
      </h2>
      <p style={{ ...bodyStyle, fontSize: 14, color: C.mute, marginBottom: 22 }}>
        Try On on products with a 3D garment. Find my size on every other product with sizes. One install.
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {PIECES.map(it => (
          <div key={it.tag} style={{
            border: `1px solid ${C.line}`, borderRadius: 16, background: C.bg, overflow: 'hidden',
          }}>
            <PieceVisual piece={it} pad={14} />
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

function MobileBrands() {
  const C = useC();
  return (
    <section style={{ background: C.surface, color: C.ink, padding: '52px 18px', borderBottom: `1px solid ${C.line}` }}>
      <h2 style={{ ...headingStyle('30px'), marginBottom: 12 }}>
        Pay less than one return per day.
      </h2>
      <p style={{ ...bodyStyle, fontSize: 13.5, color: C.mute, marginBottom: 22 }}>
        Start free with Find my size on every product. Add measured sizes and 3D try-on when you are ready.
      </p>

      <div style={{ marginBottom: 28 }}>
        <div style={{ fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600, color: C.ink, marginBottom: 8 }}>
          Shopify integration
        </div>
        <h3 style={{ ...headingStyle('22px'), marginBottom: 8 }}>
          One button, added in your Shopify theme editor.
        </h3>
        <p style={{ ...bodyStyle, fontSize: 13.5, color: C.mute }}>
          Drop the TryOn block onto your product page. No code, no SDK.
        </p>
      </div>

      <PlanSummary mobile />
    </section>
  );
}

function MobileShoppers() {
  const C = useC();
  const router = useRouter();
  return (
    <section style={{ background: C.bg, color: C.ink, padding: '52px 18px', borderBottom: `1px solid ${C.line}` }}>
      <h2 style={{ ...headingStyle('30px'), marginBottom: 12 }}>
        No account for your size.
      </h2>
      <p style={{ ...bodyStyle, fontSize: 13.5, color: C.mute, marginBottom: 18 }}>
        Free, no sign-up, remembered on every TryOn store. The fit passport is the upgrade: one photo, a measured size and your 3D avatar.
      </p>

      <div style={{ border: `1px solid ${C.line}`, borderRadius: 16, background: C.surface, marginBottom: 18 }}>
        {PASSPORT_STEPS.map((s, i) => (
          <div key={s.k} style={{
            padding: '14px 16px',
            borderBottom: i < PASSPORT_STEPS.length - 1 ? `1px solid ${C.line}` : 'none',
          }}>
            <div style={{
              fontFamily: 'var(--mono)', fontSize: 10, color: C.mute, fontWeight: 500,
              letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 4,
            }}>{s.k}</div>
            <div style={{ fontFamily: 'var(--display)', fontSize: 15, fontWeight: 600, color: C.ink, lineHeight: 1.3 }}>
              {s.title}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <button
          onClick={() => router.push('/demo')}
          style={{
            background: COBALT, color: '#FFFFFF', border: 'none',
            padding: '14px 20px', borderRadius: 9999,
            fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600, cursor: 'pointer',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          }}
        >Get your size free <span>→</span></button>
        <button
          onClick={() => router.push('/signup')}
          style={{
            background: 'transparent', color: C.ink, border: `1px solid ${C.ink}`,
            padding: '14px 20px', borderRadius: 9999,
            fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600, cursor: 'pointer',
          }}
        >Build a fit passport</button>
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

/* ─── Why fit matters: industry figures, each linked to its source ───
   Other companies' results and published studies, shown as theirs, never as TryOn's.
   Only figures checked against the primary page go here. */
type Stat = { value: string; line: string; source: string; href: string };
const STAT_GROUPS: { title: string; stats: Stat[]; note?: string }[] = [
  {
    title: 'More sales',
    stats: [
      {
        value: '30%',
        line: 'Size advice lifted conversion 30% and order value 47% for ARMEDANGELS.',
        source: 'Fit Analytics, ARMEDANGELS A/B test, 2024',
        href: 'https://fitanalytics.com/case-studies/armedangels',
      },
      {
        value: '59%',
        line: 'of online shoppers say clothes looked different on them than expected.',
        source: 'Google / Ipsos, 2023',
        href: 'https://blog.google/products-and-platforms/products/shopping/ai-virtual-try-on-google-shopping/',
      },
    ],
  },
  {
    title: 'Fewer returns',
    stats: [
      {
        value: '70%',
        line: 'of clothing returns come down to fit or style.',
        source: 'McKinsey, Returns management in apparel',
        href: 'https://www.mckinsey.com/industries/retail/our-insights/returning-to-order-improving-returns-management-for-apparel-companies',
      },
      {
        value: '10%',
        line: 'fewer size-related returns at Zalando with size advice.',
        source: 'Zalando, 2023',
        href: 'https://corporate.zalando.com/en/technology/zalando-launches-size-recommendations-based-customers-own-body-measurements',
      },
      {
        value: '$850B',
        line: 'of goods sent back by US shoppers in 2025, nearly 1 in 5 online orders.',
        source: 'NRF & Happy Returns, 2025',
        href: 'https://nrf.com/media-center/press-releases/consumers-expected-to-return-nearly-850-billion-in-merchandise-in-2025',
      },
    ],
  },
  {
    title: 'Know what fits your customers',
    stats: [
      {
        value: '4 in 10',
        line: 'shoppers say poor size guides stop them buying.',
        source: 'Zalando & YouGov, 2024',
        href: 'https://corporate.zalando.com/en/fashion/fitting-room-frustration-new-research-reveals-low-confidence-among-fashion-shoppers',
      },
      {
        value: '51%',
        line: 'of Gen Z order several sizes and send the rest back.',
        source: 'NRF & Happy Returns, 2024',
        href: 'https://happyreturns.com/2024-nrf-returns-report',
      },
    ],
    note: 'TryOn shows you which sizes your shoppers really need, product by product: fewer surprises in stock, fewer returns.',
  },
];

const RULEBOOK = [
  { date: 'Jul 2026', title: 'EU bans destruction of unsold apparel.', sub: 'Central Digital Product Passport registry goes live.' },
  { date: 'Sep 2026', title: 'ECGT applies. Anti-greenwashing.', sub: 'Words like "sustainable" become regulated. Claims need proof.' },
  { date: '2028', title: 'DPP mandatory for textiles.', sub: 'Every garment sold in the EU carries a digital twin.' },
];

function StatBlock({ s, compact }: { s: Stat; compact?: boolean }) {
  const C = useC();
  return (
    <div style={{ padding: compact ? '16px 18px' : '22px 24px', borderTop: `1px solid ${C.line}` }}>
      <div style={{
        fontFamily: 'var(--display)', fontWeight: 700,
        fontSize: compact ? 36 : 48, letterSpacing: '-0.035em', lineHeight: 1, color: C.ink,
      }}>{s.value}</div>
      <div style={{ ...bodyStyle, fontSize: compact ? 14 : 15, color: C.ink, marginTop: 10, lineHeight: 1.45 }}>{s.line}</div>
      <a
        href={s.href}
        target="_blank"
        rel="noopener noreferrer"
        style={{
          display: 'inline-block', marginTop: 8,
          fontFamily: 'var(--display)', fontSize: 12, color: C.mute,
          textDecoration: 'underline', textUnderlineOffset: 3, textDecorationColor: C.line,
        }}
      >Source: {s.source} ↗</a>
    </div>
  );
}

function StatGroup({ g, compact }: { g: typeof STAT_GROUPS[number]; compact?: boolean }) {
  const C = useC();
  return (
    <div style={{
      border: `1px solid ${C.line}`, borderRadius: 16, background: C.surface,
      display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>
      <div style={{
        padding: compact ? '14px 18px' : '18px 24px',
        fontFamily: 'var(--mono)', fontSize: 11, color: C.mute, fontWeight: 500,
        letterSpacing: '0.08em', textTransform: 'uppercase',
      }}>{g.title}</div>
      {g.stats.map((s) => <StatBlock key={s.value} s={s} compact={compact} />)}
      {g.note && (
        <div style={{
          marginTop: 'auto', padding: compact ? '16px 18px' : '20px 24px',
          borderTop: `1px solid ${C.line}`, background: C.cardBg, color: C.cardInk,
          fontFamily: 'var(--display)', fontSize: compact ? 14 : 15, fontWeight: 500, lineHeight: 1.45,
        }}>{g.note}</div>
      )}
    </div>
  );
}

function DesktopEvidence() {
  const C = useC();
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
          Why fit matters.
        </h2>
        <p style={{ ...bodyStyle, color: C.mute, maxWidth: 720, marginBottom: 40 }}>
          Published industry figures and other brands&apos; results, each linked to its source.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20, alignItems: 'stretch', marginBottom: 56 }}>
          {STAT_GROUPS.map((g) => <StatGroup key={g.title} g={g} />)}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.1fr', gap: 40, alignItems: 'start' }}>
          <div>
            <h3 style={{ ...headingStyle('clamp(26px, 3vw, 40px)'), marginBottom: 12 }}>
              The EU rulebook, 2026 to 2028.
            </h3>
            <p style={{ ...bodyStyle, fontSize: 15, color: C.mute, maxWidth: 480 }}>
              Every garment we render is already a 3D digital twin. DPP-ready by design. While other VTO vendors will be deleting &quot;sustainable&quot; from their landing pages, we will be quoting the regulation.
            </p>
          </div>
          <div style={{ border: `1px solid ${C.line}`, borderRadius: 16, background: C.surface }}>
            {RULEBOOK.map((r, i) => (
              <div key={r.date} style={{
                padding: '20px 24px',
                borderBottom: i < RULEBOOK.length - 1 ? `1px solid ${C.line}` : 'none',
              }}>
                <div style={{ fontFamily: 'var(--display)', fontSize: 13, color: C.mute, fontWeight: 500, marginBottom: 8 }}>{r.date}</div>
                <div style={{ fontFamily: 'var(--display)', fontSize: 18, fontWeight: 600, color: C.ink, lineHeight: 1.3, letterSpacing: '-0.01em' }}>{r.title}</div>
                <div style={{ ...bodyStyle, fontSize: 13.5, color: C.mute, marginTop: 6 }}>{r.sub}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function MobileEvidence() {
  const C = useC();
  return (
    <section style={{
      background: C.bg, color: C.ink, padding: '52px 18px',
      borderBottom: `1px solid ${C.line}`,
    }}>
      <h2 style={{ ...headingStyle('30px'), marginBottom: 12 }}>
        Why fit matters.
      </h2>
      <p style={{ ...bodyStyle, fontSize: 14, color: C.mute, marginBottom: 22 }}>
        Published industry figures and other brands&apos; results, each linked to its source.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginBottom: 32 }}>
        {STAT_GROUPS.map((g) => <StatGroup key={g.title} g={g} compact />)}
      </div>

      <div style={{
        fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600, color: C.ink, marginBottom: 10,
      }}>EU rulebook, 2026 to 2028</div>
      <div style={{ border: `1px solid ${C.line}`, borderRadius: 16, background: C.surface }}>
        {RULEBOOK.map((r, i) => (
          <div key={r.date} style={{
            padding: '14px 16px',
            borderBottom: i < RULEBOOK.length - 1 ? `1px solid ${C.line}` : 'none',
          }}>
            <div style={{ fontFamily: 'var(--display)', fontSize: 12, color: C.mute, fontWeight: 500, marginBottom: 4 }}>{r.date}</div>
            <div style={{ fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600, color: C.ink, lineHeight: 1.3 }}>{r.title}</div>
          </div>
        ))}
      </div>
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
        <SharedNav
          dark={dark}
          links={siteLinks('/')}
          rightSlot={mobile ? (
            <NavCta dark={dark} label="Start free" href="/start" />
          ) : (
            <>
              <AuthAwareSignInLink dark={dark} />
              <NavCta dark={dark} label="Start free →" href="/start" />
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
          </>
        ) : (
          <>
            <DesktopHero />
            <DesktopComponents />
            <DesktopBrandShopperTiles />
            <DesktopEvidence />
            <DesktopBrands />
            <DesktopShoppers />
          </>
        )}
        <SiteFooter dark={dark} />
      </div>
    </ThemeCtx.Provider>
  );
}
