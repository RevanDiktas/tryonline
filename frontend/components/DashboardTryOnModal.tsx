'use client';

import { useEffect, useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { api, type SavedItem } from '@/lib/api';
import type { FitPassport } from '@/lib/supabase-auth';

const TryOnViewer = dynamic(() => import('@/components/TryOnViewer'), { ssr: false });

interface DashboardTryOnModalProps {
  item: SavedItem;
  passport: FitPassport | null;
  dark: boolean;
  onClose: () => void;
}

export default function DashboardTryOnModal({ item, passport, dark, onClose }: DashboardTryOnModalProps) {
  const [garmentConfig, setGarmentConfig] = useState<{
    model_urls: Record<string, string>;
    size_chart: Record<string, Record<string, number>>;
    model_type?: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadConfig = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const config = await api.getProductTryonConfig(item.product_id, {
        shop: item.shop_domain,
      });
      setGarmentConfig(config);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load try-on config');
    } finally {
      setLoading(false);
    }
  }, [item.product_id, item.shop_domain]);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [onClose]);

  const avatarUrl = passport?.avatarUrl || passport?.avatar_url || undefined;
  const userMeasurements = passport
    ? {
        chest: passport.chest ?? 96,
        waist: passport.waist ?? 82,
        hips: passport.hips ?? 96,
        height: passport.height ?? 175,
      }
    : undefined;

  const productUrl = (() => {
    const domain = item.shop_domain?.replace(/\/$/, '');
    const handle = item.product_id;
    if (!domain || !handle) return undefined;
    const base = domain.startsWith('http') ? domain : `https://${domain}`;
    return `${base}/products/${handle}`;
  })();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className={`relative w-full max-w-5xl mx-4 rounded-2xl overflow-hidden shadow-2xl ${dark ? 'bg-zinc-900' : 'bg-white'}`} style={{ maxHeight: '90vh' }}>
        {/* Header */}
        <div className={`flex items-center justify-between px-6 py-4 border-b ${dark ? 'border-white/10' : 'border-slate-200'}`}>
          <div>
            <h3 className={`text-lg font-semibold ${dark ? 'text-white' : 'text-slate-900'}`}>
              {item.product_name || 'Try On'}
            </h3>
            <p className={`text-sm ${dark ? 'text-white/50' : 'text-slate-500'}`}>
              {item.brand_name || item.shop_domain}
            </p>
          </div>
          <button
            onClick={onClose}
            className={`w-10 h-10 rounded-full flex items-center justify-center transition ${dark ? 'hover:bg-white/10 text-white/70' : 'hover:bg-slate-100 text-slate-500'}`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div style={{ height: 'calc(90vh - 80px)' }}>
          {loading ? (
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <div className={`w-8 h-8 border-2 rounded-full animate-spin ${dark ? 'border-white/20 border-t-white/70' : 'border-slate-200 border-t-slate-600'}`} />
              <p className={`text-sm ${dark ? 'text-white/50' : 'text-slate-500'}`}>Loading try-on viewer...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <p className={`text-sm ${dark ? 'text-red-400' : 'text-red-600'}`}>{error}</p>
              <button
                onClick={loadConfig}
                className={`px-4 py-2 text-sm font-medium rounded-xl transition ${dark ? 'bg-white/10 text-white hover:bg-white/20' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
              >
                Retry
              </button>
            </div>
          ) : garmentConfig ? (
            <TryOnViewer
              avatarUrl={avatarUrl}
              garmentUrls={garmentConfig.model_urls}
              sizeChart={garmentConfig.size_chart as Record<string, { chest: number; waist: number; hips: number }>}
              userMeasurements={userMeasurements}
              brandName={item.brand_name || item.shop_domain}
              productName={item.product_name || undefined}
              preferredFit={(passport?.preferred_fit as 'slim' | 'regular' | 'loose') || 'regular'}
              theme={dark ? 'dark' : 'light'}
              productUrl={productUrl}
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <p className={`text-sm ${dark ? 'text-white/50' : 'text-slate-500'}`}>
                No try-on data available for this product yet.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
