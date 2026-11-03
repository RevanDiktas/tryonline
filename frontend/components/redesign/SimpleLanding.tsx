'use client';

import type React from 'react';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { useIsMobile } from './useIsMobile';
import { PLANS } from '@/lib/plans';

/* Home page in the Fravash system (fravash.ai): white, ink #141416, hairline rules #C9C7C2,
   Hanken Grotesk light display set in uppercase, JetBrains Mono eyebrows, pill buttons with
   a "+" and numbered sections. The 3D avatar is the hero, on white. */

const AvatarHero = dynamic(() => import('./AvatarHero').then((m) => m.AvatarHero), { ssr: false });

const INK = '#141416';
const BODY = '#3A3A3F';
const MUTE = '#6E6E73';
const RULE = '#C9C7C2';
const RULE2 = '#E1DFDA';
const WHITE = '#FFFFFF';
const SANS = "'Hanken Grotesk', 'Manrope', system-ui, sans-serif";
const MONO = "'JetBrains Mono', monospace";
const FRAVASH_URL = 'https://fravash.ai';

const mono: React.CSSProperties = { fontFamily: MONO, fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase' };
const disp = (size: string, extra?: React.CSSProperties): React.CSSProperties => ({
  fontFamily: SANS, fontWeight: 400, textTransform: 'uppercase', letterSpacing: '-0.02em', lineHeight: 0.98, margin: 0, fontSize: size, color: INK, ...extra,
});
const body = (size = 18): React.CSSProperties => ({ fontFamily: SANS, fontSize: size, lineHeight: 1.55, color: BODY, margin: 0 });

function Pill({ children, href, external, mobile }: { children: React.ReactNode; href: string; external?: boolean; mobile: boolean }) {
  const [hover, setHover] = useState(false);
  const style: React.CSSProperties = {
    display: 'inline-flex', alignItems: 'center', justifyContent: mobile ? 'space-between' : 'flex-start',
    gap: mobile ? 16 : 28, padding: mobile ? '18px 22px' : '30px 36px',
    border: `1px solid ${INK}`, borderRadius: 999, textDecoration: 'none',
    color: hover ? WHITE : INK, background: hover ? INK : 'transparent',
    fontFamily: SANS, fontSize: mobile ? 16 : 20, lineHeight: 1.25,
    maxWidth: mobile ? 'none' : 460, width: mobile ? '100%' : undefined, boxSizing: 'border-box',
    transition: 'background 160ms, color 160ms',
  };
  const plus = <span style={{ fontSize: mobile ? 22 : 28, lineHeight: 1 }}>+</span>;
  const props = { style, onMouseEnter: () => setHover(true), onMouseLeave: () => setHover(false) };
  if (external) return <a href={href} target="_blank" rel="noopener noreferrer" {...props}><span>{children}</span>{plus}</a>;
  return <Link href={href} {...props}><span>{children}</span>{plus}</Link>;
}

const PlusBox = ({ dark }: { dark?: boolean }) => (
  <span style={{
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 20, height: 20,
    border: `1px solid ${dark ? WHITE : INK}`, fontSize: 13, lineHeight: 1,
  }}>+</span>
);

const Wordmark = () => (
  // eslint-disable-next-line @next/next/no-img-element
  <img src="/redesign/wordmark.png" alt="TryOn" style={{ height: 18, width: 'auto', display: 'block' }} />
);

/* ─── Header: the Fravash grid, on white ─── */
const NAV_PAIRS = [
  { href: '#s01', a: '01 The problem', b: '02 The answer' },
  { href: '#s03', a: '03 Production', b: '04 Pricing' },
  { href: '#s05', a: '05 Where this goes', b: '06 Contact' },
];

function Header({ mobile }: { mobile: boolean }) {
  const cell: React.CSSProperties = { borderRight: `1px solid ${RULE}`, display: 'flex', alignItems: 'center' };
  return (
    <header style={{ width: '100%', borderBottom: `1px solid ${RULE}` }}>
      <div style={{ display: 'grid', gridTemplateColumns: mobile ? '1fr auto auto' : 'minmax(220px, 2.2fr) repeat(3, minmax(0, 1fr)) minmax(0, 1fr) auto' }}>
        <Link href="/" style={{ ...cell, gap: 14, padding: mobile ? '18px 20px' : '24px 32px', textDecoration: 'none', color: INK, fontFamily: SANS, fontSize: 17, lineHeight: 1.15 }}>
          <Wordmark />
          {!mobile && <span style={{ opacity: 0.75 }}>Size and body data</span>}
        </Link>
        {!mobile && NAV_PAIRS.map((n) => (
          <a key={n.href} href={n.href} style={{ ...cell, ...mono, flexDirection: 'column', alignItems: 'flex-start', justifyContent: 'center', gap: 6, padding: '18px 24px', color: 'rgba(20,20,22,0.7)', textDecoration: 'none' }}>
            <span>{n.a}</span><span>{n.b}</span>
          </a>
        ))}
        <Link href="/login" style={{ ...cell, ...mono, flexDirection: mobile ? 'row' : 'column', alignItems: mobile ? 'center' : 'flex-start', justifyContent: 'center', gap: 6, padding: mobile ? '0 18px' : '18px 24px', color: 'rgba(20,20,22,0.7)', textDecoration: 'none' }}>
          <span>Log in</span>{!mobile && <span style={{ opacity: 0.6 }}>Brand dashboard</span>}
        </Link>
        <Link href="/start" style={{ ...mono, display: 'inline-flex', alignItems: 'center', gap: 12, padding: mobile ? '0 20px' : '0 32px', color: INK, textDecoration: 'none', whiteSpace: 'nowrap' }}>
          Start <PlusBox />
        </Link>
      </div>
    </header>
  );
}

/* ─── Sticky status bar ─── */
const SECTIONS = ['Home', 'The problem', 'The answer', 'Production', 'Pricing', 'Where this goes', 'Contact'];
function StatusBar({ mobile, section }: { mobile: boolean; section: string }) {
  const cell: React.CSSProperties = { padding: mobile ? '13px 16px' : '20px 32px', borderRight: `1px solid ${RULE}`, display: 'flex', alignItems: 'center', gap: mobile ? 10 : 14, ...mono, color: INK };
  return (
    <div aria-hidden style={{
      position: 'sticky', top: 0, zIndex: 5, background: 'rgba(255,255,255,0.86)', backdropFilter: 'blur(18px)', WebkitBackdropFilter: 'blur(18px)',
      borderBottom: `1px solid ${RULE}`, display: 'grid',
      gridTemplateColumns: mobile ? 'auto 1fr auto' : 'minmax(220px, 2.2fr) minmax(0, 1fr) minmax(0, 1.2fr) auto',
    }}>
      <span style={{ ...cell, fontFamily: SANS, fontSize: 15, letterSpacing: 0, textTransform: 'none' }}><Wordmark /></span>
      {!mobile && <span style={cell}><span style={{ opacity: 0.65 }}>Page:</span><span>Home</span></span>}
      <span style={cell}><span style={{ opacity: 0.65 }}>Section:</span><span>{section}</span></span>
      <Link href="/start" style={{ ...cell, borderRight: 0, textDecoration: 'none' }}>Start <PlusBox /></Link>
    </div>
  );
}

/* ─── Hero: the avatar, on white ─── */
function Hero({ mobile }: { mobile: boolean }) {
  return (
    <section id="top" style={{ position: 'relative', width: '100%', minHeight: mobile ? '100svh' : '100vh', background: WHITE, color: INK, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Header mobile={mobile} />
      <div style={{
        position: 'relative', flex: '1 1 auto',
        display: 'grid', gridTemplateColumns: mobile ? '1fr' : 'minmax(0, 1fr) minmax(0, 1fr)',
        alignItems: 'center', gap: mobile ? 8 : 32,
        padding: mobile ? '40px 20px 0' : '40px 64px 0',
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: mobile ? 20 : 32, paddingBottom: mobile ? 0 : 48 }}>
          <h1 style={disp(mobile ? 'clamp(38px, 11.5vw, 54px)' : 'clamp(40px, 5.2vw, 84px)')}>TryOn<br />Size and body data<br />for fashion brands</h1>
          <p style={{ ...body(mobile ? 16 : 18), maxWidth: mobile ? 340 : 560 }}>
            A size button on every product. Your customers&apos; measurements, every month. The next run graded to them. Live with La Fam Amsterdam.
          </p>
          <div style={{ display: 'flex', gap: 28, alignItems: 'center', flexWrap: 'wrap' }}>
            <Link href="/start" style={{ ...mono, display: 'inline-flex', alignItems: 'center', gap: 12, color: INK, textDecoration: 'none' }}>Start free trial <PlusBox /></Link>
            <Link href="/product" style={{ ...mono, color: MUTE, textDecoration: 'none' }}>How it works</Link>
          </div>
        </div>
        <div style={{ position: 'relative', height: mobile ? '54vh' : 'calc(100vh - 160px)', minHeight: mobile ? 380 : 560, maxHeight: 900 }}>
          <AvatarHero height="100%" interactive={false} rotateSpeed={0.6} />
          <div aria-hidden style={{ position: 'absolute', bottom: 12, left: 0, right: 0, textAlign: 'center', ...mono, color: MUTE }}>Your shopper · Size M · live 3D</div>
        </div>
      </div>
    </section>
  );
}

/* ─── Sections ─── */
function Pad({ children, mobile, style }: { children: React.ReactNode; mobile: boolean; style?: React.CSSProperties }) {
  return <div style={{ padding: mobile ? '72px 20px 64px' : '128px 64px 112px', boxSizing: 'border-box', ...style }}>{children}</div>;
}

function Two({ left, right, mobile, cols = 'minmax(0, 1fr) minmax(0, 2fr)', align = 'start' }: { left: React.ReactNode; right: React.ReactNode; mobile: boolean; cols?: string; align?: string }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: mobile ? '1fr' : cols, gap: mobile ? 28 : 48, alignItems: mobile ? 'start' : align }}>
      {left}{right}
    </div>
  );
}

function Problem({ mobile }: { mobile: boolean }) {
  return (
    <section id="s01" data-sec="The problem" style={{ background: WHITE }}>
      <Pad mobile={mobile}>
        <Two mobile={mobile}
          left={<span style={{ ...mono, color: MUTE }}>01 — The problem</span>}
          right={
            <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
              <h2 style={disp(mobile ? '30px' : 'clamp(32px, 4.4vw, 64px)')}>A brand knows who buys and where they live but not what they measure</h2>
              <p style={{ ...body(), maxWidth: 640 }}>So the size chart is a guess, the grading is a compromise, and every drop is cut in a size run copied from the last one. The returns say which sizes were wrong. Nobody says which bodies.</p>
            </div>
          }
        />
      </Pad>
    </section>
  );
}

function Answer({ mobile }: { mobile: boolean }) {
  const items = [
    { k: 'Size', v: 'A Find my size button on every product. Seven questions, no account, every size scored as a match. Sold out in theirs? They see the next best.' },
    { k: 'Try-On', v: 'Photoreal 3D try-on on the shopper’s own body, with real cloth. One photo makes the avatar. Works where you have a 3D garment.' },
    { k: 'Report', v: 'Once a month: your customers’ measurements, the sizes that don’t fit them, and the size run for the next drop.' },
  ];
  return (
    <section id="s02" data-sec="The answer" style={{ background: WHITE }}>
      <div style={{ padding: mobile ? '72px 20px 0' : '112px 64px 0', boxSizing: 'border-box' }}>
        <p style={disp(mobile ? '20px' : 'clamp(22px, 2.6vw, 36px)', { marginBottom: mobile ? 12 : 20 })}>The answer is</p>
        <h2 style={disp(mobile ? 'clamp(52px, 15vw, 72px)' : 'clamp(56px, 9.6vw, 150px)', { letterSpacing: '-0.04em' })}>One button</h2>
        <div style={{ borderTop: `1px solid ${RULE}`, marginTop: 48 }} />
        <div style={{ padding: mobile ? '40px 0 0' : '88px 0 0' }}>
          <p style={{ margin: 0, maxWidth: 1100, fontFamily: SANS, fontSize: mobile ? 21 : 'clamp(24px, 2.9vw, 42px)', lineHeight: mobile ? 1.3 : 1.25, letterSpacing: '-0.02em', color: INK }}>
            One button in your Shopify theme. Shoppers get their size in 30 seconds. You get, every month, what the people who buy from you measure, which of your sizes don&apos;t fit them, and how many of each size to make next.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: mobile ? '1fr' : 'minmax(0, 1fr) minmax(0, 1.4fr)', gap: 48, alignItems: 'end', padding: mobile ? '40px 0 48px' : '96px 0 0' }}>
            <Pill href="/product" mobile={mobile}>See how a size check runs, from question to cart</Pill>
            <div style={{ position: 'relative', aspectRatio: '16 / 9', background: WHITE, overflow: 'hidden', border: `1px solid ${RULE2}` }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/redesign/widget.jpg" alt="The Find my size button on a product page" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>
          </div>
        </div>
      </div>
      <div style={{ padding: mobile ? '48px 20px 0' : '96px 64px 0', boxSizing: 'border-box' }}>
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gridTemplateColumns: mobile ? '1fr' : 'repeat(3, minmax(0, 1fr))', gap: 0, borderTop: `1px solid ${RULE}` }}>
          {items.map((it, i) => (
            <li key={it.k} style={{
              padding: mobile ? '24px 0 28px' : i === 0 ? '32px 32px 40px 0' : i === 2 ? '32px 0 40px 32px' : '32px 32px 40px',
              borderRight: !mobile && i < 2 ? `1px solid ${RULE2}` : 0,
              borderBottom: mobile && i < 2 ? `1px solid ${RULE2}` : 0,
              display: 'flex', flexDirection: 'column', gap: 12,
            }}>
              <span style={{ ...mono, color: MUTE }}>{it.k}</span>
              <span style={{ fontFamily: SANS, fontSize: 17, color: BODY, lineHeight: 1.5 }}>{it.v}</span>
            </li>
          ))}
        </ul>
      </div>
      <div style={{ height: mobile ? 64 : 112 }} />
    </section>
  );
}

function Production({ mobile }: { mobile: boolean }) {
  return (
    <section id="s03" data-sec="Production" style={{ background: WHITE, borderTop: `1px solid ${RULE}` }}>
      <div style={{ display: 'grid', gridTemplateColumns: mobile ? '1fr' : 'minmax(0, 1fr) minmax(0, 1fr)', gap: mobile ? 28 : '48px 96px', padding: mobile ? '72px 20px 64px' : '128px 64px 112px', boxSizing: 'border-box' }}>
        <h2 style={disp(mobile ? '28px' : 'clamp(28px, 3.4vw, 48px)')}>Then we make it and the data goes to the factory not a dashboard</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <p style={disp(mobile ? '20px' : 'clamp(20px, 2vw, 28px)')}>This is where the measurements go</p>
          <p style={body()}>Send us the design and the size run. We source the fabric, make the sample, grade it to your customers and ship the order. Denim first, through Fravash, our sourcing and production company in Amsterdam.</p>
          <div style={{ paddingTop: 12 }}>
            <Pill href={FRAVASH_URL} external mobile={mobile}>Production by Fravash</Pill>
          </div>
        </div>
      </div>
    </section>
  );
}

function Pricing({ mobile }: { mobile: boolean }) {
  const rows = PLANS.filter((p) => ['size_pro', 'try_on', 'insights'].includes(p.id)).map((p) => ({ k: `${p.name} · ${p.price}/mo`, v: p.pitch }));
  rows.push({ k: 'Production', v: 'On request, through Fravash. Priced per order.' });
  return (
    <section id="s04" data-sec="Pricing" style={{ background: WHITE, borderTop: `1px solid ${RULE}` }}>
      <div style={{ display: 'grid', gridTemplateColumns: mobile ? '1fr' : 'minmax(0, 1fr) minmax(0, 1.4fr)', gap: mobile ? 28 : '48px 96px', padding: mobile ? '72px 20px 64px' : '112px 64px', boxSizing: 'border-box' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <h2 style={disp(mobile ? '28px' : 'clamp(28px, 3.4vw, 48px)')}>Less than one return a day<br />30-day free trial on every plan</h2>
          <div><Pill href="/pricing" mobile={mobile}>See full pricing</Pill></div>
        </div>
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', borderTop: `1px solid ${RULE}` }}>
          {rows.map((r) => (
            <li key={r.k} style={{ display: 'grid', gridTemplateColumns: mobile ? '1fr' : 'minmax(0, 1fr) minmax(0, 2.2fr)', gap: mobile ? 8 : '16px 32px', padding: '24px 0', borderBottom: `1px solid ${RULE}` }}>
              <span style={{ ...mono, color: INK }}>{r.k}</span>
              <span style={{ fontFamily: SANS, fontSize: 17, color: BODY }}>{r.v}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function Vision({ mobile }: { mobile: boolean }) {
  return (
    <section id="s05" data-sec="Where this goes" style={{ background: WHITE }}>
      <div style={{ padding: mobile ? '72px 20px 0' : '128px 64px 0', boxSizing: 'border-box' }}>
        <h2 style={disp(mobile ? 'clamp(44px, 12.5vw, 64px)' : 'clamp(48px, 8vw, 120px)', { letterSpacing: '-0.04em' })}>Fit by measurement</h2>
        <div style={{ borderTop: `1px solid ${RULE}`, marginTop: 48 }} />
        <div style={{ display: 'grid', gridTemplateColumns: mobile ? '1fr' : 'minmax(0, 1fr) minmax(0, 1.4fr)', gap: 48, padding: mobile ? '36px 0 72px' : '72px 0 112px' }}>
          <span style={{ ...mono, color: MUTE }}>05 — Vision</span>
          <p style={{ margin: 0, maxWidth: 760, fontFamily: SANS, fontSize: mobile ? 18 : 'clamp(20px, 2.2vw, 30px)', lineHeight: mobile ? 1.4 : 1.35, letterSpacing: '-0.015em', color: INK }}>
            Clothes are still cut to a size chart written before anyone bought them. We start with one button that measures the shopper. The goal is a size run for every drop that comes from the people who will wear it, and a factory that cuts to it. Every scan today teaches the next run.
          </p>
        </div>
      </div>
    </section>
  );
}

function Contact({ mobile }: { mobile: boolean }) {
  return (
    <section id="s06" data-sec="Contact" style={{ background: WHITE, borderTop: `1px solid ${RULE}` }}>
      <div style={{ display: 'grid', gridTemplateColumns: mobile ? '1fr' : 'minmax(0, 1.4fr) minmax(0, 1fr)', gap: 48, alignItems: 'end', padding: mobile ? '72px 20px 56px' : '112px 64px 96px', boxSizing: 'border-box' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <span style={{ ...mono, color: MUTE }}>06 — Contact</span>
          <h2 style={disp(mobile ? 'clamp(40px, 11.5vw, 60px)' : 'clamp(40px, 6vw, 96px)', { letterSpacing: '-0.03em' })}>Put the button on one product</h2>
          <p style={{ ...body(), maxWidth: 560 }}>Install from the Shopify theme editor, no code. Thirty days free on every plan. For brands, press and production, write to hello@tryon.global.</p>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, alignItems: mobile ? 'stretch' : 'flex-end' }}>
          <Pill href="/start" mobile={mobile}>Start free trial</Pill>
          <Pill href="/book" mobile={mobile}>Book a call</Pill>
        </div>
      </div>
    </section>
  );
}

function Footer({ mobile }: { mobile: boolean }) {
  const cell: React.CSSProperties = { padding: mobile ? '14px 20px' : '20px 32px', borderRight: `1px solid ${RULE}`, display: 'flex', alignItems: 'center', gap: 14, ...mono, color: INK, textDecoration: 'none' };
  return (
    <footer style={{ borderTop: `1px solid ${RULE}`, background: WHITE }}>
      <div style={{ display: 'grid', gridTemplateColumns: mobile ? '1fr 1fr' : 'minmax(220px, 2.2fr) repeat(4, minmax(0, 1fr))' }}>
        <span style={{ ...cell, fontFamily: SANS, fontSize: 15, letterSpacing: 0, textTransform: 'none', gridColumn: mobile ? '1 / -1' : undefined, borderBottom: mobile ? `1px solid ${RULE}` : 0 }}><Wordmark /><span style={{ opacity: 0.65 }}>by Fravash, Amsterdam</span></span>
        <Link href="/product" style={cell}>Product</Link>
        <Link href="/pricing" style={cell}>Pricing</Link>
        <Link href="/privacy" style={cell}>Privacy</Link>
        <a href={FRAVASH_URL} target="_blank" rel="noopener noreferrer" style={{ ...cell, borderRight: 0 }}>fravash.ai</a>
      </div>
    </footer>
  );
}

export function SimpleLanding({ dark: _dark = false }: { dark?: boolean }) {
  const mobile = useIsMobile();
  const [section, setSection] = useState('Home');

  useEffect(() => {
    const els = Array.from(document.querySelectorAll<HTMLElement>('[data-sec]'));
    if (!els.length || !('IntersectionObserver' in window)) return;
    const io = new IntersectionObserver((entries) => {
      const hit = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (hit) setSection((hit.target as HTMLElement).dataset.sec || 'Home');
    }, { rootMargin: '-40% 0px -50% 0px', threshold: [0, 0.2, 0.5] });
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  return (
    <div style={{ width: '100%', background: WHITE, color: INK, fontFamily: SANS, fontSize: 17, lineHeight: 1.5, colorScheme: 'light' }}>
      {/* eslint-disable-next-line @next/next/no-page-custom-font */}
      <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@300;400;500&family=JetBrains+Mono:wght@400;500&display=swap" />
      <div data-sec="Home"><Hero mobile={mobile} /></div>
      <StatusBar mobile={mobile} section={SECTIONS.includes(section) ? section : 'Home'} />
      <Problem mobile={mobile} />
      <Answer mobile={mobile} />
      <Production mobile={mobile} />
      <Pricing mobile={mobile} />
      <Vision mobile={mobile} />
      <Contact mobile={mobile} />
      <Footer mobile={mobile} />
    </div>
  );
}
