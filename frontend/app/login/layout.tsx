import { pageMetadata } from '@/lib/seo';

export const metadata = pageMetadata(
  '/login',
  'Sign in',
  'Sign in to TryOn: your fit passport, or your brand dashboard.',
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
