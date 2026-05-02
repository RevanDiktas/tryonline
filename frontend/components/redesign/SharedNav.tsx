'use client';

import React, { ReactNode, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

/* Shared color tokens for nav. Black + white only. */
type NavTheme = {
  bg: string;
  ink: string;
  mute: string;
  line: string;
  ctaBg: string;
  ctaInk: string;
};

function useNavTheme(dark?: boolean): NavTheme {
  return dark
    ? { bg: '#0A0A0A', ink: '#F2F1EC', mute: '#8A8A8A', line: 'rgba(255,255,255,0.10)', ctaBg: '#F2F1EC', ctaInk: '#0A0A0A' }
    : { bg: '#FAFAF8', ink: '#0A0A0A', mute: '#6E6E6E', line: 'rgba(10,10,10,0.10)', ctaBg: '#0A0A0A', ctaInk: '#FAFAF8' };
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
        gap: 24,
        padding: '14px 24px',
        maxWidth: 1440,
        margin: '0 auto',
      }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 28, minWidth: 0 }}>
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

          {links && links.length > 0 && (
            <div style={{ display: 'flex', gap: 24, alignItems: 'center' }}>
              {links.map(it => (
                <NavTextLink key={it.label} link={it} dark={dark} />
              ))}
            </div>
          )}
        </div>

        {rightSlot && (
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 14 }}>
            {rightSlot}
          </div>
        )}
      </div>
    </div>
  );
}

/* Single nav text link. Bold when active, dim otherwise. */
function NavTextLink({ link, dark }: { link: NavLinkSpec; dark?: boolean }) {
  const C = useNavTheme(dark);
  const router = useRouter();
  const handle = () => {
    if (link.onClick) link.onClick();
    else if (link.href) router.push(link.href);
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

export function NavLink({ label, href, onClick, active, dark }: {
  label: string;
  href?: string;
  onClick?: () => void;
  active?: boolean;
  dark?: boolean;
}) {
  return <NavTextLink link={{ label, href, onClick, active }} dark={dark} />;
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
        padding: '9px 16px',
        background: solid ? C.ctaBg : 'transparent',
        color: solid ? C.ctaInk : C.ink,
        border: solid ? 'none' : `1px solid ${C.ink}`,
        borderRadius: 0,
        fontFamily: 'var(--display)',
        fontSize: 13, fontWeight: 600,
        cursor: 'pointer',
        display: 'inline-flex', alignItems: 'center', gap: 8,
        whiteSpace: 'nowrap',
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
        borderRadius: 0,
      }}
    >{icon}</button>
  );
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
