'use client';

import dynamic from 'next/dynamic';
import { useEffect, useState, useCallback, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { TryonLogo } from '@/components/TryonLogo';
import { useTheme } from '@/contexts/ThemeContext';
import { getCurrentUser, logout, type User } from '@/lib/supabase-auth';
import { api, getMyBrand, type AnalyticsMetrics, type FitMetrics, type VelocityMetrics, type AtRiskProductsResponse, type ExplorationTrendPoint, type SizeStressItem, type RegionalSizeData, type MetricsByProductResponse, type DwellMetrics, type DeviceMetricsResponse, type FitConfidenceResponse, type RepeatVisitorsResponse, type BodyShapeInsightsResponse, type ReturnMetricsData, type CohortComparisonData, type ReturnRiskResponse, type TimeSeriesResponse, type FitPurchaseCorrelationResponse, type SizeFinderAnalytics } from '@/lib/api';
import { useEnsureShopifyAdminOAuth } from '@/lib/useEnsureShopifyAdminOAuth';
import { useResolvedShopifyShop } from '@/lib/useResolvedShopifyShop';
import { formatBucket } from '@/lib/dateBuckets';

const CHART_HEIGHT = 200;

const ConversionFunnelChart = dynamic(() => import('@/components/analytics/Charts').then((m) => ({ default: m.ConversionFunnelChart })), { ssr: false });
const VelocityChart = dynamic(() => import('@/components/analytics/Charts').then((m) => ({ default: m.VelocityChart })), { ssr: false });
const SizeDistributionChart = dynamic(() => import('@/components/analytics/Charts').then((m) => ({ default: m.SizeDistributionChart })), { ssr: false });
const ExplorationTrendChart = dynamic(() => import('@/components/analytics/Charts').then((m) => ({ default: m.ExplorationTrendChart })), { ssr: false });
const RegionalSizeChart = dynamic(() => import('@/components/analytics/Charts').then((m) => ({ default: m.RegionalSizeChart })), { ssr: false });
const RegionalSizeGlobe = dynamic(() => import('@/components/analytics/RegionalSizeGlobe'), { ssr: false });
const FullFunnelChart = dynamic(() => import('@/components/analytics/Charts').then((m) => ({ default: m.FullFunnelChart })), { ssr: false });
const DeviceBreakdownChart = dynamic(() => import('@/components/analytics/Charts').then((m) => ({ default: m.DeviceBreakdownChart })), { ssr: false });
const FitConfidenceChart = dynamic(() => import('@/components/analytics/Charts').then((m) => ({ default: m.FitConfidenceChart })), { ssr: false });
const DwellTimeChart = dynamic(() => import('@/components/analytics/Charts').then((m) => ({ default: m.DwellTimeChart })), { ssr: false });
const ReturnRiskChart = dynamic(() => import('@/components/analytics/Charts').then((m) => ({ default: m.ReturnRiskChart })), { ssr: false });
const TimeSeriesChart = dynamic(() => import('@/components/analytics/Charts').then((m) => ({ default: m.TimeSeriesChart })), { ssr: false });
const FitPurchaseCorrelationChart = dynamic(() => import('@/components/analytics/Charts').then((m) => ({ default: m.FitPurchaseCorrelationChart })), { ssr: false });
const SizeFinderFunnelChart = dynamic(() => import('@/components/analytics/Charts').then((m) => ({ default: m.SizeFinderFunnelChart })), { ssr: false });
const SizeScoreChart = dynamic(() => import('@/components/analytics/Charts').then((m) => ({ default: m.SizeScoreChart })), { ssr: false });

const SIZE_ORDER = ['XS', 'S', 'M', 'L', 'XL', 'XXL'];

type Tab = 'roi' | 'fit' | 'sizefinder' | 'trend' | 'returns' | 'engagement';

// Size card funnel steps and quiz step ids, as the backend names them.
const SIZE_FINDER_STEP_LABELS: Record<string, string> = {
  opened: 'Opened',
  quiz_started: 'Quiz started',
  quiz_completed: 'Quiz done',
  estimate_shown: 'Estimate shown',
  passport_clicked: 'Passport CTA',
  build_started: 'Build started',
  build_completed: 'Build done',
  add_to_cart: 'Add to cart',
  purchase: 'Purchase',
};
const QUIZ_STEP_LABELS: Record<string, string> = {
  gender: 'Gender',
  height: 'Height',
  weight: 'Weight',
  age: 'Age',
  'shape-chest': 'Chest shape',
  'shape-belly': 'Belly shape',
  'shape-hips': 'Hips shape',
  fit: 'Fit preference',
};
const CTA_LABELS: Record<string, string> = {
  try_on: 'Try On',
  create_passport: 'Create passport',
  finish_passport: 'Finish passport',
};
const ALT_REASON_LABELS: Record<string, string> = {
  auto_sold_out: 'Sold out (auto)',
  shopper: 'Shopper picked',
};

function SunIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  );
}
function MoonIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
    </svg>
  );
}

function MetricCell({ label, value, highlight, dark }: { label: string; value: React.ReactNode; highlight?: boolean; dark: boolean }) {
  const base = 'group px-4 py-3.5 rounded-xl transition-all duration-300 ease-out';
  const hi = dark ? 'bg-white/[0.06] hover:bg-white/[0.08]' : 'bg-black/[0.06] hover:bg-black/[0.08]';
  const norm = dark ? 'bg-white/[0.03] hover:bg-white/[0.05]' : 'bg-black/[0.03] hover:bg-black/[0.05]';
  const labelCl = dark ? 'text-white/45' : 'text-black/45';
  const valCl = dark ? 'text-white' : 'text-black';
  return (
    <div className={`${base} ${highlight ? hi : norm}`}>
      <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] truncate ${labelCl}`}>{label}</p>
      <p className={`mt-1.5 text-xl font-semibold tabular-nums font-mono tracking-tight truncate ${valCl}`}>{value}</p>
    </div>
  );
}

function SizeCell({ label, data, dark }: { label: string; data: Record<string, number>; dark: boolean }) {
  const entries = Object.entries(data).sort(
    (a, b) => SIZE_ORDER.indexOf(a[0].toUpperCase()) - SIZE_ORDER.indexOf(b[0].toUpperCase())
  );
  const total = entries.reduce((s, [, v]) => s + v, 0);
  const panel = dark ? 'bg-white/[0.03]' : 'bg-black/[0.03]';
  const labelCl = dark ? 'text-white/45' : 'text-black/45';
  const valCl = dark ? 'text-white/90' : 'text-black/90';
  const borderCl = dark ? 'border-white/[0.08]' : 'border-black/[0.08]';
  const sumCl = dark ? 'text-white/40' : 'text-black/40';
  return (
    <div className={`px-4 py-3.5 rounded-xl transition-all duration-300 ${panel}`}>
      <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] mb-2 ${labelCl}`}>{label}</p>
      {entries.length ? (
        <div className="space-y-1.5 text-xs">
          {entries.slice(0, 6).map(([size, count]) => (
            <div key={size} className="flex justify-between">
              <span className={labelCl}>{size}</span>
              <span className={`font-medium tabular-nums font-mono ${valCl}`}>{count}</span>
            </div>
          ))}
          <div className={`pt-2 mt-2 border-t ${borderCl} flex justify-between ${sumCl}`}>
            <span>Σ</span>
            <span className="font-medium tabular-nums font-mono">{total}</span>
          </div>
        </div>
      ) : (
        <p className={`${sumCl} text-xs`}>-</p>
      )}
    </div>
  );
}

function EmptyState({ message, sub, dark }: { message: string; sub?: string; dark: boolean }) {
  const panel = dark ? 'bg-white/[0.02]' : 'bg-black/[0.02]';
  const icon = dark ? 'bg-white/5' : 'bg-black/5';
  const msgCl = dark ? 'text-white/60' : 'text-black/60';
  const subCl = dark ? 'text-white/40' : 'text-black/40';
  return (
    <div className={`py-8 px-6 rounded-lg text-center flex flex-col items-center justify-center ${panel}`} style={{ minHeight: CHART_HEIGHT }}>
      <div className={`w-8 h-8 mx-auto mb-3 rounded-full flex items-center justify-center ${icon}`}>
        <span className={`${subCl} text-lg`}>·</span>
      </div>
      <p className={`${msgCl} text-sm`}>{message}</p>
      {sub && <p className={`${subCl} text-xs mt-1`}>{sub}</p>}
    </div>
  );
}

function LoadingSpinner({ dark }: { dark: boolean }) {
  return (
    <div className="py-24 flex justify-center">
      <div className={`w-8 h-8 border-2 rounded-full animate-spin ${dark ? 'border-white/20 border-t-white' : 'border-black/20 border-t-black'}`} />
    </div>
  );
}

// Dashboard date ranges. Both ends are inclusive calendar days in the brand's local time:
// "1 month" on 3 Oct = 4 Sep .. 3 Oct. The backend caps spans at 366 days.
type MetricsRange = '1d' | '7d' | '1m' | '3m' | '6m' | '1y';
const RANGE_OPTIONS: { id: MetricsRange; label: string; short: string }[] = [
  { id: '1d', label: 'Today', short: '1D' },
  { id: '7d', label: 'Last 7 days', short: '1W' },
  { id: '1m', label: 'Last month', short: '1M' },
  { id: '3m', label: 'Last 3 months', short: '3M' },
  { id: '6m', label: 'Last 6 months', short: '6M' },
  { id: '1y', label: 'Last year', short: '1Y' },
];
const isMetricsRange = (v: string | null): v is MetricsRange => RANGE_OPTIONS.some((o) => o.id === v);
const localIsoDate = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
function rangeDates(range: MetricsRange, today = new Date()): { start: string; end: string } {
  const end = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const start = new Date(end);
  if (range === '7d') start.setDate(start.getDate() - 6);
  else if (range !== '1d') {
    const months = range === '1m' ? 1 : range === '3m' ? 3 : range === '6m' ? 6 : 12;
    start.setMonth(start.getMonth() - months);
    start.setDate(start.getDate() + 1);
  }
  return { start: localIsoDate(start), end: localIsoDate(end) };
}

const fmtPct = (v: number | null | undefined) => v != null ? `${(v * 100).toFixed(1)}%` : '-';
const fmtEur = (v: number | null | undefined) => v != null ? `€${v.toFixed(2)}` : '-';
const fmtHours = (v: number | null | undefined) => v != null ? `${v.toFixed(0)}h` : '-';

export default function BrandDashboardPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { theme, toggleTheme } = useTheme();
  const shopParam = searchParams.get('shop');
  const dark = theme === 'dark';
  const [user, setUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [tab, setTab] = useState<Tab>('roi');
  const [metrics, setMetrics] = useState<AnalyticsMetrics | null>(null);
  const [fitMetrics, setFitMetrics] = useState<FitMetrics | null>(null);
  const [velocity, setVelocity] = useState<VelocityMetrics | null>(null);
  const [atRisk, setAtRisk] = useState<AtRiskProductsResponse | null>(null);
  const [explorationTrend, setExplorationTrend] = useState<ExplorationTrendPoint[]>([]);
  const [sizeStress, setSizeStress] = useState<SizeStressItem[]>([]);
  const [regionalSize, setRegionalSize] = useState<RegionalSizeData | null>(null);
  const [regionalView, setRegionalView] = useState<'globe' | 'chart'>('globe');
  const [metricsByProduct, setMetricsByProduct] = useState<MetricsByProductResponse | null>(null);
  const [dwellMetrics, setDwellMetrics] = useState<DwellMetrics | null>(null);
  const [deviceMetrics, setDeviceMetrics] = useState<DeviceMetricsResponse | null>(null);
  const [fitConfidence, setFitConfidence] = useState<FitConfidenceResponse | null>(null);
  const [repeatVisitors, setRepeatVisitors] = useState<RepeatVisitorsResponse | null>(null);
  const [bodyShapeInsights, setBodyShapeInsights] = useState<BodyShapeInsightsResponse | null>(null);
  const [returnMetrics, setReturnMetrics] = useState<ReturnMetricsData | null>(null);
  const [cohortComparison, setCohortComparison] = useState<CohortComparisonData | null>(null);
  const [returnRisk, setReturnRisk] = useState<ReturnRiskResponse | null>(null);
  const [timeSeries, setTimeSeries] = useState<TimeSeriesResponse | null>(null);
  const [fitPurchaseCorrelation, setFitPurchaseCorrelation] = useState<FitPurchaseCorrelationResponse | null>(null);
  const [sizeFinder, setSizeFinder] = useState<SizeFinderAnalytics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  // Range lives in the URL (?range=3m) so a view can be bookmarked or shared.
  const [metricsRange, setMetricsRangeState] = useState<MetricsRange>(() => {
    const r = searchParams.get('range');
    return isMetricsRange(r) ? r : '1m';
  });
  const setMetricsRange = useCallback((r: MetricsRange) => {
    setMetricsRangeState(r);
    try {
      const u = new URL(window.location.href);
      u.searchParams.set('range', r);
      window.history.replaceState(null, '', u.toString());
    } catch {}
  }, []);
  const [metricsShop, setMetricsShop] = useState('');
  const [brandShop, setBrandShop] = useState<string | null>(null);
  const [hasGarments, setHasGarments] = useState(true);
  const [brandLoaded, setBrandLoaded] = useState(false);
  const [guideDismissed, setGuideDismissed] = useState(false);
  const resolvedShop = useResolvedShopifyShop(brandShop);
  useEnsureShopifyAdminOAuth(resolvedShop, searchParams.get('error'), {
    pauseOAuth: !brandLoaded,
  });

  // Each fetch gets an id; a response is applied only if no newer fetch started since,
  // so a slow earlier response (other range or shop) can never overwrite fresh data.
  const fetchIdRef = useRef(0);

  const fetchMetrics = useCallback(async () => {
    // Analytics are always scoped to the brand's own store: never fetch before it's known.
    if (!metricsShop) return;
    const fetchId = ++fetchIdRef.current;
    setMetricsLoading(true);
    setFetchError(null);
    const params: { start: string; end: string; shop: string } = { ...rangeDates(metricsRange), shop: metricsShop };
    const calls = [
      () => api.getAnalyticsMetrics(params),
      () => api.getFitMetrics(params),
      () => api.getVelocityMetrics(params),
      () => api.getAtRiskProducts(params),
      () => api.getExplorationTrend(params),
      () => api.getSizeStress(params),
      () => api.getRegionalSize(params),
      () => api.getMetricsByProduct(params),
      () => api.getDwellMetrics(params),
      () => api.getDeviceMetrics(params),
      () => api.getFitConfidence(params),
      () => api.getRepeatVisitors(params),
      () => api.getBodyShapeInsights(params),
      () => api.getReturnMetrics(params),
      () => api.getCohortComparison(params),
      () => api.getReturnRisk({ shop: metricsShop }),
      () => api.getTimeSeries(params),
      () => api.getFitPurchaseCorrelation(params),
      () => api.getSizeFinderAnalytics(params),
    ];
    const results = await Promise.allSettled(calls.map((fn) => fn()));
    if (fetchId !== fetchIdRef.current) return; // superseded by a newer range/shop
    const failures = results.filter((r): r is PromiseRejectedResult => r.status === 'rejected');
    if (failures.length > 0) {
      const reason = String(failures[0].reason?.message || failures[0].reason || '');
      if (/authori[sz]ation|401|403|not.*your|no shopify store/i.test(reason)) {
        setFetchError('You are not signed in to this store. Please sign in again.');
      } else if (failures.length === results.length) {
        setFetchError('Backend unreachable.');
      } else {
        setFetchError(`Some sections could not load (${failures.length} of ${results.length}). Try Refresh.`);
      }
    }
    // A failed section is cleared rather than left showing the previous range's numbers.
    const val = (i: number) => results[i]?.status === 'fulfilled' ? (results[i] as PromiseFulfilledResult<unknown>).value : null;
    setMetrics(val(0) as AnalyticsMetrics | null);
    setFitMetrics(val(1) as FitMetrics | null);
    setVelocity(val(2) as VelocityMetrics | null);
    setAtRisk(val(3) as AtRiskProductsResponse | null);
    const et = val(4);
    setExplorationTrend(et && typeof et === 'object' && 'data' in (et as Record<string, unknown>) ? (((et as Record<string, unknown>).data as ExplorationTrendPoint[]) || []) : []);
    const ss = val(5);
    setSizeStress(ss && typeof ss === 'object' && 'items' in (ss as Record<string, unknown>) ? (((ss as Record<string, unknown>).items as SizeStressItem[]) || []) : []);
    setRegionalSize(val(6) as RegionalSizeData | null);
    setMetricsByProduct(val(7) as MetricsByProductResponse | null);
    setDwellMetrics(val(8) as DwellMetrics | null);
    setDeviceMetrics(val(9) as DeviceMetricsResponse | null);
    setFitConfidence(val(10) as FitConfidenceResponse | null);
    setRepeatVisitors(val(11) as RepeatVisitorsResponse | null);
    setBodyShapeInsights(val(12) as BodyShapeInsightsResponse | null);
    setReturnMetrics(val(13) as ReturnMetricsData | null);
    setCohortComparison(val(14) as CohortComparisonData | null);
    setReturnRisk(val(15) as ReturnRiskResponse | null);
    setTimeSeries(val(16) as TimeSeriesResponse | null);
    setFitPurchaseCorrelation(val(17) as FitPurchaseCorrelationResponse | null);
    setSizeFinder(val(18) as SizeFinderAnalytics | null);
    setMetricsLoading(false);
  }, [metricsRange, metricsShop]);

  useEffect(() => { fetchMetrics(); }, [fetchMetrics]);

  useEffect(() => {
    const loginPath = resolvedShop ? `/login?shop=${encodeURIComponent(resolvedShop)}` : '/login';
    getCurrentUser().then(async (u) => {
      if (!u) {
        router.push(loginPath);
        return;
      }
      if (u.user_type !== 'brand') {
        router.push('/dashboard');
        return;
      }
      setUser(u);
      setAuthChecked(true);
      try {
        const brand = await getMyBrand(u.id);
        if (brand?.shopify_domain) {
          const domain = brand.shopify_domain as string;
          setBrandShop(domain);
          setMetricsShop((prev) => prev || domain);
        }
        if (brand?.id) {
          const { garmentApi } = await import('@/lib/api');
          const garments = await garmentApi.list(brand.id as string);
          setHasGarments(garments.length > 0);
        }
      } catch {}
      setBrandLoaded(true);
    }).catch(() => router.push(loginPath));
  }, [router, resolvedShop]);

  const handleLogout = async () => {
    const shopForRedirect =
      (typeof window !== 'undefined' && sessionStorage.getItem('tryon_shop_context')) ||
      shopParam ||
      brandShop;
    await logout();
    if (typeof window !== 'undefined') sessionStorage.removeItem('tryon_shop_context');
    if (shopForRedirect?.includes('.myshopify.com')) {
      router.push(`/?shop=${encodeURIComponent(shopForRedirect)}`);
    } else {
      router.push('/');
    }
  };

  if (!authChecked) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${dark ? 'bg-black' : 'bg-white'}`}>
        <div className={`w-8 h-8 border-2 rounded-full animate-spin ${dark ? 'border-white/20 border-t-white' : 'border-black/20 border-t-black'}`} />
      </div>
    );
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: 'roi', label: 'ROI & Attribution' },
    { id: 'fit', label: 'Fit Intelligence' },
    { id: 'sizefinder', label: 'Size Finder' },
    { id: 'trend', label: 'Trend & Demand' },
    { id: 'returns', label: 'Returns & Risk' },
    { id: 'engagement', label: 'Engagement' },
  ];

  const tsGranularity: 'day' | 'week' | 'month' = timeSeries?.granularity ?? 'week';

  const panelClass = dark
    ? 'rounded-2xl bg-white/[0.03] backdrop-blur-sm transition-all duration-300'
    : 'rounded-2xl bg-black/[0.03] backdrop-blur-sm transition-all duration-300';
  const tableHeaderClass = dark ? 'text-left py-3 px-4 text-[10px] font-semibold uppercase tracking-[0.2em] text-white/45' : 'text-left py-3 px-4 text-[10px] font-semibold uppercase tracking-[0.2em] text-black/45';
  const tableCellClass = dark ? 'py-3 px-4 text-sm text-white/90' : 'py-3 px-4 text-sm text-black/90';
  const chartPanelMinH = { minHeight: CHART_HEIGHT };
  const borderCl = dark ? 'border-white/10' : 'border-black/10';
  const rowHover = dark ? 'hover:bg-white/5' : 'hover:bg-black/5';
  const labelCl = dark ? 'text-white/45' : 'text-black/45';
  const badgeCl = dark ? 'bg-white/10 text-white/70' : 'bg-black/10 text-black/70';

  return (
    <div className={`min-h-screen transition-colors ${dark ? 'bg-black text-white' : 'bg-white text-black'}`}>
      <header className={`sticky top-0 z-20 backdrop-blur-xl border-b ${dark ? 'bg-black/95 border-white/10' : 'bg-white/95 border-black/10'}`}>
        <div className="max-w-7xl mx-auto px-4 py-2 md:py-1.5 flex flex-col gap-3 md:flex-row md:items-center md:gap-4">
          <div className="flex items-center justify-between gap-2 md:contents">
            <TryonLogo href="/" className="h-4 w-auto rounded" />
            <div className="flex items-center gap-2 shrink-0 md:hidden">
              <button
                onClick={toggleTheme}
                className={`p-1.5 rounded transition-colors ${dark ? 'text-white/50 hover:text-white/80' : 'text-black/50 hover:text-black/80'}`}
                title={dark ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                {dark ? <SunIcon /> : <MoonIcon />}
              </button>
              <button
                onClick={fetchMetrics}
                disabled={metricsLoading}
                className={`text-[10px] px-3 py-1.5 rounded border disabled:opacity-50 transition-colors ${dark ? 'bg-white text-black border-white/50 hover:bg-white/90' : 'bg-black text-white border-black/50 hover:bg-black/90'}`}
              >
                {metricsLoading ? '...' : 'Refresh'}
              </button>
              <button onClick={handleLogout} className={`${dark ? 'text-white/40 hover:text-white/70' : 'text-black/40 hover:text-black/70'} text-[10px] transition-colors whitespace-nowrap`}>Sign out</button>
            </div>
          </div>
          <nav className="flex gap-0.5 min-w-0 overflow-x-auto pb-1 -mx-1 md:overflow-visible md:pb-0 md:mx-0">
            {tabs.map(({ id, label }) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={`px-2.5 py-1.5 text-xs font-medium transition-all whitespace-nowrap shrink-0 ${
                  tab === id
                    ? dark ? 'text-white' : 'text-black'
                    : dark ? 'text-white/35 hover:text-white/60' : 'text-black/35 hover:text-black/60'
                }`}
              >
                {label}
              </button>
            ))}
            <Link
              href="/brand/garments"
              className={`px-2.5 py-1.5 text-xs font-medium transition-all whitespace-nowrap shrink-0 ${dark ? 'text-white/35 hover:text-white/60' : 'text-black/35 hover:text-black/60'}`}
            >
              Garments
            </Link>
            <div className="flex items-center gap-2 shrink-0 pl-2 md:hidden">
              <select
                id="metrics-shop-mobile"
                name="metrics-shop"
                value={metricsShop}
                onChange={(e) => setMetricsShop(e.target.value)}
                className={`text-[10px] px-2 py-1 rounded border focus:outline-none ${dark ? 'bg-white/5 border-white/10 text-white/70' : 'bg-black/5 border-black/10 text-black/70'}`}
              >
                {!brandShop && <option value="">No store linked</option>}
                {brandShop && <option value={brandShop}>{brandShop}</option>}
              </select>
              <select
                id="metrics-range-mobile"
                name="metrics-range"
                value={metricsRange}
                onChange={(e) => setMetricsRange(e.target.value as MetricsRange)}
                aria-label="Date range"
                className={`text-[10px] px-2 py-1 rounded border focus:outline-none ${dark ? 'bg-white/5 border-white/10 text-white/70' : 'bg-black/5 border-black/10 text-black/70'}`}
              >
                {RANGE_OPTIONS.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
              </select>
            </div>
          </nav>
          <div className="hidden md:flex items-center gap-2 ml-auto shrink-0">
            <select
              id="metrics-shop-desktop"
              name="metrics-shop"
              value={metricsShop}
              onChange={(e) => setMetricsShop(e.target.value)}
              className={`text-[10px] px-2 py-1 rounded border focus:outline-none ${dark ? 'bg-white/5 border-white/10 text-white/70' : 'bg-black/5 border-black/10 text-black/70'}`}
            >
              {!brandShop && <option value="">No store linked</option>}
              {brandShop && <option value={brandShop}>{brandShop}</option>}
            </select>
            <select
              id="metrics-range-desktop"
              name="metrics-range"
              value={metricsRange}
              onChange={(e) => setMetricsRange(e.target.value as MetricsRange)}
              aria-label="Date range"
              className={`text-[10px] px-2 py-1 rounded border focus:outline-none ${dark ? 'bg-white/5 border-white/10 text-white/70' : 'bg-black/5 border-black/10 text-black/70'}`}
            >
              {RANGE_OPTIONS.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
            </select>
            <button
              onClick={toggleTheme}
              className={`p-1 rounded transition-colors ${dark ? 'text-white/50 hover:text-white/80' : 'text-black/50 hover:text-black/80'}`}
              title={dark ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {dark ? <SunIcon /> : <MoonIcon />}
            </button>
            <button
              onClick={fetchMetrics}
              disabled={metricsLoading}
              className={`text-[10px] px-2.5 py-1 rounded border disabled:opacity-50 transition-colors ${dark ? 'bg-white text-black border-white/50 hover:bg-white/90' : 'bg-black text-white border-black/50 hover:bg-black/90'}`}
            >
              {metricsLoading ? '...' : 'Refresh'}
            </button>
            {user && <span className={`${dark ? 'text-white/40' : 'text-black/40'} text-[10px]`}>{user.email}</span>}
            <button onClick={handleLogout} className={`${dark ? 'text-white/40 hover:text-white/70' : 'text-black/40 hover:text-black/70'} text-[10px] transition-colors`}>Sign out</button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-5 py-6 dashboard-fade-in">
        {brandLoaded && !guideDismissed && (!brandShop || !hasGarments) && (
          <div className={`mb-6 rounded-xl border p-5 relative ${dark ? 'bg-white/[0.03] border-white/10' : 'bg-gradient-to-r from-blue-50 to-purple-50 border-blue-100'}`}>
            <button onClick={() => setGuideDismissed(true)} className={`absolute top-3 right-3 p-1 rounded transition ${dark ? 'text-white/30 hover:text-white/60' : 'text-gray-400 hover:text-gray-600'}`} aria-label="Dismiss">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
            <h3 className={`text-sm font-semibold mb-3 ${dark ? 'text-white' : 'text-gray-900'}`}>Getting Started</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className={`flex items-start gap-3 p-3 rounded-lg ${dark ? 'bg-white/5' : 'bg-white'}`}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold ${brandShop ? (dark ? 'bg-green-500/20 text-green-400' : 'bg-green-100 text-green-600') : (dark ? 'bg-white/10 text-white/40' : 'bg-gray-100 text-gray-400')}`}>
                  {brandShop ? '✓' : '1'}
                </div>
                <div>
                  <p className={`text-xs font-medium ${dark ? 'text-white/80' : 'text-gray-800'}`}>Connect Shopify Store</p>
                  <p className={`text-xs mt-0.5 ${dark ? 'text-white/40' : 'text-gray-500'}`}>
                    {brandShop ? `Connected: ${brandShop}` : 'Install the app on your Shopify store'}
                  </p>
                </div>
              </div>
              <Link href="/brand/garments" className={`flex items-start gap-3 p-3 rounded-lg transition hover:ring-1 ${dark ? 'bg-white/5 hover:ring-white/20' : 'bg-white hover:ring-blue-200'}`}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold ${hasGarments ? (dark ? 'bg-green-500/20 text-green-400' : 'bg-green-100 text-green-600') : (dark ? 'bg-white/10 text-white/40' : 'bg-gray-100 text-gray-400')}`}>
                  {hasGarments ? '✓' : '2'}
                </div>
                <div>
                  <p className={`text-xs font-medium ${dark ? 'text-white/80' : 'text-gray-800'}`}>Add Your Garments</p>
                  <p className={`text-xs mt-0.5 ${dark ? 'text-white/40' : 'text-gray-500'}`}>
                    {hasGarments ? 'Garments added' : 'Upload GLB files and size charts'}
                  </p>
                </div>
              </Link>
              <div className={`flex items-start gap-3 p-3 rounded-lg ${dark ? 'bg-white/5' : 'bg-white'}`}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold ${dark ? 'bg-white/10 text-white/40' : 'bg-gray-100 text-gray-400'}`}>3</div>
                <div>
                  <p className={`text-xs font-medium ${dark ? 'text-white/80' : 'text-gray-800'}`}>Enable Try-On Widget</p>
                  <p className={`text-xs mt-0.5 ${dark ? 'text-white/40' : 'text-gray-500'}`}>Add the Try On block to your product pages in the theme editor</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {brandLoaded && !brandShop && (
          <div className={`mb-5 p-4 rounded-xl text-sm ${dark ? 'bg-white/[0.03] text-white/70' : 'bg-black/[0.03] text-black/70'}`}>
            No Shopify store is linked to this brand yet, so there are no analytics to show. Install the Tryon app on your store to connect it.
          </div>
        )}
        {fetchError && (
          <div className={`mb-5 p-4 rounded-xl text-sm flex items-center justify-between ${dark ? 'bg-white/[0.03] text-white/70' : 'bg-black/[0.03] text-black/70'}`}>
            <span>{fetchError}</span>
            <button onClick={fetchMetrics} disabled={metricsLoading} className={`px-4 py-2 rounded-lg ${dark ? 'bg-white/10 hover:bg-white/20' : 'bg-black/10 hover:bg-black/20'}`}>Retry</button>
          </div>
        )}

        {/* ═══ TAB 1: ROI & Attribution ═══ */}
        {tab === 'roi' && (
          <div className="space-y-6">
            {metricsLoading && !metrics ? (
              <LoadingSpinner dark={dark} />
            ) : metrics ? (
              <>
                {/* Full Funnel Overview */}
                <div className={`${panelClass} p-5`}>
                  <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] mb-1 ${labelCl}`}>Full funnel overview</p>
                  <p className={`text-xs mb-4 ${dark ? 'text-white/40' : 'text-black/40'}`}>
                    Try-on sessions only. Each session counts once per step; a purchase is an order paid within {metrics.attribution_window_days ?? 30} days of the try-on. Store orders that did not come through the widget are under Returns &amp; Risk.
                  </p>
                  <div style={{ height: CHART_HEIGHT }}>
                    <FullFunnelChart
                      widgetOpens={metrics.widget_opens ?? 0}
                      tryons={metrics.tryons_started ?? 0}
                      atc={metrics.add_to_carts ?? 0}
                      purchases={metrics.purchases ?? 0}
                      dark={dark}
                    />
                  </div>
                </div>

                {/* Weekly Trends */}
                {timeSeries && timeSeries.weeks.length <= 1 && (
                  <p className={`text-[11px] ${labelCl}`}>Trend charts appear for ranges longer than a day.</p>
                )}
                {timeSeries && timeSeries.weeks.length > 1 && (
                  <div className="space-y-4">
                    <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] ${labelCl}`}>{tsGranularity === 'day' ? 'Daily' : tsGranularity === 'month' ? 'Monthly' : 'Weekly'} trends</p>
                    <div className={`${panelClass} p-5`}>
                      <p className={`text-[9px] font-semibold uppercase tracking-[0.2em] mb-3 ${labelCl}`}>Rates</p>
                      <TimeSeriesChart weeks={timeSeries.weeks} metrics={['conversion_rate', 'atc_rate']} dark={dark} granularity={tsGranularity} />
                    </div>
                    <div className={`${panelClass} p-5`}>
                      <p className={`text-[9px] font-semibold uppercase tracking-[0.2em] mb-3 ${labelCl}`}>Volume</p>
                      <TimeSeriesChart weeks={timeSeries.weeks} metrics={['tryons', 'add_to_carts', 'purchases']} dark={dark} granularity={tsGranularity} />
                    </div>
                    <div className={`${panelClass} overflow-hidden`}>
                      <table className="w-full text-left text-[11px]">
                        <thead>
                          <tr className={tableHeaderClass}>
                            <th className="px-4 py-2 font-semibold">{tsGranularity === 'day' ? 'Day' : tsGranularity === 'month' ? 'Month' : 'Week of'}</th>
                            <th className="px-4 py-2 font-semibold text-right">Opens</th>
                            <th className="px-4 py-2 font-semibold text-right">Try-Ons</th>
                            <th className="px-4 py-2 font-semibold text-right">ATC</th>
                            <th className="px-4 py-2 font-semibold text-right">Purchases</th>
                            <th className="px-4 py-2 font-semibold text-right">Revenue</th>
                            <th className="px-4 py-2 font-semibold text-right">Conv %</th>
                            <th className="px-4 py-2 font-semibold text-right">ATC %</th>
                          </tr>
                        </thead>
                        <tbody>
                          {[...timeSeries.weeks].reverse().map((w) => (
                            <tr key={w.week_start} className={rowHover}>
                              <td className={`px-4 py-2 ${borderCl}`}>{formatBucket(w.week_start, tsGranularity, true)}</td>
                              <td className={`px-4 py-2 text-right ${borderCl}`}>{w.widget_opens}</td>
                              <td className={`px-4 py-2 text-right ${borderCl}`}>{w.tryons}</td>
                              <td className={`px-4 py-2 text-right ${borderCl}`}>{w.add_to_carts}</td>
                              <td className={`px-4 py-2 text-right ${borderCl}`}>{w.purchases}</td>
                              <td className={`px-4 py-2 text-right ${borderCl}`}>€{w.revenue.toFixed(2)}</td>
                              <td className={`px-4 py-2 text-right ${borderCl}`}>{w.conversion_rate != null ? `${w.conversion_rate.toFixed(1)}%` : '-'}</td>
                              <td className={`px-4 py-2 text-right ${borderCl}`}>{w.atc_rate != null ? `${w.atc_rate.toFixed(1)}%` : '-'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Core metrics grid */}
                <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-10 gap-3">
                  <MetricCell label="Widget Opens" value={metrics.widget_opens ?? 0} dark={dark} />
                  <MetricCell label="Tryons" value={metrics.tryons_started} dark={dark} />
                  <MetricCell label="ATC" value={metrics.add_to_carts} dark={dark} />
                  <MetricCell label="Purchases" value={metrics.purchases} dark={dark} />
                  <MetricCell label="Widget Sessions" value={metrics.unique_sessions} dark={dark} />
                  <MetricCell label="Open→Tryon %" value={fmtPct(metrics.open_to_tryon_rate)} dark={dark} />
                  <MetricCell label="ATC %" value={fmtPct(metrics.tryon_atc_rate)} highlight dark={dark} />
                  <MetricCell label="Purchase %" value={fmtPct(metrics.tryon_purchase_rate)} highlight dark={dark} />
                  <MetricCell label="Revenue" value={fmtEur(metrics.revenue_attributed)} dark={dark} />
                  <MetricCell label="Rev/Tryon" value={fmtEur(metrics.revenue_per_tryon)} dark={dark} />
                </div>
                <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-10 gap-3">
                  <MetricCell label="AOV" value={fmtEur(metrics.aov_tryon)} dark={dark} />
                  <MetricCell
                    label="Cart Abandon %"
                    value={fmtPct(metrics.cart_abandonment_rate)}
                    highlight={metrics.cart_abandonment_rate != null && metrics.cart_abandonment_rate > 0.5}
                    dark={dark}
                  />
                  <MetricCell label="Avg Time to Purch" value={fmtHours(metrics.avg_time_to_purchase_hours)} dark={dark} />
                  <MetricCell label="Same-Session %" value={fmtPct(metrics.same_session_purchase_rate)} dark={dark} />
                  <MetricCell label="Returns" value={metrics.returns ?? 0} dark={dark} />
                  <MetricCell label="Return Rate" value={fmtPct(metrics.return_rate)} dark={dark} />
                  <MetricCell label="Revenue Lost" value={fmtEur(metrics.revenue_lost_to_returns)} dark={dark} />
                  <MetricCell label="Bracket Orders" value={metrics.bracket_orders ?? 0} dark={dark} />
                  <MetricCell label="Bracket Rate" value={fmtPct(metrics.bracket_rate)} dark={dark} />
                </div>

                {/* Conversion funnel chart */}
                <div className={`${panelClass} p-5`} style={chartPanelMinH}>
                  <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] mb-4 ${labelCl}`}>Conversion funnel</p>
                  <div style={{ height: CHART_HEIGHT }}><ConversionFunnelChart tryons={metrics.tryons_started ?? 0} atc={metrics.add_to_carts ?? 0} purchases={metrics.purchases ?? 0} dark={dark} /></div>
                </div>

                {/* Products table */}
                {metricsByProduct && (metricsByProduct.products?.length ?? 0) > 0 && (
                  <div className={`${panelClass} overflow-hidden`}>
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead><tr className={`border-b ${borderCl}`}>
                          <th className={tableHeaderClass}>Product</th>
                          <th className={`${tableHeaderClass} text-right`}>Tryons</th>
                          <th className={`${tableHeaderClass} text-right`}>ATC</th>
                          <th className={`${tableHeaderClass} text-right`}>Purch</th>
                          <th className={`${tableHeaderClass} text-right`}>Revenue</th>
                          <th className={`${tableHeaderClass} text-right`}>AOV</th>
                        </tr></thead>
                        <tbody>
                          {((metricsByProduct.products ?? []) as Array<{ product_id: string; tryons_started?: number; add_to_carts?: number; purchases?: number; revenue_attributed?: number; aov_tryon?: number | null }>).slice(0, 10).map((p, i) => (
                            <tr key={p.product_id} className={`border-b ${borderCl} last:border-0 ${rowHover} transition-colors ${i % 2 ? (dark ? 'bg-white/[0.02]' : 'bg-black/[0.02]') : ''}`}>
                              <td className={`${tableCellClass} font-medium`}>{p.product_id}</td>
                              <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{p.tryons_started}</td>
                              <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{p.add_to_carts}</td>
                              <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{p.purchases}</td>
                              <td className={`${tableCellClass} text-right font-mono tabular-nums`}>€{(p.revenue_attributed ?? 0).toFixed(2)}</td>
                               <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{p.aov_tryon != null ? `€${p.aov_tryon.toFixed(2)}` : '-'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </>
            ) : !fetchError && (
              <EmptyState message="No metrics yet" sub="Use the Tryon widget, then refresh" dark={dark} />
            )}
          </div>
        )}

        {/* ═══ TAB 2: Fit Intelligence ═══ */}
        {tab === 'fit' && (
          <div className="space-y-6">
            {metricsLoading && !fitMetrics ? (
              <LoadingSpinner dark={dark} />
            ) : fitMetrics ? (
              <>
                <div className="grid grid-cols-4 sm:grid-cols-6 gap-3">
                  <MetricCell label="Acceptance" value={fitMetrics.acceptance_rate != null ? `${(Number(fitMetrics.acceptance_rate) * 100).toFixed(1)}%` : '-'} highlight dark={dark} />
                  <MetricCell label="Size up" value={fitMetrics.size_up_rate != null ? `${(Number(fitMetrics.size_up_rate) * 100).toFixed(1)}%` : '-'} dark={dark} />
                  <MetricCell label="Size down" value={fitMetrics.size_down_rate != null ? `${(Number(fitMetrics.size_down_rate) * 100).toFixed(1)}%` : '-'} dark={dark} />
                  <MetricCell label="MASE" value={fitMetrics.mase != null ? Number(fitMetrics.mase).toFixed(2) : '-'} dark={dark} />
                  <MetricCell label="Sess w/ rec" value={String(fitMetrics.sessions_with_recommendation ?? '-')} dark={dark} />
                  <MetricCell label="Purch+size" value={String(fitMetrics.sessions_with_purchase_and_size ?? '-')} dark={dark} />
                </div>
                <div className={`${panelClass} p-5`} style={chartPanelMinH}>
                  <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] mb-2 ${labelCl}`}>Size distribution</p>
                  <p className={`text-xs mb-4 ${dark ? 'text-white/40' : 'text-black/40'}`}>Recommended = what we suggested · Selected = what they chose · Purchased = what they bought</p>
                  <div style={{ height: CHART_HEIGHT }}><SizeDistributionChart recommended={(fitMetrics.size_distribution_recommended ?? {}) as Record<string, number>} selected={(fitMetrics.size_distribution_selected ?? {}) as Record<string, number>} purchased={(fitMetrics.size_distribution_purchased ?? {}) as Record<string, number>} dark={dark} /></div>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <SizeCell label="Recommended" data={(fitMetrics.size_distribution_recommended ?? {}) as Record<string, number>} dark={dark} />
                  <SizeCell label="Selected" data={(fitMetrics.size_distribution_selected ?? {}) as Record<string, number>} dark={dark} />
                  <SizeCell label="Purchased" data={(fitMetrics.size_distribution_purchased ?? {}) as Record<string, number>} dark={dark} />
                </div>

                {/* Fit-to-Purchase Correlation */}
                {fitPurchaseCorrelation && fitPurchaseCorrelation.buckets.length > 0 && (
                  <div className="space-y-4">
                    <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] ${labelCl}`}>Fit-to-purchase correlation</p>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      <MetricCell label="Sessions w/ Rec" value={fitPurchaseCorrelation.total_sessions_with_recommendation} dark={dark} />
                      <MetricCell label="Acceptance Rate" value={fitPurchaseCorrelation.overall_acceptance_rate != null ? `${fitPurchaseCorrelation.overall_acceptance_rate.toFixed(1)}%` : '-'} highlight dark={dark} />
                      <MetricCell label="Buckets" value={fitPurchaseCorrelation.buckets.length} dark={dark} />
                    </div>
                    <div className={`${panelClass} p-5`}>
                      <FitPurchaseCorrelationChart buckets={fitPurchaseCorrelation.buckets} dark={dark} />
                    </div>
                    <div className={`${panelClass} overflow-hidden`}>
                      <table className="w-full text-left text-[11px]">
                        <thead>
                          <tr className={tableHeaderClass}>
                            <th className="px-4 py-2 font-semibold">Deviation</th>
                            <th className="px-4 py-2 font-semibold text-right">Sessions</th>
                            <th className="px-4 py-2 font-semibold text-right">Purchases</th>
                            <th className="px-4 py-2 font-semibold text-right">Returns</th>
                            <th className="px-4 py-2 font-semibold text-right">Purchase %</th>
                            <th className="px-4 py-2 font-semibold text-right">Return %</th>
                          </tr>
                        </thead>
                        <tbody>
                          {fitPurchaseCorrelation.buckets.map((b) => (
                            <tr key={b.deviation} className={rowHover}>
                              <td className={`px-4 py-2 font-medium ${borderCl}`}>
                                <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold ${b.deviation === 'accepted' ? 'bg-green-500/15 text-green-400' : b.deviation.startsWith('size_up') ? 'bg-amber-500/15 text-amber-400' : b.deviation.startsWith('size_down') ? 'bg-blue-500/15 text-blue-400' : 'bg-gray-500/15 text-gray-400'}`}>
                                  {b.deviation === 'accepted' ? 'Accepted' : b.deviation === 'size_up_1' ? '↑ +1 size' : b.deviation === 'size_down_1' ? '↓ -1 size' : b.deviation === 'size_up_2+' ? '↑↑ +2 sizes' : b.deviation === 'size_down_2+' ? '↓↓ -2 sizes' : b.deviation}
                                </span>
                              </td>
                              <td className={`px-4 py-2 text-right ${borderCl}`}>{b.sessions}</td>
                              <td className={`px-4 py-2 text-right ${borderCl}`}>{b.purchases}</td>
                              <td className={`px-4 py-2 text-right ${borderCl}`}>{b.returns}</td>
                              <td className={`px-4 py-2 text-right ${borderCl}`}>{b.purchase_rate != null ? `${b.purchase_rate.toFixed(1)}%` : '-'}</td>
                              <td className={`px-4 py-2 text-right ${borderCl}`}>{b.return_rate != null ? `${b.return_rate.toFixed(1)}%` : '-'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Per-Product Fit Confidence */}
                {fitConfidence && fitConfidence.products && fitConfidence.products.length > 0 && (
                  <div className="space-y-4">
                    <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] ${labelCl}`}>Per-product fit confidence</p>
                    <div className={`${panelClass} p-5`} style={chartPanelMinH}>
                      <div style={{ height: CHART_HEIGHT }}>
                        <FitConfidenceChart products={fitConfidence.products.slice(0, 10)} dark={dark} />
                      </div>
                    </div>
                    <div className={`${panelClass} overflow-hidden`}>
                      <div className="overflow-x-auto">
                        <table className="w-full">
                          <thead><tr className={`border-b ${borderCl}`}>
                            <th className={tableHeaderClass}>Product</th>
                            <th className={`${tableHeaderClass} text-right`}>Confidence</th>
                            <th className={`${tableHeaderClass} text-right`}>Recommendations</th>
                            <th className={`${tableHeaderClass} text-right`}>Accepted</th>
                            <th className={`${tableHeaderClass} text-right`}>Size Up</th>
                            <th className={`${tableHeaderClass} text-right`}>Size Down</th>
                            <th className={tableHeaderClass}>Deviation</th>
                          </tr></thead>
                          <tbody>
                            {fitConfidence.products.slice(0, 10).map((p, i) => (
                              <tr key={p.product_id} className={`border-b ${borderCl} last:border-0 ${rowHover} transition-colors ${i % 2 ? (dark ? 'bg-white/[0.02]' : 'bg-black/[0.02]') : ''}`}>
                                <td className={`${tableCellClass} font-medium`}>{p.product_id}</td>
                                <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{p.fit_confidence_score.toFixed(1)}%</td>
                                <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{p.total_recommendations}</td>
                                <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{p.acceptance_count}</td>
                                <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{p.size_up_count}</td>
                                <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{p.size_down_count}</td>
                                <td className={tableCellClass}><span className={`px-1.5 py-0.5 rounded text-[10px] ${badgeCl}`}>{p.most_common_deviation ?? 'none'}</span></td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}

                {/* Body Shape Insights */}
                {bodyShapeInsights && bodyShapeInsights.insights && bodyShapeInsights.insights.length > 0 && (
                  <div className="space-y-4">
                    <div className="flex items-center gap-3">
                      <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] ${labelCl}`}>Body shape insights</p>
                      <span className={`text-[10px] font-mono tabular-nums ${dark ? 'text-white/30' : 'text-black/30'}`}>
                        {bodyShapeInsights.total_data_points} data points
                      </span>
                    </div>
                    <div className={`${panelClass} overflow-hidden`}>
                      <div className="overflow-x-auto">
                        <table className="w-full">
                          <thead><tr className={`border-b ${borderCl}`}>
                            <th className={tableHeaderClass}>Product</th>
                            <th className={tableHeaderClass}>Body Group</th>
                            <th className={tableHeaderClass}>Recommended</th>
                            <th className={tableHeaderClass}>Purchased</th>
                            <th className={tableHeaderClass}>Deviation</th>
                            <th className={`${tableHeaderClass} text-right`}>Shoppers</th>
                          </tr></thead>
                          <tbody>
                            {bodyShapeInsights.insights.slice(0, 15).map((p, i) => (
                              <tr key={`${p.product_id}-${p.measurement_group}-${i}`} className={`border-b ${borderCl} last:border-0 ${rowHover} transition-colors ${i % 2 ? (dark ? 'bg-white/[0.02]' : 'bg-black/[0.02]') : ''}`}>
                                <td className={`${tableCellClass} font-medium`}>{p.product_id}</td>
                                <td className={tableCellClass}>{p.measurement_group}</td>
                                <td className={tableCellClass}>{p.recommended_size}</td>
                                <td className={tableCellClass}>{p.actual_purchased_size}</td>
                                <td className={tableCellClass}><span className={`px-1.5 py-0.5 rounded text-[10px] ${badgeCl}`}>{p.deviation}</span></td>
                                <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{p.shopper_count}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <EmptyState message="No fit data" sub="Use widget + complete purchases" dark={dark} />
            )}
          </div>
        )}

        {/* ═══ TAB: Size Finder ═══ */}
        {tab === 'sizefinder' && (() => {
          if (metricsLoading && !sizeFinder) return <div className="space-y-6"><LoadingSpinner dark={dark} /></div>;
          if (!sizeFinder || sizeFinder.sessions === 0) {
            return (
              <div className="space-y-6">
                {!fetchError && <EmptyState message="No size finder data yet" sub="Sessions appear here once shoppers open Find my size or Try On on your product pages" dark={dark} />}
              </div>
            );
          }
          const sf = sizeFinder;
          const step = (k: string) => sf.funnel.find((f) => f.step === k)?.sessions ?? 0;
          const ratio = (num: number, den: number) => (den > 0 ? num / den : null);
          const pair = (r: Record<string, number>) => `${r.estimate ?? 0} / ${r.measured ?? 0}`;
          const conf = (v: number | null | undefined) => (v != null ? `${v.toFixed(0)}` : '-');
          const fmtDrop = (prev: number, cur: number) => (prev <= 0 ? '-' : cur >= prev ? '0%' : `−${(((prev - cur) / prev) * 100).toFixed(0)}%`);
          const quizBase = step('quiz_started') || sf.step_dropoff[0]?.sessions || 0;
          const ctaTotal = Object.values(sf.cta_split).reduce((a, b) => a + b, 0);
          const autoAlt = sf.alt_picks.auto_sold_out ?? { picks: 0, add_to_cart: 0 };
          const recDist = Object.entries(sf.recommended_distribution);
          const subCl = dark ? 'text-white/40' : 'text-black/40';
          return (
            <div className="space-y-6">
              <div className={`${panelClass} p-5`}>
                <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] mb-1 ${labelCl}`}>Size finder funnel</p>
                <p className={`text-xs mb-4 ${subCl}`}>
                  Size card sessions only, from Find my size and the Try On onboarding. Each session counts once per step; a purchase is an order paid within {sf.attribution_window_days} days of the session.
                </p>
                <div style={{ height: 260 }}>
                  <SizeFinderFunnelChart
                    steps={sf.funnel.map((f) => ({ name: SIZE_FINDER_STEP_LABELS[f.step] ?? f.step, value: f.sessions }))}
                    dark={dark}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                <MetricCell label="Opens" value={step('opened')} dark={dark} />
                <MetricCell label="Quiz completion" value={fmtPct(ratio(step('quiz_completed'), step('quiz_started')))} highlight dark={dark} />
                <MetricCell label="Estimates" value={step('estimate_shown')} dark={dark} />
                <MetricCell label="Passport CTA" value={fmtPct(ratio(step('passport_clicked'), step('estimate_shown')))} highlight dark={dark} />
                <MetricCell label="Sold-out alts" value={autoAlt.picks} dark={dark} />
                <MetricCell label="ATC est / meas" value={pair(sf.atc_by_basis)} dark={dark} />
                <MetricCell label="Purch est / meas" value={pair(sf.purchases_by_basis)} dark={dark} />
                <MetricCell label="Revenue" value={fmtEur(sf.revenue)} dark={dark} />
                <MetricCell label="Conf est / meas" value={`${conf(sf.avg_confidence.estimate)} / ${conf(sf.avg_confidence.measured)}`} dark={dark} />
                <MetricCell label="Size card / Try On" value={`${sf.source_split.size_finder ?? 0} / ${sf.source_split.tryon_onboarding ?? 0}`} dark={dark} />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:items-start">
                <div className={`${panelClass} overflow-hidden`}>
                  <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] px-4 pt-4 pb-2 ${labelCl}`}>Quiz step drop-off</p>
                  {sf.step_dropoff.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead><tr className={`border-b ${borderCl}`}>
                          <th className={tableHeaderClass}>Step</th>
                          <th className={`${tableHeaderClass} text-right whitespace-nowrap`}>Sessions</th>
                          <th className={`${tableHeaderClass} text-right whitespace-nowrap`}>Of starts</th>
                          <th className={`${tableHeaderClass} text-right whitespace-nowrap`}>Drop</th>
                        </tr></thead>
                        <tbody>
                          {sf.step_dropoff.map((q, i) => {
                            const prev = i === 0 ? quizBase : sf.step_dropoff[i - 1].sessions;
                            return (
                              <tr key={q.step} className={`border-b ${borderCl} last:border-0 ${rowHover} transition-colors ${i % 2 ? (dark ? 'bg-white/[0.02]' : 'bg-black/[0.02]') : ''}`}>
                                <td className={`${tableCellClass} font-medium`}>{QUIZ_STEP_LABELS[q.step] ?? q.step}</td>
                                <td className={`${tableCellClass} text-right font-mono tabular-nums whitespace-nowrap`}>{q.sessions}</td>
                                <td className={`${tableCellClass} text-right font-mono tabular-nums whitespace-nowrap`}>{fmtPct(ratio(q.sessions, quizBase))}</td>
                                <td className={`${tableCellClass} text-right font-mono tabular-nums whitespace-nowrap`}>{fmtDrop(prev, q.sessions)}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className={`px-4 pb-4 text-xs ${subCl}`}>No quiz steps recorded in this range.</p>
                  )}
                </div>

                <div className={`${panelClass} p-5`} style={chartPanelMinH}>
                  <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] mb-1 ${labelCl}`}>Mean score by size</p>
                  <p className={`text-xs mb-4 ${subCl}`}>Average 0–100 fit score each size got across the estimates shown.</p>
                  {sf.mean_score_by_size.length > 0 ? (
                    <div style={{ height: CHART_HEIGHT }}><SizeScoreChart scores={sf.mean_score_by_size} dark={dark} /></div>
                  ) : (
                    <p className={`text-xs ${subCl}`}>No estimates with scores in this range.</p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className={`${panelClass} overflow-hidden`}>
                  <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] px-4 pt-4 pb-2 ${labelCl}`}>Passport CTA split</p>
                  <table className="w-full">
                    <tbody>
                      {Object.entries(sf.cta_split).map(([cta, n]) => (
                        <tr key={cta} className={`border-b ${borderCl} last:border-0 ${rowHover} transition-colors`}>
                          <td className={`${tableCellClass} font-medium`}>{CTA_LABELS[cta] ?? cta}</td>
                          <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{n}</td>
                          <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{fmtPct(ratio(n, ctaTotal))}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className={`${panelClass} overflow-hidden`}>
                  <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] px-4 pt-4 pb-2 ${labelCl}`}>Alternative size picks</p>
                  <table className="w-full">
                    <thead><tr className={`border-b ${borderCl}`}>
                      <th className={tableHeaderClass}>Reason</th>
                      <th className={`${tableHeaderClass} text-right`}>Picks</th>
                      <th className={`${tableHeaderClass} text-right`}>Then ATC</th>
                    </tr></thead>
                    <tbody>
                      {Object.entries(sf.alt_picks).map(([reason, a]) => (
                        <tr key={reason} className={`border-b ${borderCl} last:border-0 ${rowHover} transition-colors`}>
                          <td className={`${tableCellClass} font-medium`}>{ALT_REASON_LABELS[reason] ?? reason}</td>
                          <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{a.picks}</td>
                          <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{a.add_to_cart}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {recDist.length > 0 ? (
                  <SizeCell label="Recommended sizes" data={sf.recommended_distribution} dark={dark} />
                ) : (
                  <div className={`${panelClass} p-5`}><p className={`text-xs ${subCl}`}>No recommendations in this range.</p></div>
                )}
              </div>

              <p className={`text-[11px] ${labelCl}`}>
                Revenue est / meas: {fmtEur(sf.revenue_by_basis.estimate ?? 0)} / {fmtEur(sf.revenue_by_basis.measured ?? 0)}. Estimate = the 7-question quiz; measured = the fit passport.
              </p>
            </div>
          );
        })()}

        {/* ═══ TAB 3: Trend & Demand (UNCHANGED) ═══ */}
        {tab === 'trend' && (() => {
          const hasRegional = !!(regionalSize && typeof regionalSize.by_country === 'object' && regionalSize.by_country !== null && Object.keys(regionalSize.by_country as Record<string, unknown>).length > 0);
          const hasCountryTags = !!(hasRegional && regionalSize && regionalSize.top_size_by_country && typeof regionalSize.top_size_by_country === 'object' && Object.keys(regionalSize.top_size_by_country as Record<string, unknown>).length > 0);
          return (
          <div className="relative" style={{ minHeight: 'calc(100vh - 150px)' }}>

            {/* ── Floating globe - right side, viewport-sticky, desktop only ── */}
            <div className="hidden lg:block fixed right-0 bottom-0 z-0 overflow-visible" style={{ width: '58vw', top: '36px' }}>
              <div className={`absolute top-2 right-3 z-20 flex rounded-lg overflow-hidden border backdrop-blur-md ${dark ? 'border-white/10 bg-black/30' : 'border-black/10 bg-white/50'}`}>
                <button
                  onClick={() => setRegionalView('globe')}
                  className={`px-2.5 py-1.5 text-[10px] transition-colors ${regionalView === 'globe' ? (dark ? 'bg-white/15 text-white' : 'bg-black text-white') : (dark ? 'text-white/40 hover:text-white/60' : 'text-gray-400 hover:text-gray-600')}`}
                >
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}><circle cx="12" cy="12" r="10" /><path d="M2 12h20" /><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" /></svg>
                </button>
                <button
                  onClick={() => setRegionalView('chart')}
                  className={`px-2.5 py-1.5 text-[10px] transition-colors ${regionalView === 'chart' ? (dark ? 'bg-white/15 text-white' : 'bg-black text-white') : (dark ? 'text-white/40 hover:text-white/60' : 'text-gray-400 hover:text-gray-600')}`}
                >
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}><rect x="3" y="3" width="7" height="18" rx="1" /><rect x="14" y="9" width="7" height="12" rx="1" /></svg>
                </button>
              </div>
              <div className="w-full h-full">
                {hasRegional ? (
                  regionalView === 'globe' ? (
                    <RegionalSizeGlobe
                      by_country={(regionalSize.by_country ?? {}) as Record<string, Record<string, number>>}
                      raw_counts={(regionalSize as Record<string, unknown>).raw_counts as Record<string, Record<string, number>> | undefined}
                      top_size_by_country={(regionalSize.top_size_by_country ?? {}) as Record<string, string>}
                      by_city={(regionalSize as Record<string, unknown>).by_city as Record<string, Record<string, { sizes: Record<string, number>; raw_counts: Record<string, number>; total: number; top_size: string }>> | undefined}
                      dark={dark}
                    />
                  ) : (
                    <div className="p-8 h-full flex items-center"><div className="w-full" style={{ height: 400 }}><RegionalSizeChart by_country={(regionalSize.by_country ?? {}) as Record<string, Record<string, number>>} dark={dark} /></div></div>
                  )
                ) : null}
              </div>
              {hasCountryTags && (
                <div className="absolute bottom-3 right-4 z-10" style={{ left: '40%' }}>
                  <div className={`flex flex-wrap justify-end gap-1.5 ${dark ? 'text-white/50' : 'text-black/50'}`}>
                    {Object.entries(regionalSize!.top_size_by_country as Record<string, string>)
                      .sort(([a], [b]) => a.localeCompare(b))
                      .map(([country, size]) => (
                        <span key={country} className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-medium backdrop-blur-sm ${dark ? 'bg-black/40' : 'bg-white/60'}`}>
                          {country}: <strong className="ml-0.5">{String(size)}</strong>
                        </span>
                      ))}
                  </div>
                </div>
              )}
            </div>

            {/* ── Analytics cards - left side, scrollable ── */}
            <div className="relative z-10 lg:max-w-[44%] space-y-6">
              {/* Mobile only: Regional size (globe + chart) at top so it's visible when scrolling; desktop keeps globe in fixed right panel */}
              <div className="lg:hidden">
                {hasRegional ? (
                  <div className="space-y-3">
                    <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] ${dark ? 'text-white/45' : 'text-black/45'}`}>Regional size</p>
                    <div className={`rounded-lg overflow-hidden border ${dark ? 'border-white/10 bg-black/20' : 'border-black/10 bg-white/50'}`}>
                      <div className="flex border-b border-inherit">
                        <button
                          type="button"
                          onClick={() => setRegionalView('globe')}
                          className={`flex-1 px-3 py-2 text-[10px] font-medium transition-colors flex items-center justify-center gap-1.5 ${regionalView === 'globe' ? (dark ? 'bg-white/15 text-white' : 'bg-black text-white') : (dark ? 'text-white/40 hover:text-white/60' : 'text-gray-400 hover:text-gray-600')}`}
                        >
                          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}><circle cx="12" cy="12" r="10" /><path d="M2 12h20" /><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" /></svg>
                          Globe
                        </button>
                        <button
                          type="button"
                          onClick={() => setRegionalView('chart')}
                          className={`flex-1 px-3 py-2 text-[10px] font-medium transition-colors flex items-center justify-center gap-1.5 ${regionalView === 'chart' ? (dark ? 'bg-white/15 text-white' : 'bg-black text-white') : (dark ? 'text-white/40 hover:text-white/60' : 'text-gray-400 hover:text-gray-600')}`}
                        >
                          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}><rect x="3" y="3" width="7" height="18" rx="1" /><rect x="14" y="9" width="7" height="12" rx="1" /></svg>
                          Chart
                        </button>
                      </div>
                      {regionalView === 'globe' ? (
                        <div className="relative w-full h-[380px]">
                          <div className="absolute inset-0">
                            <RegionalSizeGlobe
                              by_country={(regionalSize!.by_country ?? {}) as Record<string, Record<string, number>>}
                              raw_counts={(regionalSize as Record<string, unknown>).raw_counts as Record<string, Record<string, number>> | undefined}
                              top_size_by_country={(regionalSize!.top_size_by_country ?? {}) as Record<string, string>}
                              by_city={(regionalSize as Record<string, unknown>).by_city as Record<string, Record<string, { sizes: Record<string, number>; raw_counts: Record<string, number>; total: number; top_size: string }>> | undefined}
                              dark={dark}
                            />
                          </div>
                          {hasCountryTags && (
                            <div className={`absolute bottom-0 left-0 right-0 px-3 pb-3 pt-6 flex flex-wrap gap-1.5 ${dark ? 'text-white/50 bg-gradient-to-t from-black/70 to-transparent' : 'text-black/50 bg-gradient-to-t from-white/80 to-transparent'}`}>
                              {Object.entries(regionalSize!.top_size_by_country as Record<string, string>)
                                .sort(([a], [b]) => a.localeCompare(b))
                                .map(([country, size]) => (
                                  <span key={country} className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-medium ${dark ? 'bg-black/40' : 'bg-white/60'}`}>
                                    {country}: <strong className="ml-0.5">{String(size)}</strong>
                                  </span>
                                ))}
                            </div>
                          )}
                        </div>
                      ) : (
                        <>
                          <div className="p-2" style={{ height: 220 }}>
                            <RegionalSizeChart by_country={(regionalSize!.by_country ?? {}) as Record<string, Record<string, number>>} dark={dark} />
                          </div>
                          {hasCountryTags && (
                            <div className={`px-3 pb-3 flex flex-wrap gap-1.5 ${dark ? 'text-white/50' : 'text-black/50'}`}>
                              {Object.entries(regionalSize!.top_size_by_country as Record<string, string>)
                                .sort(([a], [b]) => a.localeCompare(b))
                                .map(([country, size]) => (
                                  <span key={country} className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-medium ${dark ? 'bg-black/40' : 'bg-white/60'}`}>
                                    {country}: <strong className="ml-0.5">{String(size)}</strong>
                                  </span>
                                ))}
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className={panelClass} style={chartPanelMinH}><EmptyState message="No regional data" sub="Country may be missing from events" dark={dark} /></div>
                )}
              </div>

              {metricsLoading && !velocity ? (
                <div className="py-24 flex justify-center"><div className={`w-8 h-8 border-2 rounded-full animate-spin ${dark ? 'border-white/20 border-t-white' : 'border-black/20 border-t-black'}`} /></div>
              ) : (
                <>
                  <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
                    <MetricCell label="Tryon 7d" value={String(velocity?.tryon_velocity_7d ?? '-')} dark={dark} />
                    <MetricCell label="Tryon 30d" value={String(velocity?.tryon_velocity_30d ?? '-')} dark={dark} />
                    <MetricCell label="Purch 7d" value={String(velocity?.purchase_velocity_7d ?? '-')} dark={dark} />
                    <MetricCell label="Purch 30d" value={String(velocity?.purchase_velocity_30d ?? '-')} dark={dark} />
                    <MetricCell label="Ratio 7d" value={velocity?.velocity_ratio_7d != null ? Number(velocity.velocity_ratio_7d).toFixed(2) : '-'} dark={dark} />
                    <MetricCell label="Ratio 30d" value={velocity?.velocity_ratio_30d != null ? Number(velocity.velocity_ratio_30d).toFixed(2) : '-'} dark={dark} />
                  </div>
                  {velocity && <div className={`${panelClass} p-5`} style={chartPanelMinH}><div style={{ height: CHART_HEIGHT }}><VelocityChart velocity={{ tryon_velocity_7d: Number(velocity.tryon_velocity_7d), tryon_velocity_30d: Number(velocity.tryon_velocity_30d), purchase_velocity_7d: Number(velocity.purchase_velocity_7d), purchase_velocity_30d: Number(velocity.purchase_velocity_30d) }} dark={dark} /></div></div>}
                  <div>
                    <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] mb-3 ${dark ? 'text-white/45' : 'text-black/45'}`}>At-risk SKUs</p>
                    {atRisk && Array.isArray(atRisk.products) && (atRisk.products as Array<{ product_id: string; tryons: number; purchases: number; conversion?: number | null; severity: string }>).length > 0 ? (
                      <div className={`${panelClass} overflow-hidden`}>
                        <table className="w-full">
                          <thead><tr className={`border-b ${borderCl}`}><th className={tableHeaderClass}>Product</th><th className={`${tableHeaderClass} text-right`}>Tryons</th><th className={`${tableHeaderClass} text-right`}>Purch</th><th className={`${tableHeaderClass} text-right`}>Conv</th><th className={tableHeaderClass}>Severity</th></tr></thead>
                          <tbody>{(atRisk.products as Array<{ product_id: string; tryons: number; purchases: number; conversion?: number | null; severity: string }>).slice(0, 8).map((p, i) => (
                            <tr key={p.product_id} className={`border-b ${borderCl} last:border-0 ${rowHover} ${i % 2 ? (dark ? 'bg-white/[0.02]' : 'bg-black/[0.02]') : ''}`}>
                              <td className={`${tableCellClass} font-medium`}>{p.product_id}</td>
                              <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{p.tryons}</td>
                              <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{p.purchases}</td>
                              <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{p.conversion != null ? `${(Number(p.conversion) * 100).toFixed(1)}%` : '0%'}</td>
                              <td className={tableCellClass}><span className={`px-2 py-0.5 rounded text-[10px] font-medium ${p.severity === 'critical' ? 'bg-white/20 text-white' : p.severity === 'warning' ? 'bg-white/15 text-white/90' : 'bg-white/10 text-white/60'}`}>{p.severity}</span></td>
                            </tr>
                          ))}</tbody>
                        </table>
                      </div>
                    ) : <div className={panelClass} style={chartPanelMinH}><EmptyState message="No at-risk products" sub="All SKUs meet conversion threshold" dark={dark} /></div>}
                  </div>
                  <div>
                    <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] mb-3 ${dark ? 'text-white/45' : 'text-black/45'}`}>Rising size exploration</p>
                    {explorationTrend.length > 0 ? (
                      <>
                        <div className={`${panelClass} p-5 mb-4`} style={chartPanelMinH}><div style={{ height: CHART_HEIGHT }}><ExplorationTrendChart data={explorationTrend as Array<{ week_start: string; avg_sizes_per_session: number }>} dark={dark} /></div></div>
                        <div className={`${panelClass} overflow-hidden`}>
                          <table className="w-full">
                            <thead><tr className={`border-b ${borderCl}`}><th className={tableHeaderClass}>Week</th><th className={`${tableHeaderClass} text-right`}>Sessions</th><th className={`${tableHeaderClass} text-right`}>Avg sizes</th></tr></thead>
                            <tbody>{(explorationTrend as Array<{ week_start: string; sessions_count: number; avg_sizes_per_session: number }>).slice(-8).map((p, i) => (
                              <tr key={p.week_start} className={`border-b ${borderCl} last:border-0 ${rowHover} ${i % 2 ? (dark ? 'bg-white/[0.02]' : 'bg-black/[0.02]') : ''}`}>
                                <td className={tableCellClass}>{p.week_start}</td>
                                <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{p.sessions_count}</td>
                                <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{Number(p.avg_sizes_per_session).toFixed(1)}</td>
                              </tr>
                            ))}</tbody>
                          </table>
                        </div>
                      </>
                    ) : <div className={panelClass} style={chartPanelMinH}><EmptyState message="No exploration data" dark={dark} /></div>}
                  </div>
                  <div>
                    <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] mb-3 ${dark ? 'text-white/45' : 'text-black/45'}`}>Size stress</p>
                    {sizeStress.length > 0 ? (
                      <div className={`${panelClass} overflow-hidden`}>
                        <table className="w-full">
                          <thead><tr className={`border-b ${borderCl}`}><th className={tableHeaderClass}>Product</th><th className={tableHeaderClass}>Size</th><th className={`${tableHeaderClass} text-right`}>Views</th><th className={`${tableHeaderClass} text-right`}>Purch</th><th className={`${tableHeaderClass} text-right`}>Stress</th></tr></thead>
                          <tbody>{(sizeStress as Array<{ product_id: string; size: string; views: number; purchases: number; stress_score: number }>).slice(0, 8).map((s, i) => (
                            <tr key={`${s.product_id}-${s.size}-${i}`} className={`border-b ${borderCl} last:border-0 ${rowHover} ${i % 2 ? (dark ? 'bg-white/[0.02]' : 'bg-black/[0.02]') : ''}`}>
                              <td className={`${tableCellClass} font-medium`}>{s.product_id}</td>
                              <td className={tableCellClass}>{s.size}</td>
                              <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{s.views}</td>
                              <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{s.purchases}</td>
                              <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{Number(s.stress_score).toFixed(1)}×</td>
                            </tr>
                          ))}</tbody>
                        </table>
                      </div>
                    ) : <EmptyState message="No size stress" sub="All sizes show healthy conversion" dark={dark} />}
                  </div>
                </>
              )}
            </div>
          </div>
          );
        })()}

        {/* ═══ TAB 4: Returns & Risk ═══ */}
        {tab === 'returns' && (
          <div className="space-y-6">
            {metricsLoading && !returnMetrics ? (
              <LoadingSpinner dark={dark} />
            ) : returnMetrics ? (
              <>
                {/* Key metrics: store-wide, every order paid in the range */}
                <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] ${labelCl}`}>All store orders</p>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                  <MetricCell label="Orders" value={returnMetrics.total_purchases ?? 0} dark={dark} />
                  <MetricCell label="Returned Orders" value={returnMetrics.total_returns ?? 0} dark={dark} />
                  <MetricCell label="Return Rate" value={fmtPct(returnMetrics.return_rate)} highlight dark={dark} />
                  <MetricCell label="Revenue Lost" value={fmtEur(returnMetrics.revenue_lost)} dark={dark} />
                  <MetricCell label="Avg Days to Return" value={returnMetrics.avg_days_to_return != null ? `${Number(returnMetrics.avg_days_to_return).toFixed(1)}d` : '-'} dark={dark} />
                </div>

                {/* Tryon Cohort vs Baseline */}
                {cohortComparison && (
                  <div className={`${panelClass} p-5`}>
                    <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] mb-4 ${labelCl}`}>Tryon cohort vs baseline</p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-3">
                        <p className={`text-xs font-semibold ${dark ? 'text-white/70' : 'text-black/70'}`}>Try-on orders</p>
                        <div className="grid grid-cols-2 gap-3">
                          <MetricCell label="Try-on sessions" value={cohortComparison.tryon_sessions ?? '-'} dark={dark} />
                          <MetricCell label="Orders" value={cohortComparison.tryon_purchases ?? '-'} dark={dark} />
                          <MetricCell label="AOV" value={fmtEur(cohortComparison.tryon_aov)} dark={dark} />
                          <MetricCell label="Conv Rate" value={fmtPct(cohortComparison.tryon_conversion_rate)} highlight dark={dark} />
                          <MetricCell label="Bracket Rate" value={fmtPct(cohortComparison.tryon_bracket_rate)} dark={dark} />
                          <MetricCell label="Return Rate" value={fmtPct(cohortComparison.tryon_return_rate)} dark={dark} />
                        </div>
                      </div>
                      <div className="space-y-3">
                        <p className={`text-xs font-semibold ${dark ? 'text-white/70' : 'text-black/70'}`}>Store orders without try-on</p>
                        <div className="grid grid-cols-2 gap-3">
                          <MetricCell label="Orders" value={cohortComparison.baseline_orders ?? '-'} dark={dark} />
                          <MetricCell label="Returned" value={cohortComparison.baseline_returns ?? '-'} dark={dark} />
                          <MetricCell label="AOV" value={fmtEur(cohortComparison.baseline_aov)} dark={dark} />
                          <MetricCell label="Conv Rate" value="-" dark={dark} />
                          <MetricCell label="Bracket Rate" value={fmtPct(cohortComparison.baseline_bracket_rate)} dark={dark} />
                          <MetricCell label="Return Rate" value={fmtPct(cohortComparison.baseline_return_rate)} dark={dark} />
                        </div>
                      </div>
                    </div>
                    <p className={`text-xs leading-relaxed mt-4 ${dark ? 'text-white/40' : 'text-black/40'}`}>
                      An order counts for a try-on when it is paid within {cohortComparison.attribution_window_days ?? 30} days of it. The store side has no conversion rate because store visits are not tracked.
                      {cohortComparison.comparable === false && ` With fewer than ${cohortComparison.min_orders_for_comparison ?? 20} orders on a side, the two columns are not yet a fair comparison.`}
                      {' '}<Link href="/brand/cohorts" className="underline">Open the cohort view</Link>
                    </p>
                  </div>
                )}

                {/* Top Returned SKUs */}
                {returnMetrics.top_returned_products && Array.isArray(returnMetrics.top_returned_products) && returnMetrics.top_returned_products.length > 0 && (
                  <div>
                    <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] mb-3 ${labelCl}`}>Top returned SKUs</p>
                    <div className={`${panelClass} overflow-hidden`}>
                      <div className="overflow-x-auto">
                        <table className="w-full">
                          <thead><tr className={`border-b ${borderCl}`}>
                            <th className={tableHeaderClass}>SKU</th>
                            <th className={`${tableHeaderClass} text-right`}>Returns</th>
                            <th className={`${tableHeaderClass} text-right`}>Purchases</th>
                            <th className={`${tableHeaderClass} text-right`}>Return Rate</th>
                          </tr></thead>
                          <tbody>
                            {returnMetrics.top_returned_products.slice(0, 10).map((p, i) => (
                              <tr key={(p.sku || p.variant_id || p.product_id || String(i))} className={`border-b ${borderCl} last:border-0 ${rowHover} transition-colors ${i % 2 ? (dark ? 'bg-white/[0.02]' : 'bg-black/[0.02]') : ''}`}>
                                <td className={`${tableCellClass} font-medium`}>
                                  <span className="font-mono">{p.sku || p.variant_id || p.product_id || '-'}</span>
                                  {p.title ? <span className={`ml-2 ${labelCl}`}>{p.title}</span> : null}
                                </td>
                                <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{p.return_count}</td>
                                <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{p.purchase_count}</td>
                                <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{fmtPct(p.return_rate)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}

                {/* Sales & returns by SKU (every SKU sold or returned) */}
                {returnMetrics.sku_breakdown && Array.isArray(returnMetrics.sku_breakdown) && returnMetrics.sku_breakdown.length > 0 && (
                  <div>
                    <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] mb-3 ${labelCl}`}>Sales &amp; returns by SKU</p>
                    <div className={`${panelClass} overflow-hidden`}>
                      <div className="overflow-x-auto">
                        <table className="w-full">
                          <thead><tr className={`border-b ${borderCl}`}>
                            <th className={tableHeaderClass}>SKU</th>
                            <th className={`${tableHeaderClass} text-right`}>Sold</th>
                            <th className={`${tableHeaderClass} text-right`}>Returned</th>
                            <th className={`${tableHeaderClass} text-right`}>Return Rate</th>
                          </tr></thead>
                          <tbody>
                            {returnMetrics.sku_breakdown.map((p, i) => (
                              <tr key={(p.sku || p.variant_id || p.product_id || String(i))} className={`border-b ${borderCl} last:border-0 ${rowHover} transition-colors ${i % 2 ? (dark ? 'bg-white/[0.02]' : 'bg-black/[0.02]') : ''}`}>
                                <td className={`${tableCellClass} font-medium`}>
                                  <span className="font-mono">{p.sku || p.variant_id || p.product_id || '-'}</span>
                                  {p.title ? <span className={`ml-2 ${labelCl}`}>{p.title}</span> : null}
                                </td>
                                <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{p.purchase_count}</td>
                                <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{p.return_count}</td>
                                <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{fmtPct(p.return_rate)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}

                {/* Return Risk Scoring */}
                {returnRisk && (
                  <div className="space-y-4">
                    <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] ${labelCl}`}>Return risk scoring</p>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <MetricCell label="Avg Risk Score" value={returnRisk.avg_risk_score != null ? Number(returnRisk.avg_risk_score).toFixed(1) : '-'} dark={dark} />
                      <MetricCell label="Total Scored" value={returnRisk.total_scored ?? '-'} dark={dark} />
                    </div>
                    {returnRisk.high_risk_orders && returnRisk.high_risk_orders.length > 0 && (
                      <>
                        <div className={`${panelClass} p-5`} style={chartPanelMinH}>
                          <div style={{ height: CHART_HEIGHT }}>
                            <ReturnRiskChart orders={(returnRisk.high_risk_orders ?? []) as Array<{ order_id: string; risk_score: number; risk_factors: string[] }>} dark={dark} />
                          </div>
                        </div>
                        <div className={`${panelClass} overflow-hidden`}>
                          <div className="overflow-x-auto">
                            <table className="w-full">
                              <thead><tr className={`border-b ${borderCl}`}>
                                <th className={tableHeaderClass}>Order</th>
                                <th className={`${tableHeaderClass} text-right`}>Risk Score</th>
                                <th className={tableHeaderClass}>Risk Factors</th>
                                <th className={tableHeaderClass}>Product</th>
                              </tr></thead>
                              <tbody>
                                {returnRisk.high_risk_orders.slice(0, 10).map((o, i) => (
                                  <tr key={o.order_id} className={`border-b ${borderCl} last:border-0 ${rowHover} transition-colors ${i % 2 ? (dark ? 'bg-white/[0.02]' : 'bg-black/[0.02]') : ''}`}>
                                    <td className={`${tableCellClass} font-medium font-mono`}>{o.order_id}</td>
                                    <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{o.risk_score.toFixed(2)}</td>
                                    <td className={tableCellClass}>
                                      <div className="flex flex-wrap gap-1">
                                        {(o.risk_factors ?? []).map((f, fi) => (
                                          <span key={fi} className={`px-1.5 py-0.5 rounded text-[10px] ${badgeCl}`}>{f}</span>
                                        ))}
                                      </div>
                                    </td>
                                    <td className={`${tableCellClass} font-medium`}>{o.product_id ?? '-'}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                )}
              </>
            ) : !fetchError && (
              <EmptyState message="No return data yet" sub="Return metrics will appear once orders are tracked" dark={dark} />
            )}
          </div>
        )}

        {/* ═══ TAB 5: Engagement ═══ */}
        {tab === 'engagement' && (
          <div className="space-y-6">
            {metricsLoading && !dwellMetrics && !deviceMetrics && !repeatVisitors ? (
              <LoadingSpinner dark={dark} />
            ) : (dwellMetrics || deviceMetrics || repeatVisitors) ? (
              <>
                {/* Dwell Time */}
                {dwellMetrics && (
                  <div className="space-y-4">
                    <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] ${labelCl}`}>Dwell time</p>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <MetricCell label="Avg Dwell" value={dwellMetrics.avg_dwell_seconds != null ? `${Number(dwellMetrics.avg_dwell_seconds).toFixed(1)}s` : '-'} dark={dark} />
                      <MetricCell label="Median Dwell" value={dwellMetrics.median_dwell_seconds != null ? `${Number(dwellMetrics.median_dwell_seconds).toFixed(1)}s` : '-'} dark={dark} />
                      <MetricCell label="P90 Dwell" value={dwellMetrics.p90_dwell_seconds != null ? `${Number(dwellMetrics.p90_dwell_seconds).toFixed(1)}s` : '-'} dark={dark} />
                      <MetricCell label="Dwell→Conv %" value={dwellMetrics.dwell_to_conversion != null ? `${Number(dwellMetrics.dwell_to_conversion).toFixed(1)}%` : '-'} highlight dark={dark} />
                    </div>
                    <div className={`${panelClass} p-5`} style={chartPanelMinH}>
                      <div style={{ height: CHART_HEIGHT }}>
                        <DwellTimeChart avg={dwellMetrics.avg_dwell_seconds ?? 0} median={dwellMetrics.median_dwell_seconds ?? 0} p90={dwellMetrics.p90_dwell_seconds ?? 0} dark={dark} />
                      </div>
                    </div>
                  </div>
                )}

                {/* Device Breakdown */}
                {deviceMetrics && (
                  <div className="space-y-4">
                    <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] ${labelCl}`}>Device breakdown</p>
                    <div className={`${panelClass} p-5`} style={chartPanelMinH}>
                      <div style={{ height: CHART_HEIGHT }}>
                        <DeviceBreakdownChart devices={(deviceMetrics.devices ?? []) as Array<{ device_type: string; tryons: number; purchases: number; conversion_rate?: number | null }>} dark={dark} />
                      </div>
                    </div>
                    {deviceMetrics.devices && deviceMetrics.devices.length > 0 && (
                      <div className={`${panelClass} overflow-hidden`}>
                        <div className="overflow-x-auto">
                          <table className="w-full">
                            <thead><tr className={`border-b ${borderCl}`}>
                              <th className={tableHeaderClass}>Device</th>
                              <th className={`${tableHeaderClass} text-right`}>Tryons</th>
                              <th className={`${tableHeaderClass} text-right`}>Add to Cart</th>
                              <th className={`${tableHeaderClass} text-right`}>Purchases</th>
                              <th className={`${tableHeaderClass} text-right`}>Conv Rate</th>
                            </tr></thead>
                            <tbody>
                              {deviceMetrics.devices.map((d, i) => (
                                <tr key={d.device_type} className={`border-b ${borderCl} last:border-0 ${rowHover} transition-colors ${i % 2 ? (dark ? 'bg-white/[0.02]' : 'bg-black/[0.02]') : ''}`}>
                                  <td className={`${tableCellClass} font-medium`}>{d.device_type}</td>
                                  <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{d.tryons ?? 0}</td>
                                  <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{d.add_to_carts ?? 0}</td>
                                  <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{d.purchases ?? 0}</td>
                                  <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{fmtPct(d.conversion_rate)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Repeat Visitors */}
                {repeatVisitors && (
                  <div className="space-y-4">
                    <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] ${labelCl}`}>Repeat visitors</p>
                    <div className="grid grid-cols-3 sm:grid-cols-5 gap-3">
                      <MetricCell label="Unique Users" value={repeatVisitors.metrics?.unique_users ?? '-'} dark={dark} />
                      <MetricCell label="Returning Users" value={repeatVisitors.metrics?.returning_users ?? '-'} dark={dark} />
                      <MetricCell label="Returning %" value={fmtPct(repeatVisitors.metrics?.returning_user_rate)} highlight dark={dark} />
                      <MetricCell label="High-Intent Users" value={repeatVisitors.metrics?.high_intent_users ?? '-'} dark={dark} />
                      <MetricCell label="High-Intent Conv %" value={fmtPct(repeatVisitors.metrics?.high_intent_conversion_rate)} highlight dark={dark} />
                    </div>
                    {repeatVisitors.top_repeated_products && repeatVisitors.top_repeated_products.length > 0 && (
                      <div className={`${panelClass} overflow-hidden`}>
                        <div className="overflow-x-auto">
                          <table className="w-full">
                            <thead><tr className={`border-b ${borderCl}`}>
                              <th className={tableHeaderClass}>Product</th>
                              <th className={`${tableHeaderClass} text-right`}>Repeat Count</th>
                              <th className={`${tableHeaderClass} text-right`}>Converted</th>
                            </tr></thead>
                            <tbody>
                              {repeatVisitors.top_repeated_products.slice(0, 10).map((p, i) => (
                                <tr key={p.product_id} className={`border-b ${borderCl} last:border-0 ${rowHover} transition-colors ${i % 2 ? (dark ? 'bg-white/[0.02]' : 'bg-black/[0.02]') : ''}`}>
                                  <td className={`${tableCellClass} font-medium`}>{p.product_id}</td>
                                  <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{p.repeat_count}</td>
                                  <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{p.converted ? 'Yes' : 'No'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </>
            ) : !fetchError && (
              <EmptyState message="No engagement data yet" sub="Engagement metrics will appear as users interact with the widget" dark={dark} />
            )}
          </div>
        )}
      </main>
    </div>
  );
}
