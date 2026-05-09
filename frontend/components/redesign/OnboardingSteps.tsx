'use client';

import React, { createContext, useContext, ReactNode } from 'react';
import { useIsMobile } from './useIsMobile';

const PAL = {
  light: {
    bg: '#ffffff', surface: '#FFFFFF', sub: '#EBE8E0',
    ink: '#0A0A0A', dim: '#7A7770', faint: '#E1DDD2',
    accent: '#0040FF', accentInk: '#ffffff',
    good: '#1F6B3D', bad: '#8E1F1F',
  },
  dark: {
    bg: '#0A0A0A', surface: '#141414', sub: '#181818',
    ink: '#F2F1EC', dim: '#8A8A8A', faint: '#262626',
    accent: '#0040FF', accentInk: '#ffffff',
    good: '#7CFFA1', bad: '#FF7C7C',
  },
};
type Palette = typeof PAL.light;
const ThemeCtx = createContext<Palette>(PAL.light);
const useC = () => useContext(ThemeCtx);

function Wordmark({ darkBg }: { darkBg: boolean }) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={darkBg ? '/redesign/wordmark-white.png' : '/redesign/wordmark.png'}
      alt="TRYON"
      style={{ height: 18, width: 'auto', display: 'block' }}
    />
  );
}

function TopBar({ mobile, current, total = 4, darkBg }: {
  mobile: boolean; current: number; total?: number; darkBg: boolean;
}) {
  const C = useC();
  return (
    <div style={{
      borderBottom: `1px solid ${C.faint}`,
      padding: mobile ? '10px 14px' : '14px 28px',
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      gap: 12, flexShrink: 0,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: mobile ? 8 : 14, minWidth: 0 }}>
        <Wordmark darkBg={darkBg} />
        {!mobile && (
          <span style={{
            fontFamily: 'var(--display)', fontSize: 11, letterSpacing: '0.04em',
            color: C.dim, textTransform: 'uppercase',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>Build your fit passport</span>
        )}
      </div>
      <span style={{
        fontFamily: 'var(--display)', fontSize: mobile ? 11 : 12, color: C.dim,
        whiteSpace: 'nowrap',
      }}>
        {mobile
          ? `${String(current).padStart(2, '0')} / ${String(total).padStart(2, '0')}`
          : `Step ${String(current).padStart(2, '0')} of ${String(total).padStart(2, '0')}`}
      </span>
    </div>
  );
}

function ProgressStrip({ current, mobile }: { current: number; mobile: boolean }) {
  const C = useC();
  const labels = ['Measure', 'Upload', 'Build', 'Complete'];
  return (
    <div style={{
      borderBottom: `1px solid ${C.faint}`,
      padding: mobile ? '8px 16px' : '10px 28px',
      display: 'flex', alignItems: 'center', gap: mobile ? 8 : 16,
      background: C.surface,
      overflow: 'hidden', flexShrink: 0,
    }}>
      {labels.map((l, i) => {
        const active = i + 1 === current;
        const done = i + 1 < current;
        return (
          <React.Fragment key={l}>
            <div style={{ display: 'flex', alignItems: 'center', gap: mobile ? 5 : 8, flexShrink: 0 }}>
              <span style={{
                width: 14, height: 14, borderRadius: '50%',
                border: `1px solid ${active || done ? C.ink : C.faint}`,
                background: done ? C.ink : 'transparent',
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                color: C.bg, fontSize: 8, fontWeight: 700,
              }}>{done ? '✓' : ''}</span>
              <span style={{
                fontFamily: 'var(--display)', fontSize: mobile ? 11 : 12,
                color: active ? C.ink : C.dim,
                fontWeight: active ? 600 : 500,
              }}>{l}</span>
            </div>
            {i < labels.length - 1 && (
              <div style={{ flex: 1, height: 1, background: C.faint, minWidth: mobile ? 6 : 12 }} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

function Field({ label, required, children, sub }: {
  label: string; required?: boolean; children: ReactNode; sub?: ReactNode;
}) {
  const C = useC();
  return (
    <label style={{ display: 'block', minWidth: 0 }}>
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

function NumInput({ value, onChange, placeholder, suffix }: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  suffix?: string;
}) {
  const C = useC();
  return (
    <div style={{
      display: 'flex', minWidth: 0,
      border: `1px solid ${C.faint}`,
      borderRadius: 12, overflow: 'hidden',
      background: C.surface,
    }}>
      <input
        value={value}
        onChange={e => onChange(e.target.value.replace(/[^0-9.]/g, ''))}
        placeholder={placeholder}
        inputMode="numeric"
        style={{
          flex: 1, minWidth: 0, width: '100%',
          background: 'transparent', border: 'none', outline: 'none',
          padding: '11px 14px',
          fontFamily: 'var(--display)', fontSize: 16, fontWeight: 600,
          color: C.ink, letterSpacing: '-0.005em',
        }}
      />
      {suffix && (
        <div style={{
          padding: '0 12px', display: 'flex', alignItems: 'center',
          fontFamily: 'var(--display)', fontSize: 11, letterSpacing: '0.04em',
          color: C.dim, borderLeft: `1px solid ${C.faint}`,
          background: C.sub, textTransform: 'uppercase', flexShrink: 0,
        }}>{suffix}</div>
      )}
    </div>
  );
}

function ChipPicker<T extends string>({ value, onChange, options }: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string }[];
}) {
  const C = useC();
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))`,
      border: `1px solid ${C.faint}`, background: C.surface,
    }}>
      {options.map((o, i) => {
        const active = value === o.value;
        return (
          <button
            key={o.value}
            type="button"
            onClick={() => onChange(o.value)}
            style={{
              padding: '10px 12px',
              borderRight: i < options.length - 1 ? `1px solid ${C.faint}` : 'none',
              background: active ? C.ink : 'transparent',
              color: active ? C.bg : C.ink,
              fontFamily: 'var(--display)', fontSize: 13,
              fontWeight: active ? 700 : 500,
              cursor: 'pointer', border: 'none', letterSpacing: '-0.005em',
            }}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

function Primary({ children, disabled, onClick, type = 'button' }: {
  children: ReactNode; disabled?: boolean; onClick?: () => void; type?: 'button' | 'submit';
}) {
  const C = useC();
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      style={{
        width: '100%',
        background: C.accent, color: C.accentInk,
        border: 'none', borderRadius: 9999, padding: '14px 18px',
        fontFamily: 'var(--display)', fontSize: 14, fontWeight: 700,
        letterSpacing: '-0.005em',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
      }}
    >{children}</button>
  );
}

function Ghost({ children, onClick }: { children: ReactNode; onClick?: () => void }) {
  const C = useC();
  return (
    <button type="button" onClick={onClick} style={{
      width: '100%',
      background: 'transparent', color: C.ink,
      border: `1px solid ${C.faint}`, borderRadius: 9999, padding: '14px 18px',
      fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600,
      letterSpacing: '-0.005em', cursor: 'pointer',
    }}>{children}</button>
  );
}

function ThemeShell({ dark, children }: { dark: boolean; children: ReactNode }) {
  const C = dark ? PAL.dark : PAL.light;
  return (
    <ThemeCtx.Provider value={C}>
      <div className="tryon-redesign-root" style={{
        background: C.bg, color: C.ink,
        minHeight: '100vh',
        display: 'flex', flexDirection: 'column',
      }}>{children}</div>
    </ThemeCtx.Provider>
  );
}

/* ─────────────── STEP 01 - Measure ─────────────── */
export type MeasureValues = {
  height: string;
  weight: string;
  body: 'male' | 'female' | 'other';
};

export function OnboardingMeasure({
  dark = false,
  values,
  onChange,
  onSubmit,
  loading = false,
  formError = null,
}: {
  dark?: boolean;
  values: MeasureValues;
  onChange: (next: MeasureValues) => void;
  onSubmit: () => void;
  loading?: boolean;
  formError?: string | null;
}) {
  const mobile = useIsMobile();
  return (
    <ThemeShell dark={dark}>
      <TopBar mobile={mobile} current={1} darkBg={dark} />
      <ProgressStrip current={1} mobile={mobile} />
      <MeasureBody
        mobile={mobile}
        values={values}
        onChange={onChange}
        onSubmit={onSubmit}
        loading={loading}
        formError={formError}
      />
    </ThemeShell>
  );
}

function MeasureBody({
  mobile, values, onChange, onSubmit, loading, formError,
}: {
  mobile: boolean;
  values: MeasureValues;
  onChange: (next: MeasureValues) => void;
  onSubmit: () => void;
  loading: boolean;
  formError: string | null;
}) {
  const C = useC();
  const set = <K extends keyof MeasureValues>(k: K, v: MeasureValues[K]) =>
    onChange({ ...values, [k]: v });

  return (
    <div style={{
      flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: mobile ? '16px 14px' : '32px',
      minHeight: 0, width: '100%', boxSizing: 'border-box', overflow: 'hidden',
    }}>
      <form
        onSubmit={(e) => { e.preventDefault(); onSubmit(); }}
        style={{
          width: '100%', maxWidth: 460,
          display: 'grid', gap: mobile ? 12 : 16,
          boxSizing: 'border-box',
        }}
      >
        <div>
          <h1 style={{
            fontFamily: 'var(--display)', fontWeight: 700,
            fontSize: mobile ? 28 : 36, letterSpacing: '-0.025em',
            lineHeight: 1.05, margin: 0, color: C.ink,
          }}>Tell us about you.</h1>
          <p style={{
            fontFamily: 'var(--display)', fontSize: 13, color: C.dim,
            margin: '8px 0 0', letterSpacing: '-0.005em', lineHeight: 1.5,
          }}>We need a few measurements to scale your avatar and recommend sizes.</p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: 12, minWidth: 0 }}>
          <Field label="Height" required>
            <NumInput value={values.height} onChange={(v) => set('height', v)} placeholder="175" suffix="cm" />
          </Field>
          <Field label="Weight">
            <NumInput value={values.weight} onChange={(v) => set('weight', v)} placeholder="70" suffix="kg" />
          </Field>
        </div>

        <Field label="Body type" required>
          <ChipPicker<MeasureValues['body']>
            value={values.body}
            onChange={(v) => set('body', v)}
            options={[
              { value: 'male', label: 'Male' },
              { value: 'female', label: 'Female' },
              { value: 'other', label: 'Other' },
            ]}
          />
        </Field>

        {formError && (
          <div style={{
            fontFamily: 'var(--display)', fontSize: 13, color: '#B00020',
            background: 'rgba(176, 0, 32, 0.06)', padding: '10px 12px',
            border: '1px solid rgba(176, 0, 32, 0.2)',
          }}>{formError}</div>
        )}

        <Primary type="submit" disabled={loading}>
          {loading ? 'Saving…' : 'Continue →'}
        </Primary>

        <p style={{
          fontFamily: 'var(--display)', fontSize: 12, color: C.dim,
          margin: 0, letterSpacing: '-0.005em', lineHeight: 1.5, textAlign: 'center',
        }}>
          Encrypted. Used only for your avatar and size recommendations. Revocable any time.
        </p>
      </form>
    </div>
  );
}

/* ─────────────── STEP 02 - Upload ─────────────── */
function CheckIcon({ color, size = 12 }: { color: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none">
      <path d="M3 7.5L6 10.5L11.5 4" stroke={color} strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  );
}
function CrossIcon({ color, size = 12 }: { color: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none">
      <path d="M3 3L11 11M11 3L3 11" stroke={color} strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  );
}
function CameraIcon({ color, size = 16 }: { color: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M4 8h3l1.5-2h7L17 8h3v11H4V8z" stroke={color} strokeWidth="1.6"/>
      <circle cx="12" cy="13.5" r="3.5" stroke={color} strokeWidth="1.6"/>
    </svg>
  );
}
function PlusIcon({ color, size = 14 }: { color: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" aria-hidden>
      <path d="M7 2v10M2 7h10" stroke={color} strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  );
}

function RowBtn({
  icon, label, primary, onClick, disabled,
}: {
  icon: ReactNode; label: string; primary?: boolean; onClick?: () => void; disabled?: boolean;
}) {
  const C = useC();
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      style={{
        width: '100%',
        background: primary ? C.accent : 'transparent',
        color: primary ? C.accentInk : C.ink,
        border: primary ? 'none' : `1px solid ${C.faint}`,
        padding: '12px 14px',
        fontFamily: 'var(--display)', fontSize: 14, fontWeight: primary ? 700 : 600,
        letterSpacing: '-0.005em',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
      }}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

function GuideRow({ kind, text }: { kind: 'good' | 'bad'; text: string }) {
  const C = useC();
  const isGood = kind === 'good';
  const accent = isGood ? C.good : C.bad;
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
      <span style={{
        width: 16, height: 16, borderRadius: '50%',
        border: `1px solid ${accent}`,
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0, marginTop: 2,
      }}>
        {isGood ? <CheckIcon color={accent} size={9} /> : <CrossIcon color={accent} size={9} />}
      </span>
      <span style={{
        fontFamily: 'var(--display)', fontSize: 13, color: C.ink,
        letterSpacing: '-0.005em', lineHeight: 1.45,
      }}>{text}</span>
    </div>
  );
}

export function OnboardingUpload({
  dark = false,
  photoPreview,
  onTakePhoto,
  onPickFile,
  onClearPhoto,
  onBack,
  onSubmit,
  loading = false,
  formError = null,
}: {
  dark?: boolean;
  photoPreview: string | null;
  onTakePhoto: () => void;
  onPickFile: (file: File) => void;
  onClearPhoto: () => void;
  onBack: () => void;
  onSubmit: () => void;
  loading?: boolean;
  formError?: string | null;
}) {
  const mobile = useIsMobile();
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  return (
    <ThemeShell dark={dark}>
      <TopBar mobile={mobile} current={2} darkBg={dark} />
      <ProgressStrip current={2} mobile={mobile} />
      <UploadBody
        mobile={mobile}
        photoPreview={photoPreview}
        onTakePhoto={onTakePhoto}
        onPickFileClick={() => fileInputRef.current?.click()}
        onClearPhoto={onClearPhoto}
        onBack={onBack}
        onSubmit={onSubmit}
        loading={loading}
        formError={formError}
      />
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onPickFile(file);
        }}
        style={{ display: 'none' }}
      />
    </ThemeShell>
  );
}

function UploadBody({
  mobile, photoPreview, onTakePhoto, onPickFileClick, onClearPhoto, onBack, onSubmit, loading, formError,
}: {
  mobile: boolean;
  photoPreview: string | null;
  onTakePhoto: () => void;
  onPickFileClick: () => void;
  onClearPhoto: () => void;
  onBack: () => void;
  onSubmit: () => void;
  loading: boolean;
  formError: string | null;
}) {
  const C = useC();
  return (
    <div style={{
      flex: 1, display: 'grid',
      gridTemplateColumns: mobile ? '1fr' : '1fr 1fr',
      minHeight: 0, overflow: 'hidden',
    }}>
      {!mobile && (
        <div style={{
          background: C.surface, borderRight: `1px solid ${C.faint}`,
          padding: '32px 40px',
          display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
          overflow: 'auto',
        }}>
          <div>
            <h1 style={{
              fontFamily: 'var(--display)', fontWeight: 700,
              fontSize: 36, letterSpacing: '-0.025em', lineHeight: 1.05,
              margin: 0, color: C.ink,
            }}>Upload a photo.</h1>
            <p style={{
              fontFamily: 'var(--display)', fontSize: 13, color: C.dim,
              margin: '8px 0 24px', letterSpacing: '-0.005em', lineHeight: 1.5,
            }}>Full-body, A-pose, neutral background. Better photos = better avatar.</p>

            <div style={{ display: 'grid', gap: 10, marginBottom: 20 }}>
              <div style={{
                fontFamily: 'var(--display)', fontSize: 11, letterSpacing: '0.04em',
                color: C.dim, textTransform: 'uppercase',
              }}>Do</div>
              <GuideRow kind="good" text="Stand straight, arms out (A-pose)." />
              <GuideRow kind="good" text="Plain wall, grey or white background." />
              <GuideRow kind="good" text="Tight clothing: shorts + tank top." />
              <GuideRow kind="good" text="Full body visible, head to toe." />
            </div>
            <div style={{ display: 'grid', gap: 10 }}>
              <div style={{
                fontFamily: 'var(--display)', fontSize: 11, letterSpacing: '0.04em',
                color: C.dim, textTransform: 'uppercase',
              }}>Avoid</div>
              <GuideRow kind="bad" text="Loose or baggy clothing." />
              <GuideRow kind="bad" text="Busy or patterned background." />
              <GuideRow kind="bad" text="Cropped or dim photos." />
            </div>
          </div>
        </div>
      )}

      <div style={{
        padding: mobile ? '14px 16px 16px' : '32px 40px',
        display: 'flex', flexDirection: 'column', gap: mobile ? 10 : 14,
        minHeight: 0, boxSizing: 'border-box',
      }}>
        {mobile && (
          <div>
            <h1 style={{
              fontFamily: 'var(--display)', fontWeight: 700,
              fontSize: 22, letterSpacing: '-0.025em', lineHeight: 1.05,
              margin: 0, color: C.ink,
            }}>Upload a photo.</h1>
            <p style={{
              fontFamily: 'var(--display)', fontSize: 12, color: C.dim,
              margin: '4px 0 0', letterSpacing: '-0.005em', lineHeight: 1.45,
            }}>Full-body, A-pose, neutral background.</p>
          </div>
        )}

        {/* Photo preview slot */}
        <div style={{
          aspectRatio: mobile ? '16/10' : '4/5',
          border: `1px solid ${C.faint}`,
          background: C.sub,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          position: 'relative', flexShrink: 0,
          overflow: 'hidden',
        }}>
          {photoPreview ? (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={photoPreview}
                alt="Photo preview"
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
              <button
                type="button"
                onClick={onClearPhoto}
                style={{
                  position: 'absolute', top: 10, right: 10,
                  width: 28, height: 28,
                  background: C.ink, color: C.bg,
                  border: 'none', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
                aria-label="Remove photo"
              >
                <CrossIcon color={C.bg} size={12} />
              </button>
            </>
          ) : (
            <span style={{
              fontFamily: 'var(--display)', fontSize: 11, color: C.dim,
              letterSpacing: '-0.005em',
              padding: '5px 9px', border: `1px solid ${C.faint}`, background: C.surface,
            }}>Photo preview</span>
          )}
        </div>

        {mobile && !photoPreview && (
          <div style={{ display: 'grid', gap: 8 }}>
            <div style={{
              fontFamily: 'var(--display)', fontSize: 10, letterSpacing: '0.05em',
              color: C.dim, textTransform: 'uppercase',
            }}>Do</div>
            <GuideRow kind="good" text="Stand straight, arms out (A-pose)." />
            <GuideRow kind="good" text="Plain wall, grey or white background." />
            <GuideRow kind="good" text="Tight clothing: shorts + tank top." />
            <div style={{
              fontFamily: 'var(--display)', fontSize: 10, letterSpacing: '0.05em',
              color: C.dim, textTransform: 'uppercase', marginTop: 6,
            }}>Avoid</div>
            <GuideRow kind="bad" text="Loose or baggy clothing." />
            <GuideRow kind="bad" text="Busy or patterned background." />
            <GuideRow kind="bad" text="Cropped or dim photos." />
          </div>
        )}

        {!photoPreview && (
          <div style={{ display: 'grid', gap: 6 }}>
            <RowBtn primary icon={<CameraIcon color={C.accentInk} size={15} />} label="Take photo" onClick={onTakePhoto} />
            <RowBtn icon={<PlusIcon color={C.ink} size={13} />} label="Add photo from gallery" onClick={onPickFileClick} />
          </div>
        )}

        {formError && (
          <div style={{
            fontFamily: 'var(--display)', fontSize: 13, color: '#B00020',
            background: 'rgba(176, 0, 32, 0.06)', padding: '10px 12px',
            border: '1px solid rgba(176, 0, 32, 0.2)',
          }}>{formError}</div>
        )}

        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 6, marginTop: mobile ? 0 : 'auto',
        }}>
          <Ghost onClick={onBack}>← Back</Ghost>
          <Primary onClick={onSubmit} disabled={!photoPreview || loading}>
            {loading ? 'Working…' : 'Create avatar →'}
          </Primary>
        </div>
      </div>
    </div>
  );
}

/* ─────────────── STEP 03 - Building ─────────────── */
const BUILD_STAGES = [
  { from:  0, to: 22, label: 'Uploading photo',     hint: 'Encrypted transfer.' },
  { from: 22, to: 48, label: 'Reading silhouette',  hint: 'Detecting body landmarks.' },
  { from: 48, to: 78, label: 'Rigging avatar',      hint: 'Building your 3D mesh.' },
  { from: 78, to: 96, label: 'Calibrating fit',     hint: 'Mapping size signal.' },
  { from: 96, to: 101,label: 'Passport ready',      hint: 'Almost there.' },
];

function ProgressRing({ pct, size = 220, stroke = 3 }: { pct: number; size?: number; stroke?: number }) {
  const C = useC();
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const off = circ * (1 - pct / 100);
  return (
    <svg width={size} height={size} style={{ display: 'block' }}>
      <circle cx={size/2} cy={size/2} r={r} stroke={C.faint} strokeWidth={stroke} fill="none" />
      <circle cx={size/2} cy={size/2} r={r}
        stroke={C.ink} strokeWidth={stroke} fill="none"
        strokeLinecap="round"
        strokeDasharray={circ} strokeDashoffset={off}
        transform={`rotate(-90 ${size/2} ${size/2})`}
        style={{ transition: 'stroke-dashoffset 0.5s linear' }}
      />
    </svg>
  );
}

export function OnboardingBuilding({
  dark = false,
  pct,
  message,
}: {
  dark?: boolean;
  pct: number;
  message?: string;
}) {
  const mobile = useIsMobile();
  return (
    <ThemeShell dark={dark}>
      <TopBar mobile={mobile} current={3} darkBg={dark} />
      <ProgressStrip current={3} mobile={mobile} />
      <BuildBody mobile={mobile} pct={pct} message={message} />
    </ThemeShell>
  );
}

function BuildBody({ mobile, pct, message }: { mobile: boolean; pct: number; message?: string }) {
  const C = useC();
  const stage = BUILD_STAGES.find(s => pct >= s.from && pct < s.to) || BUILD_STAGES[BUILD_STAGES.length - 1];
  const heading = message || stage.label;
  return (
    <div style={{
      flex: 1, display: 'grid',
      gridTemplateColumns: mobile ? '1fr' : '1fr 1fr',
      minHeight: 0,
    }}>
      <div style={{
        padding: mobile ? '14px 16px' : '32px 40px',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', gap: mobile ? 10 : 16,
        borderRight: mobile ? 'none' : `1px solid ${C.faint}`,
        borderBottom: mobile ? `1px solid ${C.faint}` : 'none',
        background: C.surface,
      }}>
        <div style={{ position: 'relative', display: 'inline-flex' }}>
          <ProgressRing pct={pct} size={mobile ? 120 : 220} />
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexDirection: 'column',
          }}>
            <div style={{
              fontFamily: 'var(--display)', fontWeight: 700,
              fontSize: mobile ? 32 : 60, letterSpacing: '-0.03em',
              lineHeight: 1, color: C.ink,
            }}>{Math.floor(pct)}<span style={{
              fontSize: mobile ? 13 : 22, fontWeight: 500,
              color: C.dim, marginLeft: 2,
            }}>%</span></div>
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <h2 style={{
            fontFamily: 'var(--display)', fontWeight: 700,
            fontSize: mobile ? 18 : 26, letterSpacing: '-0.02em',
            lineHeight: 1.1, margin: 0, color: C.ink,
          }}>{heading}</h2>
          <p style={{
            fontFamily: 'var(--display)', fontSize: mobile ? 12 : 13, color: C.dim,
            margin: '3px 0 0', letterSpacing: '-0.005em',
          }}>{stage.hint}</p>
        </div>
      </div>

      <div style={{
        padding: mobile ? '12px 16px 14px' : '32px 40px',
        display: 'flex', flexDirection: 'column', justifyContent: 'center',
        gap: mobile ? 8 : 12,
      }}>
        <div style={{ border: `1px solid ${C.faint}`, background: C.surface }}>
          {BUILD_STAGES.map((s, i) => {
            const done = pct >= s.to;
            const active = pct >= s.from && pct < s.to;
            return (
              <div key={s.label} style={{
                display: 'grid',
                gridTemplateColumns: '20px 1fr auto',
                padding: mobile ? '7px 12px' : '10px 14px',
                borderBottom: i < BUILD_STAGES.length - 1 ? `1px solid ${C.faint}` : 'none',
                alignItems: 'center', gap: 10,
              }}>
                <span style={{
                  width: 14, height: 14, borderRadius: '50%',
                  border: `1px solid ${done || active ? C.ink : C.faint}`,
                  background: done ? C.ink : 'transparent',
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  {done && <CheckIcon color={C.bg} size={8} />}
                </span>
                <span style={{
                  fontFamily: 'var(--display)', fontSize: mobile ? 12 : 13,
                  color: done || active ? C.ink : C.dim,
                  fontWeight: active ? 600 : 500,
                }}>{s.label}</span>
                <span style={{
                  fontFamily: 'var(--display)', fontSize: mobile ? 10 : 11,
                  letterSpacing: '0.04em', textTransform: 'uppercase',
                  color: done ? C.dim : (active ? C.ink : C.dim),
                }}>{done ? 'Done' : (active ? 'Now' : '·')}</span>
              </div>
            );
          })}
        </div>
        <p style={{
          fontFamily: 'var(--display)', fontSize: mobile ? 11 : 12, color: C.dim,
          margin: 0, letterSpacing: '-0.005em', textAlign: 'center',
        }}>This may take a moment. Don&apos;t close this tab.</p>
      </div>
    </div>
  );
}

/* ─────────────── STEP 04 - Complete ─────────────── */
export type CompleteMeasurement = { key: string; value: number; unit: string };

function MeasurementCell({ label, value, unit, mobile }: {
  label: string; value: number; unit: string; mobile: boolean;
}) {
  const C = useC();
  return (
    <div style={{
      border: `1px solid ${C.faint}`, background: C.surface,
      padding: mobile ? '8px 10px' : '12px 14px',
      display: 'flex', flexDirection: 'column', gap: 3,
    }}>
      <span style={{
        fontFamily: 'var(--display)', fontSize: mobile ? 10 : 11, letterSpacing: '0.04em',
        color: C.dim, textTransform: 'uppercase',
      }}>{label}</span>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
        <span style={{
          fontFamily: 'var(--display)', fontWeight: 700,
          fontSize: mobile ? 20 : 26, letterSpacing: '-0.025em',
          color: C.ink, lineHeight: 1,
        }}>{value}</span>
        <span style={{
          fontFamily: 'var(--display)', fontSize: mobile ? 11 : 12,
          color: C.dim,
        }}>{unit}</span>
      </div>
    </div>
  );
}

export function OnboardingComplete({
  dark = false,
  measurements,
  onOpenDashboard,
}: {
  dark?: boolean;
  measurements: CompleteMeasurement[];
  onOpenDashboard: () => void;
}) {
  const mobile = useIsMobile();
  return (
    <ThemeShell dark={dark}>
      <TopBar mobile={mobile} current={4} darkBg={dark} />
      <ProgressStrip current={4} mobile={mobile} />
      <CompleteBody mobile={mobile} measurements={measurements} onOpenDashboard={onOpenDashboard} />
    </ThemeShell>
  );
}

function CompleteBody({
  mobile, measurements, onOpenDashboard,
}: {
  mobile: boolean;
  measurements: CompleteMeasurement[];
  onOpenDashboard: () => void;
}) {
  const C = useC();
  return (
    <div style={{
      flex: 1, padding: mobile ? '12px 14px 14px' : '24px 40px',
      overflow: 'auto', minHeight: 0,
    }}>
      <div style={{ maxWidth: 1100, margin: '0 auto', display: 'grid', gap: mobile ? 10 : 16 }}>
        {/* Status banner */}
        <div style={{
          border: `1px solid ${C.ink}`,
          background: C.accent, color: C.accentInk,
          padding: mobile ? '10px 12px' : '16px 22px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: mobile ? 9 : 12 }}>
            <span style={{
              width: mobile ? 20 : 24, height: mobile ? 20 : 24, borderRadius: '50%',
              border: `1.5px solid ${C.accentInk}`,
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}>
              <CheckIcon color={C.accentInk} size={mobile ? 10 : 12} />
            </span>
            <div>
              <div style={{
                fontFamily: 'var(--display)', fontSize: mobile ? 10 : 11, letterSpacing: '0.04em',
                textTransform: 'uppercase', opacity: 0.7, marginBottom: 1,
              }}>Fit passport</div>
              <div style={{
                fontFamily: 'var(--display)', fontSize: mobile ? 13 : 18,
                fontWeight: 700, letterSpacing: '-0.015em',
              }}>Ready · {measurements.length} measurements locked</div>
            </div>
          </div>
          <span style={{
            fontFamily: 'var(--display)', fontSize: 11, letterSpacing: '0.04em',
            opacity: 0.7, textTransform: 'uppercase',
            display: mobile ? 'none' : 'block',
          }}>Encrypted · revocable</span>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: mobile ? 'repeat(2, 1fr)' : 'repeat(5, 1fr)',
          gap: mobile ? 6 : 8,
        }}>
          {measurements.map((m) => (
            <MeasurementCell key={m.key} label={m.key} value={m.value} unit={m.unit} mobile={mobile} />
          ))}
        </div>

        <div style={{
          display: 'grid', gridTemplateColumns: mobile ? '1fr' : '1.4fr 1fr',
          gap: mobile ? 8 : 10, alignItems: 'stretch',
        }}>
          {!mobile && (
            <div style={{
              border: `1px solid ${C.faint}`, background: C.surface,
              padding: '12px 14px',
              display: 'flex', alignItems: 'center', gap: 10,
            }}>
              <span style={{
                fontFamily: 'var(--display)', fontSize: 13, color: C.ink,
                letterSpacing: '-0.005em',
              }}>One passport. Use these measurements at every TryOn-enabled brand. Update them any time.</span>
            </div>
          )}
          <Primary onClick={onOpenDashboard}>Open dashboard →</Primary>
        </div>
      </div>
    </div>
  );
}
