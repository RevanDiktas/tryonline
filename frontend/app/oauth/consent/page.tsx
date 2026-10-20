'use client';

/**
 * OAuth consent for the TryOn MCP server (Supabase Auth is the OAuth 2.1 server; this is its
 * "Authorization Path", set in Supabase > Authentication > OAuth Server).
 *
 * An AI app (Claude, ChatGPT, ...) sends the shopper here with ?authorization_id=. Signed out:
 * the normal sign-in form, then back here. Signed in: who is asking and what for, then
 * Allow / Deny, and the browser goes back to the app with Supabase's redirect_url.
 *
 * Google / Apple sign-in leaves the page, so the authorization id is kept in sessionStorage
 * and /auth/callback returns here (lib/oauthConsent.ts).
 */
import { Suspense, useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useTheme } from '@/contexts/ThemeContext';
import { AuthSignIn, type SignInData } from '@/components/redesign/AuthForms';
import {
  decideOAuthRequest, getCurrentUser, getOAuthRequest, login, logout, signInWithSocial,
  type OAuthRequestDetails,
} from '@/lib/supabase-auth';
import { clearOAuthConsent, pendingOAuthConsentId, rememberOAuthConsent } from '@/lib/oauthConsent';

const ID_RE = /^[A-Za-z0-9_-]{8,200}$/;

const WHAT_IT_CAN_DO = [
  'Read your fit passport: height, weight and body measurements',
  'Read your size quiz answers, and save new ones you give in the chat',
  'Work out your size for products you ask about',
  'Save products to your TryOn wishlist',
];

type Stage = 'loading' | 'signin' | 'consent' | 'redirecting' | 'error' | 'switched';

function Consent() {
  const params = useSearchParams();
  const { theme } = useTheme();
  const dark = theme === 'dark';
  const C = dark
    ? { bg: '#0A0A0A', card: '#141414', ink: '#F2F1EC', dim: '#8A8A8A', line: '#262626' }
    : { bg: '#ffffff', card: '#ffffff', ink: '#0A0A0A', dim: '#7A7770', line: '#E1DDD2' };

  const [authId, setAuthId] = useState<string | null>(null);
  const [stage, setStage] = useState<Stage>('loading');
  const [details, setDetails] = useState<OAuthRequestDetails | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [backUrl, setBackUrl] = useState<string | null>(null);

  const load = useCallback(async (id: string) => {
    setStage('loading');
    const user = await getCurrentUser();
    if (!user) { setStage('signin'); return; }
    const { details: d, error: e } = await getOAuthRequest(id);
    if (!d) { setError(e); setStage('error'); return; }
    if (d.redirectUrl) { setStage('redirecting'); window.location.href = d.redirectUrl; return; }
    setDetails(d);
    setStage('consent');
  }, []);

  useEffect(() => {
    const id = params.get('authorization_id') || pendingOAuthConsentId();
    if (id && ID_RE.test(id)) rememberOAuthConsent(id);
    if (!id || !ID_RE.test(id)) { setError('This link is missing its sign-in request. Start again from the app.'); setStage('error'); return; }
    setAuthId(id);
    load(id);
  }, [params, load]);

  const signIn = async (f: SignInData) => {
    setFormError(null);
    setBusy(true);
    try {
      const { user, error: e } = await login(f.email, f.password);
      if (e || !user) { setFormError(e || 'Invalid email or password.'); return; }
      if (authId) await load(authId);
    } finally { setBusy(false); }
  };

  const social = async (provider: 'google' | 'apple') => {
    setFormError(null);
    const { url, error: e } = await signInWithSocial(provider);
    if (url) window.location.href = url;
    else if (e) setFormError(e);
  };

  const decide = async (approve: boolean) => {
    if (!authId) return;
    setBusy(true);
    const { redirectUrl, error: e } = await decideOAuthRequest(authId, approve);
    setBusy(false);
    if (!redirectUrl) { setError(e); setStage('error'); return; }
    clearOAuthConsent();
    setStage('redirecting');
    window.location.href = redirectUrl;
  };

  // Supabase ties this request to the account that opened it, so another account cannot
  // finish it. Decline it (the app shows it was cancelled), sign out, and send the shopper
  // back to connect again: the new request then belongs to whoever signs in.
  const switchAccount = async () => {
    if (!authId) return;
    setBusy(true);
    const { redirectUrl } = await decideOAuthRequest(authId, false);
    clearOAuthConsent();
    await logout();
    setBusy(false);
    setBackUrl(redirectUrl);
    setStage('switched');
  };

  if (stage === 'signin') {
    return (
      <AuthSignIn
        dark={dark}
        loading={busy}
        formError={formError}
        onSubmit={signIn}
        onGoogle={() => social('google')}
        onApple={() => social('apple')}
        onSignUpClick={() => { window.location.href = '/signup'; }}
        shopifyMode={false}
      />
    );
  }

  const shell = (children: React.ReactNode) => (
    <main style={{ minHeight: '100vh', background: C.bg, color: C.ink, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '32px 16px', fontFamily: 'var(--display)' }}>
      <div style={{ width: '100%', maxWidth: 440, background: C.card, border: `1px solid ${C.line}`, borderRadius: 20, padding: 28 }}>
        <div style={{ fontSize: 13, letterSpacing: '0.04em', textTransform: 'uppercase', color: C.dim, marginBottom: 18 }}>TryOn</div>
        {children}
      </div>
    </main>
  );

  if (stage === 'loading' || stage === 'redirecting') {
    return shell(<p style={{ margin: 0, color: C.dim }}>{stage === 'loading' ? 'Loading…' : 'Taking you back…'}</p>);
  }
  if (stage === 'switched') {
    return shell(<>
      <h1 style={{ fontSize: 22, margin: '0 0 8px', fontWeight: 600 }}>Signed out</h1>
      <p style={{ margin: '0 0 20px', color: C.dim, lineHeight: 1.5 }}>
        Go back to {details?.clientName && details.clientName !== 'An app' ? details.clientName : 'the app'} and connect TryOn again. You will be asked to sign in, so you can use the other account.
      </p>
      {backUrl && (
        <a href={backUrl} style={{ display: 'block', textAlign: 'center', padding: '12px 16px', borderRadius: 12, background: '#0040FF', color: '#fff', fontWeight: 600, textDecoration: 'none' }}>
          Back to {details?.clientName && details.clientName !== 'An app' ? details.clientName : 'the app'}
        </a>
      )}
    </>);
  }
  if (stage === 'error' || !details) {
    return shell(<>
      <h1 style={{ fontSize: 22, margin: '0 0 8px', fontWeight: 600 }}>That did not work</h1>
      <p style={{ margin: 0, color: C.dim, lineHeight: 1.5 }}>{error || 'Something went wrong.'} If it keeps happening, write to support@tryon.global.</p>
    </>);
  }

  return shell(<>
    <h1 style={{ fontSize: 22, margin: '0 0 6px', fontWeight: 600, lineHeight: 1.3 }}>
      {details.clientName} wants to use your TryOn sizes
    </h1>
    <p style={{ margin: '0 0 20px', color: C.dim, fontSize: 14 }}>
      Signed in as {details.email}. <button type="button" disabled={busy} onClick={switchAccount} style={{ background: 'none', border: 0, padding: 0, color: '#0040FF', cursor: 'pointer', font: 'inherit' }}>Not you?</button>
    </p>
    <div style={{ fontSize: 12, letterSpacing: '0.04em', textTransform: 'uppercase', color: C.dim, marginBottom: 10 }}>It will be able to</div>
    <ul style={{ margin: '0 0 20px', paddingLeft: 18, lineHeight: 1.6, fontSize: 14, listStyle: 'disc' }}>
      {WHAT_IT_CAN_DO.map((t) => <li key={t}>{t}</li>)}
    </ul>
    <p style={{ margin: '0 0 22px', color: C.dim, fontSize: 13, lineHeight: 1.5 }}>
      It cannot see your photos or change your password. You can disconnect it any time from the app&apos;s settings.
      {' '}<a href="/privacy" style={{ color: C.dim }}>Privacy</a>
    </p>
    <div style={{ display: 'flex', gap: 10 }}>
      <button type="button" disabled={busy} onClick={() => decide(false)}
        style={{ flex: 1, padding: '12px 16px', borderRadius: 12, border: `1px solid ${C.line}`, background: 'transparent', color: C.ink, font: 'inherit', fontWeight: 600, cursor: 'pointer' }}>
        Deny
      </button>
      <button type="button" disabled={busy} onClick={() => decide(true)}
        style={{ flex: 1, padding: '12px 16px', borderRadius: 12, border: 0, background: '#0040FF', color: '#fff', font: 'inherit', fontWeight: 600, cursor: 'pointer', opacity: busy ? 0.6 : 1 }}>
        Allow
      </button>
    </div>
  </>);
}

export default function OAuthConsentPage() {
  return (
    <Suspense fallback={null}>
      <Consent />
    </Suspense>
  );
}
