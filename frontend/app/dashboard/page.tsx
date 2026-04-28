'use client';

import { useEffect, useState, useRef, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import type { WebGLRenderer } from 'three';
import { useTheme } from '@/contexts/ThemeContext';
import { getCurrentUser, getFitPassport, logout, updateFitPassport, User, FitPassport } from '@/lib/supabase-auth';
import { api, type UserAddress, type AddressCreatePayload, type SavedItem } from '@/lib/api';
import dynamic from 'next/dynamic';
import {
  DashThemeShell,
  FloatingNav,
  DashCard,
  DashPrimaryBtn,
  DashChipBtn,
  MeasureCellD,
  LedgerRow,
  PassportPill,
  EmptyZone,
  PageHeading,
  type DashTab,
} from '@/components/redesign/DashboardShell';
import { useIsMobile } from '@/components/redesign/useIsMobile';

const SavedItemsGrid = dynamic(() => import('@/components/SavedItemsGrid'), { ssr: false });
const DashboardTryOnModal = dynamic(() => import('@/components/DashboardTryOnModal'), { ssr: false });

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

const MEASUREMENT_FIELDS: { key: keyof Measurements; label: string; editable: boolean }[] = [
  { key: 'height', label: 'HEIGHT', editable: false },
  { key: 'chest', label: 'CHEST', editable: true },
  { key: 'waist', label: 'WAIST', editable: true },
  { key: 'hips', label: 'HIPS', editable: true },
  { key: 'inseam', label: 'INSEAM', editable: true },
  { key: 'shoulder_width', label: 'SHOULDER', editable: true },
  { key: 'arm_length', label: 'ARM', editable: true },
  { key: 'neck', label: 'NECK', editable: true },
  { key: 'thigh', label: 'THIGH', editable: true },
  { key: 'torso_length', label: 'TORSO', editable: true },
];

export default function DashboardPageWrapper() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-gray-300 border-t-gray-700 rounded-full animate-spin" />
      </div>
    }>
      <DashboardPage />
    </Suspense>
  );
}

function DashboardPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { theme, toggleTheme } = useTheme();
  const dark = theme === 'dark';
  const mobile = useIsMobile();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const sceneRef = useRef<{ scene: unknown; setBackground: (hex: number) => void } | null>(null);
  const avatarInitRef = useRef<(() => void) | null>(null);

  const [user, setUser] = useState<User | null>(null);
  const [passport, setPassport] = useState<FitPassport | null>(null);

  const tabParam = searchParams.get('tab');
  const initialTab: DashTab = tabParam === 'closet' ? 'closet' : tabParam === 'wishlist' ? 'wish' : 'profile';
  const [activeTab, setActiveTab] = useState<DashTab>(initialTab);
  const [tryOnItem, setTryOnItem] = useState<SavedItem | null>(null);

  const switchTab = useCallback((tab: DashTab) => {
    setActiveTab(tab);
    const url = new URL(window.location.href);
    if (tab === 'profile') url.searchParams.delete('tab');
    else url.searchParams.set('tab', tab === 'wish' ? 'wishlist' : 'closet');
    window.history.replaceState({}, '', url.toString());
  }, []);

  const [isEditing, setIsEditing] = useState(false);
  const [measurements, setMeasurements] = useState<Measurements>({
    height: 0, chest: 0, waist: 0, hips: 0, inseam: 0,
    shoulder_width: 0, arm_length: 0, neck: 0, thigh: 0, torso_length: 0,
  });
  const [saving, setSaving] = useState(false);
  const [loadTimeout, setLoadTimeout] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [addresses, setAddresses] = useState<UserAddress[]>([]);
  const [addressesLoading, setAddressesLoading] = useState(false);
  const [addressError, setAddressError] = useState<string | null>(null);
  const [addressFormMode, setAddressFormMode] = useState<'idle' | 'add' | 'edit'>('idle');
  const [editingAddress, setEditingAddress] = useState<UserAddress | null>(null);
  const [addressSaving, setAddressSaving] = useState(false);
  const [addressForm, setAddressForm] = useState({
    label: '', name: '', line1: '', line2: '', city: '', state: '', postal_code: '', country: '', is_default: false,
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

      const fitPassport = await getFitPassport(currentUser.id);
      setPassport(fitPassport);

      if (fitPassport && !fitPassport.avatarUrl) {
        setTimeout(async () => {
          const refreshed = await getFitPassport(currentUser.id);
          if (refreshed?.avatarUrl) setPassport(refreshed);
        }, 3000);
      }

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

  useEffect(() => { loadData(); }, [loadData]);

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
    setAddressForm({ label: '', name: '', line1: '', line2: '', city: '', state: '', postal_code: '', country: '', is_default: false });
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
      label: addr.label, name: addr.name, line1: addr.line1,
      line2: addr.line2 || '', city: addr.city, state: addr.state || '',
      postal_code: addr.postal_code, country: addr.country, is_default: addr.is_default,
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

  // Three.js avatar viewer
  useEffect(() => {
    if (!canvasRef.current) return;

    let animationId: number;
    let rotation = 0;
    let renderer: WebGLRenderer | null = null;
    let disposed = false;

    const canvas = canvasRef.current;

    const initThreeJS = async () => {
      if (disposed || !canvasRef.current) return;
      if (renderer) {
        cancelAnimationFrame(animationId);
        renderer.dispose();
        renderer = null;
      }
      sceneRef.current = null;
      rotation = 0;

      const THREE = await import('three');
      const { GLTFLoader } = await import('three/examples/jsm/loaders/GLTFLoader.js');
      if (disposed || !canvasRef.current) return;

      const scene = new THREE.Scene();
      const isDark = typeof window !== 'undefined' && localStorage.getItem('tryon-theme') === 'dark';
      scene.background = new THREE.Color(isDark ? 0x0a0a0a : 0xffffff);
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

      scene.add(new THREE.AmbientLight(0xffffff, 1.4));
      const frontLight = new THREE.DirectionalLight(0xffffff, 1.5);
      frontLight.position.set(2, 3, 3); scene.add(frontLight);
      const backLight = new THREE.DirectionalLight(0xffffff, 1.0);
      backLight.position.set(-2, 2, -3); scene.add(backLight);
      const fillLight = new THREE.DirectionalLight(0xffffff, 0.8);
      fillLight.position.set(0, 2, 2); scene.add(fillLight);

      const loader = new GLTFLoader();
      const avatarUrl = passport?.avatarUrl;

      const renderLoop = (model?: { rotation: { y: number } }) => {
        const animate = () => {
          if (disposed) return;
          animationId = requestAnimationFrame(animate);
          if (model) {
            rotation += 0.008;
            model.rotation.y = rotation;
          }
          if (renderer && !renderer.getContext().isContextLost()) renderer.render(scene, camera);
        };
        animate();
      };

      if (!avatarUrl) {
        renderLoop();
        return;
      }

      const cacheBustUrl = avatarUrl.includes('?')
        ? `${avatarUrl}&t=${Date.now()}`
        : `${avatarUrl}?t=${Date.now()}`;

      loader.load(
        cacheBustUrl,
        (gltf) => {
          if (disposed) return;
          const model = gltf.scene;
          const box = new THREE.Box3().setFromObject(model);
          const center = box.getCenter(new THREE.Vector3());
          const size = box.getSize(new THREE.Vector3());
          const maxDim = Math.max(size.x, size.y, size.z);
          const scale = 1.8 / maxDim;
          model.scale.setScalar(scale);
          model.position.x = -center.x * scale;
          model.position.y = -center.y * scale + 0.9;
          model.position.z = -center.z * scale;
          scene.add(model);
          renderLoop(model);
        },
        undefined,
        (error) => {
          console.error('[Dashboard] Error loading avatar:', error);
          renderLoop();
        }
      );
    };

    avatarInitRef.current = initThreeJS;

    const handleContextLost = (e: Event) => {
      e.preventDefault();
      cancelAnimationFrame(animationId);
    };
    const handleContextRestored = () => initThreeJS();

    canvas.addEventListener('webglcontextlost', handleContextLost);
    canvas.addEventListener('webglcontextrestored', handleContextRestored);

    initThreeJS();

    return () => {
      disposed = true;
      avatarInitRef.current = null;
      sceneRef.current = null;
      canvas.removeEventListener('webglcontextlost', handleContextLost);
      canvas.removeEventListener('webglcontextrestored', handleContextRestored);
      cancelAnimationFrame(animationId);
      if (renderer) {
        renderer.dispose();
        renderer = null;
      }
    };
  }, [passport]);

  useEffect(() => {
    if (sceneRef.current) {
      sceneRef.current.setBackground(dark ? 0x0a0a0a : 0xffffff);
    }
  }, [dark]);

  const prevTryOnItem = useRef<SavedItem | null>(null);
  useEffect(() => {
    const wasTryingOn = prevTryOnItem.current !== null;
    prevTryOnItem.current = tryOnItem;
    if (wasTryingOn && tryOnItem === null && avatarInitRef.current) {
      const gl = canvasRef.current?.getContext('webgl2') || canvasRef.current?.getContext('webgl');
      if (!gl || gl.isContextLost()) avatarInitRef.current();
    }
  }, [tryOnItem]);

  const handleLogout = async () => { await logout(); router.push('/login'); };

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
    setPassport((p) => (p ? { ...p, preferred_fit: fit } : p));
    setSaving(true);
    try {
      const updated = await updateFitPassport(user.id, { preferredFit: fit });
      if (!updated) {
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
      <div className="min-h-screen bg-white flex flex-col items-center justify-center gap-6 px-4">
        {loadTimeout || loadError ? (
          <>
            <p className="text-gray-700 text-center max-w-sm">
              {loadTimeout ? 'Taking longer than expected. Check your connection and try again.' : loadError}
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => loadData()}
                className="px-4 py-2.5 text-sm font-medium rounded-xl bg-black text-white hover:bg-gray-800 transition"
              >Retry</button>
              <Link href="/login" className="px-4 py-2.5 text-sm font-medium rounded-xl border border-gray-200 text-gray-700 hover:bg-gray-50 transition">Go to login</Link>
            </div>
          </>
        ) : (
          <>
            <div className="w-8 h-8 border-2 border-gray-300 border-t-gray-700 rounded-full animate-spin" />
            <p className="text-gray-500 text-sm">Loading your dashboard…</p>
          </>
        )}
      </div>
    );
  }

  const FAINT = dark ? '#262626' : '#E1DDD2';
  const SURFACE = dark ? '#141414' : '#FFFFFF';
  const INK = dark ? '#F2F1EC' : '#0A0A0A';
  const DIM = dark ? '#8A8A8A' : '#7A7770';
  const BG = dark ? '#0A0A0A' : '#ffffff';

  // Inline-styled mini text input (used inside address form, theme-aware via dark prop)
  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '9px 12px',
    fontFamily: 'var(--display)', fontSize: 14,
    background: BG, border: `1px solid ${FAINT}`,
    color: INK, outline: 'none', letterSpacing: '-0.005em',
    boxSizing: 'border-box',
  };
  const labelStyle: React.CSSProperties = {
    fontFamily: 'var(--display)', fontSize: 11, letterSpacing: '0.04em',
    color: DIM, textTransform: 'uppercase', marginBottom: 6, display: 'block',
  };

  return (
    <DashThemeShell dark={dark}>
      <FloatingNav
        active={activeTab}
        onChange={switchTab}
        email={user.email || ''}
        dark={dark}
        onToggleDark={toggleTheme}
        onSignOut={handleLogout}
        mobile={mobile}
      />

      {/* Profile tab — always mounted, hidden via display so the Three.js canvas survives switches */}
      <div style={{
        display: activeTab === 'profile' ? 'block' : 'none',
        padding: mobile ? '24px 18px 32px' : '32px 32px 40px',
      }}>
        <div style={{ display: 'grid', gap: mobile ? 18 : 24 }}>
          <PageHeading
            title={`Welcome back, ${(user.name || 'shopper').split(' ')[0]}.`}
            sub="Your Fit Passport is ready. Try on clothes from any brand."
            mobile={mobile}
          />

          <div style={{
            display: 'grid',
            gridTemplateColumns: mobile ? '1fr' : '1fr 1.2fr',
            gap: mobile ? 18 : 24,
          }}>
            <DashCard title="Your Avatar" padded={false}>
              <div style={{
                background: BG, position: 'relative',
                aspectRatio: '4/5', minHeight: 380,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
                {!passport?.avatarUrl && (
                  <span style={{
                    position: 'absolute', bottom: 14, left: 0, right: 0, textAlign: 'center',
                    fontFamily: 'var(--display)', fontSize: 12, color: DIM,
                  }}>Avatar still building. Refresh in a moment.</span>
                )}
              </div>
            </DashCard>

            <DashCard
              title="Your Measurements"
              right={
                isEditing ? (
                  <div style={{ display: 'flex', gap: 6 }}>
                    <DashPrimaryBtn size="sm" tone="ghost" onClick={() => setIsEditing(false)}>Cancel</DashPrimaryBtn>
                    <DashPrimaryBtn size="sm" onClick={handleSaveMeasurements} disabled={saving}>
                      {saving ? 'Saving…' : 'Save'}
                    </DashPrimaryBtn>
                  </div>
                ) : (
                  <DashPrimaryBtn size="sm" onClick={() => setIsEditing(true)}>Edit</DashPrimaryBtn>
                )
              }
            >
              <div style={{
                display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 14,
              }}>
                {MEASUREMENT_FIELDS.map((f) => (
                  <MeasureCellD
                    key={f.key}
                    label={f.label}
                    value={measurements[f.key]}
                    unit="cm"
                    editable={isEditing && f.editable}
                    onChange={(v) => setMeasurements({ ...measurements, [f.key]: v })}
                  />
                ))}
              </div>

              <div style={{
                marginTop: 'auto', paddingTop: 22, borderTop: `1px solid ${FAINT}`,
              }}>
                <div style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 10,
                }}>
                  <div style={{
                    fontFamily: 'var(--display)', fontSize: 12, color: DIM,
                    letterSpacing: '0.04em', textTransform: 'uppercase',
                  }}>Preferred fit</div>
                  <span style={{
                    fontFamily: 'var(--display)', fontSize: 12, color: DIM,
                    letterSpacing: '-0.005em',
                  }}>Affects size recommendations</span>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  {(['slim', 'regular', 'loose'] as const).map((fit) => (
                    <DashChipBtn
                      key={fit}
                      active={passport?.preferred_fit === fit}
                      onClick={() => handlePreferredFitChange(fit)}
                      disabled={saving}
                    >
                      {fit[0].toUpperCase() + fit.slice(1)}
                    </DashChipBtn>
                  ))}
                </div>
              </div>
            </DashCard>
          </div>

          <DashCard
            title="Shipping addresses"
            right={
              addressFormMode === 'idle' ? (
                <DashPrimaryBtn size="sm" onClick={startAddAddress}>+ Add address</DashPrimaryBtn>
              ) : null
            }
          >
            <p style={{
              fontFamily: 'var(--display)', fontSize: 13, color: DIM,
              margin: '0 0 14px', letterSpacing: '-0.005em',
            }}>Your saved addresses for checkout. Use one as default at TryOn brands.</p>

            {addressError && (
              <div style={{
                padding: '10px 12px', marginBottom: 12,
                background: 'rgba(176, 0, 32, 0.06)', border: '1px solid rgba(176, 0, 32, 0.2)',
                color: '#B00020', fontFamily: 'var(--display)', fontSize: 13,
              }}>{addressError}</div>
            )}

            {addressesLoading ? (
              <p style={{ fontFamily: 'var(--display)', fontSize: 13, color: DIM }}>Loading addresses…</p>
            ) : (addressFormMode === 'add' || addressFormMode === 'edit') ? (
              <div style={{ display: 'grid', gap: 12 }}>
                <div style={{ display: 'grid', gridTemplateColumns: mobile ? '1fr' : '1fr 1fr', gap: 12 }}>
                  <label>
                    <span style={labelStyle}>Label (e.g. Home, Work)</span>
                    <input style={inputStyle} value={addressForm.label} onChange={(e) => setAddressForm(f => ({ ...f, label: e.target.value }))} placeholder="Home" />
                  </label>
                  <label>
                    <span style={labelStyle}>Full name</span>
                    <input style={inputStyle} value={addressForm.name} onChange={(e) => setAddressForm(f => ({ ...f, name: e.target.value }))} placeholder="Jane Doe" />
                  </label>
                </div>
                <label>
                  <span style={labelStyle}>Address line 1</span>
                  <input style={inputStyle} value={addressForm.line1} onChange={(e) => setAddressForm(f => ({ ...f, line1: e.target.value }))} placeholder="Street and number" />
                </label>
                <label>
                  <span style={labelStyle}>Address line 2 (optional)</span>
                  <input style={inputStyle} value={addressForm.line2} onChange={(e) => setAddressForm(f => ({ ...f, line2: e.target.value }))} placeholder="Apt, suite, etc." />
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: mobile ? '1fr 1fr' : 'repeat(4, 1fr)', gap: 12 }}>
                  <label>
                    <span style={labelStyle}>City</span>
                    <input style={inputStyle} value={addressForm.city} onChange={(e) => setAddressForm(f => ({ ...f, city: e.target.value }))} />
                  </label>
                  <label>
                    <span style={labelStyle}>State</span>
                    <input style={inputStyle} value={addressForm.state} onChange={(e) => setAddressForm(f => ({ ...f, state: e.target.value }))} />
                  </label>
                  <label>
                    <span style={labelStyle}>Postal code</span>
                    <input style={inputStyle} value={addressForm.postal_code} onChange={(e) => setAddressForm(f => ({ ...f, postal_code: e.target.value }))} />
                  </label>
                  <label>
                    <span style={labelStyle}>Country</span>
                    <input style={inputStyle} value={addressForm.country} onChange={(e) => setAddressForm(f => ({ ...f, country: e.target.value }))} placeholder="e.g. NL" />
                  </label>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16, paddingTop: 4 }}>
                  <label style={{
                    display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer',
                    fontFamily: 'var(--display)', fontSize: 13, color: INK,
                  }}>
                    <input
                      type="checkbox"
                      checked={addressForm.is_default}
                      onChange={(e) => setAddressForm(f => ({ ...f, is_default: e.target.checked }))}
                    />
                    Use at checkout (default)
                  </label>
                  <div style={{ display: 'flex', gap: 6, marginLeft: 'auto' }}>
                    <DashPrimaryBtn tone="ghost" size="sm" onClick={resetAddressForm}>Cancel</DashPrimaryBtn>
                    <DashPrimaryBtn
                      size="sm"
                      onClick={saveAddress}
                      disabled={
                        addressSaving
                        || !addressForm.label.trim() || !addressForm.name.trim()
                        || !addressForm.line1.trim() || !addressForm.city.trim()
                        || !addressForm.postal_code.trim() || !addressForm.country.trim()
                      }
                    >
                      {addressSaving ? 'Saving…' : 'Save address'}
                    </DashPrimaryBtn>
                  </div>
                </div>
              </div>
            ) : addresses.length === 0 ? (
              <p style={{ fontFamily: 'var(--display)', fontSize: 13, color: DIM }}>
                No addresses yet. Add one to use at checkout.
              </p>
            ) : (
              <ul style={{ display: 'grid', gap: 12, listStyle: 'none', margin: 0, padding: 0 }}>
                {addresses.map((addr) => (
                  <li key={addr.id} style={{
                    display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 12,
                    padding: 16, border: `1px solid ${FAINT}`, background: BG,
                  }}>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        <span style={{
                          fontFamily: 'var(--display)', fontSize: 14, fontWeight: 700, color: INK,
                        }}>{addr.label}</span>
                        {addr.is_default && (
                          <span style={{
                            padding: '2px 8px', borderRadius: 999,
                            background: SURFACE, border: `1px solid ${FAINT}`,
                            fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.16em',
                            color: DIM, textTransform: 'uppercase',
                          }}>Default</span>
                        )}
                      </div>
                      <p style={{
                        fontFamily: 'var(--display)', fontSize: 13, color: DIM,
                        margin: '6px 0 0', lineHeight: 1.45,
                      }}>
                        {addr.name}<br />
                        {addr.line1}{addr.line2 ? `, ${addr.line2}` : ''}<br />
                        {[addr.city, addr.state, addr.postal_code].filter(Boolean).join(', ')} {addr.country}
                      </p>
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                      {!addr.is_default && (
                        <DashPrimaryBtn tone="ghost" size="sm" onClick={() => setDefaultAddress(addr)} disabled={addressSaving}>
                          Set default
                        </DashPrimaryBtn>
                      )}
                      <DashPrimaryBtn tone="ghost" size="sm" onClick={() => startEditAddress(addr)} disabled={addressSaving}>
                        Edit
                      </DashPrimaryBtn>
                      <button
                        type="button"
                        onClick={() => deleteAddress(addr)}
                        disabled={addressSaving}
                        style={{
                          background: 'transparent',
                          color: dark ? '#FF7C7C' : '#8E1F1F',
                          border: `1px solid ${FAINT}`,
                          padding: '7px 12px',
                          fontFamily: 'var(--display)', fontSize: 12,
                          fontWeight: 600, letterSpacing: '-0.005em',
                          cursor: addressSaving ? 'not-allowed' : 'pointer',
                          opacity: addressSaving ? 0.5 : 1,
                        }}
                      >Remove</button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </DashCard>

          <div style={{
            display: 'grid',
            gridTemplateColumns: mobile ? '1fr' : '1fr 1fr',
            gap: mobile ? 18 : 24,
          }}>
            <DashCard title="Account information">
              <div style={{ display: 'grid', gap: 0 }}>
                <LedgerRow label="Name" value={user.name || '—'} />
                <LedgerRow label="Email" value={user.email} />
                <LedgerRow
                  label="Member since"
                  value={user.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}
                />
                <LedgerRow label="Gender" value={passport?.gender ? passport.gender[0].toUpperCase() + passport.gender.slice(1) : 'Not set'} last />
              </div>
            </DashCard>

            <DashCard
              title="Fit Passport status"
              right={
                <span style={{
                  fontFamily: 'var(--display)', fontSize: 12,
                  color: dark ? '#7CFFA1' : '#1F6B3D', fontWeight: 600,
                }}>● Active</span>
              }
            >
              <div style={{ display: 'grid', gap: 0 }}>
                <PassportPill done={!!passport?.avatarUrl} label="Avatar created" sub="Ready to try on clothes." />
                <PassportPill done={!!passport?.height} label="Measurements saved" sub="Size recommendations enabled." />
                <PassportPill done label="Encrypted & revocable" sub="Your data is yours. Delete anytime." last />
              </div>
              <button
                onClick={handleClearData}
                style={{
                  marginTop: 18, width: '100%',
                  background: 'transparent',
                  color: dark ? '#FF7C7C' : '#8E1F1F',
                  border: `1px solid ${FAINT}`,
                  padding: '11px 14px',
                  fontFamily: 'var(--display)', fontSize: 13, fontWeight: 500,
                  letterSpacing: '-0.005em', cursor: 'pointer',
                }}
              >Delete account and data</button>
            </DashCard>
          </div>
        </div>
      </div>

      {/* Closet tab */}
      {activeTab === 'closet' && (
        <div style={{ padding: mobile ? '24px 18px 32px' : '32px 32px 40px' }}>
          <PageHeading
            title="My Closet"
            sub="Items you've purchased through TryOn. Try them on anytime."
            mobile={mobile}
          />
          <div style={{ marginTop: mobile ? 24 : 32 }}>
            <SavedItemsGrid
              listType="closet"
              dark={dark}
              onTryOn={(item) => setTryOnItem(item)}
            />
          </div>
        </div>
      )}

      {/* Wishlist tab */}
      {activeTab === 'wish' && (
        <div style={{ padding: mobile ? '24px 18px 32px' : '32px 32px 40px' }}>
          <PageHeading
            title="Wishlist"
            sub="Items you've hearted while trying on. Save from any store, try on from here."
            mobile={mobile}
          />
          <div style={{ marginTop: mobile ? 24 : 32 }}>
            <SavedItemsGrid
              listType="wishlist"
              dark={dark}
              onTryOn={(item) => setTryOnItem(item)}
            />
          </div>
        </div>
      )}

      {tryOnItem && (
        <DashboardTryOnModal
          item={tryOnItem}
          passport={passport}
          dark={dark}
          onClose={() => setTryOnItem(null)}
        />
      )}
    </DashThemeShell>
  );
}
