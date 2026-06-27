'use client';

import { useEffect } from 'react';
import { TryonLogo } from '@/components/TryonLogo';
import { useTheme } from '@/contexts/ThemeContext';

// Calendly is connected to revan@tryon.global, so every booking lands in the
// Outlook calendar. We embed the scheduler inline so brands book without
// leaving the site.
const CALENDLY_URL = 'https://calendly.com/revan-tryon/30min';

export default function BookPage() {
  const { theme } = useTheme();
  const dark = theme === 'dark';
  const ink = dark ? '#F2F1EC' : '#0A0A0A';
  const bg = dark ? '#0A0A0A' : '#FFFFFF';

  useEffect(() => {
    const id = 'calendly-widget-script';
    const existing = document.getElementById(id);
    if (!existing) {
      const s = document.createElement('script');
      s.id = id;
      s.src = 'https://assets.calendly.com/assets/external/widget.js';
      s.async = true;
      document.body.appendChild(s);
    } else {
      // Script already loaded from a prior visit: re-render the inline widget.
      const w = window as unknown as { Calendly?: { initInlineWidgets?: () => void } };
      w.Calendly?.initInlineWidgets?.();
    }
  }, []);

  return (
    <div style={{
      minHeight: '100vh', background: bg, color: ink,
      display: 'flex', flexDirection: 'column',
    }}>
      <div style={{ padding: '20px 24px' }}>
        <TryonLogo href="/" className="h-6 w-auto" />
      </div>
      <div style={{
        width: '100%', maxWidth: 820, margin: '0 auto',
        padding: '8px 20px 48px', textAlign: 'center',
      }}>
        <div style={{
          fontFamily: 'var(--mono)', fontSize: 12, letterSpacing: '0.08em',
          textTransform: 'uppercase', opacity: 0.55, marginBottom: 12,
        }}>Book a call</div>
        <h1 style={{
          fontFamily: 'var(--display)', fontWeight: 700,
          fontSize: 'clamp(28px, 4.5vw, 44px)', letterSpacing: '-0.03em',
          lineHeight: 1.05, margin: '0 0 10px',
        }}>Let us get your brand live.</h1>
        <p style={{
          fontFamily: 'var(--display)', fontSize: 16, lineHeight: 1.6,
          opacity: 0.7, margin: '0 auto 28px', maxWidth: 520,
        }}>
          Pick a time that works. We walk through your size charts, garments, and
          widget install, and map the fastest path to going live on your store.
        </p>
        <div
          className="calendly-inline-widget"
          data-url={CALENDLY_URL}
          style={{ minWidth: 320, height: 720 }}
        />
      </div>
    </div>
  );
}
