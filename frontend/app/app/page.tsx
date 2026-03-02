'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { getCurrentUser } from '@/lib/supabase-auth';

/** Backend (Railway) base URL — Shopify OAuth and session live here, not on Vercel. */
const getApiBase = () => (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/$/, '');

/**
 * Embedded Shopify app — onboarding entry.
 * Open from Shopify Admin → Apps → Tryon.
 * When no session: redirects to backend OAuth; after OAuth, Shopify redirects back here.
 * Once store is connected: checks if brand is logged in and routes accordingly.
 */
function AppPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const shop = searchParams.get('shop') ?? '';
  const host = searchParams.get('host') ?? '';
  const error = searchParams.get('error') ?? '';
  const [status, setStatus] = useState<'loading' | 'ready' | 'redirecting' | 'completing'>('loading');

  const code = searchParams.get('code') ?? '';
  const hmac = searchParams.get('hmac') ?? '';
  const state = searchParams.get('state') ?? '';

  useEffect(() => {
    if (code && shop && hmac && state) {
      setStatus('completing');
      const apiBase = getApiBase();
      fetch(`${apiBase}/api/shopify/complete-install`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, shop, hmac, state }),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.ok) {
            if (typeof window !== 'undefined') {
              window.history.replaceState({}, '', `${window.location.pathname}?shop=${encodeURIComponent(shop)}`);
              window.location.reload();
            }
          } else {
            setStatus('ready');
            window.history.replaceState({}, '', `${window.location.pathname}?shop=${encodeURIComponent(shop)}&error=${data.error || 'complete_failed'}`);
            window.location.reload();
          }
        })
        .catch(() => {
          setStatus('ready');
          window.history.replaceState({}, '', `${window.location.pathname}?shop=${encodeURIComponent(shop)}&error=complete_failed`);
          window.location.reload();
        });
      return;
    }

    if (!shop) {
      setStatus('ready');
      return;
    }
    const apiBase = getApiBase();
    const authUrl = apiBase ? `${apiBase}/api/shopify/auth?shop=${encodeURIComponent(shop)}` : '';

    if (!apiBase) {
      setStatus('redirecting');
      return;
    }
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    fetch(`${apiBase}/api/shopify/session?shop=${encodeURIComponent(shop)}`, { signal: controller.signal })
      .then((res) => {
        clearTimeout(timeout);
        if (res.ok) {
          setStatus('ready');
          return;
        }
        setStatus('redirecting');
        if (typeof window !== 'undefined' && window.top) {
          window.top.location.href = authUrl;
        }
      })
      .catch(() => {
        clearTimeout(timeout);
        setStatus('redirecting');
        if (typeof window !== 'undefined' && window.top) {
          window.top.location.href = authUrl;
        }
      });
  }, [shop, code, hmac, state]);

  // Once store is connected (status=ready), check auth and route
  useEffect(() => {
    if (status !== 'ready' || !shop) return;
    getCurrentUser()
      .then((user) => {
        if (user && user.user_type === 'brand') {
          router.push('/brand');
        } else if (user) {
          // Logged in but not a brand — go to brand signup
          router.push(`/signup?type=brand&shop=${encodeURIComponent(shop)}`);
        } else {
          // Not logged in — go to login (they may already have an account)
          router.push(`/login?redirect=/brand&shop=${encodeURIComponent(shop)}`);
        }
      })
      .catch(() => {
        router.push(`/login?redirect=/brand&shop=${encodeURIComponent(shop)}`);
      });
  }, [status, shop, router]);

  if (status === 'redirecting') {
    const apiBase = getApiBase();
    const authUrl = apiBase && shop ? `${apiBase}/api/shopify/auth?shop=${encodeURIComponent(shop)}` : '';
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-900 p-6 gap-5">
        {!authUrl ? (
          <p className="text-amber-600 dark:text-amber-400 text-center max-w-md">
            Backend URL is not set. Add <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded">NEXT_PUBLIC_API_URL</code> in Vercel to your Railway backend URL (e.g. https://heroic-celebration-production-9f72.up.railway.app), then redeploy.
          </p>
        ) : (
          <>
            <p className="text-gray-600 dark:text-gray-400 text-center">
              Complete install to connect your store. Click the button below (required when the app opens inside Shopify).
            </p>
            <a
              href={authUrl}
              target="_top"
              rel="noopener noreferrer"
              className="px-6 py-3 bg-gray-900 text-white rounded-md font-medium hover:opacity-90 text-center"
            >
              Complete install
            </a>
          </>
        )}
      </div>
    );
  }

  if (status === 'completing') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-6">
        <p className="text-gray-600 dark:text-gray-400">Completing install…</p>
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

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-6">
      <p className="text-gray-600 dark:text-gray-400">Setting up your account…</p>
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
