'use client';

import { useSearchParams } from 'next/navigation';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

/**
 * Shopify app URL is tryon.global/app. Redirect to the normal homepage (/) with the same
 * query string so ?shop=... is preserved. The root page shows only "Launch Your Brand" when shop is present.
 */
export default function AppRedirectPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const query = searchParams.toString();
    const target = query ? `/?${query}` : '/';
    router.replace(target);
  }, [router, searchParams]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-white">
      <p className="text-gray-500">Loading…</p>
    </div>
  );
}
