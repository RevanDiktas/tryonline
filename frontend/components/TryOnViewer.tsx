'use client'

import { Suspense, useRef, useState, useEffect, useMemo, useCallback } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, useGLTF, Environment } from '@react-three/drei'
import { motion, AnimatePresence } from 'framer-motion'
import * as THREE from 'three'
import { Check, Ruler, RotateCcw, ExternalLink } from 'lucide-react'
import { recommendSize, type PreferredFit, type GarmentCategory, type GarmentFitType, type SizeRecommendation } from '@/lib/sizeRecommendation'

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
  garmentUrls?: Record<string, string>
  userMeasurements?: {
    chest: number
    waist: number
    hips: number
    height: number
    inseam?: number
    shoulder_width?: number
    arm_length?: number
    thigh?: number
    neck?: number
  }
  sizeChart?: Record<string, Record<string, number>>
  brandName?: string
  productName?: string
  onSizeSelect?: (size: string) => void
  onAddToCart?: (size: string) => void
  onTryonReady?: () => void
  onSizeRecommended?: (size: string) => void
  preferredFit?: PreferredFit
  theme?: 'light' | 'dark'
  productUrl?: string
  garmentCategory?: GarmentCategory
  garmentFitType?: GarmentFitType
}

// ---------------------------------------------------------------------------
// Geometry-based bounding box (works for SkinnedMesh bind pose)
// Ported from test-viewer.html - the PDP widget uses this to get accurate
// heights even when Object3D world AABB from three.js is ~0 for skinned meshes.
// ---------------------------------------------------------------------------
function geometryWorldBounds(root: THREE.Object3D): THREE.Box3 {
  const box = new THREE.Box3()
  root.updateMatrixWorld(true)
  root.traverse((c) => {
    if (!(c instanceof THREE.Mesh) || !c.geometry) return
    const g = c.geometry as THREE.BufferGeometry
    if (!g.boundingBox) g.computeBoundingBox()
    if (!g.boundingBox || g.boundingBox.isEmpty()) return
    const b = g.boundingBox.clone()
    b.applyMatrix4(c.matrixWorld)
    box.union(b)
  })
  return box
}

function computeBindHeight(root: THREE.Object3D): number {
  const box = geometryWorldBounds(root)
  if (box.isEmpty()) return 0
  const size = new THREE.Vector3()
  box.getSize(size)
  return size.y
}

const TARGET_HEIGHT = 1.8
const GARMENT_CLEARANCE = 1.038
const GARMENT_Z_PUSHBACK = -0.010
const AVATAR_Z_OFFSET = -0.010

// ---------------------------------------------------------------------------
// Aligned scene: loads avatar + garment, normalizes both to TARGET_HEIGHT,
// aligns garment feet to avatar feet - identical to the PDP widget.
// ---------------------------------------------------------------------------
function AlignedScene({ avatarUrl, garmentUrl }: { avatarUrl: string; garmentUrl: string }) {
  const avatarGltf = useGLTF(avatarUrl)
  const garmentGltf = useGLTF(garmentUrl)
  const groupRef = useRef<THREE.Group>(null)

  useEffect(() => {
    const avatar = avatarGltf.scene
    const garment = garmentGltf.scene

    avatar.scale.setScalar(1)
    avatar.position.set(0, 0, AVATAR_Z_OFFSET)
    garment.scale.setScalar(1)
    garment.position.set(0, 0, 0)

    avatar.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        child.castShadow = true
        child.receiveShadow = true
      }
    })
    garment.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        child.castShadow = true
        if (child.material) {
          const mat = (child.material as THREE.MeshStandardMaterial).clone()
          mat.side = THREE.DoubleSide
          child.material = mat
        }
      }
    })

    const rawA = computeBindHeight(avatar)
    const rawG = computeBindHeight(garment)

    const sA = rawA > 1e-9 ? TARGET_HEIGHT / rawA : 1
    const sG = rawG > 1e-9 ? (TARGET_HEIGHT / rawG) * GARMENT_CLEARANCE : GARMENT_CLEARANCE

    avatar.scale.setScalar(sA)
    garment.scale.setScalar(sG)

    if (groupRef.current) {
      groupRef.current.updateMatrixWorld(true)
    }

    const boxA = geometryWorldBounds(avatar)
    const boxG = geometryWorldBounds(garment)
    if (!boxA.isEmpty() && !boxG.isEmpty()) {
      garment.position.set(0, boxA.min.y - boxG.min.y, GARMENT_Z_PUSHBACK)
    }

    if (groupRef.current) {
      groupRef.current.updateMatrixWorld(true)
    }
  }, [avatarGltf, garmentGltf, avatarUrl, garmentUrl])

  return (
    <group ref={groupRef} position={[0, -0.9, 0]}>
      <primitive object={avatarGltf.scene} />
      <primitive object={garmentGltf.scene} />
    </group>
  )
}

function PlaceholderAvatar() {
  const meshRef = useRef<THREE.Mesh>(null)

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.5) * 0.02 - 0.2
    }
  })

  return (
    <group>
      <mesh ref={meshRef} position={[0, -0.2, 0]}>
        <capsuleGeometry args={[0.25, 0.6, 16, 32]} />
        <meshStandardMaterial color="#e8beac" roughness={0.7} />
      </mesh>
      <mesh position={[0, 0.65, 0]}>
        <sphereGeometry args={[0.15, 32, 32]} />
        <meshStandardMaterial color="#e8beac" roughness={0.7} />
      </mesh>
      <mesh position={[-0.35, 0, 0]} rotation={[0, 0, 0.3]}>
        <capsuleGeometry args={[0.06, 0.4, 8, 16]} />
        <meshStandardMaterial color="#e8beac" roughness={0.7} />
      </mesh>
      <mesh position={[0.35, 0, 0]} rotation={[0, 0, -0.3]}>
        <capsuleGeometry args={[0.06, 0.4, 8, 16]} />
        <meshStandardMaterial color="#e8beac" roughness={0.7} />
      </mesh>
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

function PlaceholderGarment({ color = '#1d1d1f' }: { color?: string }) {
  return (
    <group position={[0, 0.05, 0.01]}>
      <mesh>
        <boxGeometry args={[0.52, 0.55, 0.2]} />
        <meshStandardMaterial color={color} roughness={0.8} side={THREE.DoubleSide} />
      </mesh>
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
      enablePan={true}
      enableZoom={true}
      minDistance={1}
      maxDistance={5}
      minPolarAngle={0}
      maxPolarAngle={Math.PI}
      target={[0, 0, 0]}
      dampingFactor={0.05}
      rotateSpeed={0.5}
      panSpeed={0.8}
      touches={{ ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN }}
    />
  )
}

function SizeButton({
  size,
  isActive,
  isRecommended,
  onClick,
}: {
  size: string
  isActive: boolean
  isRecommended: boolean
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

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
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
  onTryonReady,
  onSizeRecommended,
  preferredFit = 'regular',
  theme: themeProp,
  productUrl,
  garmentCategory = 'tops',
  garmentFitType = 'regular',
}: TryOnViewerProps) {
  const [selectedSize, setSelectedSize] = useState<string>('M')
  const hasSetInitialSize = useRef(false)
  const [resetCamera, setResetCamera] = useState(0)
  const [showMeasurements, setShowMeasurements] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const urls: string[] = []
    if (avatarUrl) urls.push(avatarUrl)
    if (garmentUrls) urls.push(...Object.values(garmentUrls).filter(Boolean))
    urls.forEach((url) => useGLTF.preload(url))
  }, [avatarUrl, garmentUrls])

  const getChart = (size: string) =>
    sizeChart[size] ?? sizeChart[size.toLowerCase()] ?? sizeChart[size.toUpperCase()]

  const sizeRec: SizeRecommendation = useMemo(() => recommendSize(
    userMeasurements,
    sizeChart,
    preferredFit,
    garmentCategory,
    garmentFitType,
  ), [userMeasurements, sizeChart, preferredFit, garmentCategory, garmentFitType])

  const recommendedSize = sizeRec.recommendedSize

  const calculateFit = useCallback((size: string): FitResult => {
    const sizeData = sizeRec.allSizes.find(
      (s) => s.size.toLowerCase() === size.toLowerCase()
    )
    if (sizeData) {
      const chart = getChart(size) ?? {}
      return {
        size,
        fit: sizeData.fit,
        measurements: {
          chest: { user: userMeasurements.chest, garment: chart.chest ?? 0, diff: (chart.chest ?? 0) - userMeasurements.chest },
          waist: { user: userMeasurements.waist, garment: chart.waist ?? 0, diff: (chart.waist ?? 0) - userMeasurements.waist },
          hips: { user: userMeasurements.hips, garment: chart.hips ?? 0, diff: (chart.hips ?? 0) - userMeasurements.hips },
        },
      }
    }
    const chart = getChart(size)
    if (!chart) return { size, fit: 'recommended', measurements: { chest: { user: 0, garment: 0, diff: 0 }, waist: { user: 0, garment: 0, diff: 0 }, hips: { user: 0, garment: 0, diff: 0 } } }
    return {
      size,
      fit: 'recommended',
      measurements: {
        chest: { user: userMeasurements.chest, garment: chart.chest ?? 0, diff: (chart.chest ?? 0) - userMeasurements.chest },
        waist: { user: userMeasurements.waist, garment: chart.waist ?? 0, diff: (chart.waist ?? 0) - userMeasurements.waist },
        hips: { user: userMeasurements.hips, garment: chart.hips ?? 0, diff: (chart.hips ?? 0) - userMeasurements.hips },
      },
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sizeRec, sizeChart, userMeasurements])

  const handleSizeSelect = (size: string) => {
    setSelectedSize(size)
    onSizeSelect?.(size)
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false)
      onTryonReady?.()
    }, 1500)
    return () => clearTimeout(timer)
  }, [onTryonReady])

  useEffect(() => {
    if (!isLoading && recommendedSize && !hasSetInitialSize.current) {
      hasSetInitialSize.current = true
      setSelectedSize(recommendedSize)
    }
  }, [isLoading, recommendedSize])

  const hasFiredRecommended = useRef(false)
  useEffect(() => {
    if (!isLoading && recommendedSize && !hasFiredRecommended.current) {
      hasFiredRecommended.current = true
      onSizeRecommended?.(recommendedSize)
    }
  }, [isLoading, recommendedSize, onSizeRecommended])

  const activeGarmentUrl = garmentUrls
    ? (garmentUrls[selectedSize] ?? garmentUrls[selectedSize.toLowerCase()] ?? garmentUrls[selectedSize.toUpperCase()])
    : undefined

  return (
    <div className="relative w-full h-full min-h-[600px] flex flex-col lg:flex-row">
      <div
        className="flex-1 relative"
        style={{ background: '#ffffff' }}
      >
        <Canvas
          className="viewer-canvas"
          gl={{
            alpha: false,
            antialias: true,
            powerPreference: 'high-performance',
          }}
          camera={{ position: [0, 0, 2.5], fov: 45 }}
          style={{ background: '#ffffff' }}
        >
          <color attach="background" args={['#ffffff']} />
          <ambientLight intensity={0.6} />
          <directionalLight
            position={[5, 5, 5]}
            intensity={1}
            castShadow
            shadow-mapSize={[2048, 2048]}
          />
          <directionalLight position={[-3, 3, -3]} intensity={0.4} />

          <Environment preset="city" />

          {/* Clean white - no floor shadow */}

          <Suspense fallback={null}>
            {avatarUrl && activeGarmentUrl ? (
              <AlignedScene avatarUrl={avatarUrl} garmentUrl={activeGarmentUrl} />
            ) : (
              <>
                <PlaceholderAvatar />
                <PlaceholderGarment />
              </>
            )}
          </Suspense>

          <CameraController resetTrigger={resetCamera} />
        </Canvas>

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

        <div className="absolute top-4 left-4">
          <div className="glass-panel px-4 py-2 flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-[#1d1d1f] flex items-center justify-center">
              <span className="text-white text-xs font-bold">
                {(brandName || 'SB').substring(0, 2).toUpperCase()}
              </span>
            </div>
            <span className="text-xs font-medium text-[#1d1d1f]">{brandName}</span>
          </div>
        </div>
      </div>

      {/* Control Panel */}
      <div className="w-full lg:w-80 p-4 lg:p-6 space-y-4 overflow-y-auto">
        <div className="glass-panel p-5">
          <h2 className="text-lg font-semibold text-[#1d1d1f] mb-1">{productName}</h2>
          <p className="text-sm text-[#86868b]">See how it fits on your body</p>
        </div>

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
                onClick={() => handleSizeSelect(size)}
              />
            ))}
          </div>

          <motion.div
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 flex items-center gap-2 text-xs text-[#34C759]"
          >
            <Check className="w-3.5 h-3.5" />
            <span className="font-medium">
              Size {recommendedSize} is your best match
              {sizeRec.confidence > 0 && (
                <span className="ml-1 text-[#86868b] font-normal">({sizeRec.confidence}% confident)</span>
              )}
            </span>
          </motion.div>
        </div>

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

        {/* View on Store / redirect to PDP */}
        {productUrl ? (
          <motion.a
            href={productUrl}
            target="_blank"
            rel="noopener noreferrer"
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            className="w-full py-4 bg-[#1d1d1f] text-white rounded-2xl font-semibold
                       shadow-lg shadow-black/20 hover:bg-[#2d2d2f] transition-colors
                       flex items-center justify-center gap-2"
          >
            View on Store
            <ExternalLink className="w-4 h-4" />
          </motion.a>
        ) : onAddToCart ? (
          <motion.button
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            onClick={() => onAddToCart?.(selectedSize)}
            className="w-full py-4 bg-[#1d1d1f] text-white rounded-2xl font-semibold
                       shadow-lg shadow-black/20 hover:bg-[#2d2d2f] transition-colors"
          >
            Add Size {selectedSize} to Cart
          </motion.button>
        ) : null}

        <p className="text-[10px] text-center text-[#86868b]">
          Your body data is encrypted and never shared. <a href="#" className="underline">Privacy Policy</a>
        </p>
      </div>
    </div>
  )
}
