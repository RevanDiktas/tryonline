'use client'

import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Camera, Globe, CheckCircle } from 'lucide-react'

/**
 * App landing: tryon.global/app
 * Same structure as main site. When opened from Shopify (?shop=...): show only "Launch Your Brand".
 * Otherwise show both shopper and brand options.
 */
export default function AppLandingPage() {
  const searchParams = useSearchParams()
  const shop = searchParams.get('shop')
  const isShopifyApp = Boolean(shop?.includes('.myshopify.com'))

  const dashboardUrl = shop ? `/app/dashboard?shop=${encodeURIComponent(shop)}` : '/app/dashboard'

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
        <span className="text-xl font-semibold tracking-tight text-black">TRYON</span>
        <Link
          href="/"
          className="px-4 py-2 bg-black text-white text-sm font-medium rounded-md hover:opacity-90 transition-opacity"
        >
          Sign In
        </Link>
      </header>

      {/* Main */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-12">
        <h1 className="text-3xl md:text-4xl font-bold text-center mb-2">
          <span className="text-black">Virtual Try-On</span>{' '}
          <span className="text-gray-500">For Everyone</span>
        </h1>
        <p className="text-center text-gray-600 max-w-lg mb-10">
          Shoppers get a perfect fit. Brands reduce returns. One platform, powered by your 3D avatar.
        </p>

        {/* Onboarding options — only hide shopper when in Shopify app */}
        <div className="flex flex-col sm:flex-row gap-4 w-full max-w-2xl justify-center">
          {!isShopifyApp && (
            <Link
              href="/"
              className="flex flex-col items-center justify-center rounded-2xl border-2 border-black bg-black text-white px-8 py-6 hover:opacity-95 transition-opacity min-h-[120px]"
            >
              <span className="text-lg font-semibold">Create Your Fit Passport</span>
              <span className="text-sm text-white/80 mt-1">I&apos;m a shopper</span>
            </Link>
          )}
          <Link
            href={dashboardUrl}
            className="flex flex-col items-center justify-center rounded-2xl border-2 border-gray-900 bg-white text-black px-8 py-6 hover:bg-gray-50 transition-colors min-h-[120px]"
          >
            <span className="text-lg font-semibold">Launch Your Brand</span>
            <span className="text-sm text-gray-600 mt-1">I&apos;m a brand</span>
          </Link>
        </div>

        {/* Feature cards — same structure as main site, icons not emojis */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-14 w-full max-w-3xl">
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-5 text-center">
            <Camera className="w-8 h-8 mx-auto mb-3 text-gray-800" strokeWidth={1.5} />
            <h3 className="font-semibold text-black mb-1">Upload Once</h3>
            <p className="text-sm text-gray-600">
              Take one photo, get your personalized 3D avatar with accurate body measurements.
            </p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-5 text-center">
            <Globe className="w-8 h-8 mx-auto mb-3 text-gray-800" strokeWidth={1.5} />
            <h3 className="font-semibold text-black mb-1">Try On Anywhere</h3>
            <p className="text-sm text-gray-600">
              Works on any brand&apos;s website. One avatar, endless possibilities.
            </p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-5 text-center">
            <CheckCircle className="w-8 h-8 mx-auto mb-3 text-gray-800" strokeWidth={1.5} />
            <h3 className="font-semibold text-black mb-1">Reduce Returns</h3>
            <p className="text-sm text-gray-600">
              Brands see up to 40% fewer returns with accurate size recommendations.
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}
