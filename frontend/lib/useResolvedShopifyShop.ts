'use client';

import { useSearchParams } from 'next/navigation';
import { useEffect, useMemo } from 'react';

const STORAGE_KEY = 'tryon_shop_context';

function isMyShopifyHost(s: string | null | undefined): s is string {
  return Boolean(s?.includes('.myshopify.com'));
}

/**
 * Stable shop hostname for embedded admin.
 * Precedence: ?shop= (Shopify iframe) → shopify_domain from /api/brand/me (extraShop) → sessionStorage.
 * Important: extraShop must win over stale sessionStorage (e.g. prior dev-store context), otherwise
 * OAuth and /api/shopify/session run for the wrong *.myshopify.com.
 */
export function useResolvedShopifyShop(extraShop?: string | null): string | null {
  const searchParams = useSearchParams();
  const qp = searchParams.get('shop');

  const resolved = useMemo(() => {
    if (isMyShopifyHost(qp)) return qp.trim().toLowerCase();
    if (isMyShopifyHost(extraShop)) return extraShop.trim().toLowerCase();
    if (typeof window !== 'undefined') {
      const st = sessionStorage.getItem(STORAGE_KEY);
      if (isMyShopifyHost(st)) return st.trim().toLowerCase();
    }
    return null;
  }, [qp, extraShop]);

  useEffect(() => {
    if (resolved) sessionStorage.setItem(STORAGE_KEY, resolved);
  }, [resolved]);

  return resolved;
}
