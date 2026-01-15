'use client'

import { Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import dynamic from 'next/dynamic'

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

function EmbedContent() {
  const searchParams = useSearchParams()
  
  // Get parameters from iframe URL
  const productId = searchParams.get('product_id')
  const variantId = searchParams.get('variant_id')
  const shop = searchParams.get('shop')
  const userId = searchParams.get('user_id')

  // These would be fetched from API based on productId and userId
  const mockUserMeasurements = {
    chest: 98,
    waist: 82,
    hips: 96,
    height: 178,
  }

  const handleAddToCart = (size: string) => {
    // Post message to parent window (Shopify)
    window.parent.postMessage(
      {
        type: 'TRYON_ADD_TO_CART',
        payload: {
          productId,
          variantId,
          size,
          shop,
        },
      },
      '*'
    )
  }

  return (
    <div className="w-full h-screen">
      <TryOnViewer
        brandName="Saint Blanc"
        productName="Essential Cotton Tee"
        userMeasurements={mockUserMeasurements}
        onSizeSelect={(size) => {
          // Track analytics
          window.parent.postMessage(
            { type: 'TRYON_SIZE_SELECTED', payload: { size, productId } },
            '*'
          )
        }}
        onAddToCart={handleAddToCart}
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
