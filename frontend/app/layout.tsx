import type { Metadata } from 'next'
import Script from 'next/script'
import { Suspense } from 'react'
import './globals.css'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { ShopifyAppBridge } from '@/components/ShopifyAppBridge'

// Must match Dev Dashboard → Tryon → Settings → Client ID. Set NEXT_PUBLIC_SHOPIFY_CLIENT_ID in Vercel.
const SHOPIFY_CLIENT_ID = process.env.NEXT_PUBLIC_SHOPIFY_CLIENT_ID || 'ec47b40d60204a8d7cf80aa50e313d19'

export const metadata: Metadata = {
  title: 'TryOn - Virtual Fitting Room',
  description: 'See how clothes fit on your body before you buy',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta name="shopify-api-key" content={SHOPIFY_CLIENT_ID} />
        {/* App Bridge from Shopify CDN — beforeInteractive so it's in initial HTML for embedded check */}
        <Script
          src="https://cdn.shopify.com/shopifycloud/app-bridge.js"
          strategy="beforeInteractive"
        />
      </head>
      <body className="antialiased">
        <ThemeProvider>
          <Suspense fallback={null}>
            <ShopifyAppBridge />
          </Suspense>
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
