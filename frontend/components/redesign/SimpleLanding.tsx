import type React from 'react';
'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { PAL, type Palette } from './marketing';
import { SharedNav, NavCta, AuthAwareSignInLink } from './SharedNav';
import { SiteFooter } from './SiteFooter';
import { siteLinks } from './siteLinks';
import { useIsMobile } from './useIsMobile';

/* Home page: one statement, a product list, a contact block. Nothing else.
   Type does the work; no cards, no stats, no numbering. */

const FRAVASH_URL = 'https://fravash.ai';

const PRODUCTS = [
  {
    id: 'size',
    line: 'A Find my size button on every product. Seven questions, no account, every size scored as a match. Sold out in theirs? They see the next best.',
    explore: 'Explore Size',
    href: '/product',
    image: null as string | null,
  },
  {
    id: 'tryon',
    line: 'Photoreal 3D try-on on the shopper’s own body, with real cloth. One photo makes the avatar. Works where you have a 3D garment.',
    explore: 'Explore Try-On',
    href: '/product',
    image: '/redesign/fit-passport.jpg',
  },
  {
    id: 'report',
    line: 'Once a month: your customers’ measurements, the sizes that don’t fit them, and the size run for the next drop.',
    explore: 'Explore Report',
    href: '/pricing',
    image: '/redesign/fit-report.jpg',
  },
  {
    id: 'production',
    line: 'Send us the design and the size run. We source the fabric, make the sample, grade it to your customers and ship the order. Denim first.',
    explore: 'Explore Fravash',
    href: FRAVASH_URL,
    image: null as string | null,
    external: true,
  },
];

const label = (C: Palette, size = 11): React.CSSProperties => ({
  fontFamily: 'var(--mono)', fontSize: size, color: C.mute, fontWeight: 500,
  letterSpacing: '0.12em', textTransform: 'uppercase',
});

function BoxButton({ children, onClick, href, dark }: {
  children: React.ReactNode; onClick?: () => void; href?: string; dark?: boolean;
}) {
  const ink = dark ? '#F2F1EC' : '#0A0A0A';
  const style: React.CSSProperties = {
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    padding: '18px 34px', border: `1px solid ${ink}`, color: ink,
    background: 'transparent', textDecoration: 'none', cursor: 'pointer',
    fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600,
    letterSpacing: '0.14em', textTransform: 'uppercase',
  };
  if (href) return <a href={href} style={style}>{children}</a>;
  return <button type="button" onClick={onClick} style={style}>{children}</button>;
}

function TextLink({ children, href, dark }: { children: React.ReactNode; href: string; dark?: boolean }) {
  const ink = dark ? '#F2F1EC' : '#0A0A0A';
  return (
    <Link href={href} style={{
      display: 'inline-flex', alignItems: 'center', gap: 10, color: ink, textDecoration: 'none',
      fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600,
      letterSpacing: '0.14em', textTransform: 'uppercase',
    }}>{children} <span aria-hidden>→</span></Link>
  );
}

export function SimpleLanding({ dark = false }: { dark?: boolean }) {
  const C = dark ? PAL.dark : PAL.light;
  const mobile = useIsMobile();
  const router = useRouter();
  const pad = mobile ? '0 20px' : '0 48px';
  const inner: React.CSSProperties = { maxWidth: 1240, margin: '0 auto', padding: pad };

  return (
    <div className="tryon-redesign-root" style={{ width: '100%', minHeight: '100vh', background: C.bg, color: C.ink }}>
      <SharedNav
        dark={dark}
        links={siteLinks('/')}
        rightSlot={mobile ? (
          <NavCta dark={dark} label="Free trial" href="/start" />
        ) : (
          <>
            <AuthAwareSignInLink dark={dark} />
            <NavCta dark={dark} label="Start free trial →" href="/start" />
          </>
        )}
      />

      {/* Statement */}
      <section style={{ ...inner, padding: mobile ? '96px 20px 112px' : '200px 48px 220px' }}>
        <h1 style={{
          fontFamily: 'var(--display)', fontWeight: 800,
          fontSize: mobile ? 'clamp(38px, 10.5vw, 56px)' : 'clamp(56px, 5.6vw, 92px)',
          letterSpacing: '-0.035em', lineHeight: 1.02, margin: 0, maxWidth: 1180,
        }}>
          We measure the people who buy your clothes, and make the next run fit them.
        </h1>
        <p style={{
          fontFamily: 'var(--display)', fontSize: mobile ? 17 : 20, lineHeight: 1.5,
          color: C.mute, margin: mobile ? '28px 0 40px' : '40px 0 56px', maxWidth: 640,
        }}>
          Size and body data for fashion brands, built in Amsterdam. Live with La Fam.
        </p>
        <div style={{ display: 'flex', gap: mobile ? 20 : 36, alignItems: 'center', flexWrap: 'wrap' }}>
          <BoxButton onClick={() => router.push('/start')} dark={dark}>Start free trial</BoxButton>
          <TextLink href="/product" dark={dark}>See how it works</TextLink>
        </div>
      </section>

      {/* Products */}
      <section style={{ background: C.surface, borderTop: `1px solid ${C.line}` }}>
        <div style={{ ...inner, padding: mobile ? '72px 20px 80px' : '120px 48px 140px' }}>
          <h2 style={{
            fontFamily: 'var(--display)', fontWeight: 500, fontSize: mobile ? 28 : 40,
            letterSpacing: '-0.02em', margin: '0 0 40px',
          }}>What we make</h2>
          <div style={{ borderTop: `1px solid ${C.line}` }}>
            {PRODUCTS.map((p, i) => (
              <div key={p.id} style={{
                display: 'grid',
                gridTemplateColumns: mobile ? '1fr' : '1.1fr 0.7fr 1fr',
                gap: mobile ? 20 : 40, alignItems: 'center',
                padding: mobile ? '44px 0' : '88px 0',
                borderBottom: `1px solid ${C.line}`,
              }}>
                <div>
                  <p style={{
                    fontFamily: 'var(--display)', fontSize: mobile ? 17 : 19, lineHeight: 1.5,
                    color: C.ink, margin: 0, maxWidth: 460,
                  }}>{p.line}</p>
                  <div style={{ ...label(C), marginTop: mobile ? 20 : 56 }}>/0{i + 1}</div>
                </div>
                <div style={{ display: mobile ? 'none' : 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 160 }}>
                  {p.image ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={p.image} alt="" style={{ maxHeight: 180, maxWidth: '80%', objectFit: 'contain', filter: dark ? 'invert(1) hue-rotate(180deg)' : 'none' }} />
                  ) : null}
                </div>
                <div style={{ textAlign: mobile ? 'left' : 'right' }}>
                  {'external' in p && p.external ? (
                    <a href={p.href} target="_blank" rel="noopener noreferrer" style={{
                      fontFamily: 'var(--display)', fontWeight: 500, textDecoration: 'none', color: C.ink,
                      fontSize: mobile ? 28 : 'clamp(36px, 3.6vw, 60px)', letterSpacing: '-0.03em', lineHeight: 1,
                    }}>{p.explore}</a>
                  ) : (
                    <Link href={p.href} style={{
                      fontFamily: 'var(--display)', fontWeight: 500, textDecoration: 'none', color: C.ink,
                      fontSize: mobile ? 28 : 'clamp(36px, 3.6vw, 60px)', letterSpacing: '-0.03em', lineHeight: 1,
                    }}>{p.explore}</Link>
                  )}
                </div>
              </div>
            ))}
          </div>
          <div style={{ ...label(C, 12), marginTop: 32, textTransform: 'none', letterSpacing: 0, fontFamily: 'var(--display)', fontSize: 14 }}>
            From $19 a month. 30-day free trial on every plan. <Link href="/pricing" style={{ color: C.ink }}>Pricing →</Link>
          </div>
        </div>
      </section>

      {/* Contact */}
      <section style={{ background: '#0A0A0A', color: '#F2F1EC' }}>
        <div style={{ ...inner, padding: mobile ? '80px 20px 96px' : '160px 48px 180px' }}>
          <div style={{ ...label(PAL.dark, 12), color: '#8A8A8A', marginBottom: mobile ? 28 : 56, textTransform: 'none', letterSpacing: '-0.01em', fontFamily: 'var(--display)', fontSize: mobile ? 22 : 28, fontWeight: 500 }}>Contact</div>
          <h2 style={{
            fontFamily: 'var(--display)', fontWeight: 500,
            fontSize: mobile ? 'clamp(34px, 9vw, 48px)' : 'clamp(48px, 5vw, 84px)',
            letterSpacing: '-0.035em', lineHeight: 1.04, margin: '0 0 48px', maxWidth: 1000, color: '#F2F1EC',
          }}>
            For brands, press, partnerships and production.
          </h2>
          <div style={{ display: 'flex', gap: mobile ? 20 : 36, alignItems: 'center', flexWrap: 'wrap' }}>
            <BoxButton href="/book" dark>Get in touch</BoxButton>
            <TextLink href="/pricing" dark>See pricing</TextLink>
          </div>
        </div>
      </section>

      <SiteFooter dark={dark} />
    </div>
  );
}
