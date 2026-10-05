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
 * - geo: the shopper's country and city, worked out from their IP address by the hosting
 *   platform (no permission prompt, nothing finer than a city). The cards attach it to
 *   their analytics events, so nobody has to be asked where they are.
 */
export const dynamic = 'force-dynamic';

function geoFrom(headers: Headers) {
  const countryCode = (headers.get('x-vercel-ip-country') || '').toUpperCase() || null;
  let city: string | null = headers.get('x-vercel-ip-city');
  try { city = city ? decodeURIComponent(city) : null; } catch { /* keep as sent */ }
  let country: string | null = null;
  try { country = countryCode ? new Intl.DisplayNames(['en'], { type: 'region' }).of(countryCode) || null : null; } catch { /* unknown code */ }
  return { countryCode, country, city };
}

export async function GET(request: Request) {
  const backendUrl = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '');
  return NextResponse.json({
    backendUrl,
    supabaseUrl: (process.env.NEXT_PUBLIC_SUPABASE_URL || '').replace(/\/+$/, ''),
    supabaseAnonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '',
    geo: geoFrom(request.headers),
  }, { headers: { 'Cache-Control': 'private, no-store' } });
}
