'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from '@/contexts/ThemeContext';
import { SharedNav, NavLink, NavCta } from '@/components/redesign/SharedNav';

const PAL = {
  light: {
    bg: '#FAFAF8', surface: '#FFFFFF',
    ink: '#0A0A0A', mute: '#6E6E6E',
    line: 'rgba(10,10,10,0.10)',
    cardBg: '#0A0A0A', cardInk: '#FAFAF8', cardMute: '#9A9A9A',
    cardLine: 'rgba(255,255,255,0.14)',
  },
  dark: {
    bg: '#0A0A0A', surface: '#121212',
    ink: '#F2F1EC', mute: '#8A8A8A',
    line: 'rgba(255,255,255,0.10)',
    cardBg: '#F2F1EC', cardInk: '#0A0A0A', cardMute: '#6E6E6E',
    cardLine: 'rgba(0,0,0,0.10)',
  },
};
type Palette = typeof PAL.light;

const fitData: Record<string, string> = {
  xs: 'Too tight in the chest and shoulders. Size up for a comfortable fit.',
  s: 'Slightly fitted, may feel snug around the chest. Good for a slim fit.',
  m: 'Recommended fit. Fits very well, not too tight, not too baggy.',
  l: 'Relaxed fit with extra room in the body. Good for a loose fit.',
  xl: 'Oversized fit, very roomy throughout. Ideal for an oversized look.',
};

const mockPassport = {
  height: 175,
  measurements: { chest: 98, waist: 78, hips: 92 },
};

function ProductPanel({ C, onTryOn }: { C: Palette; onTryOn: () => void }) {
  return (
    <div style={{
      width: 440,
      padding: '56px 48px',
      display: 'flex', flexDirection: 'column', justifyContent: 'center',
      background: C.bg, color: C.ink,
      borderLeft: `1px solid ${C.line}`,
    }}>
      <div style={{
        fontFamily: 'var(--display)', fontSize: 12, color: C.mute, fontWeight: 600,
        letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 12,
      }}>Originals</div>
      <h1 style={{
        fontFamily: 'var(--display)', fontSize: 30, fontWeight: 700,
        letterSpacing: '-0.02em', lineHeight: 1.15, margin: '0 0 12px',
        color: C.ink,
      }}>Black T-shirt</h1>
      <div style={{
        fontFamily: 'var(--display)', fontSize: 22, fontWeight: 500,
        color: C.ink, marginBottom: 32,
      }}>€49.00</div>

      <button
        onClick={onTryOn}
        style={{
          background: C.ink, color: C.bg,
          padding: '15px 22px', border: 'none', borderRadius: 0,
          fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600, cursor: 'pointer',
          marginBottom: 10,
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 10,
        }}
      >Try on <span>→</span></button>

      <button
        style={{
          background: 'transparent', color: C.ink,
          padding: '14px 22px', border: `1px solid ${C.ink}`, borderRadius: 0,
          fontFamily: 'var(--display)', fontSize: 14, fontWeight: 500, cursor: 'pointer',
        }}
      >Add to cart</button>

      <div style={{
        marginTop: 28, padding: '14px 16px',
        border: `1px solid ${C.line}`, background: C.surface,
      }}>
        <div style={{
          fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600, color: C.ink, marginBottom: 4,
        }}>Demo mode</div>
        <div style={{
          fontFamily: 'var(--display)', fontSize: 12, color: C.mute,
        }}>Using sample fit passport data. No signup needed.</div>
      </div>
    </div>
  );
}

function Widget({ C, onClose }: { C: Palette; onClose: () => void }) {
  const [currentSize, setCurrentSize] = useState('m');
  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 80,
        background: 'rgba(10,10,10,0.5)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 16,
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div style={{
        position: 'relative',
        width: 880, maxWidth: '94vw',
        maxHeight: '92vh',
        background: C.surface,
        border: `1px solid ${C.line}`, borderRadius: 0,
        overflow: 'hidden',
        display: 'flex', flexDirection: 'column',
      }}>
        <div style={{
          padding: '14px 22px',
          borderBottom: `1px solid ${C.line}`,
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: C.bg,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={C.ink === '#0A0A0A' ? '/redesign/wordmark.png' : '/redesign/wordmark-white.png'}
              alt="TryOn"
              style={{ height: 14, width: 'auto', display: 'block' }}
            />
            <div style={{
              fontFamily: 'var(--display)', fontSize: 12, color: C.mute, fontWeight: 500,
            }}>Demo user · Originals Black T-shirt</div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            style={{
              width: 28, height: 28,
              background: 'transparent', border: `1px solid ${C.line}`,
              color: C.ink, cursor: 'pointer',
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 16, borderRadius: 0,
            }}
          >×</button>
        </div>

        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 280px',
          flex: 1, minHeight: 540,
        }}>
          <div style={{
            position: 'relative',
            background: '#ffffff',
            borderRight: `1px solid ${C.line}`,
          }}>
            <iframe
              src={`/embed-viewer.html#${currentSize}`}
              className="viewer-canvas"
              style={{ width: '100%', height: '100%', border: 0, display: 'block', minHeight: 540 }}
              title="TryOn 3D viewer"
            />
            <div style={{
              position: 'absolute', bottom: 12, left: '50%', transform: 'translateX(-50%)',
              fontFamily: 'var(--display)', fontSize: 12, color: C.mute,
              background: 'rgba(255,255,255,0.92)',
              padding: '6px 12px',
              border: `1px solid ${C.line}`,
            }}>Drag to rotate. Scroll to zoom.</div>
          </div>

          <div style={{
            padding: 22, background: C.surface, color: C.ink,
            display: 'flex', flexDirection: 'column', gap: 18,
          }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              {[
                { k: 'Height', v: `${mockPassport.height} cm` },
                { k: 'Chest', v: `${mockPassport.measurements.chest} cm` },
                { k: 'Hips', v: `${mockPassport.measurements.hips} cm` },
                { k: 'Waist', v: `${mockPassport.measurements.waist} cm` },
              ].map(row => (
                <div key={row.k}>
                  <div style={{
                    fontFamily: 'var(--display)', fontSize: 11, color: C.mute, fontWeight: 600, marginBottom: 4,
                  }}>{row.k}</div>
                  <div style={{
                    fontFamily: 'var(--display)', fontSize: 18, fontWeight: 600, color: C.ink,
                    letterSpacing: '-0.01em',
                  }}>{row.v}</div>
                </div>
              ))}
            </div>

            <div>
              <div style={{
                fontFamily: 'var(--display)', fontSize: 11, color: C.mute, fontWeight: 600, marginBottom: 8,
              }}>Size</div>
              <div style={{ display: 'flex', gap: 6 }}>
                {['xs', 's', 'm', 'l', 'xl'].map(size => {
                  const active = currentSize === size;
                  return (
                    <button
                      key={size}
                      onClick={() => setCurrentSize(size)}
                      style={{
                        flex: 1, height: 38, minWidth: 38,
                        background: active ? C.ink : 'transparent',
                        color: active ? C.bg : C.ink,
                        border: `1px solid ${active ? C.ink : C.line}`,
                        borderRadius: 0,
                        fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600,
                        cursor: 'pointer',
                      }}
                    >{size.toUpperCase()}</button>
                  );
                })}
              </div>
            </div>

            <div style={{
              borderTop: `1px solid ${C.line}`, paddingTop: 16,
              fontFamily: 'var(--display)', fontSize: 13, lineHeight: 1.55, color: C.ink,
            }}>
              <div style={{
                fontFamily: 'var(--display)', fontSize: 11, color: C.mute, fontWeight: 600, marginBottom: 6,
              }}>Fit</div>
              {fitData[currentSize]}
            </div>

            <div style={{
              marginTop: 'auto', paddingTop: 16,
              borderTop: `1px solid ${C.line}`,
            }}>
              <button
                onClick={onClose}
                style={{
                  width: '100%',
                  background: C.ink, color: C.bg, border: 'none',
                  padding: '12px 14px', borderRadius: 0,
                  fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600, cursor: 'pointer',
                }}
              >Add to cart</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function DemoPage() {
  const { theme } = useTheme();
  const dark = theme === 'dark';
  const C = dark ? PAL.dark : PAL.light;
  const router = useRouter();
  const [showWidget, setShowWidget] = useState(false);

  const links = [
    { label: 'Home', href: '/' },
    { label: 'Pricing', href: '/pricing' },
    { label: 'Demo', href: '/demo', active: true },
  ];

  return (
    <div className="tryon-redesign-root" style={{
      width: '100%', minHeight: '100vh',
      background: C.bg, color: C.ink,
    }}>
      <SharedNav
        dark={dark}
        links={links}
        rightSlot={
          <>
            <NavLink dark={dark} label="Sign in" href="/login" />
            <NavCta dark={dark} label="Start free →" onClick={() => router.push('/signup?type=brand')} />
          </>
        }
      />

      <div style={{ display: 'flex', minHeight: 'calc(100vh - 60px)' }}>
        <div style={{
          flex: 1,
          background: C.surface,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: 48,
          borderRight: `1px solid ${C.line}`,
        }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/redesign/originals-black-tshirt.png"
            alt="Originals Black T-shirt"
            style={{
              maxWidth: '78%', maxHeight: '78%',
              objectFit: 'contain', display: 'block',
            }}
          />
        </div>
        <ProductPanel C={C} onTryOn={() => setShowWidget(true)} />
      </div>

      {showWidget && <Widget C={C} onClose={() => setShowWidget(false)} />}
    </div>
  );
}
