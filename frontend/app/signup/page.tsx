'use client';

import { Suspense, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { TryonLogo } from '@/components/TryonLogo';
import { signup, signInWithSocial, getCurrentUser } from '@/lib/supabase-auth';

function SignupInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const step = searchParams.get('step');
  const typeParam = searchParams.get('type');
  const userType = typeParam === 'brand' ? 'brand' : 'shopper';

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [country, setCountry] = useState('');
  const [city, setCity] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [socialLoading, setSocialLoading] = useState<'google' | 'apple' | null>(null);
  const [geoDetected, setGeoDetected] = useState(false);

  // Auto-detect rough location via IP-based geolocation (no permission prompt)
  useEffect(() => {
    if (geoDetected) return;
    const detect = async () => {
      try {
        const res = await fetch('https://ipapi.co/json/', { signal: AbortSignal.timeout(4000) });
        if (!res.ok) return;
        const data = await res.json();
        if (data.country_name && !country) setCountry(data.country_name);
        if (data.city && !city) setCity(data.city);
        setGeoDetected(true);
      } catch { /* non-critical */ }
    };
    detect();
  }, [geoDetected, country, city]);

  // If we land here with ?step=onboarding, user is already authed (came from OAuth callback)
  useEffect(() => {
    if (step === 'onboarding') {
      getCurrentUser().then(u => {
        if (u?.name) setName(u.name);
        if (u?.email) setEmail(u.email);
      });
    }
  }, [step]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (step === 'onboarding') {
      // User is already authenticated via OAuth; just redirect to dashboard
      router.replace(userType === 'brand' ? '/brand' : '/dashboard');
      return;
    }

    const { user, error: signupError } = await signup({ email, password, name, country, city, userType });
    setLoading(false);
    if (signupError) { setError(signupError); return; }
    if (user) {
      router.replace(userType === 'brand' ? '/brand' : '/dashboard');
    }
  };

  const handleSocial = async (provider: 'google' | 'apple') => {
    setError('');
    setSocialLoading(provider);
    const { url, error: socialError } = await signInWithSocial(provider);
    if (socialError) { setError(socialError); setSocialLoading(null); return; }
    if (url) window.location.href = url;
  };

  const isOnboarding = step === 'onboarding';

  return (
    <div className="min-h-screen bg-black flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <TryonLogo className="h-10 w-auto mb-2" href="/" />
          <p className="text-white/50 text-sm">
            {isOnboarding ? 'Almost there' : userType === 'brand' ? 'Create your brand account' : 'Create your Fit Passport'}
          </p>
        </div>

        <div className="bg-white/[0.06] border border-white/10 rounded-2xl p-6">
          <h2 className="text-white text-lg font-semibold mb-5">
            {isOnboarding ? 'Confirm your details' : 'Sign Up'}
          </h2>

          {!isOnboarding && (
            <>
              <div className="flex flex-col gap-3 mb-5">
                <button
                  type="button"
                  onClick={() => handleSocial('google')}
                  disabled={!!socialLoading}
                  className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl border border-white/10 bg-white/[0.04] text-white text-sm font-medium hover:bg-white/[0.08] transition disabled:opacity-50"
                >
                  {socialLoading === 'google' ? (
                    <span className="text-white/50">Redirecting…</span>
                  ) : (
                    <>
                      <svg className="w-4 h-4" viewBox="0 0 24 24">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                      </svg>
                      Continue with Google
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => handleSocial('apple')}
                  disabled={!!socialLoading}
                  className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl border border-white/10 bg-white/[0.04] text-white text-sm font-medium hover:bg-white/[0.08] transition disabled:opacity-50"
                >
                  {socialLoading === 'apple' ? (
                    <span className="text-white/50">Redirecting…</span>
                  ) : (
                    <>
                      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="white">
                        <path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.48-3.24 0-1.44.62-2.2.44-3.06-.4C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z"/>
                      </svg>
                      Continue with Apple
                    </>
                  )}
                </button>
              </div>

              <div className="flex items-center gap-3 mb-5">
                <div className="flex-1 h-px bg-white/10"/>
                <span className="text-white/30 text-xs uppercase">or</span>
                <div className="flex-1 h-px bg-white/10"/>
              </div>
            </>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label htmlFor="signup-name" className="block text-white/60 text-xs mb-1.5">Name</label>
              <input
                id="signup-name"
                name="name"
                type="text"
                autoComplete="name"
                required
                value={name}
                onChange={e => setName(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl bg-white/[0.06] border border-white/10 text-white text-sm placeholder-white/30 focus:outline-none focus:border-white/30"
                placeholder="Your name"
              />
            </div>

            {!isOnboarding && (
              <>
                <div>
                  <label htmlFor="signup-email" className="block text-white/60 text-xs mb-1.5">Email</label>
                  <input
                    id="signup-email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    className="w-full px-3 py-2.5 rounded-xl bg-white/[0.06] border border-white/10 text-white text-sm placeholder-white/30 focus:outline-none focus:border-white/30"
                    placeholder="you@example.com"
                  />
                </div>
                <div>
                  <label htmlFor="signup-password" className="block text-white/60 text-xs mb-1.5">Password</label>
                  <input
                    id="signup-password"
                    name="password"
                    type="password"
                    autoComplete="new-password"
                    required
                    minLength={6}
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    className="w-full px-3 py-2.5 rounded-xl bg-white/[0.06] border border-white/10 text-white text-sm placeholder-white/30 focus:outline-none focus:border-white/30"
                    placeholder="At least 6 characters"
                  />
                </div>
              </>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="signup-country" className="block text-white/60 text-xs mb-1.5">Country</label>
                <input
                  id="signup-country"
                  name="country"
                  type="text"
                  autoComplete="country-name"
                  value={country}
                  onChange={e => setCountry(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl bg-white/[0.06] border border-white/10 text-white text-sm placeholder-white/30 focus:outline-none focus:border-white/30"
                  placeholder="Netherlands"
                />
              </div>
              <div>
                <label htmlFor="signup-city" className="block text-white/60 text-xs mb-1.5">City</label>
                <input
                  id="signup-city"
                  name="city"
                  type="text"
                  autoComplete="address-level2"
                  value={city}
                  onChange={e => setCity(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl bg-white/[0.06] border border-white/10 text-white text-sm placeholder-white/30 focus:outline-none focus:border-white/30"
                  placeholder="Amsterdam"
                />
              </div>
            </div>

            {error && <p className="text-red-500 text-xs">{error}</p>}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-xl bg-white text-black text-sm font-semibold hover:bg-white/90 transition disabled:opacity-50"
            >
              {loading ? 'Creating account…' : isOnboarding ? 'Continue to Dashboard' : 'Create Account'}
            </button>
          </form>

          {!isOnboarding && (
            <p className="text-center text-white/40 text-xs mt-5">
              Already have an account?{' '}
              <Link href="/login" className="text-white underline">Sign in</Link>
            </p>
          )}
          <p className="text-center mt-2">
            <Link href="/privacy" className="text-white/30 text-xs hover:text-white/50 transition">Privacy Policy</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function SignupPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-black text-white/60">Loading…</div>
      }
    >
      <SignupInner />
    </Suspense>
  );
}
