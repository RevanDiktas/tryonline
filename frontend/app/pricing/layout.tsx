import { pageMetadata } from '@/lib/seo';

export const metadata = pageMetadata(
  '/pricing',
  'Pricing',
  'Size recommendation from €199 a month. The operating system by engagement, from a six-week diagnostic.',
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
