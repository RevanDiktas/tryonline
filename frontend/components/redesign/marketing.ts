import type React from 'react';

/* Marketing palette and type, shared by /product, /pricing and /start. Off-white and ink,
   cobalt only on primary CTAs (the "red thread"), Inter with tight tracking. */
export const PAL = {
  light: {
    bg: '#FAFAF8', surface: '#FFFFFF',
    ink: '#0A0A0A', mute: '#6E6E6E',
    line: 'rgba(10,10,10,0.10)',
    cardBg: '#0A0A0A', cardInk: '#FAFAF8',
    cardLine: 'rgba(255,255,255,0.14)', cardMute: '#9A9A9A',
  },
  dark: {
    bg: '#0A0A0A', surface: '#121212',
    ink: '#F2F1EC', mute: '#8A8A8A',
    line: 'rgba(255,255,255,0.10)',
    cardBg: '#F2F1EC', cardInk: '#0A0A0A',
    cardLine: 'rgba(0,0,0,0.10)', cardMute: '#6E6E6E',
  },
};
export type Palette = typeof PAL.light;

export const ACCENT = '#0040FF';

export const headingStyle = (px: string): React.CSSProperties => ({
  fontFamily: 'var(--display)',
  fontWeight: 700,
  fontSize: px,
  letterSpacing: '-0.022em',
  lineHeight: 1.04,
  margin: 0,
});

export const bodyStyle: React.CSSProperties = {
  fontFamily: 'var(--display)',
  fontWeight: 400,
  fontSize: 16,
  lineHeight: 1.6,
};

export const eyebrowStyle = (C: Palette): React.CSSProperties => ({
  fontFamily: 'var(--mono)',
  fontSize: 11.5,
  letterSpacing: '0.12em',
  textTransform: 'uppercase',
  color: C.mute,
  margin: '0 0 14px',
});

export const pillButton = (kind: 'primary' | 'ghost', C: Palette): React.CSSProperties => ({
  background: kind === 'primary' ? ACCENT : 'transparent',
  color: kind === 'primary' ? '#FFFFFF' : C.ink,
  border: kind === 'primary' ? 'none' : `1px solid ${C.ink}`,
  padding: '14px 24px',
  fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600,
  letterSpacing: '-0.005em', cursor: 'pointer',
  display: 'inline-flex', alignItems: 'center', gap: 10,
  borderRadius: 9999, textDecoration: 'none',
});
