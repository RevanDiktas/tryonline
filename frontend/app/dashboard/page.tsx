'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import type { WebGLRenderer } from 'three';
import { useTheme } from '@/contexts/ThemeContext';
import { getCurrentUser, getFitPassport, logout, updateFitPassport, User, FitPassport } from '@/lib/supabase-auth';
import { api, type UserAddress, type AddressCreatePayload } from '@/lib/api';

function SunIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  );
}
function MoonIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
    </svg>
  );
}

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
  const { theme, toggleTheme } = useTheme();
  const dark = theme === 'dark';
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const sceneRef = useRef<{ scene: any; setBackground: (hex: number) => void } | null>(null);
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
  const [loadTimeout, setLoadTimeout] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Shipping addresses (Shopper Passport)
  const [addresses, setAddresses] = useState<UserAddress[]>([]);
  const [addressesLoading, setAddressesLoading] = useState(false);
  const [addressError, setAddressError] = useState<string | null>(null);
  const [addressFormMode, setAddressFormMode] = useState<'idle' | 'add' | 'edit'>('idle');
  const [editingAddress, setEditingAddress] = useState<UserAddress | null>(null);
  const [addressSaving, setAddressSaving] = useState(false);
  const [addressForm, setAddressForm] = useState({
    label: '',
    name: '',
    line1: '',
    line2: '',
    city: '',
    state: '',
    postal_code: '',
    country: '',
    is_default: false,
  });

  const loadData = useCallback(async () => {
    setLoadTimeout(false);
    setLoadError(null);
    try {
      let currentUser: User | null;
      try {
        currentUser = await Promise.race([
          getCurrentUser(),
          new Promise<never>((_, reject) =>
            setTimeout(() => reject(new Error('LOAD_TIMEOUT')), 5000)
          ),
        ]);
      } catch (e) {
        if (e instanceof Error && e.message === 'LOAD_TIMEOUT') {
          setLoadTimeout(true);
          return;
        }
        throw e;
      }
      if (!currentUser) {
        router.push('/login');
        return;
      }

      if (currentUser.user_type === 'brand') {
        router.push('/brand');
        return;
      }

      setUser(currentUser);

      // Force fresh fetch - add timestamp to bypass any caching
      const fitPassport = await getFitPassport(currentUser.id);
      console.log('[Dashboard] ============================================');
      console.log('[Dashboard] Loaded fit passport on page load:', fitPassport);
      console.log('[Dashboard] Avatar URL from database:', fitPassport?.avatarUrl);
      console.log('[Dashboard] User ID:', currentUser.id);
      console.log('[Dashboard] ============================================');
      setPassport(fitPassport);
      
      // If no avatar URL but passport exists, it might still be generating
      // Refresh once after a delay to check for updates
      if (fitPassport && !fitPassport.avatarUrl) {
        console.log('[Dashboard] No avatar URL found, will retry in 3 seconds...');
        setTimeout(async () => {
          const refreshedPassport = await getFitPassport(currentUser.id);
          console.log('[Dashboard] Retry - Avatar URL:', refreshedPassport?.avatarUrl);
          if (refreshedPassport?.avatarUrl) {
            console.log('[Dashboard] ✓ Avatar URL found on retry:', refreshedPassport.avatarUrl);
            setPassport(refreshedPassport);
          }
        }, 3000);
      }
      
      // Set measurements from passport or calculate defaults
      // Use height from passport, or default to 175 if not available
      const h = fitPassport?.height || 175;
      setMeasurements({
        height: h,
        chest: fitPassport?.chest ?? Math.round(h * 0.53),
        waist: fitPassport?.waist ?? Math.round(h * 0.43),
        hips: fitPassport?.hips ?? Math.round(h * 0.50),
        inseam: fitPassport?.inseam ?? Math.round(h * 0.45),
        shoulder_width: fitPassport?.shoulder_width ?? Math.round(h * 0.24),
        arm_length: fitPassport?.arm_length ?? Math.round(h * 0.32),
        neck: fitPassport?.neck ?? Math.round(h * 0.21),
        thigh: fitPassport?.thigh ?? Math.round(h * 0.32),
        torso_length: fitPassport?.torso_length ?? Math.round(h * 0.30),
      });
    } catch (err) {
      console.error('[Dashboard] Load error:', err);
      setLoadError(err instanceof Error ? err.message : 'Failed to load');
    }
  }, [router]);

  useEffect(() => {
    setLoadTimeout(false);
    setLoadError(null);
    loadData();
  }, [loadData]);

  // Load addresses when user is available
  const loadAddresses = useCallback(async (userId: string) => {
    setAddressesLoading(true);
    setAddressError(null);
    try {
      const res = await api.getAddresses(userId);
      setAddresses(res.addresses);
    } catch (e) {
      setAddressError(e instanceof Error ? e.message : 'Failed to load addresses');
      setAddresses([]);
    } finally {
      setAddressesLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user?.id) loadAddresses(user.id);
  }, [user?.id, loadAddresses]);

  const resetAddressForm = useCallback(() => {
    setAddressForm({
      label: '',
      name: '',
      line1: '',
      line2: '',
      city: '',
      state: '',
      postal_code: '',
      country: '',
      is_default: false,
    });
    setAddressFormMode('idle');
    setEditingAddress(null);
  }, []);

  const startAddAddress = useCallback(() => {
    resetAddressForm();
    setAddressFormMode('add');
  }, [resetAddressForm]);

  const startEditAddress = useCallback((addr: UserAddress) => {
    setEditingAddress(addr);
    setAddressForm({
      label: addr.label,
      name: addr.name,
      line1: addr.line1,
      line2: addr.line2 || '',
      city: addr.city,
      state: addr.state || '',
      postal_code: addr.postal_code,
      country: addr.country,
      is_default: addr.is_default,
    });
    setAddressFormMode('edit');
  }, []);

  const saveAddress = useCallback(async () => {
    if (!user) return;
    setAddressSaving(true);
    setAddressError(null);
    try {
      if (addressFormMode === 'add') {
        const payload: AddressCreatePayload = {
          user_id: user.id,
          label: addressForm.label.trim(),
          name: addressForm.name.trim(),
          line1: addressForm.line1.trim(),
          city: addressForm.city.trim(),
          postal_code: addressForm.postal_code.trim(),
          country: addressForm.country.trim(),
          is_default: addressForm.is_default,
        };
        if (addressForm.line2.trim()) payload.line2 = addressForm.line2.trim();
        if (addressForm.state.trim()) payload.state = addressForm.state.trim();
        await api.createAddress(payload);
      } else if (addressFormMode === 'edit' && editingAddress) {
        await api.updateAddress(editingAddress.id, {
          user_id: user.id,
          label: addressForm.label.trim(),
          name: addressForm.name.trim(),
          line1: addressForm.line1.trim(),
          line2: addressForm.line2.trim() || undefined,
          city: addressForm.city.trim(),
          state: addressForm.state.trim() || undefined,
          postal_code: addressForm.postal_code.trim(),
          country: addressForm.country.trim(),
          is_default: addressForm.is_default,
        });
      }
      await loadAddresses(user.id);
      resetAddressForm();
    } catch (e) {
      setAddressError(e instanceof Error ? e.message : 'Failed to save address');
    } finally {
      setAddressSaving(false);
    }
  }, [user, addressFormMode, editingAddress, addressForm, loadAddresses, resetAddressForm]);

  const setDefaultAddress = useCallback(async (addr: UserAddress) => {
    if (!user || addr.is_default) return;
    setAddressSaving(true);
    setAddressError(null);
    try {
      await api.updateAddress(addr.id, { user_id: user.id, is_default: true });
      await loadAddresses(user.id);
    } catch (e) {
      setAddressError(e instanceof Error ? e.message : 'Failed to set default');
    } finally {
      setAddressSaving(false);
    }
  }, [user, loadAddresses]);

  const deleteAddress = useCallback(async (addr: UserAddress) => {
    if (!user || !confirm('Remove this address?')) return;
    setAddressSaving(true);
    setAddressError(null);
    try {
      await api.deleteAddress(addr.id, user.id);
      await loadAddresses(user.id);
      if (editingAddress?.id === addr.id) resetAddressForm();
    } catch (e) {
      setAddressError(e instanceof Error ? e.message : 'Failed to delete');
    } finally {
      setAddressSaving(false);
    }
  }, [user, editingAddress, loadAddresses, resetAddressForm]);

  // Initialize Three.js scene for avatar
  useEffect(() => {
    if (!canvasRef.current) return;

    let animationId: number;
    let rotation = 0;
    let renderer: WebGLRenderer | null = null;
    let currentModel: any = null;

    const initThreeJS = async () => {
      const THREE = await import('three');
      const { GLTFLoader } = await import('three/examples/jsm/loaders/GLTFLoader.js');

      const canvas = canvasRef.current;
      if (!canvas) return;

      const scene = new THREE.Scene();
      const isDark = typeof window !== 'undefined' && localStorage.getItem('tryon-theme') === 'dark';
      scene.background = new THREE.Color(isDark ? 0x0a0a0a : 0xf9fafb);
      sceneRef.current = {
        scene,
        setBackground: (hex: number) => { scene.background = new THREE.Color(hex); },
      };

      const camera = new THREE.PerspectiveCamera(35, canvas.clientWidth / canvas.clientHeight, 0.1, 1000);
      camera.position.set(0, 1.0, 3.5);
      camera.lookAt(0, 0.9, 0);

      renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
      renderer.setSize(canvas.clientWidth, canvas.clientHeight);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.3;

      // Lighting — brighter so avatar appears true to original color
      const ambientLight = new THREE.AmbientLight(0xffffff, 1.4);
      scene.add(ambientLight);

      const frontLight = new THREE.DirectionalLight(0xffffff, 1.5);
      frontLight.position.set(2, 3, 3);
      scene.add(frontLight);

      const backLight = new THREE.DirectionalLight(0xffffff, 1.0);
      backLight.position.set(-2, 2, -3);
      scene.add(backLight);

      const fillLight = new THREE.DirectionalLight(0xffffff, 0.8);
      fillLight.position.set(0, 2, 2);
      scene.add(fillLight);

      // Load GLB avatar model from user's fit passport
      const loader = new GLTFLoader();
      
      // Get avatar URL from passport - this should be the generated avatar_textured.glb from Supabase
      // The backend stores it at: avatars/{user_id}/avatar_textured.glb
      const avatarUrl = passport?.avatarUrl;
      
      // If no avatar URL in passport, show loading message
      if (!avatarUrl) {
        console.warn('[Dashboard] ⚠️ No avatar URL in passport yet. Passport data:', passport);
        console.warn('[Dashboard] Avatar may still be generating. Will retry when passport updates.');
        
        // Show loading placeholder
        const loadingText = document.createElement('div');
        loadingText.style.position = 'absolute';
        loadingText.style.top = '50%';
        loadingText.style.left = '50%';
        loadingText.style.transform = 'translate(-50%, -50%)';
        loadingText.style.color = '#666';
        loadingText.style.textAlign = 'center';
        loadingText.style.fontSize = '14px';
        loadingText.textContent = 'Loading your avatar...';
        if (canvas.parentElement) {
          canvas.parentElement.appendChild(loadingText);
        }
        
        // Still animate the scene
        const animate = () => {
          animationId = requestAnimationFrame(animate);
          if (renderer) renderer.render(scene, camera);
        };
        animate();
        return;
      }
      
      console.log('[Dashboard] ============================================');
      console.log('[Dashboard] ✓ Loading user-generated avatar from Supabase');
      console.log('[Dashboard] Avatar URL:', avatarUrl);
      console.log('[Dashboard] Passport data:', { 
        hasAvatarUrl: !!passport?.avatarUrl, 
        avatarUrl: passport?.avatarUrl,
        userId: passport?.user_id
      });
      console.log('[Dashboard] ============================================');
      
      // Remove previous model if exists
      if (currentModel) {
        scene.remove(currentModel);
        currentModel = null;
      }
      
      // Add cache busting to ensure we get the latest version
      // Append timestamp query param to force browser to fetch fresh file
      const cacheBustUrl = avatarUrl.includes('?') 
        ? `${avatarUrl}&t=${Date.now()}` 
        : `${avatarUrl}?t=${Date.now()}`;
      
      console.log('[Dashboard] Loading with cache-busted URL:', cacheBustUrl);
      
      loader.load(
        cacheBustUrl,
        (gltf) => {
          const model = gltf.scene;
          currentModel = model;
          
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
          console.log('[Dashboard] ============================================');
          console.log('[Dashboard] ✓✓✓ Avatar model loaded successfully! ✓✓✓');
          console.log('[Dashboard] Model URL:', avatarUrl);
          console.log('[Dashboard] Model vertices:', model.children.length, 'children');
          console.log('[Dashboard] ============================================');

          // Animation loop with rotation
          const animate = () => {
            animationId = requestAnimationFrame(animate);
            rotation += 0.008;
            model.rotation.y = rotation;
            if (renderer) renderer.render(scene, camera);
          };
          animate();
        },
        (progress) => {
          // Loading progress
          if (progress.lengthComputable) {
            const percent = (progress.loaded / progress.total) * 100;
            console.log(`[Dashboard] Loading avatar: ${percent.toFixed(1)}%`);
          }
        },
        (error) => {
          console.error('[Dashboard] ✗ Error loading user avatar from Supabase:', error);
          console.error('[Dashboard] Failed URL:', avatarUrl);
          console.error('[Dashboard] Error details:', error);
          
          // Show error message to user
          console.error('[Dashboard] ⚠️ Could not load your generated avatar. Please refresh the page or contact support if the issue persists.');
          
          // Don't load fallback - the user should see their actual avatar
          // Just show a placeholder message
          const errorText = document.createElement('div');
          errorText.style.position = 'absolute';
          errorText.style.top = '50%';
          errorText.style.left = '50%';
          errorText.style.transform = 'translate(-50%, -50%)';
          errorText.style.color = '#666';
          errorText.style.textAlign = 'center';
          errorText.style.fontSize = '14px';
          errorText.textContent = 'Avatar loading...';
          if (canvasRef.current?.parentElement) {
            canvasRef.current.parentElement.appendChild(errorText);
          }
          
          // Still animate the scene
          const animate = () => {
            animationId = requestAnimationFrame(animate);
            if (renderer) renderer.render(scene, camera);
          };
          animate();
        }
      );
    };

    initThreeJS();

    return () => {
      sceneRef.current = null;
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
      if (renderer) {
        renderer.dispose();
      }
    };
  }, [passport]); // Reload when passport changes (including avatarUrl)

  // Sync GLB viewer background with theme
  useEffect(() => {
    if (sceneRef.current) {
      sceneRef.current.setBackground(dark ? 0x0a0a0a : 0xf9fafb);
    }
  }, [theme, dark]);

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

  const handlePreferredFitChange = async (fit: 'slim' | 'regular' | 'loose') => {
    if (!user) return;
    setPassport((p) => (p ? { ...p, preferred_fit: fit } : p)); // optimistic — link/button update immediately
    setSaving(true);
    try {
      const updated = await updateFitPassport(user.id, { preferredFit: fit });
      if (!updated) {
        console.error('updateFitPassport returned null — run supabase-migration-fit-passports-preferred-fit.sql if fit_passports lacks preferred_fit');
        const fresh = await getFitPassport(user.id);
        if (fresh) setPassport(fresh);
      }
    } catch (err) {
      console.error('Error saving preferred fit:', err);
      const fresh = await getFitPassport(user.id);
      if (fresh) setPassport(fresh);
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
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center gap-6 px-4">
        {loadTimeout || loadError ? (
          <>
            <p className="text-slate-600 text-center max-w-sm">
              {loadTimeout
                ? 'Taking longer than expected. Check your connection and try again.'
                : loadError}
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => loadData()}
                className="px-4 py-2.5 text-sm font-medium rounded-xl bg-slate-900 text-white hover:bg-slate-800 transition"
              >
                Retry
              </button>
              <Link
                href="/login"
                className="px-4 py-2.5 text-sm font-medium rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-50 transition"
              >
                Go to login
              </Link>
            </div>
          </>
        ) : (
          <>
            <div className="w-8 h-8 border-2 border-slate-300 border-t-slate-600 rounded-full animate-spin" />
            <p className="text-slate-500 text-sm">Loading your dashboard…</p>
          </>
        )}
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
    <div className={`min-h-screen transition-colors ${dark ? 'bg-black text-white' : 'bg-slate-50 text-black'}`}>
      <header className={`sticky top-0 z-10 backdrop-blur-md border-b shadow-sm ${dark ? 'bg-black/95 border-white/10' : 'bg-white/95 border-slate-200/80'}`}>
        <div className="max-w-6xl mx-auto px-4 md:px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/tryon-logo.jpg" alt="TRYON" className="h-12 w-auto cursor-pointer hover:opacity-90 transition-opacity" />
          </Link>
          <div className="flex items-center gap-6">
            <span className={`text-sm hidden sm:inline ${dark ? 'text-white/60' : 'text-slate-500'}`}>{user.email}</span>
            <button onClick={toggleTheme} className={`p-2 rounded-lg border transition-colors ${dark ? 'border-white/10 text-white/70 hover:bg-white/5' : 'border-slate-200 text-slate-600 hover:bg-slate-100'}`} title={dark ? 'Switch to light mode' : 'Switch to dark mode'}>
              {dark ? <SunIcon /> : <MoonIcon />}
            </button>
            <button onClick={handleLogout} className={`text-sm transition-colors ${dark ? 'text-white/60 hover:text-white' : 'text-slate-500 hover:text-slate-900'}`}>
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 md:px-6 py-8 md:py-10 dashboard-fade-in">
        <div className="mb-8">
          <h2 className={`text-2xl font-bold mb-2 tracking-tight ${dark ? 'text-white' : 'text-slate-900'}`}>
            Welcome back, {(user.name || 'User').split(' ')[0]}
          </h2>
          <p className={dark ? 'text-white/60' : 'text-gray-500'}>
            Your Fit Passport is ready. Try on clothes from any brand.
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          <div className={`rounded-2xl p-6 transition-all duration-300 ${dark ? 'bg-white/[0.03]' : 'bg-white shadow-sm'}`}>
            <h3 className={`text-lg font-semibold mb-4 tracking-tight ${dark ? 'text-white' : 'text-slate-900'}`}>Your Avatar</h3>
            <div className={`aspect-square rounded-xl overflow-hidden relative ${dark ? 'bg-black/30' : 'bg-slate-50'}`}>
              <canvas 
                ref={canvasRef} 
                className="w-full h-full"
                style={{ display: 'block' }}
              />
            </div>
            <p className={`text-xs text-center mt-3 ${dark ? 'text-white/50' : 'text-gray-400'}`}>
              Rotating 360° preview of your avatar
            </p>
          </div>

          <div className={`rounded-2xl p-6 transition-all duration-300 ${dark ? 'bg-white/[0.03]' : 'bg-white shadow-sm'}`}>
            <div className="flex items-center justify-between mb-6">
              <h3 className={`text-lg font-semibold tracking-tight ${dark ? 'text-white' : 'text-black'}`}>Your Measurements</h3>
              {!isEditing ? (
                <button
                  onClick={() => setIsEditing(true)}
                  className={`px-4 py-2 text-sm font-medium rounded-xl transition-all duration-200 ${dark ? 'text-black bg-white hover:bg-white/90' : 'text-white bg-slate-900 hover:bg-slate-800'}`}
                >
                  Edit
                </button>
              ) : (
                <div className="flex gap-2">
                  <button
                    onClick={() => setIsEditing(false)}
                    className={`px-4 py-2 text-sm font-medium rounded-lg transition ${dark ? 'text-white/60 border-white/20 hover:bg-white/5' : 'text-gray-500 border-gray-200 hover:bg-gray-50'}`}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveMeasurements}
                    disabled={saving}
                    className={`px-4 py-2 text-sm font-medium rounded-lg transition disabled:opacity-50 ${dark ? 'text-black bg-white hover:bg-white/90' : 'text-white bg-black hover:bg-gray-800'}`}
                  >
                    {saving ? 'Saving...' : 'Save'}
                  </button>
                </div>
              )}
            </div>

            {isEditing && (
              <div className={`mb-4 p-3 rounded-lg ${dark ? 'bg-white/5' : 'bg-blue-50'}`}>
                <p className={`text-sm ${dark ? 'text-white/80' : 'text-blue-700'}`}>
                  Review your measurements below. If any are incorrect, you can adjust them.
                </p>
                </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              {measurementFields.map((field) => (
                <div key={field.key} className={`p-3 rounded-xl ${dark ? 'bg-white/5' : 'bg-gray-50'}`}>
                  <p className={`text-xs uppercase tracking-wider mb-1 ${dark ? 'text-white/50' : 'text-gray-400'}`}>{field.label}</p>
                  {isEditing && field.editable ? (
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        value={measurements[field.key as keyof Measurements]}
                        onChange={(e) => setMeasurements({
                          ...measurements,
                          [field.key]: parseInt(e.target.value) || 0
                        })}
                        className={`w-full px-2 py-1 text-lg font-bold rounded focus:outline-none focus:ring-2 ${dark ? 'text-white bg-black/30 border-white/20 focus:ring-white/30' : 'text-black bg-white border-gray-200 focus:ring-black'}`}
                      />
                      <span className={`text-sm ${dark ? 'text-white/50' : 'text-gray-400'}`}>cm</span>
                </div>
                  ) : (
                    <p className={`text-lg font-bold ${dark ? 'text-white' : 'text-black'}`}>
                      {measurements[field.key as keyof Measurements]}
                      <span className={`text-sm font-normal ml-1 ${dark ? 'text-white/50' : 'text-gray-400'}`}>cm</span>
                    </p>
                  )}
                </div>
              ))}
                </div>

            {/* Fit preference — used for size recommendations */}
            <div className={`mt-6 pt-4 border-t ${dark ? 'border-white/10' : 'border-gray-100'}`}>
              <p className={`text-xs uppercase tracking-wider mb-2 ${dark ? 'text-white/50' : 'text-gray-400'}`}>Preferred Fit</p>
              <p className={`text-sm mb-3 ${dark ? 'text-white/60' : 'text-gray-500'}`}>How you like clothes to fit. Affects size recommendations.</p>
              <div className="flex gap-2">
                {(['slim', 'regular', 'loose'] as const).map((fit) => (
                  <button
                    key={fit}
                    onClick={() => handlePreferredFitChange(fit)}
                    disabled={saving}
                    className={`px-4 py-2 text-sm font-medium rounded-lg transition capitalize ${
                      passport?.preferred_fit === fit
                        ? dark ? 'bg-white text-black' : 'bg-black text-white'
                        : dark ? 'bg-white/10 text-white/80 hover:bg-white/20' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    } disabled:opacity-50`}
                  >
                    {fit}
                  </button>
                ))}
              </div>
            </div>

            {!isEditing && (
              <p className={`text-xs mt-4 text-center ${dark ? 'text-white/50' : 'text-gray-400'}`}>
                Are these measurements accurate? Click Edit to make corrections.
              </p>
            )}
          </div>

          {/* Shipping addresses — Shopper Passport */}
          <div className={`lg:col-span-2 rounded-2xl p-6 transition-all duration-300 ${dark ? 'bg-white/[0.03]' : 'bg-white shadow-sm'}`}>
            <div className="flex items-center justify-between mb-4">
              <h3 className={`text-lg font-semibold tracking-tight ${dark ? 'text-white' : 'text-slate-900'}`}>Shipping addresses</h3>
              {addressFormMode === 'idle' && (
                <button
                  type="button"
                  onClick={startAddAddress}
                  className={`px-4 py-2 text-sm font-medium rounded-xl transition ${dark ? 'text-black bg-white hover:bg-white/90' : 'text-white bg-slate-900 hover:bg-slate-800'}`}
                >
                  Add address
                </button>
              )}
            </div>
            <p className={`text-sm mb-4 ${dark ? 'text-white/60' : 'text-slate-500'}`}>
              Your saved addresses for checkout. Use one as default at TryOn brands.
            </p>
            {addressError && (
              <p className={`text-sm mb-3 px-3 py-2 rounded-lg ${dark ? 'bg-red-500/10 text-red-400' : 'bg-red-50 text-red-600'}`}>
                {addressError}
              </p>
            )}
            {addressesLoading ? (
              <p className={`text-sm ${dark ? 'text-white/50' : 'text-slate-400'}`}>Loading addresses…</p>
            ) : (addressFormMode === 'add' || addressFormMode === 'edit') ? (
              <div className={`space-y-3 p-4 rounded-xl ${dark ? 'bg-white/5' : 'bg-slate-50'}`}>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className={`block text-xs font-medium mb-1 ${dark ? 'text-white/60' : 'text-slate-500'}`}>Label (e.g. Home, Work)</label>
                    <input
                      value={addressForm.label}
                      onChange={(e) => setAddressForm((f) => ({ ...f, label: e.target.value }))}
                      placeholder="Home"
                      className={`w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2 ${dark ? 'bg-black/30 border-white/20 text-white focus:ring-white/30' : 'bg-white border-slate-200 text-slate-900 focus:ring-slate-900'}`}
                    />
                  </div>
                  <div>
                    <label className={`block text-xs font-medium mb-1 ${dark ? 'text-white/60' : 'text-slate-500'}`}>Full name</label>
                    <input
                      value={addressForm.name}
                      onChange={(e) => setAddressForm((f) => ({ ...f, name: e.target.value }))}
                      placeholder="Jane Doe"
                      className={`w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2 ${dark ? 'bg-black/30 border-white/20 text-white focus:ring-white/30' : 'bg-white border-slate-200 text-slate-900 focus:ring-slate-900'}`}
                    />
                  </div>
                </div>
                <div>
                  <label className={`block text-xs font-medium mb-1 ${dark ? 'text-white/60' : 'text-slate-500'}`}>Address line 1</label>
                  <input
                    value={addressForm.line1}
                    onChange={(e) => setAddressForm((f) => ({ ...f, line1: e.target.value }))}
                    placeholder="Street and number"
                    className={`w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2 ${dark ? 'bg-black/30 border-white/20 text-white focus:ring-white/30' : 'bg-white border-slate-200 text-slate-900 focus:ring-slate-900'}`}
                  />
                </div>
                <div>
                  <label className={`block text-xs font-medium mb-1 ${dark ? 'text-white/60' : 'text-slate-500'}`}>Address line 2 (optional)</label>
                  <input
                    value={addressForm.line2}
                    onChange={(e) => setAddressForm((f) => ({ ...f, line2: e.target.value }))}
                    placeholder="Apt, suite, etc."
                    className={`w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2 ${dark ? 'bg-black/30 border-white/20 text-white focus:ring-white/30' : 'bg-white border-slate-200 text-slate-900 focus:ring-slate-900'}`}
                  />
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div>
                    <label className={`block text-xs font-medium mb-1 ${dark ? 'text-white/60' : 'text-slate-500'}`}>City</label>
                    <input
                      value={addressForm.city}
                      onChange={(e) => setAddressForm((f) => ({ ...f, city: e.target.value }))}
                      className={`w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2 ${dark ? 'bg-black/30 border-white/20 text-white focus:ring-white/30' : 'bg-white border-slate-200 text-slate-900 focus:ring-slate-900'}`}
                    />
                  </div>
                  <div>
                    <label className={`block text-xs font-medium mb-1 ${dark ? 'text-white/60' : 'text-slate-500'}`}>State / Province</label>
                    <input
                      value={addressForm.state}
                      onChange={(e) => setAddressForm((f) => ({ ...f, state: e.target.value }))}
                      className={`w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2 ${dark ? 'bg-black/30 border-white/20 text-white focus:ring-white/30' : 'bg-white border-slate-200 text-slate-900 focus:ring-slate-900'}`}
                    />
                  </div>
                  <div>
                    <label className={`block text-xs font-medium mb-1 ${dark ? 'text-white/60' : 'text-slate-500'}`}>Postal code</label>
                    <input
                      value={addressForm.postal_code}
                      onChange={(e) => setAddressForm((f) => ({ ...f, postal_code: e.target.value }))}
                      className={`w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2 ${dark ? 'bg-black/30 border-white/20 text-white focus:ring-white/30' : 'bg-white border-slate-200 text-slate-900 focus:ring-slate-900'}`}
                    />
                  </div>
                  <div>
                    <label className={`block text-xs font-medium mb-1 ${dark ? 'text-white/60' : 'text-slate-500'}`}>Country</label>
                    <input
                      value={addressForm.country}
                      onChange={(e) => setAddressForm((f) => ({ ...f, country: e.target.value }))}
                      placeholder="e.g. US"
                      className={`w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2 ${dark ? 'bg-black/30 border-white/20 text-white focus:ring-white/30' : 'bg-white border-slate-200 text-slate-900 focus:ring-slate-900'}`}
                    />
                  </div>
                </div>
                <div className="flex items-center gap-4 pt-2">
                  <label className={`flex items-center gap-2 text-sm cursor-pointer ${dark ? 'text-white/80' : 'text-slate-700'}`}>
                    <input
                      type="checkbox"
                      checked={addressForm.is_default}
                      onChange={(e) => setAddressForm((f) => ({ ...f, is_default: e.target.checked }))}
                      className="rounded border-slate-300"
                    />
                    Use at checkout (default)
                  </label>
                  <div className="flex gap-2 ml-auto">
                    <button
                      type="button"
                      onClick={resetAddressForm}
                      className={`px-4 py-2 text-sm font-medium rounded-lg transition ${dark ? 'text-white/60 hover:bg-white/5' : 'text-slate-600 hover:bg-slate-100'}`}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={saveAddress}
                      disabled={addressSaving || !addressForm.label.trim() || !addressForm.name.trim() || !addressForm.line1.trim() || !addressForm.city.trim() || !addressForm.postal_code.trim() || !addressForm.country.trim()}
                      className={`px-4 py-2 text-sm font-medium rounded-lg transition disabled:opacity-50 ${dark ? 'text-black bg-white hover:bg-white/90' : 'text-white bg-slate-900 hover:bg-slate-800'}`}
                    >
                      {addressSaving ? 'Saving…' : 'Save address'}
                    </button>
                  </div>
                </div>
              </div>
            ) : addresses.length === 0 ? (
              <p className={`text-sm ${dark ? 'text-white/50' : 'text-slate-500'}`}>No addresses yet. Add one to use at checkout.</p>
            ) : (
              <ul className="space-y-3">
                {addresses.map((addr) => (
                  <li
                    key={addr.id}
                    className={`flex flex-wrap items-start justify-between gap-3 p-4 rounded-xl transition ${dark ? 'bg-white/5 hover:bg-white/[0.07]' : 'bg-slate-50 hover:bg-slate-100/80'}`}
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`font-medium ${dark ? 'text-white' : 'text-slate-900'}`}>{addr.label}</span>
                        {addr.is_default && (
                          <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${dark ? 'bg-white/20 text-white/90' : 'bg-slate-200 text-slate-700'}`}>
                            Use at checkout
                          </span>
                        )}
                      </div>
                      <p className={`text-sm mt-1 ${dark ? 'text-white/70' : 'text-slate-600'}`}>
                        {addr.name}<br />
                        {addr.line1}
                        {addr.line2 ? `, ${addr.line2}` : ''}<br />
                        {[addr.city, addr.state, addr.postal_code].filter(Boolean).join(', ')} {addr.country}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {!addr.is_default && (
                        <button
                          type="button"
                          onClick={() => setDefaultAddress(addr)}
                          disabled={addressSaving}
                          className={`text-sm font-medium px-3 py-1.5 rounded-lg transition disabled:opacity-50 ${dark ? 'text-white/70 hover:bg-white/10' : 'text-slate-600 hover:bg-slate-200'}`}
                        >
                          Set default
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => startEditAddress(addr)}
                        disabled={addressSaving}
                        className={`text-sm font-medium px-3 py-1.5 rounded-lg transition disabled:opacity-50 ${dark ? 'text-white/70 hover:bg-white/10' : 'text-slate-600 hover:bg-slate-200'}`}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => deleteAddress(addr)}
                        disabled={addressSaving}
                        className={`text-sm font-medium px-3 py-1.5 rounded-lg transition disabled:opacity-50 ${dark ? 'text-red-400 hover:bg-red-500/10' : 'text-red-600 hover:bg-red-50'}`}
                      >
                        Remove
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className={`rounded-2xl p-6 transition-all duration-300 ${dark ? 'bg-white/[0.03]' : 'bg-white shadow-sm'}`}>
            <h3 className={`text-lg font-semibold mb-4 tracking-tight ${dark ? 'text-white' : 'text-slate-900'}`}>Account Information</h3>
            <div className="space-y-3">
              {['Name', 'Email', 'Member since', 'Gender'].map((label, i) => (
                <div key={label} className={`p-4 rounded-xl ${dark ? 'bg-white/5' : 'bg-gray-50'}`}>
                  <p className={`text-xs uppercase tracking-wider mb-1 ${dark ? 'text-white/50' : 'text-gray-400'}`}>{label}</p>
                  <p className={`font-medium ${dark ? 'text-white' : 'text-black'}`}>
                    {label === 'Name' ? user.name : label === 'Email' ? user.email : label === 'Member since' ? new Date(user.created_at ?? '').toLocaleDateString() : (passport?.gender || 'Not set')}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className={`rounded-2xl p-6 transition-all duration-300 ${dark ? 'bg-white/[0.03]' : 'bg-white shadow-sm'}`}>
            <div className="flex items-center justify-between mb-4">
              <h3 className={`text-lg font-semibold tracking-tight ${dark ? 'text-white' : 'text-black'}`}>Fit Passport Status</h3>
              <span className={`px-3 py-1 text-xs font-medium rounded-full ${dark ? 'bg-white/10 text-white/80' : 'bg-green-50 text-green-600'}`}>
                Active
              </span>
            </div>
            
            <div className="space-y-4">
              <div className={`flex items-center gap-3 p-3 rounded-xl ${dark ? 'bg-white/5' : 'bg-gray-50'}`}>
                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${dark ? 'bg-white/10' : 'bg-green-100'}`}>
                  <svg className={`w-5 h-5 ${dark ? 'text-white/80' : 'text-green-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <p className={`text-sm font-medium ${dark ? 'text-white' : 'text-black'}`}>Avatar created</p>
                  <p className={`text-xs ${dark ? 'text-white/50' : 'text-gray-400'}`}>Ready to try on clothes</p>
                </div>
              </div>
              
              <div className={`flex items-center gap-3 p-3 rounded-xl ${dark ? 'bg-white/5' : 'bg-gray-50'}`}>
                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${dark ? 'bg-white/10' : 'bg-green-100'}`}>
                  <svg className={`w-5 h-5 ${dark ? 'text-white/80' : 'text-green-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <p className={`text-sm font-medium ${dark ? 'text-white' : 'text-black'}`}>Measurements saved</p>
                  <p className={`text-xs ${dark ? 'text-white/50' : 'text-gray-400'}`}>Size recommendations enabled</p>
                </div>
              </div>

              <div className={`pt-4 border-t ${dark ? 'border-white/10' : 'border-gray-100'}`}>
              <button
                onClick={handleClearData}
                className={`w-full py-3 text-sm rounded-xl transition ${dark ? 'text-red-400 hover:bg-red-500/10' : 'text-red-500 hover:bg-red-50'}`}
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
