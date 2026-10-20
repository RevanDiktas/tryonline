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

async function getJson(url: string, hops = 0): Promise<any | null> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const r = await fetch(url, { redirect: 'manual', signal: ctrl.signal, headers: { accept: 'application/json', 'user-agent': 'TryOnSizeBot/1.0 (+https://tryon.global)' } });
    if (r.status >= 300 && r.status < 400) {
      const loc = r.headers.get('location');
      if (!loc || hops >= 2) return null;
      const next = new URL(loc, url);
      if (next.protocol !== 'https:' || !publicHost(next.hostname)) return null;
      return getJson(next.toString(), hops + 1);
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
