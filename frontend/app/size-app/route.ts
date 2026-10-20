import { NextRequest, NextResponse } from 'next/server';

/**
 * Embedded admin for the "TryOn Size" Shopify app (application_url = app.tryon.global/size-app).
 *
 * One page, one login: App Bridge hands us a session token, the backend verifies it and swaps
 * it for an Admin API token (backend/app/api/routes/size_app.py). The merchant never makes a
 * TryOn account. The page shows three steps (choose a plan, add the button, see it live) and
 * the last 30 days of the size card on the store.
 *
 * Plain HTML from a route handler, like /app: App Bridge must be the first script, and the
 * Polaris web components give the page Shopify admin's own look with no bundle.
 */
const SHOP_RE = /^[a-z0-9][a-z0-9-]*\.myshopify\.com$/;

export function GET(request: NextRequest) {
  const shop = (request.nextUrl.searchParams.get('shop') || '').toLowerCase();
  const clientId = process.env.NEXT_PUBLIC_SHOPIFY_SIZE_CLIENT_ID?.trim() || '4a902807121d5f2b63a81c31bbf91429';
  const frameAncestors = SHOP_RE.test(shop)
    ? `https://${shop} https://admin.shopify.com`
    : 'https://admin.shopify.com';

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="shopify-api-key" content="${escapeHtml(clientId)}"/>
  <script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
  <script src="https://cdn.shopify.com/shopifycloud/polaris.js"></script>
  <title>TryOn Size</title>
  <style>
    .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; }
    .stat b { display: block; font-size: 22px; line-height: 1.2; margin-top: 4px; }
    [hidden] { display: none !important; }
  </style>
</head>
<body>
  <s-page heading="TryOn Size">
    <s-banner id="error" tone="critical" heading="TryOn Size could not load" hidden>
      <s-paragraph id="error-text"></s-paragraph>
    </s-banner>

    <s-section id="loading"><s-spinner accessibility-label="Loading"></s-spinner></s-section>

    <div id="ready" hidden>
      <s-section heading="Set up in three steps">
        <s-stack gap="base">
          <s-stack direction="inline" gap="small-200" align-items="center">
            <s-badge id="plan-badge"></s-badge>
            <s-text type="strong">1. Choose your plan</s-text>
          </s-stack>
          <s-paragraph id="plan-text"></s-paragraph>
          <s-button id="plan-btn" variant="primary"></s-button>

          <s-divider></s-divider>

          <s-stack direction="inline" gap="small-200" align-items="center">
            <s-badge id="block-badge"></s-badge>
            <s-text type="strong">2. Add "Find my size" to your product page</s-text>
          </s-stack>
          <s-paragraph>The theme editor opens with the button already placed in your product section. Move it next to the size picker and press Save.</s-paragraph>
          <s-button id="editor-btn">Add the button in the theme editor</s-button>

          <s-divider></s-divider>

          <s-stack direction="inline" gap="small-200" align-items="center">
            <s-badge id="live-badge"></s-badge>
            <s-text type="strong">3. See it on your store</s-text>
          </s-stack>
          <s-paragraph id="live-text"></s-paragraph>
        </s-stack>
      </s-section>

      <s-section heading="Last 30 days">
        <div class="stats">
          <div class="stat"><s-text tone="subdued">Shoppers who opened it</s-text><b id="s-sessions">0</b></div>
          <div class="stat"><s-text tone="subdued">Sizes given</s-text><b id="s-sizes">0</b></div>
          <div class="stat"><s-text tone="subdued">Added to cart</s-text><b id="s-cart">0</b></div>
          <div class="stat"><s-text tone="subdued">Orders</s-text><b id="s-orders">0</b></div>
        </div>
        <s-paragraph id="top-sizes"></s-paragraph>
      </s-section>

      <s-section heading="How it works">
        <s-paragraph>Shoppers answer seven quick questions (height, weight, age and build) and get their size for the product in about 30 seconds, with a % match for every size. No account and no size chart needed. Shoppers who want more can measure themselves with one photo for their measured size, and keep it for every store that uses TryOn.</s-paragraph>
        <s-paragraph>Unlimited shoppers and sizes on every plan. Questions: <s-link href="mailto:support@tryon.global">support@tryon.global</s-link></s-paragraph>
      </s-section>
    </div>
  </s-page>

  <script>
(function () {
  var $ = function (id) { return document.getElementById(id); };
  function fail(msg) {
    $('loading').hidden = true;
    $('error').hidden = false;
    $('error-text').textContent = msg + ' Reload the page, or write to support@tryon.global.';
  }
  function badge(el, done, doneText, todoText) {
    el.setAttribute('tone', done ? 'success' : 'attention');
    el.textContent = done ? doneText : todoText;
  }
  function render(d) {
    badge($('plan-badge'), d.active, 'Done', 'To do');
    $('plan-text').textContent = d.active
      ? 'You are on ' + (d.plan_name || 'TryOn Size') + '. The button shows on your store.'
      : 'Start the 30-day free trial. The button shows on your store once a plan is active.';
    $('plan-btn').textContent = d.active ? 'Change plan' : 'Start free trial';
    $('plan-btn').setAttribute('variant', d.active ? 'secondary' : 'primary');
    $('plan-btn').onclick = function () { window.open(d.pricing_url, '_top'); };
    $('editor-btn').onclick = function () { window.open(d.theme_editor_url, '_blank'); };
    badge($('block-badge'), d.seen_on_store, 'Done', 'To do');
    badge($('live-badge'), d.seen_on_store, 'Live', 'Waiting');
    $('live-text').textContent = d.seen_on_store
      ? 'Shoppers are using Find my size on your store.'
      : 'Open any product with sizes on your store. This step turns green once a shopper opens the size card.';
    var s = d.stats || {};
    $('s-sessions').textContent = s.sessions || 0;
    $('s-sizes').textContent = s.sizes_given || 0;
    $('s-cart').textContent = s.added_to_cart || 0;
    $('s-orders').textContent = s.orders || 0;
    var top = Object.keys(s.top_sizes || {});
    $('top-sizes').textContent = top.length
      ? 'Most given sizes: ' + top.map(function (k) { return k + ' (' + s.top_sizes[k] + ')'; }).join(', ')
      : '';
    $('loading').hidden = true;
    $('ready').hidden = false;
  }
  function load() {
    if (!window.shopify || typeof window.shopify.idToken !== 'function') {
      return fail('Open TryOn Size from your Shopify admin.');
    }
    window.shopify.idToken()
      .then(function (token) {
        return fetch('/api/size-app/session', { method: 'POST', headers: { Authorization: 'Bearer ' + token } });
      })
      .then(function (r) {
        if (!r.ok) throw new Error('status ' + r.status);
        return r.json();
      })
      .then(render)
      .catch(function (e) {
        console.error('[TryOn Size]', e);
        fail('We could not reach TryOn (' + (e && e.message ? e.message : 'network') + ').');
      });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load);
  else load();
})();
  </script>
</body>
</html>`;

  return new NextResponse(html, {
    status: 200,
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-store',
      'Content-Security-Policy': `frame-ancestors ${frameAncestors};`,
    },
  });
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
