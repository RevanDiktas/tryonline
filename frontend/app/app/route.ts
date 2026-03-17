import { NextRequest, NextResponse } from 'next/server';

const SHOPIFY_CLIENT_ID = process.env.NEXT_PUBLIC_SHOPIFY_CLIENT_ID || 'ec47b40d60204a8d7cf80aa50e313d19';
const APP_BRIDGE_URL = 'https://cdn.shopify.com/shopifycloud/app-bridge.js';

/**
 * Embedded entry: Shopify loads tryon.global/app?shop=... in ONE iframe (direct child of admin).
 *
 * 1) This response is minimal HTML with App Bridge as the ONLY external script (sync, first).
 * 2) We verify session auth via direct Admin API fetch + token APIs when available.
 * 3) Then we redirect in the same iframe to /?shop=...
 */
export function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const shop = searchParams.get('shop');
  const isEmbedded = shop?.includes('.myshopify.com');

  if (!isEmbedded) {
    const target = searchParams.toString() ? `/?${searchParams.toString()}` : '/';
    return NextResponse.redirect(new URL(target, request.url));
  }

  const queryString = searchParams.toString();
  const nextPath = queryString ? `/?${queryString}` : '/';
  const debug = searchParams.get('debug') === '1' || searchParams.get('debug') === 'true';
  const hostParam = searchParams.get('host') || '';

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="shopify-api-key" content="${escapeHtml(SHOPIFY_CLIENT_ID)}"/>
  ${hostParam ? `<meta name="shopify-host" content="${escapeHtml(hostParam)}"/>` : ''}
  <script src="${APP_BRIDGE_URL}"></script>
</head>
<body style="margin:0;font-family:system-ui,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;color:#666;padding:20px;">
  <p id="msg">Loading Tryon…</p>
  <pre id="debug" style="margin-top:12px;font-size:11px;text-align:left;max-width:100%;overflow:auto;display:none;"></pre>
  <script>
(function(){
  var nextUrl = ${JSON.stringify(nextPath)};
  var debug = ${debug ? 'true' : 'false'};
  var debugEl = document.getElementById('debug');
  var msgEl = document.getElementById('msg');

  function log(s) {
    if (typeof console !== 'undefined' && console.log) console.log('[Tryon session]', s);
    if (debug && debugEl) { debugEl.style.display = 'block'; debugEl.textContent += s + '\n'; }
  }
  function setMsg(s) { if (msgEl) msgEl.textContent = s; }
  function appendMsg(s) { if (msgEl) msgEl.textContent = (msgEl.textContent || '') + s; }

  function go() {
    if (!debug) window.location.replace(window.location.origin + nextUrl);
    else log('(debug: redirect skipped)');
  }

  function runChecks() {
    var shopifyGlobal = window.shopify || null;
    var hasIdToken = !!(shopifyGlobal && typeof shopifyGlobal.idToken === 'function');
    var hasGetSessionToken = !!(shopifyGlobal && typeof shopifyGlobal.getSessionToken === 'function');

    log('shopify global: ' + (!!shopifyGlobal));
    log('has idToken(): ' + hasIdToken);
    log('has getSessionToken(): ' + hasGetSessionToken);

    // Primary signal: direct Admin API call should be authenticated by App Bridge.
    try {
      fetch('shopify:admin/api/2024-01/shop.json', { method: 'GET' })
        .then(function(res) {
          log('Admin API shop.json: ' + res.status);
          if (debug) appendMsg(' | Admin API: ' + res.status);
        })
        .catch(function(e) {
          log('FAIL: Admin API ' + (e && e.message ? e.message : String(e)));
          if (debug) appendMsg(' | Admin API: error');
        });
    } catch (e) {
      log('FAIL: fetch threw ' + (e && e.message ? e.message : String(e)));
    }

    if (hasIdToken) {
      shopifyGlobal.idToken()
        .then(function(token) {
          var ok = token && typeof token === 'string' && token.length > 0;
          log(ok ? 'idToken() OK (length ' + token.length + ')' : 'FAIL: idToken empty');
          if (debug) setMsg(ok ? 'Session token API: idToken OK' : 'Session token API: idToken empty');
        })
        .catch(function(e) {
          log('FAIL: idToken() ' + (e && e.message ? e.message : String(e)));
        });
    }

    if (hasGetSessionToken) {
      shopifyGlobal.getSessionToken()
        .then(function(token) {
          var ok = token && typeof token === 'string' && token.length > 0;
          log(ok ? 'getSessionToken() OK (length ' + token.length + ')' : 'FAIL: getSessionToken empty');
          if (debug) setMsg(ok ? 'Session token API: getSessionToken OK' : 'Session token API: getSessionToken empty');
        })
        .catch(function(e) {
          log('FAIL: getSessionToken() ' + (e && e.message ? e.message : String(e)));
        });
    }

    if (!hasIdToken && !hasGetSessionToken) {
      log('No token API exposed on window.shopify (possible on some App Bridge versions).');
      if (debug) setMsg('Session token API: not exposed');
    }

    if (!debug) setTimeout(go, 900);
    else setTimeout(go, 5000);
  }

  var attempts = 0;
  function pollReady() {
    var ready = typeof window !== 'undefined' && !!window.shopify;
    if (ready) { runChecks(); return; }
    attempts++;
    if (attempts < 80) setTimeout(pollReady, 250);
    else {
      log('FAIL: window.shopify not ready after 80 attempts. If postMessage origin mismatch appears, App Bridge handshake failed.');
      setMsg('Session token: timeout');
      if (!debug) go();
      else log('(debug: waiting)');
    }
  }

  function start() {
    if (debug && typeof window !== 'undefined' && window.location) {
      log('href: ' + window.location.href);
      log('has host param: ' + (window.location.search.indexOf('host=') !== -1));
      log('referrer: ' + document.referrer);
    }
    pollReady();
  }

  if (typeof window !== 'undefined' && window.addEventListener)
    window.addEventListener('load', function() { setTimeout(start, 400); });
  else
    setTimeout(start, 500);
})();
  </script>
</body>
</html>`;

  return new NextResponse(html, {
    status: 200,
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-store',
    },
  });
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
