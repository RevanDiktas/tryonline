'use client';

/**
 * Category size charts: one chart per category (or per Shopify product type).
 *
 * Every product that has no 3D garment of its own gets its size advice from here:
 * the size finder matches the Shopify product type first ("T-shirt", "Hoodie"), then
 * the category (tops / bottoms / outerwear / dresses / accessories). A 3D garment keeps
 * its own chart on the Garments page.
 */
import { useEffect, useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getCurrentUser, type User } from '@/lib/supabase-auth';
import { sizeChartApi, type BrandSizeChart } from '@/lib/api';
import { SIZE_SYSTEMS, inferSizeSystem, type SizeSystem } from '@/lib/sizeRecommendation';
import { useTheme } from '@/contexts/ThemeContext';
import { MEASUREMENTS, parseChartFile, pastedTextToRows, rowsToChart } from '@/lib/sizeChartImport';

const CATEGORIES = ['tops', 'bottoms', 'outerwear', 'dresses', 'accessories'];
const FIT_TYPES = ['slim', 'regular', 'oversized'];
const CATEGORY_HINT: Record<string, string> = {
  tops: 'T-shirts, hoodies, sweaters, shirts',
  bottoms: 'Jeans, trousers, shorts, skirts',
  outerwear: 'Jackets, coats, vests',
  dresses: 'Dresses, jumpsuits',
  accessories: 'Hats, belts, bags',
};

type Grid = Record<string, Record<string, string>>;

function emptyGrid(sys: SizeSystem): Grid {
  const g: Grid = {};
  for (const sz of SIZE_SYSTEMS[sys].sizes) {
    g[sz] = {};
    for (const m of MEASUREMENTS) g[sz][m] = '';
  }
  return g;
}

function gridFromChart(chart: Record<string, Record<string, number>>, sys: SizeSystem): Grid {
  const g = emptyGrid(sys);
  for (const sz of Object.keys(g)) {
    for (const m of MEASUREMENTS) {
      const v = chart?.[sz]?.[m];
      if (v !== undefined && v !== null) g[sz][m] = String(v);
    }
  }
  return g;
}

function chartFromGrid(g: Grid): Record<string, Record<string, number>> {
  const out: Record<string, Record<string, number>> = {};
  for (const sz of Object.keys(g)) {
    const vals: Record<string, number> = {};
    for (const m of MEASUREMENTS) {
      const v = parseFloat(g[sz][m]);
      if (!isNaN(v) && v > 0) vals[m] = v;
    }
    if (Object.keys(vals).length) out[sz] = vals;
  }
  return out;
}

export default function SizeChartsPage() {
  const router = useRouter();
  const { theme } = useTheme();
  const dark = theme === 'dark';
  const [user, setUser] = useState<User | null>(null);
  const [charts, setCharts] = useState<BrandSizeChart[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  // Editor
  const [editing, setEditing] = useState<BrandSizeChart | 'new' | null>(null);
  const [name, setName] = useState('');
  const [category, setCategory] = useState('tops');
  const [fitType, setFitType] = useState('regular');
  const [productTypes, setProductTypes] = useState('');
  const [system, setSystem] = useState<SizeSystem>('alpha');
  const [grid, setGrid] = useState<Grid>(emptyGrid('alpha'));
  const [pasteOpen, setPasteOpen] = useState(false);
  const [pasteText, setPasteText] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoadError('');
    try {
      setCharts(await sizeChartApi.list());
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : 'Could not load size charts');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    getCurrentUser().then((u) => {
      if (!u) { router.push('/login?as=brand'); return; }
      if (u.user_type !== 'brand') { router.push('/dashboard'); return; }
      setUser(u);
      load();
    });
  }, [router, load]);

  const openNew = () => {
    setEditing('new'); setName(''); setCategory('tops'); setFitType('regular'); setProductTypes('');
    setSystem('alpha'); setGrid(emptyGrid('alpha')); setPasteOpen(false); setPasteText(''); setError('');
  };
  const openEdit = (c: BrandSizeChart) => {
    const sys = inferSizeSystem(Object.keys(c.size_chart || {})) || 'alpha';
    setEditing(c); setName(c.name); setCategory(c.category); setFitType(c.fit_type || 'regular');
    setProductTypes((c.product_types || []).join(', '));
    setSystem(sys); setGrid(gridFromChart(c.size_chart || {}, sys)); setPasteOpen(false); setPasteText(''); setError('');
  };
  const changeSystem = (sys: SizeSystem) => {
    setSystem(sys);
    setGrid((prev) => {
      const next = emptyGrid(sys);
      for (const sz of Object.keys(next)) if (prev[sz]) next[sz] = { ...next[sz], ...prev[sz] };
      return next;
    });
  };
  const mergeParsed = (parsed: Record<string, Record<string, number>>) => {
    const keys = Object.keys(parsed);
    if (!keys.length) { setError('Could not read any sizes. Put the size (XS, S, M, L, XL or 32, 34…) in the first column or the header row, and the measurement names next to it.'); return; }
    const sys = inferSizeSystem(keys) || system;
    setSystem(sys);
    setGrid((prev) => {
      const next = emptyGrid(sys);
      for (const sz of Object.keys(next)) {
        next[sz] = { ...next[sz], ...(prev[sz] || {}) };
        if (parsed[sz]) for (const m of MEASUREMENTS) if (parsed[sz][m] !== undefined) next[sz][m] = String(parsed[sz][m]);
      }
      return next;
    });
    setError('');
  };
  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]; e.target.value = '';
    if (!f) return;
    try { mergeParsed(await parseChartFile(f)); }
    catch (err) { setError('Could not read that file. Use .xlsx, .csv or .json, or paste the table as text. ' + (err instanceof Error ? err.message : '')); }
  };
  const onPaste = () => {
    mergeParsed(rowsToChart(pastedTextToRows(pasteText)));
    setPasteOpen(false); setPasteText('');
  };

  const save = async () => {
    if (!editing) return;
    const chart = chartFromGrid(grid);
    if (!Object.keys(chart).length) { setError('Fill in at least one size.'); return; }
    setSaving(true); setError('');
    const types = productTypes.split(/[,\n;]/).map((t) => t.trim()).filter(Boolean);
    try {
      if (editing === 'new') await sizeChartApi.create({ name: name.trim() || category, category, fit_type: fitType, product_types: types, size_chart: chart });
      else await sizeChartApi.update(editing.id, { name: name.trim() || category, category, fit_type: fitType, product_types: types, size_chart: chart });
      await load();
      setEditing(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save');
    } finally {
      setSaving(false);
    }
  };
  const remove = async (c: BrandSizeChart) => {
    if (!confirm(`Delete the "${c.name}" chart? Products using it will fall back to the category chart or to no chart.`)) return;
    try { await sizeChartApi.remove(c.id); await load(); } catch (e) { alert(e instanceof Error ? e.message : 'Could not delete'); }
  };

  const card = dark ? 'bg-white/[0.04] border-white/10' : 'bg-white border-gray-200 shadow-sm';
  const muted = dark ? 'text-white/50' : 'text-gray-500';
  const input = `w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:border-transparent ${dark ? 'bg-white/5 border-white/10 text-white focus:ring-white/30' : 'border-gray-200 text-black focus:ring-black'}`;
  const btnPrimary = `px-4 py-2 text-sm font-medium rounded-lg transition ${dark ? 'bg-white text-black hover:bg-white/90' : 'bg-black text-white hover:bg-gray-800'}`;
  const btnGhost = `px-3 py-2 text-sm rounded-lg border transition ${dark ? 'border-white/15 hover:bg-white/5' : 'border-gray-200 hover:bg-gray-50'}`;

  return (
    <div className={`min-h-screen transition-colors ${dark ? 'bg-black text-white' : 'bg-gray-50 text-black'}`}>
      <input type="file" ref={fileRef} accept=".xlsx,.xls,.csv,.json" className="hidden" onChange={onFile} />
      <header className={`border-b px-6 py-3 ${dark ? 'bg-black/95 border-white/10' : 'bg-white border-gray-200'}`}>
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/brand" className={`transition ${dark ? 'text-white/40 hover:text-white' : 'text-gray-400 hover:text-black'}`}>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
            </Link>
            <div>
              <h1 className="text-xl font-semibold">Size charts</h1>
              <p className={`text-sm ${muted}`}>One chart per category. Every product without a 3D model uses these.</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className={`text-sm ${muted}`}>{user?.email}</span>
            <Link href="/brand/garments" className={btnGhost}>3D garments</Link>
            <button onClick={openNew} className={btnPrimary}>+ Add chart</button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        <div className={`rounded-xl p-4 border text-sm ${card}`}>
          <b>How it picks a chart.</b> For each product the size finder looks for, in order: the product&apos;s own 3D garment chart; a chart listing the product&apos;s Shopify <i>product type</i> (for example &quot;T-shirt&quot;); the chart for the product&apos;s category. So one chart per category covers the whole store, and you add a product-type chart only where the fit differs.
        </div>

        {loadError && <div className="rounded-xl p-4 border border-red-300 bg-red-50 text-red-700 text-sm">{loadError}</div>}

        {editing && (
          <div className={`rounded-xl p-6 border ${card}`}>
            <h2 className="text-lg font-semibold mb-4">{editing === 'new' ? 'New size chart' : `Edit: ${editing.name}`}</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className={`block text-sm font-medium mb-1 ${muted}`}>Name</label>
                <input className={input} value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Tops, or Hoodies" />
              </div>
              <div>
                <label className={`block text-sm font-medium mb-1 ${muted}`}>Category</label>
                <select className={input} value={category} onChange={(e) => setCategory(e.target.value)}>
                  {CATEGORIES.map((c) => <option key={c} value={c}>{c} — {CATEGORY_HINT[c]}</option>)}
                </select>
              </div>
              <div>
                <label className={`block text-sm font-medium mb-1 ${muted}`}>Shopify product types this chart is for (optional)</label>
                <input className={input} value={productTypes} onChange={(e) => setProductTypes(e.target.value)} placeholder="T-shirt, Longsleeve  (leave empty = whole category)" />
                <p className={`text-xs mt-1 ${muted}`}>Exactly as written in Shopify&apos;s &quot;Product type&quot; field. Case does not matter.</p>
              </div>
              <div>
                <label className={`block text-sm font-medium mb-1 ${muted}`}>Fit</label>
                <select className={input} value={fitType} onChange={(e) => setFitType(e.target.value)}>
                  {FIT_TYPES.map((f) => <option key={f} value={f}>{f}</option>)}
                </select>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 mb-3">
              <span className={`text-sm ${muted}`}>Sizes:</span>
              {(Object.keys(SIZE_SYSTEMS) as SizeSystem[]).map((s) => (
                <button key={s} type="button" onClick={() => changeSystem(s)} className={`px-3 py-1.5 text-xs rounded-full border ${system === s ? (dark ? 'bg-white text-black border-white' : 'bg-black text-white border-black') : (dark ? 'border-white/15' : 'border-gray-200')}`}>{SIZE_SYSTEMS[s].label}</button>
              ))}
              <span className="flex-1" />
              <button type="button" onClick={() => fileRef.current?.click()} className={btnGhost}>Import Excel / CSV</button>
              <button type="button" onClick={() => setPasteOpen((o) => !o)} className={btnGhost}>Paste from PDF</button>
            </div>

            {pasteOpen && (
              <div className={`rounded-lg p-3 mb-3 border ${dark ? 'border-white/10' : 'border-gray-200'}`}>
                <p className={`text-xs mb-2 ${muted}`}>Open the PDF, select the size table, copy, and paste it here. Sizes can run down the first column or across the top row; measurement names (chest, length, waist, …) next to them. Measurements in cm, flat (pit to pit).</p>
                <textarea className={`${input} font-mono text-xs`} rows={8} value={pasteText} onChange={(e) => setPasteText(e.target.value)} placeholder={'Size\tChest\tLength\nS\t52\t70\nM\t55\t72\nL\t58\t74'} />
                <div className="mt-2 flex gap-2"><button type="button" onClick={onPaste} className={btnPrimary}>Read table</button><button type="button" onClick={() => setPasteOpen(false)} className={btnGhost}>Cancel</button></div>
              </div>
            )}

            <div className="overflow-x-auto">
              <table className="text-sm min-w-full">
                <thead>
                  <tr className={muted}>
                    <th className="text-left py-2 pr-3 font-medium">Size</th>
                    {MEASUREMENTS.map((m) => <th key={m} className="text-left py-2 pr-2 font-medium capitalize">{m}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {SIZE_SYSTEMS[system].sizes.map((sz) => (
                    <tr key={sz} className={`border-t ${dark ? 'border-white/10' : 'border-gray-100'}`}>
                      <td className="py-1 pr-3 font-medium uppercase">{sz}</td>
                      {MEASUREMENTS.map((m) => (
                        <td key={m} className="py-1 pr-2">
                          <input type="number" step="0.5" value={grid[sz]?.[m] ?? ''} onChange={(e) => setGrid((g) => ({ ...g, [sz]: { ...g[sz], [m]: e.target.value } }))} className={`w-16 px-2 py-1 border rounded text-sm ${dark ? 'bg-white/5 border-white/10' : 'border-gray-200'}`} />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className={`text-xs mt-2 ${muted}`}>Measurements in cm, garment laid flat. Leave columns that do not apply empty.</p>

            {error && <div className="mt-3 text-sm text-red-600">{error}</div>}
            <div className="mt-4 flex gap-2">
              <button type="button" onClick={save} disabled={saving} className={btnPrimary}>{saving ? 'Saving…' : 'Save chart'}</button>
              <button type="button" onClick={() => setEditing(null)} className={btnGhost}>Cancel</button>
            </div>
          </div>
        )}

        {loading ? (
          <p className={muted}>Loading…</p>
        ) : charts.length === 0 && !editing ? (
          <div className={`rounded-xl p-8 border text-center ${card}`}>
            <p className="font-medium mb-1">No size charts yet</p>
            <p className={`text-sm mb-4 ${muted}`}>Start with one chart for tops and one for bottoms. That covers most of the store.</p>
            <button onClick={openNew} className={btnPrimary}>+ Add chart</button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {charts.map((c) => {
              const sizes = Object.keys(c.size_chart || {});
              const cols = MEASUREMENTS.filter((m) => sizes.some((s) => c.size_chart[s]?.[m] !== undefined));
              return (
                <div key={c.id} className={`rounded-xl p-5 border ${card}`}>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div>
                      <h3 className="font-semibold">{c.name}</h3>
                      <p className={`text-xs ${muted}`}>
                        <span className="capitalize">{c.category}</span> · {c.fit_type}
                        {c.product_types?.length ? <> · types: {c.product_types.join(', ')}</> : <> · default for the category</>}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => openEdit(c)} className={btnGhost}>Edit</button>
                      <button onClick={() => remove(c)} className={`${btnGhost} text-red-600`}>Delete</button>
                    </div>
                  </div>
                  {sizes.length ? (
                    <div className="overflow-x-auto">
                      <table className="text-xs">
                        <thead><tr className={muted}><th className="text-left pr-3 py-1">Size</th>{cols.map((m) => <th key={m} className="text-left pr-3 py-1 capitalize">{m}</th>)}</tr></thead>
                        <tbody>{sizes.map((s) => <tr key={s}><td className="pr-3 py-0.5 uppercase font-medium">{s}</td>{cols.map((m) => <td key={m} className="pr-3 py-0.5">{c.size_chart[s]?.[m] ?? ''}</td>)}</tr>)}</tbody>
                      </table>
                    </div>
                  ) : <p className={`text-sm ${muted}`}>Empty</p>}
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
