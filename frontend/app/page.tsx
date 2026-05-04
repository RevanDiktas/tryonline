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

  const [redirecting, setRedirecting] = useState(shopifyMode);

  useEffect(() => {
    if (!shopifyMode) return;
    let active = true;
    (async () => {
      try {
        const u: User | null = await getCurrentUser();
        if (!active) return;
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
        if (active) setRedirecting(false);
      }
    })();
    return () => { active = false; };
  }, [router, shopifyMode, resolvedShop]);

  if (shopifyMode && redirecting) {
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
    <Suspense fallback={<BroadcastLanding dark={false} />}>
      <HomePageContent />
    </Suspense>
  );
}
