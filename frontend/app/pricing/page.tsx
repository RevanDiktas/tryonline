'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from '@/contexts/ThemeContext';
import { SharedNav, NavCta, AuthAwareSignInLink } from '@/components/redesign/SharedNav';
import { useIsMobile } from '@/components/redesign/useIsMobile';

const PAL = {
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
type Palette = typeof PAL.light;

const headingStyle = (px: string): React.CSSProperties => ({
  fontFamily: 'var(--display)',
  fontWeight: 700,
  fontSize: px,
  letterSpacing: '-0.022em',
  lineHeight: 1.04,
  margin: 0,
});

const bodyStyle: React.CSSProperties = {
  fontFamily: 'var(--display)',
  fontWeight: 400,
  fontSize: 16,
  lineHeight: 1.6,
};

function Hero({ C }: { C: Palette }) {
  return (
    <section style={{ background: C.bg, color: C.ink, padding: '56px 20px 28px', borderBottom: `1px solid ${C.line}` }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <h1 style={{
          ...headingStyle('clamp(44px, 5.5vw, 80px)'),
          maxWidth: 1100, marginBottom: 18,
        }}>
          Pay less than the cost of one return per day.
        </h1>
        <p style={{
          ...bodyStyle, fontSize: 17, color: C.mute, maxWidth: 720, marginBottom: 8,
        }}>
          TryOn costs less than the value of returns we save you. Every paid tier prices at well under 30% of the dollar value of returns prevented at conservative assumptions.
        </p>
        <p style={{
          ...bodyStyle, fontSize: 13.5, color: C.mute, maxWidth: 720,
        }}>
          Built for Shopify Plus fashion brands losing six figures a month to returns. Pricing in USD, billed monthly. EU and UK customers invoiced in EUR or GBP.
        </p>
      </div>
    </section>
  );
}

function Tiers({ C }: { C: Palette }) {
  const router = useRouter();
  const tiers: {
    name: string; price: string; priceSub?: string; setup?: string;
    headline: string; features: string[]; cta: string; ctaHref: string; highlight?: boolean;
  }[] = [
    {
      name: 'Free', price: '$0', priceSub: 'forever',
      headline: 'Try it on your store in 10 minutes.',
      features: [
        '200 try-on sessions per month',
        '3 garment uploads',
        'Branded TryOn widget',
        'Basic funnel analytics',
        '10-minute install',
        'Community support',
      ],
      cta: 'Book a call', ctaHref: 'mailto:revan@tryon.global?subject=Tryon%20Free%20plan',
    },
    {
      name: 'Studio', price: '$149', priceSub: 'per month',
      headline: 'For SMB Shopify brands testing 3D try-on.',
      features: [
        '2,500 try-on sessions per month',
        '15 garment uploads',
        'Custom-branded widget',
        'Size recommendation v1',
        'Basic analytics dashboard',
        'Email support, 48h SLA',
      ],
      cta: 'Book a call', ctaHref: 'mailto:revan@tryon.global?subject=Tryon%20Studio%20plan',
    },
    {
      name: 'Brand', price: '$2,490', priceSub: 'per month',
      setup: '+ $1,500 one-time setup',
      highlight: true,
      headline: 'For Shopify Plus brands losing $5K to $50K a month to returns.',
      features: [
        '40,000 try-on sessions per month',
        '100 garment uploads',
        'Full cohort + funnel analytics',
        'Size recommendation v2 with confidence',
        'Return-reason export',
        'Cohort dashboards + A/B testing',
        'Shopify webhook integration',
        'Slack support, 24h SLA',
      ],
      cta: 'Book a call', ctaHref: 'mailto:revan@tryon.global?subject=Tryon%20Brand%20plan',
    },
    {
      name: 'Scale', price: 'Custom', priceSub: 'talk to us',
      setup: '+ $7,500 onboarding',
      headline: 'For multi-brand houses and DTC scale-ups losing six figures a month.',
      features: [
        '250,000 sessions included',
        'Unlimited garment uploads',
        'Multi-brand workspace',
        'Custom avatar pipeline',
        'Stressmaps and dedicated CSM',
        'SLA and SOC2 documentation',
        'Custom analytics export',
        'White-label option',
      ],
      cta: 'Book a call', ctaHref: 'mailto:revan@tryon.global?subject=Tryon%20Scale%20pricing',
    },
  ];

  return (
    <section style={{ padding: '24px 20px 64px', background: C.bg }}>
      <div style={{
        maxWidth: 1280, margin: '0 auto',
        display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 0,
        border: `1px solid ${C.line}`, background: C.surface,
      }}>
        {tiers.map((t, i) => {
          const dark = !!t.highlight;
          const bg = dark ? C.cardBg : C.surface;
          const ink = dark ? C.cardInk : C.ink;
          const mute = dark ? C.cardMute : C.mute;
          return (
            <div key={t.name} style={{
              background: bg, color: ink,
              borderRight: i < tiers.length - 1 ? `1px solid ${C.line}` : 'none',
              padding: '28px 22px',
              display: 'flex', flexDirection: 'column', gap: 16,
            }}>
              <div>
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 13, color: mute, fontWeight: 600, marginBottom: 10,
                  display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
                }}>
                  {t.name}
                  {t.highlight && (
                    <span style={{
                      background: ink, color: bg,
                      padding: '2px 8px',
                      fontSize: 10, fontWeight: 700,
                    }}>Most popular</span>
                  )}
                </div>
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 40, fontWeight: 700,
                  letterSpacing: '-0.025em', lineHeight: 1, color: ink,
                }}>{t.price}</div>
                {t.priceSub && (
                  <div style={{
                    fontFamily: 'var(--display)', fontSize: 13, color: mute, marginTop: 6,
                  }}>{t.priceSub}</div>
                )}
                {t.setup && (
                  <div style={{
                    fontFamily: 'var(--display)', fontSize: 12, color: mute, marginTop: 4,
                  }}>{t.setup}</div>
                )}
              </div>
              <p style={{
                ...bodyStyle, fontSize: 13, lineHeight: 1.5, margin: 0,
                color: ink, opacity: dark ? 0.85 : 0.78,
              }}>{t.headline}</p>
              <ul style={{
                listStyle: 'none', padding: 0, margin: 0,
                display: 'flex', flexDirection: 'column', gap: 8,
                borderTop: `1px solid ${dark ? C.cardLine : C.line}`, paddingTop: 16,
              }}>
                {t.features.map(f => (
                  <li key={f} style={{
                    fontFamily: 'var(--display)', fontSize: 12.5, lineHeight: 1.5, color: ink,
                    opacity: dark ? 0.92 : 0.88,
                    paddingLeft: 14, position: 'relative',
                  }}>
                    <span style={{
                      position: 'absolute', left: 0, top: 6,
                      width: 5, height: 5,
                      background: ink, opacity: 0.5,
                    }} />
                    {f}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => {
                  if (t.ctaHref.startsWith('mailto:')) window.location.href = t.ctaHref;
                  else router.push(t.ctaHref);
                }}
                style={{
                  marginTop: 'auto',
                  background: dark ? C.cardInk : C.ink,
                  color: dark ? C.cardBg : C.bg,
                  padding: '12px 16px', borderRadius: 16, border: 'none',
                  fontFamily: 'var(--display)', fontSize: 13.5, fontWeight: 600, cursor: 'pointer',
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                }}
              >{t.cta} <span>→</span></button>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ROI({ C }: { C: Palette }) {
  const cases = [
    { label: 'Starting brand', orders: '600 orders / month', aov: '$70 AOV', returnRate: '25% return rate',
      monthlyReturnCost: '$2,700', ourPrice: '$149', monthlySavings: '$540', tier: 'Studio' },
    { label: 'Mid-tier brand', orders: '10,000 orders / month', aov: '$115 AOV', returnRate: '30% return rate',
      monthlyReturnCost: '$96,000', ourPrice: '$2,490', monthlySavings: '$19,200', tier: 'Brand' },
    { label: 'Scale brand', orders: '80,000 orders / month', aov: '$160 AOV', returnRate: '35% return rate',
      monthlyReturnCost: '$1,260,000', ourPrice: 'Custom', monthlySavings: '$252,000', tier: 'Scale' },
  ];
  return (
    <section style={{ background: C.surface, color: C.ink, padding: '64px 20px', borderTop: `1px solid ${C.line}` }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <h2 style={{ ...headingStyle('clamp(32px, 4.5vw, 64px)'), marginBottom: 14, maxWidth: 1000 }}>
          Three brands. Every ROI positive.
        </h2>
        <p style={{ ...bodyStyle, color: C.mute, maxWidth: 720, marginBottom: 48 }}>
          Industry data, conservative assumptions. Capital One Shopping puts apparel return rates at 25 to 40 percent. Zeta and Optoro put cost-per-return at $18 to $45. Conservative virtual try-on return reduction sits at 20 percent.
        </p>

        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 0,
          border: `1px solid ${C.line}`, background: C.bg,
        }}>
          {cases.map((c) => (
            <div key={c.label} style={{
              borderRight: `1px solid ${C.line}`,
              borderBottom: `1px solid ${C.line}`,
              padding: '24px 22px',
              display: 'flex', flexDirection: 'column', gap: 14,
            }}>
              <div style={{ fontFamily: 'var(--display)', fontSize: 14, color: C.ink, fontWeight: 600 }}>
                {c.label}
              </div>
              <div style={{ fontFamily: 'var(--display)', fontSize: 13, color: C.mute, lineHeight: 1.7 }}>
                {c.orders}<br/>{c.aov}<br/>{c.returnRate}
              </div>
              <div style={{ height: 1, background: C.line }} />
              <div>
                <div style={{ fontFamily: 'var(--display)', fontSize: 12, color: C.mute, marginBottom: 4 }}>
                  Current monthly return cost
                </div>
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 22, fontWeight: 600,
                  letterSpacing: '-0.02em', color: C.ink,
                }}>{c.monthlyReturnCost}</div>
              </div>
              <div>
                <div style={{ fontFamily: 'var(--display)', fontSize: 12, color: C.mute, marginBottom: 4 }}>
                  Monthly savings with TryOn
                </div>
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 28, fontWeight: 700,
                  letterSpacing: '-0.02em', color: C.ink,
                }}>{c.monthlySavings}</div>
              </div>
              <div style={{ height: 1, background: C.line }} />
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <div>
                  <div style={{ fontFamily: 'var(--display)', fontSize: 12, color: C.mute, marginBottom: 4 }}>
                    You pay
                  </div>
                  <div style={{
                    fontFamily: 'var(--display)', fontSize: 18, fontWeight: 600,
                    letterSpacing: '-0.02em', color: C.ink,
                  }}>{c.ourPrice}</div>
                </div>
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 12, fontWeight: 600,
                  color: C.ink, padding: '3px 8px',
                  border: `1px solid ${C.ink}`,
                }}>{c.tier}</div>
              </div>
            </div>
          ))}
        </div>
        <div style={{
          marginTop: 14, fontFamily: 'var(--display)', fontSize: 12, color: C.mute,
        }}>
          Sources: Capital One Shopping 2024, Zeta 2025, Optoro 2024, McKinsey State of Fashion 2025.
        </div>
      </div>
    </section>
  );
}

function FAQ({ C }: { C: Palette }) {
  const items = [
    { q: 'How do you count a try-on session?',
      a: 'A session is one shopper opening the TryOn widget on a product page and rendering at least one garment. Page views without a render do not count. Session counts reset monthly.' },
    { q: 'Do you charge per garment upload?',
      a: 'No. Garment counts are tier limits, not per-garment fees. We do not believe in per-asset pricing because it punishes brands for adding inventory.' },
    { q: 'What happens if I exceed my tier limit?',
      a: 'Free and Studio hard-cap at the monthly limit. Brand and Scale tiers allow overage at $0.04 per session billed monthly in arrears. We will warn you at 80 and 100 percent before charging.' },
    { q: 'How long does Shopify integration take?',
      a: '8 lines of code in your theme. Brands usually go live in under a week. Studio and above get a Slack channel with our team during install.' },
    { q: 'Are you EU Digital Product Passport ready?',
      a: 'Every garment we render is structurally a 3D digital twin. We are aligning our metadata schema with the ESPR textile delegated act due late 2026 / early 2027 so brands can plug TryOn assets into their DPP records when the regulation lands.' },
    { q: 'Can I try before I commit?',
      a: 'Yes. Free tier is forever-free, no credit card. 200 sessions per month is enough to validate the experience on your store before upgrading.' },
  ];
  const [open, setOpen] = useState<number | null>(0);
  return (
    <section style={{ background: C.bg, color: C.ink, padding: '64px 20px', borderTop: `1px solid ${C.line}` }}>
      <div style={{ maxWidth: 880, margin: '0 auto' }}>
        <h2 style={{ ...headingStyle('clamp(28px, 4vw, 56px)'), marginBottom: 28 }}>
          Questions we get from brands.
        </h2>
        <div style={{ border: `1px solid ${C.line}`, background: C.surface }}>
          {items.map((it, i) => {
            const isOpen = open === i;
            return (
              <div key={it.q} style={{
                borderBottom: i < items.length - 1 ? `1px solid ${C.line}` : 'none',
              }}>
                <button
                  onClick={() => setOpen(isOpen ? null : i)}
                  style={{
                    width: '100%', textAlign: 'left',
                    padding: '18px 22px',
                    background: 'transparent', border: 'none', cursor: 'pointer',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16,
                    color: C.ink,
                  }}
                >
                  <span style={{
                    fontFamily: 'var(--display)', fontSize: 16, fontWeight: 600,
                    letterSpacing: '-0.005em',
                  }}>{it.q}</span>
                  <span style={{
                    fontFamily: 'var(--display)', fontSize: 16, color: C.mute,
                    transform: isOpen ? 'rotate(45deg)' : 'rotate(0)',
                    transition: 'transform 0.2s ease',
                    flexShrink: 0,
                  }}>+</span>
                </button>
                {isOpen && (
                  <div style={{
                    padding: '0 22px 20px',
                    ...bodyStyle, fontSize: 14, color: C.mute,
                    maxWidth: 720,
                  }}>{it.a}</div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function FinalCTA({ C }: { C: Palette }) {
  const router = useRouter();
  return (
    <section style={{ background: C.surface, color: C.ink, padding: '64px 20px 80px', borderTop: `1px solid ${C.line}` }}>
      <div style={{ maxWidth: 720, margin: '0 auto', textAlign: 'center' }}>
        <h2 style={{ ...headingStyle('clamp(36px, 4.5vw, 64px)'), marginBottom: 14 }}>
          Start with a call. Live within a week.
        </h2>
        <p style={{ ...bodyStyle, fontSize: 15, color: C.mute, margin: '0 auto 28px', maxWidth: 540 }}>
          Every plan starts with a short call. We install the widget on your store with you, you watch the conversion data, and if it is not better than your last marketing spend, you do not pay.
        </p>
        <div style={{ display: 'inline-flex', gap: 10, flexWrap: 'wrap', justifyContent: 'center' }}>
          <button
            onClick={() => { window.location.href = 'mailto:revan@tryon.global?subject=Tryon%20for%20my%20brand'; }}
            style={{
              background: '#0040FF', color: '#FFFFFF', border: 'none',
              padding: '14px 24px',
              fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600,
              letterSpacing: '-0.005em', cursor: 'pointer',
              display: 'inline-flex', alignItems: 'center', gap: 10,
              borderRadius: 9999,
              transition: 'background 180ms cubic-bezier(0.4, 0, 0.2, 1)',
            }}
          >Book a call <span>→</span></button>
          <button
            onClick={() => router.push('/demo')}
            style={{
              background: 'transparent', color: C.ink,
              border: `1px solid ${C.ink}`,
              padding: '14px 24px',
              fontFamily: 'var(--display)', fontSize: 14, fontWeight: 600,
              letterSpacing: '-0.005em', cursor: 'pointer',
              display: 'inline-flex', alignItems: 'center', gap: 10,
              borderRadius: 9999,
            }}
          >Try the demo</button>
        </div>
      </div>
    </section>
  );
}

function Footer({ C }: { C: Palette }) {
  const router = useRouter();
  return (
    <section style={{ background: C.bg, color: C.ink, padding: '36px 32px 44px' }}>
      <div style={{
        maxWidth: 1280, margin: '0 auto',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 24,
        flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={C.ink === '#0A0A0A' ? '/redesign/wordmark.png' : '/redesign/wordmark-white.png'}
            alt="TryOn"
            style={{ height: 14, width: 'auto', display: 'block' }}
          />
          <div style={{ fontFamily: 'var(--display)', fontSize: 13, color: C.mute }}>
            TryOn, 2026
          </div>
        </div>
        <div style={{ display: 'flex', gap: 22 }}>
          {[
            { label: 'Home', href: '/' },
            { label: 'Demo', href: '/demo' },
            { label: 'Privacy', href: '/privacy' },
            { label: 'Sign in', href: '/login' },
          ].map(it => (
            <button
              key={it.label}
              onClick={() => router.push(it.href)}
              style={{
                background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                fontFamily: 'var(--display)', fontSize: 13, color: C.mute, fontWeight: 500,
              }}
            >{it.label}</button>
          ))}
        </div>
      </div>
    </section>
  );
}

export default function PricingPage() {
  const { theme } = useTheme();
  const dark = theme === 'dark';
  const C = dark ? PAL.dark : PAL.light;
  const mobile = useIsMobile();

  const links = [
    { label: 'Home', href: '/' },
    { label: 'Pricing', href: '/pricing', active: true },
    { label: 'Demo', href: '/demo' },
    { label: 'Shoppers', href: '/signup' },
    { label: 'Deck', href: '/pitch-deck.html', external: true },
  ];

  return (
    <div className="tryon-redesign-root" style={{
      width: '100%', minHeight: '100vh',
      background: C.bg, color: C.ink, position: 'relative',
    }}>
      <SharedNav
        dark={dark}
        links={links}
        rightSlot={mobile ? (
          <NavCta dark={dark} label="Contact us" onClick={() => { window.location.href = 'mailto:revan@tryon.global?subject=Tryon%20for%20my%20brand'; }} />
        ) : (
          <>
            <AuthAwareSignInLink dark={dark} />
            <NavCta dark={dark} label="Contact us →" onClick={() => { window.location.href = 'mailto:revan@tryon.global?subject=Tryon%20for%20my%20brand'; }} />
          </>
        )}
      />
      <Hero C={C} />
      <Tiers C={C} />
      <ROI C={C} />
      <FAQ C={C} />
      <FinalCTA C={C} />
      <Footer C={C} />
    </div>
  );
}
