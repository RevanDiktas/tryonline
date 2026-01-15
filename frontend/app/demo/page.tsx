'use client';

import { useState } from 'react';

export default function DemoPage() {
  const [showWidget, setShowWidget] = useState(false);
  const [currentSize, setCurrentSize] = useState('m');

  // Demo/mock data - no auth required
  const mockUser = {
    name: 'Demo User',
    email: 'demo@tryon.app',
  };

  const mockPassport = {
    height: 175,
    measurements: {
      chest: 98,
      waist: 78,
      hips: 92,
    },
  };

  const fitData: Record<string, string> = {
    xs: 'TOO TIGHT in the chest and shoulders. Size up for a comfortable fit.',
    s: 'SLIGHTLY FITTED, may feel snug around the chest. Good for a slim fit.',
    m: 'FITS VERY WELL, not too tight, not too baggy. RECOMMENDED FIT',
    l: 'RELAXED FIT with extra room in the body. Good for a loose fit.',
    xl: 'OVERSIZED FIT, very roomy throughout. Ideal for an oversized look.',
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Simulated PDP */}
      <div className="flex min-h-screen">
        {/* Product Image */}
        <div className="flex-1 bg-gradient-to-br from-gray-100 via-gray-200 to-gray-300 flex items-center justify-center">
          <span className="text-[200px] drop-shadow-2xl">👕</span>
        </div>

        {/* Product Info */}
        <div className="w-[400px] p-10 flex flex-col justify-center bg-white">
          <p className="text-xs tracking-widest text-gray-500 mb-2">NUDE PROJECT</p>
          <h1 className="text-2xl font-medium mb-4">NPC Oversized T-Shirt</h1>
          <p className="text-lg mb-6">€49.00</p>
          
          <button
            onClick={() => setShowWidget(true)}
            className="w-full py-4 bg-black text-white font-medium tracking-wide hover:bg-gray-800 transition mb-4"
          >
            TRY ON
          </button>

          <button className="w-full py-4 border border-black text-black font-medium tracking-wide hover:bg-gray-50 transition">
            ADD TO CART
          </button>

          {/* Demo indicator */}
          <div className="mt-8 p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
              <div>
                <p className="text-sm font-medium text-gray-900">Demo Mode</p>
                <p className="text-xs text-gray-500">Using sample Fit Passport data</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* TryOn Widget Modal */}
      {showWidget && (
        <div 
          className="fixed inset-0 bg-black/25 z-50 flex items-center justify-center"
          onClick={(e) => e.target === e.currentTarget && setShowWidget(false)}
        >
          <div className="relative w-[800px] max-w-[92vw]">
            {/* Close button */}
            <button
              onClick={() => setShowWidget(false)}
              className="absolute -top-12 right-0 w-10 h-10 bg-white rounded-full flex items-center justify-center shadow-lg hover:scale-110 transition"
            >
              ✕
            </button>

            {/* Glassmorphism popup */}
            <div className="bg-white/20 backdrop-blur-xl border border-white/40 rounded-3xl shadow-2xl overflow-hidden" style={{ backdropFilter: 'blur(40px) saturate(180%)' }}>
              {/* Header */}
              <div className="flex justify-between items-center px-6 py-4 border-b border-white/30 bg-white/30">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img 
                  src="/tryon-logo.jpg" 
                  alt="TRYON" 
                  className="h-6 w-auto"
                />
                <span className="text-sm font-medium text-gray-700">{mockUser.name.toUpperCase()}</span>
              </div>

              {/* Content */}
              <div className="flex min-h-[540px]">
                {/* Avatar Viewer */}
                <div className="flex-1 relative border-r border-white/20 bg-white/10">
                  <iframe 
                    src={`/embed-viewer.html#${currentSize}`}
                    className="w-full h-full border-0 bg-transparent"
                    style={{ minHeight: '540px' }}
                  />
                  <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-xs text-gray-500 bg-white/70 px-3 py-1.5 rounded-full backdrop-blur-sm">
                    Drag to rotate • Scroll to zoom • Right-drag to move
                  </div>
                </div>

                {/* Info Panel */}
                <div className="w-[230px] p-6 bg-white/40 flex flex-col">
                  {/* Measurements from Fit Passport */}
                  <div className="flex-1 space-y-5">
                    <div>
                      <p className="text-[10px] font-semibold tracking-widest text-gray-400">HEIGHT</p>
                      <p className="text-xl font-semibold text-gray-900">{mockPassport.height}CM</p>
                    </div>
                    <div>
                      <p className="text-[10px] font-semibold tracking-widest text-gray-400">CHEST</p>
                      <p className="text-xl font-semibold text-gray-900">{mockPassport.measurements.chest}CM</p>
                    </div>
                    <div>
                      <p className="text-[10px] font-semibold tracking-widest text-gray-400">HIPS</p>
                      <p className="text-xl font-semibold text-gray-900">{mockPassport.measurements.hips}CM</p>
                    </div>
                    <div>
                      <p className="text-[10px] font-semibold tracking-widest text-gray-400">WAIST</p>
                      <p className="text-xl font-semibold text-gray-900">{mockPassport.measurements.waist}CM</p>
                    </div>
                  </div>

                  {/* Size Selector */}
                  <div className="flex gap-2 mb-5">
                    {['xs', 's', 'm', 'l', 'xl'].map((size) => (
                      <button
                        key={size}
                        onClick={() => setCurrentSize(size)}
                        className={`w-[42px] h-[42px] rounded-lg border font-semibold text-xs transition ${
                          currentSize === size
                            ? 'bg-black text-white border-black'
                            : 'bg-white/50 text-gray-900 border-gray-200 hover:bg-white/80'
                        }`}
                      >
                        {size.toUpperCase()}
                      </button>
                    ))}
                  </div>

                  {/* Fit Description */}
                  <div className="border-t border-white/30 pt-4">
                    <p className="text-[10px] font-semibold tracking-widest text-gray-400 mb-2">FIT</p>
                    <p className="text-xs leading-relaxed text-gray-700">
                      {fitData[currentSize]}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
