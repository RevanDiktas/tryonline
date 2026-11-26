'use client';

import Link from 'next/link';
import { Site, Header } from '@/components/os/kit';

/* /pricing: size recommendation at two published prices, the operating system by engagement.
   Upper tiers, set-up fees and the results share are discussed on a call, not published. */

const CSS = `
.os .tiers{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px;max-width:960px;margin:0 auto}
.os .tier{border:1px solid var(--rule);border-radius:14px;padding:40px;display:flex;flex-direction:column;align-items:center;text-align:center;gap:18px;background:#fff;
transition:border-color .3s var(--ease)}
.os .tier:hover{border-color:var(--accent)}
.os .tier.top{border-top:2px solid var(--accent)}
.os .price{font-family:var(--f-display),system-ui;font-weight:500;font-size:clamp(2.25rem,1.8rem + 1.6vw,3.25rem);letter-spacing:-.03em;line-height:1}
.os .per{font-size:.9375rem;color:var(--mute)}
.os .tier hr{width:100%;height:1px;background:var(--rule);border:0;margin:6px 0}
@media(max-width:760px){.os .tiers{grid-template-columns:1fr}.os .tier{padding:32px 24px}}
`;

type Tier = { name: string; price: string; per?: string; who: string; line?: string; top?: boolean };

function Tiers({ items }: { items: Tier[] }) {
  return (
    <div className="tiers">
      {items.map((t, i) => (
        <div key={t.name} className={`tier rv${t.top ? ' top' : ''}`} style={{ ['--d' as string]: `${i * 60}ms` }}>
          <span className="eb" style={{ color: t.top ? 'var(--accent)' : undefined }}>{t.name}</span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
            <span className="price">{t.price}</span>{t.per && <span className="per">{t.per}</span>}
          </div>
          <hr />
          <span className="h3" style={{ fontFamily: 'var(--f-display)', fontWeight: 500 }}>{t.who}</span>
          {t.line && <span className="small" style={{ maxWidth: '28ch' }}>{t.line}</span>}
        </div>
      ))}
    </div>
  );
}

export default function PricingPage() {
  return (
    <Site active="/pricing">
      <style dangerouslySetInnerHTML={{ __html: CSS }} />
      <section className="sec" style={{ paddingBottom: 0 }}>
        <div className="wrap">
          <Header as="h1" eyebrow="Pricing" title="Few brands done properly" />
        </div>
      </section>

      <section className="sec" style={{ paddingTop: 0 }}>
        <div className="wrap">
          <Header eyebrow="Size recommendation" title="Every product every shopper" />
          <Tiers items={[
            { name: 'Size', price: '€199', per: 'a month', who: 'For brands' },
            { name: 'Size Plus', price: '€699', per: 'a month', who: 'For bigger brands' },
          ]} />
          <div className="rv" style={{ display: 'flex', justifyContent: 'center', marginTop: 40 }}>
            <Link href="/book" className="btn btn-s">Get started</Link>
          </div>
        </div>
      </section>

      <section className="sec" style={{ borderTop: '1px solid var(--rule)', background: 'var(--tint)' }}>
        <div className="wrap">
          <Header eyebrow="The operating system" title="By engagement" line="3D try-on intelligence and production for brands we choose to work with" />
          <Tiers items={[
            { name: 'Diagnostic', price: '€35,000', who: 'Six weeks on your data', line: 'Credited in full when you continue' },
            { name: 'Operating system', price: '€72,000', per: 'a year and up', who: 'Shopper to factory', line: 'Try-on intelligence stress tests and production', top: true },
          ]} />
          <p className="eb rv" style={{ textAlign: 'center', marginTop: 40 }}>Paid from results on request</p>
          <div className="rv" style={{ display: 'flex', justifyContent: 'center', marginTop: 32 }}>
            <Link href="/book" className="btn btn-p">Apply to work with us</Link>
          </div>
        </div>
      </section>
    </Site>
  );
}
