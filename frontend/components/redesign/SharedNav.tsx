'use client';

import React, { ReactNode, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser, type User } from '@/lib/supabase-auth';
import { useIsMobile } from './useIsMobile';

/* Shared color tokens for nav. Black + white foundation, cobalt accent on
   primary CTA only (the "red thread"). Both modes use cobalt for the solid
   button so the accent reads consistently across the marketing surface. */
type NavTheme = {
  bg: string;
  ink: string;
  mute: string;
  line: string;
  ctaBg: string;
  ctaInk: string;
  accent: string;
};

function useNavTheme(dark?: boolean): NavTheme {
  return dark
    ? { bg: '#0A0A0A', ink: '#F2F1EC', mute: '#8A8A8A', line: 'rgba(255,255,255,0.10)', ctaBg: '#0040FF', ctaInk: '#FFFFFF', accent: '#0040FF' }
    : { bg: '#FAFAF8', ink: '#0A0A0A', mute: '#6E6E6E', line: 'rgba(10,10,10,0.10)', ctaBg: '#0040FF', ctaInk: '#FFFFFF', accent: '#0040FF' };
}

/* Smart hide-on-scroll behavior, used by every nav. */
function useSmartNav(): boolean {
  const [hidden, setHidden] = useState(false);
  useEffect(() => {
    let lastY = window.scrollY;
    let downAccum = 0;
    let raf = 0;
    const onScroll = () => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        const y = window.scrollY;
        const dy = y - lastY;
        lastY = y;
        raf = 0;
        if (y < 100) { downAccum = 0; setHidden(false); return; }
        if (dy < 0) { downAccum = 0; setHidden(false); return; }
        downAccum += dy;
        if (downAccum > 60) setHidden(true);
      });
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  return hidden;
}

export type NavLinkSpec = {
  label: string;
  href?: string;
  onClick?: () => void;
  active?: boolean;
  external?: boolean;
};

/* The nav itself. Sharp corners, sentence case, single font, no pills. */
export function SharedNav({
  dark,
  links,
  rightSlot,
  homeHref = '/',
  sticky = true,
}: {
  dark?: boolean;
  links?: NavLinkSpec[];
  rightSlot?: ReactNode;
  homeHref?: string;
  sticky?: boolean;
}) {
  const C = useNavTheme(dark);
  const router = useRouter();
  const hidden = useSmartNav();
  const mobile = useIsMobile();
  const [menuOpen, setMenuOpen] = useState(false);

  const hasLinks = !!(links && links.length > 0);

  return (
    <div style={{
      position: sticky ? 'sticky' : 'static',
      top: 0,
      zIndex: 70,
      background: C.bg,
      borderBottom: `1px solid ${C.line}`,
      transform: sticky && hidden ? 'translateY(-110%)' : 'translateY(0)',
      transition: 'transform 0.28s cubic-bezier(0.4, 0.0, 0.2, 1)',
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: 16,
        padding: mobile ? '12px 16px' : '14px 24px',
        maxWidth: 1440,
        margin: '0 auto',
      }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 24, minWidth: 0 }}>
          <button
            type="button"
            onClick={() => router.push(homeHref)}
            style={{
              background: 'none', border: 'none', padding: 0,
              cursor: 'pointer', display: 'inline-flex',
            }}
            aria-label="TryOn home"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={dark ? '/redesign/wordmark-white.png' : '/redesign/wordmark.png'}
              alt="TryOn"
              style={{ height: 18, width: 'auto', display: 'block' }}
            />
          </button>

          {!mobile && hasLinks && (
            <div style={{ display: 'flex', gap: 24, alignItems: 'center' }}>
              {links!.map(it => (
                <NavTextLink key={it.label} link={it} dark={dark} />
              ))}
            </div>
          )}
        </div>

        <div style={{ display: 'inline-flex', alignItems: 'center', gap: mobile ? 10 : 14 }}>
          {rightSlot}
          {mobile && hasLinks && (
            <button
              type="button"
              onClick={() => setMenuOpen(o => !o)}
              aria-label={menuOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={menuOpen}
              style={{
                width: 36, height: 36,
                background: 'transparent',
                border: `1px solid ${C.line}`,
                color: C.ink,
                cursor: 'pointer',
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                borderRadius: 8,
                flexShrink: 0,
              }}
            >
              {menuOpen ? (
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M2 2l10 10M12 2L2 12" stroke={C.ink} strokeWidth="1.6" strokeLinecap="round" />
                </svg>
              ) : (
                <svg width="16" height="14" viewBox="0 0 16 14" fill="none">
                  <path d="M0 1.5h16M0 7h16M0 12.5h16" stroke={C.ink} strokeWidth="1.6" strokeLinecap="round" />
                </svg>
              )}
            </button>
          )}
        </div>
      </div>

      {mobile && menuOpen && hasLinks && (
        <div style={{
          borderTop: `1px solid ${C.line}`,
          background: C.bg,
          padding: '10px 16px 14px',
          display: 'flex', flexDirection: 'column', gap: 0,
        }}>
          {links!.map(it => (
            <button
              key={it.label}
              onClick={() => {
                setMenuOpen(false);
                if (it.onClick) it.onClick();
                else if (it.href) {
                  if (it.external) window.open(it.href, '_blank', 'noopener');
                  else router.push(it.href);
                }
              }}
              style={{
                background: 'none', border: 'none', padding: '14px 0',
                textAlign: 'left', cursor: 'pointer',
                fontFamily: 'var(--display)',
                fontSize: 16,
                color: it.active ? C.ink : C.mute,
                fontWeight: it.active ? 600 : 500,
                borderBottom: `1px solid ${C.line}`,
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              }}
            >
              <span>{it.label}</span>
              <span style={{ fontSize: 14, color: C.mute }}>{it.external ? '↗' : '→'}</span>
            </button>
          ))}
          <div style={{ paddingTop: 14 }}>
            <AuthAwareSignInLink dark={dark} mobile />
          </div>
        </div>
      )}
    </div>
  );
}

/* Single nav text link. Bold when active, dim otherwise. */
function NavTextLink({ link, dark }: { link: NavLinkSpec; dark?: boolean }) {
  const C = useNavTheme(dark);
  const router = useRouter();
  const handle = () => {
    if (link.onClick) link.onClick();
    else if (link.href) {
      if (link.external) window.open(link.href, '_blank', 'noopener');
      else router.push(link.href);
    }
  };
  return (
    <button
      onClick={handle}
      style={{
        background: 'none', border: 'none', padding: 0, cursor: 'pointer',
        fontFamily: 'var(--display)',
        fontSize: 14,
        color: link.active ? C.ink : C.mute,
        fontWeight: link.active ? 600 : 500,
      }}
    >{link.label}</button>
  );
}

export function NavLink({ label, href, onClick, active, dark, external }: {
  label: string;
  href?: string;
  onClick?: () => void;
  active?: boolean;
  dark?: boolean;
  external?: boolean;
}) {
  return <NavTextLink link={{ label, href, onClick, active, external }} dark={dark} />;
}

export function NavText({ children, dark }: { children: ReactNode; dark?: boolean }) {
  const C = useNavTheme(dark);
  return (
    <span style={{
      fontFamily: 'var(--display)', fontSize: 13, color: C.mute,
      whiteSpace: 'nowrap',
    }}>{children}</span>
  );
}

export function NavCta({
  label, href, onClick, variant = 'solid', dark,
}: {
  label: string;
  href?: string;
  onClick?: () => void;
  variant?: 'solid' | 'outline';
  dark?: boolean;
}) {
  const C = useNavTheme(dark);
  const router = useRouter();
  const handle = () => {
    if (onClick) onClick();
    else if (href) router.push(href);
  };
  const solid = variant === 'solid';
  return (
    <button
      onClick={handle}
      style={{
        padding: '10px 20px',
        background: solid ? C.ctaBg : 'transparent',
        color: solid ? C.ctaInk : C.ink,
        border: solid ? 'none' : `1px solid ${C.ink}`,
        borderRadius: 9999,
        fontFamily: 'var(--display)',
        fontSize: 13, fontWeight: 600,
        letterSpacing: '-0.005em',
        cursor: 'pointer',
        display: 'inline-flex', alignItems: 'center', gap: 8,
        whiteSpace: 'nowrap',
        transition: 'transform 180ms cubic-bezier(0.4, 0, 0.2, 1), background 180ms cubic-bezier(0.4, 0, 0.2, 1)',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-1px)';
        if (!solid) {
          e.currentTarget.style.background = 'rgba(0, 64, 255, 0.08)';
          e.currentTarget.style.borderColor = '#0040FF';
          e.currentTarget.style.color = '#0040FF';
        } else {
          e.currentTarget.style.background = '#0030CC';
        }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        if (!solid) {
          e.currentTarget.style.background = 'transparent';
          e.currentTarget.style.borderColor = C.ink;
          e.currentTarget.style.color = C.ink;
        } else {
          e.currentTarget.style.background = C.ctaBg;
        }
      }}
    >{label}</button>
  );
}

export function NavIconButton({
  onClick, icon, label, dark,
}: {
  onClick: () => void;
  icon: ReactNode;
  label: string;
  dark?: boolean;
}) {
  const C = useNavTheme(dark);
  return (
    <button
      onClick={onClick}
      aria-label={label}
      title={label}
      style={{
        width: 30, height: 30,
        border: `1px solid ${C.line}`,
        background: 'transparent',
        color: C.ink,
        cursor: 'pointer',
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        borderRadius: 8,
      }}
    >{icon}</button>
  );
}

/**
 * Auth-aware right side: detects current user and shows Dashboard link if signed in,
 * Sign in link otherwise. Use this everywhere the marketing nav lives so a returning
 * brand or shopper does not get prompted to sign in again.
 */
export function AuthAwareSignInLink({ dark, mobile }: { dark?: boolean; mobile?: boolean }) {
  const C = useNavTheme(dark);
  const router = useRouter();
  const [user, setUser] = useState<User | null | undefined>(undefined);
  useEffect(() => {
    let alive = true;
    getCurrentUser()
      .then(u => { if (alive) setUser(u); })
      .catch(() => { if (alive) setUser(null); });
    return () => { alive = false; };
  }, []);

  if (user === undefined) {
    if (mobile) return null;
    return <span style={{ width: 50, height: 14, display: 'inline-block' }} aria-hidden />;
  }

  const label = user ? 'Dashboard' : 'Sign in';
  const href = user
    ? (user.user_type === 'brand' ? '/brand' : '/dashboard')
    : '/login';

  if (mobile) {
    return (
      <button
        onClick={() => router.push(href)}
        style={{
          background: C.ctaBg, color: C.ctaInk,
          border: 'none', padding: '14px 20px',
          fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600,
          cursor: 'pointer', borderRadius: 9999,
          width: '100%', textAlign: 'left',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          letterSpacing: '-0.005em',
        }}
      >
        <span>{label}</span>
        <span>→</span>
      </button>
    );
  }

  return <NavLink dark={dark} label={label} href={href} />;
}

export function NavThemeToggle({ dark, onToggle }: { dark: boolean; onToggle: () => void }) {
  const C = useNavTheme(dark);
  const sun = (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={C.ink} strokeWidth="1.6">
      <circle cx="12" cy="12" r="4" />
      <path strokeLinecap="round" d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </svg>
  );
  const moon = (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M11 8.5A4.5 4.5 0 016.5 4 4 4 0 109 11.5 4.5 4.5 0 0111 8.5z" stroke={C.ink} strokeWidth="1.4" />
    </svg>
  );
  return <NavIconButton onClick={onToggle} icon={dark ? sun : moon} label="Toggle theme" dark={dark} />;
}
