'use client'

import { Suspense, useRef, useEffect, useState, useCallback } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, useGLTF, Environment } from '@react-three/drei'
import * as THREE from 'three'
import { api } from '@/lib/api'

function computeBindHeight(root: THREE.Object3D): number {
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
  if (box.isEmpty()) return 0
  const size = new THREE.Vector3()
  box.getSize(size)
  return size.y
}

function GarmentModel({ url }: { url: string }) {
  const { scene } = useGLTF(url)
  const groupRef = useRef<THREE.Group>(null)

  useEffect(() => {
    scene.scale.setScalar(1)
    scene.position.set(0, 0, 0)

    scene.traverse((child) => {
      if (child instanceof THREE.Mesh && child.material) {
        const mat = (child.material as THREE.MeshStandardMaterial).clone()
        mat.side = THREE.DoubleSide
        child.material = mat
      }
    })

    const rawH = computeBindHeight(scene)
    if (rawH > 1e-9) {
      scene.scale.setScalar(1.8 / rawH)
    }

    scene.updateMatrixWorld(true)
    const box = new THREE.Box3()
    scene.traverse((c) => {
      if (!(c instanceof THREE.Mesh) || !c.geometry) return
      const g = c.geometry as THREE.BufferGeometry
      if (!g.boundingBox) g.computeBoundingBox()
      if (!g.boundingBox || g.boundingBox.isEmpty()) return
      const b = g.boundingBox.clone()
      b.applyMatrix4(c.matrixWorld)
      box.union(b)
    })
    if (!box.isEmpty()) {
      const center = new THREE.Vector3()
      box.getCenter(center)
      scene.position.set(-center.x, -center.y, -center.z)
    }
  }, [scene])

  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = state.clock.elapsedTime * 0.3
    }
  })

  return (
    <group ref={groupRef}>
      <primitive object={scene} />
    </group>
  )
}

interface GarmentPreview3DProps {
  productId: string
  shopDomain: string
  dark?: boolean
  fallbackImageUrl?: string | null
}

export default function GarmentPreview3D({
  productId,
  shopDomain,
  dark = false,
  fallbackImageUrl,
}: GarmentPreview3DProps) {
  const [glbUrl, setGlbUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  const loadGlb = useCallback(async () => {
    try {
      const config = await api.getProductTryonConfig(productId, { shop: shopDomain })
      const urls = config.model_urls || {}
      const url = urls['m'] || urls['M'] || urls['s'] || urls['S'] || Object.values(urls)[0]
      if (url) {
        setGlbUrl(url)
      } else {
        setFailed(true)
      }
    } catch {
      setFailed(true)
    }
  }, [productId, shopDomain])

  useEffect(() => {
    loadGlb()
  }, [loadGlb])

  if (failed || !glbUrl) {
    if (fallbackImageUrl) {
      return (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={fallbackImageUrl}
          alt="Product"
          className="w-full h-full object-cover"
        />
      )
    }
    return (
      <div className={`w-full h-full flex items-center justify-center ${dark ? 'bg-white/5' : 'bg-slate-100'}`}>
        <svg className={`w-10 h-10 ${dark ? 'text-white/20' : 'text-slate-300'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      </div>
    )
  }

  return (
    <Canvas
      gl={{ alpha: true, antialias: true, powerPreference: 'default' }}
      camera={{ position: [0, 0, 2.2], fov: 40 }}
      style={{ background: dark ? '#111' : '#f4f4f5' }}
    >
      <ambientLight intensity={0.8} />
      <directionalLight position={[3, 4, 5]} intensity={0.8} />
      <directionalLight position={[-2, 2, -3]} intensity={0.3} />
      <Environment preset="city" />
      <Suspense fallback={null}>
        <GarmentModel url={glbUrl} />
      </Suspense>
      <OrbitControls
        enablePan={false}
        enableZoom={false}
        autoRotate={false}
        enableRotate={false}
      />
    </Canvas>
  )
}
