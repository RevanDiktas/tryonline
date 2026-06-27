'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getCurrentUser, type User } from '@/lib/supabase-auth';
import { getMyBrand, garmentApi, type Garment } from '@/lib/api';
import { SIZE_SYSTEMS, inferSizeSystem, type SizeSystem } from '@/lib/sizeRecommendation';
import { useTheme } from '@/contexts/ThemeContext';

const CATEGORIES = ['tops', 'bottoms', 'outerwear', 'dresses', 'accessories'];
const FIT_TYPES = ['slim', 'regular', 'oversized'];
// Default (letter) size labels; a garment's actual rows come from its chosen size system.
const SIZES = SIZE_SYSTEMS.alpha.sizes;
// Every size label across all systems — used to validate sizes on import before merging.
const ALL_SIZE_LABELS = new Set(Object.values(SIZE_SYSTEMS).flatMap((s) => s.sizes));

// Garment measurements, ordered head-to-toe. Each maps to a body measurement the avatar
// extracts (see avatar-creation handler.py MEASUREMENT_MAPPING) so the recommender can compare
// garment vs body: neck->neck, shoulder->shoulder_width, sleeve->arm_length, cuff->wrist,
// bicep->bicep, rise->crotch_height, thigh->thigh, inseam->inseam, hem->leg/calf opening.
// length & hem are garment-only (no body equivalent). Merchants leave irrelevant columns blank.
const MEASUREMENTS = ['neck', 'shoulder', 'chest', 'bicep', 'sleeve', 'cuff', 'length', 'waist', 'hips', 'rise', 'thigh', 'inseam', 'hem'];

// Maps real-world size-chart header names (from merchant Excel/CSV packs) onto our canonical keys.
const MEASUREMENT_ALIASES: Record<string, string> = {
  bust: 'chest', chest: 'chest',
  shoulder: 'shoulder', shoulders: 'shoulder', 'shoulder width': 'shoulder', 'across shoulder': 'shoulder', 'across back': 'shoulder',
  bicep: 'bicep', biceps: 'bicep', 'upper arm': 'bicep', armhole: 'bicep',
  sleeve: 'sleeve', 'sleeve length': 'sleeve', 'arm length': 'sleeve', arm: 'sleeve',
  cuff: 'cuff', wrist: 'cuff', 'sleeve opening': 'cuff', 'cuff width': 'cuff', 'cuff opening': 'cuff',
  neck: 'neck', neckline: 'neck', collar: 'neck', 'neck width': 'neck',
  length: 'length', 'body length': 'length', 'garment length': 'length', 'total length': 'length', 'back length': 'length', 'front length': 'length',
  waist: 'waist',
  hip: 'hips', hips: 'hips', seat: 'hips',
  rise: 'rise', 'front rise': 'rise', 'rise front': 'rise',
  thigh: 'thigh', 'thigh width': 'thigh', 'leg width': 'thigh',
  inseam: 'inseam', 'inside leg': 'inseam', 'inner leg': 'inseam', inleg: 'inseam',
  hem: 'hem', 'hem width': 'hem', 'bottom opening': 'hem', 'leg opening': 'hem', sweep: 'hem', 'bottom width': 'hem', opening: 'hem',
};

// Normalize a header cell ("Sleeve Length (cm)", "CHEST", "inside leg") to a canonical key, or null.
function normalizeHeader(raw: unknown): string | null {
  if (raw == null) return null;
  let h = String(raw).toLowerCase().trim();
  h = h.replace(/\([^)]*\)/g, ' ');                 // drop parenthetical units e.g. "(cm)"
  h = h.replace(/\bcm\b|\binch(es)?\b|"/g, ' ');     // drop bare units
  h = h.replace(/[_\-/]+/g, ' ').replace(/[^a-z0-9 ]/g, ' ').replace(/\s+/g, ' ').trim();
  if (!h) return null;
  if (MEASUREMENT_ALIASES[h]) return MEASUREMENT_ALIASES[h];
  if (MEASUREMENTS.includes(h)) return h;
  const first = h.split(' ')[0];                     // "chest circumference" -> "chest"
  if (MEASUREMENT_ALIASES[first]) return MEASUREMENT_ALIASES[first];
  if (MEASUREMENTS.includes(first)) return first;
  return null;
}

// Parse a numeric cell, tolerating European decimal commas ("33,5") and thousands separators.
function parseNum(raw: unknown): number {
  if (typeof raw === 'number') return raw;
  if (raw == null) return NaN;
  let s = String(raw).trim().replace(/\s/g, '');
  if (!s) return NaN;
  s = s.replace(/[^0-9.,-]/g, '');
  if (s.includes(',') && !s.includes('.')) s = s.replace(',', '.'); // decimal comma -> dot
  else s = s.replace(/,/g, '');                                     // comma is thousands sep
  return parseFloat(s);
}

// Split a CSV (comma / semicolon / tab delimited) into a row-major array of trimmed cells.
function csvToRows(text: string): string[][] {
  const lines = text.replace(/\r\n?/g, '\n').trim().split('\n').filter((l) => l.length);
  if (!lines.length) return [];
  const count = (ch: string) => (lines[0].split(ch).length - 1);
  const semi = count(';'), tab = count('\t'), comma = count(',');
  const delim = semi >= comma && semi >= tab ? ';' : tab > comma ? '\t' : ',';
  return lines.map((l) => l.split(delim).map((c) => c.trim().replace(/^"|"$/g, '')));
}

// Turn a sheet (array of rows; col 0 = size label, header row names measurements) into a size chart.
function rowsToChart(rows: unknown[][]): Record<string, Record<string, number>> {
  const out: Record<string, Record<string, number>> = {};
  if (!rows || rows.length < 2) return out;
  let headerIdx = rows.findIndex((r) => Array.isArray(r) && r.slice(1).some((c) => normalizeHeader(c)));
  if (headerIdx < 0) headerIdx = 0;
  const header = rows[headerIdx] || [];
  const colMap: Record<number, string> = {};
  for (let i = 1; i < header.length; i++) {            // col 0 holds the size label
    const key = normalizeHeader(header[i]);
    if (key) colMap[i] = key;
  }
  for (let r = headerIdx + 1; r < rows.length; r++) {
    const row = rows[r];
    if (!Array.isArray(row)) continue;
    const sz = String(row[0] ?? '').trim().toLowerCase();
    if (!ALL_SIZE_LABELS.has(sz)) continue;
    const vals: Record<string, number> = {};
    for (const idx of Object.keys(colMap)) {
      const v = parseNum(row[Number(idx)]);
      if (!isNaN(v) && v > 0) vals[colMap[Number(idx)]] = v;
    }
    out[sz] = vals;
  }
  return out;
}

interface GarmentForm {
  name: string;
  category: string;
  shopify_product_id: string;
  fit_type: string;
}

export default function GarmentsPage() {
  const router = useRouter();
  const { theme } = useTheme();
  const dark = theme === 'dark';
  const [user, setUser] = useState<User | null>(null);
  const [brandId, setBrandId] = useState<string | null>(null);
  const [garments, setGarments] = useState<Garment[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<GarmentForm>({ name: '', category: 'tops', shopify_product_id: '', fit_type: 'regular' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [uploadingSize, setUploadingSize] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadTarget, setUploadTarget] = useState<{ garmentId: string; size: string } | null>(null);

  const [syncingId, setSyncingId] = useState<string | null>(null);

  const [loadError, setLoadError] = useState('');

  const loadGarments = useCallback(async (bid: string) => {
    setLoadError('');
    try {
      const list = await garmentApi.list(bid);
      setGarments(list);
      for (const g of list) {
        if (g.shopify_product_id && Object.keys(g.sizes || {}).length === 0) {
          try {
            await garmentApi.sync(g.id);
          } catch {}
        }
      }
      const updated = await garmentApi.list(bid);
      setGarments(updated);
    } catch (e) {
      console.error('Failed to load garments:', e);
      setLoadError('Failed to load garments. Please check your connection and try again.');
    }
  }, []);

  useEffect(() => {
    getCurrentUser().then(async (u) => {
      if (!u || u.user_type !== 'brand') { router.push('/login'); return; }
      setUser(u);
      const brand = await getMyBrand(u.id);
      if (brand?.id) {
        setBrandId(brand.id as string);
        await loadGarments(brand.id as string);
      }
      setLoading(false);
    }).catch(() => router.push('/login'));
  }, [router, loadGarments]);

  const handleSubmit = async () => {
    if (!form.name.trim()) { setError('Name is required'); return; }
    if (!brandId) return;
    setSaving(true);
    setError('');
    try {
      if (editingId) {
        await garmentApi.update(editingId, {
          name: form.name,
          category: form.category,
          shopify_product_id: form.shopify_product_id || undefined,
          fit_type: form.fit_type,
        });
      } else {
        await garmentApi.create({
          brand_id: brandId,
          name: form.name,
          category: form.category,
          shopify_product_id: form.shopify_product_id || undefined,
          fit_type: form.fit_type,
        });
      }
      await loadGarments(brandId);
      resetForm();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const resetForm = () => {
    setShowForm(false);
    setEditingId(null);
    setForm({ name: '', category: 'tops', shopify_product_id: '', fit_type: 'regular' });
    setError('');
  };

  const startEdit = (g: Garment) => {
    setForm({
      name: g.name,
      category: g.category || 'tops',
      shopify_product_id: g.shopify_product_id || '',
      fit_type: g.fit_type || 'regular',
    });
    setEditingId(g.id);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this garment and all its files?')) return;
    try {
      await garmentApi.remove(id);
      if (brandId) await loadGarments(brandId);
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Delete failed');
    }
  };

  const triggerUpload = (garmentId: string, size: string) => {
    setUploadTarget({ garmentId, size });
    fileInputRef.current?.click();
  };

  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !uploadTarget) return;
    e.target.value = '';

    setUploadingSize(`${uploadTarget.garmentId}-${uploadTarget.size}`);
    try {
      await garmentApi.uploadGlb(uploadTarget.garmentId, uploadTarget.size, file);
      if (brandId) await loadGarments(brandId);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploadingSize(null);
      setUploadTarget(null);
    }
  };

  // --- Size Chart Editor --- (MEASUREMENTS + import helpers are module-level, above)
  const [sizeChartGarmentId, setSizeChartGarmentId] = useState<string | null>(null);
  const [sizeChartData, setSizeChartData] = useState<Record<string, Record<string, string>>>({});
  const [savingSizeChart, setSavingSizeChart] = useState(false);
  const csvInputRef = useRef<HTMLInputElement>(null);

  // Per-garment size system (letters / Women EU / Men EU). A merchant override is kept here;
  // otherwise it's inferred from the labels already stored on the garment.
  const [garmentSystems, setGarmentSystems] = useState<Record<string, SizeSystem>>({});
  const systemOf = (id: string): SizeSystem => {
    if (garmentSystems[id]) return garmentSystems[id];
    const g = garments.find((x) => x.id === id);
    const keys = g ? [...Object.keys(g.sizes || {}), ...Object.keys(g.size_chart || {})] : [];
    return inferSizeSystem(keys);
  };
  const setSystem = (id: string, sys: SizeSystem) => setGarmentSystems((p) => ({ ...p, [id]: sys }));
  const sizesOf = (id: string): string[] => SIZE_SYSTEMS[systemOf(id)].sizes;

  // Switch the open editor to a different size system, rebuilding the rows (keeping any values
  // already stored or typed for labels that carry over).
  const changeModalSystem = (sys: SizeSystem) => {
    if (!sizeChartGarmentId) return;
    setSystem(sizeChartGarmentId, sys);
    const g = garments.find((x) => x.id === sizeChartGarmentId);
    const chart: Record<string, Record<string, string>> = {};
    for (const sz of SIZE_SYSTEMS[sys].sizes) {
      chart[sz] = {};
      for (const m of MEASUREMENTS) {
        const stored = (g?.size_chart?.[sz] as Record<string, number> | undefined)?.[m];
        chart[sz][m] = String(stored ?? sizeChartData[sz]?.[m] ?? '');
      }
    }
    setSizeChartData(chart);
  };

  const openSizeChart = (g: Garment) => {
    const chart: Record<string, Record<string, string>> = {};
    for (const sz of sizesOf(g.id)) {
      chart[sz] = {};
      for (const m of MEASUREMENTS) {
        chart[sz][m] = String((g.size_chart?.[sz] as Record<string, number> | undefined)?.[m] ?? '');
      }
    }
    setSizeChartData(chart);
    setSizeChartGarmentId(g.id);
  };

  const updateSizeChartCell = (size: string, measurement: string, value: string) => {
    setSizeChartData((prev) => ({
      ...prev,
      [size]: { ...prev[size], [measurement]: value },
    }));
  };

  const saveSizeChart = async () => {
    if (!sizeChartGarmentId) return;
    setSavingSizeChart(true);
    try {
      const chart: Record<string, Record<string, number>> = {};
      for (const sz of sizesOf(sizeChartGarmentId)) {
        const row = sizeChartData[sz];
        if (!row) continue;
        const vals: Record<string, number> = {};
        let hasValue = false;
        for (const m of MEASUREMENTS) {
          const v = parseFloat(row[m]);
          if (!isNaN(v) && v > 0) { vals[m] = v; hasValue = true; }
        }
        if (hasValue) chart[sz] = vals;
      }
      await garmentApi.update(sizeChartGarmentId, { size_chart: chart });
      if (brandId) await loadGarments(brandId);
      setSizeChartGarmentId(null);
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to save size chart');
    } finally {
      setSavingSizeChart(false);
    }
  };

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = '';
    try {
      const name = file.name.toLowerCase();
      let parsed: Record<string, Record<string, number>> = {};

      if (name.endsWith('.json')) {
        // JSON: {"xs": {"chest": 86, "sleeve length": 60, ...}, ...} — keys + values are normalized.
        const obj = JSON.parse(await file.text());
        for (const rawSz of Object.keys(obj || {})) {
          const sz = rawSz.toLowerCase().trim();
          if (!ALL_SIZE_LABELS.has(sz)) continue;
          const vals: Record<string, number> = {};
          for (const [rawKey, rawVal] of Object.entries(obj[rawSz] || {})) {
            const key = normalizeHeader(rawKey);
            const v = parseNum(rawVal);
            if (key && !isNaN(v) && v > 0) vals[key] = v;
          }
          parsed[sz] = vals;
        }
      } else if (name.endsWith('.xlsx') || name.endsWith('.xls')) {
        // Excel: read the first sheet as a grid (size in col 0, measurement names in the header row).
        const XLSX = await import('xlsx');
        const wb = XLSX.read(await file.arrayBuffer(), { type: 'array' });
        const ws = wb.Sheets[wb.SheetNames[0]];
        const rows = XLSX.utils.sheet_to_json(ws, { header: 1, raw: true, defval: '' }) as unknown[][];
        parsed = rowsToChart(rows);
      } else {
        parsed = rowsToChart(csvToRows(await file.text()));
      }

      if (!Object.keys(parsed).length) {
        alert('Could not read any size rows. Put the size (XS/S/M/L/XL) in the first column and the measurement names in the header row.');
        return;
      }

      // Merge into editor (only canonical keys survive normalization, so this stays in-schema)
      const updated = { ...sizeChartData };
      for (const sz of (sizeChartGarmentId ? sizesOf(sizeChartGarmentId) : SIZES)) {
        if (!updated[sz]) updated[sz] = {};
        if (parsed[sz]) {
          for (const m of MEASUREMENTS) {
            if (parsed[sz][m] !== undefined) updated[sz][m] = String(parsed[sz][m]);
          }
        }
      }
      setSizeChartData(updated);
    } catch (err) {
      alert('Failed to parse file. Accepted formats: .xlsx, .csv, .json. ' + (err instanceof Error ? err.message : ''));
    }
  };

  const sizeCount = (g: Garment) => Object.keys(g.sizes || {}).length;
  const sizeChartCount = (g: Garment) => Object.keys(g.size_chart || {}).length;

  if (loading) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${dark ? 'bg-black' : 'bg-white'}`}>
        <div className={`w-8 h-8 border-2 rounded-full animate-spin ${dark ? 'border-white/20 border-t-white' : 'border-black/20 border-t-black'}`} />
      </div>
    );
  }

  return (
    <div className={`min-h-screen transition-colors ${dark ? 'bg-black text-white' : 'bg-gray-50 text-black'}`}>
      <input type="file" ref={fileInputRef} accept=".glb" className="hidden" onChange={handleFileSelected} />

      {/* Header */}
      <header className={`border-b px-6 py-3 ${dark ? 'bg-black/95 border-white/10' : 'bg-white border-gray-200'}`}>
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/brand" className={`transition ${dark ? 'text-white/40 hover:text-white' : 'text-gray-400 hover:text-black'}`}>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <h1 className="text-xl font-semibold">Garments</h1>
              <p className={`text-sm ${dark ? 'text-white/50' : 'text-gray-500'}`}>Manage your products and 3D models</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className={`text-sm ${dark ? 'text-white/50' : 'text-gray-500'}`}>{user?.email}</span>
            <button
              onClick={() => { resetForm(); setShowForm(true); }}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition ${dark ? 'bg-white text-black hover:bg-white/90' : 'bg-black text-white hover:bg-gray-800'}`}
            >
              + Add Garment
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* Add / Edit Form */}
        {showForm && (
          <div className={`rounded-xl p-6 mb-8 border ${dark ? 'bg-white/[0.04] border-white/10' : 'bg-white border-gray-200 shadow-sm'}`}>
            <h2 className="text-lg font-semibold mb-4">{editingId ? 'Edit Garment' : 'Add New Garment'}</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className={`block text-sm font-medium mb-1 ${dark ? 'text-white/60' : 'text-gray-700'}`} htmlFor="garment-name">Name *</label>
                <input
                  id="garment-name"
                  name="garment-name"
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. Classic T-Shirt"
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:border-transparent ${dark ? 'bg-white/5 border-white/10 text-white focus:ring-white/30' : 'border-gray-200 text-black focus:ring-black'}`}
                />
              </div>
              <div>
                <label className={`block text-sm font-medium mb-1 ${dark ? 'text-white/60' : 'text-gray-700'}`} htmlFor="garment-shopify-product-id">Shopify product handle *</label>
                <input
                  id="garment-shopify-product-id"
                  name="shopify_product_id"
                  type="text"
                  value={form.shopify_product_id}
                  onChange={(e) => setForm({ ...form, shopify_product_id: e.target.value.trim() })}
                  placeholder="e.g. rs-zip-up"
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:border-transparent ${dark ? 'bg-white/5 border-white/10 text-white focus:ring-white/30' : 'border-gray-200 text-black focus:ring-black'}`}
                />
                <p className={`text-xs mt-1 ${dark ? 'text-white/30' : 'text-gray-400'}`}>
                  Must match the storefront URL slug: /products/<strong>handle</strong> (same value the theme sends to Tryon). Stored as product id + handle in the database.
                </p>
              </div>
              <div>
                <label className={`block text-sm font-medium mb-1 ${dark ? 'text-white/60' : 'text-gray-700'}`} htmlFor="garment-category">Category</label>
                <select
                  id="garment-category"
                  name="category"
                  value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:border-transparent ${dark ? 'bg-white/5 border-white/10 text-white focus:ring-white/30' : 'border-gray-200 text-black focus:ring-black'}`}
                >
                  {CATEGORIES.map((c) => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
                </select>
              </div>
              <div>
                <label className={`block text-sm font-medium mb-1 ${dark ? 'text-white/60' : 'text-gray-700'}`} htmlFor="garment-fit-type">Fit Type</label>
                <select
                  id="garment-fit-type"
                  name="fit_type"
                  value={form.fit_type}
                  onChange={(e) => setForm({ ...form, fit_type: e.target.value })}
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:border-transparent ${dark ? 'bg-white/5 border-white/10 text-white focus:ring-white/30' : 'border-gray-200 text-black focus:ring-black'}`}
                >
                  {FIT_TYPES.map((f) => <option key={f} value={f}>{f.charAt(0).toUpperCase() + f.slice(1)}</option>)}
                </select>
              </div>
            </div>

            {error && <p className="text-red-500 text-sm mt-3">{error}</p>}

            <div className="flex gap-3 mt-5">
              <button
                onClick={handleSubmit}
                disabled={saving}
                className={`px-5 py-2 text-sm font-medium rounded-lg transition disabled:opacity-40 ${dark ? 'bg-white text-black hover:bg-white/90' : 'bg-black text-white hover:bg-gray-800'}`}
              >
                {saving ? 'Saving...' : editingId ? 'Update' : 'Create Garment'}
              </button>
              <button onClick={resetForm} className={`px-5 py-2 text-sm transition ${dark ? 'text-white/50 hover:text-white' : 'text-gray-600 hover:text-black'}`}>
                Cancel
              </button>
            </div>
          </div>
        )}

        {loadError && (
          <div className={`mb-4 p-4 rounded-xl text-sm flex items-center justify-between border ${dark ? 'bg-red-500/10 border-red-500/20 text-red-400' : 'bg-red-50 border-red-100 text-red-700'}`}>
            <span>{loadError}</span>
            <button onClick={() => brandId && loadGarments(brandId)} className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${dark ? 'bg-red-500/20 hover:bg-red-500/30' : 'bg-red-100 hover:bg-red-200'}`}>
              Retry
            </button>
          </div>
        )}

        {/* Garments List */}
        {garments.length === 0 ? (
          <div className={`rounded-xl p-12 text-center border ${dark ? 'bg-white/[0.04] border-white/10' : 'bg-white border-gray-200'}`}>
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 ${dark ? 'bg-white/5' : 'bg-gray-100'}`}>
              <svg className={`w-8 h-8 ${dark ? 'text-white/30' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold mb-2">No garments yet</h3>
            <p className={`text-sm mb-6 ${dark ? 'text-white/50' : 'text-gray-500'}`}>Add your first garment to start using virtual try-on</p>
            <button
              onClick={() => { resetForm(); setShowForm(true); }}
              className={`px-5 py-2.5 text-sm font-medium rounded-lg transition ${dark ? 'bg-white text-black hover:bg-white/90' : 'bg-black text-white hover:bg-gray-800'}`}
            >
              + Add Your First Garment
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {garments.map((g) => (
              <div key={g.id} className={`rounded-xl p-5 border ${dark ? 'bg-white/[0.04] border-white/10' : 'bg-white border-gray-200 shadow-sm'}`}>
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-base font-semibold">{g.name}</h3>
                    <div className="flex items-center gap-3 mt-1">
                      {g.category && (
                        <span className={`text-xs px-2 py-0.5 rounded-full ${dark ? 'bg-white/10 text-white/60' : 'bg-gray-100 text-gray-600'}`}>
                          {g.category}
                        </span>
                      )}
                      <span className={`text-xs px-2 py-0.5 rounded-full ${dark ? 'bg-white/10 text-white/60' : 'bg-gray-100 text-gray-600'}`}>
                        {g.fit_type || 'regular'}
                      </span>
                      {g.shopify_product_id && (
                        <span className={`text-xs font-mono ${dark ? 'text-white/30' : 'text-gray-400'}`}>
                          {g.shopify_product_id}
                        </span>
                      )}
                      {!g.shopify_product_id && (
                        <span className="text-xs text-amber-500">No product linked</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={async () => {
                        setSyncingId(g.id);
                        try {
                          await garmentApi.sync(g.id);
                          if (brandId) await loadGarments(brandId);
                        } catch (e) {
                          setError('Sync failed. Please try again.');
                          console.error('Sync error:', e);
                        }
                        setSyncingId(null);
                      }}
                      disabled={syncingId === g.id}
                      className={`text-xs transition px-2 py-1 ${dark ? 'text-blue-400 hover:text-blue-300' : 'text-blue-500 hover:text-blue-700'}`}
                    >
                      {syncingId === g.id ? 'Syncing...' : 'Sync Files'}
                    </button>
                    <button onClick={() => startEdit(g)} className={`text-xs transition px-2 py-1 ${dark ? 'text-white/50 hover:text-white' : 'text-gray-500 hover:text-black'}`}>
                      Edit
                    </button>
                    <button onClick={() => handleDelete(g.id)} className="text-xs text-red-400 hover:text-red-500 transition px-2 py-1">
                      Delete
                    </button>
                  </div>
                </div>

                {/* Size GLB uploads */}
                <div className={`border-t pt-4 ${dark ? 'border-white/10' : 'border-gray-100'}`}>
                  <div className="flex items-center justify-between mb-2">
                    <p className={`text-xs font-medium uppercase tracking-wide ${dark ? 'text-white/40' : 'text-gray-500'}`}>
                      3D Models ({sizeCount(g)}/{sizesOf(g.id).length} sizes)
                    </p>
                    <label className={`flex items-center gap-1.5 text-xs ${dark ? 'text-white/40' : 'text-gray-500'}`}>
                      Sizing
                      <select
                        value={systemOf(g.id)}
                        onChange={(e) => setSystem(g.id, e.target.value as SizeSystem)}
                        className={`text-xs rounded border px-1.5 py-1 focus:outline-none ${dark ? 'bg-white/5 border-white/10 text-white' : 'bg-white border-gray-200 text-black'}`}
                      >
                        {(Object.keys(SIZE_SYSTEMS) as SizeSystem[]).map((s) => (
                          <option key={s} value={s}>{SIZE_SYSTEMS[s].label}</option>
                        ))}
                      </select>
                    </label>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {sizesOf(g.id).map((size) => {
                      const hasFile = !!(g.sizes && g.sizes[size]);
                      const isUploading = uploadingSize === `${g.id}-${size}`;
                      return (
                        <button
                          key={size}
                          onClick={() => triggerUpload(g.id, size)}
                          disabled={isUploading}
                          className={`
                            relative px-4 py-2 text-sm font-medium rounded-lg border transition
                            ${hasFile
                              ? dark ? 'bg-green-500/10 border-green-500/30 text-green-400 hover:bg-green-500/20' : 'bg-green-50 border-green-200 text-green-700 hover:bg-green-100'
                              : dark ? 'bg-white/5 border-white/10 text-white/50 hover:border-white/30 hover:text-white' : 'bg-white border-gray-200 text-gray-500 hover:border-black hover:text-black'}
                            ${isUploading ? 'opacity-50 cursor-wait' : ''}
                          `}
                        >
                          {isUploading ? (
                            <span className="flex items-center gap-1">
                              <svg className="w-3 h-3 animate-spin" viewBox="0 0 24 24" fill="none">
                                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
                                <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                              </svg>
                              {size.toUpperCase()}
                            </span>
                          ) : (
                            <>
                              {size.toUpperCase()}
                              {hasFile && (
                                <svg className="w-3 h-3 inline ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                              )}
                            </>
                          )}
                        </button>
                      );
                    })}
                  </div>
                  <p className={`text-xs mt-2 ${dark ? 'text-white/25' : 'text-gray-400'}`}>Click a size to upload or replace a .glb file</p>
                </div>

                {/* Size Chart */}
                <div className={`border-t pt-4 mt-4 ${dark ? 'border-white/10' : 'border-gray-100'}`}>
                  <div className="flex items-center justify-between mb-2">
                    <p className={`text-xs font-medium uppercase tracking-wide ${dark ? 'text-white/40' : 'text-gray-500'}`}>
                      Size Chart ({sizeChartCount(g)} sizes)
                    </p>
                    <button
                      onClick={() => openSizeChart(g)}
                      className={`text-xs transition ${dark ? 'text-blue-400 hover:text-blue-300' : 'text-blue-500 hover:text-blue-700'}`}
                    >
                      {sizeChartCount(g) > 0 ? 'Edit Size Chart' : '+ Add Size Chart'}
                    </button>
                  </div>
                  {sizeChartCount(g) > 0 && (() => {
                    const usedMeasurements = MEASUREMENTS.filter((m) =>
                      sizesOf(g.id).some((sz) => (g.size_chart?.[sz] as Record<string, number> | undefined)?.[m] != null)
                    );
                    return (
                    <div className="overflow-x-auto">
                      <table className="text-xs w-full">
                        <thead>
                          <tr className={dark ? 'text-white/40' : 'text-gray-400'}>
                            <th className="text-left pr-4 py-1 font-medium">Size</th>
                            {usedMeasurements.map((m) => (
                              <th key={m} className="text-right px-2 py-1 font-medium capitalize">{m}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {sizesOf(g.id).filter((sz) => g.size_chart?.[sz]).map((sz) => {
                            const row = g.size_chart[sz] as Record<string, number>;
                            return (
                              <tr key={sz} className={dark ? 'text-white/70' : 'text-gray-700'}>
                                <td className="pr-4 py-1 font-medium uppercase">{sz}</td>
                                {usedMeasurements.map((m) => (
                                  <td key={m} className="text-right px-2 py-1">{row[m] ?? '-'}</td>
                                ))}
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>);
                  })()}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Size Chart Editor Modal */}
        {sizeChartGarmentId && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => setSizeChartGarmentId(null)}>
            <div className={`rounded-2xl p-6 w-full max-w-2xl shadow-xl ${dark ? 'bg-gray-900 border border-white/10' : 'bg-white'}`} onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-5">
                <h3 className="text-lg font-semibold">Size Chart (measurements in cm)</h3>
                <div className="flex items-center gap-3">
                  <label className={`flex items-center gap-1.5 text-xs ${dark ? 'text-white/40' : 'text-gray-500'}`}>
                    Sizing
                    <select
                      value={systemOf(sizeChartGarmentId)}
                      onChange={(e) => changeModalSystem(e.target.value as SizeSystem)}
                      className={`text-xs rounded border px-1.5 py-1 focus:outline-none ${dark ? 'bg-white/5 border-white/10 text-white' : 'bg-white border-gray-200 text-black'}`}
                    >
                      {(Object.keys(SIZE_SYSTEMS) as SizeSystem[]).map((s) => (
                        <option key={s} value={s}>{SIZE_SYSTEMS[s].label}</option>
                      ))}
                    </select>
                  </label>
                  <button onClick={() => setSizeChartGarmentId(null)} className={`text-xl ${dark ? 'text-white/40 hover:text-white' : 'text-gray-400 hover:text-black'}`}>&times;</button>
                </div>
              </div>

              <input id="size-chart-import" name="size-chart-import" type="file" ref={csvInputRef} accept=".csv,.json,.xlsx,.xls" className="hidden" onChange={handleImportFile} />

              <div className="overflow-x-auto mb-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className={`border-b ${dark ? 'border-white/10' : 'border-gray-200'}`}>
                      <th className={`text-left py-2 pr-3 font-medium text-xs uppercase ${dark ? 'text-white/40' : 'text-gray-500'}`}>Size</th>
                      {MEASUREMENTS.map((m) => (
                        <th key={m} className={`text-center py-2 px-2 font-medium text-xs uppercase ${dark ? 'text-white/40' : 'text-gray-500'}`}>{m}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {sizesOf(sizeChartGarmentId).map((sz) => (
                      <tr key={sz} className={`border-b ${dark ? 'border-white/5' : 'border-gray-100'}`}>
                        <td className="py-2 pr-3 font-medium uppercase">{sz}</td>
                        {MEASUREMENTS.map((m) => (
                          <td key={m} className="py-2 px-1">
                            <input
                              id={`size-chart-${sz}-${m}`}
                              name={`size-chart-${sz}-${m}`}
                              type="number"
                              value={sizeChartData[sz]?.[m] ?? ''}
                              onChange={(e) => updateSizeChartCell(sz, m, e.target.value)}
                              placeholder="-"
                              className={`w-full px-2 py-1.5 border rounded text-center text-sm focus:outline-none focus:ring-1 ${dark ? 'bg-white/5 border-white/10 text-white focus:ring-white/30' : 'border-gray-200 text-black focus:ring-black'}`}
                            />
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex items-center justify-between">
                <button
                  onClick={() => csvInputRef.current?.click()}
                  className={`text-sm transition flex items-center gap-1 ${dark ? 'text-white/50 hover:text-white' : 'text-gray-500 hover:text-black'}`}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                  Import Excel / CSV / JSON
                </button>
                <div className="flex gap-3">
                  <button onClick={() => setSizeChartGarmentId(null)} className={`px-4 py-2 text-sm transition ${dark ? 'text-white/50 hover:text-white' : 'text-gray-600 hover:text-black'}`}>
                    Cancel
                  </button>
                  <button
                    onClick={saveSizeChart}
                    disabled={savingSizeChart}
                    className={`px-5 py-2 text-sm font-medium rounded-lg transition disabled:opacity-40 ${dark ? 'bg-white text-black hover:bg-white/90' : 'bg-black text-white hover:bg-gray-800'}`}
                  >
                    {savingSizeChart ? 'Saving...' : 'Save Size Chart'}
                  </button>
                </div>
              </div>

              <p className={`text-xs mt-3 ${dark ? 'text-white/25' : 'text-gray-400'}`}>
                Excel/CSV: first column = size (XS/S/M/L/XL), header row names the measurements (chest,
                sleeve length, inside leg, hem ... are recognized; decimal commas OK). JSON: {`{"xs": {"chest": 86, "sleeve": 60, ...}, ...}`}
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
