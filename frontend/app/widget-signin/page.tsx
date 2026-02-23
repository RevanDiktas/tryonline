'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { login, getCurrentUser } from '@/lib/supabase-auth';

/**
 * Sign-in for the TryOn widget (opened in a popup from the store).
 * When the user signs in, we post their user_id to the opener (the widget iframe)
 * so it can reload with user_id and show the GLB viewer with their avatar.
 */
export default function WidgetSignInPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(true);

  const isPopup = typeof window !== 'undefined' && !!window.opener;

  useEffect(() => {
    const run = async () => {
      if (!isPopup) {
        setChecking(false);
        return;
      }
      try {
        const user = await getCurrentUser();
        if (user) {
          try {
            window.opener?.postMessage({ type: 'TRYON_USER_ID', user_id: user.id }, '*');
          } catch (_) {}
          window.close();
          return;
        }
      } catch (_) {}
      setChecking(false);
    };
    run();
  }, [isPopup]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
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
        } catch (_) {}
        window.close();
        return;
      }
      if (user) {
        router.push('/dashboard');
      }
    } catch (err) {
      setErrors({ form: 'Something went wrong. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  if (!isPopup) {
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
            <p className="text-red-600 text-sm">{errors.form}</p>
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
          After signing in, this window will close and the try-on will open.
        </p>
      </div>
    </div>
  );
}
