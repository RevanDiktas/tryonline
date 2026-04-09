'use client';

import { useEffect, useState, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { TryonLogo } from '@/components/TryonLogo';
import { useTheme } from '@/contexts/ThemeContext';
import { getCurrentUser, type User } from '@/lib/supabase-auth';
import { getMyBrand } from '@/lib/api';
import { isShopifyMode } from '@/lib/app-mode';
import { useEnsureShopifyAdminOAuth } from '@/lib/useEnsureShopifyAdminOAuth';
import { useRouter } from 'next/navigation';

function HomePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { theme } = useTheme();
  const dark = theme === 'dark';
  const [user, setUser] = useState<User | null>(null);
  const [brandName, setBrandName] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);
  const shopifyMode = isShopifyMode();
  const shop = searchParams.get('shop');
  const isShopifyApp = Boolean(shop?.includes('.myshopify.com'));
  useEnsureShopifyAdminOAuth(shop, searchParams.get('error'));

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const u = await getCurrentUser();
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
      <div className={`min-h-screen flex items-center justify-center transition-colors ${dark ? 'bg-black' : 'bg-white'}`}>
        <div className={dark ? 'text-white/50' : 'text-gray-400'}>Loading...</div>
      </div>
    );
  }

  const dashboardUrl = user?.user_type === 'brand' ? (shop ? `/brand?shop=${encodeURIComponent(shop)}` : '/brand') : '/dashboard';

  return (
    <div className={`min-h-screen transition-colors ${dark ? 'bg-black' : 'bg-white'}`}>
      <header className={`absolute top-0 left-0 right-0 z-10 border-b md:border-0 ${dark ? 'bg-black md:bg-transparent border-white/10' : 'bg-white md:bg-transparent border-gray-100'}`}>
        <div className="max-w-6xl mx-auto px-4 py-4 md:px-6 md:py-6 flex items-center justify-between">
          <TryonLogo className="h-8 w-auto md:h-10" href="/" />

          {user ? (
            <div className="flex items-center gap-3 md:gap-4">
              <span className={`text-sm hidden sm:inline ${dark ? 'text-white/60' : 'text-gray-600'}`}>
                {user.user_type === 'brand' ? (brandName || user.name || user.email) : (user.name || user.email)}
              </span>
              <Link
                href={dashboardUrl}
                className={`px-4 py-2 md:px-6 md:py-2.5 font-medium rounded-xl transition text-sm ${dark ? 'bg-white text-black hover:bg-white/90' : 'bg-black text-white hover:bg-gray-800'}`}
              >
                {user.user_type === 'brand' ? 'Brand Dashboard' : 'My Dashboard'}
              </Link>
            </div>
          ) : (
            <Link
              href="/login"
              className={`px-4 py-2 md:px-6 md:py-2.5 font-medium rounded-xl transition text-sm ${dark ? 'bg-white text-black hover:bg-white/90' : 'bg-black text-white hover:bg-gray-800'}`}
            >
              Sign In
            </Link>
          )}
        </div>
      </header>

      <main className="relative min-h-screen flex items-start md:items-center justify-center px-4 pt-20 md:pt-0">
        <div className="relative text-center max-w-3xl mx-auto pt-4 md:pt-0">
          <h2 className={`text-5xl md:text-7xl font-bold mb-6 leading-tight ${dark ? 'text-white' : 'text-black'}`}>
            Virtual Try-On
            <br />
            <span className={dark ? 'text-white/50' : 'text-gray-400'}>For Everyone</span>
          </h2>

          <p className={`text-xl mb-12 max-w-xl mx-auto ${dark ? 'text-white/60' : 'text-gray-500'}`}>
            {isShopifyApp || shopifyMode
              ? 'Add virtual try-on to your store. Shoppers see fit before they buy.'
              : 'Shoppers get a perfect fit. Brands reduce returns. One platform, powered by your 3D avatar.'}
          </p>

          {user ? (
            <Link
              href={dashboardUrl}
              className={`inline-block px-8 py-5 font-semibold rounded-2xl transition text-lg ${dark ? 'bg-white text-black hover:bg-white/90' : 'bg-black text-white hover:bg-gray-800'}`}
            >
              {user.user_type === 'brand' ? 'Go to Brand Dashboard' : 'Go to My Dashboard'}
            </Link>
          ) : isShopifyApp ? (
            <div className="flex flex-col sm:flex-row gap-4 justify-center max-w-lg mx-auto">
              <Link
                href={shop ? `/signup?type=brand&shop=${encodeURIComponent(shop)}` : '/signup?type=brand'}
                className={`flex-1 group relative overflow-hidden px-8 py-5 font-semibold rounded-2xl border-2 transition text-center ${dark ? 'bg-transparent text-white border-white/30 hover:bg-white/10' : 'bg-white text-black border-black hover:bg-gray-50'}`}
              >
                <span className="block text-lg">Launch Your Brand</span>
                <span className={`block text-sm font-normal mt-1 ${dark ? 'text-white/60' : 'text-gray-500'}`}>I&apos;m a brand</span>
              </Link>
            </div>
          ) : shopifyMode ? (
            <div className="flex flex-col gap-4 justify-center max-w-md mx-auto">
              <Link
                href="/login"
                className={`px-8 py-5 font-semibold rounded-2xl transition text-center text-lg ${dark ? 'bg-white text-black hover:bg-white/90' : 'bg-black text-white hover:bg-gray-800'}`}
              >
                Sign In
              </Link>
              <Link
                href="/signup?type=brand"
                className={`px-8 py-5 font-semibold rounded-2xl border-2 transition text-center text-lg ${dark ? 'bg-transparent text-white border-white/30 hover:bg-white/10' : 'bg-white text-black border-black hover:bg-gray-50'}`}
              >
                Create Brand Account
              </Link>
            </div>
          ) : (
            <div className="flex flex-col sm:flex-row gap-4 justify-center max-w-lg mx-auto">
              <Link
                href="/signup?type=shopper"
                className={`flex-1 group relative overflow-hidden px-8 py-5 font-semibold rounded-2xl transition text-center ${dark ? 'bg-white text-black hover:bg-white/90' : 'bg-black text-white hover:bg-gray-800'}`}
              >
                <span className="block text-lg">Create Your Fit Passport</span>
                <span className={`block text-sm font-normal mt-1 ${dark ? 'text-black/60' : 'text-white/60'}`}>I&apos;m a shopper</span>
              </Link>
              <Link
                href="/signup?type=brand"
                className={`flex-1 group relative overflow-hidden px-8 py-5 font-semibold rounded-2xl border-2 transition text-center ${dark ? 'bg-transparent text-white border-white/30 hover:bg-white/10' : 'bg-white text-black border-black hover:bg-gray-50'}`}
              >
                <span className="block text-lg">Launch Your Brand</span>
                <span className={`block text-sm font-normal mt-1 ${dark ? 'text-white/60' : 'text-gray-500'}`}>I&apos;m a brand</span>
              </Link>
            </div>
          )}

          <div className="grid md:grid-cols-3 gap-6 mt-20">
            <div className={`rounded-2xl p-6 text-left border ${dark ? 'bg-white/[0.04] border-white/10' : 'bg-white border-gray-200 shadow-sm'}`}>
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 ${dark ? 'bg-white/10' : 'bg-gray-100'}`}>
                <svg className={`w-6 h-6 ${dark ? 'text-white/70' : 'text-gray-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <h3 className={`font-semibold mb-2 ${dark ? 'text-white' : 'text-black'}`}>Upload Once</h3>
              <p className={dark ? 'text-white/50 text-sm' : 'text-gray-500 text-sm'}>
                Take one photo, get your personalized 3D avatar with accurate body measurements
              </p>
            </div>
            <div className={`rounded-2xl p-6 text-left border ${dark ? 'bg-white/[0.04] border-white/10' : 'bg-white border-gray-200 shadow-sm'}`}>
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 ${dark ? 'bg-white/10' : 'bg-gray-100'}`}>
                <svg className={`w-6 h-6 ${dark ? 'text-white/70' : 'text-gray-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                </svg>
              </div>
              <h3 className={`font-semibold mb-2 ${dark ? 'text-white' : 'text-black'}`}>Try On Anywhere</h3>
              <p className={dark ? 'text-white/50 text-sm' : 'text-gray-500 text-sm'}>
                Works on any brand&apos;s website. One avatar, endless possibilities
              </p>
            </div>
            <div className={`rounded-2xl p-6 text-left border ${dark ? 'bg-white/[0.04] border-white/10' : 'bg-white border-gray-200 shadow-sm'}`}>
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 ${dark ? 'bg-white/10' : 'bg-gray-100'}`}>
                <svg className={`w-6 h-6 ${dark ? 'text-white/70' : 'text-gray-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className={`font-semibold mb-2 ${dark ? 'text-white' : 'text-black'}`}>Reduce Returns</h3>
              <p className={dark ? 'text-white/50 text-sm' : 'text-gray-500 text-sm'}>
                Accurate size recommendations help shoppers choose the right fit and reduce returns
              </p>
            </div>
          </div>

          <footer className="mt-24 pb-8 text-center">
            <Link href="/privacy" className={`text-sm transition ${dark ? 'text-white/50 hover:text-white' : 'text-gray-500 hover:text-black'}`}>
              Privacy Policy
            </Link>
          </footer>
        </div>
      </main>
    </div>
  );
}

export default function HomePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="text-gray-400">Loading...</div>
      </div>
    }>
      <HomePageContent />
    </Suspense>
  );
}
