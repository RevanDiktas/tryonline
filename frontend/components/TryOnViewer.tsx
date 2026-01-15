'use client'

import { Suspense, useRef, useState, useEffect } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, useGLTF, Environment, ContactShadows } from '@react-three/drei'
import { motion, AnimatePresence } from 'framer-motion'
import * as THREE from 'three'
import { Check, ChevronDown, Ruler, Sparkles, RotateCcw, ZoomIn, ZoomOut } from 'lucide-react'

// Types
interface FitResult {
  size: string
  fit: 'tight' | 'recommended' | 'loose'
  measurements: {
    chest: { user: number; garment: number; diff: number }
    waist: { user: number; garment: number; diff: number }
    hips: { user: number; garment: number; diff: number }
  }
}

interface TryOnViewerProps {
  avatarUrl?: string
  garmentUrls?: Record<string, string> // size -> URL
  userMeasurements?: {
    chest: number
    waist: number
    hips: number
    height: number
  }
  sizeChart?: Record<string, { chest: number; waist: number; hips: number }>
  brandName?: string
  productName?: string
  onSizeSelect?: (size: string) => void
  onAddToCart?: (size: string) => void
}

// Avatar Model Component
function AvatarModel({ url }: { url: string }) {
  const { scene } = useGLTF(url)
  const groupRef = useRef<THREE.Group>(null)

  useEffect(() => {
    // Apply skin material
    scene.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        child.material = new THREE.MeshStandardMaterial({
          color: new THREE.Color('#e8beac'),
          roughness: 0.7,
          metalness: 0.0,
        })
        child.castShadow = true
        child.receiveShadow = true
      }
    })
  }, [scene])

  // Subtle breathing animation
  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.5) * 0.02
    }
  })

  return (
    <group ref={groupRef}>
      <primitive object={scene} scale={1} position={[0, -0.9, 0]} />
    </group>
  )
}

// Garment Model Component with Body Masking
function GarmentModel({ url, bodyMaskEnabled = true }: { url: string; bodyMaskEnabled?: boolean }) {
  const { scene } = useGLTF(url)

  useEffect(() => {
    scene.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        // Enable proper rendering order for transparency
        child.renderOrder = 1
        child.castShadow = true
        
        // Apply garment material
        if (child.material) {
          const mat = child.material as THREE.MeshStandardMaterial
          mat.side = THREE.DoubleSide
        }
      }
    })
  }, [scene])

  return <primitive object={scene} scale={1} position={[0, -0.9, 0]} />
}

// Placeholder Avatar (for demo without actual GLB)
function PlaceholderAvatar() {
  const meshRef = useRef<THREE.Mesh>(null)

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.5) * 0.02 - 0.2
    }
  })

  return (
    <group>
      {/* Body */}
      <mesh ref={meshRef} position={[0, -0.2, 0]}>
        <capsuleGeometry args={[0.25, 0.6, 16, 32]} />
        <meshStandardMaterial color="#e8beac" roughness={0.7} />
      </mesh>
      {/* Head */}
      <mesh position={[0, 0.65, 0]}>
        <sphereGeometry args={[0.15, 32, 32]} />
        <meshStandardMaterial color="#e8beac" roughness={0.7} />
      </mesh>
      {/* Arms */}
      <mesh position={[-0.35, 0, 0]} rotation={[0, 0, 0.3]}>
        <capsuleGeometry args={[0.06, 0.4, 8, 16]} />
        <meshStandardMaterial color="#e8beac" roughness={0.7} />
      </mesh>
      <mesh position={[0.35, 0, 0]} rotation={[0, 0, -0.3]}>
        <capsuleGeometry args={[0.06, 0.4, 8, 16]} />
        <meshStandardMaterial color="#e8beac" roughness={0.7} />
      </mesh>
      {/* Legs */}
      <mesh position={[-0.12, -0.8, 0]}>
        <capsuleGeometry args={[0.08, 0.5, 8, 16]} />
        <meshStandardMaterial color="#e8beac" roughness={0.7} />
      </mesh>
      <mesh position={[0.12, -0.8, 0]}>
        <capsuleGeometry args={[0.08, 0.5, 8, 16]} />
        <meshStandardMaterial color="#e8beac" roughness={0.7} />
      </mesh>
    </group>
  )
}

// Placeholder Garment (T-shirt shape)
function PlaceholderGarment({ color = '#1d1d1f' }: { color?: string }) {
  return (
    <group position={[0, 0.05, 0.01]}>
      {/* Torso */}
      <mesh>
        <boxGeometry args={[0.52, 0.55, 0.2]} />
        <meshStandardMaterial color={color} roughness={0.8} side={THREE.DoubleSide} />
      </mesh>
      {/* Sleeves */}
      <mesh position={[-0.35, 0.15, 0]} rotation={[0, 0, 0.5]}>
        <boxGeometry args={[0.15, 0.25, 0.12]} />
        <meshStandardMaterial color={color} roughness={0.8} />
      </mesh>
      <mesh position={[0.35, 0.15, 0]} rotation={[0, 0, -0.5]}>
        <boxGeometry args={[0.15, 0.25, 0.12]} />
        <meshStandardMaterial color={color} roughness={0.8} />
      </mesh>
    </group>
  )
}

// Camera Controls Component
function CameraController({ resetTrigger }: { resetTrigger: number }) {
  const { camera } = useThree()
  const controlsRef = useRef<any>(null)

  useEffect(() => {
    if (controlsRef.current) {
      controlsRef.current.reset()
      camera.position.set(0, 0, 2.5)
    }
  }, [resetTrigger, camera])

  return (
    <OrbitControls
      ref={controlsRef}
      enablePan={false}
      enableZoom={true}
      minDistance={1.5}
      maxDistance={4}
      minPolarAngle={Math.PI / 4}
      maxPolarAngle={Math.PI / 1.5}
      target={[0, 0, 0]}
      dampingFactor={0.05}
      rotateSpeed={0.5}
    />
  )
}

// Size Button Component
function SizeButton({
  size,
  isActive,
  isRecommended,
  fit,
  onClick,
}: {
  size: string
  isActive: boolean
  isRecommended: boolean
  fit?: 'tight' | 'recommended' | 'loose'
  onClick: () => void
}) {
  return (
    <motion.button
      onClick={onClick}
      className={`
        relative px-5 py-2.5 rounded-2xl text-sm font-semibold
        transition-all duration-300 ease-out
        ${isActive
          ? 'bg-[#1d1d1f] text-white shadow-lg'
          : 'bg-white/60 text-[#1d1d1f] hover:bg-white/80 border border-black/5'
        }
      `}
      whileHover={{ scale: 1.02, y: -1 }}
      whileTap={{ scale: 0.98 }}
    >
      {size}
      {isRecommended && (
        <motion.span
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="absolute -top-1 -right-1 w-4 h-4 bg-[#34C759] rounded-full 
                     flex items-center justify-center shadow-sm"
        >
          <Check className="w-2.5 h-2.5 text-white" strokeWidth={3} />
        </motion.span>
      )}
    </motion.button>
  )
}

// Fit Indicator Component
function FitIndicator({ fit, measurements }: { fit: FitResult['fit']; measurements?: FitResult['measurements'] }) {
  const config = {
    tight: {
      label: 'Too Tight',
      color: 'bg-red-500/10 text-red-600',
      icon: '↓',
      description: 'May feel restrictive',
    },
    recommended: {
      label: 'Perfect Fit',
      color: 'bg-green-500/10 text-green-600',
      icon: '✓',
      description: 'Ideal for your body',
    },
    loose: {
      label: 'Relaxed Fit',
      color: 'bg-orange-500/10 text-orange-600',
      icon: '↑',
      description: 'Extra room throughout',
    },
  }

  const { label, color, description } = config[fit]

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel p-4"
    >
      <div className="flex items-center gap-3 mb-2">
        <span className={`fit-pill ${fit}`}>
          <Sparkles className="w-3 h-3" />
          {label}
        </span>
      </div>
      <p className="text-xs text-[#86868b]">{description}</p>
      
      {measurements && (
        <div className="mt-3 pt-3 border-t border-black/5 space-y-2">
          {Object.entries(measurements).map(([area, data]) => (
            <div key={area} className="flex justify-between text-xs">
              <span className="text-[#86868b] capitalize">{area}</span>
              <span className={`font-medium ${data.diff > 0 ? 'text-green-600' : data.diff < -2 ? 'text-red-600' : 'text-[#1d1d1f]'}`}>
                {data.diff > 0 ? '+' : ''}{data.diff.toFixed(1)} cm
              </span>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  )
}

// Main TryOn Viewer Component
export default function TryOnViewer({
  avatarUrl,
  garmentUrls,
  userMeasurements = { chest: 98, waist: 82, hips: 96, height: 178 },
  sizeChart = {
    XS: { chest: 88, waist: 72, hips: 86 },
    S: { chest: 92, waist: 76, hips: 90 },
    M: { chest: 100, waist: 84, hips: 98 },
    L: { chest: 108, waist: 92, hips: 106 },
    XL: { chest: 116, waist: 100, hips: 114 },
  },
  brandName = 'Saint Blanc',
  productName = 'Essential Cotton Tee',
  onSizeSelect,
  onAddToCart,
}: TryOnViewerProps) {
  const [selectedSize, setSelectedSize] = useState<string>('M')
  const [resetCamera, setResetCamera] = useState(0)
  const [showMeasurements, setShowMeasurements] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  // Calculate fit for each size
  const calculateFit = (size: string): FitResult => {
    const chart = sizeChart[size]
    const chestDiff = chart.chest - userMeasurements.chest
    const waistDiff = chart.waist - userMeasurements.waist
    const hipsDiff = chart.hips - userMeasurements.hips

    // Determine fit based on ease (garment - body)
    const avgEase = (chestDiff + waistDiff + hipsDiff) / 3
    let fit: 'tight' | 'recommended' | 'loose'
    
    if (avgEase < 0) fit = 'tight'
    else if (avgEase > 8) fit = 'loose'
    else fit = 'recommended'

    return {
      size,
      fit,
      measurements: {
        chest: { user: userMeasurements.chest, garment: chart.chest, diff: chestDiff },
        waist: { user: userMeasurements.waist, garment: chart.waist, diff: waistDiff },
        hips: { user: userMeasurements.hips, garment: chart.hips, diff: hipsDiff },
      },
    }
  }

  // Find recommended size
  const allFits = Object.keys(sizeChart).map(calculateFit)
  const recommendedSize = allFits.find((f) => f.fit === 'recommended')?.size || 'M'
  const currentFit = calculateFit(selectedSize)

  const handleSizeSelect = (size: string) => {
    setSelectedSize(size)
    onSizeSelect?.(size)
  }

  // Simulate loading
  useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 1500)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div className="relative w-full h-full min-h-[600px] flex flex-col lg:flex-row">
      {/* 3D Viewer - Transparent Background */}
      <div className="flex-1 relative">
        <Canvas
          className="viewer-canvas"
          gl={{ 
            alpha: true, 
            antialias: true,
            powerPreference: 'high-performance',
          }}
          camera={{ position: [0, 0, 2.5], fov: 45 }}
          style={{ background: 'transparent' }}
        >
          {/* Lighting */}
          <ambientLight intensity={0.6} />
          <directionalLight
            position={[5, 5, 5]}
            intensity={1}
            castShadow
            shadow-mapSize={[2048, 2048]}
          />
          <directionalLight position={[-3, 3, -3]} intensity={0.4} />

          {/* Environment for reflections */}
          <Environment preset="city" />

          {/* Subtle ground shadow */}
          <ContactShadows
            position={[0, -1.1, 0]}
            opacity={0.3}
            scale={3}
            blur={2.5}
            far={1.5}
          />

          <Suspense fallback={null}>
            {/* Avatar */}
            {avatarUrl ? (
              <AvatarModel url={avatarUrl} />
            ) : (
              <PlaceholderAvatar />
            )}

            {/* Garment */}
            {garmentUrls?.[selectedSize] ? (
              <GarmentModel url={garmentUrls[selectedSize]} />
            ) : (
              <PlaceholderGarment />
            )}
          </Suspense>

          <CameraController resetTrigger={resetCamera} />
        </Canvas>

        {/* Loading Overlay */}
        <AnimatePresence>
          {isLoading && (
            <motion.div
              initial={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 flex items-center justify-center"
            >
              <div className="glass-panel px-6 py-4 flex items-center gap-3">
                <div className="w-5 h-5 border-2 border-[#1d1d1f] border-t-transparent rounded-full animate-spin" />
                <span className="text-sm font-medium text-[#1d1d1f]">Loading your fit...</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Camera Controls - Bottom Left */}
        <div className="absolute bottom-4 left-4 flex gap-2">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setResetCamera((r) => r + 1)}
            className="glass-panel w-10 h-10 flex items-center justify-center"
          >
            <RotateCcw className="w-4 h-4 text-[#1d1d1f]" />
          </motion.button>
        </div>

        {/* Brand Badge - Top Left */}
        <div className="absolute top-4 left-4">
          <div className="glass-panel px-4 py-2 flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-[#1d1d1f] flex items-center justify-center">
              <span className="text-white text-xs font-bold">SB</span>
            </div>
            <span className="text-xs font-medium text-[#1d1d1f]">{brandName}</span>
          </div>
        </div>
      </div>

      {/* Control Panel - Right Side */}
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.3 }}
        className="w-full lg:w-80 p-4 lg:p-6 space-y-4"
      >
        {/* Product Info */}
        <div className="glass-panel p-5">
          <h2 className="text-lg font-semibold text-[#1d1d1f] mb-1">{productName}</h2>
          <p className="text-sm text-[#86868b]">See how it fits on your body</p>
        </div>

        {/* Size Selector */}
        <div className="glass-panel p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[#1d1d1f]">Select Size</h3>
            <button
              onClick={() => setShowMeasurements(!showMeasurements)}
              className="text-xs text-[#007AFF] font-medium flex items-center gap-1"
            >
              <Ruler className="w-3 h-3" />
              Size Guide
            </button>
          </div>
          
          <div className="flex flex-wrap gap-2">
            {Object.keys(sizeChart).map((size) => (
              <SizeButton
                key={size}
                size={size}
                isActive={selectedSize === size}
                isRecommended={size === recommendedSize}
                fit={calculateFit(size).fit}
                onClick={() => handleSizeSelect(size)}
              />
            ))}
          </div>

          {/* Recommended Badge */}
          <motion.div
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 flex items-center gap-2 text-xs text-[#34C759]"
          >
            <Check className="w-3.5 h-3.5" />
            <span className="font-medium">Size {recommendedSize} is your best match</span>
          </motion.div>
        </div>

        {/* Fit Indicator */}
        <FitIndicator fit={currentFit.fit} measurements={currentFit.measurements} />

        {/* Measurements Panel */}
        <AnimatePresence>
          {showMeasurements && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="glass-panel p-5 overflow-hidden"
            >
              <h4 className="text-sm font-semibold text-[#1d1d1f] mb-3">Your Measurements</h4>
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-[#86868b]">Chest</span>
                  <span className="font-medium text-[#1d1d1f]">{userMeasurements.chest} cm</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-[#86868b]">Waist</span>
                  <span className="font-medium text-[#1d1d1f]">{userMeasurements.waist} cm</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-[#86868b]">Hips</span>
                  <span className="font-medium text-[#1d1d1f]">{userMeasurements.hips} cm</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-[#86868b]">Height</span>
                  <span className="font-medium text-[#1d1d1f]">{userMeasurements.height} cm</span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Add to Cart Button */}
        <motion.button
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
          onClick={() => onAddToCart?.(selectedSize)}
          className="w-full py-4 bg-[#1d1d1f] text-white rounded-2xl font-semibold
                     shadow-lg shadow-black/20 hover:bg-[#2d2d2f] transition-colors"
        >
          Add Size {selectedSize} to Cart
        </motion.button>

        {/* Privacy Note */}
        <p className="text-[10px] text-center text-[#86868b]">
          Your body data is encrypted and never shared. <a href="#" className="underline">Privacy Policy</a>
        </p>
      </motion.div>
    </div>
  )
}
