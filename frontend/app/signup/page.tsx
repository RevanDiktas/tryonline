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
import { TryonLogo } from '@/components/TryonLogo';

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
    // Shopify-embedded install stays self-serve: the merchant arrives through the
    // Shopify admin and needs an account immediately. Website brand onboarding is
    // high-touch (size charts, 3D garment build, widget install) with no self-serve
    // billing yet, so it routes to a booked call instead of an account form.
    if (shopifyMode) {
      return <BrandSignupView dark={dark} shopifyMode={shopifyMode} resolvedShop={resolvedShop} />;
    }
    return <BrandBookACallView dark={dark} />;
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

/* ───────── Brand onboarding: book a call (website) ───────── */
function BrandBookACallView({ dark }: { dark: boolean }) {
  const router = useRouter();
  const ink = dark ? '#F2F1EC' : '#0A0A0A';
  const bg = dark ? '#0A0A0A' : '#FFFFFF';
  return (
    <div style={{
      minHeight: '100vh', background: bg, color: ink,
      display: 'flex', flexDirection: 'column',
    }}>
      <div style={{ padding: '20px 24px' }}>
        <TryonLogo href="/" className="h-6 w-auto" />
      </div>
      <div style={{
        flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
      }}>
        <div style={{ maxWidth: 480, textAlign: 'center' }}>
          <div style={{
            fontFamily: 'var(--mono)', fontSize: 12, letterSpacing: '0.08em',
            textTransform: 'uppercase', opacity: 0.55, marginBottom: 16,
          }}>For brands</div>
          <h1 style={{
            fontFamily: 'var(--display)', fontWeight: 700,
            fontSize: 'clamp(30px, 5vw, 46px)', letterSpacing: '-0.03em',
            lineHeight: 1.05, margin: '0 0 16px',
          }}>Get your brand set up.</h1>
          <p style={{
            fontFamily: 'var(--display)', fontSize: 16, lineHeight: 1.6,
            opacity: 0.7, margin: '0 0 28px',
          }}>
            Onboarding is hands-on: we map your size charts, build your garments in 3D,
            and get the widget live on your store. Book a call and we will set it up with you.
          </p>
          <button
            onClick={() => router.push('/book')}
            style={{
              background: '#0040FF', color: '#FFFFFF',
              padding: '14px 28px', borderRadius: 9999,
              fontFamily: 'var(--display)', fontSize: 15, fontWeight: 600,
              border: 'none', cursor: 'pointer',
              display: 'inline-flex', alignItems: 'center', gap: 8,
            }}
          >Book a call <span>→</span></button>
          <div>
            <button
              onClick={() => router.push('/login')}
              style={{
                marginTop: 24, background: 'none', border: 'none', cursor: 'pointer',
                fontFamily: 'var(--display)', fontSize: 14, color: ink, opacity: 0.6,
              }}
            >Already have an account? Sign in</button>
          </div>
        </div>
      </div>
    </div>
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
