import type { Metadata } from 'next';

export const SITE_URL = 'https://tryon.global';
export const SITE_NAME = 'TryOn';
export const DEFAULT_TITLE = 'TryOn: know who you are dressing';
export const DEFAULT_DESCRIPTION =
  'Fit intelligence for fashion brands. Shoppers get their size in 30 seconds on every product; you see what your customers\' bodies actually look like, and we make the clothes to fit them. One button for Shopify stores.';

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
