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
  const [showLanding, setShowLanding] = useState(!shopifyMode);

  useEffect(() => {
    let active = true;
    (async () => {
      // The marketing page is for everyone - even signed-in users. Clicking
      // the TRYON wordmark from the dashboard should land here without an
      // auto-bounce back. Auth state still drives the nav buttons.
      if (shopifyMode) {
        try {
          const u: User | null = await getCurrentUser();
          if (!active) return;
          // Inside Shopify-admin, never render the public marketing page.
          if (!u) {
            router.replace(resolvedShop ? `/login?shop=${encodeURIComponent(resolvedShop)}` : '/login');
          } else if (u.user_type === 'brand') {
            router.replace(resolvedShop ? `/brand?shop=${encodeURIComponent(resolvedShop)}` : '/brand');
          } else {
            router.replace('/dashboard');
          }
        } catch (e) {
          console.error('[HomePage] Auth check error in shopifyMode:', e);
          router.replace('/login');
        } finally {
          if (active) setChecking(false);
        }
        return;
      }
      // Public web: render the landing immediately.
      if (active) setChecking(false);
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
