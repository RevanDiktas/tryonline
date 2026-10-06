'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTheme } from '@/contexts/ThemeContext';
import { SharedNav, NavCta, AuthAwareSignInLink } from '@/components/redesign/SharedNav';
import { useIsMobile } from '@/components/redesign/useIsMobile';
import { siteLinks } from '@/components/redesign/siteLinks';
import { SiteFooter } from '@/components/redesign/SiteFooter';

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

// The second product has no 3D garment, so the store button reads "Find my size" and opens
// the real size card. The card is hosted the way the Shopify block hosts it
// (shopify_app/.../tryon-size.js): a full-screen transparent frame, READY -> PRODUCT + OPEN.
// No shop is passed, so nothing is tracked against a brand.
const SIZE_FINDER_URL = 'https://tryon.global/size-finder.html';
const SIZE_PRODUCT = {
  name: 'Black T-shirt',
  brand: 'TryOn demo',
  price: '€29.00',
  image: '/redesign/originals-black-tshirt.png',
  // The card loads from tryon.global and only shows https images.
  cardImage: 'https://tryon.global/redesign/originals-black-tshirt.png',
  sizes: ['XS', 'S', 'M', 'L', 'XL'],
  soldOut: ['L'],
};
const sizeFinderSrc = () => {
  const q = new URLSearchParams({
    product_name: SIZE_PRODUCT.name,
    brand_name: SIZE_PRODUCT.brand,
    product_type: 'T-shirt',
    sizes: SIZE_PRODUCT.sizes.join(','),
    sold_out: SIZE_PRODUCT.soldOut.join(','),
    product_image: SIZE_PRODUCT.cardImage,
  });
  return `${SIZE_FINDER_URL}?${q.toString()}`;
};

type SizeResult = { size: string; score?: number };

/** Mounts the size card on first use and keeps it mounted, so a second open is instant and
 *  remembers the answers. */
function useSizeFinder() {
  const frameRef = useRef<HTMLIFrameElement | null>(null);
  const readyRef = useRef(false);
  const wantOpenRef = useRef(false);
  const [mounted, setMounted] = useState(false);
  const [open, setOpen] = useState(false);
  const [ready, setReady] = useState(false);
  const [result, setResult] = useState<SizeResult | null>(null);
  const [added, setAdded] = useState<string | null>(null);

  const post = useCallback((type: string, payload?: unknown) => {
    const w = frameRef.current?.contentWindow;
    if (w) w.postMessage(payload ? { type, payload } : { type }, '*');
  }, []);
  const sendProduct = useCallback(() => {
    post('TRYON_SIZE_PRODUCT', {
      sizes: SIZE_PRODUCT.sizes.map((label) => ({ label, available: !SIZE_PRODUCT.soldOut.includes(label) })),
      image: SIZE_PRODUCT.cardImage,
      hasTryon: false,
    });
  }, [post]);

  const show = useCallback(() => {
    setOpen(true);
    if (!readyRef.current) { wantOpenRef.current = true; setMounted(true); return; }
    sendProduct();
    post('TRYON_SIZE_OPEN');
  }, [post, sendProduct]);

  const close = useCallback((fromCard: boolean) => {
    setOpen(false);
    if (!fromCard) post('TRYON_SIZE_HIDE');
  }, [post]);

  useEffect(() => {
    const onMessage = (e: MessageEvent) => {
      if (!frameRef.current || e.source !== frameRef.current.contentWindow || !e.data) return;
      const d = e.data as { type?: string; payload?: { size?: string; score?: number } };
      if (d.type === 'TRYON_SIZE_READY') {
        readyRef.current = true;
        setReady(true);
        sendProduct();
        if (wantOpenRef.current) { wantOpenRef.current = false; post('TRYON_SIZE_OPEN'); }
      }
      if (d.type === 'TRYON_SIZE_RESULT' && d.payload?.size) setResult({ size: d.payload.size, score: d.payload.score });
      if (d.type === 'TRYON_SIZE_CLOSE') setOpen(false);
      if (d.type === 'TRYON_SIZE_ADD_TO_CART' && d.payload?.size) { setAdded(d.payload.size); setOpen(false); }
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [post, sendProduct]);

  // The page behind the sheet must not scroll while it is open.
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, [open]);

  const frame = mounted ? (
    <>
      <iframe
        ref={frameRef}
        src={sizeFinderSrc()}
        title="Find your size"
        style={{
          display: open ? 'block' : 'none',
          position: 'fixed', inset: 0, width: '100%', height: '100%',
          zIndex: 90, border: 'none', background: 'transparent',
        }}
      />
      {open && !ready && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 89, background: 'rgba(10,10,10,0.45)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <button
            onClick={() => close(false)}
            aria-label="Close"
            style={{
              position: 'fixed', top: 12, right: 12, zIndex: 91, width: 36, height: 36,
              borderRadius: 18, border: 'none', background: '#FFFFFF', color: '#0A0A0A',
              fontSize: 18, cursor: 'pointer',
            }}
          >×</button>
          <div className="animate-spin" style={{
            width: 28, height: 28, borderRadius: 14,
            border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#FFFFFF',
          }} />
        </div>
      )}
    </>
  ) : null;

  return { show, frame, result, added };
}

function ProductCard({
  C, mobile, eyebrow, name, price, image, cta, onCta, note, status,
}: {
  C: Palette; mobile: boolean;
  eyebrow: string; name: string; price: string; image: string;
  cta: string; onCta: () => void; note: string; status?: React.ReactNode;
}) {
  return (
    <div style={{
      border: `1px solid ${C.line}`, borderRadius: 16, background: C.bg, overflow: 'hidden',
      display: 'flex', flexDirection: 'column', minWidth: 0,
    }}>
      <div style={{
        background: '#FFFFFF', borderBottom: `1px solid ${C.line}`,
        height: mobile ? 300 : 420,
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24, boxSizing: 'border-box',
      }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={image} alt={name} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', display: 'block', mixBlendMode: 'multiply' }} />
      </div>
      <div style={{ padding: mobile ? '20px 18px 22px' : '24px 26px 28px', display: 'flex', flexDirection: 'column', flex: 1 }}>
        <div style={{
          fontFamily: 'var(--mono)', fontSize: 11, color: C.mute, fontWeight: 500,
          letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 8,
        }}>{eyebrow}</div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, marginBottom: 18 }}>
          <h2 style={{
            fontFamily: 'var(--display)', fontSize: mobile ? 22 : 24, fontWeight: 700,
            letterSpacing: '-0.02em', lineHeight: 1.15, margin: 0, color: C.ink,
          }}>{name}</h2>
          <div style={{ fontFamily: 'var(--display)', fontSize: 17, fontWeight: 500, color: C.ink, whiteSpace: 'nowrap' }}>{price}</div>
        </div>

        <button
          onClick={onCta}
          style={{
            background: '#0040FF', color: '#FFFFFF',
            padding: '14px 22px', border: 'none', borderRadius: 9999,
            fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600,
            letterSpacing: '-0.005em', cursor: 'pointer', marginBottom: 10,
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 10,
          }}
        >{cta} <span>→</span></button>
        <button
          style={{
            background: 'transparent', color: C.ink,
            padding: '13px 22px', border: `1px solid ${C.ink}`, borderRadius: 9999,
            fontFamily: 'var(--display)', fontSize: 14, fontWeight: 500,
            letterSpacing: '-0.005em', cursor: 'pointer',
          }}
        >Add to cart</button>

        {status && (
          <div style={{
            marginTop: 12, fontFamily: 'var(--display)', fontSize: 13, color: C.ink, fontWeight: 500,
          }}>{status}</div>
        )}

        <div style={{
          marginTop: 'auto', paddingTop: 18,
          fontFamily: 'var(--display)', fontSize: 12.5, color: C.mute, lineHeight: 1.5,
        }}>{note}</div>
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
              alt="Tryon"
              style={{ height: 14, width: 'auto', display: 'block', flexShrink: 0 }}
            />
            <div style={{
              fontFamily: 'var(--display)', fontSize: mobile ? 11 : 12, color: C.mute, fontWeight: 500,
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>Originals · Zipup</div>
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
              title="Tryon 3D viewer"
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
  const mobile = useIsMobile();
  const [showWidget, setShowWidget] = useState(false);
  const sizeFinder = useSizeFinder();

  const sizeStatus = sizeFinder.added
    ? <>Added size {sizeFinder.added} to the cart. (Demo, nothing is ordered.)</>
    : sizeFinder.result
      ? <>Your size: {sizeFinder.result.size}{sizeFinder.result.score != null ? ` · ${sizeFinder.result.score}% match` : ''}</>
      : null;

  return (
    <div className="tryon-redesign-root" style={{
      width: '100%', minHeight: '100vh',
      background: C.bg, color: C.ink,
    }}>
      <SharedNav
        dark={dark}
        links={siteLinks('/demo')}
        rightSlot={mobile ? (
          <NavCta dark={dark} label="Start free" href="/start" />
        ) : (
          <>
            <AuthAwareSignInLink dark={dark} />
            <NavCta dark={dark} label="Start free →" href="/start" />
          </>
        )}
      />

      <section style={{
        padding: mobile ? '32px 18px 48px' : '64px 32px 88px',
        borderBottom: `1px solid ${C.line}`,
      }}>
        <div style={{ maxWidth: 1080, margin: '0 auto' }}>
          <div style={{
            fontFamily: 'var(--mono)', fontSize: mobile ? 11 : 12, color: C.mute,
            letterSpacing: '0.08em', textTransform: 'uppercase', fontWeight: 500, marginBottom: mobile ? 14 : 18,
          }}>Demo store</div>
          <h1 style={{
            fontFamily: 'var(--display)', fontWeight: 800,
            fontSize: mobile ? 34 : 'clamp(40px, 4.6vw, 60px)',
            letterSpacing: '-0.03em', lineHeight: 1.02, margin: '0 0 14px',
          }}>One button. Two products.</h1>
          <p style={{
            fontFamily: 'var(--display)', fontSize: mobile ? 15 : 17, lineHeight: 1.55,
            color: C.mute, maxWidth: 620, margin: `0 0 ${mobile ? 28 : 40}px`,
          }}>
            The same TryOn block on both product pages. This zip-up has a 3D garment, so the button reads Try On. The T-shirt does not, so it reads Find my size. No account needed for either.
          </p>

          <div style={{
            display: 'grid', gridTemplateColumns: mobile ? '1fr' : '1fr 1fr', gap: mobile ? 16 : 24,
          }}>
            <ProductCard
              C={C} mobile={mobile}
              eyebrow="Has a 3D garment"
              name="Zipup" price="€49.00" image="/redesign/zipup_demo.webp"
              cta="Try on" onCta={() => setShowWidget(true)}
              note="Demo mode: the avatar uses a sample fit passport."
            />
            <ProductCard
              C={C} mobile={mobile}
              eyebrow="No 3D garment"
              name={SIZE_PRODUCT.name} price={SIZE_PRODUCT.price} image={SIZE_PRODUCT.image}
              cta="Find my size" onCta={sizeFinder.show}
              status={sizeStatus}
              note={`The real size card: seven questions, every size scored. Size ${SIZE_PRODUCT.soldOut.join(', ')} is sold out here, so you can see the next best.`}
            />
          </div>
        </div>
      </section>

      <SiteFooter dark={dark} />

      {showWidget && <Widget C={C} mobile={mobile} onClose={() => setShowWidget(false)} />}
      {sizeFinder.frame}
    </div>
  );
}
