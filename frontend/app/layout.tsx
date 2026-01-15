import type { Metadata } from 'next'
import './globals.css'

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
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  )
}
