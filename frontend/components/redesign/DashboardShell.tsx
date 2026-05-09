'use client';

import React, { createContext, useContext, ReactNode } from 'react';
import { useRouter } from 'next/navigation';

const PAL = {
  light: {
    bg: '#ffffff', surface: '#FFFFFF',
    ink: '#0A0A0A', dim: '#7A7770', faint: '#E1DDD2',
    accent: '#0040FF', accentInk: '#ffffff',
    good: '#1F6B3D', bad: '#8E1F1F',
  },
  dark: {
    bg: '#0A0A0A', surface: '#141414',
    ink: '#F2F1EC', dim: '#8A8A8A', faint: '#262626',
    accent: '#0040FF', accentInk: '#ffffff',
    good: '#7CFFA1', bad: '#FF7C7C',
  },
};
type Palette = typeof PAL.light;
const ThemeCtx = createContext<Palette>(PAL.light);
export const useDashTheme = () => useContext(ThemeCtx);

export type DashTab = 'profile' | 'closet' | 'wish';

export function DashThemeShell({ dark, children }: { dark: boolean; children: ReactNode }) {
  const C = dark ? PAL.dark : PAL.light;
  return (
    <ThemeCtx.Provider value={C}>
      <div className="tryon-redesign-root" style={{
        background: C.bg, color: C.ink, minHeight: '100vh',
      }}>{children}</div>
    </ThemeCtx.Provider>
  );
}

export function FloatingNav({
  active, onChange, email, dark, onToggleDark, onSignOut, mobile = false,
}: {
  active: DashTab;
  onChange: (k: DashTab) => void;
  email: string;
  dark: boolean;
  onToggleDark: () => void;
  onSignOut: () => void;
  mobile?: boolean;
}) {
  const C = useDashTheme();
  const router = useRouter();
  const items: { key: DashTab; label: string }[] = [
    { key: 'profile', label: 'Profile' },
    { key: 'closet', label: mobile ? 'Closet' : 'My closet' },
    { key: 'wish', label: 'Wishlist' },
  ];

  return (
    <div style={{
      position: 'sticky', top: 0, zIndex: 70,
      background: C.bg,
      borderBottom: `1px solid ${C.faint}`,
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        gap: mobile ? 10 : 24,
        padding: mobile ? '10px 14px' : '14px 24px',
        maxWidth: 1440, margin: '0 auto',
      }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center',
          gap: mobile ? 14 : 24, minWidth: 0,
        }}>
          <button
            type="button"
            onClick={() => router.push('/')}
            style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', display: 'inline-flex' }}
            aria-label="TryOn home"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={dark ? '/redesign/wordmark-white.png' : '/redesign/wordmark.png'}
              alt="TryOn"
              style={{ height: mobile ? 16 : 18, width: 'auto', display: 'block' }}
            />
          </button>
          <div style={{ display: 'flex', gap: mobile ? 14 : 22, alignItems: 'center' }}>
            {items.map(it => {
              const on = active === it.key;
              return (
                <button
                  key={it.key}
                  onClick={() => onChange(it.key)}
                  style={{
                    border: 0, padding: 0, background: 'transparent', cursor: 'pointer',
                    fontFamily: 'var(--display)',
                    fontSize: mobile ? 13 : 14,
                    color: on ? C.ink : C.dim,
                    fontWeight: on ? 600 : 500,
                    whiteSpace: 'nowrap',
                  }}
                >{it.label}</button>
              );
            })}
          </div>
        </div>

        <div style={{
          display: 'inline-flex', alignItems: 'center',
          gap: mobile ? 8 : 14,
        }}>
          {!mobile && (
            <span style={{
              fontFamily: 'var(--display)', fontSize: 13,
              color: C.dim, whiteSpace: 'nowrap',
            }}>{email}</span>
          )}
          <button
            onClick={onToggleDark}
            title="Toggle theme"
            aria-label="Toggle theme"
            style={{
              width: 30, height: 30,
              border: `1px solid ${C.faint}`, background: 'transparent',
              color: C.ink, cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              borderRadius: 8,
            }}
          >
            {dark ? (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={C.ink} strokeWidth="1.6">
                <circle cx="12" cy="12" r="4" />
                <path strokeLinecap="round" d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
              </svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M11 8.5A4.5 4.5 0 016.5 4 4 4 0 109 11.5 4.5 4.5 0 0111 8.5z" stroke={C.ink} strokeWidth="1.4"/>
              </svg>
            )}
          </button>
          <button
            onClick={onSignOut}
            style={{
              background: C.ink, color: C.bg, border: 'none',
              padding: mobile ? '9px 14px' : '10px 18px',
              fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600,
              letterSpacing: '-0.005em',
              cursor: 'pointer', whiteSpace: 'nowrap',
              borderRadius: 9999,
            }}
          >Sign out</button>
        </div>
      </div>
    </div>
  );
}

export function DashCard({
  title, right, children, padded = true,
}: {
  title?: string;
  right?: ReactNode;
  children: ReactNode;
  padded?: boolean;
}) {
  const C = useDashTheme();
  return (
    <div style={{
      border: `1px solid ${C.faint}`,
      background: C.surface,
      borderRadius: 16,
      overflow: 'hidden',
      display: 'flex', flexDirection: 'column',
      height: '100%',
    }}>
      {(title || right) && (
        <div style={{
          padding: '14px 18px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12,
          borderBottom: `1px solid ${C.faint}`,
          flex: '0 0 auto',
        }}>
          {title && (
            <span style={{
              fontFamily: 'var(--display)', fontSize: 14, fontWeight: 700,
              color: C.ink, letterSpacing: '-0.01em',
            }}>{title}</span>
          )}
          {right}
        </div>
      )}
      <div style={{
        padding: padded ? '18px' : 0,
        flex: '1 1 auto', minHeight: 0,
        display: 'flex', flexDirection: 'column',
      }}>{children}</div>
    </div>
  );
}

export function DashPrimaryBtn({
  children, onClick, size = 'md', tone = 'solid', disabled, type = 'button',
}: {
  children: ReactNode;
  onClick?: () => void;
  size?: 'sm' | 'md';
  tone?: 'solid' | 'ghost';
  disabled?: boolean;
  type?: 'button' | 'submit';
}) {
  const C = useDashTheme();
  const pad = size === 'sm' ? '7px 12px' : '10px 16px';
  const fontSize = size === 'sm' ? 12 : 13;

  if (tone === 'ghost') {
    return (
      <button
        type={type}
        onClick={onClick}
        disabled={disabled}
        style={{
          background: 'transparent', color: C.ink,
          border: `1px solid ${C.faint}`,
          padding: pad,
          fontFamily: 'var(--display)', fontSize,
          letterSpacing: '-0.005em', fontWeight: 600,
          borderRadius: 9999,
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.5 : 1,
          transition: 'border-color 180ms cubic-bezier(0.4, 0, 0.2, 1), color 180ms cubic-bezier(0.4, 0, 0.2, 1)',
        }}
      >{children}</button>
    );
  }
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      style={{
        background: C.accent, color: C.accentInk,
        border: 'none',
        padding: pad,
        fontFamily: 'var(--display)', fontSize,
        letterSpacing: '-0.005em', fontWeight: 600,
        borderRadius: 9999,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        transition: 'background 180ms cubic-bezier(0.4, 0, 0.2, 1), transform 180ms cubic-bezier(0.4, 0, 0.2, 1)',
      }}
    >{children}</button>
  );
}

export function DashChipBtn({
  active, children, onClick, disabled,
}: {
  active: boolean;
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
}) {
  const C = useDashTheme();
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: '7px 14px',
        background: active ? C.accent : 'transparent',
        color: active ? C.accentInk : C.dim,
        border: `1px solid ${active ? C.accent : C.faint}`,
        borderRadius: 9999,
        fontFamily: 'var(--display)', fontSize: 12, letterSpacing: '-0.005em',
        fontWeight: active ? 700 : 500,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        transition: 'all 180ms cubic-bezier(0.4, 0, 0.2, 1)',
      }}
    >{children}</button>
  );
}

export function MeasureCellD({
  label, value, unit, editable, onChange,
}: {
  label: string;
  value: number;
  unit: string;
  editable?: boolean;
  onChange?: (v: number) => void;
}) {
  const C = useDashTheme();
  return (
    <div style={{
      background: C.bg,
      padding: '12px 14px',
      display: 'flex', flexDirection: 'column', gap: 4,
      border: `1px solid ${C.faint}`,
      borderRadius: 12,
    }}>
      <span style={{
        fontFamily: 'var(--display)', fontSize: 10, letterSpacing: '0.06em',
        color: C.dim, textTransform: 'uppercase', fontWeight: 500,
      }}>{label}</span>
      {editable && onChange ? (
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
          <input
            type="number"
            value={value}
            onChange={(e) => onChange(parseInt(e.target.value, 10) || 0)}
            style={{
              fontFamily: 'var(--display)', fontWeight: 700,
              fontSize: 20, letterSpacing: '-0.025em',
              color: C.ink, lineHeight: 1,
              background: 'transparent', border: 'none', outline: 'none',
              width: 70,
            }}
          />
          <span style={{
            fontFamily: 'var(--display)', fontSize: 12, fontWeight: 400, color: C.dim,
            letterSpacing: '0.02em',
          }}>{unit}</span>
        </div>
      ) : (
        <span style={{
          fontFamily: 'var(--display)', fontWeight: 700,
          fontSize: 20, letterSpacing: '-0.025em',
          color: C.ink, lineHeight: 1,
        }}>
          {value}{' '}
          <span style={{
            fontFamily: 'var(--display)', fontSize: 12, fontWeight: 400, color: C.dim,
            letterSpacing: '0.02em',
          }}>{unit}</span>
        </span>
      )}
    </div>
  );
}

export function LedgerRow({
  label, value, last,
}: {
  label: string;
  value: ReactNode;
  last?: boolean;
}) {
  const C = useDashTheme();
  return (
    <div style={{
      borderBottom: last ? 'none' : `1px solid ${C.faint}`,
      padding: '9px 0',
      display: 'grid', gridTemplateColumns: '120px 1fr', gap: 12, alignItems: 'baseline',
    }}>
      <span style={{
        fontFamily: 'var(--display)', fontSize: 10, letterSpacing: '0.04em',
        color: C.dim, textTransform: 'uppercase',
      }}>{label}</span>
      <span style={{
        fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600,
        color: C.ink, letterSpacing: '-0.005em',
      }}>{value}</span>
    </div>
  );
}

export function PassportPill({
  done, label, sub, last,
}: {
  done: boolean;
  label: string;
  sub: string;
  last?: boolean;
}) {
  const C = useDashTheme();
  return (
    <div style={{
      borderBottom: last ? 'none' : `1px solid ${C.faint}`,
      padding: '8px 0',
      display: 'grid', gridTemplateColumns: '22px 1fr', gap: 10, alignItems: 'flex-start',
    }}>
      <span style={{
        width: 16, height: 16, borderRadius: '50%',
        border: `1.5px solid ${done ? C.good : C.faint}`,
        background: 'transparent',
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginTop: 2,
      }}>
        {done && (
          <svg width="10" height="10" viewBox="0 0 14 14" fill="none">
            <path d="M3 7.5L6 10.5L11.5 4" stroke={C.good} strokeWidth="1.6" strokeLinecap="round"/>
          </svg>
        )}
      </span>
      <div>
        <div style={{
          fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600,
          color: C.ink, letterSpacing: '-0.005em',
        }}>{label}</div>
        <div style={{
          fontFamily: 'var(--display)', fontSize: 11, color: C.dim,
          marginTop: 1, letterSpacing: '-0.005em',
        }}>{sub}</div>
      </div>
    </div>
  );
}

export function EmptyZone({
  icon, title, sub,
}: {
  icon: 'closet' | 'heart';
  title: string;
  sub: string;
}) {
  const C = useDashTheme();
  return (
    <div style={{
      padding: '80px 24px',
      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16,
    }}>
      <div style={{
        width: 56, height: 56, borderRadius: '50%',
        border: `1px solid ${C.faint}`, background: C.surface,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {icon === 'closet' ? (
          <svg width="22" height="22" viewBox="0 0 28 28" fill="none">
            <path d="M5 9h18v15H5z" stroke={C.dim} strokeWidth="1.5"/>
            <path d="M10 9V5h8v4" stroke={C.dim} strokeWidth="1.5"/>
          </svg>
        ) : (
          <svg width="22" height="22" viewBox="0 0 28 28" fill="none">
            <path d="M14 24l-8-7.6a4.6 4.6 0 016.6-6.4L14 11l1.4-1c2-1.5 4.9-1 6.6 1a4.6 4.6 0 010 5.4L14 24z"
              stroke={C.dim} strokeWidth="1.5" strokeLinejoin="round"/>
          </svg>
        )}
      </div>
      <div style={{ textAlign: 'center' }}>
        <h2 style={{
          fontFamily: 'var(--display)', fontWeight: 700, fontSize: 20,
          letterSpacing: '-0.015em', margin: 0, color: C.ink,
        }}>{title}</h2>
        <p style={{
          fontFamily: 'var(--display)', fontSize: 13, color: C.dim,
          marginTop: 6, letterSpacing: '-0.005em',
        }}>{sub}</p>
      </div>
    </div>
  );
}

export function PageHeading({
  title, sub, mobile,
}: {
  title: string;
  sub: string;
  mobile?: boolean;
}) {
  const C = useDashTheme();
  return (
    <div>
      <h1 style={{
        fontFamily: 'var(--display)', fontWeight: 700,
        fontSize: mobile ? 22 : 26, letterSpacing: '-0.025em',
        lineHeight: 1.05, margin: 0, color: C.ink,
      }}>{title}</h1>
      <p style={{
        fontFamily: 'var(--display)', fontSize: 13,
        color: C.dim, margin: '4px 0 0', letterSpacing: '-0.005em',
      }}>{sub}</p>
    </div>
  );
}
