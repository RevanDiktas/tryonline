'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getCurrentUser, type User } from '@/lib/supabase-auth';
import { getMyBrand } from '@/lib/api';
import { isShopifyMode } from '@/lib/app-mode';
import { useRouter } from 'next/navigation';

export default function HomePage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [brandName, setBrandName] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);
  const shopifyMode = isShopifyMode();

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const u = await getCurrentUser();
        if (shopifyMode && !u) {
          router.push('/signup');
          return;
        }
        setUser(u);
        if (u?.user_type === 'brand') {
          const brand = await getMyBrand(u.id);
          if (brand?.name) setBrandName(brand.name as string);
        }
      } catch (error) {
        console.error('[HomePage] Auth check error:', error);
      } finally {
        setChecking(false);
      }
    };
    checkAuth();
  }, [router, shopifyMode]);

  if (checking) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-gray-400">Loading...</div>
      </div>
    );
  }

  const dashboardUrl = user?.user_type === 'brand' ? '/brand' : '/dashboard';

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="absolute top-0 left-0 right-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-6 flex items-center justify-between">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/tryon-logo.jpg" alt="TRYON" className="h-14 w-auto" />

          {user ? (
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600 hidden sm:inline">
                {user.user_type === 'brand' ? (brandName || user.name || user.email) : (user.name || user.email)}
              </span>
              <Link
                href={dashboardUrl}
                className="px-6 py-2.5 bg-black text-white font-medium rounded-xl hover:bg-gray-800 transition text-sm"
              >
                {user.user_type === 'brand' ? 'Brand Dashboard' : 'My Dashboard'}
              </Link>
            </div>
          ) : (
            <Link
              href="/login"
              className="px-6 py-2.5 bg-black text-white font-medium rounded-xl hover:bg-gray-800 transition text-sm"
            >
              Sign In
            </Link>
          )}
        </div>
      </header>

      {/* Hero */}
      <main className="relative min-h-screen flex items-center justify-center px-4">
        <div className="relative text-center max-w-3xl mx-auto">
          <h2 className="text-5xl md:text-7xl font-bold text-black mb-6 leading-tight">
            Virtual Try-On
            <br />
            <span className="text-gray-400">For Everyone</span>
          </h2>

          <p className="text-xl text-gray-500 mb-12 max-w-xl mx-auto">
            Shoppers get a perfect fit. Brands reduce returns.
            One platform, powered by your 3D avatar.
          </p>

          {/* Two CTAs — show signup buttons when logged out, dashboard when logged in */}
          {user ? (
            <Link
              href={dashboardUrl}
              className="inline-block px-8 py-5 bg-black text-white font-semibold rounded-2xl hover:bg-gray-800 transition text-lg"
            >
              {user.user_type === 'brand' ? 'Go to Brand Dashboard' : 'Go to My Dashboard'}
            </Link>
          ) : (
            <div className="flex flex-col sm:flex-row gap-4 justify-center max-w-lg mx-auto">
              <Link
                href="/signup?type=shopper"
                className="flex-1 group relative overflow-hidden px-8 py-5 bg-black text-white font-semibold rounded-2xl hover:bg-gray-800 transition text-center"
              >
                <span className="block text-lg">Create Your Fit Passport</span>
                <span className="block text-sm font-normal text-white/60 mt-1">I&apos;m a shopper</span>
              </Link>

              <Link
                href="/signup?type=brand"
                className="flex-1 group relative overflow-hidden px-8 py-5 bg-white text-black font-semibold rounded-2xl border-2 border-black hover:bg-gray-50 transition text-center"
              >
                <span className="block text-lg">Launch Your Brand</span>
                <span className="block text-sm font-normal text-gray-500 mt-1">I&apos;m a brand</span>
              </Link>
            </div>
          )}

          {/* Features */}
          <div className="grid md:grid-cols-3 gap-6 mt-20">
            <div className="bg-white border border-gray-200 rounded-2xl p-6 text-left shadow-sm">
              <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <h3 className="text-black font-semibold mb-2">Upload Once</h3>
              <p className="text-gray-500 text-sm">
                Take one photo, get your personalized 3D avatar with accurate body measurements
              </p>
            </div>

            <div className="bg-white border border-gray-200 rounded-2xl p-6 text-left shadow-sm">
              <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                </svg>
              </div>
              <h3 className="text-black font-semibold mb-2">Try On Anywhere</h3>
              <p className="text-gray-500 text-sm">
                Works on any brand&apos;s website. One avatar, endless possibilities
              </p>
            </div>

            <div className="bg-white border border-gray-200 rounded-2xl p-6 text-left shadow-sm">
              <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-black font-semibold mb-2">Reduce Returns</h3>
              <p className="text-gray-500 text-sm">
                Brands see up to 40% fewer returns with accurate size recommendations
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
