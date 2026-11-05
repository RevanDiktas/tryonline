import type { Metadata } from 'next';

export const SITE_URL = 'https://tryon.global';
export const SITE_NAME = 'Tryon';
export const DEFAULT_TITLE = 'Tryon: size and body data for fashion brands';
export const DEFAULT_DESCRIPTION =
  'A size button on every product. Your customers\' measurements, every month. The next run graded to them. Built in Amsterdam, live with La Fam.';

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
