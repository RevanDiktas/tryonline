'use client';

import { useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';

const STORAGE_KEY = 'tryon_shop_context';

function isMyShopifyHost(s: string | null | undefined): s is string {
  return Boolean(s?.includes('.myshopify.com'));
}

/**
 * Stable shop hostname for embedded admin: query ?shop= → sessionStorage → optional
 * shopify_domain from /api/brand/me (pass extraShop when brand row loads).
 * Without this, client navigations drop ?shop= and OAuth uses primary SHOPIFY_CLIENT_ID.
 */
export function useResolvedShopifyShop(extraShop?: string | null): string | null {
  const searchParams = useSearchParams();
  const qp = searchParams.get('shop');
  const [resolved, setResolved] = useState<string | null>(() => {
    if (isMyShopifyHost(qp)) return qp.trim().toLowerCase();
    if (typeof window !== 'undefined') {
      const st = sessionStorage.getItem(STORAGE_KEY);
      if (isMyShopifyHost(st)) return st.trim().toLowerCase();
    }
    return null;
  });

  useEffect(() => {
    if (isMyShopifyHost(qp)) {
      const s = qp.trim().toLowerCase();
      sessionStorage.setItem(STORAGE_KEY, s);
      setResolved(s);
      return;
    }
    if (typeof window !== 'undefined') {
      const st = sessionStorage.getItem(STORAGE_KEY);
      if (isMyShopifyHost(st)) {
        setResolved((prev) => prev || st!.trim().toLowerCase());
      }
    }
  }, [qp]);

  useEffect(() => {
    if (!isMyShopifyHost(extraShop)) return;
    const s = extraShop.trim().toLowerCase();
    sessionStorage.setItem(STORAGE_KEY, s);
    setResolved((prev) => prev || s);
  }, [extraShop]);

  return resolved;
}
