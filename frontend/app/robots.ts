import type { MetadataRoute } from 'next';
import { SITE_URL } from '@/lib/seo';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      // Signed-in and embedded surfaces: dashboards, the API, the Shopify admin shell, the
      // storefront embeds and the auth hand-offs. Nothing there is meant to be found by search.
      disallow: ['/brand', '/dashboard', '/api', '/app', '/embed', '/auth', '/onboarding', '/widget-signin', '/widget-config'],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
