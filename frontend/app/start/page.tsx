'use client';

import React, { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useTheme } from '@/contexts/ThemeContext';
import { SharedNav, AuthAwareSignInLink } from '@/components/redesign/SharedNav';
import { useIsMobile } from '@/components/redesign/useIsMobile';
import { siteLinks } from '@/components/redesign/siteLinks';
import { SiteFooter } from '@/components/redesign/SiteFooter';
import { PAL, type Palette, headingStyle, bodyStyle, eyebrowStyle, pillButton } from '@/components/redesign/marketing';
import { PLANS, TRIAL_DAYS, type Plan } from '@/lib/plans';

/* /start: a brand asks to start. Until the public Shopify app is in the App Store, the team
   replies with a private install link; the request lands in Supabase brand_leads. */

const field: React.CSSProperties = {
  width: '100%', height: 50, padding: '0 14px', borderRadius: 12, fontSize: 16,
  fontFamily: 'var(--display)', boxSizing: 'border-box', outline: 'none',
};

function StartForm({ C }: { C: Palette }) {
  const params = useSearchParams();
  const router = useRouter();
  const initialPlan = (PLANS.find((p) => p.id === params.get('plan'))?.id || 'size_pro') as Plan['id'];
  const [plan, setPlan] = useState<Plan['id']>(initialPlan);
  const [form, setForm] = useState({ brand_name: '', contact_name: '', email: '', shop_domain: '', notes: '' });
  const [state, setState] = useState<'idle' | 'sending' | 'sent'>('idle');
  const [error, setError] = useState('');
  const input = { ...field, background: C.surface, color: C.ink, border: `1px solid ${C.line}` };
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!form.brand_name.trim()) { setError('Enter your brand name.'); return; }
    if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) { setError('Enter your work email.'); return; }
    setState('sending');
    try {
      const r = await fetch('/api/brand/leads', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, plan, source: 'website_start' }),
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        throw new Error((d && d.detail && typeof d.detail === 'string') ? d.detail : 'Something went wrong. Try again, or email revan@tryon.global.');
      }
      setState('sent');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.');
      setState('idle');
    }
  };

  if (state === 'sent') {
    return (
      <div style={{ border: `1px solid ${C.line}`, background: C.surface, borderRadius: 24, padding: '36px 30px' }}>
        <h2 style={{ ...headingStyle('32px'), marginBottom: 12 }}>You are on the list.</h2>
        <p style={{ ...bodyStyle, color: C.mute, marginBottom: 24 }}>
          We will email {form.email.trim()} your install link within one working day. It takes a few minutes: install, add the TryOn block in your theme editor, done. Find my size is then live on every product.
        </p>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button type="button" style={pillButton('primary', C)} onClick={() => router.push('/product')}>See how it works</button>
          <button type="button" style={pillButton('ghost', C)} onClick={() => router.push('/book')}>Book a call too</button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={submit} noValidate style={{ border: `1px solid ${C.line}`, background: C.surface, borderRadius: 24, padding: '28px 26px', display: 'grid', gap: 16 }}>
      <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
        <legend style={{ fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600, marginBottom: 10 }}>Plan</legend>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(118px, 1fr))', gap: 8 }}>
          {PLANS.map((p) => (
            <label key={p.id} style={{
              display: 'grid', gap: 2, padding: '10px 12px', borderRadius: 12, cursor: 'pointer',
              border: `1.5px solid ${plan === p.id ? C.ink : C.line}`, background: plan === p.id ? C.bg : 'transparent',
            }}>
              <input type="radio" name="plan" value={p.id} checked={plan === p.id} onChange={() => setPlan(p.id)} style={{ position: 'absolute', opacity: 0, pointerEvents: 'none' }} />
              <span style={{ fontFamily: 'var(--display)', fontSize: 13.5, fontWeight: 600 }}>{p.name}</span>
              <span style={{ fontFamily: 'var(--display)', fontSize: 12.5, color: C.mute }}>{p.price}/mo{p.setup ? ' + setup' : ''}</span>
            </label>
          ))}
        </div>
      </fieldset>
      {[
        ['brand_name', 'Brand name', 'text', 'organization'],
        ['contact_name', 'Your name', 'text', 'name'],
        ['email', 'Work email', 'email', 'email'],
        ['shop_domain', 'Shopify store (yourstore.myshopify.com or your domain)', 'text', 'url'],
      ].map(([k, label, type, ac]) => (
        <label key={k} style={{ display: 'grid', gap: 7 }}>
          <span style={{ fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600 }}>{label}</span>
          <input type={type} autoComplete={ac} value={form[k as keyof typeof form]} onChange={set(k as keyof typeof form)} style={input} />
        </label>
      ))}
      <label style={{ display: 'grid', gap: 7 }}>
        <span style={{ fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600 }}>Anything we should know? <span style={{ fontWeight: 400, color: C.mute }}>optional</span></span>
        <textarea value={form.notes} onChange={set('notes')} rows={3} style={{ ...input, height: 'auto', padding: '12px 14px', resize: 'vertical' }} />
      </label>
      {error && <p role="alert" style={{ ...bodyStyle, fontSize: 13.5, color: '#C62828', margin: 0 }}>{error}</p>}
      <button type="submit" disabled={state === 'sending'} style={{ ...pillButton('primary', C), justifyContent: 'center', opacity: state === 'sending' ? 0.6 : 1 }}>
        {state === 'sending' ? 'Sending…' : <>Send me my install link <span>→</span></>}
      </button>
      <p style={{ ...bodyStyle, fontSize: 12.5, color: C.mute, margin: 0 }}>
        Every plan starts with a {TRIAL_DAYS}-day free trial and is billed through Shopify. Cancel any time.
      </p>
    </form>
  );
}

export default function StartPage() {
  const { theme } = useTheme();
  const dark = theme === 'dark';
  const C = dark ? PAL.dark : PAL.light;
  const mobile = useIsMobile();
  const steps = [
    ['Today', 'Tell us your store. We reply within one working day with your install link.'],
    ['Five minutes', 'Install TryOn and add its block in your Shopify theme editor. No code.'],
    ['Live', 'Find my size runs on every product with sizes. We make your garments in 3D for Try On.'],
  ];
  return (
    <div className="tryon-redesign-root" style={{ width: '100%', minHeight: '100vh', background: C.bg, color: C.ink, overflowX: 'hidden' }}>
      <SharedNav dark={dark} links={siteLinks('/start')} rightSlot={mobile ? undefined : <AuthAwareSignInLink dark={dark} />} />
      <section style={{ padding: mobile ? '36px 20px 64px' : '72px 32px 96px' }}>
        <div style={{ maxWidth: 1120, margin: '0 auto', display: 'grid', gap: mobile ? 36 : 72, gridTemplateColumns: mobile ? '1fr' : '0.95fr 1.05fr', alignItems: 'start' }}>
          <div>
            <p style={eyebrowStyle(C)}>{TRIAL_DAYS}-day free trial · For Shopify brands</p>
            <h1 style={{ ...headingStyle('clamp(40px, 5.4vw, 72px)'), marginBottom: 18 }}>Get TryOn on your store.</h1>
            <p style={{ ...bodyStyle, fontSize: 17.5, color: C.mute, maxWidth: 460, marginBottom: 32 }}>
              Your shoppers get their size on every product in 30 seconds. You get fewer returns, and the data to prove it.
            </p>
            <ol style={{ listStyle: 'none', padding: 0, margin: 0, borderTop: `1px solid ${C.line}` }}>
              {steps.map(([t, d]) => (
                <li key={t} style={{ padding: '16px 0', borderBottom: `1px solid ${C.line}`, display: 'grid', gridTemplateColumns: '120px 1fr', gap: 12 }}>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.08em', paddingTop: 3 }}>{t}</span>
                  <span style={{ ...bodyStyle, fontSize: 15, color: C.mute }}>{d}</span>
                </li>
              ))}
            </ol>
          </div>
          <Suspense fallback={null}><StartForm C={C} /></Suspense>
        </div>
      </section>
      <SiteFooter dark={dark} />
    </div>
  );
}
