'use client';

import React, { createContext, useContext, useState, ReactNode, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useIsMobile } from './useIsMobile';

const PAL = {
  light: {
    bg: '#ffffff', surface: '#FFFFFF',
    ink: '#0A0A0A', dim: '#7A7770', faint: '#E1DDD2',
    accent: '#0A0A0A', accentInk: '#ffffff',
  },
  dark: {
    bg: '#0A0A0A', surface: '#141414',
    ink: '#F2F1EC', dim: '#8A8A8A', faint: '#262626',
    accent: '#F2F1EC', accentInk: '#0A0A0A',
  },
};

type Palette = typeof PAL.light;
const ThemeCtx = createContext<Palette>(PAL.light);
const useC = () => useContext(ThemeCtx);

/* ───────────── Atoms ───────────── */
function Field({ label, required, children, sub }: {
  label: string; required?: boolean; children: ReactNode; sub?: ReactNode;
}) {
  const C = useC();
  return (
    <label style={{ display: 'block' }}>
      <div style={{
        fontFamily: 'var(--display)', fontSize: 11, letterSpacing: '0.04em',
        color: C.dim, textTransform: 'uppercase', marginBottom: 6,
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
      }}>
        <span>{label}{required && <span style={{ color: C.dim, marginLeft: 3 }}>*</span>}</span>
        {sub && <span style={{ opacity: 0.8 }}>{sub}</span>}
      </div>
      {children}
    </label>
  );
}

const baseInput = (C: Palette, focus: boolean) => ({
  width: '100%', boxSizing: 'border-box' as const,
  background: C.surface,
  border: `1px solid ${focus ? C.ink : C.faint}`,
  padding: '9px 12px',
  fontFamily: 'var(--display)', fontSize: 14, fontWeight: 500,
  color: C.ink, outline: 'none', letterSpacing: '-0.005em',
});

function TextInput({
  value, onChange, placeholder, type = 'text', name, autoComplete,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
  name?: string;
  autoComplete?: string;
}) {
  const C = useC();
  const [focus, setFocus] = useState(false);
  return (
    <input
      type={type}
      name={name}
      autoComplete={autoComplete}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      onFocus={() => setFocus(true)}
      onBlur={() => setFocus(false)}
      style={baseInput(C, focus)}
    />
  );
}

function PhoneInput({
  code, onCodeChange, value, onChange,
}: {
  code: string;
  onCodeChange: (v: string) => void;
  value: string;
  onChange: (v: string) => void;
}) {
  const C = useC();
  const [focus, setFocus] = useState(false);
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '92px 1fr', gap: 6 }}>
      <select
        value={code}
        onChange={(e) => onCodeChange(e.target.value)}
        style={{
          background: C.surface, border: `1px solid ${C.faint}`,
          padding: '0 10px', appearance: 'none', WebkitAppearance: 'none',
          fontFamily: 'var(--display)', fontSize: 14, color: C.ink, fontWeight: 500,
          outline: 'none',
        }}
      >
        {['+31', '+1', '+44', '+49', '+33', '+34', '+39', '+32', '+41', '+45', '+46'].map(c => (
          <option key={c} value={c}>{c}</option>
        ))}
      </select>
      <input
        type="tel"
        autoComplete="tel"
        value={value}
        onChange={(e) => onChange(e.target.value.replace(/[^0-9]/g, ''))}
        placeholder="6 12345678"
        onFocus={() => setFocus(true)}
        onBlur={() => setFocus(false)}
        style={baseInput(C, focus)}
      />
    </div>
  );
}

function SelectInput({
  value, onChange, placeholder, options,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  options: string[];
}) {
  const C = useC();
  return (
    <div style={{ position: 'relative' }}>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          ...baseInput(C, false), appearance: 'none', WebkitAppearance: 'none',
          paddingRight: 28, color: value ? C.ink : C.dim,
        }}
      >
        <option value="" disabled>{placeholder}</option>
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
      <span style={{
        position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
        pointerEvents: 'none', color: C.dim,
      }}>▾</span>
    </div>
  );
}

const GoogleG = (
  <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden>
    <path fill="#4285F4" d="M21.6 12.227c0-.696-.062-1.365-.179-2.005H12v3.79h5.382a4.6 4.6 0 0 1-1.998 3.018v2.51h3.232c1.89-1.74 2.984-4.302 2.984-7.313z"/>
    <path fill="#34A853" d="M12 22c2.7 0 4.964-.895 6.616-2.46l-3.232-2.51c-.895.6-2.04.955-3.384.955-2.604 0-4.808-1.76-5.595-4.124H3.064v2.59A9.998 9.998 0 0 0 12 22z"/>
    <path fill="#FBBC05" d="M6.405 13.86A6.013 6.013 0 0 1 6.09 12c0-.645.111-1.272.315-1.86V7.55H3.064a9.996 9.996 0 0 0 0 8.9l3.341-2.59z"/>
    <path fill="#EA4335" d="M12 5.957c1.47 0 2.788.505 3.825 1.498l2.868-2.868C16.957 2.99 14.694 2 12 2 8.094 2 4.717 4.244 3.064 7.55l3.341 2.59C7.193 7.717 9.396 5.957 12 5.957z"/>
  </svg>
);
const AppleA = (
  <svg width="14" height="14" viewBox="-2 0 26 24" aria-hidden fill="currentColor">
    <path d="M16.365 1.43c0 1.14-.49 2.27-1.27 3.07-.84.86-2.21 1.52-3.31 1.43-.13-1.13.41-2.31 1.21-3.13.86-.89 2.34-1.55 3.37-1.37zM20.5 17.27c-.59 1.36-.87 1.96-1.62 3.16-1.05 1.66-2.53 3.74-4.36 3.76-1.62.02-2.04-1.06-4.25-1.05-2.21.01-2.66 1.07-4.29 1.05-1.83-.02-3.23-1.9-4.28-3.56C-.97 16.2-1.28 10.5 1.49 7.41c1.41-1.55 3.62-2.5 5.71-2.5 2.13 0 3.47 1.16 5.23 1.16 1.71 0 2.75-1.16 5.21-1.16 1.86 0 3.83.99 5.24 2.71-4.61 2.51-3.86 9.05-2.38 9.65z"/>
  </svg>
);

function SSOButton({
  kind, children, onClick, disabled,
}: {
  kind: 'google' | 'apple';
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
}) {
  const C = useC();
  const isGoogle = kind === 'google';
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      style={{
        width: '100%',
        background: isGoogle ? C.surface : C.ink,
        color: isGoogle ? C.ink : '#F2F1EC',
        border: `1px solid ${isGoogle ? C.faint : C.ink}`,
        padding: '10px 12px',
        fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600,
        letterSpacing: '-0.005em',
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.6 : 1,
      }}
    >
      {isGoogle ? GoogleG : <span style={{ display: 'inline-flex', color: '#F2F1EC' }}>{AppleA}</span>}
      {children}
    </button>
  );
}

function Divider({ label = 'or' }: { label?: string }) {
  const C = useC();
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      fontFamily: 'var(--display)', fontSize: 12, color: C.dim,
      margin: '16px 0',
    }}>
      <div style={{ height: 1, background: C.faint, flex: 1 }} />
      <span>{label}</span>
      <div style={{ height: 1, background: C.faint, flex: 1 }} />
    </div>
  );
}

function LedgerLine({ k, v }: { k: string; v: string }) {
  const C = useC();
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '90px 1fr', gap: 10, alignItems: 'baseline',
    }}>
      <span style={{
        fontFamily: 'var(--display)', fontSize: 11, letterSpacing: '0.04em',
        color: C.dim, textTransform: 'uppercase',
      }}>{k}</span>
      <span style={{
        fontFamily: 'var(--display)', fontSize: 13, color: C.ink, letterSpacing: '-0.005em',
      }}>{v}</span>
    </div>
  );
}

function Wordmark({ darkBg }: { darkBg: boolean }) {
  const router = useRouter();
  return (
    <button
      type="button"
      onClick={() => router.push('/')}
      style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', display: 'inline-flex' }}
      aria-label="TRYON home"
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={darkBg ? '/redesign/wordmark-white.png' : '/redesign/wordmark.png'}
        alt="TRYON"
        style={{ height: 18, width: 'auto', display: 'block' }}
      />
    </button>
  );
}

/* ───────────── SignUp form data ───────────── */
export type SignUpData = {
  name: string;
  email: string;
  code: string;
  phone: string;
  dob: string;
  country: string;
  city: string;
  password: string;
  confirm: string;
};

export type AuthSignUpProps = {
  dark?: boolean;
  loading?: boolean;
  formError?: string | null;
  onSubmit: (data: SignUpData) => void | Promise<void>;
  onGoogle?: () => void | Promise<void>;
  onApple?: () => void | Promise<void>;
  onSignInClick?: () => void;
};

export function AuthSignUp({
  dark = false,
  loading = false,
  formError = null,
  onSubmit,
  onGoogle,
  onApple,
  onSignInClick,
}: AuthSignUpProps) {
  const C = dark ? PAL.dark : PAL.light;
  const mobile = useIsMobile();

  return (
    <ThemeCtx.Provider value={C}>
      <div className="tryon-redesign-root" style={{
        background: C.bg, color: C.ink,
        minHeight: '100vh',
        display: 'flex', flexDirection: 'column',
      }}>
        <SignUpInner
          mobile={mobile}
          loading={loading}
          formError={formError}
          onSubmit={onSubmit}
          onGoogle={onGoogle}
          onApple={onApple}
          onSignInClick={onSignInClick}
          darkBg={dark}
        />
      </div>
    </ThemeCtx.Provider>
  );
}

function SignUpInner({
  mobile, loading, formError, onSubmit, onGoogle, onApple, onSignInClick, darkBg,
}: {
  mobile: boolean;
  loading: boolean;
  formError: string | null;
  onSubmit: (data: SignUpData) => void | Promise<void>;
  onGoogle?: () => void | Promise<void>;
  onApple?: () => void | Promise<void>;
  onSignInClick?: () => void;
  darkBg: boolean;
}) {
  const C = useC();
  const [f, setF] = useState<SignUpData>({
    name: '', email: '', code: '+31', phone: '',
    dob: '', country: '', city: '', password: '', confirm: '',
  });
  const set = <K extends keyof SignUpData>(k: K) => (v: SignUpData[K]) =>
    setF(s => ({ ...s, [k]: v }));
  const [agreed, setAgreed] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit(f);
  };

  return (
    <>
      <div style={{
        borderBottom: `1px solid ${C.faint}`,
        padding: mobile ? '12px 18px' : '14px 28px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexShrink: 0,
      }}>
        <Wordmark darkBg={darkBg} />
        <span style={{ fontFamily: 'var(--display)', fontSize: 12, color: C.dim }}>
          Already have an account?{' '}
          <button
            type="button"
            onClick={onSignInClick}
            style={{ color: C.ink, fontWeight: 600, background: 'none', border: 'none', cursor: 'pointer', padding: 0, font: 'inherit' }}
          >Sign in</button>
        </span>
      </div>

      <form
        onSubmit={handleSubmit}
        style={{
          flex: 1, display: 'grid',
          gridTemplateColumns: mobile ? '1fr' : '1fr 1fr',
          minHeight: 0,
        }}
      >
        {!mobile && (
          <div style={{
            background: C.surface, borderRight: `1px solid ${C.faint}`,
            padding: '40px 40px',
            display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
          }}>
            <div>
              <div style={{
                fontFamily: 'var(--display)', fontSize: 12, letterSpacing: '0.04em',
                color: C.dim, textTransform: 'uppercase', marginBottom: 16,
              }}>Build your fit passport</div>
              <h1 style={{
                fontFamily: 'var(--display)', fontWeight: 700,
                fontSize: 44, letterSpacing: '-0.03em', lineHeight: 1.05,
                margin: 0, color: C.ink,
              }}>Open your passport.</h1>
              <p style={{
                fontFamily: 'var(--display)', fontSize: 14, color: C.dim,
                margin: '14px 0 0', maxWidth: 380, letterSpacing: '-0.005em', lineHeight: 1.5,
              }}>One body. Every brand. Build your fit passport once and try clothes on from any TryOn-enabled store.</p>
            </div>

            <div style={{
              borderTop: `1px solid ${C.faint}`, paddingTop: 18, marginTop: 24,
              display: 'grid', gap: 8,
            }}>
              <LedgerLine k="Name" v="On your passport." />
              <LedgerLine k="Email" v="One login. Every brand." />
              <LedgerLine k="Phone" v="Order updates only." />
              <LedgerLine k="Birthdate" v="Age-gated brands." />
              <LedgerLine k="Location" v="Currency · sizing · shipping." />
              <LedgerLine k="Password" v="Encrypted. We never see it." />
            </div>
          </div>
        )}

        <div style={{
          padding: mobile ? '20px 18px' : '32px 40px',
          overflowY: 'auto', minHeight: 0,
        }}>
          <div style={{ maxWidth: 460, margin: '0 auto' }}>
            {mobile && (
              <h1 style={{
                fontFamily: 'var(--display)', fontWeight: 700,
                fontSize: 28, letterSpacing: '-0.025em', lineHeight: 1.05,
                margin: '0 0 16px', color: C.ink,
              }}>Open your passport.</h1>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <SSOButton kind="google" onClick={onGoogle} disabled={loading}>Google</SSOButton>
              <SSOButton kind="apple" onClick={onApple} disabled={loading}>Apple</SSOButton>
            </div>

            <Divider />

            <div style={{ display: 'grid', gap: 12 }}>
              <Field label="Full name" required>
                <TextInput value={f.name} onChange={set('name')} placeholder="First and last name" autoComplete="name" />
              </Field>
              <Field label="Email" required>
                <TextInput value={f.email} onChange={set('email')} placeholder="you@email.com" type="email" autoComplete="email" />
              </Field>
              <Field label="Phone" required>
                <PhoneInput code={f.code} onCodeChange={set('code')} value={f.phone} onChange={set('phone')} />
              </Field>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <Field label="Date of birth" required>
                  <TextInput value={f.dob} onChange={set('dob')} placeholder="dd/mm/yyyy" />
                </Field>
                <Field label="City" required>
                  <TextInput value={f.city} onChange={set('city')} placeholder="Amsterdam" autoComplete="address-level2" />
                </Field>
              </div>
              <Field label="Country" required>
                <SelectInput
                  value={f.country}
                  onChange={set('country')}
                  placeholder="Select country"
                  options={['Netherlands', 'Belgium', 'Germany', 'France', 'United Kingdom', 'United States']}
                />
              </Field>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <Field label="Password" required>
                  <TextInput value={f.password} onChange={set('password')} placeholder="••••••••••" type="password" autoComplete="new-password" />
                </Field>
                <Field label="Confirm" required>
                  <TextInput value={f.confirm} onChange={set('confirm')} placeholder="••••••••••" type="password" autoComplete="new-password" />
                </Field>
              </div>

              <label style={{
                display: 'flex', gap: 10, alignItems: 'flex-start', padding: '4px 0', cursor: 'pointer',
              }}>
                <span
                  onClick={() => setAgreed(a => !a)}
                  style={{
                    width: 14, height: 14, border: `1px solid ${C.faint}`,
                    background: agreed ? C.ink : C.surface,
                    marginTop: 2, flexShrink: 0,
                    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  }}
                >
                  {agreed && (
                    <svg width="9" height="9" viewBox="0 0 10 10" fill="none">
                      <path d="M2 5.5L4 7.5L8 2.5" stroke={C.bg} strokeWidth="1.5" strokeLinecap="round"/>
                    </svg>
                  )}
                </span>
                <input
                  type="checkbox"
                  checked={agreed}
                  onChange={(e) => setAgreed(e.target.checked)}
                  style={{ position: 'absolute', opacity: 0, pointerEvents: 'none' }}
                />
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 12, lineHeight: 1.5,
                  color: C.dim, letterSpacing: '-0.005em',
                }}>
                  I agree to the <a href="#" style={{ color: C.ink, borderBottom: `1px solid ${C.ink}`, textDecoration: 'none' }}>Terms</a> and <a href="/privacy" style={{ color: C.ink, borderBottom: `1px solid ${C.ink}`, textDecoration: 'none' }}>Privacy Protocol</a>. My measurements are mine and revocable any time.
                </div>
              </label>

              {formError && (
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 13, color: '#B00020',
                  background: 'rgba(176, 0, 32, 0.06)', padding: '10px 12px',
                  border: '1px solid rgba(176, 0, 32, 0.2)',
                }}>{formError}</div>
              )}

              <button
                type="submit"
                disabled={loading || !agreed}
                style={{
                  width: '100%',
                  background: C.accent, color: C.accentInk,
                  border: 'none', padding: '12px 14px',
                  fontFamily: 'var(--display)', fontSize: 14, fontWeight: 700,
                  letterSpacing: '-0.005em',
                  cursor: (loading || !agreed) ? 'not-allowed' : 'pointer',
                  opacity: (loading || !agreed) ? 0.5 : 1,
                }}
              >
                {loading ? 'Creating account…' : 'Create account →'}
              </button>
            </div>
          </div>
        </div>
      </form>
    </>
  );
}

/* ───────────── SignIn ───────────── */
export type SignInData = {
  email: string;
  password: string;
  remember: boolean;
};

export type AuthSignInProps = {
  dark?: boolean;
  loading?: boolean;
  formError?: string | null;
  onSubmit: (data: SignInData) => void | Promise<void>;
  onGoogle?: () => void | Promise<void>;
  onApple?: () => void | Promise<void>;
  onSignUpClick?: () => void;
  /** Brand-only embedded Shopify surface: brand copy, hide shopper SSO. */
  shopifyMode?: boolean;
};

export function AuthSignIn({
  dark = false,
  loading = false,
  formError = null,
  onSubmit,
  onGoogle,
  onApple,
  onSignUpClick,
  shopifyMode = false,
}: AuthSignInProps) {
  const C = dark ? PAL.dark : PAL.light;
  const mobile = useIsMobile();
  return (
    <ThemeCtx.Provider value={C}>
      <div className="tryon-redesign-root" style={{
        background: C.bg, color: C.ink,
        minHeight: '100vh',
        display: 'flex', flexDirection: 'column',
      }}>
        <SignInInner
          mobile={mobile}
          loading={loading}
          formError={formError}
          onSubmit={onSubmit}
          onGoogle={onGoogle}
          onApple={onApple}
          onSignUpClick={onSignUpClick}
          darkBg={dark}
          shopifyMode={shopifyMode}
        />
      </div>
    </ThemeCtx.Provider>
  );
}

function SignInInner({
  mobile, loading, formError, onSubmit, onGoogle, onApple, onSignUpClick, darkBg, shopifyMode,
}: {
  mobile: boolean;
  loading: boolean;
  formError: string | null;
  onSubmit: (data: SignInData) => void | Promise<void>;
  onGoogle?: () => void | Promise<void>;
  onApple?: () => void | Promise<void>;
  onSignUpClick?: () => void;
  darkBg: boolean;
  shopifyMode: boolean;
}) {
  const C = useC();
  const [f, setF] = useState<SignInData>({ email: '', password: '', remember: true });
  const set = <K extends keyof SignInData>(k: K) => (v: SignInData[K]) =>
    setF(s => ({ ...s, [k]: v }));

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit(f);
  };

  return (
    <>
      <div style={{
        borderBottom: `1px solid ${C.faint}`,
        padding: mobile ? '12px 18px' : '14px 28px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexShrink: 0,
      }}>
        <Wordmark darkBg={darkBg} />
        <span style={{ fontFamily: 'var(--display)', fontSize: 12, color: C.dim }}>
          New here?{' '}
          <button
            type="button"
            onClick={onSignUpClick}
            style={{ color: C.ink, fontWeight: 600, background: 'none', border: 'none', cursor: 'pointer', padding: 0, font: 'inherit' }}
          >{shopifyMode ? 'Sign up' : 'Open a passport'}</button>
        </span>
      </div>

      <form onSubmit={handleSubmit} style={{
        flex: 1,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: mobile ? '20px 18px' : '32px',
        minHeight: 0,
      }}>
        <div style={{
          width: '100%', maxWidth: 380,
          display: 'flex', flexDirection: 'column', gap: 16,
        }}>
          <div>
            <div style={{
              fontFamily: 'var(--display)', fontSize: 12, letterSpacing: '0.04em',
              color: C.dim, textTransform: 'uppercase', marginBottom: 8,
            }}>{shopifyMode ? 'Brand sign in' : 'Enter your passport'}</div>
            <h1 style={{
              fontFamily: 'var(--display)', fontWeight: 700,
              fontSize: mobile ? 28 : 36, letterSpacing: '-0.025em', lineHeight: 1.05,
              margin: 0, color: C.ink,
            }}>{shopifyMode ? 'Welcome back, brand.' : 'Welcome back, shopper.'}</h1>
          </div>

          {!shopifyMode && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <SSOButton kind="google" onClick={onGoogle} disabled={loading}>Google</SSOButton>
                <SSOButton kind="apple" onClick={onApple} disabled={loading}>Apple</SSOButton>
              </div>

              <Divider />
            </>
          )}

          <div style={{ display: 'grid', gap: 12 }}>
            <Field label="Email" required>
              <TextInput
                value={f.email}
                onChange={set('email')}
                placeholder="you@email.com"
                type="email"
                autoComplete="email"
              />
            </Field>
            <Field
              label="Password"
              required
              sub={
                <a href="#" style={{ color: C.ink, fontFamily: 'var(--display)', fontSize: 11, letterSpacing: '0.02em' }}>Forgot?</a>
              }
            >
              <TextInput
                value={f.password}
                onChange={set('password')}
                placeholder="••••••••••"
                type="password"
                autoComplete="current-password"
              />
            </Field>

            <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
              <span
                onClick={() => set('remember')(!f.remember)}
                style={{
                  width: 14, height: 14, border: `1px solid ${C.faint}`,
                  background: f.remember ? C.ink : C.surface,
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                }}
              >
                {f.remember && (
                  <svg width="9" height="9" viewBox="0 0 10 10" fill="none">
                    <path d="M2 5.5L4 7.5L8 2.5" stroke={C.bg} strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                )}
              </span>
              <span style={{
                fontFamily: 'var(--display)', fontSize: 13, color: C.ink,
                letterSpacing: '-0.005em',
              }}>Keep me signed in</span>
            </label>

            {formError && (
              <div style={{
                fontFamily: 'var(--display)', fontSize: 13, color: '#B00020',
                background: 'rgba(176, 0, 32, 0.06)', padding: '10px 12px',
                border: '1px solid rgba(176, 0, 32, 0.2)',
              }}>{formError}</div>
            )}

            <button
              type="submit"
              disabled={loading}
              style={{
                width: '100%',
                background: C.accent, color: C.accentInk,
                border: 'none', padding: '12px 14px',
                fontFamily: 'var(--display)', fontSize: 14, fontWeight: 700,
                letterSpacing: '-0.005em',
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.5 : 1,
              }}
            >
              {loading ? 'Signing in…' : 'Sign in →'}
            </button>
          </div>
        </div>
      </form>
    </>
  );
}

/* ───────────── Brand sign up (two-column, mirrors shopper) ───────────── */
export type BrandSignUpData = {
  brandName: string;
  contactName: string;
  email: string;
  code: string;
  phone: string;
  shopifyDomain: string;
  country: string;
  password: string;
  confirm: string;
};

export type AuthBrandSignUpProps = {
  dark?: boolean;
  loading?: boolean;
  formError?: string | null;
  onSubmit: (data: BrandSignUpData) => void | Promise<void>;
  onSignInClick?: () => void;
  shopifyMode?: boolean;
  prefilledShop?: string | null;
};

export function AuthBrandSignUp({
  dark = false,
  loading = false,
  formError = null,
  onSubmit,
  onSignInClick,
  shopifyMode = false,
  prefilledShop = null,
}: AuthBrandSignUpProps) {
  const C = dark ? PAL.dark : PAL.light;
  const mobile = useIsMobile();
  return (
    <ThemeCtx.Provider value={C}>
      <div className="tryon-redesign-root" style={{
        background: C.bg, color: C.ink,
        minHeight: '100vh',
        display: 'flex', flexDirection: 'column',
      }}>
        <BrandSignUpInner
          mobile={mobile}
          loading={loading}
          formError={formError}
          onSubmit={onSubmit}
          onSignInClick={onSignInClick}
          shopifyMode={shopifyMode}
          prefilledShop={prefilledShop}
          darkBg={dark}
        />
      </div>
    </ThemeCtx.Provider>
  );
}

function ShopifyDomainInput({
  value, onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const C = useC();
  const [focus, setFocus] = useState(false);
  return (
    <div style={{
      display: 'flex', alignItems: 'stretch',
      border: `1px solid ${focus ? C.ink : C.faint}`,
      background: C.surface,
    }}>
      <input
        type="text"
        autoComplete="off"
        value={value}
        placeholder="your-store"
        onFocus={() => setFocus(true)}
        onBlur={() => setFocus(false)}
        onChange={(e) => onChange(e.target.value.replace(/\s/g, '').toLowerCase())}
        style={{
          flex: 1, minWidth: 0,
          background: 'transparent', border: 'none', outline: 'none',
          padding: '9px 12px',
          fontFamily: 'var(--display)', fontSize: 14, fontWeight: 500,
          color: C.ink, letterSpacing: '-0.005em',
        }}
      />
      <span style={{
        padding: '9px 12px',
        background: C.bg,
        borderLeft: `1px solid ${C.faint}`,
        fontFamily: 'var(--display)', fontSize: 13, color: C.dim,
        display: 'inline-flex', alignItems: 'center', whiteSpace: 'nowrap',
      }}>.myshopify.com</span>
    </div>
  );
}

function BrandSignUpInner({
  mobile, loading, formError, onSubmit, onSignInClick, shopifyMode, prefilledShop, darkBg,
}: {
  mobile: boolean;
  loading: boolean;
  formError: string | null;
  onSubmit: (data: BrandSignUpData) => void | Promise<void>;
  onSignInClick?: () => void;
  shopifyMode: boolean;
  prefilledShop: string | null;
  darkBg: boolean;
}) {
  const C = useC();
  const [f, setF] = useState<BrandSignUpData>({
    brandName: '', contactName: '', email: '',
    code: '+31', phone: '',
    shopifyDomain: prefilledShop ? prefilledShop.replace(/\.myshopify\.com$/i, '') : '',
    country: '', password: '', confirm: '',
  });
  const set = <K extends keyof BrandSignUpData>(k: K) => (v: BrandSignUpData[K]) =>
    setF(s => ({ ...s, [k]: v }));
  const [agreed, setAgreed] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit(f);
  };

  const shopifyRequired = !shopifyMode;

  return (
    <>
      <div style={{
        borderBottom: `1px solid ${C.faint}`,
        padding: mobile ? '12px 18px' : '14px 28px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexShrink: 0,
      }}>
        <Wordmark darkBg={darkBg} />
        <span style={{ fontFamily: 'var(--display)', fontSize: 12, color: C.dim }}>
          Already have an account?{' '}
          <button
            type="button"
            onClick={onSignInClick}
            style={{ color: C.ink, fontWeight: 600, background: 'none', border: 'none', cursor: 'pointer', padding: 0, font: 'inherit' }}
          >Sign in</button>
        </span>
      </div>

      <form
        onSubmit={handleSubmit}
        style={{
          flex: 1, display: 'grid',
          gridTemplateColumns: mobile ? '1fr' : '1fr 1fr',
          minHeight: 0,
        }}
      >
        {!mobile && (
          <div style={{
            background: C.surface, borderRight: `1px solid ${C.faint}`,
            padding: '40px 40px',
            display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
          }}>
            <div>
              <div style={{
                fontFamily: 'var(--display)', fontSize: 12, letterSpacing: '0.04em',
                color: C.dim, textTransform: 'uppercase', marginBottom: 16,
              }}>For brands</div>
              <h1 style={{
                fontFamily: 'var(--display)', fontWeight: 700,
                fontSize: 44, letterSpacing: '-0.03em', lineHeight: 1.05,
                margin: 0, color: C.ink,
              }}>Set up your brand.</h1>
              <p style={{
                fontFamily: 'var(--display)', fontSize: 14, color: C.dim,
                margin: '14px 0 0', maxWidth: 380, letterSpacing: '-0.005em', lineHeight: 1.5,
              }}>Connect your Shopify store. Cut returns. Pay less than the cost of one return per day. Live in under a week.</p>
            </div>

            <div style={{
              borderTop: `1px solid ${C.faint}`, paddingTop: 18, marginTop: 24,
              display: 'grid', gap: 8,
            }}>
              <LedgerLine k="Brand" v="Your store identity." />
              <LedgerLine k="Contact" v="Who we email and Slack." />
              <LedgerLine k="Email" v="Login. Invoices. Receipts." />
              <LedgerLine k="Phone" v="Account alerts only." />
              <LedgerLine k="Shopify" v="Where the widget lives." />
              <LedgerLine k="Country" v="Currency · billing · VAT." />
              <LedgerLine k="Password" v="Encrypted. We never see it." />
            </div>
          </div>
        )}

        <div style={{
          padding: mobile ? '20px 18px' : '32px 40px',
          overflowY: 'auto', minHeight: 0,
        }}>
          <div style={{ maxWidth: 460, margin: '0 auto' }}>
            {mobile && (
              <h1 style={{
                fontFamily: 'var(--display)', fontWeight: 700,
                fontSize: 28, letterSpacing: '-0.025em', lineHeight: 1.05,
                margin: '0 0 16px', color: C.ink,
              }}>Set up your brand.</h1>
            )}

            <div style={{ display: 'grid', gap: 12 }}>
              <Field label="Brand or company name" required>
                <TextInput value={f.brandName} onChange={set('brandName')} placeholder="e.g. Moncler" autoComplete="organization" />
              </Field>
              <Field label="Contact name" required>
                <TextInput value={f.contactName} onChange={set('contactName')} placeholder="First and last name" autoComplete="name" />
              </Field>
              <Field label="Business email" required>
                <TextInput value={f.email} onChange={set('email')} placeholder="you@brand.com" type="email" autoComplete="email" />
              </Field>
              <Field label="Phone" required>
                <PhoneInput code={f.code} onCodeChange={set('code')} value={f.phone} onChange={set('phone')} />
              </Field>
              <Field label="Shopify store URL" required={shopifyRequired}>
                <ShopifyDomainInput value={f.shopifyDomain} onChange={set('shopifyDomain')} />
              </Field>
              <Field label="Country" required>
                <SelectInput
                  value={f.country}
                  onChange={set('country')}
                  placeholder="Select country"
                  options={['Netherlands', 'Belgium', 'Germany', 'France', 'United Kingdom', 'United States', 'Spain', 'Italy', 'Denmark', 'Sweden']}
                />
              </Field>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <Field label="Password" required>
                  <TextInput value={f.password} onChange={set('password')} placeholder="••••••••••" type="password" autoComplete="new-password" />
                </Field>
                <Field label="Confirm" required>
                  <TextInput value={f.confirm} onChange={set('confirm')} placeholder="••••••••••" type="password" autoComplete="new-password" />
                </Field>
              </div>

              <label style={{
                display: 'flex', gap: 10, alignItems: 'flex-start', padding: '4px 0', cursor: 'pointer',
              }}>
                <span
                  onClick={() => setAgreed(a => !a)}
                  style={{
                    width: 14, height: 14, border: `1px solid ${C.faint}`,
                    background: agreed ? C.ink : C.surface,
                    marginTop: 2, flexShrink: 0,
                    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  }}
                >
                  {agreed && (
                    <svg width="9" height="9" viewBox="0 0 10 10" fill="none">
                      <path d="M2 5.5L4 7.5L8 2.5" stroke={C.bg} strokeWidth="1.5" strokeLinecap="round"/>
                    </svg>
                  )}
                </span>
                <input
                  type="checkbox"
                  checked={agreed}
                  onChange={(e) => setAgreed(e.target.checked)}
                  style={{ position: 'absolute', opacity: 0, pointerEvents: 'none' }}
                />
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 12, lineHeight: 1.5,
                  color: C.dim, letterSpacing: '-0.005em',
                }}>
                  I agree to the <a href="#" style={{ color: C.ink, borderBottom: `1px solid ${C.ink}`, textDecoration: 'none' }}>Terms</a> and <a href="/privacy" style={{ color: C.ink, borderBottom: `1px solid ${C.ink}`, textDecoration: 'none' }}>Privacy Protocol</a>.
                </div>
              </label>

              {formError && (
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 13, color: '#B00020',
                  background: 'rgba(176, 0, 32, 0.06)', padding: '10px 12px',
                  border: '1px solid rgba(176, 0, 32, 0.2)',
                }}>{formError}</div>
              )}

              <button
                type="submit"
                disabled={loading || !agreed}
                style={{
                  width: '100%',
                  background: C.accent, color: C.accentInk,
                  border: 'none', padding: '12px 14px',
                  fontFamily: 'var(--display)', fontSize: 14, fontWeight: 700,
                  letterSpacing: '-0.005em',
                  cursor: (loading || !agreed) ? 'not-allowed' : 'pointer',
                  opacity: (loading || !agreed) ? 0.5 : 1,
                }}
              >
                {loading ? 'Creating account…' : 'Create account →'}
              </button>
            </div>
          </div>
        </div>
      </form>
    </>
  );
}
