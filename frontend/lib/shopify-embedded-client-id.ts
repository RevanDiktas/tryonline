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
