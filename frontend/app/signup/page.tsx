'use client';

import { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useTheme } from '@/contexts/ThemeContext';
import { signup, signInWithSocial } from '@/lib/supabase-auth';
import { registerBrand } from '@/lib/api';
import { isShopifyMode } from '@/lib/app-mode';
import { useEnsureShopifyAdminOAuth } from '@/lib/useEnsureShopifyAdminOAuth';
import { useResolvedShopifyShop } from '@/lib/useResolvedShopifyShop';
import {
  AuthSignUp, type SignUpData,
  AuthBrandSignUp, type BrandSignUpData,
} from '@/components/redesign/AuthForms';

function SignupContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { theme } = useTheme();
  const dark = theme === 'dark';
  const shopifyMode = isShopifyMode();

  const typeParam = searchParams.get('type');
  const resolvedShop = useResolvedShopifyShop();
  useEnsureShopifyAdminOAuth(resolvedShop, searchParams.get('error'));
  const isBrand = shopifyMode || typeParam === 'brand';

  if (isBrand) {
    return <BrandSignupView dark={dark} shopifyMode={shopifyMode} resolvedShop={resolvedShop} />;
  }

  return <ShopperSignupView dark={dark} router={router} />;
}

/* ───────── Shopper signup ───────── */
function ShopperSignupView({ dark, router }: { dark: boolean; router: ReturnType<typeof useRouter> }) {
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const handleSubmit = async (f: SignUpData) => {
    setFormError(null);
    if (!f.name.trim()) return setFormError('Full name is required.');
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email)) return setFormError('Please enter a valid email address.');
    if (!f.phone.trim()) return setFormError('Phone number is required.');
    if (!f.dob.trim()) return setFormError('Date of birth is required.');
    if (!f.city.trim()) return setFormError('City is required.');
    if (!f.country.trim()) return setFormError('Country is required.');
    if (!f.password || f.password.length < 6) return setFormError('Password must be at least 6 characters.');
    if (f.password !== f.confirm) return setFormError('Passwords do not match.');

    setLoading(true);
    try {
      const fullPhone = `${f.code}${f.phone}`;
      let dob = f.dob;
      const ddmmyyyy = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(f.dob);
      if (ddmmyyyy) dob = `${ddmmyyyy[3]}-${ddmmyyyy[2]}-${ddmmyyyy[1]}`;

      const { user, error } = await signup({
        email: f.email,
        password: f.password,
        name: f.name,
        phone: fullPhone,
        dateOfBirth: dob || undefined,
        country: f.country,
        city: f.city,
        userType: 'shopper',
      });

      if (error) { setFormError(error); return; }
      if (!user) { setFormError('Signup failed. Please try again.'); return; }
      router.push('/onboarding');
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

  return (
    <AuthSignUp
      dark={dark}
      loading={loading}
      formError={formError}
      onSubmit={handleSubmit}
      onGoogle={() => handleSocial('google')}
      onApple={() => handleSocial('apple')}
      onSignInClick={() => router.push('/login')}
    />
  );
}

/* ───────── Brand signup ───────── */
function BrandSignupView({
  dark, shopifyMode, resolvedShop,
}: {
  dark: boolean;
  shopifyMode: boolean;
  resolvedShop: string | null;
}) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const handleSubmit = async (f: BrandSignUpData) => {
    setFormError(null);
    if (!f.brandName.trim()) return setFormError('Brand name is required.');
    if (!f.contactName.trim()) return setFormError('Contact name is required.');
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email)) return setFormError('Please enter a valid email address.');
    if (!f.phone.trim()) return setFormError('Phone number is required.');
    if (!shopifyMode && !f.shopifyDomain.trim()) {
      return setFormError('Shopify store URL is required.');
    }
    if (!f.country.trim()) return setFormError('Country is required.');
    if (!f.password || f.password.length < 6) return setFormError('Password must be at least 6 characters.');
    if (f.password !== f.confirm) return setFormError('Passwords do not match.');

    setLoading(true);
    try {
      const fullPhone = `${f.code}${f.phone}`;
      const { user, error } = await signup({
        email: f.email,
        password: f.password,
        name: f.contactName,
        phone: fullPhone,
        country: f.country,
        userType: 'brand',
      });
      if (error) { setFormError(error); return; }
      if (!user) { setFormError('Signup failed. Please try again.'); return; }

      const brandRes = await registerBrand({
        user_id: user.id,
        brand_name: f.brandName,
        email: f.email,
        phone: fullPhone,
        country: f.country,
        shopify_domain: f.shopifyDomain || resolvedShop || undefined,
      });
      if (!brandRes.ok) {
        setFormError(brandRes.error || 'Failed to create brand record');
        return;
      }

      router.push(
        resolvedShop ? `/brand?shop=${encodeURIComponent(resolvedShop)}` : '/brand'
      );
    } catch {
      setFormError('Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthBrandSignUp
      dark={dark}
      loading={loading}
      formError={formError}
      onSubmit={handleSubmit}
      onSignInClick={() => router.push('/login')}
      shopifyMode={shopifyMode}
      prefilledShop={resolvedShop}
    />
  );
}

export default function SignupPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-gray-400">Loading…</div>
      </div>
    }>
      <SignupContent />
    </Suspense>
  );
}
