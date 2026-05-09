'use client';

import { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Environment, ContactShadows } from '@react-three/drei';
import { AlignedScene } from '@/components/TryOnViewer';

/**
 * Canonical TryOn avatar + Ramin small-logo M garment GLBs (public Supabase).
 * Same URLs the drape pipeline tests against, so we know they render correctly.
 */
const AVATAR_URL =
  'https://cykwthsbrylonconqlfz.supabase.co/storage/v1/object/public/avatars/ca5808a9-99bd-45a2-86ec-f3f0f90db831/avatar_textured.glb';
const GARMENT_URL =
  'https://cykwthsbrylonconqlfz.supabase.co/storage/v1/object/public/garments/27ca6be1-55f6-4e94-b13f-49de33ac959a/small-logo/m.glb';

interface AvatarHeroProps {
  /** CSS height for the canvas container. Default 70vh. */
  height?: string;
  className?: string;
  /** Allow user to drag-rotate the avatar. Default true. */
  interactive?: boolean;
  /** Auto-rotate speed (drei units, ~0.6 to 1.2 reads as slow). Default 0.8. */
  rotateSpeed?: number;
}

/**
 * Full-bleed 3D scene of the canonical TryOn avatar wearing the Ramin small-logo
 * M garment. Slow auto-rotate, neutral studio lighting, transparent background.
 *
 * Reuses AlignedScene from TryOnViewer so the hero scene matches what shoppers
 * see during a real try-on (same scaling, same alignment, same cache).
 *
 * Cobalt accent stays out of the scene; lighting is neutral so the garment
 * colors read true and the brand-side visuals don't compete with the page CTA.
 */
export function AvatarHero({
  height = '70vh',
  className = '',
  interactive = true,
  rotateSpeed = 0.8,
}: AvatarHeroProps) {
  return (
    <div
      className={className}
      style={{ width: '100%', height, position: 'relative' }}
      aria-label="3D avatar wearing Ramin Studios garment, size M"
    >
      <Canvas
        camera={{ position: [0, 0.35, 2.6], fov: 28 }}
        shadows
        gl={{ alpha: true, antialias: true, preserveDrawingBuffer: false }}
        style={{ background: 'transparent' }}
        dpr={[1, 2]}
      >
        <ambientLight intensity={0.45} />
        <directionalLight
          position={[3, 4, 3]}
          intensity={1.2}
          castShadow
          shadow-mapSize-width={1024}
          shadow-mapSize-height={1024}
        />
        <directionalLight position={[-3, 2, -2]} intensity={0.4} />
        <Environment preset="studio" />

        <Suspense fallback={null}>
          <AlignedScene avatarUrl={AVATAR_URL} garmentUrl={GARMENT_URL} />
          <ContactShadows
            position={[0, -0.9, 0]}
            opacity={0.32}
            scale={4}
            blur={2.4}
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
