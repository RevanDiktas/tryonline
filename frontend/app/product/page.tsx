'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from '@/contexts/ThemeContext';
import { SharedNav, NavCta, AuthAwareSignInLink } from '@/components/redesign/SharedNav';
import { useIsMobile } from '@/components/redesign/useIsMobile';
import { siteLinks } from '@/components/redesign/siteLinks';
import { SiteFooter } from '@/components/redesign/SiteFooter';
import LiveSizeDemo from '@/components/redesign/LiveSizeDemo';
import { PAL, type Palette, headingStyle, bodyStyle, eyebrowStyle, pillButton, ACCENT } from '@/components/redesign/marketing';
import { PLANS, TRIAL_DAYS, ENTRY_PLAN } from '@/lib/plans';

/* /product: what TryOn is. One button on the store; Find my size on every product, Try On on
   products in 3D; the fit passport as the upgrade; what the brand gets. With the real card live. */

function Hero({ C, mobile }: { C: Palette; mobile: boolean }) {
  const router = useRouter();
  return (
    <section style={{ background: C.bg, color: C.ink, padding: mobile ? '40px 20px 48px' : '72px 32px 80px', borderBottom: `1px solid ${C.line}` }}>
      <div style={{
        maxWidth: 1180, margin: '0 auto', display: 'grid', gap: mobile ? 40 : 64, alignItems: 'center',
        gridTemplateColumns: mobile ? '1fr' : 'minmax(0, 1.1fr) minmax(0, 0.9fr)',
      }}>
        <div>
          <p style={eyebrowStyle(C)}>Product · One button for your Shopify store</p>
          <h1 style={{ ...headingStyle('clamp(44px, 6vw, 84px)'), marginBottom: 22 }}>
            One button.<br />Every product.
          </h1>
          <p style={{ ...bodyStyle, fontSize: 18, color: C.mute, maxWidth: 520, margin: '0 0 14px' }}>
            On every product with sizes, shoppers tap <b style={{ color: C.ink }}>Find my size</b> and get their size in about 30 seconds, without an account.
          </p>
          <p style={{ ...bodyStyle, fontSize: 18, color: C.mute, maxWidth: 520, margin: '0 0 30px' }}>
            On products you have in 3D, the same button reads <b style={{ color: C.ink }}>Try On</b>: they see your clothes on their own body.
          </p>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button type="button" style={pillButton('primary', C)} onClick={() => router.push('/start')}>Start free trial <span>→</span></button>
            <button type="button" style={pillButton('ghost', C)} onClick={() => router.push('/demo')}>See the 3D try-on</button>
          </div>
          <p style={{ ...bodyStyle, fontSize: 13, color: C.mute, marginTop: 16 }}>
            From {ENTRY_PLAN.price} a month, with a {TRIAL_DAYS}-day free trial on every plan.
          </p>
        </div>
        <LiveSizeDemo C={C} />
      </div>
    </section>
  );
}

function Steps({ C, mobile }: { C: Palette; mobile: boolean }) {
  const steps = [
    { n: '01', title: 'Seven quick questions', body: 'Who it is for, height and weight on a ruler, age, two body-shape questions with drawings, and how they like their clothes to fit. No account, about 30 seconds.' },
    { n: '02', title: 'Every size, scored', body: 'Their size, and a % match for every size: L 96, M 31, XL 23. If their size is sold out, the card says so and moves them to the next best, with how it will fit.' },
    { n: '03', title: 'Add to cart, from the card', body: 'The size they pick goes straight into your cart. Their answers are remembered on every product, and in every store that uses TryOn.' },
  ];
  return (
    <section style={{ background: C.surface, color: C.ink, padding: mobile ? '56px 20px' : '88px 32px', borderBottom: `1px solid ${C.line}` }}>
      <div style={{ maxWidth: 1180, margin: '0 auto' }}>
        <p style={eyebrowStyle(C)}>For shoppers · Find my size</p>
        <h2 style={{ ...headingStyle('clamp(32px, 4.4vw, 60px)'), maxWidth: 820, marginBottom: 44 }}>
          A size they can trust, before they buy.
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: mobile ? '1fr' : 'repeat(3, 1fr)', border: `1px solid ${C.line}` }}>
          {steps.map((s, i) => (
            <div key={s.n} style={{
              padding: '28px 26px 32px', background: C.bg,
              borderRight: !mobile && i < steps.length - 1 ? `1px solid ${C.line}` : 'none',
              borderBottom: mobile && i < steps.length - 1 ? `1px solid ${C.line}` : 'none',
            }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: ACCENT, marginBottom: 18 }}>{s.n}</div>
              <h3 style={{ ...headingStyle('22px'), marginBottom: 10 }}>{s.title}</h3>
              <p style={{ ...bodyStyle, fontSize: 15, color: C.mute, margin: 0 }}>{s.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Passport({ C, mobile }: { C: Palette; mobile: boolean }) {
  const points = [
    ['One photo', 'Head to feet, in about two minutes. We measure chest, waist, hips and more from it.'],
    ['A measured size', 'Not an estimate: the size comes from their own measurements, on every product.'],
    ['Their own 3D body', 'A photoreal avatar. On products in 3D they see the garment on it, with real cloth simulation.'],
  ];
  return (
    <section style={{ background: C.bg, color: C.ink, padding: mobile ? '56px 20px' : '88px 32px', borderBottom: `1px solid ${C.line}` }}>
      <div style={{
        maxWidth: 1180, margin: '0 auto', display: 'grid', gap: mobile ? 36 : 64, alignItems: 'center',
        gridTemplateColumns: mobile ? '1fr' : '1fr 1fr',
      }}>
        <div>
          <p style={eyebrowStyle(C)}>The upgrade · Fit passport</p>
          <h2 style={{ ...headingStyle('clamp(32px, 4.4vw, 60px)'), marginBottom: 18 }}>
            From an estimate to their exact size.
          </h2>
          <p style={{ ...bodyStyle, color: C.mute, maxWidth: 520, marginBottom: 28 }}>
            After their size, the card offers the fit passport: <b style={{ color: C.ink }}>Try On</b> on products in 3D, <b style={{ color: C.ink }}>Create my fit passport</b> on the rest. It is free for shoppers and follows them to every TryOn store.
          </p>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, borderTop: `1px solid ${C.line}` }}>
            {points.map(([t, d]) => (
              <li key={t} style={{ padding: '16px 0', borderBottom: `1px solid ${C.line}`, display: 'grid', gridTemplateColumns: mobile ? '1fr' : '180px 1fr', gap: 6 }}>
                <span style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 15 }}>{t}</span>
                <span style={{ ...bodyStyle, fontSize: 14.5, color: C.mute }}>{d}</span>
              </li>
            ))}
          </ul>
        </div>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/redesign/tryon-product.jpg" alt="A shopper's 3D avatar wearing the garment" style={{ width: '100%', borderRadius: 24, display: 'block', border: `1px solid ${C.line}` }} />
      </div>
    </section>
  );
}

function ForBrands({ C, mobile }: { C: Palette; mobile: boolean }) {
  const install = [
    ['Install TryOn', 'From the Shopify App Store, or from the private link we send you today.'],
    ['Add the button', 'Open your theme editor and add the TryOn block next to your size picker. No code.'],
    ['Live on every product', 'Find my size works on every product with sizes from the first minute. We make your garments in 3D for Try On.'],
  ];
  const insights = [
    ['ROI and attribution', 'Orders, revenue and add-to-carts from shoppers who used TryOn, against the rest.'],
    ['Size finder funnel', 'Where shoppers drop off in the quiz, and the % match each size gets.'],
    ['Fit intelligence', 'Recommended against bought sizes, per product, and which sizes are under pressure.'],
    ['Returns and risk', 'Return rates by size and product, and the orders most likely to come back.'],
  ];
  return (
    <section style={{ background: C.surface, color: C.ink, padding: mobile ? '56px 20px' : '88px 32px', borderBottom: `1px solid ${C.line}` }}>
      <div style={{ maxWidth: 1180, margin: '0 auto' }}>
        <p style={eyebrowStyle(C)}>For brands · Shopify</p>
        <h2 style={{ ...headingStyle('clamp(32px, 4.4vw, 60px)'), maxWidth: 900, marginBottom: 44 }}>
          Live in an afternoon. No code.
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: mobile ? '1fr' : 'repeat(3, 1fr)', gap: 0, border: `1px solid ${C.line}`, marginBottom: 64 }}>
          {install.map(([t, d], i) => (
            <div key={t} style={{
              padding: '26px 24px 30px', background: C.bg,
              borderRight: !mobile && i < install.length - 1 ? `1px solid ${C.line}` : 'none',
              borderBottom: mobile && i < install.length - 1 ? `1px solid ${C.line}` : 'none',
            }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: ACCENT, marginBottom: 16 }}>STEP {i + 1}</div>
              <h3 style={{ ...headingStyle('21px'), marginBottom: 8 }}>{t}</h3>
              <p style={{ ...bodyStyle, fontSize: 15, color: C.mute, margin: 0 }}>{d}</p>
            </div>
          ))}
        </div>
        <div style={{ display: 'grid', gap: mobile ? 32 : 56, gridTemplateColumns: mobile ? '1fr' : '0.9fr 1.1fr', alignItems: 'center' }}>
          <div>
            <h3 style={{ ...headingStyle('clamp(26px, 3vw, 40px)'), marginBottom: 14 }}>See what fit is worth to you.</h3>
            <p style={{ ...bodyStyle, color: C.mute, marginBottom: 22 }}>Your dashboard shows every size shoppers were given, what they bought, and what came back.</p>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, borderTop: `1px solid ${C.line}` }}>
              {insights.map(([t, d]) => (
                <li key={t} style={{ padding: '14px 0', borderBottom: `1px solid ${C.line}` }}>
                  <div style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 15, marginBottom: 3 }}>{t}</div>
                  <div style={{ ...bodyStyle, fontSize: 14, color: C.mute }}>{d}</div>
                </li>
              ))}
            </ul>
          </div>
          <figure style={{ margin: 0 }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/redesign/fit-intelligence.jpg" alt="The TryOn brand dashboard" style={{ width: '100%', borderRadius: 20, display: 'block', border: `1px solid ${C.line}` }} />
            <figcaption style={{ fontFamily: 'var(--display)', fontSize: 12, color: C.mute, marginTop: 10 }}>The brand dashboard (example data).</figcaption>
          </figure>
        </div>
      </div>
    </section>
  );
}

function PlansStrip({ C, mobile }: { C: Palette; mobile: boolean }) {
  const router = useRouter();
  const shown = PLANS;
  return (
    <section style={{ background: C.bg, color: C.ink, padding: mobile ? '56px 20px' : '88px 32px', borderBottom: `1px solid ${C.line}` }}>
      <div style={{ maxWidth: 1180, margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 24, flexWrap: 'wrap', marginBottom: 32 }}>
          <h2 style={{ ...headingStyle('clamp(30px, 4vw, 52px)'), maxWidth: 680 }}>Try it free for {TRIAL_DAYS} days.</h2>
          <button type="button" style={pillButton('ghost', C)} onClick={() => router.push('/pricing')}>All plans <span>→</span></button>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: mobile ? '1fr 1fr' : `repeat(${shown.length}, 1fr)`, border: `1px solid ${C.line}`, background: C.surface }}>
          {shown.map((p, i) => (
            <div key={p.id} style={{
              padding: '22px 20px',
              borderRight: (mobile ? i % 2 === 0 : i < shown.length - 1) ? `1px solid ${C.line}` : 'none',
              borderBottom: mobile && i < 2 ? `1px solid ${C.line}` : 'none',
            }}>
              <div style={{ fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600, color: C.mute }}>{p.name}</div>
              <div style={{ fontFamily: 'var(--display)', fontSize: 32, fontWeight: 700, letterSpacing: '-0.025em', margin: '6px 0 4px' }}>{p.price}</div>
              <div style={{ fontFamily: 'var(--display)', fontSize: 12.5, color: C.mute }}>{p.period}{p.setup ? ` ${p.setup}` : ''}</div>
              <p style={{ ...bodyStyle, fontSize: 13.5, margin: '12px 0 0', color: C.ink, opacity: 0.8 }}>{p.pitch}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function FinalCTA({ C }: { C: Palette }) {
  const router = useRouter();
  return (
    <section style={{ background: C.surface, color: C.ink, padding: '72px 20px 88px' }}>
      <div style={{ maxWidth: 720, margin: '0 auto', textAlign: 'center' }}>
        <h2 style={{ ...headingStyle('clamp(34px, 4.5vw, 60px)'), marginBottom: 14 }}>Put it on your store today.</h2>
        <p style={{ ...bodyStyle, color: C.mute, margin: '0 auto 28px', maxWidth: 520 }}>
          Tell us your store. We send your install link within one working day, and Find my size is live on every product from the first minute. Free for 30 days.
        </p>
        <div style={{ display: 'inline-flex', gap: 10, flexWrap: 'wrap', justifyContent: 'center' }}>
          <button type="button" style={pillButton('primary', C)} onClick={() => router.push('/start')}>Start free trial <span>→</span></button>
          <button type="button" style={pillButton('ghost', C)} onClick={() => router.push('/book')}>Book a call</button>
        </div>
      </div>
    </section>
  );
}

export default function ProductPage() {
  const { theme } = useTheme();
  const dark = theme === 'dark';
  const C = dark ? PAL.dark : PAL.light;
  const router = useRouter();
  const mobile = useIsMobile();
  return (
    <div className="tryon-redesign-root" style={{ width: '100%', minHeight: '100vh', background: C.bg, color: C.ink, overflowX: 'hidden' }}>
      <SharedNav
        dark={dark}
        links={siteLinks('/product')}
        rightSlot={mobile ? (
          <NavCta dark={dark} label="Free trial" onClick={() => router.push('/start')} />
        ) : (
          <>
            <AuthAwareSignInLink dark={dark} />
            <NavCta dark={dark} label="Start free trial →" onClick={() => router.push('/start')} />
          </>
        )}
      />
      <Hero C={C} mobile={mobile} />
      <Steps C={C} mobile={mobile} />
      <Passport C={C} mobile={mobile} />
      <ForBrands C={C} mobile={mobile} />
      <PlansStrip C={C} mobile={mobile} />
      <FinalCTA C={C} />
      <SiteFooter dark={dark} />
    </div>
  );
}
