import { pageMetadata } from '@/lib/seo';

export const metadata = pageMetadata(
  '/product',
  'Find my size and 3D try-on for Shopify',
  'One button for your Shopify store. Shoppers get their size on every product in 30 seconds, with a % match for every size, and try your clothes on their own 3D body.',
);

export default function ProductLayout({ children }: { children: React.ReactNode }) {
  return children;
}
