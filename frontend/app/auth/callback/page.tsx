'use client';

/**
 * OAuth return URL for Supabase (Google / Apple).
 *
 * With implicit flow, Supabase redirects here with tokens in the URL fragment:
 *   /auth/callback#access_token=...&refresh_token=...
 *
 * The shared Supabase client (detectSessionInUrl: true) auto-parses the
 * fragment and sets up the session. This page just waits for that, then
 * routes the user to dashboard or onboarding.
 */
import { Suspense, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { ensureUserProfile, isProfileComplete, hasFitPassport, getSession } from '@/lib/supabase-auth';

export const dynamic = 'force-dynamic';

function AuthCallbackInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [message, setMessage] = useState('Signing you in\u2026');
  const [isError, setIsError] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const routeAfterAuth = async () => {
      const user = await ensureUserProfile();
      if (!user) {
        if (!cancelled) { setIsError(true); setMessage('Could not complete sign-in.'); }
        return;
      }

      // If the user came from the widget sign-in flow
      const widgetReturn = searchParams.get('widget_return');
      if (widgetReturn) {
        const displayName = user.name || user.email?.split('@')[0] || 'User';

        // When opened as a popup (social login from widget iframe),
        // post user_id back to the opener and close the popup.
        if (window.opener) {
          try {
            window.opener.postMessage(
              { type: 'TRYON_USER_ID', user_id: user.id, display_name: displayName },
              '*',
            );
          } catch (_) { /* cross-origin opener — fall through to redirect */ }
          setTimeout(() => window.close(), 200);
          return;
        }

        const sep = widgetReturn.includes('?') ? '&' : '?';
        window.location.href = widgetReturn + sep + 'user_id=' + encodeURIComponent(user.id) + '&display_name=' + encodeURIComponent(displayName);
        return;
      }

      if (!isProfileComplete(user)) {
        router.replace('/auth/complete-profile');
        return;
      }
      const hasFP = await hasFitPassport(user.id);
      if (hasFP) {
        router.replace(user.user_type === 'brand' ? '/brand' : '/dashboard');
      } else {
        router.replace('/onboarding');
      }
    };

    const finish = async () => {
      const href = typeof window !== 'undefined' ? window.location.href : '';
      const url = new URL(href || 'https://tryon.global/');

      // Check for OAuth error in query string
      const oauthError = url.searchParams.get('error') || searchParams.get('error');
      if (oauthError) {
        const desc = url.searchParams.get('error_description') || searchParams.get('error_description');
        if (!cancelled) {
          setIsError(true);
          setMessage(desc ? decodeURIComponent(desc.replace(/\+/g, ' ')) : oauthError);
        }
        return;
      }

      // Implicit flow: tokens are in the URL fragment.
      // The Supabase client with detectSessionInUrl: true should have already
      // parsed them. Give it a moment, then check for a valid session.
      // We poll a few times because the client processes the fragment async.
      for (let attempt = 0; attempt < 10; attempt++) {
        const { data: { session } } = await getSession();
        if (cancelled) return;
        if (session) {
          await routeAfterAuth();
          return;
        }
        await new Promise(r => setTimeout(r, 300));
      }

      if (!cancelled) {
        setIsError(true);
        setMessage(
          'Sign-in could not be completed. Please try again from the login page.',
        );
      }
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
