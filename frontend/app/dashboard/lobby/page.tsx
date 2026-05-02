'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from '@/contexts/ThemeContext';
import { SharedNav, NavLink, NavCta, AuthAwareSignInLink } from '@/components/redesign/SharedNav';
import { useIsMobile } from '@/components/redesign/useIsMobile';

const PAL = {
  light: {
    bg: '#FAFAF8',
    surface: '#FFFFFF',
    stage: '#F0EFE9',
    ink: '#0A0A0A',
    mute: '#6E6E6E',
    line: 'rgba(10,10,10,0.10)',
    cardBg: '#0A0A0A', cardInk: '#FAFAF8',
  },
  dark: {
    bg: '#0A0A0A',
    surface: '#121212',
    stage: '#161614',
    ink: '#F2F1EC',
    mute: '#8A8A8A',
    line: 'rgba(255,255,255,0.10)',
    cardBg: '#F2F1EC', cardInk: '#0A0A0A',
  },
};
type Palette = typeof PAL.light;

const headingStyle = (px: string): React.CSSProperties => ({
  fontFamily: 'var(--display)', fontWeight: 700,
  fontSize: px, letterSpacing: '-0.022em', lineHeight: 1.04, margin: 0,
});

/* ─── Center stage: avatar on a platform ─── */
function AvatarStage({ C, mobile }: { C: Palette; mobile: boolean }) {
  return (
    <div style={{
      position: 'relative',
      flex: 1, minWidth: 0,
      display: 'flex', flexDirection: 'column', alignItems: 'stretch',
      borderRight: mobile ? 'none' : `1px solid ${C.line}`,
      borderBottom: mobile ? `1px solid ${C.line}` : 'none',
      background: C.stage,
      overflow: 'hidden',
    }}>
      {/* Top strip: season-equivalent eyebrow */}
      <div style={{
        padding: mobile ? '14px 16px' : '20px 28px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
        borderBottom: `1px solid ${C.line}`, gap: 16,
      }}>
        <div>
          <div style={{
            fontFamily: 'var(--display)', fontSize: 11, color: C.mute, fontWeight: 600,
            letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 4,
          }}>Fit Passport · Season 01</div>
          <div style={{
            fontFamily: 'var(--display)', fontSize: mobile ? 18 : 22, fontWeight: 700,
            color: C.ink, letterSpacing: '-0.015em',
          }}>Welcome back, shopper.</div>
        </div>
        <div style={{
          fontFamily: 'var(--display)', fontSize: 12, color: C.mute,
          padding: '4px 10px', border: `1px solid ${C.line}`,
          whiteSpace: 'nowrap',
        }}>BETA · LOBBY</div>
      </div>

      {/* Avatar canvas area */}
      <div style={{
        flex: 1, position: 'relative',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: mobile ? '24px 16px 16px' : '40px 40px 24px',
        minHeight: mobile ? 360 : 420,
      }}>
        {/* Subtle radial gradient under feet */}
        <div aria-hidden style={{
          position: 'absolute', bottom: mobile ? 60 : 80, left: '50%', transform: 'translateX(-50%)',
          width: mobile ? 240 : 320, height: 60,
          background: `radial-gradient(ellipse, ${C.line} 0%, transparent 70%)`,
          pointerEvents: 'none',
        }} />
        {/* Concentric rings as platform */}
        <div aria-hidden style={{
          position: 'absolute', bottom: mobile ? 50 : 64, left: '50%', transform: 'translateX(-50%)',
          width: mobile ? 280 : 360,
          display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'center',
          pointerEvents: 'none',
        }}>
          <div style={{ width: '100%', height: 1, background: C.line }} />
          <div style={{ width: '85%', height: 1, background: C.line, opacity: 0.7 }} />
          <div style={{ width: '70%', height: 1, background: C.line, opacity: 0.5 }} />
        </div>
        {/* Avatar image (placeholder; will be Three.js canvas tomorrow) */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/redesign/avatar.png"
          alt="Your fit passport avatar"
          style={{
            position: 'relative', zIndex: 2,
            maxHeight: mobile ? 360 : 480,
            width: 'auto', height: '100%',
            objectFit: 'contain', display: 'block',
          }}
        />
      </div>

      {/* Bottom stats strip */}
      <div style={{
        borderTop: `1px solid ${C.line}`,
        padding: mobile ? '12px 16px' : '14px 28px',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
        gap: 0,
        background: C.bg,
      }}>
        {[
          { k: 'Height', v: '175 cm' },
          { k: 'Confidence', v: '82%' },
          { k: 'Sessions', v: '23' },
          { k: 'Try-ons', v: '47' },
          { k: 'Saved', v: '12' },
        ].map((s, i, arr) => (
          <div key={s.k} style={{
            padding: mobile ? '6px 10px' : '8px 14px',
            borderRight: i < arr.length - 1 ? `1px solid ${C.line}` : 'none',
            minWidth: 0,
          }}>
            <div style={{
              fontFamily: 'var(--display)', fontSize: 10, color: C.mute, fontWeight: 600,
              letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 2,
            }}>{s.k}</div>
            <div style={{
              fontFamily: 'var(--display)', fontSize: 16, fontWeight: 600, color: C.ink,
              letterSpacing: '-0.01em',
            }}>{s.v}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Right rail: stacked modules ─── */
function Module({
  C, label, sub, items, ctaLabel, ctaHref, accent,
}: {
  C: Palette;
  label: string;
  sub?: string;
  items: { name: string; meta: string; thumb?: string }[];
  ctaLabel: string;
  ctaHref: string;
  accent?: boolean;
}) {
  const router = useRouter();
  const bg = accent ? C.cardBg : C.surface;
  const ink = accent ? C.cardInk : C.ink;
  const mute = accent ? 'rgba(255,255,255,0.6)' : C.mute;
  const hair = accent ? 'rgba(255,255,255,0.14)' : C.line;
  return (
    <div style={{
      background: bg, color: ink,
      border: `1px solid ${C.line}`,
      display: 'flex', flexDirection: 'column',
    }}>
      <div style={{
        padding: '14px 18px', borderBottom: `1px solid ${hair}`,
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 10,
      }}>
        <div>
          <div style={{
            fontFamily: 'var(--display)', fontSize: 14, fontWeight: 700, color: ink, letterSpacing: '-0.01em',
          }}>{label}</div>
          {sub && (
            <div style={{ fontFamily: 'var(--display)', fontSize: 11.5, color: mute, marginTop: 2 }}>{sub}</div>
          )}
        </div>
        <button
          onClick={() => router.push(ctaHref)}
          style={{
            background: 'none', border: 'none', padding: 0, cursor: 'pointer',
            fontFamily: 'var(--display)', fontSize: 12, fontWeight: 600, color: ink,
          }}
        >{ctaLabel} →</button>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {items.map((it, i) => (
          <div key={`${it.name}-${i}`} style={{
            padding: '10px 18px',
            borderBottom: i < items.length - 1 ? `1px solid ${hair}` : 'none',
            display: 'flex', alignItems: 'center', gap: 12,
          }}>
            <div style={{
              width: 36, height: 36, flexShrink: 0,
              background: accent ? 'rgba(255,255,255,0.08)' : C.bg,
              border: `1px solid ${hair}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              overflow: 'hidden',
            }}>
              {it.thumb && (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img src={it.thumb} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
              )}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600, color: ink,
                letterSpacing: '-0.005em',
                whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
              }}>{it.name}</div>
              <div style={{
                fontFamily: 'var(--display)', fontSize: 11.5, color: mute,
                whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
              }}>{it.meta}</div>
            </div>
            <span style={{ fontFamily: 'var(--display)', fontSize: 14, color: mute }}>→</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function RightRail({ C, mobile }: { C: Palette; mobile: boolean }) {
  return (
    <div style={{
      width: mobile ? '100%' : 360,
      flexShrink: 0,
      display: 'flex', flexDirection: 'column', gap: 16,
      padding: mobile ? '16px' : '20px',
      background: C.bg,
      overflowY: mobile ? 'visible' : 'auto',
    }}>
      <Module
        C={C}
        label="Recent fits"
        sub="Last 7 days"
        items={[
          { name: 'NPC Oversized T-shirt', meta: 'Nude Project · M · fit recommended' },
          { name: 'Black Tracksuit Top', meta: 'Originals · L · sized up' },
          { name: 'Cropped Hoodie', meta: 'Nude Project · S · close fit' },
        ]}
        ctaLabel="Closet"
        ctaHref="/dashboard?tab=closet"
      />
      <Module
        C={C}
        label="New brands"
        sub="Just added"
        items={[
          { name: 'Ramin Studios', meta: 'Amsterdam · streetwear' },
          { name: 'Originals', meta: 'EU · basics' },
          { name: 'Nude Project', meta: 'Madrid · oversized' },
        ]}
        ctaLabel="Browse"
        ctaHref="/dashboard?tab=closet"
        accent
      />
      <Module
        C={C}
        label="Wishlist"
        sub="Saved for later"
        items={[
          { name: 'Hoodie Black', meta: 'Wishlist · check fit' },
          { name: 'Track Pant Slim', meta: 'Wishlist · check size' },
        ]}
        ctaLabel="Wishlist"
        ctaHref="/dashboard?tab=wishlist"
      />
    </div>
  );
}

/* ─── Lobby footer with primary CTA ─── */
function LobbyFooter({ C, mobile }: { C: Palette; mobile: boolean }) {
  const router = useRouter();
  return (
    <div style={{
      borderTop: `1px solid ${C.line}`,
      background: C.bg, color: C.ink,
      padding: mobile ? '14px 16px' : '16px 28px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 14,
      flexWrap: 'wrap',
    }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
        <div style={{
          fontFamily: 'var(--display)', fontSize: 11, color: C.mute, fontWeight: 600,
          letterSpacing: '0.04em', textTransform: 'uppercase',
        }}>Daily ritual</div>
        <div style={{
          fontFamily: 'var(--display)', fontSize: 14, color: C.ink, fontWeight: 500,
          letterSpacing: '-0.005em',
        }}>Try on a brand. See if it fits before you check out.</div>
      </div>
      <button
        onClick={() => router.push('/dashboard?tab=closet')}
        style={{
          background: C.ink, color: C.bg, border: 'none',
          padding: mobile ? '13px 22px' : '14px 28px',
          fontFamily: 'var(--display)', fontSize: 14, fontWeight: 700,
          letterSpacing: '0.02em',
          cursor: 'pointer', borderRadius: 0,
          display: 'inline-flex', alignItems: 'center', gap: 12,
        }}
      >
        Browse brands
        <span style={{ fontSize: 16 }}>→</span>
      </button>
    </div>
  );
}

export default function ShopperLobbyPage() {
  const { theme, toggleTheme } = useTheme();
  const dark = theme === 'dark';
  const C = dark ? PAL.dark : PAL.light;
  const router = useRouter();
  const mobile = useIsMobile();

  const links = [
    { label: 'Lobby', onClick: () => router.push('/dashboard/lobby'), active: true },
    { label: 'Profile', onClick: () => router.push('/dashboard') },
    { label: 'Closet', onClick: () => router.push('/dashboard?tab=closet') },
    { label: 'Wishlist', onClick: () => router.push('/dashboard?tab=wishlist') },
  ];

  return (
    <div className="tryon-redesign-root" style={{
      width: '100%', minHeight: '100vh',
      background: C.bg, color: C.ink,
      display: 'flex', flexDirection: 'column',
    }}>
      <SharedNav
        dark={dark}
        homeHref="/dashboard"
        links={links}
        rightSlot={mobile ? null : (
          <>
            <NavLink dark={dark} label="Old dashboard" href="/dashboard" />
            <NavCta dark={dark} label="Sign out" onClick={() => router.push('/login')} />
          </>
        )}
      />

      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: mobile ? 'column' : 'row',
        minHeight: 0,
      }}>
        <AvatarStage C={C} mobile={mobile} />
        <RightRail C={C} mobile={mobile} />
      </div>

      <LobbyFooter C={C} mobile={mobile} />
    </div>
  );
}
