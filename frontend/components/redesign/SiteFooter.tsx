'use client';

import Link from 'next/link';
import { useIsMobile } from './useIsMobile';
import { FOOTER_LINKS } from './siteLinks';

// Same tokens as the page palettes. No top rule: every section above already ends in one.
const PAL = {
  light: { bg: '#FAFAF8', ink: '#0A0A0A', mute: '#6E6E6E' },
  dark: { bg: '#0A0A0A', ink: '#F2F1EC', mute: '#8A8A8A' },
};

/** The one footer for every public page. Real <a> links, so crawlers can follow them. */
export function SiteFooter({ dark }: { dark: boolean }) {
  const C = dark ? PAL.dark : PAL.light;
  const mobile = useIsMobile();

  const links = (
    <nav aria-label="Footer" style={{ display: 'flex', gap: mobile ? 18 : 22, flexWrap: 'wrap' }}>
      {FOOTER_LINKS.map((it) => (
        <Link
          key={it.href}
          href={it.href}
          style={{
            fontFamily: 'var(--display)', fontSize: 13, color: C.mute, fontWeight: 500,
            textDecoration: 'none',
          }}
        >{it.label}</Link>
      ))}
    </nav>
  );

  const wordmark = (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={dark ? '/redesign/wordmark-white.png' : '/redesign/wordmark.png'}
      alt="TryOn"
      style={{ height: mobile ? 13 : 14, width: 'auto', display: 'block' }}
    />
  );

  if (mobile) {
    return (
      <footer style={{
        background: C.bg, color: C.ink, padding: '24px 18px 36px',
        display: 'flex', flexDirection: 'column', gap: 12, alignItems: 'flex-start',
      }}>
        {wordmark}
        {links}
        <div style={{ fontFamily: 'var(--display)', fontSize: 12, color: C.mute }}>TryOn, 2026</div>
      </footer>
    );
  }

  return (
    <footer style={{
      background: C.bg, color: C.ink, padding: '40px 32px 48px',
    }}>
      <div style={{
        maxWidth: 1280, margin: '0 auto',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 24,
        flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
          {wordmark}
          <div style={{ fontFamily: 'var(--display)', fontSize: 13, color: C.mute }}>TryOn, 2026</div>
        </div>
        {links}
      </div>
    </footer>
  );
}
