'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from '@/contexts/ThemeContext';
import { SharedNav, NavLink } from '@/components/redesign/SharedNav';
import { useIsMobile } from '@/components/redesign/useIsMobile';
import { getCurrentUser } from '@/lib/supabase-auth';
import {
  api, getMyBrand,
  type AnalyticsMetrics, type CohortComparisonData, type DwellMetrics, type MetricsByProductResponse,
} from '@/lib/api';

// Everything on this page is measured: the brand's own events for the last 30 days, with
// the same definitions as the dashboard (backend/app/services/analytics_cohort.py).
// A number that cannot be measured yet shows as a dash, never as an estimate.
const WINDOW_DAYS = 30;

type ProductRow = {
  product_id: string;
  tryons_started?: number;
  add_to_carts?: number;
  purchases?: number;
  tryon_purchase_rate?: number | null;
};

type CohortData = {
  shop: string;
  start: string;
  end: string;
  cohort: CohortComparisonData | null;
  metrics: AnalyticsMetrics | null;
  dwell: DwellMetrics | null;
  products: ProductRow[];
};

const localIsoDate = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

function lastDays(days: number): { start: string; end: string } {
  const end = new Date();
  const start = new Date(end.getFullYear(), end.getMonth(), end.getDate() - (days - 1));
  return { start: localIsoDate(start), end: localIsoDate(end) };
}

const pct = (v: number | null | undefined, digits = 1) => (v != null ? `${(v * 100).toFixed(digits)}%` : '–');
const eur = (v: number | null | undefined) => (v != null ? `€${v.toFixed(2)}` : '–');
const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`;

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

function Hero({ C, data }: { C: Palette; data: CohortData }) {
  const c = data.cohort;
  const orders = c?.tryon_purchases ?? 0;
  const sessions = c?.tryon_sessions ?? 0;
  const minOrders = c?.min_orders_for_comparison ?? 20;
  const aovRatio = c?.comparable && c.tryon_aov && c.baseline_aov ? c.tryon_aov / c.baseline_aov : null;

  let headline: React.ReactNode;
  let sub: string;
  if (aovRatio != null) {
    headline = <>Try-on orders are worth <CountUp to={aovRatio} decimals={2} suffix="x" /> a store order.</>;
    sub = `Average order value of ${plural(orders, 'try-on order')} against ${plural(c?.baseline_orders ?? 0, 'store order')} that did not come through the widget.`;
  } else if (orders > 0) {
    headline = <>{plural(orders, 'try-on order')} so far.</>;
    sub = `That is too few to compare with the rest of the store. The comparison is shown once both sides have at least ${minOrders} orders.`;
  } else if (sessions > 0) {
    headline = <>{plural(sessions, 'try-on')}, no try-on orders yet.</>;
    sub = 'Shoppers are trying on, but no order has come through the widget in this period, so there is nothing to compare with the store yet.';
  } else {
    headline = <>No try-ons in this period.</>;
    sub = 'The comparison fills in once shoppers use the widget on your product pages.';
  }

  return (
    <section style={{ background: C.bg, color: C.ink, padding: '48px 32px 24px', borderBottom: `1px solid ${C.line}` }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <div style={{
          fontFamily: 'var(--display)', fontSize: 13, color: C.mute, fontWeight: 500, marginBottom: 10,
        }}>
          {data.shop}, last {WINDOW_DAYS} days ({data.start} to {data.end})
        </div>
        <h1 style={{
          ...headingStyle('clamp(36px, 5vw, 72px)'),
          maxWidth: 1100, marginBottom: 14,
        }}>
          {headline}
        </h1>
        <p style={{
          fontFamily: 'var(--display)', fontSize: 15, lineHeight: 1.55,
          color: C.mute, maxWidth: 720, margin: 0,
        }}>
          {sub}
        </p>
      </div>
    </section>
  );
}

type Card = {
  label: string;
  value: string;
  detail: string;
  baseline: string;
  delta: string | null;
};

function relativeDelta(tryon: number | null | undefined, baseline: number | null | undefined): string | null {
  if (tryon == null || baseline == null || baseline === 0) return null;
  const d = ((tryon - baseline) / baseline) * 100;
  return `${d >= 0 ? '+' : '−'}${Math.abs(d).toFixed(0)}% vs store`;
}

function MetricGrid({ C, data }: { C: Palette; data: CohortData }) {
  const c = data.cohort;
  const m = data.metrics;
  const comparable = !!c?.comparable;
  const orders = c?.tryon_purchases ?? 0;
  const baseOrders = c?.baseline_orders ?? 0;
  const cards: Card[] = [
    {
      label: 'Try-on conversion',
      value: pct(c?.tryon_conversion_rate),
      detail: `${m?.purchase_sessions ?? 0} of ${plural(c?.tryon_sessions ?? 0, 'try-on session')} ordered`,
      baseline: 'No store figure: store visits are not tracked.',
      delta: null,
    },
    {
      label: 'Average order value',
      value: eur(c?.tryon_aov),
      detail: plural(orders, 'try-on order'),
      baseline: `Store ${eur(c?.baseline_aov)} over ${plural(baseOrders, 'order')}`,
      delta: comparable ? relativeDelta(c?.tryon_aov, c?.baseline_aov) : null,
    },
    {
      label: 'Return rate',
      value: pct(c?.tryon_return_rate),
      detail: `${c?.tryon_returns ?? 0} of ${plural(orders, 'try-on order')} refunded`,
      baseline: `Store ${pct(c?.baseline_return_rate)} (${c?.baseline_returns ?? 0} of ${baseOrders})`,
      delta: comparable ? relativeDelta(c?.tryon_return_rate, c?.baseline_return_rate) : null,
    },
    {
      label: 'Bracketing',
      value: pct(c?.tryon_bracket_rate),
      detail: 'Orders with the same product in several sizes',
      baseline: `Store ${pct(c?.baseline_bracket_rate)}`,
      delta: comparable ? relativeDelta(c?.tryon_bracket_rate, c?.baseline_bracket_rate) : null,
    },
  ];
  return (
    <section style={{ background: C.bg, color: C.ink, padding: '24px 20px 48px' }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 0,
          border: `1px solid ${C.line}`, background: C.surface,
        }}>
          {cards.map((card) => (
            <div key={card.label} style={{
              borderRight: `1px solid ${C.line}`,
              borderBottom: `1px solid ${C.line}`,
              padding: '22px 20px',
              display: 'flex', flexDirection: 'column', gap: 12,
            }}>
              <div style={{
                fontFamily: 'var(--display)', fontSize: 12, fontWeight: 600, color: C.mute,
              }}>{card.label}</div>

              <div style={{
                fontFamily: 'var(--display)', fontSize: 38, fontWeight: 700,
                letterSpacing: '-0.025em', lineHeight: 1, color: C.ink,
                fontVariantNumeric: 'tabular-nums',
              }}>
                {card.value}
              </div>

              <div style={{ fontFamily: 'var(--display)', fontSize: 13, color: C.mute }}>
                {card.detail}
              </div>
              <div style={{ fontFamily: 'var(--display)', fontSize: 13, color: C.mute }}>
                {card.baseline}
              </div>

              {card.delta && (
                <div style={{
                  marginTop: 'auto',
                  fontFamily: 'var(--display)', fontSize: 12, fontWeight: 600, color: C.ink,
                  padding: '4px 10px',
                  border: `1px solid ${C.ink}`,
                  alignSelf: 'flex-start',
                }}>{card.delta}</div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Funnel({ C, data }: { C: Palette; data: CohortData }) {
  const m = data.metrics;
  // Four measured steps. Each is a count of distinct widget sessions; the last is orders.
  const stages = [
    { k: 'Widget opens', v: m?.widget_opens ?? 0, sub: 'Sessions that opened the widget.' },
    { k: 'Try-ons', v: m?.tryons_started ?? 0, sub: 'Sessions that dressed the avatar.' },
    { k: 'Add to cart', v: m?.add_to_carts ?? 0, sub: 'Try-on sessions that added to cart.' },
    { k: 'Orders', v: m?.purchases ?? 0, sub: `Paid within ${m?.attribution_window_days ?? WINDOW_DAYS} days of the try-on.` },
  ];
  const max = Math.max(...stages.map((s) => s.v), 1);
  return (
    <section style={{
      background: C.surface, color: C.ink, padding: '56px 32px',
      borderTop: `1px solid ${C.line}`,
    }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <h2 style={{ ...headingStyle('clamp(28px, 3.5vw, 44px)'), marginBottom: 20 }}>
          Try-on funnel.
        </h2>
        <div style={{
          border: `1px solid ${C.line}`, background: C.bg,
        }}>
          {stages.map((s, i) => {
            const pctWidth = (s.v / max) * 100;
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
                    width: `${pctWidth}%`, background: C.ink, transition: 'width 0.6s ease',
                  }} />
                </div>
                <div style={{
                  textAlign: 'right',
                  fontFamily: 'var(--display)', fontSize: 20, fontWeight: 700, color: C.ink,
                  letterSpacing: '-0.02em', fontVariantNumeric: 'tabular-nums',
                }}>
                  {s.v}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function Dwell({ C, data }: { C: Palette; data: CohortData }) {
  const d = data.dwell;
  const buckets = d?.histogram ?? [];
  const max = Math.max(...buckets.map((b) => b.sessions), 1);
  const hasData = (d?.total_sessions ?? 0) > 0 && buckets.length > 0;
  return (
    <section style={{
      background: C.bg, color: C.ink, padding: '56px 32px',
      borderTop: `1px solid ${C.line}`,
    }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 20, gap: 16, flexWrap: 'wrap' }}>
          <h2 style={{ ...headingStyle('clamp(28px, 3.5vw, 44px)'), margin: 0 }}>
            Dwell time.
          </h2>
          {hasData && (
            <div style={{ fontFamily: 'var(--display)', fontSize: 14, color: C.mute }}>
              Median <span style={{ color: C.ink, fontWeight: 600 }}>{Math.round(d?.median_dwell_seconds ?? 0)}s</span>
              {' '}over {plural(d?.total_sessions ?? 0, 'session')}
            </div>
          )}
        </div>
        {hasData ? (
          <div style={{
            border: `1px solid ${C.line}`, padding: 24, background: C.surface,
            display: 'flex', alignItems: 'flex-end', gap: 18, height: 200,
          }}>
            {buckets.map((b) => {
              const h = Math.round((b.sessions / max) * 144);
              return (
                <div key={b.label} style={{
                  flex: 1,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
                }}>
                  <div style={{
                    fontFamily: 'var(--display)', fontSize: 12, fontWeight: 600, color: C.ink,
                  }}>{b.sessions}</div>
                  <div style={{
                    width: '100%', height: h,
                    background: C.ink,
                    transition: 'height 0.6s ease',
                  }} />
                  <div style={{
                    fontFamily: 'var(--display)', fontSize: 12, color: C.mute, textAlign: 'center',
                  }}>{b.label}</div>
                </div>
              );
            })}
          </div>
        ) : (
          <EmptyRow C={C} text="No finished try-ons in this period yet." />
        )}
      </div>
    </section>
  );
}

function EmptyRow({ C, text }: { C: Palette; text: string }) {
  return (
    <div style={{
      border: `1px solid ${C.line}`, background: C.surface, padding: '28px 22px',
      fontFamily: 'var(--display)', fontSize: 14, color: C.mute,
    }}>{text}</div>
  );
}

function TopProducts({ C, data }: { C: Palette; data: CohortData }) {
  const rows = [...data.products]
    .sort((a, b) => (b.tryons_started ?? 0) - (a.tryons_started ?? 0))
    .slice(0, 8);
  const cols = '1.6fr 0.6fr 0.6fr 0.6fr 0.7fr';
  return (
    <section style={{
      background: C.surface, color: C.ink, padding: '56px 32px',
      borderTop: `1px solid ${C.line}`,
    }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <h2 style={{ ...headingStyle('clamp(28px, 3.5vw, 44px)'), marginBottom: 20 }}>
          Top products by try-on volume.
        </h2>
        {rows.length === 0 ? (
          <EmptyRow C={C} text="No products tried on in this period yet." />
        ) : (
          <div style={{ border: `1px solid ${C.line}`, background: C.bg, overflowX: 'auto' }}>
            <div style={{ minWidth: 520 }}>
              <div style={{
                padding: '12px 22px', borderBottom: `1px solid ${C.line}`,
                display: 'grid', gridTemplateColumns: cols, gap: 22,
                fontFamily: 'var(--display)', fontSize: 12, fontWeight: 600, color: C.mute,
              }}>
                <span>Product</span>
                <span style={{ textAlign: 'right' }}>Try-ons</span>
                <span style={{ textAlign: 'right' }}>Add to cart</span>
                <span style={{ textAlign: 'right' }}>Orders</span>
                <span style={{ textAlign: 'right' }}>Conversion</span>
              </div>
              {rows.map((r, i) => (
                <div key={r.product_id} style={{
                  padding: '14px 22px',
                  borderBottom: i < rows.length - 1 ? `1px solid ${C.line}` : 'none',
                  display: 'grid', gridTemplateColumns: cols, gap: 22, alignItems: 'center',
                  fontFamily: 'var(--display)', fontSize: 14, color: C.ink, fontVariantNumeric: 'tabular-nums',
                }}>
                  <div style={{ fontWeight: 500, overflowWrap: 'anywhere' }}>{r.product_id}</div>
                  <div style={{ textAlign: 'right' }}>{r.tryons_started ?? 0}</div>
                  <div style={{ textAlign: 'right' }}>{r.add_to_carts ?? 0}</div>
                  <div style={{ textAlign: 'right' }}>{r.purchases ?? 0}</div>
                  <div style={{ textAlign: 'right', fontWeight: 600 }}>{pct(r.tryon_purchase_rate, 0)}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function Footnote({ C, data }: { C: Palette; data: CohortData }) {
  const days = data.cohort?.attribution_window_days ?? WINDOW_DAYS;
  return (
    <section style={{ background: C.bg, color: C.mute, padding: '28px 32px 44px', borderTop: `1px solid ${C.line}` }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <p style={{ fontFamily: 'var(--display)', fontSize: 12, lineHeight: 1.6, margin: 0, maxWidth: 900 }}>
          How this is counted. A try-on is a widget session that dressed the avatar at least once in the period. A try-on order is a Shopify order paid within {days} days of that session&apos;s try-on. Store orders are every other order paid in the period. An order counts as returned once it has a refund, including cancellations. Conversion is try-on sessions with an order, divided by try-on sessions. All figures are this store&apos;s own data; none are industry benchmarks.
        </p>
      </div>
    </section>
  );
}

function StatusPanel({ C, text }: { C: Palette; text: string }) {
  return (
    <section style={{ background: C.bg, color: C.mute, padding: '96px 32px' }}>
      <div style={{ maxWidth: 1280, margin: '0 auto', fontFamily: 'var(--display)', fontSize: 15 }}>{text}</div>
    </section>
  );
}

export default function CohortsPage() {
  const { theme } = useTheme();
  const dark = theme === 'dark';
  const C = dark ? PAL.dark : PAL.light;
  const router = useRouter();
  const mobile = useIsMobile();
  const [data, setData] = useState<CohortData | null>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'no-store' | 'error'>('loading');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const user = await getCurrentUser();
        if (cancelled) return;
        if (!user) { router.push('/login'); return; }
        if (user.user_type !== 'brand') { router.push('/dashboard'); return; }
        const brand = await getMyBrand(user.id);
        const shop = (brand?.shopify_domain as string | undefined) || '';
        if (cancelled) return;
        if (!shop) { setStatus('no-store'); return; }
        const range = lastDays(WINDOW_DAYS);
        const params = { ...range, shop };
        const [cohort, metrics, dwell, byProduct] = await Promise.allSettled([
          api.getCohortComparison(params),
          api.getAnalyticsMetrics(params),
          api.getDwellMetrics(params),
          api.getMetricsByProduct(params),
        ]);
        if (cancelled) return;
        // The comparison and the funnel are the page; without them there is nothing honest to show.
        if (cohort.status !== 'fulfilled' || metrics.status !== 'fulfilled') { setStatus('error'); return; }
        setData({
          shop,
          ...range,
          cohort: cohort.value,
          metrics: metrics.value,
          dwell: dwell.status === 'fulfilled' ? dwell.value : null,
          products: byProduct.status === 'fulfilled'
            ? (((byProduct.value as MetricsByProductResponse).products ?? []) as ProductRow[])
            : [],
        });
        setStatus('ready');
      } catch {
        if (!cancelled) setStatus('error');
      }
    })();
    return () => { cancelled = true; };
  }, [router]);

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
        links={links}
        rightSlot={mobile ? null : (
          <NavLink dark={dark} label="Back to dashboard" href="/brand" />
        )}
      />
      {status === 'loading' && <StatusPanel C={C} text="Loading your store's numbers…" />}
      {status === 'no-store' && <StatusPanel C={C} text="No Shopify store is linked to this brand yet, so there is nothing to compare. Install the Tryon app on your store to connect it." />}
      {status === 'error' && <StatusPanel C={C} text="The numbers could not be loaded. Reload the page to try again." />}
      {status === 'ready' && data && (
        <>
          <Hero C={C} data={data} />
          <MetricGrid C={C} data={data} />
          <Funnel C={C} data={data} />
          <Dwell C={C} data={data} />
          <TopProducts C={C} data={data} />
          <Footnote C={C} data={data} />
        </>
      )}
    </div>
  );
}
