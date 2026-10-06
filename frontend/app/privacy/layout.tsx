import { pageMetadata } from '@/lib/seo';

export const metadata = pageMetadata(
  '/privacy',
  'Privacy',
  'How TryOn collects, uses and protects shopper and brand data.',
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
