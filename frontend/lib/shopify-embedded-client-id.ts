/**
 * Client ID for the Shopify app embedded in admin (App Bridge `shopify-api-key`).
 *
 * Vercel: set **NEXT_PUBLIC_SHOPIFY_EMBEDDED_CLIENT_ID** so it is not confused with
 * Railway’s server-only **SHOPIFY_CLIENT_ID** / **SHOPIFY_CLIENT_ID_PILOT**.
 *
 * Legacy: **NEXT_PUBLIC_SHOPIFY_CLIENT_ID** is still read if the new var is unset.
 */
export const SHOPIFY_EMBEDDED_CLIENT_ID =
  process.env.NEXT_PUBLIC_SHOPIFY_EMBEDDED_CLIENT_ID?.trim() ||
  process.env.NEXT_PUBLIC_SHOPIFY_CLIENT_ID?.trim() ||
  'ec47b40d60204a8d7cf80aa50e313d19';

/**
 * Per-shop dedicated apps (a brand on its OWN Shopify app) map their *.myshopify.com host to
 * that app's client_id via **NEXT_PUBLIC_SHOPIFY_EMBEDDED_CLIENT_IDS** (JSON), e.g.
 *   {"la-fam-ams.myshopify.com":"9ef2f50e267d2339dfd39332f85096ce"}
 * Client IDs are public (they appear in OAuth URLs), so mapping them here exposes no secret.
 */
function shopClientIdMap(): Record<string, string> {
  const raw = process.env.NEXT_PUBLIC_SHOPIFY_EMBEDDED_CLIENT_IDS?.trim();
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw);
    const out: Record<string, string> = {};
    if (parsed && typeof parsed === 'object') {
      for (const [shop, id] of Object.entries(parsed)) {
        if (typeof id === 'string') out[shop.trim().toLowerCase()] = id.trim();
      }
    }
    return out;
  } catch {
    return {};
  }
}

/** App Bridge client_id for a shop: its dedicated app if mapped, else the default (pilot/public) app. */
export function embeddedClientIdForShop(shop?: string | null): string {
  const s = (shop || '').trim().toLowerCase();
  if (s) {
    const mapped = shopClientIdMap()[s];
    if (mapped) return mapped;
  }
  return SHOPIFY_EMBEDDED_CLIENT_ID;
}
