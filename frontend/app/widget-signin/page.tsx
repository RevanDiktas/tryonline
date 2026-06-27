'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { login, getCurrentUser, signInWithSocial } from '@/lib/supabase-auth';

const SUPABASE_CONFIGURED =
  typeof process.env.NEXT_PUBLIC_SUPABASE_URL === 'string' &&
  process.env.NEXT_PUBLIC_SUPABASE_URL?.length > 0 &&
  typeof process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY === 'string' &&
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.length > 0;

/**
 * Sign-in for the Tryon widget.
 * - If opened in iframe with ?return=<widget URL>: after sign-in, redirect iframe to return URL + user_id (stays on product page).
 * - If opened in popup (window.opener): after sign-in, post user_id to opener and close.
 */
export default function WidgetSignInPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnUrl = searchParams.get('return');
  const showForm = searchParams.get('show_form') === '1';
  const providerParam = searchParams.get('provider') as 'google' | 'apple' | null;
  const widgetState = searchParams.get('widget_state');

  const [formData, setFormData] = useState({ email: '', password: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [socialLoading, setSocialLoading] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);

  const isPopup = typeof window !== 'undefined' && !!window.opener;
  const isIframeReturn = typeof window !== 'undefined' && !!returnUrl;

  const completeWidgetState = async (userId: string, displayName: string) => {
    if (!widgetState) return;
    try {
      await fetch(`/api/auth/widget-state/${widgetState}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, display_name: displayName }),
      });
    } catch (_) { /* best-effort */ }
  };

  const handleSocialLogin = async (provider: 'google' | 'apple') => {
    setSocialLoading(provider);
    setErrors({});
    const { url, error } = await signInWithSocial(provider, {
      widgetReturn: returnUrl || undefined,
      widgetState: widgetState || undefined,
    });
    if (error || !url) {
      setErrors({ form: error || 'Failed to start sign-in' });
      setSocialLoading(null);
      return;
    }
    window.location.href = url;
  };

  useEffect(() => {
    const run = async () => {
      if (!SUPABASE_CONFIGURED) {
        setChecking(false);
        return;
      }
      if (showForm) {
        setChecking(false);
        return;
      }
      try {
        const user = await getCurrentUser();
        if (user) {
          const displayName = user.name || user.email?.split('@')[0] || 'User';

          if (widgetState) {
            await completeWidgetState(user.id, displayName);
            setTimeout(() => { try { window.close(); } catch (_) {} }, 400);
            return;
          }
          if (isPopup && window.opener) {
            try {
              window.opener.postMessage({ type: 'TRYON_USER_ID', user_id: user.id, display_name: displayName }, '*');
              setTimeout(() => window.close(), 150);
            } catch (_) {
              window.close();
            }
            return;
          }
          if (returnUrl) {
            const sep = returnUrl.includes('?') ? '&' : '?';
            window.location.href = returnUrl + sep + 'user_id=' + encodeURIComponent(user.id) + '&display_name=' + encodeURIComponent(displayName);
            return;
          }
          router.push('/dashboard');
          return;
        }
      } catch (_) {}
      // Auto-trigger social login if provider param is set
      if (providerParam === 'google' || providerParam === 'apple') {
        handleSocialLogin(providerParam);
        return;
      }
      setChecking(false);
    };
    run();
  }, [returnUrl, isPopup, router, showForm, providerParam]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!SUPABASE_CONFIGURED) {
      setErrors({ form: 'Sign-in is not configured. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in Vercel.' });
      return;
    }
    if (!formData.email.trim() || !formData.password) {
      setErrors({ form: 'Email and password are required' });
      return;
    }
    setLoading(true);
    setErrors({});
    try {
      const { user, error } = await login(formData.email, formData.password);
      if (error) {
        setErrors({ form: error });
        setLoading(false);
        return;
      }
      if (user && widgetState) {
        const displayName = user.name || user.email?.split('@')[0] || 'User';
        await completeWidgetState(user.id, displayName);
        setTimeout(() => { try { window.close(); } catch (_) {} }, 400);
        return;
      }
      if (user && isPopup && window.opener) {
        const displayName = user.name || user.email?.split('@')[0] || 'User';
        try {
          window.opener.postMessage({ type: 'TRYON_USER_ID', user_id: user.id, display_name: displayName }, '*');
          setTimeout(() => window.close(), 150);
        } catch (_) {
          window.close();
        }
        return;
      }
      if (user && returnUrl) {
        const displayName = user.name || user.email?.split('@')[0] || 'User';
        const sep = returnUrl.includes('?') ? '&' : '?';
        window.location.href = returnUrl + sep + 'user_id=' + encodeURIComponent(user.id) + '&display_name=' + encodeURIComponent(displayName);
        return;
      }
      if (user) {
        router.push('/dashboard');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Something went wrong. Please try again.';
      setErrors({ form: msg });
    } finally {
      setLoading(false);
    }
  };

  if (!SUPABASE_CONFIGURED) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center p-4">
        <div className="w-full max-w-sm text-center">
          <p className="text-red-600 font-medium mb-2">Sign-in not configured</p>
          <p className="text-gray-600 text-sm mb-4">
            Set <code className="bg-gray-100 px-1 rounded">NEXT_PUBLIC_SUPABASE_URL</code> and{' '}
            <code className="bg-gray-100 px-1 rounded">NEXT_PUBLIC_SUPABASE_ANON_KEY</code> in your Vercel project environment variables, then redeploy.
          </p>
          <a href="/login" className="text-black font-medium underline">Go to Sign In</a>
        </div>
      </div>
    );
  }

  if (!isPopup && !returnUrl && !widgetState) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center p-4">
        <div className="text-center">
          <p className="text-gray-600 mb-4">This page is for signing in from the Try On widget.</p>
          <a href="/login" className="text-black font-medium underline">Go to Sign In</a>
        </div>
      </div>
    );
  }

  if (checking) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center p-4">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-6">
          <p className="text-lg font-semibold text-black">Sign in to Try On</p>
          <p className="text-sm text-gray-500 mt-1">Use your Tryon account</p>
        </div>

        {/* Social login buttons */}
        <div className="space-y-2 mb-4">
          <button
            onClick={() => handleSocialLogin('google')}
            disabled={!!socialLoading}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 border border-gray-200 rounded-lg bg-white text-gray-700 font-medium text-sm hover:bg-gray-50 disabled:opacity-50"
          >
            <svg width="18" height="18" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
            {socialLoading === 'google' ? 'Redirecting...' : 'Continue with Google'}
          </button>
          <button
            onClick={() => handleSocialLogin('apple')}
            disabled={!!socialLoading}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-black text-white font-medium text-sm hover:bg-gray-800 disabled:opacity-50"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.48-3.24 0-1.44.62-2.2.44-3.06-.4C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z"/></svg>
            {socialLoading === 'apple' ? 'Redirecting...' : 'Continue with Apple'}
          </button>
        </div>

        <div className="flex items-center gap-3 mb-4">
          <div className="flex-1 border-t border-gray-200" />
          <span className="text-xs text-gray-400 uppercase tracking-wide">or</span>
          <div className="flex-1 border-t border-gray-200" />
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-black focus:outline-none focus:ring-2 focus:ring-black"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              required
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-black focus:outline-none focus:ring-2 focus:ring-black"
            />
          </div>
          {errors.form && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3">
              <p className="text-red-700 text-sm font-medium">{errors.form}</p>
              <p className="text-red-600 text-xs mt-1">Check email/password, or Supabase Auth → URL Configuration (Redirect URLs).</p>
            </div>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-black text-white font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
        <p className="text-center text-gray-500 text-xs mt-4">
          After signing in, the try-on will open.
        </p>
      </div>
    </div>
  );
}
