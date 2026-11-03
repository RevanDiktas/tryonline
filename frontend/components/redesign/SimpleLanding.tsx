'use client';

import type React from 'react';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { useIsMobile } from './useIsMobile';
import { PLANS } from '@/lib/plans';

/* TryOn home. White. Ink and one cobalt. Mono eyebrows, sentence-case headlines set tight,
   pill buttons. The 3D avatar, the La Fam launch film and two shots of the try-on are the only pictures.
   One ink section, one cobalt section. Nothing else. */

const AvatarHero = dynamic(() => import('./AvatarHero').then((m) => m.AvatarHero), { ssr: false });

const INK = '#0A0A0A';
const GREY = '#6E6E73';
const SOFT = '#A1A1A6';
const WHITE = '#FFFFFF';
const COBALT = '#0040FF';
const RULE = 'rgba(10,10,10,0.10)';
const SANS = "'Hanken Grotesk', 'Manrope', system-ui, sans-serif";
const MONO = "'JetBrains Mono', monospace";
const FRAVASH_URL = 'https://fravash.ai';

const CSS = `
@keyframes up{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
.up{animation:up .9s cubic-bezier(.2,.7,.2,1) both}.d1{animation-delay:.08s}.d2{animation-delay:.2s}.d3{animation-delay:.32s}
.rv{opacity:0;transform:translateY(14px);transition:opacity .8s cubic-bezier(.2,.7,.2,1),transform .8s cubic-bezier(.2,.7,.2,1)}
.rv.in{opacity:1;transform:none}.rv-1{transition-delay:.1s}.rv-2{transition-delay:.2s}.rv-3{transition-delay:.3s}
.pill{transition:transform .16s cubic-bezier(.2,.7,.2,1),opacity .16s}.pill:hover{transform:translateY(-1px)}
.lnk{transition:color .16s}.lnk:hover{color:#0A0A0A !important}
@media (prefers-reduced-motion: reduce){.up,.rv{animation:none !important;opacity:1 !important;transform:none !important;transition:none !important}}
`;

function useReveal() {
  useEffect(() => {
    const els = Array.from(document.querySelectorAll<HTMLElement>('.rv'));
    if (!els.length) return;
    if (!('IntersectionObserver' in window)) { els.forEach((e) => e.classList.add('in')); return; }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.1 });
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);
}

const eyebrow = (color = GREY): React.CSSProperties => ({ fontFamily: MONO, fontSize: 12, letterSpacing: '0.18em', textTransform: 'uppercase', color, fontWeight: 500 });
const head = (size: string, color = INK): React.CSSProperties => ({ fontFamily: SANS, fontWeight: 600, fontSize: size, letterSpacing: '-0.035em', lineHeight: 1.02, margin: 0, color });
const text = (size = 20, color = GREY): React.CSSProperties => ({ fontFamily: SANS, fontSize: size, lineHeight: 1.45, color, margin: 0, letterSpacing: '-0.01em' });

function Pill({ children, href, kind = 'solid', on = 'light', external }: { children: React.ReactNode; href: string; kind?: 'solid' | 'outline' | 'white'; on?: 'light' | 'dark'; external?: boolean }) {
  const look: Record<string, React.CSSProperties> = {
    solid: { background: COBALT, color: WHITE, border: `1px solid ${COBALT}` },
    outline: { background: 'transparent', color: on === 'light' ? INK : WHITE, border: `1px solid ${on === 'light' ? 'rgba(10,10,10,0.22)' : 'rgba(255,255,255,0.4)'}` },
    white: { background: WHITE, color: INK, border: `1px solid ${WHITE}` },
  };
  const style: React.CSSProperties = { ...look[kind], display: 'inline-flex', alignItems: 'center', justifyContent: 'center', padding: '15px 28px', borderRadius: 999, textDecoration: 'none', fontFamily: SANS, fontSize: 16, fontWeight: 500, letterSpacing: '-0.01em', lineHeight: 1 };
  if (external) return <a className="pill" href={href} target="_blank" rel="noopener noreferrer" style={style}>{children}</a>;
  return <Link className="pill" href={href} style={style}>{children}</Link>;
}

const Wrap = ({ children, mobile, pad = 'section' }: { children: React.ReactNode; mobile: boolean; pad?: 'section' | 'none' }) => (
  <div style={{ maxWidth: 1320, margin: '0 auto', padding: pad === 'none' ? (mobile ? '0 20px' : '0 48px') : (mobile ? '88px 20px' : '160px 48px') }}>{children}</div>
);

/* ─── Nav ─── */
function Nav({ mobile }: { mobile: boolean }) {
  const [open, setOpen] = useState(false);
  const links = [{ label: 'How it works', href: '#how' }, { label: '3D', href: '#tryon' }, { label: 'The report', href: '#report' }, { label: 'Production', href: '#production' }, { label: 'Pricing', href: '/pricing' }];
  return (
    <header style={{ background: 'rgba(255,255,255,0.86)', backdropFilter: 'blur(14px)', WebkitBackdropFilter: 'blur(14px)', position: 'sticky', top: 0, zIndex: 20 }}>
      <div style={{ maxWidth: 1320, margin: '0 auto', padding: mobile ? '16px 20px' : '22px 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 24 }}>
        <Link href="/" aria-label="TryOn home" style={{ display: 'flex', alignItems: 'center' }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/redesign/wordmark.png" alt="TryOn" style={{ height: mobile ? 20 : 22, width: 'auto', display: 'block' }} />
        </Link>
        {!mobile ? (
          <nav style={{ display: 'flex', alignItems: 'center', gap: 34 }}>
            {links.map((l) => <a key={l.href} href={l.href} className="lnk" style={{ fontFamily: SANS, fontSize: 17, color: GREY, textDecoration: 'none', letterSpacing: '-0.01em' }}>{l.label}</a>)}
            <Pill href="/book" kind="outline">Contact</Pill>
            <Pill href="/start">Start free trial</Pill>
          </nav>
        ) : (
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <Pill href="/start">Start</Pill>
            <button type="button" aria-label={open ? 'Close menu' : 'Menu'} onClick={() => setOpen((o) => !o)} style={{ width: 44, height: 44, borderRadius: 999, border: '1px solid rgba(10,10,10,0.22)', background: 'transparent', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ width: 16 }}><span style={{ display: 'block', height: 1.5, background: INK, marginBottom: 4 }} /><span style={{ display: 'block', height: 1.5, background: INK, marginBottom: 4 }} /><span style={{ display: 'block', height: 1.5, background: INK }} /></span>
            </button>
          </div>
        )}
      </div>
      {mobile && open && (
        <nav style={{ padding: '4px 20px 28px', display: 'flex', flexDirection: 'column', gap: 16, background: WHITE }}>
          {[...links, { label: 'Contact', href: '/book' }, { label: 'Sign in', href: '/login' }].map((l) => (
            <a key={l.href} href={l.href} onClick={() => setOpen(false)} style={{ fontFamily: SANS, fontSize: 26, fontWeight: 500, color: INK, textDecoration: 'none', letterSpacing: '-0.025em' }}>{l.label}</a>
          ))}
        </nav>
      )}
    </header>
  );
}

/* ─── Hero ─── */
function Hero({ mobile }: { mobile: boolean }) {
  return (
    <section style={{ background: WHITE }}>
      <div style={{ maxWidth: 1320, margin: '0 auto', padding: mobile ? '28px 20px 0' : '48px 48px 0', display: 'grid', gridTemplateColumns: mobile ? '1fr' : '1.05fr 1fr', gap: mobile ? 16 : 40, alignItems: 'center' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: mobile ? 20 : 28, paddingBottom: mobile ? 0 : 56 }}>
          <div className="up" style={eyebrow()}>TryOn · Amsterdam</div>
          <h1 className="up d1" style={head(mobile ? 'clamp(40px, 11vw, 56px)' : 'clamp(52px, 5.4vw, 92px)')}>Clothes made for the bodies that buy them.</h1>
          <p className="up d2" style={{ ...text(mobile ? 18 : 22), maxWidth: 540 }}>One button measures your shoppers. The next run is cut to them.</p>
          <div className="up d3" style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <Pill href="/start">Start free trial</Pill>
            <Pill href="#how" kind="outline">How it works</Pill>
          </div>
        </div>
        <div className="up d2" style={{ position: 'relative', height: mobile ? '54vh' : 'calc(100vh - 180px)', minHeight: mobile ? 380 : 560, maxHeight: 820 }}>
          <AvatarHero height="100%" interactive={false} rotateSpeed={0.6} />
        </div>
      </div>
      <div style={{ maxWidth: 1320, margin: '0 auto', padding: mobile ? '36px 20px 0' : '40px 48px 0', display: 'flex', alignItems: 'center', gap: mobile ? 24 : 48, flexWrap: 'wrap' }}>
        <span style={eyebrow(SOFT)}>Live with</span>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/partners/lafam.webp" alt="La Fam Amsterdam" className="rv" style={{ height: mobile ? 40 : 56, width: 'auto', objectFit: 'contain', display: 'block' }} />
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/partners/ramin.webp" alt="Ramin Studios" className="rv rv-1" style={{ height: mobile ? 13 : 18, width: 'auto', objectFit: 'contain', display: 'block' }} />
      </div>
    </section>
  );
}

/* ─── How it works: the film, and three lines ─── */
const STEPS = [
  { n: '01', t: 'Tap Find my size' },
  { n: '02', t: 'Seven questions. No account.' },
  { n: '03', t: 'Every size, scored. Add the right one to cart.' },
];
function How({ mobile }: { mobile: boolean }) {
  return (
    <section id="how" style={{ background: WHITE }}>
      <div style={{ maxWidth: 1320, margin: '0 auto', padding: mobile ? '88px 20px' : '170px 48px 150px', display: 'grid', gridTemplateColumns: mobile ? '1fr' : '1fr 1fr', gap: mobile ? 44 : 64, alignItems: 'center' }}>
        <div>
          <div className="rv" style={eyebrow()}>On the product page</div>
          <h2 className="rv rv-1" style={{ ...head(mobile ? 'clamp(34px, 9.5vw, 48px)' : 'clamp(44px, 4.4vw, 72px)'), marginTop: 18, maxWidth: 560 }}>Your size in 30 seconds.</h2>
          <ol style={{ listStyle: 'none', margin: mobile ? '36px 0 0' : '56px 0 0', padding: 0, display: 'flex', flexDirection: 'column', gap: mobile ? 22 : 28 }}>
            {STEPS.map((s, i) => (
              <li key={s.n} className={`rv rv-${i + 1}`} style={{ display: 'grid', gridTemplateColumns: '40px 1fr', gap: 14, alignItems: 'baseline' }}>
                <span style={{ ...eyebrow(i === 2 ? COBALT : SOFT), fontSize: 12 }}>{s.n}</span>
                <span style={{ fontFamily: SANS, fontSize: mobile ? 22 : 28, fontWeight: 500, letterSpacing: '-0.025em', color: INK, lineHeight: 1.15 }}>{s.t}</span>
              </li>
            ))}
          </ol>
          <p className="rv rv-3" style={{ ...text(mobile ? 16 : 18), marginTop: mobile ? 32 : 48, maxWidth: 460 }}>Live on lafamamsterdam.com. One photo upgrades the answer to a measured size and a 3D avatar.</p>
        </div>
        <div className="rv rv-1" style={{ display: 'flex', justifyContent: 'center' }}>
          <video autoPlay muted loop playsInline poster="/redesign/lafam-launch.jpg" aria-label="TryOn on the La Fam product page" style={{ width: '100%', maxWidth: mobile ? 340 : 440, height: 'auto', display: 'block', background: WHITE }}>
            <source src="/redesign/lafam-launch.mp4" type="video/mp4" />
          </video>
        </div>
      </div>
    </section>
  );
}

/* ─── The 3D try-on ─── */
const TECH = [
  { k: 'One passport, every brand', d: 'A shopper measures once. Their fit passport works in every store that runs TryOn. New customers arrive already sized.' },
  { k: '3D cloth physics', d: 'The garment is simulated on the customer\u2019s body, not pasted on a photo. You see where it pulls and where it hangs.' },
  { k: 'Agentic fit API', d: 'The same size answer, for AI shopping agents. Already live as an MCP for Claude and ChatGPT.' },
];
function ThreeD({ mobile }: { mobile: boolean }) {
  return (
    <section id="tryon" style={{ background: WHITE }}>
      <div style={{ maxWidth: 1320, margin: '0 auto', padding: mobile ? '0 20px 88px' : '0 48px 150px' }}>
        <div className="rv" style={eyebrow()}>The 3D try-on</div>
        <h2 className="rv rv-1" style={{ ...head(mobile ? 'clamp(34px, 9.5vw, 48px)' : 'clamp(44px, 4.4vw, 72px)'), marginTop: 18, maxWidth: 760 }}>Your clothes on their body. Real cloth.</h2>
        <div style={{ display: 'grid', gridTemplateColumns: mobile ? '1fr' : '1.9fr 1fr', gap: mobile ? 20 : 32, marginTop: mobile ? 36 : 64, alignItems: 'stretch' }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="rv rv-1" src="/redesign/ramin-widget.jpg" alt="TryOn open on a Ramin product page: the shopper\u2019s avatar in the hoodie, measurements and recommended size" style={{ width: '100%', height: 'auto', display: 'block', borderRadius: 16, border: `1px solid ${RULE}` }} />
          <div className="rv rv-2" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: 16, border: `1px solid ${RULE}`, overflow: 'hidden', minHeight: mobile ? 360 : 0 }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/redesign/avatar-render.jpg" alt="A measured avatar wearing a simulated black hoodie and sweatpants" style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block', maxHeight: mobile ? 420 : 'none' }} />
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: mobile ? '1fr' : 'repeat(3, 1fr)', gap: mobile ? 32 : 48, marginTop: mobile ? 48 : 80 }}>
          {TECH.map((t, i) => (
            <div key={t.k} className={`rv rv-${i + 1}`} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <span style={eyebrow(i === 2 ? COBALT : GREY)}>{t.k}</span>
              <span style={{ ...text(mobile ? 17 : 19, INK), maxWidth: 360 }}>{t.d}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── The report: ink ─── */
const OUT = [
  { k: 'Measurements', v: 'chest · waist · hips · height', d: 'Of the people who buy, not a size chart.' },
  { k: 'Sizes that miss', v: 'M · 27 %', d: 'Which of your sizes nobody fits, and how many of them.' },
  { k: 'Next run', v: 'S 12 · M 41 · L 35 · XL 12', d: 'How many of each size to make for the next drop.' },
];
function Report({ mobile }: { mobile: boolean }) {
  return (
    <section id="report" style={{ background: INK, color: WHITE }}>
      <Wrap mobile={mobile}>
        <div className="rv" style={eyebrow('rgba(255,255,255,0.5)')}>The report · monthly</div>
        <h2 className="rv rv-1" style={{ ...head(mobile ? 'clamp(34px, 9.5vw, 48px)' : 'clamp(44px, 4.6vw, 76px)', WHITE), marginTop: 18, maxWidth: 820 }}>A different body behind every order.</h2>
        <div style={{ display: 'grid', gridTemplateColumns: mobile ? '1fr' : 'repeat(3, 1fr)', gap: mobile ? 40 : 48, marginTop: mobile ? 56 : 112 }}>
          {OUT.map((o, i) => (
            <div key={o.k} className={`rv rv-${i + 1}`} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <span style={{ ...eyebrow('rgba(255,255,255,0.5)') }}>{o.k}</span>
              <span style={{ fontFamily: MONO, fontSize: mobile ? 20 : 24, color: '#7D97FF', letterSpacing: '-0.01em', lineHeight: 1.2 }}>{o.v}</span>
              <span style={{ ...text(mobile ? 16 : 17, 'rgba(255,255,255,0.65)'), maxWidth: 320 }}>{o.d}</span>
            </div>
          ))}
        </div>
      </Wrap>
    </section>
  );
}

/* ─── Where this goes ─── */
function Vision({ mobile }: { mobile: boolean }) {
  return (
    <section id="production" style={{ background: WHITE }}>
      <Wrap mobile={mobile}>
        <div className="rv" style={eyebrow()}>Where this goes</div>
        <h2 className="rv rv-1" style={{ ...head(mobile ? 'clamp(44px, 13vw, 72px)' : 'clamp(64px, 8vw, 140px)'), marginTop: 18, letterSpacing: '-0.045em' }}>Measured.<br />Then made.</h2>
        <div style={{ display: 'grid', gridTemplateColumns: mobile ? '1fr' : '1fr 1.2fr', gap: mobile ? 28 : 64, marginTop: mobile ? 36 : 72, alignItems: 'start' }}>
          <p className="rv rv-2" style={{ ...text(mobile ? 19 : 26, INK), maxWidth: 620, letterSpacing: '-0.02em' }}>The size run goes to Fravash, our production company. The next drop comes back cut to your customers. Denim first.</p>
          <div className="rv rv-3" style={{ display: 'flex', flexDirection: 'column', gap: 28, alignItems: mobile ? 'flex-start' : 'flex-end' }}>
            <p style={{ ...text(mobile ? 16 : 18), maxWidth: 400, textAlign: mobile ? 'left' : 'right' }}>Clothes are cut to a chart written before anyone bought them. We cut to the people who did. Every scan teaches the next run.</p>
            <Pill href={FRAVASH_URL} kind="outline" external>Production by Fravash</Pill>
          </div>
        </div>
      </Wrap>
    </section>
  );
}

/* ─── Pricing ─── */
function Pricing({ mobile }: { mobile: boolean }) {
  const short: Record<string, string> = { size_pro: 'The button. No 3D.', try_on: 'Your clothes on their body.', insights: 'Try-On plus the monthly report.' };
  const rows = PLANS.filter((p) => ['size_pro', 'try_on', 'insights'].includes(p.id));
  return (
    <section style={{ background: WHITE, borderTop: `1px solid ${RULE}` }}>
      <div style={{ maxWidth: 1320, margin: '0 auto', padding: mobile ? '88px 20px' : '140px 48px', display: 'grid', gridTemplateColumns: mobile ? '1fr' : '1fr 1.3fr', gap: mobile ? 40 : 64, alignItems: 'start' }}>
        <div>
          <div className="rv" style={eyebrow()}>Pricing</div>
          <h2 className="rv rv-1" style={{ ...head(mobile ? 'clamp(32px, 9vw, 44px)' : 'clamp(40px, 4vw, 60px)'), marginTop: 18 }}>Less than one return a day.</h2>
          <p className="rv rv-2" style={{ ...text(mobile ? 16 : 19), marginTop: 16 }}>Thirty days free on every plan.</p>
          <div className="rv rv-2" style={{ marginTop: 28 }}><Pill href="/pricing" kind="outline">See full pricing</Pill></div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: mobile ? '1fr' : 'repeat(3, 1fr)', gap: mobile ? 28 : 32 }}>
          {rows.map((p, i) => (
            <div key={p.id} className={`rv rv-${i + 1}`} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <span style={{ fontFamily: MONO, fontSize: 22, color: p.highlight ? COBALT : INK }}>{p.price}<span style={{ color: SOFT, fontSize: 14 }}> /mo</span></span>
              <span style={{ fontFamily: SANS, fontSize: 22, fontWeight: 500, letterSpacing: '-0.02em', color: INK }}>{p.name}</span>
              <span style={text(16)}>{short[p.id]}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── Contact: cobalt ─── */
function Contact({ mobile }: { mobile: boolean }) {
  return (
    <section style={{ background: COBALT, color: WHITE }}>
      <Wrap mobile={mobile}>
        <div className="rv" style={eyebrow('rgba(255,255,255,0.7)')}>Contact</div>
        <h2 className="rv rv-1" style={{ ...head(mobile ? 'clamp(40px, 11vw, 56px)' : 'clamp(52px, 5.6vw, 96px)', WHITE), marginTop: 18, maxWidth: 820 }}>Put it on one product.</h2>
        <p className="rv rv-2" style={{ ...text(mobile ? 18 : 22, 'rgba(255,255,255,0.85)'), marginTop: 20, maxWidth: 560 }}>Shopify theme editor, no code. Brands, press and production: hello@tryon.global</p>
        <div className="rv rv-3" style={{ display: 'flex', gap: 10, marginTop: 40, flexWrap: 'wrap' }}>
          <Pill href="/start" kind="white">Start free trial</Pill>
          <Pill href="/book" kind="outline" on="dark">Book a call</Pill>
        </div>
      </Wrap>
    </section>
  );
}

function Footer({ mobile }: { mobile: boolean }) {
  const l: React.CSSProperties = { color: GREY, textDecoration: 'none' };
  return (
    <footer style={{ background: WHITE }}>
      <div style={{ maxWidth: 1320, margin: '0 auto', padding: mobile ? '28px 20px' : '36px 48px', display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, ...eyebrow(SOFT), fontSize: 11 }}>
        <span>TryOn · by Fravash, Amsterdam · 2026</span>
        <span style={{ display: 'flex', gap: 24 }}><Link href="/product" style={l}>Product</Link><Link href="/pricing" style={l}>Pricing</Link><Link href="/privacy" style={l}>Privacy</Link><a href={FRAVASH_URL} target="_blank" rel="noopener noreferrer" style={l}>fravash.ai</a></span>
      </div>
    </footer>
  );
}

export function SimpleLanding({ dark: _dark = false }: { dark?: boolean }) {
  const mobile = useIsMobile();
  useReveal();
  return (
    <div style={{ width: '100%', background: WHITE, color: INK, fontFamily: SANS, colorScheme: 'light' }}>
      {/* eslint-disable-next-line @next/next/no-page-custom-font */}
      <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" />
      <style dangerouslySetInnerHTML={{ __html: CSS }} />
      <Nav mobile={mobile} />
      <Hero mobile={mobile} />
      <How mobile={mobile} />
      <ThreeD mobile={mobile} />
      <Report mobile={mobile} />
      <Vision mobile={mobile} />
      <Pricing mobile={mobile} />
      <Contact mobile={mobile} />
      <Footer mobile={mobile} />
    </div>
  );
}
