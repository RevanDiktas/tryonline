'use client';

import { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { TryonLogo } from '@/components/TryonLogo';
import { useTheme } from '@/contexts/ThemeContext';
import { login, hasAvatarFiles, getCurrentUser, signInWithSocial } from '@/lib/supabase-auth';
import { isShopifyMode } from '@/lib/app-mode';

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { theme } = useTheme();
  const dark = theme === 'dark';
  const shopifyMode = isShopifyMode();
  const shopParam = searchParams.get('shop') ?? '';
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [socialLoading, setSocialLoading] = useState<string | null>(null);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email address';
    }
    if (!formData.password) newErrors.password = 'Password is required';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setLoading(true);
    try {
      const { user, error } = await login(formData.email, formData.password);
      if (error) { setErrors({ form: error }); return; }
      if (!user) { setErrors({ form: 'Invalid email or password' }); return; }

      // Route based on user_type
      if (user.user_type === 'brand') {
        router.push('/brand');
      } else {
        // Shopper flow: check avatar → dashboard or onboarding
        const hasAvatar = await hasAvatarFiles(user.id);
        router.push(hasAvatar ? '/dashboard' : '/onboarding');
      }
    } catch {
      setErrors({ form: 'Something went wrong. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  const handleSocialLogin = async (provider: 'google' | 'apple') => {
    setSocialLoading(provider);
    setErrors({});
    try {
      const { url, error } = await signInWithSocial(provider);
      if (error || !url) {
        setErrors({ form: error || 'Failed to start sign-in' });
        setSocialLoading(null);
        return;
      }
      window.location.href = url;
    } catch {
      setErrors({ form: 'Something went wrong' });
      setSocialLoading(null);
    }
  };

  const isFormValid = formData.email.trim() && formData.password;

  return (
    <div className={`min-h-screen flex items-center justify-center p-4 transition-colors ${dark ? 'bg-black' : 'bg-white'}`}>
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <TryonLogo href="/" className="h-10 w-auto mx-auto mb-4 cursor-pointer hover:opacity-80 transition" />
          <p className={dark ? 'text-white/60' : 'text-gray-500'}>
            {shopifyMode ? 'Sign in to your brand account' : 'Welcome back'}
          </p>
        </div>

        <div className={`rounded-2xl p-8 shadow-sm border ${dark ? 'bg-white/[0.04] border-white/10' : 'bg-white border-gray-200'}`}>
          <h2 className={`text-xl font-semibold mb-6 ${dark ? 'text-white' : 'text-black'}`}>Sign In</h2>

          {!shopifyMode && (
            <>
              <div className="space-y-3 mb-6">
                <button
                  type="button"
                  onClick={() => handleSocialLogin('google')}
                  disabled={!!socialLoading}
                  className={`w-full flex items-center justify-center gap-3 py-3 px-4 border rounded-xl transition disabled:opacity-40 ${dark ? 'bg-white/5 border-white/10 hover:bg-white/10 text-white' : 'bg-white border-gray-200 hover:bg-gray-50 text-gray-700'}`}
                >
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                  </svg>
                  <span className="text-sm font-medium">
                    {socialLoading === 'google' ? 'Redirecting...' : 'Continue with Google'}
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => handleSocialLogin('apple')}
                  disabled={!!socialLoading}
                  className="w-full flex items-center justify-center gap-3 py-3 px-4 bg-black text-white rounded-xl hover:bg-gray-800 transition disabled:opacity-40 border border-transparent"
                >
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.48-3.24 0-1.44.62-2.2.44-3.06-.4C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z"/>
                  </svg>
                  <span className="text-sm font-medium">
                    {socialLoading === 'apple' ? 'Redirecting...' : 'Continue with Apple'}
                  </span>
                </button>
              </div>

              <div className="relative mb-6">
                <div className="absolute inset-0 flex items-center">
                  <div className={`w-full border-t ${dark ? 'border-white/10' : 'border-gray-200'}`} />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className={`px-3 uppercase tracking-wide ${dark ? 'bg-white/[0.04] text-white/40' : 'bg-white text-gray-400'}`}>or</span>
                </div>
              </div>
            </>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className={`block text-sm font-medium mb-2 ${dark ? 'text-white/70' : 'text-gray-700'}`}>
                Email <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                required
                value={formData.email}
                onChange={(e) => {
                  setFormData({ ...formData, email: e.target.value });
                  if (errors.email) setErrors({ ...errors, email: '' });
                }}
                className={`w-full px-4 py-3 border rounded-xl focus:outline-none focus:ring-2 focus:border-transparent transition ${errors.email ? 'border-red-500' : ''} ${dark ? 'bg-white/5 border-white/10 text-white focus:ring-white/30 placeholder:text-white/30' : 'bg-gray-50 border-gray-200 text-black focus:ring-black placeholder:text-gray-400'}`}
              />
              {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email}</p>}
            </div>

            <div>
              <label className={`block text-sm font-medium mb-2 ${dark ? 'text-white/70' : 'text-gray-700'}`}>
                Password <span className="text-red-500">*</span>
              </label>
              <input
                type="password"
                required
                value={formData.password}
                onChange={(e) => {
                  setFormData({ ...formData, password: e.target.value });
                  if (errors.password) setErrors({ ...errors, password: '' });
                }}
                className={`w-full px-4 py-3 border rounded-xl focus:outline-none focus:ring-2 focus:border-transparent transition ${errors.password ? 'border-red-500' : ''} ${dark ? 'bg-white/5 border-white/10 text-white focus:ring-white/30 placeholder:text-white/30' : 'bg-gray-50 border-gray-200 text-black focus:ring-black placeholder:text-gray-400'}`}
              />
              {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password}</p>}
            </div>

            {errors.form && (
              <div className={`text-sm rounded-lg p-3 ${dark ? 'text-red-400 bg-red-500/10 border border-red-500/20' : 'text-red-600 bg-red-50 border border-red-100'}`}>
                {errors.form}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !isFormValid}
              className="w-full py-3 bg-black text-white font-semibold rounded-xl hover:bg-gray-800 transition disabled:opacity-40 disabled:cursor-not-allowed mt-6"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <p className={`text-center text-sm mt-6 ${dark ? 'text-white/50' : 'text-gray-500'}`}>
            Don&apos;t have an account?{' '}
            <Link
              href={shopifyMode || shopParam ? `/signup?type=brand${shopParam ? `&shop=${encodeURIComponent(shopParam)}` : ''}` : '/signup'}
              className={dark ? 'text-white font-medium hover:underline' : 'text-black font-medium hover:underline'}
            >
              Create one
            </Link>
          </p>
          <p className={`text-center text-xs mt-4 ${dark ? 'text-white/40' : 'text-gray-400'}`}>
            <Link href="/privacy" className={dark ? 'hover:text-white transition' : 'hover:text-black transition'}>Privacy Policy</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-gray-400">Loading...</div>
      </div>
    }>
      <LoginContent />
    </Suspense>
  );
}
