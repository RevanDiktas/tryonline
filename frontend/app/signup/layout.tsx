import { pageMetadata } from '@/lib/seo';

export const metadata = pageMetadata(
  '/signup',
  'Create your fit passport',
  'Create a TryOn account: one photo gives you a measured size and a photoreal 3D avatar, on every TryOn store.',
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
