import { NextResponse } from 'next/server';

/**
 * GET /widget-config - what the static store-page cards (test-viewer.html,
 * size-finder.html) need at runtime and cannot read from the build environment:
 *
 * - backendUrl: so a card can fall back to a direct request when the same-origin
 *   /api rewrite fails (e.g. deploy cache).
 * - supabaseUrl + supabaseAnonKey: so a card can create an account and sign in without
 *   leaving the store page. Both are public by design (they ship in every page of this
 *   site already); what a signed-in shopper may read or write is decided by row-level
 *   security and by the backend, never by this key.
 */
export async function GET() {
  const backendUrl = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '');
  return NextResponse.json({
    backendUrl,
    supabaseUrl: (process.env.NEXT_PUBLIC_SUPABASE_URL || '').replace(/\/+$/, ''),
    supabaseAnonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '',
  });
}
