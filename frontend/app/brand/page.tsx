'use client';

import dynamic from 'next/dynamic';
import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useTheme } from '@/contexts/ThemeContext';
import { getCurrentUser, logout, type User } from '@/lib/supabase-auth';
import { api, getMyBrand, type AnalyticsMetrics, type FitMetrics, type VelocityMetrics, type AtRiskProductsResponse, type ExplorationTrendPoint, type SizeStressItem, type RegionalSizeData, type MetricsByProductResponse } from '@/lib/api';

const CHART_HEIGHT = 200;

const ConversionFunnelChart = dynamic(() => import('@/components/analytics/Charts').then((m) => ({ default: m.ConversionFunnelChart })), { ssr: false });
const VelocityChart = dynamic(() => import('@/components/analytics/Charts').then((m) => ({ default: m.VelocityChart })), { ssr: false });
const SizeDistributionChart = dynamic(() => import('@/components/analytics/Charts').then((m) => ({ default: m.SizeDistributionChart })), { ssr: false });
const ExplorationTrendChart = dynamic(() => import('@/components/analytics/Charts').then((m) => ({ default: m.ExplorationTrendChart })), { ssr: false });
const RegionalSizeChart = dynamic(() => import('@/components/analytics/Charts').then((m) => ({ default: m.RegionalSizeChart })), { ssr: false });
const RegionalSizeGlobe = dynamic(() => import('@/components/analytics/RegionalSizeGlobe'), { ssr: false });

const SIZE_ORDER = ['XS', 'S', 'M', 'L', 'XL', 'XXL'];

type Tab = 'roi' | 'fit' | 'trend';

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
        <p className={`${sumCl} text-xs`}>—</p>
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

export default function BrandDashboardPage() {
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();
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
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [metricsRange, setMetricsRange] = useState<'7d' | '30d'>('30d');
  const [metricsShop, setMetricsShop] = useState('');

  const fetchMetrics = useCallback(async () => {
    setMetricsLoading(true);
    setFetchError(null);
    const end = new Date();
    const days = metricsRange === '7d' ? 7 : 30;
    const start = new Date();
    start.setDate(start.getDate() - days);
    const params: { start: string; end: string; shop?: string } = {
      start: start.toISOString().slice(0, 10),
      end: end.toISOString().slice(0, 10),
    };
    if (metricsShop) params.shop = metricsShop;
    const calls = [
      () => api.getAnalyticsMetrics(params),
      () => api.getFitMetrics(params),
      () => api.getVelocityMetrics(params),
      () => api.getAtRiskProducts(params),
      () => api.getExplorationTrend(params),
      () => api.getSizeStress(params),
      () => api.getRegionalSize(params),
      () => api.getMetricsByProduct(params),
    ];
    const results = await Promise.allSettled(calls.map((fn) => fn()));
    const [m, fm, v, ar, et, ss, rs, mp] = results.map((r) =>
      r.status === 'fulfilled' ? r.value : null
    );
    const failures = results.filter((r) => r.status === 'rejected');
    if (failures.length > 0 && failures.length === results.length) {
      setFetchError('Backend unreachable.');
    }
    if (m) setMetrics(m);
    if (fm) setFitMetrics(fm);
    if (v) setVelocity(v);
    if (ar) setAtRisk(ar);
    if (et && typeof et === 'object' && 'data' in et) setExplorationTrend((et as { data?: ExplorationTrendPoint[] }).data || []);
    if (ss && typeof ss === 'object' && 'items' in ss) setSizeStress((ss as { items?: SizeStressItem[] }).items || []);
    if (rs) setRegionalSize(rs);
    if (mp) setMetricsByProduct(mp);
    setMetricsLoading(false);
  }, [metricsRange, metricsShop]);

  useEffect(() => { fetchMetrics(); }, [fetchMetrics]);

  const [brandShop, setBrandShop] = useState<string | null>(null);
  const [hasGarments, setHasGarments] = useState(true);

  useEffect(() => {
    getCurrentUser().then(async (u) => {
      if (!u) {
        router.push('/login');
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
          setBrandShop(brand.shopify_domain as string);
          setMetricsShop((prev) => prev || (brand.shopify_domain as string));
        }
        if (brand?.id) {
          const { garmentApi } = await import('@/lib/api');
          const garments = await garmentApi.list(brand.id as string);
          setHasGarments(garments.length > 0);
        }
      } catch {}
    }).catch(() => router.push('/login'));
  }, [router]);

  const handleLogout = async () => {
    await logout();
    router.push('/');
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
    { id: 'fit', label: 'Fit Accuracy' },
    { id: 'trend', label: 'Trend & Demand' },
  ];

  const panelClass = dark
    ? 'rounded-2xl bg-white/[0.03] backdrop-blur-sm transition-all duration-300'
    : 'rounded-2xl bg-black/[0.03] backdrop-blur-sm transition-all duration-300';
  const tableHeaderClass = dark ? 'text-left py-3 px-4 text-[10px] font-semibold uppercase tracking-[0.2em] text-white/45' : 'text-left py-3 px-4 text-[10px] font-semibold uppercase tracking-[0.2em] text-black/45';
  const tableCellClass = dark ? 'py-3 px-4 text-sm text-white/90' : 'py-3 px-4 text-sm text-black/90';
  const chartPanelMinH = { minHeight: CHART_HEIGHT };
  const borderCl = dark ? 'border-white/10' : 'border-black/10';
  const rowHover = dark ? 'hover:bg-white/5' : 'hover:bg-black/5';

  return (
    <div className={`min-h-screen transition-colors ${dark ? 'bg-black text-white' : 'bg-white text-black'}`}>
      <header className={`sticky top-0 z-20 backdrop-blur-xl border-b ${dark ? 'bg-black/95 border-white/10' : 'bg-white/95 border-black/10'}`}>
        <div className="max-w-7xl mx-auto px-4 py-1.5 flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2 shrink-0 opacity-90 hover:opacity-100 transition-opacity">
            <img src="/tryon-logo.jpg" alt="TRYON" className="h-5 w-auto rounded" />
          </Link>
          <nav className="flex gap-0.5 min-w-0">
            {tabs.map(({ id, label }) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={`px-2.5 py-1 text-xs font-medium transition-all whitespace-nowrap ${
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
              className={`px-2.5 py-1 text-xs font-medium transition-all whitespace-nowrap ${dark ? 'text-white/35 hover:text-white/60' : 'text-black/35 hover:text-black/60'}`}
            >
              Garments
            </Link>
          </nav>
          <div className="flex items-center gap-2 ml-auto shrink-0">
            <select
              value={metricsShop}
              onChange={(e) => setMetricsShop(e.target.value)}
              className={`text-[10px] px-2 py-1 rounded border focus:outline-none ${dark ? 'bg-white/5 border-white/10 text-white/70' : 'bg-black/5 border-black/10 text-black/70'}`}
            >
              <option value="">All shops</option>
              {brandShop && <option value={brandShop}>{brandShop}</option>}
            </select>
            <select
              value={metricsRange}
              onChange={(e) => setMetricsRange(e.target.value as '7d' | '30d')}
              className={`text-[10px] px-2 py-1 rounded border focus:outline-none ${dark ? 'bg-white/5 border-white/10 text-white/70' : 'bg-black/5 border-black/10 text-black/70'}`}
            >
              <option value="7d">7d</option>
              <option value="30d">30d</option>
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
            {user && <span className={`${dark ? 'text-white/40' : 'text-black/40'} text-[10px] hidden md:inline`}>{user.email}</span>}
            <button onClick={handleLogout} className={`${dark ? 'text-white/40 hover:text-white/70' : 'text-black/40 hover:text-black/70'} text-[10px] transition-colors`}>Sign out</button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-5 py-6 dashboard-fade-in">
        {/* Getting Started Guide */}
        {(!brandShop || !hasGarments) && (
          <div className={`mb-6 rounded-xl border p-5 ${dark ? 'bg-white/[0.03] border-white/10' : 'bg-gradient-to-r from-blue-50 to-purple-50 border-blue-100'}`}>
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

        {fetchError && (
          <div className={`mb-5 p-4 rounded-xl text-sm flex items-center justify-between ${dark ? 'bg-white/[0.03] text-white/70' : 'bg-black/[0.03] text-black/70'}`}>
            <span>{fetchError}</span>
            <button onClick={fetchMetrics} disabled={metricsLoading} className={`px-4 py-2 rounded-lg ${dark ? 'bg-white/10 hover:bg-white/20' : 'bg-black/10 hover:bg-black/20'}`}>Retry</button>
          </div>
        )}

        {tab === 'roi' && (
          <div className="space-y-6">
            {metricsLoading && !metrics ? (
              <div className="py-24 flex justify-center"><div className={`w-8 h-8 border-2 rounded-full animate-spin ${dark ? 'border-white/20 border-t-white' : 'border-black/20 border-t-black'}`} /></div>
            ) : metrics ? (
              <>
                <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-10 gap-3">
                  <MetricCell label="Tryons" value={metrics.tryons_started} dark={dark} />
                  <MetricCell label="ATC" value={metrics.add_to_carts} dark={dark} />
                  <MetricCell label="Purchases" value={metrics.purchases} dark={dark} />
                  <MetricCell label="Sessions" value={metrics.unique_sessions} dark={dark} />
                  <MetricCell label="ATC %" value={metrics.tryon_atc_rate != null ? `${(metrics.tryon_atc_rate * 100).toFixed(1)}%` : '—'} highlight dark={dark} />
                  <MetricCell label="Purchase %" value={metrics.tryon_purchase_rate != null ? `${(metrics.tryon_purchase_rate * 100).toFixed(1)}%` : '—'} highlight dark={dark} />
                  <MetricCell label="Revenue" value={`€${(metrics.revenue_attributed ?? 0).toFixed(2)}`} dark={dark} />
                  <MetricCell label="Rev/Tryon" value={metrics.revenue_per_tryon != null ? `€${metrics.revenue_per_tryon.toFixed(2)}` : '—'} dark={dark} />
                  <MetricCell label="AOV" value={metrics.aov_tryon != null ? `€${metrics.aov_tryon.toFixed(2)}` : '—'} dark={dark} />
                </div>
                <div className={`${panelClass} p-5`} style={chartPanelMinH}>
                  <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] mb-4 ${dark ? 'text-white/45' : 'text-black/45'}`}>Conversion funnel</p>
                  <div style={{ height: CHART_HEIGHT }}><ConversionFunnelChart tryons={metrics.tryons_started ?? 0} atc={metrics.add_to_carts ?? 0} purchases={metrics.purchases ?? 0} dark={dark} /></div>
                </div>
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
                               <td className={`${tableCellClass} text-right font-mono tabular-nums`}>{p.aov_tryon != null ? `€${p.aov_tryon.toFixed(2)}` : '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </>
            ) : !fetchError && (
              <EmptyState message="No metrics yet" sub="Use the TryOn widget, then refresh" dark={dark} />
            )}
          </div>
        )}

        {tab === 'fit' && (
          <div className="space-y-6">
            {metricsLoading && !fitMetrics ? (
              <div className="py-24 flex justify-center"><div className={`w-8 h-8 border-2 rounded-full animate-spin ${dark ? 'border-white/20 border-t-white' : 'border-black/20 border-t-black'}`} /></div>
            ) : fitMetrics ? (
              <>
                <div className="grid grid-cols-4 sm:grid-cols-6 gap-3">
                  <MetricCell label="Acceptance" value={fitMetrics.acceptance_rate != null ? `${(Number(fitMetrics.acceptance_rate) * 100).toFixed(1)}%` : '—'} highlight dark={dark} />
                  <MetricCell label="Size up" value={fitMetrics.size_up_rate != null ? `${(Number(fitMetrics.size_up_rate) * 100).toFixed(1)}%` : '—'} dark={dark} />
                  <MetricCell label="Size down" value={fitMetrics.size_down_rate != null ? `${(Number(fitMetrics.size_down_rate) * 100).toFixed(1)}%` : '—'} dark={dark} />
                  <MetricCell label="MASE" value={fitMetrics.mase != null ? Number(fitMetrics.mase).toFixed(2) : '—'} dark={dark} />
                  <MetricCell label="Sess w/ rec" value={String(fitMetrics.sessions_with_recommendation ?? '—')} dark={dark} />
                  <MetricCell label="Purch+size" value={String(fitMetrics.sessions_with_purchase_and_size ?? '—')} dark={dark} />
                </div>
                <div className={`${panelClass} p-5`} style={chartPanelMinH}>
                  <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] mb-2 ${dark ? 'text-white/45' : 'text-black/45'}`}>Size distribution</p>
                  <p className={`text-xs mb-4 ${dark ? 'text-white/40' : 'text-black/40'}`}>Recommended = what we suggested · Selected = what they chose · Purchased = what they bought</p>
                  <div style={{ height: CHART_HEIGHT }}><SizeDistributionChart recommended={(fitMetrics.size_distribution_recommended ?? {}) as Record<string, number>} selected={(fitMetrics.size_distribution_selected ?? {}) as Record<string, number>} purchased={(fitMetrics.size_distribution_purchased ?? {}) as Record<string, number>} dark={dark} /></div>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <SizeCell label="Recommended" data={(fitMetrics.size_distribution_recommended ?? {}) as Record<string, number>} dark={dark} />
                  <SizeCell label="Selected" data={(fitMetrics.size_distribution_selected ?? {}) as Record<string, number>} dark={dark} />
                  <SizeCell label="Purchased" data={(fitMetrics.size_distribution_purchased ?? {}) as Record<string, number>} dark={dark} />
                </div>
              </>
            ) : (
              <EmptyState message="No fit data" sub="Use widget + complete purchases" dark={dark} />
            )}
          </div>
        )}

        {tab === 'trend' && (() => {
          const hasRegional = !!(regionalSize && typeof regionalSize.by_country === 'object' && regionalSize.by_country !== null && Object.keys(regionalSize.by_country as Record<string, unknown>).length > 0);
          const hasCountryTags = !!(hasRegional && regionalSize && regionalSize.top_size_by_country && typeof regionalSize.top_size_by_country === 'object' && Object.keys(regionalSize.top_size_by_country as Record<string, unknown>).length > 0);
          return (
          <div className="relative" style={{ minHeight: 'calc(100vh - 150px)' }}>

            {/* ── Floating globe — right side, viewport-sticky, desktop only ── */}
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

            {/* ── Analytics cards — left side, scrollable ── */}
            <div className="relative z-10 lg:max-w-[44%] space-y-6">
              {metricsLoading && !velocity ? (
                <div className="py-24 flex justify-center"><div className={`w-8 h-8 border-2 rounded-full animate-spin ${dark ? 'border-white/20 border-t-white' : 'border-black/20 border-t-black'}`} /></div>
              ) : (
                <>
                  <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
                    <MetricCell label="Tryon 7d" value={String(velocity?.tryon_velocity_7d ?? '—')} dark={dark} />
                    <MetricCell label="Tryon 30d" value={String(velocity?.tryon_velocity_30d ?? '—')} dark={dark} />
                    <MetricCell label="Purch 7d" value={String(velocity?.purchase_velocity_7d ?? '—')} dark={dark} />
                    <MetricCell label="Purch 30d" value={String(velocity?.purchase_velocity_30d ?? '—')} dark={dark} />
                    <MetricCell label="Ratio 7d" value={velocity?.velocity_ratio_7d != null ? Number(velocity.velocity_ratio_7d).toFixed(2) : '—'} dark={dark} />
                    <MetricCell label="Ratio 30d" value={velocity?.velocity_ratio_30d != null ? Number(velocity.velocity_ratio_30d).toFixed(2) : '—'} dark={dark} />
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

                  {/* Mobile: regional chart inline (globe hidden on small screens) */}
                  <div className="lg:hidden">
                    {hasRegional ? (
                      <div>
                        <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] mb-3 ${dark ? 'text-white/45' : 'text-black/45'}`}>Regional size</p>
                        <div className={`${panelClass} p-5`} style={chartPanelMinH}><div style={{ height: CHART_HEIGHT }}><RegionalSizeChart by_country={(regionalSize!.by_country ?? {}) as Record<string, Record<string, number>>} dark={dark} /></div></div>
                      </div>
                    ) : <EmptyState message="No regional data" sub="Country may be missing from events" dark={dark} />}
                  </div>
                </>
              )}
            </div>
          </div>
          );
        })()}
      </main>
    </div>
  );
}
