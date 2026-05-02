'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from '@/contexts/ThemeContext';

const PAL = {
  light: {
    void: '#ffffff', ash: '#fafafa', steel: '#f5f4ef', iron: '#ebebe5',
    bone: '#0A0A0A', dim: '#6E6E6E', faint: '#D8D4C9',
    slit: 'rgba(0,0,0,0.07)',
    cardBg: '#0A0A0A', cardInk: '#F2F1EC',
    cardHair: 'rgba(255,255,255,0.12)', cardDim: '#9A9A9A',
  },
  dark: {
    void: '#0A0A0A', ash: '#0E0E0E', steel: '#141414', iron: '#1A1A1A',
    bone: '#F2F1EC', dim: '#8A8A8A', faint: '#252525',
    slit: 'rgba(255,255,255,0.05)',
    cardBg: '#F2F1EC', cardInk: '#0A0A0A',
    cardHair: 'rgba(0,0,0,0.12)', cardDim: '#6E6E6E',
  },
};

function useSmartNav() {
  const [hidden, setHidden] = useState(false);
  useEffect(() => {
    let lastY = window.scrollY;
    let downAccum = 0;
    let raf = 0;
    const onScroll = () => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        const y = window.scrollY;
        const dy = y - lastY;
        lastY = y;
        raf = 0;
        if (y < 100) { downAccum = 0; setHidden(false); return; }
        if (dy < 0) { downAccum = 0; setHidden(false); return; }
        downAccum += dy;
        if (downAccum > 60) setHidden(true);
      });
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  return hidden;
}

type Palette = typeof PAL.light;

function Nav({ C }: { C: Palette }) {
  const router = useRouter();
  const hidden = useSmartNav();
  const cap: React.CSSProperties = {
    background: C.bone === '#0A0A0A' ? 'rgba(255,255,255,0.78)' : 'rgba(10,10,10,0.72)',
    border: `1px solid ${C.faint}`,
    boxShadow: '0 8px 24px rgba(10,10,10,0.06), 0 1px 3px rgba(10,10,10,0.04)',
    backdropFilter: 'saturate(180%) blur(20px)',
    WebkitBackdropFilter: 'saturate(180%) blur(20px)',
  };
  return (
    <div style={{
      position: 'sticky', top: 0, zIndex: 70,
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '14px 20px',
      pointerEvents: 'none',
      transform: hidden ? 'translateY(-110%)' : 'translateY(0)',
      transition: 'transform 0.28s cubic-bezier(0.4, 0.0, 0.2, 1)',
    }}>
      <div style={{
        ...cap, pointerEvents: 'auto',
        display: 'inline-flex', alignItems: 'center',
        gap: 22, padding: '10px 18px 10px 14px', borderRadius: 999,
      }}>
        <button
          type="button"
          onClick={() => router.push('/')}
          style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', display: 'inline-flex' }}
          aria-label="TRYON home"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={C.bone === '#0A0A0A' ? '/redesign/wordmark.png' : '/redesign/wordmark-white.png'}
            alt="TRYON"
            style={{ height: 22, width: 'auto', display: 'block' }}
          />
        </button>
        <div style={{ width: 1, height: 18, background: C.faint }} />
        <div style={{ display: 'flex', gap: 22 }}>
          <button
            onClick={() => router.push('/')}
            style={{
              border: 0, padding: 0, background: 'transparent', cursor: 'pointer',
              fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
              color: C.dim, textTransform: 'uppercase', fontWeight: 500,
            }}
          >HOME</button>
          <span style={{
            fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
            color: C.bone, textTransform: 'uppercase', fontWeight: 700,
          }}>PRICING</span>
        </div>
      </div>
      <div style={{
        ...cap, pointerEvents: 'auto',
        display: 'inline-flex', alignItems: 'stretch',
        padding: 4, gap: 4, borderRadius: 999,
      }}>
        <button
          onClick={() => router.push('/login')}
          style={{
            padding: '9px 16px', background: 'transparent', border: 'none', color: C.bone,
            fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
            textTransform: 'uppercase', fontWeight: 500, cursor: 'pointer',
          }}
        >SIGN IN</button>
        <button
          onClick={() => router.push('/signup?type=brand')}
          style={{
            padding: '9px 16px',
            background: C.bone, color: C.void, border: 'none',
            fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
            textTransform: 'uppercase', fontWeight: 700, cursor: 'pointer',
            display: 'inline-flex', alignItems: 'center', gap: 8, borderRadius: 999,
          }}
        >START FREE<span style={{ fontSize: 12 }}>→</span></button>
      </div>
    </div>
  );
}

function Hero({ C }: { C: Palette }) {
  return (
    <section style={{
      background: C.void, color: C.bone,
      padding: '96px 32px 48px', maxWidth: 1280, margin: '0 auto',
    }}>
      <div style={{
        fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.4em',
        color: C.dim, textTransform: 'uppercase', marginBottom: 24,
      }}>FOR BRANDS · FASHION E-COMMERCE</div>
      <h1 style={{
        fontFamily: 'var(--display)', fontWeight: 900,
        fontSize: 'clamp(64px, 9vw, 144px)', letterSpacing: '-0.05em', lineHeight: 0.84,
        margin: '0 0 28px', textTransform: 'uppercase', maxWidth: 1100,
      }}>
        PAY LESS THAN<br/>
        <span style={{ WebkitTextStroke: `2px ${C.bone}`, color: 'transparent' }}>ONE RETURN</span> A DAY.
      </h1>
      <p style={{
        fontSize: 18, lineHeight: 1.55, margin: '0 0 8px', maxWidth: 720,
        color: C.bone, opacity: 0.8, fontWeight: 500,
      }}>
        TRYON costs less than the value of returns we save you. The math is simple: every paid tier prices at well under 30% of the dollar value of returns prevented at conservative assumptions.
      </p>
      <p style={{
        fontSize: 14, lineHeight: 1.55, margin: 0, maxWidth: 720,
        color: C.dim,
      }}>
        Built for Shopify Plus fashion brands losing six figures a month to returns. Pricing in USD, billed monthly. EU and UK customers invoiced in EUR or GBP.
      </p>
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
      name: 'FREE',
      price: '$0',
      priceSub: 'forever',
      headline: 'Try it on your store in 10 minutes.',
      features: [
        '200 try-on sessions / mo',
        '3 garment uploads',
        'Branded TRYON widget',
        'Basic funnel analytics',
        'Self-serve install',
        'Community support',
      ],
      cta: 'Start free',
      ctaHref: '/signup?type=brand',
    },
    {
      name: 'STUDIO',
      price: '$149',
      priceSub: '/ month',
      headline: 'For SMB Shopify brands testing 3D try-on.',
      features: [
        '2,500 try-on sessions / mo',
        '15 garment uploads',
        'Custom-branded widget',
        'Size recommendation v1',
        'Basic analytics dashboard',
        'Email support, 48h SLA',
      ],
      cta: 'Start',
      ctaHref: '/signup?type=brand&plan=studio',
    },
    {
      name: 'BRAND',
      price: '$2,490',
      priceSub: '/ month',
      setup: '+ $1,500 one-time setup',
      highlight: true,
      headline: 'For Shopify Plus brands losing $5K to $50K a month to returns.',
      features: [
        '40,000 try-on sessions / mo',
        '100 garment uploads',
        'Full Palantir-grade analytics',
        'Size recommendation v2 + confidence',
        'Return-reason export',
        'Cohort dashboards + A/B testing',
        'Shopify webhook integration',
        'Slack support, 24h SLA',
      ],
      cta: 'Start',
      ctaHref: '/signup?type=brand&plan=brand',
    },
    {
      name: 'SCALE',
      price: 'Custom',
      priceSub: 'talk to us',
      setup: '+ $7,500 onboarding',
      headline: 'For multi-brand houses and DTC scale-ups losing six figures a month.',
      features: [
        '250,000 sessions included',
        'Unlimited garment uploads',
        'Multi-brand workspace',
        'Custom avatar pipeline',
        'Stressmaps + dedicated CSM',
        'SLA + SOC2 documentation',
        'Custom analytics export',
        'White-label option',
      ],
      cta: 'Book a call',
      ctaHref: 'mailto:revandiktas1@gmail.com?subject=TryOn%20Scale%20pricing',
    },
  ];
  return (
    <section style={{
      padding: '32px 32px 96px', maxWidth: 1280, margin: '0 auto',
    }}>
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 0,
        border: `1px solid ${C.faint}`, background: C.ash,
      }}>
        {tiers.map((t, i) => {
          const dark = !!t.highlight;
          const bg = dark ? C.bone : C.ash;
          const ink = dark ? C.void : C.bone;
          const dim = dark ? 'rgba(255,255,255,0.6)' : C.dim;
          const hair = dark ? 'rgba(255,255,255,0.18)' : C.faint;
          return (
            <div key={t.name} style={{
              background: bg, color: ink,
              borderRight: i < tiers.length - 1 ? `1px solid ${C.faint}` : 'none',
              padding: '32px 24px 32px',
              display: 'flex', flexDirection: 'column', gap: 18,
            }}>
              <div>
                <div style={{
                  fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
                  color: dim, textTransform: 'uppercase', fontWeight: 700, marginBottom: 12,
                }}>{t.name}{t.highlight ? ' · MOST POPULAR' : ''}</div>
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 48, fontWeight: 900,
                  letterSpacing: '-0.04em', lineHeight: 1, color: ink,
                }}>{t.price}</div>
                {t.priceSub && (
                  <div style={{
                    fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.18em',
                    color: dim, textTransform: 'uppercase', marginTop: 6,
                  }}>{t.priceSub}</div>
                )}
                {t.setup && (
                  <div style={{
                    fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.18em',
                    color: dim, textTransform: 'uppercase', marginTop: 4,
                  }}>{t.setup}</div>
                )}
              </div>
              <p style={{
                fontSize: 13, lineHeight: 1.5, margin: 0,
                color: ink, opacity: dark ? 0.85 : 0.78,
              }}>{t.headline}</p>
              <ul style={{
                listStyle: 'none', padding: 0, margin: 0,
                display: 'flex', flexDirection: 'column', gap: 8,
                borderTop: `1px solid ${hair}`, paddingTop: 18,
              }}>
                {t.features.map(f => (
                  <li key={f} style={{
                    fontSize: 12.5, lineHeight: 1.45, color: ink,
                    opacity: dark ? 0.9 : 0.85,
                    paddingLeft: 14, position: 'relative',
                  }}>
                    <span style={{
                      position: 'absolute', left: 0, top: 6,
                      width: 6, height: 6, background: ink, opacity: 0.5,
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
                  background: dark ? C.void : C.bone,
                  color: dark ? C.bone : C.void,
                  padding: '14px 18px', borderRadius: 999, border: 'none',
                  fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.28em',
                  textTransform: 'uppercase', fontWeight: 800, cursor: 'pointer',
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                }}
              >{t.cta} <span style={{ fontSize: 14 }}>→</span></button>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ROI({ C }: { C: Palette }) {
  const cases = [
    {
      label: 'STARTING BRAND',
      orders: '600 orders/mo',
      aov: '$70 AOV',
      returnRate: '25% return rate',
      monthlyReturnCost: '$2,700',
      ourPrice: '$149',
      monthlySavings: '$540',
      tier: 'STUDIO',
    },
    {
      label: 'MID-TIER BRAND',
      orders: '10,000 orders/mo',
      aov: '$115 AOV',
      returnRate: '30% return rate',
      monthlyReturnCost: '$96,000',
      ourPrice: '$2,490',
      monthlySavings: '$19,200',
      tier: 'BRAND',
    },
    {
      label: 'SCALE BRAND',
      orders: '80,000 orders/mo',
      aov: '$160 AOV',
      returnRate: '35% return rate',
      monthlyReturnCost: '$1,260,000',
      ourPrice: 'Custom',
      monthlySavings: '$252,000',
      tier: 'SCALE',
    },
  ];
  return (
    <section style={{
      background: C.ash, color: C.bone, padding: '96px 32px',
    }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <div style={{
          fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.4em',
          color: C.dim, textTransform: 'uppercase', marginBottom: 18,
        }}>THE MATH</div>
        <h2 style={{
          fontFamily: 'var(--display)', fontWeight: 900, margin: '0 0 18px',
          fontSize: 'clamp(48px, 6.5vw, 96px)', letterSpacing: '-0.04em', lineHeight: 0.86,
          textTransform: 'uppercase', maxWidth: 1000,
        }}>
          THREE BRANDS.<br/>
          <span style={{ WebkitTextStroke: `2px ${C.bone}`, color: 'transparent' }}>EVERY ROI</span> POSITIVE.
        </h2>
        <p style={{
          fontSize: 15, lineHeight: 1.55, margin: '0 0 48px', maxWidth: 720,
          color: C.bone, opacity: 0.78,
        }}>
          Industry data, conservative assumptions. Capital One Shopping puts apparel return rates at 25 to 40 percent. Zeta and Optoro put cost-per-return at $18 to $45. Conservative virtual try-on return reduction sits at 20 percent. Math below uses those numbers.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 0, border: `1px solid ${C.faint}` }}>
          {cases.map((c, i) => (
            <div key={c.label} style={{
              background: C.steel,
              borderRight: i < cases.length - 1 ? `1px solid ${C.faint}` : 'none',
              padding: '32px 28px',
              display: 'flex', flexDirection: 'column', gap: 14,
            }}>
              <div style={{
                fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
                color: C.dim, textTransform: 'uppercase', fontWeight: 700,
              }}>{c.label}</div>
              <div style={{
                fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.12em',
                color: C.bone, opacity: 0.6, lineHeight: 1.6,
              }}>
                {c.orders}<br/>{c.aov}<br/>{c.returnRate}
              </div>
              <div style={{ height: 1, background: C.faint }} />
              <div>
                <div style={{
                  fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.32em',
                  color: C.dim, textTransform: 'uppercase', marginBottom: 4,
                }}>CURRENT MONTHLY RETURN COST</div>
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 28, fontWeight: 900,
                  letterSpacing: '-0.03em', color: C.bone,
                }}>{c.monthlyReturnCost}</div>
              </div>
              <div>
                <div style={{
                  fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.32em',
                  color: C.dim, textTransform: 'uppercase', marginBottom: 4,
                }}>MONTHLY SAVINGS WITH TRYON</div>
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 36, fontWeight: 900,
                  letterSpacing: '-0.03em', color: C.bone,
                }}>{c.monthlySavings}</div>
              </div>
              <div style={{ height: 1, background: C.faint }} />
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
              }}>
                <div>
                  <div style={{
                    fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.32em',
                    color: C.dim, textTransform: 'uppercase', marginBottom: 4,
                  }}>TIER · YOU PAY</div>
                  <div style={{
                    fontFamily: 'var(--display)', fontSize: 22, fontWeight: 900,
                    letterSpacing: '-0.03em', color: C.bone,
                  }}>{c.ourPrice}</div>
                </div>
                <div style={{
                  fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.28em',
                  color: C.bone, fontWeight: 700, textTransform: 'uppercase',
                  border: `1px solid ${C.bone}`, padding: '4px 8px',
                }}>{c.tier}</div>
              </div>
            </div>
          ))}
        </div>
        <div style={{
          marginTop: 18,
          fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.28em',
          color: C.dim, textTransform: 'uppercase',
        }}>SOURCES · CAPITAL ONE SHOPPING 2024 · ZETA 2025 · OPTORO 2024 · MCKINSEY STATE OF FASHION 2025</div>
      </div>
    </section>
  );
}

function FAQ({ C }: { C: Palette }) {
  const items = [
    {
      q: 'How do you count a "try-on session"?',
      a: 'A session is one shopper opening the TRYON widget on a product page and rendering at least one garment. Page views without a render do not count. Session counts reset monthly.',
    },
    {
      q: 'Do you charge per garment upload?',
      a: 'No. Garment counts are tier limits, not per-garment fees. We do not believe in per-asset pricing because it punishes brands for adding inventory.',
    },
    {
      q: 'What happens if I exceed my tier limit?',
      a: 'Free and Studio hard-cap at the monthly limit. Brand and Scale tiers allow overage at $0.04 per session billed monthly in arrears. We will warn you at 80 percent and 100 percent before charging.',
    },
    {
      q: 'How long does Shopify integration take?',
      a: '8 lines of code in your theme. Brands usually go live in under a week. Studio and above get a Slack channel with our team during install.',
    },
    {
      q: 'Are you EU Digital Product Passport ready?',
      a: 'Every garment we render is structurally a 3D digital twin. We are aligning our metadata schema with the ESPR textile delegated act due late 2026 / early 2027 so brands can plug TryOn assets into their DPP records when the regulation lands.',
    },
    {
      q: 'Can I try before I commit?',
      a: 'Yes. Free tier is forever-free, no credit card. 200 sessions per month is enough to validate the experience on your store before upgrading.',
    },
  ];
  const [open, setOpen] = useState<number | null>(0);
  return (
    <section style={{
      background: C.void, color: C.bone, padding: '96px 32px',
    }}>
      <div style={{ maxWidth: 880, margin: '0 auto' }}>
        <div style={{
          fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.4em',
          color: C.dim, textTransform: 'uppercase', marginBottom: 18,
        }}>FAQ</div>
        <h2 style={{
          fontFamily: 'var(--display)', fontWeight: 900, margin: '0 0 36px',
          fontSize: 'clamp(40px, 5vw, 72px)', letterSpacing: '-0.04em', lineHeight: 0.9,
          textTransform: 'uppercase',
        }}>
          QUESTIONS WE GET FROM BRANDS.
        </h2>
        <div style={{ border: `1px solid ${C.faint}` }}>
          {items.map((it, i) => {
            const isOpen = open === i;
            return (
              <div key={it.q} style={{
                borderBottom: i < items.length - 1 ? `1px solid ${C.faint}` : 'none',
                background: C.ash,
              }}>
                <button
                  onClick={() => setOpen(isOpen ? null : i)}
                  style={{
                    width: '100%', textAlign: 'left',
                    padding: '20px 24px',
                    background: 'transparent', border: 'none', cursor: 'pointer',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    color: C.bone,
                  }}
                >
                  <span style={{
                    fontFamily: 'var(--display)', fontSize: 17, fontWeight: 700,
                    letterSpacing: '-0.01em',
                  }}>{it.q}</span>
                  <span style={{
                    fontFamily: 'var(--mono)', fontSize: 16, color: C.dim,
                    transform: isOpen ? 'rotate(45deg)' : 'rotate(0)',
                    transition: 'transform 0.2s ease',
                  }}>+</span>
                </button>
                {isOpen && (
                  <div style={{
                    padding: '0 24px 22px',
                    fontSize: 14, lineHeight: 1.6, color: C.bone, opacity: 0.78,
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
    <section style={{
      background: C.ash, color: C.bone, padding: '96px 32px 120px',
    }}>
      <div style={{
        maxWidth: 880, margin: '0 auto', textAlign: 'center',
      }}>
        <h2 style={{
          fontFamily: 'var(--display)', fontWeight: 900, margin: '0 0 16px',
          fontSize: 'clamp(48px, 6.5vw, 96px)', letterSpacing: '-0.04em', lineHeight: 0.88,
          textTransform: 'uppercase',
        }}>
          INSTALL FREE.<br/>
          <span style={{ WebkitTextStroke: `2px ${C.bone}`, color: 'transparent' }}>UPGRADE</span> WHEN IT WORKS.
        </h2>
        <p style={{
          fontSize: 16, lineHeight: 1.55, margin: '0 auto 36px', maxWidth: 560,
          color: C.bone, opacity: 0.8,
        }}>
          200 free sessions. No credit card. 10 minutes to live on your store. If the conversion data is not better than your last marketing spend, do not upgrade.
        </p>
        <div style={{ display: 'inline-flex', gap: 12, flexWrap: 'wrap', justifyContent: 'center' }}>
          <button
            onClick={() => router.push('/signup?type=brand')}
            style={{
              background: C.bone, color: C.void, border: 'none',
              padding: '18px 28px',
              fontFamily: 'var(--mono)', fontSize: 12, letterSpacing: '0.32em',
              textTransform: 'uppercase', fontWeight: 800, cursor: 'pointer',
              display: 'inline-flex', alignItems: 'center', gap: 12,
              borderRadius: 999,
            }}
          >START FREE <span style={{ fontSize: 16 }}>→</span></button>
          <button
            onClick={() => { window.location.href = 'mailto:revandiktas1@gmail.com?subject=TryOn%20Brand%20Demo'; }}
            style={{
              background: 'transparent', color: C.bone,
              border: `1px solid ${C.bone}`,
              padding: '18px 28px',
              fontFamily: 'var(--mono)', fontSize: 12, letterSpacing: '0.32em',
              textTransform: 'uppercase', fontWeight: 800, cursor: 'pointer',
              display: 'inline-flex', alignItems: 'center', gap: 12,
              borderRadius: 999,
            }}
          >BOOK A CALL</button>
        </div>
      </div>
    </section>
  );
}

function Footer({ C }: { C: Palette }) {
  const router = useRouter();
  return (
    <section style={{
      background: C.void, color: C.bone, padding: '64px 32px 48px',
      borderTop: `1px solid ${C.faint}`,
    }}>
      <div style={{
        maxWidth: 1280, margin: '0 auto',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 32,
        flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', gap: 18, alignItems: 'center' }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={C.bone === '#0A0A0A' ? '/redesign/wordmark.png' : '/redesign/wordmark-white.png'}
            alt="TRYON"
            style={{ height: 18, width: 'auto', display: 'block' }}
          />
          <div style={{ width: 1, height: 14, background: C.faint }} />
          <div style={{
            fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
            color: C.dim, textTransform: 'uppercase',
          }}>FIT FOLLOWS · TRYON · MMXXVI</div>
        </div>
        <div style={{ display: 'flex', gap: 22 }}>
          {[
            { label: 'HOME', href: '/' },
            { label: 'PRIVACY', href: '/privacy' },
            { label: 'DEMO', href: '/demo' },
            { label: 'SIGN IN', href: '/login' },
          ].map(it => (
            <button
              key={it.label}
              onClick={() => router.push(it.href)}
              style={{
                background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.32em',
                color: C.dim, textTransform: 'uppercase', fontWeight: 500,
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
  return (
    <div style={{
      width: '100%', minHeight: '100vh',
      background: C.void, color: C.bone, position: 'relative',
    }}>
      <Nav C={C} />
      <Hero C={C} />
      <Tiers C={C} />
      <ROI C={C} />
      <FAQ C={C} />
      <FinalCTA C={C} />
      <Footer C={C} />
    </div>
  );
}
