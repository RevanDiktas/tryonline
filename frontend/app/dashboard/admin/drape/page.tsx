'use client';

import { useEffect, useState } from 'react';
import { getCurrentUser, type User } from '@/lib/supabase-auth';

type QueueCounts = {
  queued: number;
  dispatched: number;
  running: number;
  completed: number;
  failed: number;
  cancelled: number;
  skipped_cache_hit: number;
};

type QueueStatus = {
  jobs: QueueCounts;
  cached_meshes: number;
  completed_avatars: number;
  active_garments: number;
};

const apiBase = (() => {
  const url = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '');
  return url.endsWith('/api') ? url.slice(0, -4) : url;
})();

const TOKEN_KEY = 'drape_admin_token';

const ADMIN_EMAILS: string[] = (process.env.NEXT_PUBLIC_ADMIN_EMAILS || '')
  .split(',')
  .map((e) => e.trim().toLowerCase())
  .filter(Boolean);

function NotFound() {
  return (
    <div className="min-h-screen bg-white text-black flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-6xl font-bold mb-2">404</h1>
        <p className="text-sm opacity-70">This page could not be found.</p>
      </div>
    </div>
  );
}

export default function DrapeAdminPage() {
  const [authState, setAuthState] = useState<'loading' | 'allowed' | 'denied'>('loading');
  const [token, setToken] = useState('');
  const [status, setStatus] = useState<QueueStatus | null>(null);
  const [error, setError] = useState<string>('');
  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState<string[]>([]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const u: User | null = await getCurrentUser();
        const email = (u?.email || '').toLowerCase();
        const allowed = !!email && ADMIN_EMAILS.includes(email);
        if (mounted) setAuthState(allowed ? 'allowed' : 'denied');
      } catch {
        if (mounted) setAuthState('denied');
      }
    })();
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    if (authState !== 'allowed') return;
    const saved = typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) ?? '' : '';
    setToken(saved);
  }, [authState]);

  function persistToken(t: string) {
    setToken(t);
    if (typeof window !== 'undefined') localStorage.setItem(TOKEN_KEY, t);
  }

  function logLine(line: string) {
    setLog((prev) => [`${new Date().toISOString().slice(11, 19)}  ${line}`, ...prev].slice(0, 50));
  }

  async function call(path: string, init?: RequestInit) {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(`${apiBase}${path}`, { ...init, headers });
    const text = await res.text();
    let data: unknown;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = text;
    }
    if (!res.ok) {
      throw new Error(`${res.status} ${typeof data === 'string' ? data : JSON.stringify(data)}`);
    }
    return data;
  }

  async function refresh() {
    setError('');
    try {
      const data = (await call('/api/draping/admin/queue')) as QueueStatus;
      setStatus(data);
    } catch (e) {
      setError(String(e));
    }
  }

  async function backfill(brandId: string | null, dryRun: boolean) {
    setBusy(true);
    setError('');
    try {
      const body: Record<string, unknown> = { priority: 200, dry_run: dryRun };
      if (brandId) body.brand_id = brandId;
      const data = (await call('/api/draping/backfill', {
        method: 'POST',
        body: JSON.stringify(body),
      })) as Record<string, number | boolean>;
      logLine(`backfill ${dryRun ? '(dry-run)' : ''} -> ${JSON.stringify(data)}`);
      await refresh();
    } catch (e) {
      setError(String(e));
      logLine(`backfill error: ${e}`);
    } finally {
      setBusy(false);
    }
  }

  async function drain() {
    if (!confirm('Cancel all queued drape jobs? Running jobs continue.')) return;
    setBusy(true);
    setError('');
    try {
      const data = (await call('/api/draping/admin/drain', {
        method: 'POST',
        body: JSON.stringify({ confirm: true }),
      })) as { cancelled: number };
      logLine(`drain -> cancelled ${data.cancelled}`);
      await refresh();
    } catch (e) {
      setError(String(e));
      logLine(`drain error: ${e}`);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (authState !== 'allowed' || !token) return;
    refresh();
    const id = setInterval(refresh, 10000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authState, token]);

  const [brandIdInput, setBrandIdInput] = useState('');

  if (authState === 'loading') {
    return <div className="min-h-screen bg-white" />;
  }
  if (authState === 'denied') {
    return <NotFound />;
  }

  return (
    <div className="min-h-screen bg-white text-black p-8 font-mono">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold border-b-2 border-black pb-2 mb-6">
          drape queue / admin
        </h1>

        <section className="border-2 border-black p-4 mb-4">
          <label className="block text-xs uppercase tracking-wider mb-1">admin token</label>
          <input
            type="password"
            value={token}
            onChange={(e) => persistToken(e.target.value)}
            placeholder="DRAPE_ADMIN_TOKEN (from backend env, leave blank if unset)"
            className="w-full border border-black px-2 py-1 text-sm"
          />
          <p className="text-xs mt-1 opacity-70">
            Stored in localStorage. Sent as <code>Authorization: Bearer ...</code>.
          </p>
        </section>

        {error && (
          <div className="border-2 border-black p-3 mb-4 text-sm">
            <strong>error:</strong> {error}
          </div>
        )}

        <section className="border-2 border-black p-4 mb-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-bold">queue</h2>
            <button
              onClick={refresh}
              className="border border-black px-3 py-1 text-xs hover:bg-black hover:text-white"
            >
              refresh
            </button>
          </div>
          {status ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
              {(Object.keys(status.jobs) as (keyof QueueCounts)[]).map((k) => (
                <div key={k} className="border border-black p-2">
                  <div className="text-xs uppercase opacity-70">{k.replace('_', ' ')}</div>
                  <div className="text-xl font-bold">{status.jobs[k]}</div>
                </div>
              ))}
              <div className="border border-black p-2 col-span-2">
                <div className="text-xs uppercase opacity-70">cached meshes</div>
                <div className="text-xl font-bold">{status.cached_meshes}</div>
              </div>
              <div className="border border-black p-2">
                <div className="text-xs uppercase opacity-70">avatars</div>
                <div className="text-xl font-bold">{status.completed_avatars}</div>
              </div>
              <div className="border border-black p-2">
                <div className="text-xs uppercase opacity-70">garments</div>
                <div className="text-xl font-bold">{status.active_garments}</div>
              </div>
            </div>
          ) : (
            <p className="text-sm opacity-70">enter token + refresh</p>
          )}
        </section>

        <section className="border-2 border-black p-4 mb-4">
          <h2 className="text-lg font-bold mb-3">actions</h2>
          <div className="flex flex-col gap-3">
            <div className="flex gap-2">
              <button
                disabled={busy}
                onClick={() => backfill(null, true)}
                className="border-2 border-black px-3 py-2 text-sm hover:bg-black hover:text-white disabled:opacity-30"
              >
                dry-run backfill (all brands)
              </button>
              <button
                disabled={busy}
                onClick={() => backfill(null, false)}
                className="border-2 border-black px-3 py-2 text-sm hover:bg-black hover:text-white disabled:opacity-30"
              >
                run backfill (all brands)
              </button>
            </div>

            <div className="flex gap-2 items-center">
              <input
                value={brandIdInput}
                onChange={(e) => setBrandIdInput(e.target.value)}
                placeholder="brand_id uuid"
                className="flex-1 border border-black px-2 py-1 text-sm"
              />
              <button
                disabled={busy || !brandIdInput.trim()}
                onClick={() => backfill(brandIdInput.trim(), true)}
                className="border-2 border-black px-3 py-2 text-sm hover:bg-black hover:text-white disabled:opacity-30"
              >
                dry-run brand
              </button>
              <button
                disabled={busy || !brandIdInput.trim()}
                onClick={() => backfill(brandIdInput.trim(), false)}
                className="border-2 border-black px-3 py-2 text-sm hover:bg-black hover:text-white disabled:opacity-30"
              >
                run brand
              </button>
            </div>

            <div>
              <button
                disabled={busy}
                onClick={drain}
                className="border-2 border-black px-3 py-2 text-sm hover:bg-black hover:text-white disabled:opacity-30"
              >
                drain queue (cancel all queued)
              </button>
            </div>
          </div>
        </section>

        <section className="border-2 border-black p-4">
          <h2 className="text-lg font-bold mb-3">log</h2>
          {log.length === 0 ? (
            <p className="text-sm opacity-70">(empty)</p>
          ) : (
            <pre className="text-xs whitespace-pre-wrap break-all">
              {log.join('\n')}
            </pre>
          )}
        </section>
      </div>
    </div>
  );
}
