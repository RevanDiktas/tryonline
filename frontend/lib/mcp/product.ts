/**
 * A product page URL -> what sizing needs: the product's own size labels with stock, its type
 * and title (for the category), and the store's myshopify domain (for a TryOn brand's chart).
 *
 * Works for any Shopify store: every storefront serves /products/<handle>.js and /meta.json
 * publicly. Other stores return null and the tool says it needs the sizes.
 *
 * The URL comes from a chat, so fetching it is guarded: https only, a public host name (no IP
 * literals, no localhost), only the two Shopify paths, redirects re-checked, short timeouts
 * and a size cap.
 */

export interface ProductSize { label: string; available: boolean }

export interface ShopifyProduct {
  url: string;
  host: string;
  handle: string;
  title: string;
  productType: string;
  vendor: string;
  image: string | null;
  price: string | null;
  currency: string | null;
  sizes: ProductSize[];
  sizeOptionName: string | null;
  /** *.myshopify.com, when the store says (meta.json) */
  shop: string | null;
  storeName: string | null;
  storeCountry: string | null;
}

const SIZE_WORDS = ['size', 'maat', 'taille', 'talla', 'größe', 'grösse', 'groesse', 'größe', 'tamaño', 'taglia'];
const LETTER_SIZES = new Set(['xxxs', 'xxs', 'xs', 's', 'm', 'l', 'xl', 'xxl', 'xxxl', '2xs', '3xs', '2xl', '3xl', '4xl', '5xl',
  'x-small', 'small', 'medium', 'large', 'x-large', 'xx-large', 'one size', 'os']);
const MAX_BYTES = 2_000_000;
const TIMEOUT_MS = 6000;

export class ProductUrlError extends Error {}

function publicHost(host: string): boolean {
  const h = host.toLowerCase();
  if (!h.includes('.') || h === 'localhost' || h.endsWith('.localhost') || h.endsWith('.local') || h.endsWith('.internal')) return false;
  if (/^[\d.]+$/.test(h) || h.includes(':') || h.startsWith('[')) return false; // IPv4 / IPv6 literals
  return true;
}

/** https://store.com/(locale/)(collections/x/)products/<handle>[?variant=..] -> parts, or throws. */
export function parseProductUrl(raw: string): { origin: string; host: string; handle: string; variantId: number | null } {
  let u: URL;
  try { u = new URL(raw.trim()); } catch { throw new ProductUrlError('That is not a link to a product page.'); }
  if (u.protocol !== 'https:') throw new ProductUrlError('Only https product links are supported.');
  if (u.username || u.password || u.port) throw new ProductUrlError('That link is not a normal store link.');
  if (!publicHost(u.hostname)) throw new ProductUrlError('That link is not a public store.');
  const m = u.pathname.match(/\/products\/([a-z0-9][a-z0-9\-_.%]*?)(?:\.js|\.json)?\/?$/i);
  if (!m) throw new ProductUrlError('That link is not a product page (it should contain /products/...).');
  const variant = parseInt(u.searchParams.get('variant') || '', 10);
  return { origin: `https://${u.hostname}`, host: u.hostname.toLowerCase(), handle: decodeURIComponent(m[1]).toLowerCase(), variantId: Number.isFinite(variant) ? variant : null };
}

// Shopify rate-limits its public storefront JSON per IP (429), and every chat reaches it from
// the same few server IPs. Successful reads are kept for 2 minutes per server instance, and a
// 429 gets one retry after Shopify's Retry-After (at most 2 s).
const CACHE_MS = 2 * 60 * 1000;
const cache = new Map<string, { at: number; value: any }>();

async function getJson(url: string): Promise<any | null> {
  const hit = cache.get(url);
  if (hit && Date.now() - hit.at < CACHE_MS) return hit.value;
  let value = await fetchJson(url);
  if (value === RATE_LIMITED) {
    await new Promise((r) => setTimeout(r, retryAfterMs));
    value = await fetchJson(url);
  }
  if (value === RATE_LIMITED) { lastRateLimitedAt = Date.now(); return null; }
  if (value === null) return null;
  if (cache.size > 500) cache.clear();
  cache.set(url, { at: Date.now(), value });
  return value;
}

const RATE_LIMITED = Symbol('rate-limited');
let lastRateLimitedAt = 0;
/** True when Shopify throttled one of our reads in the last few seconds (for an honest message). */
export const recentlyRateLimited = () => Date.now() - lastRateLimitedAt < 10_000;
let retryAfterMs = 1000;

async function fetchJson(url: string, hops = 0): Promise<any | typeof RATE_LIMITED | null> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const r = await fetch(url, { redirect: 'manual', signal: ctrl.signal, headers: { accept: 'application/json', 'user-agent': 'TryOnSizeBot/1.0 (+https://tryon.global)' } });
    if (r.status >= 300 && r.status < 400) {
      const loc = r.headers.get('location');
      if (!loc || hops >= 2) return null;
      const next = new URL(loc, url);
      if (next.protocol !== 'https:' || !publicHost(next.hostname)) return null;
      return fetchJson(next.toString(), hops + 1);
    }
    if (r.status === 429) {
      const ra = Number(r.headers.get('retry-after'));
      retryAfterMs = Number.isFinite(ra) && ra > 0 ? Math.min(ra * 1000, 2000) : 1000;
      return RATE_LIMITED;
    }
    if (!r.ok) return null;
    const len = Number(r.headers.get('content-length') || 0);
    if (len > MAX_BYTES) return null;
    const text = await r.text();
    if (text.length > MAX_BYTES) return null;
    return JSON.parse(text);
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

function looksLikeSize(value: string): boolean {
  const v = value.trim().toLowerCase();
  if (LETTER_SIZES.has(v)) return true;
  const first = v.split('/')[0];
  const n = Number(first);
  return String(n) === first && n >= 20 && n <= 60;
}

/** Index of the size option, by name (EN/NL/FR/ES/DE/IT) or a lone option whose values all look like sizes. Same rule as the Liquid blocks. */
export function sizeOptionIndex(options: { name: string; values: string[] }[]): number {
  const byName = options.findIndex((o) => SIZE_WORDS.some((w) => o.name.toLowerCase().includes(w)));
  if (byName >= 0) return byName;
  if (options.length === 1 && options[0].values.length > 0 && options[0].values.every(looksLikeSize)) return 0;
  return -1;
}

export async function fetchShopifyProduct(rawUrl: string): Promise<ShopifyProduct | null> {
  const { origin, host, handle, variantId } = parseProductUrl(rawUrl);
  const [p, meta] = await Promise.all([
    getJson(`${origin}/products/${encodeURIComponent(handle)}.js`),
    getJson(`${origin}/meta.json`),
  ]);
  if (!p || !Array.isArray(p.variants)) return null;

  const options: { name: string; values: string[] }[] = (p.options || []).map((o: any) =>
    typeof o === 'string' ? { name: o, values: [] } : { name: String(o?.name || ''), values: (o?.values || []).map(String) });
  const pos = sizeOptionIndex(options);
  const variants: any[] = p.variants;
  const base = variants.find((v) => v.id === variantId) || null;

  const order: string[] = [];
  const byKey: Record<string, ProductSize> = {};
  if (pos >= 0 && !p.gift_card) {
    for (const v of variants) {
      const opts: string[] = v.options || [v.option1, v.option2, v.option3].filter((x) => x != null);
      // With ?variant=, only that colour's sizes (as the card does); otherwise any colour.
      if (base && opts.some((o, j) => j !== pos && o !== (base.options || [])[j])) continue;
      const label = String(opts[pos] || '').trim();
      const key = label.toLowerCase();
      if (!key) continue;
      if (!byKey[key]) { byKey[key] = { label, available: false }; order.push(key); }
      if (v.available) byKey[key].available = true;
    }
  }

  const priceCents = (base || variants[0])?.price;
  const img = p.featured_image ? String(p.featured_image) : null;
  const shop = typeof meta?.myshopify_domain === 'string' && /^[a-z0-9-]+\.myshopify\.com$/.test(meta.myshopify_domain)
    ? meta.myshopify_domain : null;
  return {
    url: `${origin}/products/${handle}${base ? `?variant=${base.id}` : ''}`,
    host,
    handle,
    title: String(p.title || ''),
    productType: String(p.type || ''),
    vendor: String(p.vendor || ''),
    image: img ? (img.startsWith('//') ? `https:${img}` : img) : null,
    price: typeof priceCents === 'number' ? (priceCents / 100).toFixed(2) : null,
    currency: typeof meta?.currency === 'string' ? meta.currency : null,
    sizes: order.map((k) => byKey[k]),
    sizeOptionName: pos >= 0 ? options[pos].name : null,
    shop,
    storeName: typeof meta?.name === 'string' ? meta.name : null,
    storeCountry: typeof meta?.country === 'string' ? meta.country : null,
  };
}

export interface ProductHit { title: string; url: string; price: string | null; available: boolean; image: string | null; productType: string }

/** A store (link to any page of it, or just its domain) -> the store's origin, and the
 *  collection handle when the link is a collection page. Same guards as product links. */
export function parseStoreUrl(raw: string): { origin: string; collection: string | null } {
  const text = raw.trim();
  let u: URL;
  try { u = new URL(/^https?:\/\//i.test(text) ? text : `https://${text}`); } catch { throw new ProductUrlError('That is not a store link.'); }
  if (u.protocol !== 'https:') throw new ProductUrlError('Only https store links are supported.');
  if (u.username || u.password || u.port || !publicHost(u.hostname)) throw new ProductUrlError('That link is not a public store.');
  const m = u.pathname.match(/\/collections\/([a-z0-9][a-z0-9\-_.%]*)/i);
  return { origin: `https://${u.hostname.toLowerCase()}`, collection: m ? decodeURIComponent(m[1]).toLowerCase() : null };
}

const words = (q: string) => q.toLowerCase().split(/[^a-z0-9à-ÿ]+/).filter((w) => w.length > 1);
const matches = (p: any, q: string[]) => {
  if (!q.length) return true;
  const hay = `${p.title || ''} ${p.product_type || p.type || ''} ${(Array.isArray(p.tags) ? p.tags.join(' ') : p.tags) || ''}`.toLowerCase();
  // "t-shirt" should find "tee" and "shirt" products too: any query word is enough.
  return q.some((w) => hay.includes(w) || (w === 'tshirt' && hay.includes('shirt')));
};

/** Products in a Shopify store (optionally one collection), matching `query`. Up to `limit`. */
export async function findShopifyProducts(store: string, query: string, limit = 10): Promise<{ origin: string; storeName: string | null; products: ProductHit[] } | null> {
  const { origin, collection } = parseStoreUrl(store);
  // Shopify throttles /products.json and /collections/x/products.json hard (a 60 s Retry-After
  // after a few calls from one IP), while /search/suggest.json holds up. So search first; a
  // collection link with no query is searched by its own name ("t-shirts").
  const searchFor = (query || '').trim() || (collection ? collection.replace(/[-_]+/g, ' ') : '');
  const q = words(searchFor);
  const meta = await getJson(`${origin}/meta.json`);
  let hits: ProductHit[] = [];
  const fromList = (list: any[], filterBy: string[]) => list.filter((p) => matches(p, filterBy)).map((p) => ({
    title: String(p.title || ''),
    url: `${origin}/products/${p.handle}`,
    price: p.variants?.[0]?.price != null ? String(p.variants[0].price) : null,
    available: Array.isArray(p.variants) ? p.variants.some((v: any) => v.available) : true,
    image: p.images?.[0]?.src || null,
    productType: String(p.product_type || ''),
  }));
  if (searchFor) {
    const d = await getJson(`${origin}/search/suggest.json?q=${encodeURIComponent(searchFor)}&resources%5Btype%5D=product&resources%5Blimit%5D=${limit}`);
    const list = d?.resources?.results?.products;
    if (Array.isArray(list)) hits = list.map((p: any) => ({
      title: String(p.title || ''), url: `${origin}/products/${p.handle}`, price: p.price != null ? String(p.price) : null,
      available: p.available !== false, image: p.image || null, productType: String(p.type || ''),
    }));
  }
  if (!hits.length && collection) {
    const d = await getJson(`${origin}/collections/${encodeURIComponent(collection)}/products.json?limit=60`);
    // The whole collection unless the shopper named something within it.
    if (d && Array.isArray(d.products)) hits = fromList(d.products, words(query || ''));
  }
  if (!hits.length) {
    const d = await getJson(`${origin}/products.json?limit=60`);
    if (d && Array.isArray(d.products)) hits = fromList(d.products, q);
    else if (!meta) return null;
  }
  return { origin, storeName: typeof meta?.name === 'string' ? meta.name : null, products: hits.slice(0, limit) };
}
