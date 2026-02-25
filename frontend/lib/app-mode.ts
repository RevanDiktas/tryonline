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

export function isShopifyMode(): boolean {
  return getAppMode() === 'shopify';
}
