'use client';

/**
 * Password reset, step 2. The recovery link from the email lands on
 * /auth/callback (which holds the session) and sends the user here.
 */
import { FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getSession, getCurrentUser, updatePassword } from '@/lib/supabase-auth';

export const dynamic = 'force-dynamic';

export default function ResetPasswordPage() {
  const router = useRouter();
  const [ready, setReady] = useState<'checking' | 'ok' | 'expired'>('checking');
  const [pw, setPw] = useState('');
  const [pw2, setPw2] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      for (let i = 0; i < 10; i++) {
        const { data: { session } } = await getSession();
        if (cancelled) return;
        if (session) { setReady('ok'); return; }
        await new Promise(r => setTimeout(r, 300));
      }
      if (!cancelled) setReady('expired');
    })();
    return () => { cancelled = true; };
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setErr(null);
    if (pw.length < 8) return setErr('Use at least 8 characters.');
    if (pw !== pw2) return setErr('The two passwords do not match.');
    setBusy(true);
    try {
      const { error } = await updatePassword(pw);
      if (error) { setErr(error); return; }
      const user = await getCurrentUser();
      router.replace(user?.user_type === 'brand' ? '/brand' : '/dashboard');
    } finally {
      setBusy(false);
    }
  };

  const input: React.CSSProperties = { width: '100%', boxSizing: 'border-box', padding: '12px 14px', borderRadius: 12, border: '1px solid rgba(10,10,10,0.18)', fontSize: 15, outline: 'none' };

  return (
    <div style={{ minHeight: '100vh', background: '#FFFFFF', color: '#0A0A0A', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24, fontFamily: 'var(--display), system-ui, sans-serif' }}>
      <div style={{ width: '100%', maxWidth: 380, display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ fontSize: 12, letterSpacing: '0.04em', textTransform: 'uppercase', color: '#6E6E73' }}>Reset password</div>
        {ready === 'checking' && <p style={{ color: '#6E6E73' }}>One moment…</p>}
        {ready === 'expired' && (
          <>
            <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.025em', margin: 0 }}>This link has expired.</h1>
            <p style={{ color: '#6E6E73', margin: 0 }}>Go back to sign in and press Forgot again to get a fresh one.</p>
            <a href="/login?as=brand" style={{ color: '#0040FF', fontWeight: 600 }}>Back to sign in</a>
          </>
        )}
        {ready === 'ok' && (
          <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.025em', margin: 0 }}>Choose a new password.</h1>
            <label style={{ fontSize: 12, color: '#6E6E73' }}>New password
              <input type="password" value={pw} onChange={e => setPw(e.target.value)} autoComplete="new-password" style={{ ...input, marginTop: 6 }} />
            </label>
            <label style={{ fontSize: 12, color: '#6E6E73' }}>Repeat it
              <input type="password" value={pw2} onChange={e => setPw2(e.target.value)} autoComplete="new-password" style={{ ...input, marginTop: 6 }} />
            </label>
            {err && <div style={{ fontSize: 13, color: '#B00020' }}>{err}</div>}
            <button type="submit" disabled={busy} style={{ width: '100%', background: '#0040FF', color: '#fff', border: 'none', borderRadius: 9999, padding: '14px 18px', fontSize: 14, fontWeight: 700, cursor: busy ? 'not-allowed' : 'pointer', opacity: busy ? 0.6 : 1 }}>
              {busy ? 'Saving…' : 'Save and sign in →'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
