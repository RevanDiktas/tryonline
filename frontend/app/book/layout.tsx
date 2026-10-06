import { pageMetadata } from '@/lib/seo';

export const metadata = pageMetadata(
  '/book',
  'Book a call',
  'Book a call about size recommendation and 3D virtual try-on for your Shopify store.',
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
