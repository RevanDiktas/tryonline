import { pageMetadata } from '@/lib/seo';

export const metadata = pageMetadata(
  '/start',
  'Start free',
  'Get TryOn on your Shopify store. Find my size is free on every product; paid plans start with a 30-day trial.',
);

export default function StartLayout({ children }: { children: React.ReactNode }) {
  return children;
}
