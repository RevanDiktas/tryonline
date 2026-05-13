'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from '@/contexts/ThemeContext';
import { SharedNav, NavCta, AuthAwareSignInLink } from '@/components/redesign/SharedNav';
import { useIsMobile } from '@/components/redesign/useIsMobile';

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

function ProductPanel({ C, mobile, onTryOn }: { C: Palette; mobile: boolean; onTryOn: () => void }) {
  return (
    <div style={{
      width: mobile ? '100%' : 380,
      padding: mobile ? '24px 20px 32px' : '48px 40px',
      display: 'flex', flexDirection: 'column', justifyContent: 'center',
      background: C.bg, color: C.ink,
      borderLeft: mobile ? 'none' : `1px solid ${C.line}`,
      borderTop: mobile ? `1px solid ${C.line}` : 'none',
    }}>
      <div style={{
        fontFamily: 'var(--display)', fontSize: 11, color: C.mute, fontWeight: 600,
        letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 10,
      }}>Originals</div>
      <h1 style={{
        fontFamily: 'var(--display)', fontSize: mobile ? 24 : 26, fontWeight: 700,
        letterSpacing: '-0.02em', lineHeight: 1.15, margin: '0 0 10px',
        color: C.ink,
      }}>Black T-shirt</h1>
      <div style={{
        fontFamily: 'var(--display)', fontSize: mobile ? 18 : 20, fontWeight: 500,
        color: C.ink, marginBottom: mobile ? 20 : 28,
      }}>€49.00</div>

      <button
        onClick={onTryOn}
        style={{
          background: '#0040FF', color: '#FFFFFF',
          padding: mobile ? '14px 20px' : '15px 24px', border: 'none', borderRadius: 9999,
          fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600,
          letterSpacing: '-0.005em', cursor: 'pointer',
          marginBottom: 10,
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 10,
          transition: 'background 180ms cubic-bezier(0.4, 0, 0.2, 1)',
        }}
      >Try on <span>→</span></button>

      <button
        style={{
          background: 'transparent', color: C.ink,
          padding: mobile ? '13px 20px' : '14px 24px', border: `1px solid ${C.ink}`, borderRadius: 9999,
          fontFamily: 'var(--display)', fontSize: 14, fontWeight: 500,
          letterSpacing: '-0.005em', cursor: 'pointer',
        }}
      >Add to cart</button>

      <div style={{
        marginTop: 22, padding: '12px 14px',
        border: `1px solid ${C.line}`, background: C.surface,
      }}>
        <div style={{
          fontFamily: 'var(--display)', fontSize: 12.5, fontWeight: 600, color: C.ink, marginBottom: 4,
        }}>Demo mode</div>
        <div style={{
          fontFamily: 'var(--display)', fontSize: 11.5, color: C.mute, lineHeight: 1.5,
        }}>Using sample fit passport data. No signup needed.</div>
      </div>
    </div>
  );
}

function Widget({ C, mobile, onClose }: { C: Palette; mobile: boolean; onClose: () => void }) {
  const [currentSize, setCurrentSize] = useState('m');

  const measurementRows = [
    { k: 'Height', v: `${mockPassport.height}cm` },
    { k: 'Chest', v: `${mockPassport.measurements.chest}cm` },
    { k: 'Hips', v: `${mockPassport.measurements.hips}cm` },
    { k: 'Waist', v: `${mockPassport.measurements.waist}cm` },
  ];

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 80,
        background: 'rgba(10,10,10,0.5)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: mobile ? 0 : 16,
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div style={{
        position: 'relative',
        width: mobile ? '100vw' : 880, maxWidth: mobile ? '100vw' : '94vw',
        height: mobile ? '100dvh' : 'auto',
        maxHeight: mobile ? '100dvh' : '92vh',
        background: C.surface,
        border: mobile ? 'none' : `1px solid ${C.line}`,
        borderRadius: 16,
        overflow: 'hidden',
        display: 'flex', flexDirection: 'column',
      }}>
        <div style={{
          padding: mobile ? '12px 16px' : '14px 22px',
          borderBottom: `1px solid ${C.line}`,
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: C.bg, flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: mobile ? 10 : 14, minWidth: 0 }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={C.ink === '#0A0A0A' ? '/redesign/wordmark.png' : '/redesign/wordmark-white.png'}
              alt="TryOn"
              style={{ height: 14, width: 'auto', display: 'block', flexShrink: 0 }}
            />
            <div style={{
              fontFamily: 'var(--display)', fontSize: mobile ? 11 : 12, color: C.mute, fontWeight: 500,
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>Originals · Black T-shirt</div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            style={{
              width: 28, height: 28,
              background: 'transparent', border: `1px solid ${C.line}`,
              color: C.ink, cursor: 'pointer',
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 16, borderRadius: 16, flexShrink: 0,
            }}
          >×</button>
        </div>

        <div style={{
          display: mobile ? 'flex' : 'grid',
          flexDirection: mobile ? 'column' : undefined,
          gridTemplateColumns: mobile ? undefined : '1fr 280px',
          flex: 1, minHeight: 0,
        }}>
          <div style={{
            position: 'relative',
            background: '#ffffff',
            borderRight: mobile ? 'none' : `1px solid ${C.line}`,
            borderBottom: mobile ? `1px solid ${C.line}` : 'none',
            height: mobile ? '50dvh' : 'auto',
            minHeight: mobile ? '50dvh' : 540,
            flexShrink: 0,
          }}>
            <iframe
              src={`/embed-viewer.html#${currentSize}`}
              className="viewer-canvas"
              style={{ width: '100%', height: '100%', border: 0, display: 'block' }}
              title="TryOn 3D viewer"
            />
            <div style={{
              position: 'absolute', bottom: 10, left: '50%', transform: 'translateX(-50%)',
              fontFamily: 'var(--display)', fontSize: 11, color: C.mute,
              background: 'rgba(255,255,255,0.92)',
              padding: '5px 10px',
              border: `1px solid ${C.line}`,
              whiteSpace: 'nowrap',
            }}>{mobile ? 'Drag to rotate' : 'Drag to rotate. Scroll to zoom.'}</div>
          </div>

          <div style={{
            padding: mobile ? '14px 16px 16px' : 22,
            background: C.surface, color: C.ink,
            display: 'flex', flexDirection: 'column', gap: mobile ? 12 : 18,
            flex: 1, minHeight: 0, overflowY: 'auto',
          }}>
            <div style={{
              display: mobile ? 'flex' : 'grid',
              flexDirection: mobile ? 'row' : undefined,
              gridTemplateColumns: mobile ? undefined : '1fr 1fr',
              gap: mobile ? 6 : 14,
            }}>
              {measurementRows.map(row => (
                <div key={row.k} style={{
                  flex: mobile ? '1 1 0' : undefined, minWidth: 0,
                }}>
                  <div style={{
                    fontFamily: 'var(--display)', fontSize: mobile ? 9 : 11,
                    color: C.mute, fontWeight: 600, marginBottom: 2,
                    letterSpacing: mobile ? '0.02em' : 0,
                  }}>{row.k}</div>
                  <div style={{
                    fontFamily: 'var(--display)', fontSize: mobile ? 14 : 18,
                    fontWeight: 600, color: C.ink, letterSpacing: '-0.01em',
                  }}>{row.v}</div>
                </div>
              ))}
            </div>

            <div>
              <div style={{
                fontFamily: 'var(--display)', fontSize: mobile ? 10 : 11,
                color: C.mute, fontWeight: 600, marginBottom: 6,
              }}>Size</div>
              <div style={{ display: 'flex', gap: mobile ? 5 : 6 }}>
                {['s', 'm', 'l'].map(size => {
                  const active = currentSize === size;
                  return (
                    <button
                      key={size}
                      onClick={() => setCurrentSize(size)}
                      style={{
                        flex: 1, height: mobile ? 34 : 38, minWidth: 0,
                        background: active ? C.ink : 'transparent',
                        color: active ? C.bg : C.ink,
                        border: `1px solid ${active ? C.ink : C.line}`,
                        borderRadius: 16,
                        fontFamily: 'var(--display)', fontSize: mobile ? 12 : 13, fontWeight: 600,
                        cursor: 'pointer',
                      }}
                    >{size.toUpperCase()}</button>
                  );
                })}
              </div>
            </div>

            <div style={{
              borderTop: `1px solid ${C.line}`, paddingTop: 12,
              fontFamily: 'var(--display)', fontSize: mobile ? 12 : 13,
              lineHeight: 1.55, color: C.ink,
            }}>
              <div style={{
                fontFamily: 'var(--display)', fontSize: mobile ? 10 : 11,
                color: C.mute, fontWeight: 600, marginBottom: 4,
              }}>Fit</div>
              {fitData[currentSize]}
            </div>

            <div style={{
              marginTop: 'auto', paddingTop: 12,
              borderTop: `1px solid ${C.line}`, flexShrink: 0,
            }}>
              <button
                onClick={onClose}
                style={{
                  width: '100%',
                  background: C.ink, color: C.bg, border: 'none',
                  padding: mobile ? '12px 14px' : '12px 14px', borderRadius: 16,
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
  const mobile = useIsMobile();
  const [showWidget, setShowWidget] = useState(false);

  const links = [
    { label: 'Home', href: '/' },
    { label: 'Pricing', href: '/pricing' },
    { label: 'Demo', href: '/demo', active: true },
    { label: 'Shoppers', href: '/signup' },
    { label: 'Deck', href: '/pitch-deck.html', external: true },
  ];

  return (
    <div className="tryon-redesign-root" style={{
      width: '100%', minHeight: '100vh',
      background: C.bg, color: C.ink,
    }}>
      <SharedNav
        dark={dark}
        links={links}
        rightSlot={mobile ? (
          <NavCta dark={dark} label="Start" onClick={() => router.push('/signup?type=brand')} />
        ) : (
          <>
            <AuthAwareSignInLink dark={dark} />
            <NavCta dark={dark} label="Start free" onClick={() => router.push('/signup?type=brand')} />
          </>
        )}
      />

      <div style={{
        display: 'flex',
        flexDirection: mobile ? 'column' : 'row',
        minHeight: 'calc(100vh - 60px)',
      }}>
        <div style={{
          flex: 1,
          background: C.surface,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: mobile ? '24px 20px' : 32,
          borderRight: mobile ? 'none' : `1px solid ${C.line}`,
          minHeight: mobile ? 320 : 'auto',
        }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/redesign/originals-black-tshirt.png"
            alt="Originals Black T-shirt"
            style={{
              maxWidth: mobile ? '60%' : 360,
              maxHeight: mobile ? 280 : 480,
              width: 'auto', height: 'auto',
              objectFit: 'contain', display: 'block',
            }}
          />
        </div>
        <ProductPanel C={C} mobile={mobile} onTryOn={() => setShowWidget(true)} />
      </div>

      {showWidget && <Widget C={C} mobile={mobile} onClose={() => setShowWidget(false)} />}
    </div>
  );
}
