'use client';

import type React from 'react';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { useIsMobile } from './useIsMobile';
import { PLANS } from '@/lib/plans';

/* Home page in the Fravash v6 system: off-white and navy and cobalt, mono eyebrows,
   sentence-case headlines set tight, pill buttons, one hairline per list row and no more.
   Sections alternate light / dark / cobalt. The 3D avatar is the hero visual. */

const AvatarHero = dynamic(() => import('./AvatarHero').then((m) => m.AvatarHero), { ssr: false });

const INK = '#0A0A0A';
const GREY = '#6E6E73';
const PAPER = '#F4F4F2';
const WHITE = '#FFFFFF';
const NAVY = '#0B0F1A';
const COBALT = '#1F3BFF';
const RULE = 'rgba(10,10,10,0.12)';
const SANS = "'Hanken Grotesk', 'Manrope', system-ui, sans-serif";
const MONO = "'JetBrains Mono', monospace";
const FRAVASH_URL = 'https://fravash.ai';

const CSS = `
@keyframes fv-up{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
.fv-up{animation:fv-up 1s cubic-bezier(.2,.7,.2,1) both}.fv-d1{animation-delay:.1s}.fv-d2{animation-delay:.25s}.fv-d3{animation-delay:.4s}
.rv{opacity:0;transform:translateY(18px);transition:opacity .9s cubic-bezier(.2,.7,.2,1),transform .9s cubic-bezier(.2,.7,.2,1)}
.rv.in{opacity:1;transform:none}
.rv-d1{transition-delay:.12s}.rv-d2{transition-delay:.24s}.rv-d3{transition-delay:.36s}
@keyframes pulse{0%,100%{opacity:.35}50%{opacity:1}}
.dot{animation:pulse 2.4s ease-in-out infinite}
.pill{transition:transform .18s cubic-bezier(.2,.7,.2,1),background .18s,color .18s}
.pill:hover{transform:translateY(-1px)}
.plogo{object-fit:contain;display:block;opacity:.85}
@media (prefers-reduced-motion: reduce){.fv-up,.rv,.dot{animation:none !important;opacity:1 !important;transform:none !important;transition:none !important}}
`;

function useReveal() {
  useEffect(() => {
    const els = Array.from(document.querySelectorAll<HTMLElement>('.rv'));
    if (!els.length) return;
    if (!('IntersectionObserver' in window)) { els.forEach((e) => e.classList.add('in')); return; }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
    }, { rootMargin: '0px 0px -10% 0px', threshold: 0.08 });
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);
}

const eyebrow = (color = GREY): React.CSSProperties => ({ fontFamily: MONO, fontSize: 12, letterSpacing: '0.2em', textTransform: 'uppercase', color, fontWeight: 500 });
const h = (size: string, color = INK, weight = 600): React.CSSProperties => ({ fontFamily: SANS, fontWeight: weight, fontSize: size, letterSpacing: '-0.035em', lineHeight: 1.02, margin: 0, color });
const sub = (size = 20, color = GREY): React.CSSProperties => ({ fontFamily: SANS, fontSize: size, lineHeight: 1.4, color, margin: 0, letterSpacing: '-0.01em' });

function Pill({ children, href, kind = 'solid', on = 'light', external }: { children: React.ReactNode; href: string; kind?: 'solid' | 'outline' | 'white'; on?: 'light' | 'dark' | 'cobalt'; external?: boolean }) {
  const styles: Record<string, React.CSSProperties> = {
    solid: { background: COBALT, color: WHITE, border: `1px solid ${COBALT}` },
    outline: { background: 'transparent', color: on === 'light' ? INK : WHITE, border: `1px solid ${on === 'light' ? RULE : 'rgba(255,255,255,0.35)'}` },
    white: { background: WHITE, color: COBALT, border: `1px solid ${WHITE}` },
  };
  const style: React.CSSProperties = {
    ...styles[kind], display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    padding: '16px 30px', borderRadius: 999, textDecoration: 'none',
    fontFamily: SANS, fontSize: 17, fontWeight: 500, letterSpacing: '-0.01em', lineHeight: 1,
  };
  if (external) return <a className="pill" href={href} target="_blank" rel="noopener noreferrer" style={style}>{children}</a>;
  return <Link className="pill" href={href} style={style}>{children}</Link>;
}

/* ─── Nav ─── */
function Nav({ mobile }: { mobile: boolean }) {
  const [open, setOpen] = useState(false);
  const links = [
    { label: 'How it works', href: '#how' }, { label: 'The report', href: '#report' },
    { label: 'Production', href: '#production' }, { label: 'Pricing', href: '/pricing' },
  ];
  return (
    <header style={{ background: PAPER, position: 'sticky', top: 0, zIndex: 20 }}>
      <div style={{ maxWidth: 1360, margin: '0 auto', padding: mobile ? '18px 20px' : '26px 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 24 }}>
        <Link href="/" aria-label="TryOn home" style={{ display: 'flex', alignItems: 'center', gap: 12, textDecoration: 'none' }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/redesign/wordmark.png" alt="TryOn" style={{ height: mobile ? 20 : 24, width: 'auto', display: 'block' }} />
        </Link>
        {!mobile && (
          <nav style={{ display: 'flex', alignItems: 'center', gap: 36 }}>
            {links.map((l) => <a key={l.href} href={l.href} style={{ fontFamily: SANS, fontSize: 18, color: GREY, textDecoration: 'none', letterSpacing: '-0.01em' }}>{l.label}</a>)}
            <Pill href="/book" kind="outline">Contact</Pill>
            <Pill href="/start">Start free trial</Pill>
          </nav>
        )}
        {mobile && (
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <Pill href="/start">Start</Pill>
            <button type="button" aria-label={open ? 'Close menu' : 'Menu'} onClick={() => setOpen((o) => !o)} style={{ width: 44, height: 44, borderRadius: 999, border: `1px solid ${RULE}`, background: 'transparent', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ width: 18 }}>
                <span style={{ display: 'block', height: 1.5, background: INK, marginBottom: 4 }} />
                <span style={{ display: 'block', height: 1.5, background: INK, marginBottom: 4 }} />
                <span style={{ display: 'block', height: 1.5, background: INK }} />
              </span>
            </button>
          </div>
        )}
      </div>
      {mobile && open && (
        <nav style={{ padding: '8px 20px 28px', display: 'flex', flexDirection: 'column', gap: 18, background: PAPER }}>
          {[...links, { label: 'Contact', href: '/book' }, { label: 'Sign in', href: '/login' }].map((l) => (
            <a key={l.href} href={l.href} onClick={() => setOpen(false)} style={{ fontFamily: SANS, fontSize: 26, fontWeight: 500, color: INK, textDecoration: 'none', letterSpacing: '-0.02em' }}>{l.label}</a>
          ))}
        </nav>
      )}
    </header>
  );
}

/* ─── Hero: the avatar, and the one line ─── */
function Hero({ mobile }: { mobile: boolean }) {
  return (
    <section style={{ background: PAPER }}>
      <div style={{ maxWidth: 1360, margin: '0 auto', padding: mobile ? '32px 20px 0' : '64px 48px 0', display: 'grid', gridTemplateColumns: mobile ? '1fr' : '1.05fr 1fr', gap: mobile ? 24 : 48, alignItems: 'center' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: mobile ? 22 : 30, paddingBottom: mobile ? 0 : 64 }}>
          <div className="fv-up" style={eyebrow()}>Fit, measured</div>
          <h1 className="fv-up fv-d1" style={h(mobile ? 'clamp(40px, 11vw, 56px)' : 'clamp(52px, 5.4vw, 92px)')}>Clothes made for the bodies that buy them.</h1>
          <p className="fv-up fv-d2" style={{ ...sub(mobile ? 18 : 22), maxWidth: 560 }}>One button measures your shoppers. The next run is cut to them.</p>
          <div className="fv-up fv-d3" style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <Pill href="/start">Start free trial</Pill>
            <Pill href="#how" kind="outline">How it works</Pill>
          </div>
        </div>
        <div className="fv-up fv-d2" style={{ position: 'relative', height: mobile ? '56vh' : 'calc(100vh - 200px)', minHeight: mobile ? 400 : 560, maxHeight: 860 }}>
          <AvatarHero height="100%" interactive={false} rotateSpeed={0.6} />
          <div aria-hidden style={{ position: 'absolute', bottom: 8, left: 0, right: 0, textAlign: 'center', ...eyebrow(), fontSize: 11 }}>Your shopper · size M · live 3D</div>
        </div>
      </div>
      <div style={{ maxWidth: 1360, margin: '0 auto', padding: mobile ? '40px 20px 56px' : '48px 48px 96px', display: 'flex', alignItems: 'center', gap: mobile ? 28 : 56, flexWrap: 'wrap' }}>
        <span style={eyebrow()}>Live with</span>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/partners/lafam.webp" alt="La Fam Amsterdam" className="plogo rv" style={{ height: mobile ? 44 : 64 }} />
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/partners/ramin.webp" alt="Ramin Studios" className="plogo rv rv-d1" style={{ height: mobile ? 14 : 20 }} />
      </div>
    </section>
  );
}

/* ─── Phone: the size result, drawn ─── */
const SCORES = [{ s: 'M', v: 31 }, { s: 'L', v: 96, best: true }, { s: 'XL', v: 23 }];
function Phone({ mobile }: { mobile: boolean }) {
  const w = mobile ? 280 : 340;
  return (
    <div className="rv rv-d1" style={{ width: w, margin: '0 auto', background: '#0A0A0A', borderRadius: 48, padding: 12, boxShadow: '0 30px 80px rgba(10,10,10,0.18)' }}>
      <div style={{ background: WHITE, borderRadius: 38, padding: '22px 22px 26px', minHeight: w * 2.05, display: 'flex', flexDirection: 'column', fontFamily: SANS, color: INK }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, fontWeight: 600 }}><span>9:41</span><span style={{ width: 90, height: 24, background: '#0A0A0A', borderRadius: 999 }} /><span>●●●</span></div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 28, ...eyebrow(), fontSize: 11 }}><span>TryOn</span><span style={{ color: COBALT }}>03 / 04</span></div>
        <div style={{ ...h('26px'), marginTop: 18 }}>Your size at La Fam</div>
        <div style={{ ...eyebrow(), fontSize: 11, marginTop: 36, textAlign: 'center' }}>best match</div>
        <div style={{ fontFamily: MONO, fontSize: 64, color: COBALT, textAlign: 'center', letterSpacing: '-0.04em', lineHeight: 1, marginTop: 10 }}>L · 96%</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 30 }}>
          {SCORES.map((x) => (
            <div key={x.s} style={{ display: 'grid', gridTemplateColumns: '28px 1fr 42px', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 14, fontWeight: x.best ? 700 : 500 }}>{x.s}</span>
              <span style={{ height: 6, borderRadius: 3, background: 'rgba(10,10,10,0.08)', overflow: 'hidden' }}><span style={{ display: 'block', height: '100%', width: `${x.v}%`, background: x.best ? COBALT : '#B8B8BC', borderRadius: 3 }} /></span>
              <span style={{ fontSize: 13, color: x.best ? INK : GREY, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{x.v}%</span>
            </div>
          ))}
        </div>
        <p style={{ ...sub(14), textAlign: 'center', marginTop: 24 }}>Sold out in L? You see the next best, and how it fits.</p>
        <div style={{ marginTop: 'auto', background: '#EAF5EE', color: '#1E6B3A', borderRadius: 999, padding: '14px 18px', display: 'flex', alignItems: 'center', gap: 10, fontSize: 15, fontWeight: 500 }}>
          <span className="dot" style={{ width: 8, height: 8, borderRadius: 999, background: '#1E6B3A' }} /> measured · true
        </div>
      </div>
    </div>
  );
}

/* ─── How it works: four steps, one active ─── */
const STEPS = [
  { n: '01', t: 'Shopper taps Find my size', d: '' },
  { n: '02', t: 'Seven questions, or one photo', d: '' },
  { n: '03', t: 'Every size scored', d: 'A match for each size on the product, in 30 seconds. No account.', active: true },
  { n: '04', t: 'You get the measurements', d: '' },
];
function How({ mobile }: { mobile: boolean }) {
  return (
    <section id="how" style={{ background: PAPER }}>
      <div style={{ maxWidth: 1360, margin: '0 auto', padding: mobile ? '72px 20px 80px' : '140px 48px 160px', display: 'grid', gridTemplateColumns: mobile ? '1fr' : '1.3fr 1fr', gap: mobile ? 48 : 64, alignItems: 'center' }}>
        <div>
          <div className="rv" style={eyebrow()}>Four steps</div>
          <h2 className="rv rv-d1" style={{ ...h(mobile ? 'clamp(32px, 9vw, 44px)' : 'clamp(40px, 4.2vw, 68px)'), marginTop: 18 }}>One button, and you know your customers.</h2>
          <div className="rv rv-d2" style={{ display: 'inline-block', marginTop: 24, ...eyebrow(INK), fontSize: 11, border: `1px solid ${RULE}`, borderRadius: 999, padding: '10px 18px' }}>Under 30 seconds</div>
          <ol style={{ listStyle: 'none', margin: mobile ? '40px 0 0' : '56px 0 0', padding: 0 }}>
            {STEPS.map((s, i) => (
              <li key={s.n} className={`rv rv-d${Math.min(i, 3)}`} style={{
                display: 'grid', gridTemplateColumns: '44px 1fr', gap: 16, padding: mobile ? '22px 0' : '28px 0',
                borderTop: i === 0 ? `1px solid ${RULE}` : 0, borderBottom: `1px solid ${RULE}`,
                borderLeft: s.active ? `2px solid ${COBALT}` : '2px solid transparent', paddingLeft: 16, marginLeft: -18,
              }}>
                <span style={{ ...eyebrow(s.active ? COBALT : GREY), fontSize: 12, paddingTop: 10 }}>{s.n}</span>
                <div>
                  <div style={{ ...h(mobile ? '24px' : '32px', INK, 500), letterSpacing: '-0.025em' }}>{s.t}</div>
                  {s.d && <p style={{ ...sub(mobile ? 16 : 19), marginTop: 12, maxWidth: 520 }}>{s.d}</p>}
                </div>
              </li>
            ))}
          </ol>
        </div>
        <Phone mobile={mobile} />
      </div>
    </section>
  );
}

/* ─── The report: on navy ─── */
const OUT = [
  { k: 'Measurements', v: 'chest · waist · hips' },
  { k: 'Sizes that miss', v: 'M · 27%' },
  { k: 'Next run', v: 'S 12 · M 41 · L 35 · XL 12' },
];
function Report({ mobile }: { mobile: boolean }) {
  const card: React.CSSProperties = { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 16, padding: mobile ? '18px 20px' : '26px 28px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16 };
  return (
    <section id="report" style={{ background: NAVY, color: WHITE, position: 'relative', overflow: 'hidden' }}>
      <div aria-hidden style={{ position: 'absolute', inset: 0, background: 'radial-gradient(60% 50% at 70% 60%, rgba(31,59,255,0.18) 0%, rgba(11,15,26,0) 70%)' }} />
      <div style={{ position: 'relative', maxWidth: 1360, margin: '0 auto', padding: mobile ? '80px 20px 88px' : '150px 48px 160px' }}>
        <div className="rv" style={eyebrow('rgba(255,255,255,0.55)')}>The report</div>
        <h2 className="rv rv-d1" style={{ ...h(mobile ? 'clamp(34px, 9.5vw, 48px)' : 'clamp(44px, 4.6vw, 76px)', WHITE), marginTop: 18, maxWidth: 900 }}>A different body behind every order.</h2>
        <p className="rv rv-d2" style={{ ...sub(mobile ? 18 : 24, 'rgba(255,255,255,0.7)'), marginTop: 18, maxWidth: 640 }}>Every month, what your customers measure and what to cut next.</p>

        <div className="rv rv-d2" style={{ display: 'grid', gridTemplateColumns: mobile ? '1fr' : '1fr auto 1.3fr', gap: mobile ? 28 : 56, alignItems: 'center', marginTop: mobile ? 56 : 96 }}>
          <div style={{ border: '1px solid rgba(255,255,255,0.18)', borderRadius: 14, padding: mobile ? '26px' : '38px', textAlign: 'center', ...eyebrow('rgba(255,255,255,0.85)'), fontSize: 13 }}>Your shoppers</div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
            <div style={{ width: 96, height: 96, borderRadius: 999, border: '2px solid rgba(255,255,255,0.9)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 0 10px rgba(255,255,255,0.06), 0 0 0 20px rgba(255,255,255,0.03)' }}>
              <span className="dot" style={{ width: 22, height: 22, borderRadius: 999, background: COBALT, boxShadow: `0 0 24px ${COBALT}` }} />
            </div>
            <span style={{ ...eyebrow('rgba(255,255,255,0.6)'), fontSize: 11 }}>TryOn measures</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {OUT.map((o) => (
              <div key={o.k} style={card}>
                <span style={{ ...eyebrow('rgba(255,255,255,0.7)'), fontSize: 12 }}>{o.k}</span>
                <span style={{ fontFamily: MONO, fontSize: mobile ? 15 : 20, color: '#8EA2FF', letterSpacing: '-0.01em', whiteSpace: 'nowrap' }}>{o.v}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="rv rv-d3" style={{ marginTop: mobile ? 48 : 72, display: 'flex', gap: mobile ? 14 : 40, flexWrap: 'wrap', justifyContent: 'center', ...eyebrow('rgba(255,255,255,0.55)'), fontSize: 12 }}>
          <span><b style={{ color: WHITE, fontWeight: 600 }}>No spreadsheets</b></span><span>No fit sessions</span><span>One report a month</span>
        </div>
      </div>
    </section>
  );
}

/* ─── Where they are: the globe card we had ─── */
function Where({ mobile }: { mobile: boolean }) {
  return (
    <section style={{ background: WHITE }}>
      <div style={{ maxWidth: 1360, margin: '0 auto', padding: mobile ? '72px 20px' : '140px 48px', display: 'grid', gridTemplateColumns: mobile ? '1fr' : '1fr 1fr', gap: mobile ? 36 : 64, alignItems: 'center' }}>
        <div>
          <div className="rv" style={eyebrow()}>Where they are</div>
          <h2 className="rv rv-d1" style={{ ...h(mobile ? 'clamp(32px, 9vw, 44px)' : 'clamp(40px, 4.2vw, 64px)'), marginTop: 18 }}>Sizes by country, before you ship there.</h2>
          <p className="rv rv-d2" style={{ ...sub(mobile ? 17 : 21), marginTop: 18, maxWidth: 520 }}>The Netherlands runs large. Spain runs small. Your report says by how much.</p>
        </div>
        <div className="rv rv-d1" style={{ display: 'flex', justifyContent: 'center' }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/redesign/fit-report.jpg" alt="Size report by country" style={{ width: '100%', maxWidth: 560, height: 'auto', display: 'block' }} />
        </div>
      </div>
    </section>
  );
}

/* ─── Production: cobalt ─── */
function Production({ mobile }: { mobile: boolean }) {
  const tile: React.CSSProperties = { padding: mobile ? '22px 22px' : '30px 34px', textDecoration: 'none', color: WHITE, display: 'flex', flexDirection: 'column', gap: 6 };
  const tiles = [
    { t: 'Start free trial', d: 'One button, thirty days free.', href: '/start' },
    { t: 'See pricing', d: 'From $19 a month.', href: '/pricing' },
    { t: 'Production by Fravash', d: 'Fabric, sample, graded order. Denim first.', href: FRAVASH_URL, ext: true },
    { t: 'Book a call', d: 'Brands, press, partnerships.', href: '/book' },
  ];
  return (
    <section id="production" style={{ background: COBALT, color: WHITE, position: 'relative', overflow: 'hidden' }}>
      <div aria-hidden style={{ position: 'absolute', right: mobile ? -160 : -120, top: '50%', transform: 'translateY(-50%)', width: 620, height: 620, borderRadius: 999, border: '70px solid rgba(255,255,255,0.08)', boxShadow: 'inset 0 0 0 60px rgba(255,255,255,0.06)' }} />
      <div style={{ position: 'relative', maxWidth: 1360, margin: '0 auto', padding: mobile ? '80px 20px 88px' : '150px 48px 160px' }}>
        <div className="rv" style={eyebrow('rgba(255,255,255,0.7)')}>Where this goes</div>
        <h2 className="rv rv-d1" style={{ ...h(mobile ? 'clamp(40px, 11vw, 56px)' : 'clamp(52px, 5.6vw, 96px)', WHITE), marginTop: 18, maxWidth: 820 }}>Cut to the people who buy.</h2>
        <p className="rv rv-d2" style={{ ...sub(mobile ? 18 : 24, 'rgba(255,255,255,0.85)'), marginTop: 22, maxWidth: 680 }}>The size run goes to Fravash, our production company. The next drop comes back graded to your customers.</p>
        <div className="rv rv-d2" style={{ marginTop: mobile ? 44 : 64, display: 'grid', gridTemplateColumns: mobile ? '1fr' : '1fr 1fr', border: '1px solid rgba(255,255,255,0.35)', borderRadius: 14, overflow: 'hidden' }}>
          {tiles.map((t, i) => {
            const st: React.CSSProperties = { ...tile, background: i === 0 ? WHITE : 'transparent', color: i === 0 ? COBALT : WHITE, borderRight: !mobile && i % 2 === 0 ? '1px solid rgba(255,255,255,0.35)' : 0, borderBottom: (mobile ? i < 3 : i < 2) ? '1px solid rgba(255,255,255,0.35)' : 0 };
            const inner = <><span style={{ fontFamily: SANS, fontSize: mobile ? 22 : 28, fontWeight: 500, letterSpacing: '-0.025em' }}>{t.t}</span><span style={{ fontFamily: SANS, fontSize: mobile ? 15 : 18, opacity: 0.8 }}>{t.d}</span></>;
            return t.ext ? <a key={t.t} href={t.href} target="_blank" rel="noopener noreferrer" style={st}>{inner}</a> : <Link key={t.t} href={t.href} style={st}>{inner}</Link>;
          })}
        </div>
        <div className="rv rv-d3" style={{ display: 'flex', gap: 12, marginTop: 28, flexWrap: 'wrap' }}>
          <Pill href="/start" kind="white">Start free trial</Pill>
          <Pill href="/book" kind="outline" on="cobalt">Contact us</Pill>
        </div>
      </div>
    </section>
  );
}

/* ─── Pricing, short ─── */
function Pricing({ mobile }: { mobile: boolean }) {
  const short: Record<string, string> = { size_pro: 'The button. No 3D.', try_on: 'Your clothes on their body.', insights: 'Try-On plus the monthly report.' };
  const rows = PLANS.filter((p) => ['size_pro', 'try_on', 'insights'].includes(p.id));
  return (
    <section style={{ background: PAPER }}>
      <div style={{ maxWidth: 1360, margin: '0 auto', padding: mobile ? '72px 20px 80px' : '140px 48px 150px', display: 'grid', gridTemplateColumns: mobile ? '1fr' : '1fr 1.2fr', gap: mobile ? 36 : 64, alignItems: 'start' }}>
        <div>
          <div className="rv" style={eyebrow()}>Pricing</div>
          <h2 className="rv rv-d1" style={{ ...h(mobile ? 'clamp(32px, 9vw, 44px)' : 'clamp(40px, 4.2vw, 64px)'), marginTop: 18 }}>Less than one return a day.</h2>
          <p className="rv rv-d2" style={{ ...sub(mobile ? 17 : 21), marginTop: 18, maxWidth: 440 }}>Thirty days free on every plan. Shopify billing.</p>
          <div className="rv rv-d2" style={{ marginTop: 28 }}><Pill href="/pricing" kind="outline">See full pricing</Pill></div>
        </div>
        <div className="rv rv-d1">
          {rows.map((p, i) => (
            <div key={p.id} style={{ display: 'grid', gridTemplateColumns: mobile ? '1fr auto' : '1fr 1.4fr auto', gap: 16, alignItems: 'baseline', padding: mobile ? '20px 0' : '26px 0', borderTop: i === 0 ? `1px solid ${RULE}` : 0, borderBottom: `1px solid ${RULE}` }}>
              <span style={{ ...h(mobile ? '22px' : '28px', INK, 500), letterSpacing: '-0.02em' }}>{p.name}</span>
              {!mobile && <span style={sub(18)}>{short[p.id]}</span>}
              <span style={{ fontFamily: MONO, fontSize: mobile ? 16 : 18, color: p.highlight ? COBALT : INK }}>{p.price}<span style={{ color: GREY }}>/mo</span></span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── Contact ─── */
function Contact({ mobile }: { mobile: boolean }) {
  return (
    <section style={{ background: WHITE }}>
      <div style={{ maxWidth: 1360, margin: '0 auto', padding: mobile ? '72px 20px 80px' : '140px 48px 150px', display: 'grid', gridTemplateColumns: mobile ? '1fr' : '1fr 1fr', gap: mobile ? 36 : 64, alignItems: 'center' }}>
        <div>
          <div className="rv" style={eyebrow()}>Contact</div>
          <h2 className="rv rv-d1" style={{ ...h(mobile ? 'clamp(32px, 9vw, 44px)' : 'clamp(40px, 4.2vw, 64px)'), marginTop: 18 }}>Tell us what you make.</h2>
          <p className="rv rv-d2" style={{ ...sub(mobile ? 17 : 21), marginTop: 18, maxWidth: 480 }}>Every message is read by someone who can answer it. hello@tryon.global</p>
        </div>
        <div className="rv rv-d2" style={{ display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: mobile ? 'flex-start' : 'flex-end' }}>
          <Pill href="/book">Book a call</Pill>
          <Pill href="/start" kind="outline">Start free trial</Pill>
        </div>
      </div>
      <div style={{ maxWidth: 1360, margin: '0 auto', padding: mobile ? '0 20px 32px' : '0 48px 40px', display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, ...eyebrow(), fontSize: 11 }}>
        <span>TryOn · by Fravash, Amsterdam · 2026</span>
        <span style={{ display: 'flex', gap: 24 }}><Link href="/product" style={{ color: GREY, textDecoration: 'none' }}>Product</Link><Link href="/pricing" style={{ color: GREY, textDecoration: 'none' }}>Pricing</Link><Link href="/privacy" style={{ color: GREY, textDecoration: 'none' }}>Privacy</Link><a href={FRAVASH_URL} target="_blank" rel="noopener noreferrer" style={{ color: GREY, textDecoration: 'none' }}>fravash.ai</a></span>
      </div>
    </section>
  );
}

export function SimpleLanding({ dark: _dark = false }: { dark?: boolean }) {
  const mobile = useIsMobile();
  useReveal();
  return (
    <div style={{ width: '100%', background: PAPER, color: INK, fontFamily: SANS, colorScheme: 'light' }}>
      {/* eslint-disable-next-line @next/next/no-page-custom-font */}
      <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" />
      <style dangerouslySetInnerHTML={{ __html: CSS }} />
      <Nav mobile={mobile} />
      <Hero mobile={mobile} />
      <How mobile={mobile} />
      <Report mobile={mobile} />
      <Where mobile={mobile} />
      <Production mobile={mobile} />
      <Pricing mobile={mobile} />
      <Contact mobile={mobile} />
    </div>
  );
}
