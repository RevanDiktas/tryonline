/**
 * The TryOn backend (Railway FastAPI), called by the MCP tools with the shopper's own OAuth
 * access token. The backend checks that token exactly as it checks a website session, so a
 * tool can only ever read or write the signed-in shopper's own data.
 */
// @ts-ignore - plain ES module shared with the store-page card
import { estimateBody, normalizeGender } from '../../public/size-estimator.js';
import type { Body, Fit, Garment, QuizAnswers } from './sizing';
import { usableAnswers } from './sizing';

const API = (process.env.TRYON_API_URL || process.env.NEXT_PUBLIC_API_URL || 'https://heroic-celebration-production-9f72.up.railway.app').replace(/\/+$/, '');
const MEASURE_KEYS = ['chest', 'waist', 'hips', 'inseam', 'shoulder_width', 'arm_length', 'neck', 'thigh', 'torso_length'];

async function call(path: string, token: string | null, init: RequestInit = {}): Promise<Response> {
  const headers: Record<string, string> = { accept: 'application/json', ...(init.headers as Record<string, string> || {}) };
  if (token) headers.authorization = `Bearer ${token}`;
  return fetch(`${API}${path}`, { ...init, headers, cache: 'no-store', signal: AbortSignal.timeout(10000) });
}

export interface PassportState {
  status: 'none' | 'processing' | 'failed' | 'completed';
  measured: Extract<Body, { basis: 'measured' }> | null;
  height?: number;
  weight?: number;
  measuredAt?: string | null;
}

/** The fit passport, as the card reads it: only a completed one is a measurement. */
export async function getPassport(userId: string, token: string): Promise<PassportState> {
  const r = await call(`/api/measurements/passport/${encodeURIComponent(userId)}`, token);
  if (r.status === 404) return { status: 'none', measured: null };
  if (!r.ok) throw new Error(`passport ${r.status}`);
  const p = await r.json();
  const m = p.measurements || {};
  const measurements: Record<string, number> = {};
  if (p.height > 0) measurements.height = p.height;
  for (const k of MEASURE_KEYS) if (typeof m[k] === 'number' && m[k] > 0) measurements[k] = m[k];
  const status = ['processing', 'failed', 'completed'].includes(p.status) ? p.status : 'none';
  const done = status === 'completed' && !!(measurements.chest || measurements.waist || measurements.hips);
  return {
    status: done ? 'completed' : status === 'completed' ? 'none' : status,
    measured: done ? { basis: 'measured', measurements, gender: normalizeGender(p.gender), fit: p.preferred_fit || undefined } : null,
    height: p.height || undefined,
    weight: p.weight || undefined,
    measuredAt: p.measured_at || null,
  };
}

export async function getQuizAnswers(userId: string, token: string): Promise<QuizAnswers | null> {
  const r = await call(`/api/measurements/quiz-profile/${encodeURIComponent(userId)}`, token);
  if (!r.ok) return null;
  const d = await r.json();
  return usableAnswers(d.profile) ? d.profile : null;
}

export async function saveQuizAnswers(userId: string, token: string, answers: QuizAnswers): Promise<void> {
  const est = estimateBody({ gender: answers.gender, height: answers.height, weight: answers.weight, age: answers.age, shape: answers.shape || {} });
  const m: Record<string, number | null | undefined> = (est && est.measurements) || {};
  const r = await call(`/api/measurements/quiz-profile/${encodeURIComponent(userId)}`, token, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ profile: { ...answers, shape: answers.shape || {} }, estimate: { chest: m.chest, waist: m.waist, hips: m.hips } }),
  });
  if (!r.ok) throw new Error(`Could not save your answers (${r.status}): ${(await r.text()).slice(0, 200)}`);
}

/** The body to size from: a completed fit passport, else the saved quiz answers, else null. */
export async function bodyFor(userId: string, token: string): Promise<{ body: Body | null; passport: PassportState }> {
  const passport = await getPassport(userId, token);
  if (passport.measured) return { body: passport.measured, passport };
  const answers = await getQuizAnswers(userId, token);
  return { body: answers ? { basis: 'estimate', answers } : null, passport };
}

/** A TryOn brand's own garment (category, cut, chart) for this product; null when the store or product has none. */
export async function getBrandGarment(shop: string, handle: string): Promise<(Garment & { has3d: boolean }) | null> {
  const r = await call(`/api/products/${encodeURIComponent(handle)}/tryon-config?shop=${encodeURIComponent(shop)}`, null);
  if (!r.ok) return null;
  const d = await r.json();
  return { category: d.category || 'tops', fitType: d.fit_type || 'regular', chart: d.size_chart || {}, has3d: true };
}

export async function addToWishlist(token: string, item: {
  productId: string; shopDomain: string; productName?: string; imageUrl?: string | null;
  price?: string | null; currency?: string | null; brandName?: string | null; size?: string;
}): Promise<void> {
  const r = await call('/api/wishlist', token, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      product_id: item.productId, shop_domain: item.shopDomain, product_name: item.productName,
      product_image_url: item.imageUrl || undefined, product_price: item.price ? Number(item.price) : undefined,
      currency: item.currency || undefined, brand_name: item.brandName || undefined,
    }),
  });
  if (!r.ok) throw new Error(`Could not save to your wishlist (${r.status})`);
}

export type { Fit };
