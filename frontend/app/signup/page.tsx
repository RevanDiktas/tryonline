'use client';

import { useState, useEffect, useRef, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { TryonLogo } from '@/components/TryonLogo';
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

/* ───────── Brand signup - preserved unchanged from previous design ───────── */
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

  return (
    <div className={`min-h-screen flex items-center justify-center p-4 transition-colors ${dark ? 'bg-black' : 'bg-white'}`}>
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <TryonLogo href="/" className="h-10 w-auto mx-auto mb-4 cursor-pointer hover:opacity-80 transition" />
          <p className={dark ? 'text-white/60' : 'text-gray-500'}>Set up your brand account</p>
        </div>

        <div className={`rounded-2xl p-8 shadow-sm border ${dark ? 'bg-white/[0.04] border-white/10' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-gradient-to-br from-orange-500 to-pink-600">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            </div>
            <div>
              <h2 className={`text-xl font-semibold ${dark ? 'text-white' : 'text-black'}`}>Brand Account</h2>
              <p className={dark ? 'text-white/60 text-sm' : 'text-gray-500 text-sm'}>Enter your details below</p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className={`block text-sm font-medium mb-2 ${dark ? 'text-white/70' : 'text-gray-700'}`}>
                Brand / Company Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Moncler"
                value={formData.brandName}
                onChange={(e) => {
                  setFormData({ ...formData, brandName: e.target.value });
                  if (errors.brandName) setErrors({ ...errors, brandName: '' });
                }}
                className={`w-full px-4 py-3 border rounded-xl focus:outline-none focus:ring-2 focus:border-transparent transition ${errors.brandName ? 'border-red-500' : ''} ${dark ? 'bg-white/5 border-white/10 text-white focus:ring-white/30' : 'bg-gray-50 border-gray-200 text-black focus:ring-black'}`}
              />
              {errors.brandName && <p className="text-red-500 text-xs mt-1">{errors.brandName}</p>}
            </div>

            <div>
              <label className={`block text-sm font-medium mb-2 ${dark ? 'text-white/70' : 'text-gray-700'}`}>
                Contact Person Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={formData.contactName}
                onChange={(e) => {
                  setFormData({ ...formData, contactName: e.target.value });
                  if (errors.contactName) setErrors({ ...errors, contactName: '' });
                }}
                className={`w-full px-4 py-3 border rounded-xl focus:outline-none focus:ring-2 focus:border-transparent transition ${errors.contactName ? 'border-red-500' : ''} ${dark ? 'bg-white/5 border-white/10 text-white focus:ring-white/30' : 'bg-gray-50 border-gray-200 text-black focus:ring-black'}`}
              />
              {errors.contactName && <p className="text-red-500 text-xs mt-1">{errors.contactName}</p>}
            </div>

            <div>
              <label className={`block text-sm font-medium mb-2 ${dark ? 'text-white/70' : 'text-gray-700'}`}>
                Business Email <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                required
                value={formData.email}
                onChange={(e) => {
                  setFormData({ ...formData, email: e.target.value });
                  if (errors.email) setErrors({ ...errors, email: '' });
                }}
                className={`w-full px-4 py-3 border rounded-xl focus:outline-none focus:ring-2 focus:border-transparent transition ${errors.email ? 'border-red-500' : ''} ${dark ? 'bg-white/5 border-white/10 text-white focus:ring-white/30' : 'bg-gray-50 border-gray-200 text-black focus:ring-black'}`}
              />
              {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email}</p>}
            </div>

            <div>
              <label className={`block text-sm font-medium mb-2 ${dark ? 'text-white/70' : 'text-gray-700'}`}>
                Phone Number <span className="text-red-500">*</span>
              </label>
              <div className="flex gap-2">
                <div className="relative" ref={dropdownRef}>
                  <button
                    type="button"
                    onClick={() => setShowCodeDropdown(!showCodeDropdown)}
                    className={`flex items-center gap-2 px-3 py-3 border rounded-xl transition min-w-[110px] ${errors.phone ? 'border-red-500' : ''} ${dark ? 'bg-white/5 border-white/10 text-white hover:bg-white/10' : 'bg-gray-50 border-gray-200 text-black hover:bg-gray-100'}`}
                  >
                    <span className={`text-xs font-semibold w-6 text-center ${dark ? 'text-white/50' : 'text-gray-500'}`}>{selectedCountry.abbr}</span>
                    <span className="font-medium">{phoneCode}</span>
                    <svg className={`w-4 h-4 ml-auto ${dark ? 'text-white/40' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  {showCodeDropdown && (
                    <div className={`absolute top-full left-0 mt-1 w-64 border rounded-xl shadow-lg z-50 max-h-60 overflow-y-auto ${dark ? 'bg-zinc-900 border-white/10' : 'bg-white border-gray-200'}`}>
                      {countryCodes.map((c) => (
                        <button
                          key={c.code}
                          type="button"
                          onClick={() => { setPhoneCode(c.code); setShowCodeDropdown(false); }}
                          className={`w-full flex items-center gap-3 px-4 py-2.5 transition text-left ${phoneCode === c.code ? (dark ? 'bg-white/10' : 'bg-gray-100') : ''} ${dark ? 'hover:bg-white/5 text-white' : 'hover:bg-gray-50 text-black'}`}
                        >
                          <span className={`text-xs font-semibold w-6 text-center ${dark ? 'text-white/50' : 'text-gray-500'}`}>{c.abbr}</span>
                          <span className="flex-1">{c.country}</span>
                          <span className={dark ? 'text-white/40 text-sm' : 'text-gray-500 text-sm'}>{c.code}</span>
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
                  className={`flex-1 px-4 py-3 border rounded-xl focus:outline-none focus:ring-2 focus:border-transparent transition ${errors.phone ? 'border-red-500' : ''} ${dark ? 'bg-white/5 border-white/10 text-white focus:ring-white/30' : 'bg-gray-50 border-gray-200 text-black focus:ring-black'}`}
                />
              </div>
              {errors.phone && <p className="text-red-500 text-xs mt-1">{errors.phone}</p>}
            </div>

            {!shopifyMode && (
              <div>
                <label className={`block text-sm font-medium mb-2 ${dark ? 'text-white/70' : 'text-gray-700'}`}>
                  Shopify Store URL <span className={dark ? 'text-white/30 font-normal' : 'text-gray-400 font-normal'}>(optional)</span>
                </label>
                <div className="flex items-center gap-0">
                  <input
                    type="text"
                    placeholder="your-store"
                    value={formData.shopifyDomain}
                    onChange={(e) => setFormData({ ...formData, shopifyDomain: e.target.value.replace(/\s/g, '').toLowerCase() })}
                    className={`flex-1 px-4 py-3 border rounded-l-xl focus:outline-none focus:ring-2 focus:border-transparent transition ${dark ? 'bg-white/5 border-white/10 text-white focus:ring-white/30' : 'bg-gray-50 border-gray-200 text-black focus:ring-black'}`}
                  />
                  <span className={`px-3 py-3 border border-l-0 rounded-r-xl text-sm whitespace-nowrap ${dark ? 'bg-white/5 border-white/10 text-white/50' : 'bg-gray-100 border-gray-200 text-gray-500'}`}>.myshopify.com</span>
                </div>
                <p className={`text-xs mt-1 ${dark ? 'text-white/40' : 'text-gray-400'}`}>You can connect your store later from the dashboard</p>
              </div>
            )}

            <div className="relative" ref={countryDropdownRef}>
              <label className={`block text-sm font-medium mb-2 ${dark ? 'text-white/70' : 'text-gray-700'}`}>
                Country <span className="text-red-500">*</span>
              </label>
              <button
                type="button"
                onClick={() => setShowCountryDropdown(!showCountryDropdown)}
                className={`w-full px-4 py-3 border rounded-xl text-left flex items-center justify-between transition ${errors.country ? 'border-red-500' : ''} ${dark ? 'bg-white/5 border-white/10 text-white hover:bg-white/10' : 'bg-gray-50 border-gray-200 text-black hover:bg-gray-100'}`}
              >
                <span className={formData.country ? '' : (dark ? 'text-white/40' : 'text-gray-400')}>
                  {formData.country || 'Select country'}
                </span>
                <svg className={`w-4 h-4 ${dark ? 'text-white/40' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {showCountryDropdown && (
                <div className={`absolute top-full left-0 right-0 mt-1 border rounded-xl shadow-lg z-50 max-h-60 overflow-y-auto ${dark ? 'bg-zinc-900 border-white/10' : 'bg-white border-gray-200'}`}>
                  {countries.map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => {
                        setFormData({ ...formData, country: c });
                        setShowCountryDropdown(false);
                        if (errors.country) setErrors({ ...errors, country: '' });
                      }}
                      className={`w-full px-4 py-2 text-left text-sm ${dark ? 'hover:bg-white/5 text-white' : 'hover:bg-gray-50 text-black'}`}
                    >
                      {c}
                    </button>
                  ))}
                </div>
              )}
              {errors.country && <p className="text-red-500 text-xs mt-1">{errors.country}</p>}
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
                className={`w-full px-4 py-3 border rounded-xl focus:outline-none focus:ring-2 focus:border-transparent transition ${errors.password ? 'border-red-500' : ''} ${dark ? 'bg-white/5 border-white/10 text-white focus:ring-white/30' : 'bg-gray-50 border-gray-200 text-black focus:ring-black'}`}
              />
              {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password}</p>}
            </div>

            <div>
              <label className={`block text-sm font-medium mb-2 ${dark ? 'text-white/70' : 'text-gray-700'}`}>
                Confirm Password <span className="text-red-500">*</span>
              </label>
              <input
                type="password"
                required
                value={formData.confirmPassword}
                onChange={(e) => {
                  setFormData({ ...formData, confirmPassword: e.target.value });
                  if (errors.confirmPassword) setErrors({ ...errors, confirmPassword: '' });
                }}
                className={`w-full px-4 py-3 border rounded-xl focus:outline-none focus:ring-2 focus:border-transparent transition ${errors.confirmPassword ? 'border-red-500' : ''} ${dark ? 'bg-white/5 border-white/10 text-white focus:ring-white/30' : 'bg-gray-50 border-gray-200 text-black focus:ring-black'}`}
              />
              {errors.confirmPassword && <p className="text-red-500 text-xs mt-1">{errors.confirmPassword}</p>}
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
              {loading ? 'Creating account...' : 'Create Account'}
            </button>
          </form>

          <p className={`text-center text-sm mt-6 ${dark ? 'text-white/50' : 'text-gray-500'}`}>
            Already have an account?{' '}
            <Link href="/login" className={dark ? 'text-white font-medium hover:underline' : 'text-black font-medium hover:underline'}>Sign in</Link>
          </p>
        </div>

        <p className={`text-center text-xs mt-6 ${dark ? 'text-white/40' : 'text-gray-400'}`}>
          By signing up, you agree to our Terms of Service and{' '}
          <Link href="/privacy" className={dark ? 'text-white/60 hover:text-white underline' : 'text-gray-600 hover:text-black underline'}>Privacy Policy</Link>.
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
