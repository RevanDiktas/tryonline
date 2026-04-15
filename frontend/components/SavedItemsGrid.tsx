'use client';

import { useEffect, useState, useCallback } from 'react';
import { api, type SavedItem } from '@/lib/api';

interface SavedItemsGridProps {
  listType: 'wishlist' | 'closet';
  dark: boolean;
  onTryOn: (item: SavedItem) => void;
}

function PlaceholderImage({ dark }: { dark: boolean }) {
  return (
    <div className={`w-full h-full flex items-center justify-center ${dark ? 'bg-white/5' : 'bg-slate-100'}`}>
      <svg className={`w-10 h-10 ${dark ? 'text-white/20' : 'text-slate-300'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    </div>
  );
}

function HeartIcon({ filled }: { filled: boolean }) {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill={filled ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth={2}>
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
    </svg>
  );
}

export default function SavedItemsGrid({ listType, dark, onTryOn }: SavedItemsGridProps) {
  const [items, setItems] = useState<SavedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [removingId, setRemovingId] = useState<string | null>(null);

  const loadItems = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getWishlist(listType);
      setItems(res.items || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load items');
    } finally {
      setLoading(false);
    }
  }, [listType]);

  useEffect(() => {
    loadItems();
  }, [loadItems]);

  const handleRemove = async (item: SavedItem) => {
    setRemovingId(item.id);
    try {
      await api.removeFromWishlist(item.id);
      setItems((prev) => prev.filter((i) => i.id !== item.id));
    } catch {
      // Silently fail; item stays in list
    } finally {
      setRemovingId(null);
    }
  };

  // Group items by store
  const grouped = items.reduce<Record<string, SavedItem[]>>((acc, item) => {
    const key = item.brand_name || item.shop_domain || 'Unknown Store';
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {});

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className={`w-6 h-6 border-2 rounded-full animate-spin ${dark ? 'border-white/20 border-t-white/70' : 'border-slate-200 border-t-slate-600'}`} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-16">
        <p className={`text-sm mb-3 ${dark ? 'text-red-400' : 'text-red-600'}`}>{error}</p>
        <button
          onClick={loadItems}
          className={`px-4 py-2 text-sm font-medium rounded-xl transition ${dark ? 'bg-white/10 text-white hover:bg-white/20' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
        >
          Retry
        </button>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-20">
        <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 ${dark ? 'bg-white/5' : 'bg-slate-100'}`}>
          {listType === 'wishlist' ? (
            <HeartIcon filled={false} />
          ) : (
            <svg className={`w-7 h-7 ${dark ? 'text-white/30' : 'text-slate-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
            </svg>
          )}
        </div>
        <h3 className={`text-lg font-semibold mb-1 ${dark ? 'text-white' : 'text-slate-900'}`}>
          {listType === 'wishlist' ? 'No items in your wishlist' : 'No items in your closet'}
        </h3>
        <p className={`text-sm max-w-sm mx-auto ${dark ? 'text-white/50' : 'text-slate-500'}`}>
          {listType === 'wishlist'
            ? 'Heart items when trying them on in-store to save them here. You can try them on anytime from your dashboard.'
            : 'Items you purchase through TryOn will appear here automatically.'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {Object.entries(grouped).map(([storeName, storeItems]) => (
        <div key={storeName}>
          <div className="flex items-center gap-2 mb-4">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${dark ? 'bg-white/10 text-white/70' : 'bg-slate-200 text-slate-600'}`}>
              {storeName.charAt(0).toUpperCase()}
            </div>
            <h4 className={`text-sm font-medium uppercase tracking-wider ${dark ? 'text-white/50' : 'text-slate-400'}`}>
              {storeName}
            </h4>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {storeItems.map((item) => (
              <div
                key={item.id}
                className={`group rounded-2xl overflow-hidden transition-all duration-200 hover:scale-[1.02] ${dark ? 'bg-white/[0.04] hover:bg-white/[0.07]' : 'bg-white shadow-sm hover:shadow-md'}`}
              >
                {/* Product Image */}
                <div className="aspect-square relative overflow-hidden">
                  {item.product_image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={item.product_image_url}
                      alt={item.product_name || 'Product'}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <PlaceholderImage dark={dark} />
                  )}

                  {/* Badges */}
                  <div className="absolute top-3 left-3 flex gap-2">
                    {listType === 'closet' && (
                      <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-green-500/90 text-white backdrop-blur-sm">
                        Purchased
                      </span>
                    )}
                  </div>

                  {/* Remove button (wishlist only) */}
                  {listType === 'wishlist' && (
                    <button
                      onClick={() => handleRemove(item)}
                      disabled={removingId === item.id}
                      className="absolute top-3 right-3 w-8 h-8 rounded-full bg-black/40 backdrop-blur-sm text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/60 disabled:opacity-50"
                      title="Remove from wishlist"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  )}
                </div>

                {/* Product Info */}
                <div className="p-3">
                  <p className={`text-xs font-semibold mb-0.5 truncate ${dark ? 'text-white' : 'text-slate-900'}`}>
                    {item.product_name || item.product_id}
                  </p>
                  <p className={`text-[11px] mb-2 ${dark ? 'text-white/40' : 'text-slate-400'}`}>
                    {item.brand_name || item.shop_domain}
                  </p>
                  {item.product_price != null && (
                    <p className={`text-xs font-bold mb-2 ${dark ? 'text-white' : 'text-slate-900'}`}>
                      {item.currency === 'EUR' ? '\u20AC' : item.currency === 'GBP' ? '\u00A3' : '$'}
                      {Number(item.product_price).toFixed(2)}
                    </p>
                  )}

                  <button
                    onClick={() => onTryOn(item)}
                    className={`w-full py-2 text-xs font-medium rounded-xl transition-all duration-200 ${dark ? 'bg-white text-black hover:bg-white/90' : 'bg-slate-900 text-white hover:bg-slate-800'}`}
                  >
                    Try On
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
