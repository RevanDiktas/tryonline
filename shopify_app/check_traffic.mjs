// Checks for assets/tryon-traffic.js: the cart tag on first use and on later visits.
// Fake browser, no network.   node shopify_app/check_traffic.mjs
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const src = readFileSync(new URL('./extensions/tryon-widget/assets/tryon-traffic.js', import.meta.url), 'utf8');
let failures = 0;
const check = (name, cond, detail) => { console.log((cond ? 'PASS ' : 'FAIL ') + name + (!cond && detail !== undefined ? '  (' + JSON.stringify(detail) + ')' : '')); if (!cond) failures++; };
const settle = () => new Promise((r) => setTimeout(r, 5));

// One page load. `store` is the shopper's localStorage, `cart` the Shopify cart; both outlive the page.
function page(store, cart, { consent = true } = {}) {
  const calls = [];
  const win = {
    Shopify: { routes: { root: '/' }, customerPrivacy: { analyticsProcessingAllowed: () => consent } },
    crypto: { getRandomValues: (b) => { for (let i = 0; i < b.length; i++) b[i] = (i * 37 + 11) % 256; return b; } },
  };
  const ctx = {
    window: win,
    document: { currentScript: { getAttribute: (k) => ({ 'data-shop': 'shop.myshopify.com', 'data-product': '1' }[k] || '') }, readyState: 'complete', addEventListener() {} },
    localStorage: { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } },
    navigator: { sendBeacon: (url, blob) => { calls.push(['beacon', blob.parts[0]]); return true; } },
    Blob: class { constructor(parts) { this.parts = parts; } },
    fetch: async (url, opts = {}) => {
      calls.push([opts.method || 'GET', url]);
      if (url.endsWith('cart.js')) return { json: async () => cart };
      if (url.endsWith('cart/update.js')) { Object.assign(cart.attributes, JSON.parse(opts.body).attributes); return { json: async () => cart }; }
      return { json: async () => ({}) };
    },
    Uint8Array, Date, JSON, Promise, Array, String, setTimeout,
  };
  vm.runInNewContext(src, ctx);
  return { win, calls, writes: () => calls.filter((c) => c[0] === 'POST').length, reads: () => calls.filter((c) => c[0] === 'GET').length };
}

const store = {};
let cart = { attributes: {} };

let p = page(store, cart); await settle();
check('new visitor: cart is not read or written', p.reads() === 0 && p.writes() === 0, p.calls);
check('new visitor: one visit beacon', p.calls.filter((c) => c[0] === 'beacon').length === 1, p.calls);

p.win.TryonTraffic.used(); await settle();
const vid = store.tryon_vid;
check('widget showed a size: cart carries the visitor id', cart.attributes._tryon_visitor_id === vid && !!vid, cart);
check('widget showed a size: use is remembered', !!store.tryon_used, store);

p = page(store, cart); await settle();
check('later page, same cart: read once, not written again', p.reads() === 1 && p.writes() === 0, p.calls);

cart = { attributes: {} };   // two days later: the order went through, Shopify gave a new cart
p = page(store, cart); await settle();
check('later page, new cart, widget not opened: tagged again', cart.attributes._tryon_visitor_id === vid && p.writes() === 1, p.calls);
p.win.TryonTraffic.used(); await settle();
check('same page, size shown as well: still one write', p.writes() === 1, p.calls);

cart = { attributes: {} };
p = page(store, cart, { consent: false }); await settle();
check('analytics refused in the cookie banner: nothing read, written or sent', p.calls.length === 0 && !cart.attributes._tryon_visitor_id, p.calls);

const fresh = {}; cart = { attributes: {} };
p = page(fresh, cart, { consent: false }); p.win.TryonTraffic.used(); await settle();
check('refused, then used: no id stored, no tag', !fresh.tryon_used && !fresh.tryon_vid && !cart.attributes._tryon_visitor_id, fresh);

const a = readFileSync(new URL('../shopify_size_app/extensions/size-widget/assets/tryon-traffic.js', import.meta.url), 'utf8');
check('TryOn Size app ships the same file', a === src);

process.exit(failures ? 1 : 0);
