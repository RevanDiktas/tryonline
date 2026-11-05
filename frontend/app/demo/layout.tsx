import { pageMetadata } from '@/lib/seo';

export const metadata = pageMetadata(
  '/demo',
  'Demo',
  'Try Tryon on a demo store: Find my size on a T-shirt, and 3D virtual try-on on a zip-up.',
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
