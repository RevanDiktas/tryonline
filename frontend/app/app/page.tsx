'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';

/**
 * Embedded Shopify app — onboarding entry.
 * Open from Shopify Admin → Apps → Tryon.
 * When no session: redirects to backend OAuth; after OAuth, Shopify redirects back here.
 */
function AppPageContent() {
  const searchParams = useSearchParams();
  const shop = searchParams.get('shop') ?? '';
  const host = searchParams.get('host') ?? '';
  const error = searchParams.get('error') ?? '';
  const [status, setStatus] = useState<'loading' | 'ready' | 'redirecting'>('loading');

  useEffect(() => {
    if (!shop) {
      setStatus('ready');
      return;
    }
    // Check if we have a session for this shop (backend has access token)
    const apiBase = typeof window !== 'undefined' ? '' : (process.env.NEXT_PUBLIC_API_URL || '');
    fetch(`${apiBase}/api/shopify/session?shop=${encodeURIComponent(shop)}`)
      .then((res) => {
        if (res.ok) {
          setStatus('ready');
          return;
        }
        // No session: redirect to backend OAuth (breaks out of iframe)
        const authUrl = `${apiBase || window.location.origin}/api/shopify/auth?shop=${encodeURIComponent(shop)}`;
        setStatus('redirecting');
        if (typeof window !== 'undefined' && window.top) {
          window.top.location.href = authUrl;
        }
      })
      .catch(() => setStatus('ready'));
  }, [shop]);

  if (status === 'redirecting') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-6">
        <p className="text-gray-600 dark:text-gray-400">Redirecting to install…</p>
      </div>
    );
  }

  if (!shop) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-6">
        <div className="text-center text-gray-600 dark:text-gray-400">
          <p className="font-medium">Open this app from Shopify Admin</p>
          <p className="mt-2 text-sm">Apps → Tryon</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-6">
        <div className="text-center text-gray-600 dark:text-gray-400">
          <p className="font-medium">Something went wrong</p>
          <p className="mt-2 text-sm">Error: {error}</p>
        </div>
      </div>
    );
  }

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-6">
        <p className="text-gray-600 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-xl mx-auto">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
          Welcome to Try On
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Your store is connected. Next steps: add the Try On button and enable the cart embed (onboarding steps will go here).
        </p>
        <p className="mt-4 text-sm text-gray-500 dark:text-gray-500">
          Shop: {shop}
        </p>
      </div>
    </div>
  );
}

export default function AppPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <p className="text-gray-600 dark:text-gray-400">Loading…</p>
      </div>
    }>
      <AppPageContent />
    </Suspense>
  );
}
