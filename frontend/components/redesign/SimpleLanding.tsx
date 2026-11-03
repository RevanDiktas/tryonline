'use client';

import type React from 'react';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { siteLinks } from './siteLinks';
import { useIsMobile } from './useIsMobile';

/* Home page. One fixed, inset nav bar; a full-screen hero with the avatar and a two-tone
   tagline; one statement; a product list; a dark contact block; a column footer.
   Single light theme by design: paper, ink, one grey. */

const AvatarHero = dynamic(() => import('./AvatarHero').then((m) => m.AvatarHero), { ssr: false });

const INK = '#141414';
const PAPER = '#F4F4F2';
const WHITE = '#FBFBFA';
const GREY = '#8C8C8C';
const LINE = 'rgba(20,20,20,0.14)';
const DARK = '#111111';

const FRAVASH_URL = 'https://fravash.ai';

const PRODUCTS = [
  {
    id: 'size',
    name: 'Size',
    line: 'A Find my size button on every product. Seven questions, no account, every size scored as a match. Sold out in theirs? They see the next best.',
    explore: 'Explore Size',
    href: '/product',
    image: '/redesign/widget.jpg',
  },
  {
    id: 'tryon',
    name: 'Try-On',
    line: 'Photoreal 3D try-on on the shopper’s own body, with real cloth. One photo makes the avatar. Works where you have a 3D garment.',
    explore: 'Explore Try-On',
    href: '/product',
    image: '/redesign/fit-passport.jpg',
  },
  {
    id: 'report',
    name: 'Report',
    line: 'Once a month: your customers’ measurements, the sizes that don’t fit them, and the size run for the next drop.',
    explore: 'Explore Report',
    href: '/pricing',
    image: '/redesign/fit-report.jpg',
  },
  {
    id: 'fravash',
    name: 'Fravash',
    line: 'Send us the design and the size run. We source the fabric, make the sample, grade it to your customers and ship the order. Denim first.',
    explore: 'Explore Fravash',
    href: FRAVASH_URL,
    image: null as string | null,
    external: true,
  },
];

const caps = (size = 12, color = INK): React.CSSProperties => ({
  fontFamily: 'var(--display)', fontSize: size, fontWeight: 600,
  letterSpacing: '0.18em', textTransform: 'uppercase', color,
});

function BoxButton({ children, href, light }: { children: React.ReactNode; href: string; light?: boolean }) {
  const ink = light ? '#F4F4F2' : INK;
  return (
    <Link href={href} style={{
      ...caps(13, ink),
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      padding: '22px 36px', border: `1px solid ${ink}`, textDecoration: 'none', background: 'transparent',
    }}>{children}</Link>
  );
}

function ArrowLink({ children, href, light, external }: { children: React.ReactNode; href: string; light?: boolean; external?: boolean }) {
  const ink = light ? '#F4F4F2' : INK;
  const style: React.CSSProperties = { ...caps(13, ink), display: 'inline-flex', alignItems: 'center', gap: 14, textDecoration: 'none' };
  if (external) return <a href={href} target="_blank" rel="noopener noreferrer" style={style}>{children} <span aria-hidden style={{ fontSize: 18, letterSpacing: 0 }}>→</span></a>;
  return <Link href={href} style={style}>{children} <span aria-hidden style={{ fontSize: 18, letterSpacing: 0 }}>→</span></Link>;
}

/* ─── Nav: a translucent bar inset from the page edge, logo left, menu right ─── */
function FloatingNav({ mobile }: { mobile: boolean }) {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [open]);
  const inset = mobile ? 12 : 24;
  return (
    <>
      <div style={{
        position: 'fixed', top: inset, left: inset, right: inset, zIndex: 50,
        height: mobile ? 72 : 92,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: mobile ? '0 16px 0 20px' : '0 24px 0 36px',
        background: 'rgba(232,232,230,0.82)', backdropFilter: 'blur(14px)', WebkitBackdropFilter: 'blur(14px)',
        border: `1px solid ${LINE}`,
      }}>
        <Link href="/" aria-label="TryOn home" style={{ display: 'flex', alignItems: 'center' }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/redesign/wordmark.png" alt="TryOn" style={{ height: mobile ? 22 : 26, width: 'auto', display: 'block' }} />
        </Link>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {!mobile && (
            <Link href="/start" style={{
              ...caps(12), display: 'inline-flex', alignItems: 'center', height: 54, padding: '0 26px',
              border: `1px solid ${INK}`, textDecoration: 'none',
            }}>Start free trial</Link>
          )}
          <button
            type="button" aria-label={open ? 'Close menu' : 'Open menu'} aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
            style={{
              width: mobile ? 48 : 54, height: mobile ? 48 : 54, border: `1px solid ${INK}`, background: 'transparent',
              display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', padding: 0,
            }}
          >
            <span style={{ display: 'block', width: 22 }}>
              {open ? (
                <span style={{ display: 'block', position: 'relative', height: 14 }}>
                  <span style={{ position: 'absolute', left: 0, right: 0, top: 6, height: 1.5, background: INK, transform: 'rotate(45deg)' }} />
                  <span style={{ position: 'absolute', left: 0, right: 0, top: 6, height: 1.5, background: INK, transform: 'rotate(-45deg)' }} />
                </span>
              ) : (
                <>
                  <span style={{ display: 'block', height: 1.5, background: INK, marginBottom: 5 }} />
                  <span style={{ display: 'block', height: 1.5, background: INK, marginBottom: 5 }} />
                  <span style={{ display: 'block', height: 1.5, background: INK }} />
                </>
              )}
            </span>
          </button>
        </div>
      </div>

      {open && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 40, background: PAPER, color: INK,
          padding: mobile ? '120px 24px 40px' : '160px 60px 60px',
          display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
        }}>
          <nav style={{ display: 'flex', flexDirection: 'column', gap: mobile ? 18 : 22 }}>
            {[{ label: 'Home', href: '/' }, ...siteLinks('/').map((l) => ({ label: l.label, href: l.href ?? '/' })), { label: 'Sign in', href: '/login' }].map((l) => (
              <Link key={l.href} href={l.href} onClick={() => setOpen(false)} style={{
                fontFamily: 'var(--display)', fontWeight: 700, color: INK, textDecoration: 'none',
                fontSize: mobile ? 40 : 64, letterSpacing: '-0.035em', lineHeight: 1,
              }}>{l.label}</Link>
            ))}
          </nav>
          <div style={{ display: 'flex', gap: 24, alignItems: 'center', flexWrap: 'wrap' }}>
            <BoxButton href="/start">Start free trial</BoxButton>
            <ArrowLink href={FRAVASH_URL} external>Fravash</ArrowLink>
          </div>
        </div>
      )}
    </>
  );
}

/* ─── Hero: the avatar fills the screen; the tagline sits over it, two tones ─── */
function Hero({ mobile }: { mobile: boolean }) {
  return (
    <section style={{
      position: 'relative', height: mobile ? '100svh' : 'calc(100vh)', minHeight: mobile ? 640 : 720, maxHeight: 1100,
      background: `linear-gradient(180deg, ${WHITE} 0%, #EEEEEA 100%)`, overflow: 'hidden',
    }}>
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', alignItems: 'flex-end', justifyContent: mobile ? 'center' : 'flex-end',
        paddingRight: mobile ? 0 : '6vw',
      }}>
        <div style={{ width: mobile ? '100%' : '58%', height: mobile ? '78%' : '92%' }}>
          <AvatarHero height="100%" interactive={false} rotateSpeed={0.5} />
        </div>
      </div>
      <div style={{
        position: 'absolute', left: mobile ? 24 : 60, top: mobile ? 150 : '26%', maxWidth: mobile ? '80%' : 640,
        fontFamily: 'var(--display)', fontWeight: 700, lineHeight: 0.98, letterSpacing: '-0.04em',
        fontSize: mobile ? 'clamp(44px, 12vw, 64px)' : 'clamp(64px, 6.2vw, 104px)',
      }}>
        <div style={{ color: GREY }}>measuring</div>
        <div style={{ color: INK }}>the people you dress</div>
      </div>
      <div style={{ position: 'absolute', left: mobile ? 24 : 60, bottom: mobile ? 28 : 44, ...caps(11, GREY) }}>
        Your shopper · Size M · live 3D
      </div>
    </section>
  );
}

/* ─── Statement ─── */
function Statement({ mobile }: { mobile: boolean }) {
  return (
    <section style={{ background: WHITE, borderTop: `1px solid ${LINE}` }}>
      <div style={{ maxWidth: 1240, margin: '0 auto', padding: mobile ? '120px 24px 128px' : '220px 60px 240px' }}>
        <h1 style={{
          fontFamily: 'var(--display)', fontWeight: 700, color: INK, margin: 0, maxWidth: 1100,
          fontSize: mobile ? 'clamp(36px, 10vw, 54px)' : 'clamp(52px, 5.2vw, 84px)',
          letterSpacing: '-0.04em', lineHeight: 1.0,
        }}>
          We&apos;re a fit and production company based in Amsterdam.
        </h1>
        <p style={{
          fontFamily: 'var(--display)', fontSize: mobile ? 18 : 22, lineHeight: 1.5, color: INK,
          margin: mobile ? '36px 0 48px' : '48px 0 64px', maxWidth: 620,
        }}>
          We measure the people who buy your clothes, and make the next run fit them. Live with La Fam.
        </p>
        <div style={{ display: 'flex', gap: mobile ? 28 : 40, alignItems: 'center', flexWrap: 'wrap' }}>
          <BoxButton href="/start">Start free trial</BoxButton>
          <ArrowLink href="/product">See how it works</ArrowLink>
        </div>
      </div>
    </section>
  );
}

/* ─── Products ─── */
function Products({ mobile }: { mobile: boolean }) {
  return (
    <section style={{ background: PAPER, borderTop: `1px solid ${LINE}` }}>
      <div style={{ maxWidth: 1240, margin: '0 auto', padding: mobile ? '96px 24px 110px' : '160px 60px 180px' }}>
        <h2 style={{
          fontFamily: 'var(--display)', fontWeight: 800, color: INK, margin: mobile ? '0 0 56px' : '0 0 80px',
          fontSize: mobile ? 'clamp(44px, 14vw, 72px)' : 'clamp(56px, 6vw, 96px)', letterSpacing: '-0.045em', lineHeight: 1,
        }}>Our products</h2>

        <div style={{ borderTop: `1px solid ${LINE}` }}>
          {PRODUCTS.map((p, i) => (
            <article key={p.id} style={{
              padding: mobile ? '56px 0 64px' : '96px 0 104px',
              borderBottom: `1px solid ${LINE}`,
              display: 'grid',
              gridTemplateColumns: mobile ? '1fr' : '1fr 0.8fr 1fr',
              gap: mobile ? 28 : 48, alignItems: 'center',
            }}>
              <div>
                <div style={{ ...caps(12, GREY), marginBottom: mobile ? 28 : 36 }}>/0.{i + 1} / Product</div>
                <div style={{
                  fontFamily: 'var(--display)', fontWeight: 800, color: INK,
                  fontSize: mobile ? 'clamp(56px, 17vw, 88px)' : 'clamp(56px, 5.6vw, 96px)',
                  letterSpacing: '-0.045em', lineHeight: 0.95, marginBottom: mobile ? 0 : 36,
                }}>{p.name}</div>
                {!mobile && (
                  <p style={{ fontFamily: 'var(--display)', fontSize: 18, lineHeight: 1.5, color: INK, margin: '0 0 36px', maxWidth: 420 }}>{p.line}</p>
                )}
                {!mobile && <ArrowLink href={p.href} external={'external' in p && !!p.external}>{p.explore}</ArrowLink>}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: mobile ? 220 : 280 }}>
                {p.image ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={p.image} alt="" style={{ maxHeight: mobile ? 260 : 320, maxWidth: '86%', objectFit: 'contain' }} />
                ) : (
                  <div aria-hidden style={{ display: 'flex', alignItems: 'flex-end', gap: mobile ? 14 : 18, height: mobile ? 200 : 260 }}>
                    {[0.25, 0.45, 0.8, 1, 0.6].map((h, k) => (
                      <div key={k} style={{ width: mobile ? 34 : 44, height: `${h * 100}%`, background: '#1E1E24' }} />
                    ))}
                  </div>
                )}
              </div>

              {mobile ? (
                <div>
                  <p style={{ fontFamily: 'var(--display)', fontSize: 17, lineHeight: 1.5, color: INK, margin: '0 0 32px' }}>{p.line}</p>
                  <ArrowLink href={p.href} external={'external' in p && !!p.external}>{p.explore}</ArrowLink>
                </div>
              ) : (
                <div style={{ textAlign: 'right' }}>
                  {'external' in p && p.external ? (
                    <a href={p.href} target="_blank" rel="noopener noreferrer" style={{
                      fontFamily: 'var(--display)', fontWeight: 500, color: INK, textDecoration: 'none',
                      fontSize: 'clamp(36px, 3.4vw, 56px)', letterSpacing: '-0.035em', lineHeight: 1,
                    }}>{p.explore}</a>
                  ) : (
                    <Link href={p.href} style={{
                      fontFamily: 'var(--display)', fontWeight: 500, color: INK, textDecoration: 'none',
                      fontSize: 'clamp(36px, 3.4vw, 56px)', letterSpacing: '-0.035em', lineHeight: 1,
                    }}>{p.explore}</Link>
                  )}
                </div>
              )}
            </article>
          ))}
        </div>

        <p style={{ fontFamily: 'var(--display)', fontSize: 15, color: GREY, marginTop: 36 }}>
          From $19 a month. 30-day free trial on every plan. <Link href="/pricing" style={{ color: INK }}>Pricing →</Link>
        </p>
      </div>
    </section>
  );
}

/* ─── Contact ─── */
function Contact({ mobile }: { mobile: boolean }) {
  return (
    <section style={{ background: DARK, color: '#F4F4F2' }}>
      <div style={{ maxWidth: 1240, margin: '0 auto', padding: mobile ? '120px 24px 130px' : '200px 60px 220px' }}>
        <div style={{
          fontFamily: 'var(--display)', fontWeight: 800, color: '#F4F4F2', margin: mobile ? '0 0 56px' : '0 0 96px',
          fontSize: mobile ? 'clamp(48px, 15vw, 80px)' : 'clamp(40px, 3.6vw, 56px)', letterSpacing: '-0.045em', lineHeight: 1,
        }}>Contact</div>
        <h2 style={{
          fontFamily: 'var(--display)', fontWeight: 500, color: '#F4F4F2', margin: '0 0 56px', maxWidth: 1060,
          fontSize: mobile ? 'clamp(40px, 11.5vw, 60px)' : 'clamp(56px, 6vw, 104px)',
          letterSpacing: '-0.045em', lineHeight: 0.98,
        }}>
          For brands, press, partnerships and production.
        </h2>
        <div style={{ display: 'flex', gap: mobile ? 28 : 40, alignItems: 'center', flexWrap: 'wrap' }}>
          <BoxButton href="/book" light>Get in touch</BoxButton>
          <ArrowLink href="/pricing" light>See pricing</ArrowLink>
        </div>
      </div>
    </section>
  );
}

/* ─── Footer ─── */
const FOOT = [
  { title: 'Navigate', links: [{ label: 'Home', href: '/' }, { label: 'Product', href: '/product' }, { label: 'Pricing', href: '/pricing' }, { label: 'Demo', href: '/demo' }] },
  { title: 'Company', links: [{ label: 'Book a call', href: '/book' }, { label: 'Sign in', href: '/login' }, { label: 'Fravash', href: FRAVASH_URL }] },
  { title: 'Legal', links: [{ label: 'Privacy Policy', href: '/privacy' }] },
];

function Footer({ mobile }: { mobile: boolean }) {
  return (
    <footer style={{ background: PAPER, color: INK }}>
      <div style={{
        maxWidth: 1240, margin: '0 auto', padding: mobile ? '80px 24px 48px' : '120px 60px 64px',
        display: 'grid', gridTemplateColumns: mobile ? '1fr' : '1.4fr 1fr 1fr 1fr', gap: mobile ? 56 : 48,
      }}>
        <div>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/redesign/wordmark.png" alt="TryOn" style={{ height: 26, width: 'auto', display: 'block', marginBottom: 28 }} />
          <p style={{ fontFamily: 'var(--display)', fontSize: mobile ? 18 : 19, lineHeight: 1.5, color: '#5A5A5A', margin: 0, maxWidth: 440 }}>
            We measure the people who buy your clothes, and make the next run fit them.
          </p>
        </div>
        {FOOT.map((col) => (
          <div key={col.title}>
            <div style={{ ...caps(12, GREY), marginBottom: 28 }}>{col.title}</div>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 20 }}>
              {col.links.map((l) => (
                <li key={l.href}>
                  {l.href.startsWith('http') ? (
                    <a href={l.href} target="_blank" rel="noopener noreferrer" style={{ fontFamily: 'var(--display)', fontSize: 18, color: INK, textDecoration: 'none' }}>{l.label}</a>
                  ) : (
                    <Link href={l.href} style={{ fontFamily: 'var(--display)', fontSize: 18, color: INK, textDecoration: 'none' }}>{l.label}</Link>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div style={{ maxWidth: 1240, margin: '0 auto', padding: mobile ? '0 24px 40px' : '0 60px 48px', ...caps(11, GREY) }}>
        TryOn · by Fravash, Amsterdam · 2026
      </div>
    </footer>
  );
}

export function SimpleLanding({ dark: _dark = false }: { dark?: boolean }) {
  const mobile = useIsMobile();
  return (
    <div className="tryon-redesign-root" style={{ width: '100%', background: PAPER, color: INK, colorScheme: 'light' }}>
      <FloatingNav mobile={mobile} />
      <Hero mobile={mobile} />
      <Statement mobile={mobile} />
      <Products mobile={mobile} />
      <Contact mobile={mobile} />
      <Footer mobile={mobile} />
    </div>
  );
}
