'use client';

import { useState, useEffect, useRef, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { signup } from '@/lib/supabase-auth';
import { registerBrand } from '@/lib/api';
import { isShopifyMode } from '@/lib/app-mode';

const countryCodes = [
  { code: '+31', country: 'Netherlands', flag: '🇳🇱' },
  { code: '+1', country: 'United States', flag: '🇺🇸' },
  { code: '+44', country: 'United Kingdom', flag: '🇬🇧' },
  { code: '+49', country: 'Germany', flag: '🇩🇪' },
  { code: '+33', country: 'France', flag: '🇫🇷' },
  { code: '+34', country: 'Spain', flag: '🇪🇸' },
  { code: '+39', country: 'Italy', flag: '🇮🇹' },
  { code: '+32', country: 'Belgium', flag: '🇧🇪' },
  { code: '+41', country: 'Switzerland', flag: '🇨🇭' },
  { code: '+43', country: 'Austria', flag: '🇦🇹' },
  { code: '+45', country: 'Denmark', flag: '🇩🇰' },
  { code: '+46', country: 'Sweden', flag: '🇸🇪' },
  { code: '+47', country: 'Norway', flag: '🇳🇴' },
  { code: '+48', country: 'Poland', flag: '🇵🇱' },
  { code: '+351', country: 'Portugal', flag: '🇵🇹' },
  { code: '+353', country: 'Ireland', flag: '🇮🇪' },
  { code: '+358', country: 'Finland', flag: '🇫🇮' },
  { code: '+30', country: 'Greece', flag: '🇬🇷' },
  { code: '+36', country: 'Hungary', flag: '🇭🇺' },
  { code: '+420', country: 'Czech Republic', flag: '🇨🇿' },
  { code: '+61', country: 'Australia', flag: '🇦🇺' },
  { code: '+64', country: 'New Zealand', flag: '🇳🇿' },
  { code: '+81', country: 'Japan', flag: '🇯🇵' },
  { code: '+82', country: 'South Korea', flag: '🇰🇷' },
  { code: '+86', country: 'China', flag: '🇨🇳' },
  { code: '+91', country: 'India', flag: '🇮🇳' },
  { code: '+65', country: 'Singapore', flag: '🇸🇬' },
  { code: '+971', country: 'UAE', flag: '🇦🇪' },
  { code: '+966', country: 'Saudi Arabia', flag: '🇸🇦' },
  { code: '+55', country: 'Brazil', flag: '🇧🇷' },
  { code: '+52', country: 'Mexico', flag: '🇲🇽' },
  { code: '+27', country: 'South Africa', flag: '🇿🇦' },
  { code: '+90', country: 'Turkey', flag: '🇹🇷' },
  { code: '+7', country: 'Russia', flag: '🇷🇺' },
  { code: '+380', country: 'Ukraine', flag: '🇺🇦' },
  { code: '+62', country: 'Indonesia', flag: '🇮🇩' },
  { code: '+60', country: 'Malaysia', flag: '🇲🇾' },
  { code: '+66', country: 'Thailand', flag: '🇹🇭' },
  { code: '+84', country: 'Vietnam', flag: '🇻🇳' },
  { code: '+63', country: 'Philippines', flag: '🇵🇭' },
];

const countries = [
  'Netherlands', 'United States', 'United Kingdom', 'Germany', 'France',
  'Spain', 'Italy', 'Belgium', 'Switzerland', 'Austria', 'Denmark',
  'Sweden', 'Norway', 'Poland', 'Portugal', 'Ireland', 'Finland',
  'Greece', 'Hungary', 'Czech Republic', 'Australia', 'New Zealand',
  'Japan', 'South Korea', 'China', 'India', 'Singapore', 'UAE',
  'Saudi Arabia', 'Brazil', 'Mexico', 'South Africa', 'Turkey',
  'Russia', 'Ukraine', 'Indonesia', 'Malaysia', 'Thailand', 'Vietnam', 'Philippines'
];

function SignupContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const dropdownRef = useRef<HTMLDivElement>(null);
  const countryDropdownRef = useRef<HTMLDivElement>(null);
  const shopifyMode = isShopifyMode();

  // Determine initial state from query param or APP_MODE
  const typeParam = searchParams.get('type');
  const shopParam = searchParams.get('shop') ?? '';
  const preselected = shopifyMode ? 'brand' : (typeParam === 'brand' ? 'brand' : typeParam === 'shopper' ? 'shopper' : null);
  const skipSelection = shopifyMode || preselected !== null;

  const [step, setStep] = useState<'user_type' | 'details'>(skipSelection ? 'details' : 'user_type');
  const [userType, setUserType] = useState<'shopper' | 'brand'>(preselected || 'shopper');

  const [phoneCode, setPhoneCode] = useState('+31');
  const [showCodeDropdown, setShowCodeDropdown] = useState(false);
  const [showCountryDropdown, setShowCountryDropdown] = useState(false);

  const [formData, setFormData] = useState({
    // Shared
    email: '',
    password: '',
    confirmPassword: '',
    phone: '',
    country: '',
    // Shopper-only
    name: '',
    dateOfBirth: '',
    city: '',
    // Brand-only
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

    if (userType === 'brand') {
      if (!formData.brandName.trim()) newErrors.brandName = 'Brand name is required';
      if (!formData.contactName.trim()) newErrors.contactName = 'Contact name is required';
    } else {
      if (!formData.name.trim()) newErrors.name = 'Full name is required';
      if (!formData.city.trim()) newErrors.city = 'City is required';
    }

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
      const displayName = userType === 'brand' ? formData.contactName : formData.name;

      const { user, error } = await signup({
        email: formData.email,
        password: formData.password,
        name: displayName,
        phone: fullPhone,
        dateOfBirth: userType === 'shopper' ? formData.dateOfBirth || undefined : undefined,
        country: formData.country,
        city: userType === 'shopper' ? formData.city : undefined,
        userType,
      });

      if (error) { setErrors({ form: error }); return; }
      if (!user) { setErrors({ form: 'Signup failed' }); return; }

      // For brands, create the brand record in the brands table
      if (userType === 'brand') {
        const brandRes = await registerBrand({
          user_id: user.id,
          brand_name: formData.brandName,
          email: formData.email,
          phone: fullPhone,
          country: formData.country,
          shopify_domain: formData.shopifyDomain || shopParam || undefined,
        });
        if (!brandRes.ok) {
          setErrors({ form: brandRes.error || 'Failed to create brand record' });
          return;
        }
      }

      // Route directly — Supabase signup auto-signs in the user
      if (userType === 'brand') {
        router.push('/brand');
      } else {
        router.push('/onboarding');
      }
    } catch {
      setErrors({ form: 'Something went wrong. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  // --- User type selection screen ---
  if (step === 'user_type') {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <Link href="/">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/tryon-logo.jpg" alt="TRYON" className="h-14 w-auto mx-auto mb-4 cursor-pointer hover:opacity-80 transition" />
            </Link>
            <p className="text-gray-500">Join the future of fashion</p>
          </div>

          <div className="bg-white border border-gray-200 rounded-2xl p-8 shadow-sm">
            <h2 className="text-xl font-semibold text-black mb-2 text-center">How will you use TryOn?</h2>
            <p className="text-gray-500 text-sm text-center mb-8">Select your account type to get started</p>

            <div className="space-y-4">
              <button
                onClick={() => { setUserType('shopper'); setStep('details'); }}
                className="w-full p-6 border-2 border-gray-200 rounded-2xl hover:border-black hover:bg-gray-50 transition-all group text-left"
              >
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center flex-shrink-0">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-semibold text-black text-lg group-hover:text-black">I&apos;m a Shopper</h3>
                    <p className="text-gray-500 text-sm mt-1">Create your Fit Passport and try on clothes virtually before you buy</p>
                  </div>
                </div>
              </button>

              <button
                onClick={() => { setUserType('brand'); setStep('details'); }}
                className="w-full p-6 border-2 border-gray-200 rounded-2xl hover:border-black hover:bg-gray-50 transition-all group text-left"
              >
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-gradient-to-br from-orange-500 to-pink-600 rounded-xl flex items-center justify-center flex-shrink-0">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-semibold text-black text-lg group-hover:text-black">I&apos;m a Brand</h3>
                    <p className="text-gray-500 text-sm mt-1">Add virtual try-on to your store and reduce returns by up to 40%</p>
                  </div>
                </div>
              </button>
            </div>
          </div>

          <p className="text-center text-gray-500 text-sm mt-6">
            Already have an account?{' '}
            <Link href="/login" className="text-black font-medium hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    );
  }

  // --- Details form ---
  const isBrand = userType === 'brand';

  const isFormValid = isBrand
    ? formData.brandName.trim() && formData.contactName.trim() && formData.email.trim() && formData.phone.trim() && formData.country.trim() && formData.password && formData.confirmPassword && formData.password === formData.confirmPassword && formData.password.length >= 6
    : formData.name.trim() && formData.email.trim() && formData.phone.trim() && formData.country.trim() && formData.city.trim() && formData.password && formData.confirmPassword && formData.password === formData.confirmPassword && formData.password.length >= 6;

  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link href="/">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/tryon-logo.jpg" alt="TRYON" className="h-14 w-auto mx-auto mb-4 cursor-pointer hover:opacity-80 transition" />
          </Link>
          <p className="text-gray-500">
            {isBrand ? 'Set up your brand account' : 'Create your Fit Passport'}
          </p>
        </div>

        <div className="bg-white border border-gray-200 rounded-2xl p-8 shadow-sm">
          {/* Back button (only on website mode where user chose type) */}
          {!shopifyMode && (
            <button
              onClick={() => { setStep('user_type'); setUserType('shopper'); }}
              className="flex items-center gap-2 text-gray-500 hover:text-black mb-4 transition"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back
            </button>
          )}

          <div className="flex items-center gap-3 mb-6">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
              isBrand ? 'bg-gradient-to-br from-orange-500 to-pink-600' : 'bg-gradient-to-br from-blue-500 to-purple-600'
            }`}>
              {isBrand ? (
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
              ) : (
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              )}
            </div>
            <div>
              <h2 className="text-xl font-semibold text-black">
                {isBrand ? 'Brand Account' : 'Shopper Account'}
              </h2>
              <p className="text-gray-500 text-sm">Enter your details below</p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* === BRAND FIELDS === */}
            {isBrand && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
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
                    className={`w-full px-4 py-3 bg-gray-50 border rounded-xl text-black focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent transition ${errors.brandName ? 'border-red-500' : 'border-gray-200'}`}
                  />
                  {errors.brandName && <p className="text-red-500 text-xs mt-1">{errors.brandName}</p>}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
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
                    className={`w-full px-4 py-3 bg-gray-50 border rounded-xl text-black focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent transition ${errors.contactName ? 'border-red-500' : 'border-gray-200'}`}
                  />
                  {errors.contactName && <p className="text-red-500 text-xs mt-1">{errors.contactName}</p>}
                </div>
              </>
            )}

            {/* === SHOPPER FIELDS === */}
            {!isBrand && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Full Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => {
                    setFormData({ ...formData, name: e.target.value });
                    if (errors.name) setErrors({ ...errors, name: '' });
                  }}
                  className={`w-full px-4 py-3 bg-gray-50 border rounded-xl text-black focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent transition ${errors.name ? 'border-red-500' : 'border-gray-200'}`}
                />
                {errors.name && <p className="text-red-500 text-xs mt-1">{errors.name}</p>}
              </div>
            )}

            {/* === SHARED FIELDS === */}

            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {isBrand ? 'Business Email' : 'Email'} <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                required
                value={formData.email}
                onChange={(e) => {
                  setFormData({ ...formData, email: e.target.value });
                  if (errors.email) setErrors({ ...errors, email: '' });
                }}
                className={`w-full px-4 py-3 bg-gray-50 border rounded-xl text-black focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent transition ${errors.email ? 'border-red-500' : 'border-gray-200'}`}
              />
              {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email}</p>}
            </div>

            {/* Phone */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Phone Number <span className="text-red-500">*</span>
              </label>
              <div className="flex gap-2">
                <div className="relative" ref={dropdownRef}>
                  <button
                    type="button"
                    onClick={() => setShowCodeDropdown(!showCodeDropdown)}
                    className={`flex items-center gap-2 px-3 py-3 bg-gray-50 border rounded-xl text-black hover:bg-gray-100 transition min-w-[110px] ${errors.phone ? 'border-red-500' : 'border-gray-200'}`}
                  >
                    <span className="text-lg">{selectedCountry.flag}</span>
                    <span className="font-medium">{phoneCode}</span>
                    <svg className="w-4 h-4 text-gray-400 ml-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  {showCodeDropdown && (
                    <div className="absolute top-full left-0 mt-1 w-64 bg-white border border-gray-200 rounded-xl shadow-lg z-50 max-h-60 overflow-y-auto">
                      {countryCodes.map((c) => (
                        <button
                          key={c.code}
                          type="button"
                          onClick={() => { setPhoneCode(c.code); setShowCodeDropdown(false); }}
                          className={`w-full flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 transition text-left ${phoneCode === c.code ? 'bg-gray-100' : ''}`}
                        >
                          <span className="text-lg">{c.flag}</span>
                          <span className="text-black flex-1">{c.country}</span>
                          <span className="text-gray-500 text-sm">{c.code}</span>
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
                  className={`flex-1 px-4 py-3 bg-gray-50 border rounded-xl text-black focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent transition ${errors.phone ? 'border-red-500' : 'border-gray-200'}`}
                />
              </div>
              {errors.phone && <p className="text-red-500 text-xs mt-1">{errors.phone}</p>}
            </div>

            {/* Date of birth — shopper only */}
            {!isBrand && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Date of Birth</label>
                <input
                  type="date"
                  value={formData.dateOfBirth}
                  onChange={(e) => setFormData({ ...formData, dateOfBirth: e.target.value })}
                  className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-black focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent transition"
                />
              </div>
            )}

            {/* Shopify domain — brand only, optional */}
            {isBrand && !shopifyMode && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Shopify Store URL <span className="text-gray-400 font-normal">(optional)</span>
                </label>
                <div className="flex items-center gap-0">
                  <input
                    type="text"
                    placeholder="your-store"
                    value={formData.shopifyDomain}
                    onChange={(e) => setFormData({ ...formData, shopifyDomain: e.target.value.replace(/\s/g, '').toLowerCase() })}
                    className="flex-1 px-4 py-3 bg-gray-50 border border-gray-200 rounded-l-xl text-black focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent transition"
                  />
                  <span className="px-3 py-3 bg-gray-100 border border-l-0 border-gray-200 rounded-r-xl text-gray-500 text-sm whitespace-nowrap">.myshopify.com</span>
                </div>
                <p className="text-gray-400 text-xs mt-1">You can connect your store later from the dashboard</p>
              </div>
            )}

            {/* Country (+ City for shoppers) */}
            <div className={!isBrand ? 'grid grid-cols-2 gap-3' : ''}>
              <div className="relative" ref={countryDropdownRef}>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Country <span className="text-red-500">*</span>
                </label>
                <button
                  type="button"
                  onClick={() => setShowCountryDropdown(!showCountryDropdown)}
                  className={`w-full px-4 py-3 bg-gray-50 border rounded-xl text-left flex items-center justify-between hover:bg-gray-100 transition ${errors.country ? 'border-red-500' : 'border-gray-200'}`}
                >
                  <span className={formData.country ? 'text-black' : 'text-gray-400'}>
                    {formData.country || 'Select country'}
                  </span>
                  <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {showCountryDropdown && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-xl shadow-lg z-50 max-h-60 overflow-y-auto">
                    {countries.map((c) => (
                      <button
                        key={c}
                        type="button"
                        onClick={() => {
                          setFormData({ ...formData, country: c });
                          setShowCountryDropdown(false);
                          if (errors.country) setErrors({ ...errors, country: '' });
                        }}
                        className="w-full px-4 py-2 text-left hover:bg-gray-50 text-black text-sm"
                      >
                        {c}
                      </button>
                    ))}
                  </div>
                )}
                {errors.country && <p className="text-red-500 text-xs mt-1">{errors.country}</p>}
              </div>

              {!isBrand && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    City <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.city}
                    onChange={(e) => {
                      setFormData({ ...formData, city: e.target.value });
                      if (errors.city) setErrors({ ...errors, city: '' });
                    }}
                    className={`w-full px-4 py-3 bg-gray-50 border rounded-xl text-black focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent transition ${errors.city ? 'border-red-500' : 'border-gray-200'}`}
                  />
                  {errors.city && <p className="text-red-500 text-xs mt-1">{errors.city}</p>}
                </div>
              )}
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
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
                className={`w-full px-4 py-3 bg-gray-50 border rounded-xl text-black focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent transition ${errors.password ? 'border-red-500' : 'border-gray-200'}`}
              />
              {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
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
                className={`w-full px-4 py-3 bg-gray-50 border rounded-xl text-black focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent transition ${errors.confirmPassword ? 'border-red-500' : 'border-gray-200'}`}
              />
              {errors.confirmPassword && <p className="text-red-500 text-xs mt-1">{errors.confirmPassword}</p>}
            </div>

            {errors.form && (
              <div className="text-red-600 text-sm bg-red-50 border border-red-100 rounded-lg p-3">
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

          <p className="text-center text-gray-500 text-sm mt-6">
            Already have an account?{' '}
            <Link href="/login" className="text-black font-medium hover:underline">Sign in</Link>
          </p>
        </div>

        <p className="text-center text-gray-400 text-xs mt-6">
          By signing up, you agree to our Terms of Service and Privacy Policy
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
