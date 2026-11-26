import { pageMetadata } from '@/lib/seo';

export const metadata = pageMetadata(
  '/product',
  'Products',
  'Size recommendation, 3D try-on, fit intelligence and the operating system that takes a design from your audience to the factory.',
);

export default function ProductLayout({ children }: { children: React.ReactNode }) {
  return children;
}
