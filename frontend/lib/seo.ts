import type { Metadata } from 'next';

export const SITE_URL = 'https://tryon.global';
export const SITE_NAME = 'Tryon';
export const DEFAULT_TITLE = 'Tryon: the operating system for fashion';
export const DEFAULT_DESCRIPTION =
  'The intelligence layer between consumer, brand and factory. Size recommendation, 3D try-on, fit intelligence and production, built on the bodies that buy. Amsterdam.';

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
