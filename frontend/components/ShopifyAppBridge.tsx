'use client';

import { useEffect, useRef } from 'react';
import { useSearchParams } from 'next/navigation';

const SHOPIFY_APP_BRIDGE_URL = 'https://cdn.shopify.com/shopifycloud/app-bridge.js';
const SHOPIFY_CLIENT_ID = process.env.NEXT_PUBLIC_SHOPIFY_CLIENT_ID || 'ec47b40d60204a8d7cf80aa50e313d19';

/**
 * When the app is embedded in Shopify Admin (?shop= & ?host= in URL), inject
 * App Bridge from Shopify's CDN and request a session token so Shopify's
 * "Controles ingesloten apps" (embedded app checks) can pass.
 */
export function ShopifyAppBridge() {
  const searchParams = useSearchParams();
  const injected = useRef(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const shop = searchParams.get('shop');
    const host = searchParams.get('host');
    const isEmbedded = shop?.includes('.myshopify.com');

    if (!isEmbedded || injected.current) return;
    injected.current = true;

    // Meta tag for App Bridge (required by Shopify CDN script)
    let meta = document.querySelector('meta[name="shopify-api-key"]');
    if (!meta) {
      meta = document.createElement('meta');
      meta.setAttribute('name', 'shopify-api-key');
      meta.setAttribute('content', SHOPIFY_CLIENT_ID);
      document.head.appendChild(meta);
    }

    // Load App Bridge from Shopify's CDN (required for "uses latest App Bridge" check)
    if (document.querySelector(`script[src="${SHOPIFY_APP_BRIDGE_URL}"]`)) {
      tryUseSessionToken();
      return;
    }

    const script = document.createElement('script');
    script.src = SHOPIFY_APP_BRIDGE_URL;
    script.async = true;
    script.onload = () => {
      tryUseSessionToken();
    };
    document.head.appendChild(script);
  }, [searchParams]);

  return null;
}

function tryUseSessionToken() {
  try {
    const w = window as Window & {
      shopify?: { getSessionToken?: () => Promise<string> };
      ['app-bridge']?: { utilities?: { getSessionToken?: (app: unknown) => Promise<string> } };
    };
    // App Bridge 3 CDN: global can be shopify or app-bridge
    if (w.shopify?.getSessionToken) {
      w.shopify.getSessionToken().catch(() => {});
      return;
    }
    if (w['app-bridge']?.utilities?.getSessionToken) {
      // Some versions need an app instance; try without first
      (w['app-bridge'].utilities.getSessionToken as (app?: unknown) => Promise<string>)().catch(() => {});
    }
  } catch {
    // Session token usage is best-effort for the automated check
  }
}
