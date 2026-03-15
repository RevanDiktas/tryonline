import type { Metadata } from 'next'
import { Suspense } from 'react'
import './globals.css'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { ShopifyAppBridge } from '@/components/ShopifyAppBridge'

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
