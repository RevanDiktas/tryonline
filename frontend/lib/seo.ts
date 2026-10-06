import type { Metadata } from 'next';

export const SITE_URL = 'https://tryon.global';
export const SITE_NAME = 'TryOn';
export const DEFAULT_TITLE = 'TryOn: your size on every product, and 3D try-on';
export const DEFAULT_DESCRIPTION =
  'Find my size on every product, no account: seven quick questions and every size scored as a % match. Photoreal 3D virtual try-on where there is a 3D garment. One button for Shopify stores.';

/**
 * Metadata for one public page. Sets the canonical URL and the Open Graph / Twitter copy
 * per page: a canonical in the root layout would be inherited by every page that doesn't
 * set its own. The share image comes from app/opengraph-image.tsx for every page.
 */
export function pageMetadata(path: string, title: string, description: string): Metadata {
  const full = `${title} · ${SITE_NAME}`;
  return {
    title,
    description,
    alternates: { canonical: path },
    openGraph: { type: 'website', siteName: SITE_NAME, url: path, title: full, description },
    twitter: { card: 'summary_large_image', title: full, description },
  };
}
