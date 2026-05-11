'use client';

import { Suspense, useEffect, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Environment, ContactShadows, useGLTF } from '@react-three/drei';
import * as THREE from 'three';

/**
 * Canonical TryOn avatar + Ramin bow-sweats M garment GLBs, served from
 * frontend/public/redesign. These are the cleaner v45.12.1 drape outputs.
 *
 * Both GLBs share the same world coordinate system (the drape pipeline writes
 * the draped garment in the avatar's frame) modulo a unit mismatch: the avatar
 * pipeline exports millimeters, the drape pipeline exports meters. Each mesh
 * is pre-scaled to meters, then the wrapping group is fit to the canvas.
 */
const AVATAR_URL = '/redesign/avatar_textured.glb';
const GARMENT_URL = '/redesign/bow-sweats_m.glb';

const TARGET_HEIGHT = 1.8;
const FLOOR_Y = -0.9;

function geometryWorldBounds(root: THREE.Object3D): THREE.Box3 {
  const box = new THREE.Box3();
  root.updateMatrixWorld(true);
  root.traverse((c) => {
    if (!(c instanceof THREE.Mesh) || !c.geometry) return;
    const g = c.geometry as THREE.BufferGeometry;
    if (!g.boundingBox) g.computeBoundingBox();
    if (!g.boundingBox || g.boundingBox.isEmpty()) return;
    const b = g.boundingBox.clone();
    b.applyMatrix4(c.matrixWorld);
    box.union(b);
  });
  return box;
}

/**
 * Detect the unit of a GLB by its y-extent. The avatar pipeline exports in
 * millimeters (height ~1800), the drape pipeline exports in meters (height
 * ~1.83). Without this both meshes can't share a coordinate space and one
 * disappears when the combined group is normalized.
 */
function metersScaleFor(root: THREE.Object3D): number {
  const box = geometryWorldBounds(root);
  if (box.isEmpty()) return 1;
  const size = new THREE.Vector3();
  box.getSize(size);
  return size.y > 100 ? 0.001 : 1;
}

function DrapedScene({ avatarUrl, garmentUrl }: { avatarUrl: string; garmentUrl: string }) {
  const avatarGltf = useGLTF(avatarUrl);
  const garmentGltf = useGLTF(garmentUrl);
  const groupRef = useRef<THREE.Group>(null);

  useEffect(() => {
    const avatar = avatarGltf.scene;
    const garment = garmentGltf.scene;
    const group = groupRef.current;
    if (!group) return;

    avatar.position.set(0, 0, 0);
    avatar.rotation.set(0, 0, 0);
    avatar.scale.setScalar(metersScaleFor(avatar));
    garment.position.set(0, 0, 0);
    garment.rotation.set(0, 0, 0);
    garment.scale.setScalar(metersScaleFor(garment));

    avatar.traverse((c) => {
      if (c instanceof THREE.Mesh) {
        c.castShadow = true;
        c.receiveShadow = true;
      }
    });
    garment.traverse((c) => {
      if (c instanceof THREE.Mesh) {
        c.castShadow = true;
        if (c.material) {
          const mat = (c.material as THREE.MeshStandardMaterial).clone();
          mat.side = THREE.DoubleSide;
          c.material = mat;
        }
      }
    });

    group.scale.setScalar(1);
    group.position.set(0, 0, 0);
    group.updateMatrixWorld(true);

    const combined = geometryWorldBounds(group);
    if (combined.isEmpty()) return;

    const size = new THREE.Vector3();
    combined.getSize(size);
    const center = new THREE.Vector3();
    combined.getCenter(center);

    const scale = size.y > 1e-9 ? TARGET_HEIGHT / size.y : 1;
    group.scale.setScalar(scale);
    group.position.set(-center.x * scale, FLOOR_Y - combined.min.y * scale, -center.z * scale);
  }, [avatarGltf, garmentGltf, avatarUrl, garmentUrl]);

  return (
    <group ref={groupRef}>
      <primitive object={avatarGltf.scene} />
      <primitive object={garmentGltf.scene} />
    </group>
  );
}

interface AvatarHeroProps {
  height?: string;
  className?: string;
  interactive?: boolean;
  rotateSpeed?: number;
}

/**
 * Full-bleed 3D scene of the canonical TryOn avatar wearing the Ramin bow-sweats
 * M garment. Slow auto-rotate only. Drag, pan, and zoom are disabled so the
 * hero reads as a moving brand visual, not an interactive widget.
 *
 * Avatar and garment are loaded at the origin with no per-mesh normalization;
 * the drape pipeline already fit the garment to this avatar in shared world
 * coordinates, so any per-mesh scaling would break the fit and let the cloth
 * eat the avatar's face/hands.
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
      aria-label="3D avatar wearing Ramin Studios bow-sweats, size M"
    >
      <Canvas
        camera={{ position: [0, 0.05, 3.6], fov: 30 }}
        shadows
        gl={{
          alpha: true,
          antialias: true,
          preserveDrawingBuffer: false,
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: 1.25,
        }}
        style={{ background: 'transparent' }}
        dpr={[1, 2]}
      >
        <ambientLight intensity={0.45} />
        <directionalLight
          position={[5, 5, 5]}
          intensity={1.6}
          castShadow
          shadow-mapSize-width={2048}
          shadow-mapSize-height={2048}
        />
        <directionalLight position={[-3, 3, -3]} intensity={0.7} />
        <Environment preset="warehouse" environmentIntensity={1.1} />

        <Suspense fallback={null}>
          <DrapedScene avatarUrl={AVATAR_URL} garmentUrl={GARMENT_URL} />
          <ContactShadows
            position={[0, FLOOR_Y, 0]}
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
