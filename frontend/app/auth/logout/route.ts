import { createServerClient } from '@supabase/auth-helpers-nextjs';
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

/**
 * POST /auth/logout - ends the tryon.global cookie session that /auth/me reads.
 * The Try On widget calls this on "Sign out", otherwise the next load of the widget
 * finds the same session and signs the shopper straight back in.
 */
export async function POST() {
  const cookieStore = cookies();
  const res = NextResponse.json({ ok: true });
  try {
    const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
      cookies: {
        getAll() { return cookieStore.getAll(); },
        setAll(list) { for (const c of list) res.cookies.set(c.name, c.value, c.options); },
      },
    });
    await supabase.auth.signOut();
  } catch (e) {
    console.error('[auth/logout]', e);
  }
  // Belt and braces: expire every Supabase auth cookie we can see.
  for (const c of cookieStore.getAll()) {
    if (c.name.startsWith('sb-') && c.name.includes('auth-token')) {
      res.cookies.set(c.name, '', { path: '/', maxAge: 0 });
    }
  }
  return res;
}
