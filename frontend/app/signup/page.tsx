'use client';

import { useState, useEffect, useRef, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useTheme } from '@/contexts/ThemeContext';
import { signup, signInWithSocial } from '@/lib/supabase-auth';
import { registerBrand } from '@/lib/api';
import { isShopifyMode } from '@/lib/app-mode';
import { useEnsureShopifyAdminOAuth } from '@/lib/useEnsureShopifyAdminOAuth';
import { useResolvedShopifyShop } from '@/lib/useResolvedShopifyShop';
import { AuthSignUp, type SignUpData } from '@/components/redesign/AuthForms';

const countryCodes = [
  { code: '+31', country: 'Netherlands', abbr: 'NL' },
  { code: '+1', country: 'United States', abbr: 'US' },
  { code: '+44', country: 'United Kingdom', abbr: 'GB' },
  { code: '+49', country: 'Germany', abbr: 'DE' },
  { code: '+33', country: 'France', abbr: 'FR' },
  { code: '+34', country: 'Spain', abbr: 'ES' },
  { code: '+39', country: 'Italy', abbr: 'IT' },
  { code: '+32', country: 'Belgium', abbr: 'BE' },
  { code: '+41', country: 'Switzerland', abbr: 'CH' },
  { code: '+43', country: 'Austria', abbr: 'AT' },
  { code: '+45', country: 'Denmark', abbr: 'DK' },
  { code: '+46', country: 'Sweden', abbr: 'SE' },
  { code: '+47', country: 'Norway', abbr: 'NO' },
  { code: '+48', country: 'Poland', abbr: 'PL' },
  { code: '+351', country: 'Portugal', abbr: 'PT' },
  { code: '+353', country: 'Ireland', abbr: 'IE' },
  { code: '+358', country: 'Finland', abbr: 'FI' },
  { code: '+30', country: 'Greece', abbr: 'GR' },
  { code: '+36', country: 'Hungary', abbr: 'HU' },
  { code: '+420', country: 'Czech Republic', abbr: 'CZ' },
  { code: '+61', country: 'Australia', abbr: 'AU' },
  { code: '+64', country: 'New Zealand', abbr: 'NZ' },
  { code: '+81', country: 'Japan', abbr: 'JP' },
  { code: '+82', country: 'South Korea', abbr: 'KR' },
  { code: '+86', country: 'China', abbr: 'CN' },
  { code: '+91', country: 'India', abbr: 'IN' },
  { code: '+65', country: 'Singapore', abbr: 'SG' },
  { code: '+971', country: 'UAE', abbr: 'AE' },
  { code: '+966', country: 'Saudi Arabia', abbr: 'SA' },
  { code: '+55', country: 'Brazil', abbr: 'BR' },
  { code: '+52', country: 'Mexico', abbr: 'MX' },
  { code: '+27', country: 'South Africa', abbr: 'ZA' },
  { code: '+90', country: 'Turkey', abbr: 'TR' },
  { code: '+7', country: 'Russia', abbr: 'RU' },
  { code: '+380', country: 'Ukraine', abbr: 'UA' },
  { code: '+62', country: 'Indonesia', abbr: 'ID' },
  { code: '+60', country: 'Malaysia', abbr: 'MY' },
  { code: '+66', country: 'Thailand', abbr: 'TH' },
  { code: '+84', country: 'Vietnam', abbr: 'VN' },
  { code: '+63', country: 'Philippines', abbr: 'PH' },
];

const countries = [
  'Netherlands', 'United States', 'United Kingdom', 'Germany', 'France',
  'Spain', 'Italy', 'Belgium', 'Switzerland', 'Austria', 'Denmark',
  'Sweden', 'Norway', 'Poland', 'Portugal', 'Ireland', 'Finland',
  'Greece', 'Hungary', 'Czech Republic', 'Australia', 'New Zealand',
  'Japan', 'South Korea', 'China', 'India', 'Singapore', 'UAE',
  'Saudi Arabia', 'Brazil', 'Mexico', 'South Africa', 'Turkey',
  'Russia', 'Ukraine', 'Indonesia', 'Malaysia', 'Thailand', 'Vietnam', 'Philippines',
];

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

/* ───────── Shopper signup - redesigned ───────── */
function ShopperSignupView({ dark, router }: { dark: boolean; router: ReturnType<typeof useRouter> }) {
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const handleSubmit = async (f: SignUpData) => {
    setFormError(null);

    // Validate
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
      // Convert dd/mm/yyyy → yyyy-mm-dd if needed
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

/* ───────── Brand signup, redesigned theme ───────── */
const BRAND_PAL = {
  light: {
    bg: '#FAFAF8', surface: '#FFFFFF',
    ink: '#0A0A0A', mute: '#6E6E6E',
    line: 'rgba(10,10,10,0.10)',
    danger: '#C13128',
  },
  dark: {
    bg: '#0A0A0A', surface: '#121212',
    ink: '#F2F1EC', mute: '#8A8A8A',
    line: 'rgba(255,255,255,0.10)',
    danger: '#FF7C7C',
  },
};

function BrandSignupView({
  dark, shopifyMode, resolvedShop,
}: {
  dark: boolean;
  shopifyMode: boolean;
  resolvedShop: string | null;
}) {
  const router = useRouter();
  const dropdownRef = useRef<HTMLDivElement>(null);
  const countryDropdownRef = useRef<HTMLDivElement>(null);
  const C = dark ? BRAND_PAL.dark : BRAND_PAL.light;

  const [phoneCode, setPhoneCode] = useState('+31');
  const [showCodeDropdown, setShowCodeDropdown] = useState(false);
  const [showCountryDropdown, setShowCountryDropdown] = useState(false);

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    phone: '',
    country: '',
    brandName: '',
    contactName: '',
    shopifyDomain: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const selectedCountry = countryCodes.find(c => c.code === phoneCode) || countryCodes[0];

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowCodeDropdown(false);
      }
      if (countryDropdownRef.current && !countryDropdownRef.current.contains(event.target as Node)) {
        setShowCountryDropdown(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.brandName.trim()) newErrors.brandName = 'Brand name is required';
    if (!formData.contactName.trim()) newErrors.contactName = 'Contact name is required';
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email address';
    }
    if (!formData.phone.trim()) newErrors.phone = 'Phone number is required';
    if (!formData.country.trim()) newErrors.country = 'Country is required';
    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters';
    }
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password';
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setLoading(true);
    try {
      const fullPhone = `${phoneCode}${formData.phone}`;
      const { user, error } = await signup({
        email: formData.email,
        password: formData.password,
        name: formData.contactName,
        phone: fullPhone,
        country: formData.country,
        userType: 'brand',
      });
      if (error) { setErrors({ form: error }); return; }
      if (!user) { setErrors({ form: 'Signup failed' }); return; }

      const brandRes = await registerBrand({
        user_id: user.id,
        brand_name: formData.brandName,
        email: formData.email,
        phone: fullPhone,
        country: formData.country,
        shopify_domain: formData.shopifyDomain || resolvedShop || undefined,
      });
      if (!brandRes.ok) {
        setErrors({ form: brandRes.error || 'Failed to create brand record' });
        return;
      }

      router.push(
        resolvedShop ? `/brand?shop=${encodeURIComponent(resolvedShop)}` : '/brand'
      );
    } catch {
      setErrors({ form: 'Something went wrong. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  const isFormValid = formData.brandName.trim() && formData.contactName.trim()
    && formData.email.trim() && formData.phone.trim() && formData.country.trim()
    && formData.password && formData.confirmPassword
    && formData.password === formData.confirmPassword && formData.password.length >= 6;

  const labelStyle: React.CSSProperties = {
    display: 'block',
    fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600,
    color: C.ink, marginBottom: 6,
  };

  const fieldStyle = (hasError?: boolean): React.CSSProperties => ({
    width: '100%', padding: '12px 14px',
    border: `1px solid ${hasError ? C.danger : C.line}`,
    borderRadius: 10,
    background: C.surface,
    fontFamily: 'var(--display)', fontSize: 15, fontWeight: 500,
    color: C.ink,
    outline: 'none',
    boxSizing: 'border-box',
  });

  const errorStyle: React.CSSProperties = {
    fontFamily: 'var(--display)', fontSize: 12, color: C.danger, marginTop: 4,
  };

  return (
    <div className="tryon-redesign-root" style={{
      minHeight: '100vh', background: C.bg, color: C.ink,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '40px 20px',
    }}>
      <div style={{ width: '100%', maxWidth: 480 }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <button
            onClick={() => router.push('/')}
            style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', display: 'inline-flex', marginBottom: 18 }}
            aria-label="TryOn home"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={dark ? '/redesign/wordmark-white.png' : '/redesign/wordmark.png'}
              alt="TryOn"
              style={{ height: 22, width: 'auto' }}
            />
          </button>
          <h1 style={{
            fontFamily: 'var(--display)', fontSize: 26, fontWeight: 700,
            color: C.ink, letterSpacing: '-0.015em', margin: '0 0 6px',
          }}>Set up your brand account</h1>
          <p style={{ fontFamily: 'var(--display)', fontSize: 14, color: C.mute, margin: 0 }}>
            Connect your store. Start cutting returns.
          </p>
        </div>

        <div style={{
          background: C.surface,
          border: `1px solid ${C.line}`,
          borderRadius: 14,
          padding: 28,
          boxShadow: '0 12px 40px rgba(0,0,0,0.04)',
        }}>
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <label style={labelStyle}>Brand or company name</label>
              <input
                type="text"
                required
                placeholder="e.g. Moncler"
                value={formData.brandName}
                onChange={(e) => {
                  setFormData({ ...formData, brandName: e.target.value });
                  if (errors.brandName) setErrors({ ...errors, brandName: '' });
                }}
                style={fieldStyle(!!errors.brandName)}
              />
              {errors.brandName && <p style={errorStyle}>{errors.brandName}</p>}
            </div>

            <div>
              <label style={labelStyle}>Contact name</label>
              <input
                type="text"
                required
                value={formData.contactName}
                onChange={(e) => {
                  setFormData({ ...formData, contactName: e.target.value });
                  if (errors.contactName) setErrors({ ...errors, contactName: '' });
                }}
                style={fieldStyle(!!errors.contactName)}
              />
              {errors.contactName && <p style={errorStyle}>{errors.contactName}</p>}
            </div>

            <div>
              <label style={labelStyle}>Business email</label>
              <input
                type="email"
                required
                value={formData.email}
                onChange={(e) => {
                  setFormData({ ...formData, email: e.target.value });
                  if (errors.email) setErrors({ ...errors, email: '' });
                }}
                style={fieldStyle(!!errors.email)}
              />
              {errors.email && <p style={errorStyle}>{errors.email}</p>}
            </div>

            <div>
              <label style={labelStyle}>Phone</label>
              <div style={{ display: 'flex', gap: 8 }}>
                <div style={{ position: 'relative' }} ref={dropdownRef}>
                  <button
                    type="button"
                    onClick={() => setShowCodeDropdown(!showCodeDropdown)}
                    style={{
                      display: 'inline-flex', alignItems: 'center', gap: 8,
                      padding: '12px 12px',
                      border: `1px solid ${errors.phone ? C.danger : C.line}`,
                      borderRadius: 10,
                      background: C.surface, color: C.ink,
                      fontFamily: 'var(--display)', fontSize: 14, fontWeight: 500,
                      cursor: 'pointer', minWidth: 116,
                    }}
                  >
                    <span style={{ fontSize: 11, fontWeight: 600, color: C.mute, width: 22, textAlign: 'center' }}>
                      {selectedCountry.abbr}
                    </span>
                    <span>{phoneCode}</span>
                    <span style={{ marginLeft: 'auto', color: C.mute, fontSize: 12 }}>▾</span>
                  </button>
                  {showCodeDropdown && (
                    <div style={{
                      position: 'absolute', top: 'calc(100% + 4px)', left: 0,
                      width: 280,
                      background: C.surface, border: `1px solid ${C.line}`,
                      borderRadius: 10, boxShadow: '0 16px 40px rgba(0,0,0,0.1)',
                      zIndex: 50, maxHeight: 240, overflowY: 'auto',
                    }}>
                      {countryCodes.map((c) => (
                        <button
                          key={c.code}
                          type="button"
                          onClick={() => { setPhoneCode(c.code); setShowCodeDropdown(false); }}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 12,
                            width: '100%', padding: '10px 14px',
                            background: phoneCode === c.code ? C.bg : 'transparent',
                            border: 'none', cursor: 'pointer', textAlign: 'left',
                            fontFamily: 'var(--display)', fontSize: 13, color: C.ink,
                          }}
                        >
                          <span style={{ fontSize: 11, fontWeight: 600, color: C.mute, width: 22, textAlign: 'center' }}>{c.abbr}</span>
                          <span style={{ flex: 1 }}>{c.country}</span>
                          <span style={{ color: C.mute, fontSize: 12 }}>{c.code}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <input
                  type="tel"
                  required
                  placeholder="6 12345678"
                  value={formData.phone}
                  onChange={(e) => {
                    const value = e.target.value.replace(/[^0-9]/g, '');
                    setFormData({ ...formData, phone: value });
                    if (errors.phone) setErrors({ ...errors, phone: '' });
                  }}
                  style={{ ...fieldStyle(!!errors.phone), flex: 1 }}
                />
              </div>
              {errors.phone && <p style={errorStyle}>{errors.phone}</p>}
            </div>

            {!shopifyMode && (
              <div>
                <label style={labelStyle}>
                  Shopify store URL <span style={{ color: C.mute, fontWeight: 400 }}>(optional)</span>
                </label>
                <div style={{ display: 'flex' }}>
                  <input
                    type="text"
                    placeholder="your-store"
                    value={formData.shopifyDomain}
                    onChange={(e) => setFormData({ ...formData, shopifyDomain: e.target.value.replace(/\s/g, '').toLowerCase() })}
                    style={{
                      ...fieldStyle(false),
                      flex: 1,
                      borderRadius: '10px 0 0 10px',
                      borderRight: 'none',
                    }}
                  />
                  <span style={{
                    padding: '12px 14px',
                    border: `1px solid ${C.line}`,
                    borderRadius: '0 10px 10px 0',
                    background: C.bg, color: C.mute,
                    fontFamily: 'var(--display)', fontSize: 13,
                    display: 'inline-flex', alignItems: 'center', whiteSpace: 'nowrap',
                  }}>.myshopify.com</span>
                </div>
                <p style={{ fontFamily: 'var(--display)', fontSize: 12, color: C.mute, marginTop: 4 }}>
                  You can connect your store later from the dashboard.
                </p>
              </div>
            )}

            <div style={{ position: 'relative' }} ref={countryDropdownRef}>
              <label style={labelStyle}>Country</label>
              <button
                type="button"
                onClick={() => setShowCountryDropdown(!showCountryDropdown)}
                style={{
                  ...fieldStyle(!!errors.country),
                  textAlign: 'left',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  cursor: 'pointer',
                }}
              >
                <span style={{ color: formData.country ? C.ink : C.mute }}>
                  {formData.country || 'Select country'}
                </span>
                <span style={{ color: C.mute, fontSize: 12 }}>▾</span>
              </button>
              {showCountryDropdown && (
                <div style={{
                  position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0,
                  background: C.surface, border: `1px solid ${C.line}`,
                  borderRadius: 10, boxShadow: '0 16px 40px rgba(0,0,0,0.1)',
                  zIndex: 50, maxHeight: 240, overflowY: 'auto',
                }}>
                  {countries.map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => {
                        setFormData({ ...formData, country: c });
                        setShowCountryDropdown(false);
                        if (errors.country) setErrors({ ...errors, country: '' });
                      }}
                      style={{
                        display: 'block', width: '100%', textAlign: 'left',
                        padding: '10px 14px',
                        background: 'transparent', border: 'none', cursor: 'pointer',
                        fontFamily: 'var(--display)', fontSize: 13, color: C.ink,
                      }}
                    >{c}</button>
                  ))}
                </div>
              )}
              {errors.country && <p style={errorStyle}>{errors.country}</p>}
            </div>

            <div>
              <label style={labelStyle}>Password</label>
              <input
                type="password"
                required
                value={formData.password}
                onChange={(e) => {
                  setFormData({ ...formData, password: e.target.value });
                  if (errors.password) setErrors({ ...errors, password: '' });
                }}
                style={fieldStyle(!!errors.password)}
              />
              {errors.password && <p style={errorStyle}>{errors.password}</p>}
            </div>

            <div>
              <label style={labelStyle}>Confirm password</label>
              <input
                type="password"
                required
                value={formData.confirmPassword}
                onChange={(e) => {
                  setFormData({ ...formData, confirmPassword: e.target.value });
                  if (errors.confirmPassword) setErrors({ ...errors, confirmPassword: '' });
                }}
                style={fieldStyle(!!errors.confirmPassword)}
              />
              {errors.confirmPassword && <p style={errorStyle}>{errors.confirmPassword}</p>}
            </div>

            {errors.form && (
              <div style={{
                padding: '12px 14px', borderRadius: 10,
                background: 'rgba(193,49,40,0.08)',
                color: C.danger, fontSize: 13, fontFamily: 'var(--display)',
                border: '1px solid rgba(193,49,40,0.18)',
              }}>{errors.form}</div>
            )}

            <button
              type="submit"
              disabled={loading || !isFormValid}
              style={{
                marginTop: 8,
                background: C.ink, color: C.bg,
                padding: '14px 18px', borderRadius: 999, border: 'none',
                fontFamily: 'var(--display)', fontSize: 15, fontWeight: 600,
                cursor: (loading || !isFormValid) ? 'not-allowed' : 'pointer',
                opacity: (loading || !isFormValid) ? 0.4 : 1,
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 10,
              }}
            >{loading ? 'Creating account...' : (<>Create account <span>→</span></>)}</button>
          </form>

          <p style={{
            textAlign: 'center', fontFamily: 'var(--display)', fontSize: 13, color: C.mute,
            marginTop: 20, marginBottom: 0,
          }}>
            Already have an account?{' '}
            <Link href="/login" style={{ color: C.ink, fontWeight: 600, textDecoration: 'underline' }}>Sign in</Link>
          </p>
        </div>

        <p style={{
          textAlign: 'center', fontFamily: 'var(--display)', fontSize: 12, color: C.mute,
          marginTop: 18,
        }}>
          By signing up, you agree to our Terms of Service and{' '}
          <Link href="/privacy" style={{ color: C.mute, textDecoration: 'underline' }}>Privacy Policy</Link>.
        </p>
      </div>
    </div>
  );
}

export default function SignupPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-gray-400">Loading...</div>
      </div>
    }>
      <SignupContent />
    </Suspense>
  );
}
