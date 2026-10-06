import type { NavLinkSpec } from './SharedNav';

/** The marketing nav, the same on every public page. Pass the current path to mark it active. */
export function siteLinks(active?: string): NavLinkSpec[] {
  return [
    { label: 'Product', href: '/product' },
    { label: 'Pricing', href: '/pricing' },
    { label: 'Demo', href: '/demo' },
    { label: 'Book a call', href: '/book' },
  ].map((l) => ({ ...l, active: l.href === active }));
}

/** Footer links, the same on every public page. */
export const FOOTER_LINKS = [
  { label: 'Product', href: '/product' },
  { label: 'Pricing', href: '/pricing' },
  { label: 'Demo', href: '/demo' },
  { label: 'Start free', href: '/start' },
  { label: 'Sign in', href: '/login' },
  { label: 'Privacy', href: '/privacy' },
];
