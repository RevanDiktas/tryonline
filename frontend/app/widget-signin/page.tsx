'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { login, getCurrentUser } from '@/lib/supabase-auth';

const SUPABASE_CONFIGURED =
  typeof process.env.NEXT_PUBLIC_SUPABASE_URL === 'string' &&
  process.env.NEXT_PUBLIC_SUPABASE_URL?.length > 0 &&
  typeof process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY === 'string' &&
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.length > 0;

/**
 * Sign-in for the TryOn widget.
 * - If opened in iframe with ?return=<widget URL>: after sign-in, redirect iframe to return URL + user_id (stays on product page).
 * - If opened in popup (window.opener): after sign-in, post user_id to opener and close.
 */
export default function WidgetSignInPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnUrl = searchParams.get('return');

  const [formData, setFormData] = useState({ email: '', password: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(true);

  const isPopup = typeof window !== 'undefined' && !!window.opener;
  const isIframeReturn = typeof window !== 'undefined' && !!returnUrl;

  useEffect(() => {
    const run = async () => {
      if (!SUPABASE_CONFIGURED) {
        setChecking(false);
        return;
      }
      try {
        const user = await getCurrentUser();
        if (user) {
          if (isPopup && window.opener) {
            try {
              window.opener.postMessage({ type: 'TRYON_USER_ID', user_id: user.id }, '*');
              setTimeout(() => window.close(), 150);
            } catch (_) {
              window.close();
            }
            return;
          }
          if (returnUrl) {
            const sep = returnUrl.includes('?') ? '&' : '?';
            window.location.href = returnUrl + sep + 'user_id=' + encodeURIComponent(user.id);
            return;
          }
          router.push('/dashboard');
          return;
        }
      } catch (_) {}
      setChecking(false);
    };
    run();
  }, [returnUrl, isPopup, router]);

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
      if (user && isPopup && window.opener) {
        try {
          window.opener.postMessage({ type: 'TRYON_USER_ID', user_id: user.id }, '*');
          setTimeout(() => window.close(), 150);
        } catch (_) {
          window.close();
        }
        return;
      }
      if (user && returnUrl) {
        const sep = returnUrl.includes('?') ? '&' : '?';
        window.location.href = returnUrl + sep + 'user_id=' + encodeURIComponent(user.id);
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

  if (!isPopup && !returnUrl) {
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
          <p className="text-sm text-gray-500 mt-1">Use your TryOn account</p>
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
