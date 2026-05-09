/**
 * APP_MODE controls which flows are visible:
 *   "website"  — both shopper and brand signup/login (default)
 *   "shopify"  — brand-only signup/login (for the Shopify app deployment)
 */
export type AppMode = 'website' | 'shopify';

export function getAppMode(): AppMode {
  const mode = process.env.NEXT_PUBLIC_APP_MODE ?? 'website';
  return mode === 'shopify' ? 'shopify' : 'website';
}

const SHOPIFY_HOSTS = new Set(['app.tryon.global']);

export function isShopifyMode(): boolean {
  if (getAppMode() === 'shopify') return true;
  // Runtime host detection: app.tryon.global is the dedicated Shopify-embedded
  // surface and must always render brand-only flows even when the build is
  // shared with the consumer site. Server-side render returns false on that
  // host (window is undefined); client hydration flips it to true.
  if (typeof window !== 'undefined' && SHOPIFY_HOSTS.has(window.location.hostname)) {
    return true;
  }
  return false;
}
