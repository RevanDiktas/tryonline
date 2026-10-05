/**
 * Widget → tryon.global → back-to-store hand-off.
 *
 * The PDP widget opens /signup or /onboarding in a new tab with
 *   ?from=widget&return=<https product URL>&brand=<store name>&link_state=<uuid>
 * We persist that in sessionStorage so it survives OAuth round-trips
 * (/auth/callback, /auth/complete-profile) and client-side router pushes.
 *
 * - link_state: once the account exists we complete the widget-state token so
 *   the PDP iframe (which polls it) signs in while this tab keeps onboarding.
 *   Unlike widget_state it never closes the window. The token is kept and
 *   re-completed when the avatar is ready and on "Back to store": the backend
 *   expires completed tokens, and a background store tab (iOS) may not have
 *   polled yet. Re-completing is harmless - the poller deletes on read.
 * - return/brand: once the shopper has an avatar we offer "Back to {brand}".
 */

import { getAccessToken } from './supabase-auth';

const STORAGE_KEY = 'tryon_widget_return';
const MAX_BRAND_LENGTH = 60;
// Widget tokens are UUIDs; accept any URL-safe token so the path segment stays clean.
const LINK_STATE_RE = /^[A-Za-z0-9_-]{8,128}$/;

export interface WidgetReturn {
  url: string;
  brand?: string;
}

interface StoredHandoff {
  url?: string;
  brand?: string;
  linkState?: string;
}

function parseHttpsUrl(raw: string | null | undefined): string | null {
  if (!raw) return null;
  try {
    const u = new URL(raw);
    return u.protocol === 'https:' ? u.toString() : null;
  } catch {
    return null;
  }
}

function cleanBrand(raw: string | null | undefined): string | undefined {
  const b = raw?.trim().slice(0, MAX_BRAND_LENGTH);
  return b || undefined;
}

function cleanLinkState(raw: string | null | undefined): string | undefined {
  return raw && LINK_STATE_RE.test(raw) ? raw : undefined;
}

export function isValidLinkState(raw: string | null | undefined): raw is string {
  return !!cleanLinkState(raw);
}

function readStored(): StoredHandoff {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as StoredHandoff;
    return {
      url: parseHttpsUrl(parsed?.url) ?? undefined,
      brand: cleanBrand(parsed?.brand),
      linkState: cleanLinkState(parsed?.linkState),
    };
  } catch {
    return {};
  }
}

function writeStored(value: StoredHandoff): void {
  try {
    if (!value.url && !value.linkState) sessionStorage.removeItem(STORAGE_KEY);
    else sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch { /* storage blocked - hand-off just won't persist */ }
}

/** Store return/brand/link_state from the URL when it carries a widget hand-off.
 *  A valid `return` replaces the stored one; a new link_state replaces the old. */
export function captureWidgetReturn(params: { get(name: string): string | null } | null | undefined): void {
  if (!params) return;
  const url = parseHttpsUrl(params.get('return'));
  const linkState = cleanLinkState(params.get('link_state'));
  if (!url && !linkState) return;
  const prev = readStored();
  writeStored({
    url: url ?? prev.url,
    brand: url ? cleanBrand(params.get('brand')) : prev.brand,
    linkState: linkState ?? prev.linkState,
  });
}

export function getWidgetReturn(): WidgetReturn | null {
  const { url, brand } = readStored();
  return url ? { url, brand } : null;
}

export function clearWidgetReturn(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch { /* noop */ }
}

/** "?from=widget&return=…&brand=…&link_state=…" for the stored hand-off, or ''. */
export function widgetReturnQuery(): string {
  const { url, brand, linkState } = readStored();
  if (!url && !linkState) return '';
  const q = new URLSearchParams({ from: 'widget' });
  if (url) q.set('return', url);
  if (brand) q.set('brand', brand);
  if (linkState) q.set('link_state', linkState);
  return `?${q.toString()}`;
}

type LinkUser = { id: string; name?: string; email?: string };

/** Complete the widget's link_state token so the PDP iframe polling it becomes
 *  signed in. Best-effort; keepalive lets it finish across a navigation. */
export async function completeWidgetLink(user: LinkUser): Promise<void> {
  const { linkState } = readStored();
  if (!linkState) return;
  const displayName = user.name || user.email?.split('@')[0] || 'User';
  try {
    await fetch(`/api/auth/widget-state/${linkState}/complete`, {
      method: 'POST',
      headers: await widgetStateHeaders(),
      body: JSON.stringify({ user_id: user.id, display_name: displayName }),
      keepalive: true,
    });
  } catch { /* best-effort */ }
}

/** Headers for POST /api/auth/widget-state/{token}/complete. The bearer token proves
 *  this page is signed in as the user it names; the backend only hands the widget a
 *  widget token for a completion proven this way. */
export async function widgetStateHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  try {
    const token = await getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  } catch { /* no session yet - the backend treats the call as unproven */ }
  return headers;
}

/** Where a signed-in shopper goes next. A pending hand-off always lands on
 *  /onboarding, which shows the "back to store" step once the avatar exists. */
export function shopperHomePath(hasAvatar: boolean): '/dashboard' | '/onboarding' {
  return hasAvatar && !getWidgetReturn() ? '/dashboard' : '/onboarding';
}

/** Send the shopper back to the store product page and drop the hand-off.
 *  Re-completes link_state first (keepalive, not awaited) so the store's
 *  widget can still pick up the sign-in if its token had expired. */
export function goBackToStore(value: WidgetReturn, user: LinkUser | null): void {
  if (user) void completeWidgetLink(user);
  clearWidgetReturn();
  window.location.href = value.url;
}
