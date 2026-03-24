'use client';

import { Suspense, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { TryonLogo } from '@/components/TryonLogo';
import {
  getCurrentUser,
  updateUserProfile,
  hasFitPassport,
  type User,
} from '@/lib/supabase-auth';

const countryCodes = [
  { code: '+31', country: 'Netherlands', flag: '\u{1F1F3}\u{1F1F1}' },
  { code: '+1', country: 'United States', flag: '\u{1F1FA}\u{1F1F8}' },
  { code: '+44', country: 'United Kingdom', flag: '\u{1F1EC}\u{1F1E7}' },
  { code: '+49', country: 'Germany', flag: '\u{1F1E9}\u{1F1EA}' },
  { code: '+33', country: 'France', flag: '\u{1F1EB}\u{1F1F7}' },
  { code: '+34', country: 'Spain', flag: '\u{1F1EA}\u{1F1F8}' },
  { code: '+39', country: 'Italy', flag: '\u{1F1EE}\u{1F1F9}' },
  { code: '+32', country: 'Belgium', flag: '\u{1F1E7}\u{1F1EA}' },
  { code: '+41', country: 'Switzerland', flag: '\u{1F1E8}\u{1F1ED}' },
  { code: '+43', country: 'Austria', flag: '\u{1F1E6}\u{1F1F9}' },
  { code: '+45', country: 'Denmark', flag: '\u{1F1E9}\u{1F1F0}' },
  { code: '+46', country: 'Sweden', flag: '\u{1F1F8}\u{1F1EA}' },
  { code: '+47', country: 'Norway', flag: '\u{1F1F3}\u{1F1F4}' },
  { code: '+48', country: 'Poland', flag: '\u{1F1F5}\u{1F1F1}' },
  { code: '+351', country: 'Portugal', flag: '\u{1F1F5}\u{1F1F9}' },
  { code: '+353', country: 'Ireland', flag: '\u{1F1EE}\u{1F1EA}' },
  { code: '+358', country: 'Finland', flag: '\u{1F1EB}\u{1F1EE}' },
  { code: '+30', country: 'Greece', flag: '\u{1F1EC}\u{1F1F7}' },
  { code: '+36', country: 'Hungary', flag: '\u{1F1ED}\u{1F1FA}' },
  { code: '+420', country: 'Czech Republic', flag: '\u{1F1E8}\u{1F1FF}' },
  { code: '+61', country: 'Australia', flag: '\u{1F1E6}\u{1F1FA}' },
  { code: '+64', country: 'New Zealand', flag: '\u{1F1F3}\u{1F1FF}' },
  { code: '+81', country: 'Japan', flag: '\u{1F1EF}\u{1F1F5}' },
  { code: '+82', country: 'South Korea', flag: '\u{1F1F0}\u{1F1F7}' },
  { code: '+86', country: 'China', flag: '\u{1F1E8}\u{1F1F3}' },
  { code: '+91', country: 'India', flag: '\u{1F1EE}\u{1F1F3}' },
  { code: '+65', country: 'Singapore', flag: '\u{1F1F8}\u{1F1EC}' },
  { code: '+971', country: 'UAE', flag: '\u{1F1E6}\u{1F1EA}' },
  { code: '+966', country: 'Saudi Arabia', flag: '\u{1F1F8}\u{1F1E6}' },
  { code: '+55', country: 'Brazil', flag: '\u{1F1E7}\u{1F1F7}' },
  { code: '+52', country: 'Mexico', flag: '\u{1F1F2}\u{1F1FD}' },
  { code: '+27', country: 'South Africa', flag: '\u{1F1FF}\u{1F1E6}' },
  { code: '+90', country: 'Turkey', flag: '\u{1F1F9}\u{1F1F7}' },
];

const countries = [
  'Netherlands', 'United States', 'United Kingdom', 'Germany', 'France',
  'Spain', 'Italy', 'Belgium', 'Switzerland', 'Austria', 'Denmark',
  'Sweden', 'Norway', 'Poland', 'Portugal', 'Ireland', 'Finland',
  'Greece', 'Hungary', 'Czech Republic', 'Australia', 'New Zealand',
  'Japan', 'South Korea', 'China', 'India', 'Singapore', 'UAE',
  'Saudi Arabia', 'Brazil', 'Mexico', 'South Africa', 'Turkey',
];

function CompleteProfileInner() {
  const router = useRouter();
  const dropdownRef = useRef<HTMLDivElement>(null);
  const countryDropdownRef = useRef<HTMLDivElement>(null);

  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [phoneCode, setPhoneCode] = useState('+31');
  const [showCodeDropdown, setShowCodeDropdown] = useState(false);
  const [showCountryDropdown, setShowCountryDropdown] = useState(false);

  const [form, setForm] = useState({
    phone: '',
    dateOfBirth: '',
    country: '',
    city: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const selectedCountry = countryCodes.find(c => c.code === phoneCode) || countryCodes[0];

  useEffect(() => {
    getCurrentUser().then((u) => {
      if (!u) { router.replace('/login'); return; }
      setUser(u);
      setForm(prev => ({
        ...prev,
        country: u.country || prev.country,
        city: u.city || prev.city,
      }));
      setLoading(false);
    });
  }, [router]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) setShowCodeDropdown(false);
      if (countryDropdownRef.current && !countryDropdownRef.current.contains(event.target as Node)) setShowCountryDropdown(false);
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const isValid = form.phone.trim() && form.dateOfBirth.trim() && form.country.trim() && form.city.trim();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: Record<string, string> = {};
    if (!form.phone.trim()) newErrors.phone = 'Phone number is required';
    if (!form.dateOfBirth.trim()) newErrors.dateOfBirth = 'Date of birth is required';
    if (!form.country.trim()) newErrors.country = 'Country is required';
    if (!form.city.trim()) newErrors.city = 'City is required';
    setErrors(newErrors);
    if (Object.keys(newErrors).length > 0) return;

    setSaving(true);
    const fullPhone = `${phoneCode}${form.phone}`;
    await updateUserProfile(user!.id, {
      phone: fullPhone,
      date_of_birth: form.dateOfBirth,
      country: form.country,
      city: form.city,
    });

    const hasFP = await hasFitPassport(user!.id);
    router.replace(hasFP ? '/dashboard' : '/onboarding');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black">
        <p className="text-white/60">Loading\u2026</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-black">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <TryonLogo href="/" className="h-10 w-auto mx-auto mb-4 cursor-pointer hover:opacity-80 transition" />
          <p className="text-white/60">Almost there — a few details for your Fit Passport</p>
        </div>

        <div className="rounded-2xl p-8 shadow-sm border bg-white/[0.04] border-white/10">
          <h2 className="text-xl font-semibold text-white mb-1">Complete Your Profile</h2>
          <p className="text-white/50 text-sm mb-6">
            We need this to give you accurate sizing across brands and regions.
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Date of Birth */}
            <div>
              <label className="block text-sm font-medium text-white/70 mb-2">
                Date of Birth <span className="text-red-400">*</span>
              </label>
              <input
                type="date"
                required
                value={form.dateOfBirth}
                onChange={(e) => {
                  setForm({ ...form, dateOfBirth: e.target.value });
                  if (errors.dateOfBirth) setErrors({ ...errors, dateOfBirth: '' });
                }}
                className={`w-full px-4 py-3 bg-white/5 border rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-white/30 focus:border-transparent transition ${errors.dateOfBirth ? 'border-red-500' : 'border-white/10'}`}
              />
              {errors.dateOfBirth && <p className="text-red-400 text-xs mt-1">{errors.dateOfBirth}</p>}
            </div>

            {/* Phone */}
            <div>
              <label className="block text-sm font-medium text-white/70 mb-2">
                Phone Number <span className="text-red-400">*</span>
              </label>
              <div className="flex gap-2">
                <div className="relative" ref={dropdownRef}>
                  <button
                    type="button"
                    onClick={() => setShowCodeDropdown(!showCodeDropdown)}
                    className={`flex items-center gap-2 px-3 py-3 bg-white/5 border rounded-xl text-white hover:bg-white/10 transition min-w-[110px] ${errors.phone ? 'border-red-500' : 'border-white/10'}`}
                  >
                    <span className="text-lg">{selectedCountry.flag}</span>
                    <span className="font-medium">{phoneCode}</span>
                    <svg className="w-4 h-4 text-white/40 ml-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  {showCodeDropdown && (
                    <div className="absolute top-full left-0 mt-1 w-64 bg-neutral-900 border border-white/10 rounded-xl shadow-lg z-50 max-h-60 overflow-y-auto">
                      {countryCodes.map((c) => (
                        <button
                          key={c.code}
                          type="button"
                          onClick={() => { setPhoneCode(c.code); setShowCodeDropdown(false); }}
                          className={`w-full flex items-center gap-3 px-4 py-2.5 hover:bg-white/10 transition text-left ${phoneCode === c.code ? 'bg-white/5' : ''}`}
                        >
                          <span className="text-lg">{c.flag}</span>
                          <span className="text-white flex-1">{c.country}</span>
                          <span className="text-white/50 text-sm">{c.code}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <input
                  type="tel"
                  required
                  placeholder="6 12345678"
                  value={form.phone}
                  onChange={(e) => {
                    const value = e.target.value.replace(/[^0-9]/g, '');
                    setForm({ ...form, phone: value });
                    if (errors.phone) setErrors({ ...errors, phone: '' });
                  }}
                  className={`flex-1 px-4 py-3 bg-white/5 border rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-white/30 focus:border-transparent transition ${errors.phone ? 'border-red-500' : 'border-white/10'}`}
                />
              </div>
              {errors.phone && <p className="text-red-400 text-xs mt-1">{errors.phone}</p>}
            </div>

            {/* Country + City */}
            <div className="grid grid-cols-2 gap-3">
              <div className="relative" ref={countryDropdownRef}>
                <label className="block text-sm font-medium text-white/70 mb-2">
                  Country <span className="text-red-400">*</span>
                </label>
                <button
                  type="button"
                  onClick={() => setShowCountryDropdown(!showCountryDropdown)}
                  className={`w-full px-4 py-3 bg-white/5 border rounded-xl text-left flex items-center justify-between hover:bg-white/10 transition ${errors.country ? 'border-red-500' : 'border-white/10'}`}
                >
                  <span className={form.country ? 'text-white' : 'text-white/40'}>
                    {form.country || 'Select'}
                  </span>
                  <svg className="w-4 h-4 text-white/40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {showCountryDropdown && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-neutral-900 border border-white/10 rounded-xl shadow-lg z-50 max-h-60 overflow-y-auto">
                    {countries.map((c) => (
                      <button
                        key={c}
                        type="button"
                        onClick={() => {
                          setForm({ ...form, country: c });
                          setShowCountryDropdown(false);
                          if (errors.country) setErrors({ ...errors, country: '' });
                        }}
                        className="w-full px-4 py-2 text-left hover:bg-white/10 text-white text-sm"
                      >
                        {c}
                      </button>
                    ))}
                  </div>
                )}
                {errors.country && <p className="text-red-400 text-xs mt-1">{errors.country}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-2">
                  City <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={form.city}
                  onChange={(e) => {
                    setForm({ ...form, city: e.target.value });
                    if (errors.city) setErrors({ ...errors, city: '' });
                  }}
                  className={`w-full px-4 py-3 bg-white/5 border rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-white/30 focus:border-transparent transition ${errors.city ? 'border-red-500' : 'border-white/10'}`}
                />
                {errors.city && <p className="text-red-400 text-xs mt-1">{errors.city}</p>}
              </div>
            </div>

            <button
              type="submit"
              disabled={saving || !isValid}
              className="w-full py-3 bg-white text-black font-semibold rounded-xl hover:bg-white/90 transition disabled:opacity-40 disabled:cursor-not-allowed mt-6"
            >
              {saving ? 'Saving\u2026' : 'Continue'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default function CompleteProfilePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-black">
          <p className="text-white/60">Loading\u2026</p>
        </div>
      }
    >
      <CompleteProfileInner />
    </Suspense>
  );
}
