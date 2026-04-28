'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useTheme } from '@/contexts/ThemeContext';
import { getCurrentUser, type User } from '@/lib/supabase-auth';
import { isShopifyMode } from '@/lib/app-mode';
import { useEnsureShopifyAdminOAuth } from '@/lib/useEnsureShopifyAdminOAuth';
import { useResolvedShopifyShop } from '@/lib/useResolvedShopifyShop';
import { BroadcastLanding } from '@/components/redesign/Broadcast';

function HomePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { theme } = useTheme();
  const dark = theme === 'dark';
  const shopifyMode = isShopifyMode();
  const resolvedShop = useResolvedShopifyShop();
  useEnsureShopifyAdminOAuth(resolvedShop, searchParams.get('error'));

  const [checking, setChecking] = useState(true);
  const [showLanding, setShowLanding] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const u: User | null = await getCurrentUser();
        if (!active) return;

        if (u) {
          // Signed-in users skip the marketing page and go to their workspace.
          if (u.user_type === 'brand') {
            const target = resolvedShop ? `/brand?shop=${encodeURIComponent(resolvedShop)}` : '/brand';
            router.replace(target);
          } else {
            router.replace('/dashboard');
          }
          return;
        }

        // In Shopify-admin context we never want to render the public marketing
        // landing — bounce straight into brand sign-in/up.
        if (shopifyMode) {
          router.replace(resolvedShop ? `/login?shop=${encodeURIComponent(resolvedShop)}` : '/login');
          return;
        }

        setShowLanding(true);
      } catch (e) {
        console.error('[HomePage] Auth check error:', e);
        setShowLanding(true); // fall back to landing on auth error
      } finally {
        if (active) setChecking(false);
      }
    })();
    return () => { active = false; };
  }, [router, shopifyMode, resolvedShop]);

  if (checking || !showLanding) {
    return (
      <div className={`min-h-screen flex items-center justify-center transition-colors ${dark ? 'bg-black' : 'bg-white'}`}>
        <div className={dark ? 'text-white/50' : 'text-gray-400'}>Loading…</div>
      </div>
    );
  }

  return <BroadcastLanding dark={dark} />;
}

export default function HomePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-gray-400">Loading…</div>
      </div>
    }>
      <HomePageContent />
    </Suspense>
  );
}
