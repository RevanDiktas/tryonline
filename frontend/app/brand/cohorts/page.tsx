'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from '@/contexts/ThemeContext';
import { SharedNav, NavLink } from '@/components/redesign/SharedNav';
import { useIsMobile } from '@/components/redesign/useIsMobile';

const PAL = {
  light: {
    bg: '#FAFAF8', surface: '#FFFFFF',
    ink: '#0A0A0A', mute: '#6E6E6E',
    line: 'rgba(10,10,10,0.10)',
    cardBg: '#0A0A0A', cardInk: '#FAFAF8', cardMute: '#9A9A9A',
    cardLine: 'rgba(255,255,255,0.14)',
  },
  dark: {
    bg: '#0A0A0A', surface: '#121212',
    ink: '#F2F1EC', mute: '#8A8A8A',
    line: 'rgba(255,255,255,0.10)',
    cardBg: '#F2F1EC', cardInk: '#0A0A0A', cardMute: '#6E6E6E',
    cardLine: 'rgba(0,0,0,0.10)',
  },
};
type Palette = typeof PAL.light;

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

function CountUp({ to, suffix = '', prefix = '', duration = 1200, decimals = 0, style }: {
  to: number; suffix?: string; prefix?: string; duration?: number; decimals?: number; style?: React.CSSProperties;
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
  return <span ref={ref} style={style}>{prefix}{display}{suffix}</span>;
}

const headingStyle = (px: string): React.CSSProperties => ({
  fontFamily: 'var(--display)', fontWeight: 700,
  fontSize: px, letterSpacing: '-0.022em', lineHeight: 1.04, margin: 0,
});

function Hero({ C }: { C: Palette }) {
  return (
    <section style={{ background: C.bg, color: C.ink, padding: '48px 32px 24px', borderBottom: `1px solid ${C.line}` }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <div style={{
          fontFamily: 'var(--display)', fontSize: 13, color: C.mute, fontWeight: 500, marginBottom: 10,
        }}>
          Ramin Studios pilot, last 30 days
        </div>
        <h1 style={{
          ...headingStyle('clamp(36px, 5vw, 72px)'),
          maxWidth: 1100, marginBottom: 14,
        }}>
          Virtual try-on lifted conversion <CountUp to={1.78} decimals={2} suffix="x" />.
        </h1>
        <p style={{
          fontFamily: 'var(--display)', fontSize: 15, lineHeight: 1.55,
          color: C.mute, maxWidth: 720, margin: 0,
        }}>
          Side-by-side comparison of shoppers who used the TryOn widget against the store baseline. Numbers are computed on the rolling 30-day window. Baselines pulled from your Shopify Analytics.
        </p>
      </div>
    </section>
  );
}

function MetricGrid({ C }: { C: Palette }) {
  const metrics = [
    { label: 'Conversion rate', tryon: 3.2, baseline: 1.8, suffix: '%', decimals: 1, delta: '+78%' },
    { label: 'Average order value', tryon: 47, baseline: 39, prefix: '€', decimals: 0, delta: '+20%' },
    { label: 'Return rate', tryon: 8, baseline: 12, suffix: '%', decimals: 0, delta: '−33%' },
    { label: 'Fit confidence', tryon: 82, suffix: '%', decimals: 0, delta: 'Per-SKU avg' },
  ];
  return (
    <section style={{ background: C.bg, color: C.ink, padding: '24px 20px 48px' }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 0,
          border: `1px solid ${C.line}`, background: C.surface,
        }}>
          {metrics.map((m) => (
            <div key={m.label} style={{
              borderRight: `1px solid ${C.line}`,
              borderBottom: `1px solid ${C.line}`,
              padding: '22px 20px',
              display: 'flex', flexDirection: 'column', gap: 12,
            }}>
              <div style={{
                fontFamily: 'var(--display)', fontSize: 12, fontWeight: 600, color: C.mute,
              }}>{m.label}</div>

              <div style={{
                fontFamily: 'var(--display)', fontSize: 38, fontWeight: 700,
                letterSpacing: '-0.025em', lineHeight: 1, color: C.ink,
              }}>
                <CountUp to={m.tryon} prefix={m.prefix} suffix={m.suffix} decimals={m.decimals} />
              </div>

              {m.baseline !== undefined ? (
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 13, color: C.mute,
                }}>
                  vs {m.prefix || ''}{m.baseline.toFixed(m.decimals || 0)}{m.suffix || ''} baseline
                </div>
              ) : (
                <div style={{ fontFamily: 'var(--display)', fontSize: 13, color: C.mute }}>
                  Average across SKUs.
                </div>
              )}

              <div style={{
                marginTop: 'auto',
                fontFamily: 'var(--display)', fontSize: 12, fontWeight: 600, color: C.ink,
                padding: '4px 10px',
                border: `1px solid ${C.ink}`,
                alignSelf: 'flex-start',
              }}>{m.delta}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Funnel({ C }: { C: Palette }) {
  const stages = [
    { k: 'Widget opens', v: 100, sub: 'Shoppers clicked Try On.' },
    { k: 'Try-on rendered', v: 94, sub: 'Avatar dressed in garment.' },
    { k: 'Size selected', v: 71, sub: 'Picked recommended or alternate.' },
    { k: 'Add to cart', v: 34, sub: 'Pushed to checkout.' },
    { k: 'Purchase', v: 25, sub: 'Order completed.' },
  ];
  const max = stages[0].v;
  return (
    <section style={{
      background: C.surface, color: C.ink, padding: '56px 32px',
      borderTop: `1px solid ${C.line}`,
    }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <h2 style={{ ...headingStyle('clamp(28px, 3.5vw, 44px)'), marginBottom: 20 }}>
          Fit-to-purchase funnel.
        </h2>
        <div style={{
          border: `1px solid ${C.line}`, background: C.bg,
        }}>
          {stages.map((s, i) => {
            const pct = (s.v / max) * 100;
            return (
              <div key={s.k} style={{
                padding: '16px 22px',
                borderBottom: i < stages.length - 1 ? `1px solid ${C.line}` : 'none',
                display: 'grid', gridTemplateColumns: '1.4fr 2fr 0.8fr', alignItems: 'center', gap: 22,
              }}>
                <div>
                  <div style={{
                    fontFamily: 'var(--display)', fontSize: 14.5, fontWeight: 600, color: C.ink,
                  }}>{s.k}</div>
                  <div style={{
                    fontFamily: 'var(--display)', fontSize: 12, color: C.mute, marginTop: 2,
                  }}>{s.sub}</div>
                </div>
                <div style={{
                  height: 12, background: C.line, position: 'relative', overflow: 'hidden',
                }}>
                  <div style={{
                    position: 'absolute', left: 0, top: 0, bottom: 0,
                    width: `${pct}%`, background: C.ink, transition: 'width 0.6s ease',
                  }} />
                </div>
                <div style={{
                  textAlign: 'right',
                  fontFamily: 'var(--display)', fontSize: 20, fontWeight: 700, color: C.ink,
                  letterSpacing: '-0.02em',
                }}>
                  <CountUp to={s.v} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function Dwell({ C }: { C: Palette }) {
  const buckets = [
    { range: '0 to 10s', count: 8 },
    { range: '10 to 20s', count: 19 },
    { range: '20 to 30s', count: 28 },
    { range: '30 to 60s', count: 24 },
    { range: 'Over 60s', count: 15 },
  ];
  const max = Math.max(...buckets.map(b => b.count));
  return (
    <section style={{
      background: C.bg, color: C.ink, padding: '56px 32px',
      borderTop: `1px solid ${C.line}`,
    }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 20 }}>
          <h2 style={{ ...headingStyle('clamp(28px, 3.5vw, 44px)'), margin: 0 }}>
            Dwell time.
          </h2>
          <div style={{ fontFamily: 'var(--display)', fontSize: 14, color: C.mute }}>
            Avg <span style={{ color: C.ink, fontWeight: 600 }}>38s</span> per session
          </div>
        </div>
        <div style={{
          border: `1px solid ${C.line}`, padding: 24, background: C.surface,
          display: 'flex', alignItems: 'flex-end', gap: 18, height: 200,
        }}>
          {buckets.map(b => {
            const h = Math.round((b.count / max) * 144);
            return (
              <div key={b.range} style={{
                flex: 1,
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
              }}>
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 12, fontWeight: 600, color: C.ink,
                }}>{b.count}</div>
                <div style={{
                  width: '100%', height: h,
                  background: C.ink,
                  transition: 'height 0.6s ease',
                }} />
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 12, color: C.mute, textAlign: 'center',
                }}>{b.range}</div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function TopProducts({ C }: { C: Palette }) {
  const rows = [
    { name: 'NPC Oversized T-shirt', tryons: 38, conv: 32, lift: '+1.9x' },
    { name: 'NPC Cropped Hoodie', tryons: 22, conv: 28, lift: '+1.6x' },
    { name: 'NPC Flow Pant', tryons: 17, conv: 24, lift: '+1.4x' },
    { name: 'NPC Tank', tryons: 12, conv: 18, lift: '+1.2x' },
    { name: 'NPC Track Top', tryons: 5, conv: 14, lift: '+1.1x' },
  ];
  return (
    <section style={{
      background: C.surface, color: C.ink, padding: '56px 32px',
      borderTop: `1px solid ${C.line}`,
    }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <h2 style={{ ...headingStyle('clamp(28px, 3.5vw, 44px)'), marginBottom: 20 }}>
          Top products by try-on volume.
        </h2>
        <div style={{ border: `1px solid ${C.line}`, background: C.bg }}>
          <div style={{
            padding: '12px 22px', borderBottom: `1px solid ${C.line}`,
            display: 'grid', gridTemplateColumns: '1.6fr 0.6fr 0.6fr 0.6fr', gap: 22,
            fontFamily: 'var(--display)', fontSize: 12, fontWeight: 600, color: C.mute,
          }}>
            <span>Product</span>
            <span style={{ textAlign: 'right' }}>Try-ons</span>
            <span style={{ textAlign: 'right' }}>Conversion</span>
            <span style={{ textAlign: 'right' }}>Lift</span>
          </div>
          {rows.map((r, i) => (
            <div key={r.name} style={{
              padding: '14px 22px',
              borderBottom: i < rows.length - 1 ? `1px solid ${C.line}` : 'none',
              display: 'grid', gridTemplateColumns: '1.6fr 0.6fr 0.6fr 0.6fr', gap: 22, alignItems: 'center',
            }}>
              <div style={{ fontFamily: 'var(--display)', fontSize: 14, color: C.ink, fontWeight: 500 }}>
                {r.name}
              </div>
              <div style={{ fontFamily: 'var(--display)', fontSize: 14, color: C.ink, textAlign: 'right' }}>
                {r.tryons}
              </div>
              <div style={{ fontFamily: 'var(--display)', fontSize: 14, color: C.ink, textAlign: 'right' }}>
                {r.conv}%
              </div>
              <div style={{
                fontFamily: 'var(--display)', fontSize: 14, color: C.ink, fontWeight: 600,
                textAlign: 'right',
              }}>{r.lift}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Footnote({ C }: { C: Palette }) {
  return (
    <section style={{ background: C.bg, color: C.mute, padding: '28px 32px 44px', borderTop: `1px solid ${C.line}` }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <p style={{ fontFamily: 'var(--display)', fontSize: 12, lineHeight: 1.6, margin: 0 }}>
          Ramin Studios pilot data, 2026-04-17 to 2026-05-02. Baselines: McKinsey State of Fashion 2025 (industry conversion), Shopify Plus Apparel benchmark 2024 (AOV), Coresight 2024 (apparel return rate). Fit confidence is the per-SKU average from our recommendation engine. Numbers refresh hourly when the brand dashboard is connected to Shopify Analytics.
        </p>
      </div>
    </section>
  );
}

export default function CohortsPage() {
  const { theme } = useTheme();
  const dark = theme === 'dark';
  const C = dark ? PAL.dark : PAL.light;
  const router = useRouter();
  const mobile = useIsMobile();

  const links = [
    { label: 'Overview', onClick: () => router.push('/brand') },
    { label: 'Cohorts', onClick: () => router.push('/brand/cohorts'), active: true },
    { label: 'Garments', onClick: () => router.push('/brand/garments') },
  ];

  return (
    <div className="tryon-redesign-root" style={{
      width: '100%', minHeight: '100vh',
      background: C.bg, color: C.ink, position: 'relative',
    }}>
      <SharedNav
        dark={dark}
        homeHref="/brand"
        links={mobile ? undefined : links}
        rightSlot={
          <NavLink dark={dark} label={mobile ? 'Dashboard' : 'Back to dashboard'} href="/brand" />
        }
      />
      <Hero C={C} />
      <MetricGrid C={C} />
      <Funnel C={C} />
      <Dwell C={C} />
      <TopProducts C={C} />
      <Footnote C={C} />
    </div>
  );
}
