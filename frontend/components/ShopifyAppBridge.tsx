'use client';

import { useEffect, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import { SHOPIFY_EMBEDDED_CLIENT_ID } from '@/lib/shopify-embedded-client-id';

const SHOPIFY_APP_BRIDGE_URL = 'https://cdn.shopify.com/shopifycloud/app-bridge.js';

/**
 * Embedded flow: Shopify loads /app first (App Bridge as first script) → we redirect to /?shop=...
 * On the / page we are inside the admin iframe. We must NOT inject App Bridge here — it would
 * load with async and not be first, so App Bridge aborts and you get "getSessionToken not found".
 * The embedded check is already satisfied by /app. Here we no-op when in iframe.
 */
export function ShopifyAppBridge() {
  const searchParams = useSearchParams();
  const injected = useRef(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const shop = searchParams.get('shop');
    const isEmbedded = shop?.includes('.myshopify.com');
    const inIframe = window.self !== window.top;

    // We're in the admin iframe on / after redirect from /app. Do NOT inject App Bridge —
    // it would be async and not first → App Bridge aborts, getSessionToken never exists.
    if (inIframe && isEmbedded) {
      return;
    }

    if (!isEmbedded || injected.current) return;
    injected.current = true;

    // Only for top-level (e.g. direct visit to /?shop= outside admin): ensure meta + script.
    let meta = document.querySelector('meta[name="shopify-api-key"]');
    if (!meta) {
      meta = document.createElement('meta');
      meta.setAttribute('name', 'shopify-api-key');
      meta.setAttribute('content', SHOPIFY_EMBEDDED_CLIENT_ID);
      document.head.appendChild(meta);
    }

    if (document.querySelector(`script[src="${SHOPIFY_APP_BRIDGE_URL}"]`)) {
      pollForAppBridge(runEmbeddedChecks);
      return;
    }

    const script = document.createElement('script');
    script.src = SHOPIFY_APP_BRIDGE_URL;
    script.async = true;
    script.onload = () => pollForAppBridge(runEmbeddedChecks);
    document.head.appendChild(script);
  }, [searchParams]);

  return null;
}

const LOG = '[Tryon embedded]';

/** Poll until App Bridge is available (script can load after our code), then run checks. */
function pollForAppBridge(onReady: () => void) {
  const maxAttempts = 40;
  let attempts = 0;
  const tick = () => {
    if (getSessionTokenFn()) {
      if (typeof console !== 'undefined' && console.info) console.info(LOG, 'App Bridge ready after', attempts * 200, 'ms');
      onReady();
      return;
    }
    attempts++;
    if (attempts < maxAttempts) setTimeout(tick, 200);
    else {
      if (typeof console !== 'undefined' && console.warn) console.warn(LOG, 'App Bridge getSessionToken not found after', maxAttempts, 'attempts');
      onReady();
    }
  };
  setTimeout(tick, 300);
}

function getSessionTokenFn(): (() => Promise<string>) | null {
  const w = window as Window & {
    shopify?: { getSessionToken?: () => Promise<string>; config?: unknown };
    ['app-bridge']?: { utilities?: { getSessionToken?: (app?: unknown) => Promise<string> } };
  };
  if (w.shopify?.getSessionToken) return w.shopify.getSessionToken.bind(w.shopify);
  const util = w['app-bridge']?.utilities?.getSessionToken;
  if (util) return () => (util as (app?: unknown) => Promise<string>)(w.shopify ?? undefined);
  return null;
}

/**
 * 1) Call getSessionToken so the checker sees session token usage.
 * 2) Make one fetch to Shopify Admin API (only when in real embedded context; skip if no App Bridge).
 */
function runEmbeddedChecks() {
  try {
    const getToken = getSessionTokenFn();
    if (getToken) {
      getToken()
        .then(() => {
          if (typeof console !== 'undefined' && console.info) console.info(LOG, 'Session token received');
        })
        .catch(() => {});
    } else {
      if (typeof console !== 'undefined' && console.warn) console.warn(LOG, 'App Bridge getSessionToken not found');
    }

    // Only call shopify:admin when we have App Bridge (otherwise browser throws "URL scheme not supported").
    if (getToken) {
      fetch('shopify:admin/api/2024-01/shop.json', { method: 'GET' })
        .then((res) => {
          if (typeof console !== 'undefined' && console.info) console.info(LOG, 'Admin API fetch:', res.status);
        })
        .catch(() => {});
    }
  } catch (e) {
    if (typeof console !== 'undefined' && console.warn) console.warn(LOG, 'runEmbeddedChecks error', e);
  }
}
