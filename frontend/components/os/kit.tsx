'use client';

import type React from 'react';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { fontVars } from './fonts';

/* The public site's design kit. White ground, ink #131519, one cobalt used as lines, text and the primary
   button. Inter Tight headings, Inter text, IBM Plex Mono labels, weights 400 and 500. No shadows: hairlines.
   Everything below the hero sits on one centre axis. Headings carry no full stops or commas. */

const CSS = `
.os{--bg:#FFFFFF;--tint:#F3F6FD;--deep:#080A12;--accent:#0040FF;--accent-soft:#7FA0FF;--accent-pale:#DCE4FA;--accent-press:#0032C8;
--ink:#131519;--ink2:#4E5460;--mute:#626A78;--inv:#F7F8FB;--inv2:rgba(247,248,251,.68);--rule:rgba(19,21,25,.11);--rule2:rgba(19,21,25,.2);
--rulei:rgba(247,248,251,.16);--ease:cubic-bezier(.22,1,.36,1);--pad:80px;--sec:136px;
background:var(--bg);color:var(--ink);font-family:var(--f-body),system-ui,sans-serif;font-size:clamp(1rem,.98rem + .16vw,1.0625rem);
line-height:1.55;-webkit-font-smoothing:antialiased;color-scheme:light;min-height:100vh}
@media(max-width:768px){.os{--pad:24px;--sec:88px}}
.os ::selection{background:var(--accent-pale);color:var(--ink)}
.os a{color:inherit;text-decoration:none}
.os :focus-visible{outline:none;box-shadow:0 0 0 2px var(--bg),0 0 0 4px var(--accent);border-radius:8px}
.os h1,.os h2,.os h3,.os h4{font-family:var(--f-display),system-ui,sans-serif;font-weight:500;margin:0;text-wrap:balance}
.os p{margin:0;text-wrap:pretty}
.os .h1{font-size:clamp(2.5rem,1.6rem + 3.9vw,4.5rem);line-height:1.02;letter-spacing:-.03em}
.os .h2{font-size:clamp(2rem,1.55rem + 1.95vw,3.25rem);line-height:1.08;letter-spacing:-.025em}
.os .h3{font-size:clamp(1.25rem,1.16rem + .39vw,1.5rem);line-height:1.2;letter-spacing:-.01em}
.os .eb{font-family:var(--f-mono),ui-monospace,monospace;font-size:.75rem;letter-spacing:.14em;text-transform:uppercase;color:var(--mute);font-weight:500;line-height:1}
.os .num{font-family:var(--f-mono),ui-monospace,monospace;font-size:.8125rem;letter-spacing:.06em;color:var(--accent);line-height:1}
.os .lede{color:var(--ink2);max-width:680px}
.os .small{font-size:.9375rem;line-height:1.5;color:var(--ink2)}
.os .wrap{max-width:calc(1240px + var(--pad) * 2);margin-inline:auto;padding-inline:var(--pad)}
.os .sec{padding-block:var(--sec)}
.os .hdr{display:flex;flex-direction:column;align-items:center;text-align:center;gap:16px;max-width:680px;margin:0 auto 80px}
.os .hdr h2{max-width:20ch}
@media(max-width:768px){.os .hdr{margin-bottom:48px}}
.os .rule{height:1px;background:var(--rule);border:0;margin:0}
.os .btn{display:inline-flex;align-items:center;justify-content:center;gap:10px;padding:13px 22px;border-radius:10px;border:1px solid transparent;
font-family:var(--f-body),system-ui,sans-serif;font-size:.9375rem;font-weight:500;letter-spacing:-.005em;line-height:1;cursor:pointer;
transition:background-color .2s var(--ease),border-color .2s var(--ease),color .2s var(--ease)}
.os .btn-p{background:var(--accent);color:#fff;border-color:var(--accent)}.os .btn-p:hover{background:var(--accent-press);border-color:var(--accent-press)}
.os .btn-s{background:transparent;color:var(--ink);border-color:var(--rule2)}.os .btn-s:hover{background:var(--accent-pale)}
.os .deep .btn-s{color:var(--inv);border-color:var(--rulei)}.os .deep .btn-s:hover{background:rgba(247,248,251,.10);border-color:var(--accent-soft)}
.os .btn-t{padding:6px 0;border:0;background:none;color:var(--ink)}.os .btn-t:hover{color:var(--accent)}
.os .btn-t svg{transition:transform .2s var(--ease)}.os .btn-t:hover svg{transform:translateX(4px)}
.os .deep{background:var(--deep);color:var(--inv)}.os .deep .eb{color:var(--inv2)}.os .deep .lede,.os .deep .small{color:var(--inv2)}
.os .frame{border:1px solid var(--rule);border-radius:14px;overflow:hidden;background:#fff}
.os .cap{font-family:var(--f-mono),ui-monospace,monospace;font-size:.6875rem;letter-spacing:.14em;text-transform:uppercase;color:var(--mute)}
/* nav */
.os .nav{position:sticky;top:0;z-index:30;height:76px;background:rgba(255,255,255,0);border-bottom:1px solid transparent;
transition:background-color .3s var(--ease),border-color .3s var(--ease)}
.os .nav.solid{background:#fff;border-bottom-color:var(--rule)}
.os .nav .in{height:100%;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:24px}
.os .nav .links{display:flex;gap:4px}
.os .nav .lk{font-size:.9375rem;font-weight:500;padding:10px 14px;border-radius:8px;color:var(--ink);transition:background-color .2s var(--ease),color .2s var(--ease)}
.os .nav .lk:hover{background:var(--tint)}.os .nav .lk.on{color:var(--accent)}
.os .nav .end{display:flex;justify-content:flex-end;align-items:center;gap:8px}
.os .burger{display:none;width:42px;height:42px;border-radius:999px;border:1px solid var(--rule2);background:none;cursor:pointer;align-items:center;justify-content:center}
.os .drawer{position:fixed;inset:76px 0 0 0;background:#fff;z-index:29;padding:8px 24px 40px;display:flex;flex-direction:column}
.os .drawer a{font-family:var(--f-display),system-ui;font-size:1.5rem;font-weight:500;letter-spacing:-.02em;padding:18px 0;border-bottom:1px solid var(--rule)}
@media(max-width:1024px){.os .nav .links,.os .nav .end .hide-m{display:none}.os .burger{display:inline-flex}.os .nav .in{grid-template-columns:1fr auto}}
/* reveal */
.os .rv{opacity:0;transform:translateY(22px) scale(.995);filter:blur(6px);transition:opacity .76s var(--ease),transform .76s var(--ease),filter .76s var(--ease);transition-delay:var(--d,0ms)}
.os .rv.in{opacity:1;transform:none;filter:none}
/* footer */
.os .foot .cta{display:flex;flex-direction:column;align-items:center;text-align:center;gap:24px;padding-block:var(--sec)}
.os .foot .bar{border-top:1px solid var(--rulei);padding-block:32px;display:flex;justify-content:center;gap:28px;flex-wrap:wrap}
.os .foot .bar a,.os .foot .bar span{font-size:.875rem;color:var(--inv2);transition:color .2s var(--ease)}.os .foot .bar a:hover{color:var(--inv)}
@media (prefers-reduced-motion: reduce){.os *{animation-duration:.001ms!important;animation-iteration-count:1!important;transition-duration:.001ms!important}
.os .rv{opacity:1;transform:none;filter:none}}
`;

export const NAV = [
  { label: 'Products', href: '/product' },
  { label: 'Pricing', href: '/pricing' },
  { label: 'Contact', href: '/book' },
];

export function useReveal() {
  useEffect(() => {
    const els = Array.from(document.querySelectorAll<HTMLElement>('.os .rv'));
    if (!('IntersectionObserver' in window)) { els.forEach((e) => e.classList.add('in')); return; }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
    }, { rootMargin: '0px 0px -6% 0px', threshold: 0.08 });
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);
}

export const Arrow = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden><path d="M1 7h11M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.3" /></svg>
);

function Nav({ active }: { active?: string }) {
  const [solid, setSolid] = useState(false);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const on = () => setSolid(window.scrollY > 8);
    on(); window.addEventListener('scroll', on, { passive: true });
    return () => window.removeEventListener('scroll', on);
  }, []);
  return (
    <>
      <header className={`nav${solid || open ? ' solid' : ''}`}>
        <div className="wrap in">
          <Link href="/" aria-label="Tryon home" style={{ display: 'flex', alignItems: 'center' }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/redesign/wordmark.png" alt="Tryon" style={{ height: 20, width: 'auto', display: 'block' }} />
          </Link>
          <nav className="links" aria-label="Main">
            {NAV.map((l) => <Link key={l.href} href={l.href} className={`lk${active === l.href ? ' on' : ''}`}>{l.label}</Link>)}
          </nav>
          <div className="end">
            <Link href="/login" className="lk hide-m">Sign in</Link>
            <Link href="/book" className="btn btn-p hide-m">Work with us</Link>
            <button type="button" className="burger" aria-label={open ? 'Close menu' : 'Menu'} aria-expanded={open} onClick={() => setOpen((o) => !o)}>
              <svg width="16" height="12" viewBox="0 0 16 12" aria-hidden>
                {open ? <path d="M2 1l12 10M14 1L2 11" stroke="#131519" strokeWidth="1.5" /> : <path d="M0 2h16M0 6h16M0 10h16" stroke="#131519" strokeWidth="1.5" />}
              </svg>
            </button>
          </div>
        </div>
      </header>
      {open && (
        <nav className="drawer" aria-label="Menu">
          {[...NAV, { label: 'Sign in', href: '/login' }].map((l) => <Link key={l.href} href={l.href} onClick={() => setOpen(false)}>{l.label}</Link>)}
          <Link href="/book" className="btn btn-p" style={{ marginTop: 28, fontSize: '1rem', borderBottom: 0, padding: '16px 22px' }} onClick={() => setOpen(false)}>Work with us</Link>
        </nav>
      )}
    </>
  );
}

function Footer() {
  return (
    <footer className="deep foot">
      <div className="wrap">
        <div className="cta">
          <span className="eb rv">Start here</span>
          <h2 className="h2 rv" style={{ ['--d' as string]: '60ms', maxWidth: '16ch' }}>Your next collection built on real bodies</h2>
          <div className="rv" style={{ ['--d' as string]: '120ms', display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: 'center' }}>
            <Link href="/book" className="btn btn-p">Work with us</Link>
            <Link href="/product" className="btn btn-s">Products</Link>
          </div>
        </div>
        <div className="bar">
          <span>Tryon Amsterdam 2026</span>
          <Link href="/product">Products</Link>
          <Link href="/pricing">Pricing</Link>
          <Link href="/book">Contact</Link>
          <Link href="/login">Sign in</Link>
          <Link href="/privacy">Privacy</Link>
        </div>
      </div>
    </footer>
  );
}

/** Page shell: fonts, tokens, nav, footer, scroll reveal. */
export function Site({ active, children }: { active?: string; children: React.ReactNode }) {
  useReveal();
  return (
    <div className={`os ${fontVars}`}>
      <style dangerouslySetInnerHTML={{ __html: CSS }} />
      <Nav active={active} />
      <main>{children}</main>
      <Footer />
    </div>
  );
}

/** Centred section header: mono eyebrow, short heading, optional one line. */
export function Header({ eyebrow, title, line, as = 'h2' }: { eyebrow: string; title: React.ReactNode; line?: React.ReactNode; as?: 'h1' | 'h2' }) {
  const H = as;
  return (
    <div className="hdr">
      <span className="eb rv">{eyebrow}</span>
      <H className={`${as === 'h1' ? 'h1' : 'h2'} rv`} style={{ ['--d' as string]: '60ms' }}>{title}</H>
      {line && <p className="lede rv" style={{ ['--d' as string]: '120ms' }}>{line}</p>}
    </div>
  );
}
