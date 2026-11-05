'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useTheme } from '@/contexts/ThemeContext';
import { login, hasAvatarFiles, signInWithSocial, requestPasswordReset } from '@/lib/supabase-auth';
import { useEnsureShopifyAdminOAuth } from '@/lib/useEnsureShopifyAdminOAuth';
import { useResolvedShopifyShop } from '@/lib/useResolvedShopifyShop';
import { isShopifyMode } from '@/lib/app-mode';
import { captureWidgetReturn, completeWidgetLink, shopperHomePath, widgetReturnQuery } from '@/lib/widgetReturn';
import { AuthSignIn, AuthRoleChooser, type SignInData } from '@/components/redesign/AuthForms';

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { theme } = useTheme();
  const dark = theme === 'dark';
  const resolvedShop = useResolvedShopifyShop();
  useEnsureShopifyAdminOAuth(resolvedShop, searchParams.get('error'));

  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const handleForgot = async (email: string) => {
    setFormError(null); setNotice(null);
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return setFormError('Type your email above first, then press Forgot.');
    setLoading(true);
    try {
      const { error } = await requestPasswordReset(email);
      if (error) setFormError(error);
      else setNotice(`We sent a reset link to ${email}. Open it on this device to choose a new password.`);
    } finally {
      setLoading(false);
    }
  };

  // Website fork: brand or shopper. Deep-linkable with ?as=brand / ?as=shopper.
  // Skipped on the Shopify-embedded surface and on widget hand-offs (those are shopper flows).
  const asParam = searchParams.get('as');
  const [role, setRole] = useState<'brand' | 'shopper' | null>(
    asParam === 'brand' || asParam === 'shopper' ? asParam : null,
  );

  // Widget hand-off (?from=widget&return=…): persist before any OAuth redirect.
  useEffect(() => { captureWidgetReturn(searchParams); }, [searchParams]);

  const handleSubmit = async (f: SignInData) => {
    setFormError(null);
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email)) return setFormError('Please enter a valid email address.');
    if (!f.password) return setFormError('Password is required.');

    setLoading(true);
    try {
      const { user, error } = await login(f.email, f.password);
      if (error) { setFormError(error); return; }
      if (!user) { setFormError('Invalid email or password.'); return; }
      await completeWidgetLink(user);

      if (user.user_type === 'brand') {
        router.push(resolvedShop ? `/brand?shop=${encodeURIComponent(resolvedShop)}` : '/brand');
      } else {
        const hasAvatar = await hasAvatarFiles(user.id);
        router.push(shopperHomePath(hasAvatar));
      }
    } catch {
      setFormError('Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSocial = async (provider: 'google' | 'apple') => {
    setFormError(null);
    const { url, error } = await signInWithSocial(provider);
    if (url) window.location.href = url;
    else if (error) setFormError(error);
  };

  // Brand-only sign in is reserved for the Shopify-embedded surface (host/env).
  // It must NOT be driven by resolvedShop: a stale shop context in sessionStorage
  // would otherwise hide the shopper Google/Apple sign in on the public website.
  const shopifyMode = isShopifyMode();
  const widgetFlow = Boolean(searchParams.get('from') || searchParams.get('return') || searchParams.get('link_state'));

  if (!shopifyMode && !widgetFlow && !role) {
    return <AuthRoleChooser dark={dark} onChoose={setRole} />;
  }
  const brandMode = shopifyMode || role === 'brand';

  return (
    <AuthSignIn
      dark={dark}
      loading={loading}
      formError={formError}
      onSubmit={handleSubmit}
      onGoogle={() => handleSocial('google')}
      onApple={() => handleSocial('apple')}
      onSignUpClick={() => router.push(resolvedShop ? `/signup?shop=${encodeURIComponent(resolvedShop)}` : `/signup${widgetReturnQuery()}`)}
      shopifyMode={brandMode}
      onForgot={handleForgot}
      notice={notice}
      switchLabel={!shopifyMode && !widgetFlow ? (role === 'brand' ? 'Not a brand? Sign in as a shopper' : 'Run a brand? Sign in as a brand') : undefined}
      onSwitchRole={!shopifyMode && !widgetFlow ? () => { setFormError(null); setRole(role === 'brand' ? 'shopper' : 'brand'); } : undefined}
    />
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
