import type { Metadata } from 'next'
import { Suspense } from 'react'
import './globals.css'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { ShopifyAppBridge } from '@/components/ShopifyAppBridge'
import { SHOPIFY_EMBEDDED_CLIENT_ID } from '@/lib/shopify-embedded-client-id'

export const metadata: Metadata = {
  title: 'Tryon - Virtual Fitting Room',
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
        <meta name="shopify-api-key" content={SHOPIFY_EMBEDDED_CLIENT_ID} />
        {/* App Bridge is loaded only in the /app embed shell (first script there). This doc is either the iframe (token via postMessage) or non-embed. */}
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
