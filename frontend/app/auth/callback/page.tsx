'use client';

/**
 * OAuth return URL for Supabase (Google / Apple).
 * Handles both PKCE (?code=) and implicit (#access_token=) flows.
 * Uses the single shared Supabase client to avoid "Multiple GoTrueClient" errors.
 */
import { Suspense, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { exchangeCodeForSession, getCurrentUser, hasFitPassport, getSession } from '@/lib/supabase-auth';

export const dynamic = 'force-dynamic';

function AuthCallbackInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [message, setMessage] = useState('Signing you in\u2026');
  const [isError, setIsError] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const routeAfterAuth = async () => {
      const user = await getCurrentUser();
      if (!user) {
        if (!cancelled) { setIsError(true); setMessage('Could not complete sign-in.'); }
        return;
      }
      const hasFP = await hasFitPassport(user.id);
      if (hasFP) {
        router.replace(user.user_type === 'brand' ? '/brand' : '/dashboard');
      } else {
        router.replace('/signup?step=onboarding');
      }
    };

    const finish = async () => {
      const href = typeof window !== 'undefined' ? window.location.href : '';
      const url = new URL(href || 'https://tryon.global/');

      const oauthError = url.searchParams.get('error') || searchParams.get('error');
      if (oauthError) {
        const desc = url.searchParams.get('error_description') || searchParams.get('error_description');
        if (!cancelled) {
          setIsError(true);
          setMessage(desc ? decodeURIComponent(desc.replace(/\+/g, ' ')) : oauthError);
        }
        return;
      }

      // --- PKCE: code in query string ---
      const code = url.searchParams.get('code') || searchParams.get('code');
      if (code) {
        const { error } = await exchangeCodeForSession(code);
        if (cancelled) return;
        if (error) { setIsError(true); setMessage(error); return; }
        await routeAfterAuth();
        return;
      }

      // --- Implicit: tokens in URL fragment (#access_token=...&refresh_token=...) ---
      const hash = typeof window !== 'undefined' ? window.location.hash : '';
      if (hash && hash.includes('access_token')) {
        const { data: { session }, error } = await getSession();
        if (cancelled) return;
        if (error || !session) {
          setIsError(true);
          setMessage(error?.message || 'Session could not be established from URL tokens.');
          return;
        }
        await routeAfterAuth();
        return;
      }

      // --- Fallback: maybe Supabase already consumed the fragment before React rendered ---
      await new Promise(r => setTimeout(r, 600));
      const { data: { session } } = await getSession();
      if (cancelled) return;
      if (session) {
        await routeAfterAuth();
        return;
      }

      setIsError(true);
      setMessage(
        'No authorization code received. Make sure Supabase \u2192 URL Configuration includes https://tryon.global/auth/callback, then try again.',
      );
    };

    finish();
    return () => { cancelled = true; };
  }, [router, searchParams]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 bg-black">
      <p className={isError ? 'text-red-500' : 'text-white/60'}>{message}</p>
      {isError && (
        <Link href="/login" className="text-blue-400 underline">
          Back to login
        </Link>
      )}
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-black text-white/60">
          Loading\u2026
        </div>
      }
    >
      <AuthCallbackInner />
    </Suspense>
  );
}
