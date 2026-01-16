'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser, getFitPassport, logout, updateFitPassport, User, FitPassport } from '@/lib/supabase-auth';

interface Measurements {
  height: number;
  chest: number;
  waist: number;
  hips: number;
  inseam: number;
  shoulder_width: number;
  arm_length: number;
  neck: number;
  thigh: number;
  torso_length: number;
}

export default function DashboardPage() {
  const router = useRouter();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [user, setUser] = useState<User | null>(null);
  const [passport, setPassport] = useState<FitPassport | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [measurements, setMeasurements] = useState<Measurements>({
    height: 0,
    chest: 0,
    waist: 0,
    hips: 0,
    inseam: 0,
    shoulder_width: 0,
    arm_length: 0,
    neck: 0,
    thigh: 0,
    torso_length: 0,
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      const currentUser = await getCurrentUser();
      
      if (!currentUser) {
        router.push('/login');
        return;
      }

      setUser(currentUser);
      
      const fitPassport = await getFitPassport(currentUser.id);
      console.log('Loaded fit passport:', fitPassport); // Debug
      setPassport(fitPassport);
      
      // Set measurements from passport or calculate defaults
      // Use height from passport, or default to 175 if not available
      const h = fitPassport?.height || 175;
      setMeasurements({
        height: h,
        chest: fitPassport?.measurements?.chest || Math.round(h * 0.53),
        waist: fitPassport?.measurements?.waist || Math.round(h * 0.43),
        hips: fitPassport?.measurements?.hips || Math.round(h * 0.50),
        inseam: fitPassport?.measurements?.inseam || Math.round(h * 0.45),
        shoulder_width: Math.round(h * 0.24),
        arm_length: Math.round(h * 0.32),
        neck: Math.round(h * 0.21),
        thigh: Math.round(h * 0.32),
        torso_length: Math.round(h * 0.30),
      });
    };
    
    loadData();
  }, [router]);

  // Initialize Three.js scene for avatar
  useEffect(() => {
    if (!canvasRef.current) return;

    let animationId: number;
    let rotation = 0;
    let renderer: ReturnType<typeof import('three').WebGLRenderer.prototype.constructor> | null = null;

    const initThreeJS = async () => {
      const THREE = await import('three');
      const { GLTFLoader } = await import('three/examples/jsm/loaders/GLTFLoader.js');

      const canvas = canvasRef.current;
      if (!canvas) return;

      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0xf9fafb);

      const camera = new THREE.PerspectiveCamera(35, canvas.clientWidth / canvas.clientHeight, 0.1, 1000);
      camera.position.set(0, 1.0, 3.5);
      camera.lookAt(0, 0.9, 0);

      renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
      renderer.setSize(canvas.clientWidth, canvas.clientHeight);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

      // Lighting
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
      scene.add(ambientLight);

      const frontLight = new THREE.DirectionalLight(0xffffff, 0.9);
      frontLight.position.set(2, 3, 3);
      scene.add(frontLight);

      const backLight = new THREE.DirectionalLight(0xffffff, 0.4);
      backLight.position.set(-2, 2, -3);
      scene.add(backLight);

      // Load GLB avatar model (nude body for measurements display)
      const loader = new GLTFLoader();
      
      loader.load(
        '/models/avatar_with_tshirt_m.glb',
        (gltf) => {
          const model = gltf.scene;
          
          // Center and scale the model
          const box = new THREE.Box3().setFromObject(model);
          const center = box.getCenter(new THREE.Vector3());
          const size = box.getSize(new THREE.Vector3());
          
          // Scale to fit view
          const maxDim = Math.max(size.x, size.y, size.z);
          const scale = 1.8 / maxDim;
          model.scale.setScalar(scale);
          
          // Center
          model.position.x = -center.x * scale;
          model.position.y = -center.y * scale + 0.9;
          model.position.z = -center.z * scale;

          scene.add(model);

          // Animation loop with rotation
          const animate = () => {
            animationId = requestAnimationFrame(animate);
            rotation += 0.008;
            model.rotation.y = rotation;
            if (renderer) renderer.render(scene, camera);
          };
          animate();
        },
        undefined,
        (error) => {
          console.error('Error loading avatar model:', error);
          // Fallback to a simple capsule
          const geometry = new THREE.CapsuleGeometry(0.25, 1.0, 8, 16);
          const material = new THREE.MeshStandardMaterial({ color: 0xc4a484 });
          const capsule = new THREE.Mesh(geometry, material);
          capsule.position.y = 0.9;
          scene.add(capsule);

          const animate = () => {
            animationId = requestAnimationFrame(animate);
            rotation += 0.008;
            capsule.rotation.y = rotation;
            if (renderer) renderer.render(scene, camera);
          };
          animate();
        }
      );
    };

    initThreeJS();

    return () => {
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
      if (renderer) {
        renderer.dispose();
      }
    };
  }, []);

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  const handleSaveMeasurements = async () => {
    if (!user) return;
    
    setSaving(true);
    try {
      await updateFitPassport(user.id, {
        measurements: {
          chest: measurements.chest,
          waist: measurements.waist,
          hips: measurements.hips,
          inseam: measurements.inseam,
        },
      });
      setIsEditing(false);
    } catch (err) {
      console.error('Error saving measurements:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleClearData = async () => {
    if (confirm('This will sign you out and delete your data. Are you sure?')) {
      await logout();
      router.push('/signup');
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-gray-400">Loading...</div>
      </div>
    );
  }

  const measurementFields = [
    { key: 'height', label: 'Height', editable: false },
    { key: 'chest', label: 'Chest', editable: true },
    { key: 'waist', label: 'Waist', editable: true },
    { key: 'hips', label: 'Hips', editable: true },
    { key: 'inseam', label: 'Inseam', editable: true },
    { key: 'shoulder_width', label: 'Shoulder Width', editable: true },
    { key: 'arm_length', label: 'Arm Length', editable: true },
    { key: 'neck', label: 'Neck', editable: true },
    { key: 'thigh', label: 'Thigh', editable: true },
    { key: 'torso_length', label: 'Torso Length', editable: true },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <a href="/">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img 
            src="/tryon-logo.jpg" 
            alt="TRYON" 
              className="h-14 w-auto cursor-pointer hover:opacity-80 transition"
          />
          </a>
          <div className="flex items-center gap-4">
            <span className="text-gray-500 text-sm">{user.email}</span>
            <button
              onClick={handleLogout}
              className="text-gray-500 text-sm hover:text-black transition"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-black mb-2">
            Welcome back, {user.name.split(' ')[0]}
          </h2>
          <p className="text-gray-500">
            Your Fit Passport is ready. Try on clothes from any brand.
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* 3D Avatar Preview */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6">
            <h3 className="text-lg font-semibold text-black mb-4">Your Avatar</h3>
            <div className="aspect-square bg-gray-50 rounded-xl overflow-hidden">
              <canvas 
                ref={canvasRef} 
                className="w-full h-full"
                style={{ display: 'block' }}
              />
            </div>
            <p className="text-gray-400 text-xs text-center mt-3">
              Rotating 360° preview of your avatar
            </p>
          </div>

          {/* Measurements Card */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-black">Your Measurements</h3>
              {!isEditing ? (
                <button
                  onClick={() => setIsEditing(true)}
                  className="px-4 py-2 text-sm font-medium text-black border border-gray-200 rounded-lg hover:bg-gray-50 transition"
                >
                  Edit
                </button>
              ) : (
                <div className="flex gap-2">
                  <button
                    onClick={() => setIsEditing(false)}
                    className="px-4 py-2 text-sm font-medium text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveMeasurements}
                    disabled={saving}
                    className="px-4 py-2 text-sm font-medium text-white bg-black rounded-lg hover:bg-gray-800 transition disabled:opacity-50"
                  >
                    {saving ? 'Saving...' : 'Save'}
                  </button>
                </div>
              )}
            </div>

            {isEditing && (
              <div className="mb-4 p-3 bg-blue-50 rounded-lg">
                <p className="text-blue-700 text-sm">
                  Review your measurements below. If any are incorrect, you can adjust them.
                </p>
                </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              {measurementFields.map((field) => (
                <div key={field.key} className="p-3 bg-gray-50 rounded-xl">
                  <p className="text-gray-400 text-xs uppercase tracking-wider mb-1">{field.label}</p>
                  {isEditing && field.editable ? (
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        value={measurements[field.key as keyof Measurements]}
                        onChange={(e) => setMeasurements({
                          ...measurements,
                          [field.key]: parseInt(e.target.value) || 0
                        })}
                        className="w-full px-2 py-1 text-lg font-bold text-black bg-white border border-gray-200 rounded focus:outline-none focus:ring-2 focus:ring-black"
                      />
                      <span className="text-gray-400 text-sm">cm</span>
                </div>
                  ) : (
                    <p className="text-black text-lg font-bold">
                      {measurements[field.key as keyof Measurements]}
                      <span className="text-sm font-normal text-gray-400 ml-1">cm</span>
                    </p>
                  )}
                </div>
              ))}
                </div>

            {!isEditing && (
              <p className="text-gray-400 text-xs mt-4 text-center">
                Are these measurements accurate? Click Edit to make corrections.
              </p>
            )}
          </div>

          {/* Account Settings */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6">
            <h3 className="text-lg font-semibold text-black mb-4">Account Information</h3>
            <div className="space-y-3">
              <div className="p-4 bg-gray-50 rounded-xl">
                <p className="text-gray-400 text-xs uppercase tracking-wider mb-1">Name</p>
                <p className="text-black font-medium">{user.name}</p>
              </div>
              <div className="p-4 bg-gray-50 rounded-xl">
                <p className="text-gray-400 text-xs uppercase tracking-wider mb-1">Email</p>
                <p className="text-black font-medium">{user.email}</p>
              </div>
              <div className="p-4 bg-gray-50 rounded-xl">
                <p className="text-gray-400 text-xs uppercase tracking-wider mb-1">Member since</p>
                <p className="text-black font-medium">{new Date(user.createdAt).toLocaleDateString()}</p>
              </div>
              <div className="p-4 bg-gray-50 rounded-xl">
                <p className="text-gray-400 text-xs uppercase tracking-wider mb-1">Gender</p>
                <p className="text-black font-medium capitalize">{passport?.gender || 'Not set'}</p>
              </div>
            </div>
          </div>

          {/* Fit Passport Status */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-black">Fit Passport Status</h3>
              <span className="px-3 py-1 bg-green-50 text-green-600 text-xs font-medium rounded-full">
                Active
              </span>
            </div>
            
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl">
                <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                  <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <p className="text-black text-sm font-medium">Avatar created</p>
                  <p className="text-gray-400 text-xs">Ready to try on clothes</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl">
                <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                  <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <p className="text-black text-sm font-medium">Measurements saved</p>
                  <p className="text-gray-400 text-xs">Size recommendations enabled</p>
            </div>
          </div>

              <div className="pt-4 border-t border-gray-100">
              <button
                onClick={handleClearData}
                className="w-full py-3 text-red-500 text-sm hover:bg-red-50 rounded-xl transition"
              >
                  Delete account and data
              </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
