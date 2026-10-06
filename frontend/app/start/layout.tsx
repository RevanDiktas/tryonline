import { pageMetadata } from '@/lib/seo';

export const metadata = pageMetadata(
  '/start',
  'Start your free trial',
  'Get TryOn on your Shopify store: Find my size on every product, 3D try-on where you want it. Every plan starts with a 30-day free trial.',
);

export default function StartLayout({ children }: { children: React.ReactNode }) {
  return children;
}
