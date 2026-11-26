'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { Site, Header, Arrow } from './kit';
import { OsDiagram } from './OsDiagram';

/* Home. The avatar and the title, then what we are drawn as a system, then the four steps of a new
   garment, then the footer call to action. As little text as possible. */

const AvatarHero = dynamic(() => import('@/components/redesign/AvatarHero').then((m) => m.AvatarHero), { ssr: false });

const STEPS = [
  { n: '01', t: 'Measure', d: 'Fit and behaviour from every shopper' },
  { n: '02', t: 'Stress test', d: 'A new design tested on your audience before it exists' },
  { n: '03', t: 'Size the run', d: 'How many of each size to make' },
  { n: '04', t: 'Produce', d: 'Made with our factories and mills' },
];

const CSS = `
.os .hero{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,1fr);gap:40px;align-items:center;min-height:calc(100svh - 76px)}
.os .hero .copy{display:flex;flex-direction:column;gap:28px;padding-block:48px}
.os .hero .stage{height:calc(100svh - 140px);min-height:520px;max-height:860px}
.os .live{display:flex;align-items:center;gap:40px;flex-wrap:wrap;padding-block:8px 40px}
.os .steps{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--rule);border-top:1px solid var(--rule);border-bottom:1px solid var(--rule)}
.os .steps li{background:#fff;padding:40px 28px;display:flex;flex-direction:column;align-items:center;text-align:center;gap:14px}
@media(max-width:1024px){.os .hero{grid-template-columns:1fr;min-height:0;gap:0}.os .hero .copy{padding-block:40px 8px}.os .hero .stage{height:58vh;min-height:380px}
.os .steps{grid-template-columns:1fr 1fr}}
@media(max-width:600px){.os .steps{grid-template-columns:1fr}.os .live{gap:28px;justify-content:center}}
`;

export function OsLanding() {
  // A Supabase recovery link that lands on the home page goes to the reset screen with its fragment intact.
  useEffect(() => {
    if (/type=recovery/.test(window.location.hash)) window.location.replace('/auth/reset-password' + window.location.hash);
  }, []);
  return (
    <Site>
      <style dangerouslySetInnerHTML={{ __html: CSS }} />
      <section className="wrap hero">
        <div className="copy">
          <span className="eb rv">The operating system for fashion</span>
          <h1 className="h1 rv" style={{ ['--d' as string]: '60ms', maxWidth: '13ch' }}>The future of clothing starts here</h1>
          <p className="lede rv" style={{ ['--d' as string]: '120ms', fontSize: '1.1875rem', maxWidth: '30ch' }}>The intelligence layer between consumer brand and factory</p>
          <div className="rv" style={{ ['--d' as string]: '180ms', display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <Link href="/book" className="btn btn-p">Work with us</Link>
            <Link href="/product" className="btn btn-s">Products</Link>
          </div>
        </div>
        <div className="stage rv" style={{ ['--d' as string]: '120ms' }}>
          <AvatarHero height="100%" interactive={false} rotateSpeed={0.6} />
        </div>
      </section>

      <div className="wrap live">
        <span className="eb">Live with</span>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/partners/lafam.webp" alt="La Fam Amsterdam" style={{ height: 44, width: 'auto', display: 'block' }} />
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/partners/ramin.webp" alt="Ramin Studios" style={{ height: 15, width: 'auto', display: 'block' }} />
      </div>

      <section className="sec" style={{ borderTop: '1px solid var(--rule)' }}>
        <div className="wrap">
          <Header eyebrow="What we are" title="One layer from shopper to factory" />
          <div className="rv" style={{ ['--d' as string]: '120ms' }}><OsDiagram /></div>
        </div>
      </section>

      <section className="sec" style={{ paddingTop: 0 }}>
        <div className="wrap">
          <Header eyebrow="A new long sleeve" title="From idea to factory on real bodies" />
          <ol className="steps" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
            {STEPS.map((s, i) => (
              <li key={s.n} className="rv" style={{ ['--d' as string]: `${i * 60}ms` }}>
                <span className="num">{s.n}</span>
                <h3 className="h3">{s.t}</h3>
                <p className="small" style={{ maxWidth: '24ch' }}>{s.d}</p>
              </li>
            ))}
          </ol>
          <div className="rv" style={{ display: 'flex', justifyContent: 'center', marginTop: 48 }}>
            <Link href="/product" className="btn btn-t">See the products <Arrow /></Link>
          </div>
        </div>
      </section>
    </Site>
  );
}
