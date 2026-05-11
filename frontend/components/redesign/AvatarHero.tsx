'use client';

import { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Environment, ContactShadows } from '@react-three/drei';
import { AlignedScene } from '@/components/TryOnViewer';

/**
 * Canonical TryOn avatar + Ramin bow-sweats M garment GLBs, served from
 * frontend/public/redesign. These are the cleaner v45.12.1 drape outputs.
 */
const AVATAR_URL = '/redesign/avatar_textured.glb';
const GARMENT_URL = '/redesign/bow-sweats_m.glb';

interface AvatarHeroProps {
  /** CSS height for the canvas container. Default 70vh. */
  height?: string;
  className?: string;
  /** Allow user to drag-rotate the avatar. Default false (auto-rotate only). */
  interactive?: boolean;
  /** Auto-rotate speed (drei units, ~0.6 to 1.2 reads as slow). Default 0.8. */
  rotateSpeed?: number;
}

/**
 * Full-bleed 3D scene of the canonical TryOn avatar wearing the Ramin bow-sweats
 * M garment. Slow auto-rotate only. Drag, pan, and zoom are disabled so the
 * hero reads as a moving brand visual, not an interactive widget.
 *
 * Reuses AlignedScene from TryOnViewer so the hero scene matches what shoppers
 * see during a real try-on (same scaling, same alignment, same cache).
 */
export function AvatarHero({
  height = '70vh',
  className = '',
  interactive = false,
  rotateSpeed = 0.8,
}: AvatarHeroProps) {
  return (
    <div
      className={className}
      style={{ width: '100%', height, position: 'relative' }}
      aria-label="3D avatar wearing Ramin Studios garment, size M"
    >
      <Canvas
        camera={{ position: [0, 0.05, 3.6], fov: 30 }}
        shadows
        gl={{ alpha: true, antialias: true, preserveDrawingBuffer: false }}
        style={{ background: 'transparent' }}
        dpr={[1, 2]}
      >
        <ambientLight intensity={0.5} />
        <directionalLight
          position={[3, 4, 3]}
          intensity={1.1}
          castShadow
          shadow-mapSize-width={1024}
          shadow-mapSize-height={1024}
        />
        <directionalLight position={[-3, 2, -2]} intensity={0.35} />
        <Environment preset="studio" />

        <Suspense fallback={null}>
          <AlignedScene avatarUrl={AVATAR_URL} garmentUrl={GARMENT_URL} />
          <ContactShadows
            position={[0, -0.9, 0]}
            opacity={0.28}
            scale={5}
            blur={2.6}
            far={2}
          />
        </Suspense>

        <OrbitControls
          enableZoom={false}
          enablePan={false}
          enableRotate={interactive}
          autoRotate
          autoRotateSpeed={rotateSpeed}
          minPolarAngle={Math.PI / 2.4}
          maxPolarAngle={Math.PI / 1.9}
        />
      </Canvas>
    </div>
  );
}

export default AvatarHero;
