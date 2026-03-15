'use client'

import { useSearchParams, useRouter } from 'next/navigation'
import { useEffect } from 'react'

/**
 * Launch Your Brand destination. Redirects to /brand with shop param so the
 * brand dashboard (ROI, Garments, etc.) loads. Avoids 404 when clicking from /app.
 */
export default function AppDashboardPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const shop = searchParams.get('shop')

  useEffect(() => {
    if (shop) {
      router.replace(`/brand?shop=${encodeURIComponent(shop)}`)
    } else {
      router.replace('/brand')
    }
  }, [shop, router])

  return (
    <div className="min-h-screen flex items-center justify-center bg-white">
      <p className="text-gray-600">Redirecting to your brand dashboard…</p>
    </div>
  )
}
