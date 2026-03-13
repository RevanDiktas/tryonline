'use client'

import { useSearchParams } from 'next/navigation'
import Link from 'next/link'

/**
 * App landing: tryon.global/app
 * - When opened from Shopify (URL has ?shop=...): show only brand onboarding ("Launch Your Brand").
 * - When opened on the main website (no shop param): show both shopper and brand options.
 */
export default function AppLandingPage() {
  const searchParams = useSearchParams()
  const shop = searchParams.get('shop')
  const isShopifyApp = Boolean(shop?.includes('.myshopify.com'))

  const dashboardUrl = shop ? `/app/dashboard?shop=${encodeURIComponent(shop)}` : '/app/dashboard'

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-white/10">
        <span className="text-xl font-semibold tracking-tight">Tryon</span>
        <Link
          href="/"
          className="text-sm font-medium text-white/80 hover:text-white transition-colors"
        >
          Sign In
        </Link>
      </header>

      {/* Main */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-12">
        <h1 className="text-3xl md:text-4xl font-bold text-center text-white/95 mb-3">
          Virtual Try-On For Everyone
        </h1>
        <p className="text-center text-white/70 max-w-lg mb-10">
          Shoppers get a perfect fit. Brands reduce returns. One platform, powered by your 3D avatar.
        </p>

        {/* Onboarding options */}
        <div className="flex flex-col sm:flex-row gap-4 w-full max-w-2xl justify-center">
          {!isShopifyApp && (
            <Link
              href="/"
              className="flex flex-col items-center justify-center rounded-2xl border-2 border-white/20 bg-white/5 px-8 py-6 hover:bg-white/10 hover:border-white/30 transition-all min-h-[120px]"
            >
              <span className="text-lg font-semibold text-white">Create Your Fit Passport</span>
              <span className="text-sm text-white/60 mt-1">I&apos;m a shopper</span>
            </Link>
          )}
          <Link
            href={dashboardUrl}
            className="flex flex-col items-center justify-center rounded-2xl border-2 border-white bg-white/10 px-8 py-6 hover:bg-white/15 transition-all min-h-[120px]"
          >
            <span className="text-lg font-semibold text-white">Launch Your Brand</span>
            <span className="text-sm text-white/60 mt-1">I&apos;m a brand</span>
          </Link>
        </div>

        {/* Feature cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-14 w-full max-w-3xl">
          <div className="rounded-xl border border-white/10 bg-white/5 p-5 text-center">
            <div className="text-2xl mb-2">📷</div>
            <h3 className="font-semibold text-white mb-1">Upload Once</h3>
            <p className="text-sm text-white/60">
              Take one photo, get your personalized 3D avatar with accurate body measurements.
            </p>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/5 p-5 text-center">
            <div className="text-2xl mb-2">🌐</div>
            <h3 className="font-semibold text-white mb-1">Try On Anywhere</h3>
            <p className="text-sm text-white/60">
              Works on any brand&apos;s website. One avatar, endless possibilities.
            </p>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/5 p-5 text-center">
            <div className="text-2xl mb-2">✓</div>
            <h3 className="font-semibold text-white mb-1">Reduce Returns</h3>
            <p className="text-sm text-white/60">
              Brands see up to 40% fewer returns with accurate size recommendations.
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}
