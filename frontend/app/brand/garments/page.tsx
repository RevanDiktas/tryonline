'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getCurrentUser, type User } from '@/lib/supabase-auth';
import { getMyBrand, garmentApi, type Garment } from '@/lib/api';

const CATEGORIES = ['tops', 'bottoms', 'outerwear', 'dresses', 'accessories'];
const FIT_TYPES = ['slim', 'regular', 'oversized'];
const SIZES = ['xs', 's', 'm', 'l', 'xl'];

interface GarmentForm {
  name: string;
  category: string;
  shopify_product_id: string;
  fit_type: string;
}

export default function GarmentsPage() {
  const router = useRouter();
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

  const loadGarments = useCallback(async (bid: string) => {
    try {
      const list = await garmentApi.list(bid);
      setGarments(list);
      // Auto-sync garments that have no sizes but have a shopify_product_id
      for (const g of list) {
        if (g.shopify_product_id && Object.keys(g.sizes || {}).length === 0) {
          try {
            await garmentApi.sync(g.id);
          } catch {}
        }
      }
      // Reload after sync
      const updated = await garmentApi.list(bid);
      setGarments(updated);
    } catch {
      console.error('Failed to load garments');
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

  const sizeCount = (g: Garment) => Object.keys(g.sizes || {}).length;

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-black/20 border-t-black rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <input type="file" ref={fileInputRef} accept=".glb" className="hidden" onChange={handleFileSelected} />

      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/brand" className="text-gray-400 hover:text-black transition">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <h1 className="text-xl font-semibold text-black">Garments</h1>
              <p className="text-sm text-gray-500">Manage your products and 3D models</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500">{user?.email}</span>
            <button
              onClick={() => { resetForm(); setShowForm(true); }}
              className="px-4 py-2 bg-black text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition"
            >
              + Add Garment
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* Add / Edit Form */}
        {showForm && (
          <div className="bg-white border border-gray-200 rounded-xl p-6 mb-8 shadow-sm">
            <h2 className="text-lg font-semibold text-black mb-4">{editingId ? 'Edit Garment' : 'Add New Garment'}</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. Classic T-Shirt"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-black focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Shopify Product ID *</label>
                <input
                  type="text"
                  value={form.shopify_product_id}
                  onChange={(e) => setForm({ ...form, shopify_product_id: e.target.value.trim() })}
                  placeholder="e.g. 8234567890123"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-black focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                />
                <p className="text-xs text-gray-400 mt-1">
                  Find this in Shopify Admin → Products → click product → the number in the URL.
                  Creates a storage folder and links to the TryOn widget on this product page.
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                <select
                  value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-black focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                >
                  {CATEGORIES.map((c) => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Fit Type</label>
                <select
                  value={form.fit_type}
                  onChange={(e) => setForm({ ...form, fit_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-black focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                >
                  {FIT_TYPES.map((f) => <option key={f} value={f}>{f.charAt(0).toUpperCase() + f.slice(1)}</option>)}
                </select>
              </div>
            </div>

            {error && <p className="text-red-600 text-sm mt-3">{error}</p>}

            <div className="flex gap-3 mt-5">
              <button
                onClick={handleSubmit}
                disabled={saving}
                className="px-5 py-2 bg-black text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition disabled:opacity-40"
              >
                {saving ? 'Saving...' : editingId ? 'Update' : 'Create Garment'}
              </button>
              <button onClick={resetForm} className="px-5 py-2 text-gray-600 text-sm hover:text-black transition">
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Garments List */}
        {garments.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-xl p-12 text-center">
            <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-black mb-2">No garments yet</h3>
            <p className="text-gray-500 text-sm mb-6">Add your first garment to start using virtual try-on</p>
            <button
              onClick={() => { resetForm(); setShowForm(true); }}
              className="px-5 py-2.5 bg-black text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition"
            >
              + Add Your First Garment
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {garments.map((g) => (
              <div key={g.id} className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-base font-semibold text-black">{g.name}</h3>
                    <div className="flex items-center gap-3 mt-1">
                      {g.category && (
                        <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                          {g.category}
                        </span>
                      )}
                      <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                        {g.fit_type || 'regular'}
                      </span>
                      {g.shopify_product_id && (
                        <span className="text-xs text-gray-400 font-mono">
                          {g.shopify_product_id}
                        </span>
                      )}
                      {!g.shopify_product_id && (
                        <span className="text-xs text-amber-600">No product linked</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={async () => {
                        setSyncingId(g.id);
                        try { await garmentApi.sync(g.id); if (brandId) await loadGarments(brandId); } catch {}
                        setSyncingId(null);
                      }}
                      disabled={syncingId === g.id}
                      className="text-xs text-blue-500 hover:text-blue-700 transition px-2 py-1"
                    >
                      {syncingId === g.id ? 'Syncing...' : 'Sync Files'}
                    </button>
                    <button onClick={() => startEdit(g)} className="text-xs text-gray-500 hover:text-black transition px-2 py-1">
                      Edit
                    </button>
                    <button onClick={() => handleDelete(g.id)} className="text-xs text-red-400 hover:text-red-600 transition px-2 py-1">
                      Delete
                    </button>
                  </div>
                </div>

                {/* Size GLB uploads */}
                <div className="border-t border-gray-100 pt-4">
                  <p className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">
                    3D Models ({sizeCount(g)}/{SIZES.length} sizes)
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {SIZES.map((size) => {
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
                              ? 'bg-green-50 border-green-200 text-green-700 hover:bg-green-100'
                              : 'bg-white border-gray-200 text-gray-500 hover:border-black hover:text-black'}
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
                  <p className="text-xs text-gray-400 mt-2">Click a size to upload or replace a .glb file</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
