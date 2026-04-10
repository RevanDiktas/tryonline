'use client'

import { Suspense, useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import dynamic from 'next/dynamic'
import { useTheme } from '@/contexts/ThemeContext'
import { api, isBackendAvailable } from '@/lib/api'

const TryOnViewer = dynamic(() => import('@/components/TryOnViewer'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center">
      <div className="glass-panel px-6 py-4 flex items-center gap-3">
        <div className="w-5 h-5 border-2 border-[#1d1d1f] border-t-transparent rounded-full animate-spin" />
        <span className="text-sm font-medium text-[#1d1d1f]">Loading TryOn...</span>
      </div>
    </div>
  ),
})

const DEFAULT_MEASUREMENTS = { chest: 98, waist: 82, hips: 96, height: 178 }

function EmbedContent() {
  const searchParams = useSearchParams()
  const { theme } = useTheme()
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [userMeasurements, setUserMeasurements] = useState(DEFAULT_MEASUREMENTS)
  const [avatarUrl, setAvatarUrl] = useState<string | undefined>(undefined)
  const [garmentUrls, setGarmentUrls] = useState<Record<string, string> | undefined>(undefined)
  const [sizeChart, setSizeChart] = useState<Record<string, { chest: number; waist: number; hips: number }> | undefined>(undefined)
  const [combinedModels, setCombinedModels] = useState(true)

  const productId = searchParams.get('product_id') || 'demo-npc-tshirt'
  const variantId = searchParams.get('variant_id')
  const shop = searchParams.get('shop')
  const userId = searchParams.get('user_id')
  const preferredFit = searchParams.get('preferred_fit')
  const country = searchParams.get('country')  // ISO 3166-1 alpha-2, e.g. NL, US

  const track = useCallback(
    async (eventType: string, metadata?: Record<string, unknown>) => {
      if (!(await isBackendAvailable())) return
      try {
        await api.trackEvent({
          event_type: eventType,
          user_id: userId || undefined,
          session_id: sessionId || undefined,
          shop_domain: shop || undefined,
          product_id: productId || undefined,
          variant_id: variantId || undefined,
          preferred_fit: preferredFit || undefined,
          country: country || undefined,
          metadata,
        })
      } catch (e) {
        console.warn('[Analytics] track failed:', e)
      }
    },
    [sessionId, userId, shop, productId, variantId, preferredFit]
  )

  useEffect(() => {
    let mounted = true
    ;(async () => {
      const available = await isBackendAvailable()
      if (!available) return
      try {
        const [avatarRes, productRes] = await Promise.all([
          userId ? api.getAvatar(userId).catch(() => null) : null,
          api.getProductTryonConfig(productId, shop ? { shop } : undefined).catch(() => null),
        ])
        if (mounted && avatarRes?.measurements) {
          const m = avatarRes.measurements
          setUserMeasurements({
            chest: m.chest ?? DEFAULT_MEASUREMENTS.chest,
            waist: m.waist ?? DEFAULT_MEASUREMENTS.waist,
            hips: m.hips ?? DEFAULT_MEASUREMENTS.hips,
            height: m.height ?? DEFAULT_MEASUREMENTS.height,
          })
          if (avatarRes.avatar_url) setAvatarUrl(avatarRes.avatar_url)
        }
        if (mounted && productRes) {
          setCombinedModels(productRes.model_type !== 'garment_only')
          const base = typeof window !== 'undefined' ? window.location.origin : ''
          const urls: Record<string, string> = {}
          for (const [k, v] of Object.entries(productRes.model_urls || {})) {
            urls[k] = (v && (v as string).startsWith('http')) ? v as string : base + ((v as string).startsWith('/') ? v : '/' + v)
          }
          setGarmentUrls(urls)
          if (productRes.size_chart && Object.keys(productRes.size_chart).length) {
            const chart: Record<string, { chest: number; waist: number; hips: number }> = {}
            for (const [k, v] of Object.entries(productRes.size_chart)) {
              const o = v as Record<string, number>
              chart[k] = { chest: o.chest ?? 100, waist: o.waist ?? 84, hips: o.hips ?? 98 }
            }
            setSizeChart(chart)
          }
        }
      } catch (e) {
        console.warn('[Embed] Fetch config failed:', e)
      }
    })()
    return () => { mounted = false }
  }, [userId, productId, shop])

  useEffect(() => {
    let mounted = true
    ;(async () => {
      if (!(await isBackendAvailable())) return
      try {
        const res = await api.createTryonSession({
          user_id: userId || undefined,
          shop_domain: shop || undefined,
          product_id: productId || undefined,
          variant_id: variantId || undefined,
        })
        if (mounted && res.session_id) {
          setSessionId(res.session_id)
          await api.trackEvent({
            event_type: 'widget_opened',
            user_id: userId || undefined,
            session_id: res.session_id,
            shop_domain: shop || undefined,
            product_id: productId || undefined,
            variant_id: variantId || undefined,
            country: country || undefined,
          })
        }
      } catch (e) {
        console.warn('[Analytics] create session failed:', e)
      }
    })()
    return () => {
      mounted = false
    }
  }, [userId, shop, productId, variantId])

  const handleAddToCart = useCallback(
    (size: string) => {
      track('add_to_cart', { size })
      window.parent.postMessage(
        {
          type: 'TRYON_ADD_TO_CART',
          payload: {
            productId,
            variantId,
            size,
            shop,
            session_id: sessionId,
          },
        },
        '*'
      )
    },
    [sessionId, track]
  )

  return (
    <div className={`w-full h-screen ${theme === 'dark' ? 'bg-black' : 'bg-[#f9fafb]'}`}>
      <TryOnViewer
        theme={theme}
        brandName="Saint Blanc"
        productName="Essential Cotton Tee"
        avatarUrl={combinedModels ? undefined : avatarUrl}
        garmentUrls={garmentUrls}
        userMeasurements={userMeasurements}
        sizeChart={sizeChart}
        preferredFit={preferredFit === 'slim' || preferredFit === 'loose' ? preferredFit : 'regular'}
        onSizeSelect={(size) => {
          track('size_selected', { size })
          window.parent.postMessage(
            { type: 'TRYON_SIZE_SELECTED', payload: { size, productId } },
            '*'
          )
        }}
        onAddToCart={handleAddToCart}
        onTryonReady={() => track('tryon_started')}
        onSizeRecommended={(size) => track('size_recommended', { size })}
      />
    </div>
  )
}

export default function EmbedPage() {
  return (
    <Suspense fallback={
      <div className="w-full h-screen flex items-center justify-center">
        <div className="glass-panel px-6 py-4">
          <span className="text-sm font-medium text-[#1d1d1f]">Loading...</span>
        </div>
      </div>
    }>
      <EmbedContent />
    </Suspense>
  )
}
