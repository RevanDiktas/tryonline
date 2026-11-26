'use client';

import type React from 'react';
import Link from 'next/link';
import { Site, Header, Arrow } from '@/components/os/kit';

/* /product: the four products, each with its real pictures or film and three short facts. */

const CSS = `
.os .facts{display:grid;grid-template-columns:repeat(3,1fr);margin-top:56px;border-top:1px solid var(--rule)}
.os .facts li{display:flex;flex-direction:column;align-items:center;text-align:center;gap:10px;padding:28px 24px 0}
.os .facts li+li{border-left:1px solid var(--rule)}
.os .pair{display:grid;grid-template-columns:1.9fr 1fr;gap:24px;align-items:stretch}
@media(max-width:860px){.os .facts{grid-template-columns:1fr}.os .facts li+li{border-left:0;border-top:1px solid var(--rule)}.os .facts li{padding:24px 0}
.os .pair{grid-template-columns:1fr}}
`;

type Fact = { k: string; v: string };

function Facts({ items }: { items: Fact[] }) {
  return (
    <ul className="facts" style={{ listStyle: 'none', padding: 0 }}>
      {items.map((f, i) => (
        <li key={f.k} className="rv" style={{ ['--d' as string]: `${i * 60}ms` }}>
          <span className="eb">{f.k}</span>
          <span className="h3" style={{ fontFamily: 'var(--f-display)', fontWeight: 500 }}>{f.v}</span>
        </li>
      ))}
    </ul>
  );
}

function Product({ id, eyebrow, title, children, facts, more }: { id: string; eyebrow: string; title: string; children: React.ReactNode; facts: Fact[]; more?: { label: string; href: string } }) {
  return (
    <section id={id} className="sec" style={{ borderTop: '1px solid var(--rule)' }}>
      <div className="wrap">
        <Header eyebrow={eyebrow} title={title} />
        <div className="rv" style={{ ['--d' as string]: '120ms' }}>{children}</div>
        <Facts items={facts} />
        {more && (
          <div className="rv" style={{ display: 'flex', justifyContent: 'center', marginTop: 40 }}>
            <Link href={more.href} className="btn btn-t">{more.label} <Arrow /></Link>
          </div>
        )}
      </div>
    </section>
  );
}

export default function ProductPage() {
  return (
    <Site active="/product">
      <style dangerouslySetInnerHTML={{ __html: CSS }} />
      <section className="sec" style={{ paddingBottom: 96 }}>
        <div className="wrap">
          <Header as="h1" eyebrow="Products" title="Four products one system" />
          <nav aria-label="Products" className="rv" style={{ display: 'flex', justifyContent: 'center', gap: 8, flexWrap: 'wrap', marginTop: -32 }}>
            {[['#size', 'Size'], ['#tryon', '3D try-on'], ['#intelligence', 'Intelligence'], ['#os', 'Operating system']].map(([h, l]) => (
              <a key={h} href={h} className="btn btn-s">{l}</a>
            ))}
          </nav>
        </div>
      </section>

      <Product id="size" eyebrow="01 Size recommendation" title="Their size in thirty seconds"
        facts={[{ k: 'Where', v: 'Every product' }, { k: 'Shopper', v: 'No account needed' }, { k: 'From', v: '€199 a month' }]}
        more={{ label: 'Pricing', href: '/pricing' }}>
        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <video autoPlay muted loop playsInline poster="/redesign/lafam-launch.jpg" aria-label="Find my size on the La Fam product page"
            style={{ width: '100%', maxWidth: 380, height: 'auto', display: 'block' }}>
            <source src="/redesign/lafam-launch.mp4" type="video/mp4" />
          </video>
        </div>
      </Product>

      <Product id="tryon" eyebrow="02 3D try-on" title="Your clothes on their body"
        facts={[{ k: 'Cloth', v: 'Simulated not pasted' }, { k: 'Body', v: 'Measured from photos' }, { k: 'Passport', v: 'One body every store' }]}>
        <div className="pair">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="frame" src="/redesign/ramin-widget.jpg" alt="Tryon open on a Ramin product page with the shopper's avatar in the hoodie" style={{ width: '100%', height: 'auto', display: 'block' }} />
          <div className="frame" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/redesign/avatar-render.jpg" alt="A measured avatar wearing a simulated black hoodie and sweatpants" style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block', maxHeight: 520 }} />
          </div>
        </div>
      </Product>

      <Product id="intelligence" eyebrow="03 Fit intelligence" title="The bodies behind every order"
        facts={[{ k: 'Measured', v: 'Real buyers not charts' }, { k: 'Found', v: 'Sizes that miss' }, { k: 'Planned', v: 'The next size run' }]}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="frame" src="/redesign/fit-intelligence.jpg" alt="The Tryon brand dashboard" style={{ width: '100%', height: 'auto', display: 'block' }} />
      </Product>

      <Product id="os" eyebrow="04 Operating system" title="Designs tested before they are made"
        facts={[{ k: 'Test', v: 'On your audience' }, { k: 'Size', v: 'A curve per market' }, { k: 'Make', v: 'Factories and mills' }]}
        more={{ label: 'Work with us', href: '/book' }}>
        <div className="pair" style={{ gridTemplateColumns: '1fr 1fr' }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="frame" src="/redesign/garment-bind.jpg" alt="A hoodie draped on a shopper's measured body" style={{ width: '100%', height: 'auto', display: 'block' }} />
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="frame" src="/redesign/fit-report.jpg" alt="The size curve per market" style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block', background: '#fff' }} />
        </div>
      </Product>
    </Site>
  );
}
