'use client';

import { useEffect, useRef } from 'react';

/** OAuth must not run inside the admin iframe — accounts.shopify.com sets X-Frame-Options: deny. */
function navigateOAuthTopLevel(url: string): void {
  if (typeof window === 'undefined') return;
  if (window.self === window.top) {
    window.location.assign(url);
    return;
  }
  try {
    const opened = window.open(url, '_top', 'noopener,noreferrer');
    if (opened) {
      opened.opener = null;
      return;
    }
  } catch {
    /* fall through */
  }
  try {
    const a = document.createElement('a');
    a.href = url;
    a.target = '_top';
    a.rel = 'noopener noreferrer';
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  } catch {
    window.location.assign(url);
  }
}

/**
 * When the app loads inside Shopify admin (?shop=*.myshopify.com) but the backend
 * has no Admin API token yet (signup created the brand without OAuth), send the
 * merchant through /api/shopify/auth once so the OAuth callback can call
 * upsert_brand_for_shop and set shopify_access_token on the existing row.
 */
export type EnsureShopifyOAuthOptions = {
  /** When true, skip session check / redirect until brand context is loaded (avoids OAuth for stale sessionStorage shop). */
  pauseOAuth?: boolean;
};

export function useEnsureShopifyAdminOAuth(
  shop: string | null | undefined,
  oauthCallbackError: string | null | undefined,
  options?: EnsureShopifyOAuthOptions
): void {
  /** Avoid redirect loops for the same shop; allow OAuth again when `shop` changes (e.g. pilot vs primary domain). */
  const redirectIssuedForShop = useRef<string | null>(null);

  useEffect(() => {
    if (options?.pauseOAuth) return;
    const s = shop?.trim();
    if (!s || !s.includes('.myshopify.com')) return;
    if (oauthCallbackError) return;
    if (redirectIssuedForShop.current === s) return;

    let cancelled = false;

    (async () => {
      try {
        const res = await fetch(`/api/shopify/session?shop=${encodeURIComponent(s)}`, {
          credentials: 'same-origin',
        });
        if (cancelled) return;
        if (res.ok) return;

        if (res.status === 401) {
          redirectIssuedForShop.current = s;
          const url = `${window.location.origin}/api/shopify/auth?shop=${encodeURIComponent(s)}`;
          navigateOAuthTopLevel(url);
        }
      } catch {
        // network — ignore; user can refresh
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [shop, oauthCallbackError, options?.pauseOAuth]);
}
