import { NextRequest, NextResponse } from 'next/server';
import { SHOPIFY_EMBEDDED_CLIENT_ID } from '@/lib/shopify-embedded-client-id';
const APP_BRIDGE_URL = 'https://cdn.shopify.com/shopifycloud/app-bridge.js';

/**
 * Embedded entry: Shopify loads tryon.global/app?shop=... in ONE iframe (direct child of admin).
 *
 * 1) This response is minimal HTML with App Bridge as the ONLY external script (sync, first) -
 *    satisfies Shopify’s embedded checks.
 * 2) We run getSessionToken + shopify:admin fetch here.
 * 3) We then redirect IN THE SAME IFRAME to /brand?shop=... (the brand-only surface). We go
 *    straight to /brand, NOT the marketing root /: on the pilot host (tryon.global) the root
 *    renders the consumer landing because isShopifyMode() only flips true on app.tryon.global.
 *    /brand has its own auth gate (-> /login when logged out), so merchants never see the
 *    consumer site. No nested iframe - avoids postMessage errors.
 */
export function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const shop = searchParams.get('shop');
  const isEmbedded = shop?.includes('.myshopify.com');

  if (!isEmbedded) {
    const target = searchParams.toString() ? `/brand?${searchParams.toString()}` : '/brand';
    return NextResponse.redirect(new URL(target, request.url));
  }

  const queryString = searchParams.toString();
  const nextPath = queryString ? `/brand?${queryString}` : '/brand';
  const debug = searchParams.get('debug') === '1' || searchParams.get('debug') === 'true';

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="shopify-api-key" content="${escapeHtml(SHOPIFY_EMBEDDED_CLIENT_ID)}"/>
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
    if (debug && debugEl) { debugEl.style.display = 'block'; debugEl.textContent += s + '\\n'; }
  }
  function setMsg(s) { if (msgEl) msgEl.textContent = s; }
  function appendMsg(s) { if (msgEl) msgEl.textContent = (msgEl.textContent || '') + s; }
  function sendProof(token, source) {
    if (!token || typeof token !== 'string') {
      log('FAIL: no token to send proof (' + source + ')');
      return;
    }
    fetch('/api/session-proof', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token,
      },
      body: JSON.stringify({ source: source }),
    })
      .then(function(res) {
        log('Session proof (' + source + '): ' + res.status);
        if (debug) appendMsg(' | Session proof: ' + res.status);
      })
      .catch(function(e) {
        log('FAIL: session proof (' + source + ') ' + (e && e.message ? e.message : String(e)));
        if (debug) appendMsg(' | Session proof: error');
      });
  }
  function getSessionTokenFn(){
    if (window.shopify && typeof window.shopify.getSessionToken === 'function')
      return window.shopify.getSessionToken.bind(window.shopify);
    return null;
  }
  function getIdTokenFn(){
    if (window.shopify && typeof window.shopify.idToken === 'function')
      return window.shopify.idToken.bind(window.shopify);
    return null;
  }
  function go() {
    if (!debug) window.location.replace(window.location.origin + nextUrl);
    else log('(debug: redirect skipped)');
  }
  function run() {
    var getIdToken = getIdTokenFn();
    var getSessionToken = getSessionTokenFn();
    log('Token API idToken: ' + !!getIdToken + ', getSessionToken: ' + !!getSessionToken);

    if (getIdToken) {
      getIdToken()
        .then(function(token) {
          var ok = token && typeof token === 'string' && token.length > 0;
          log(ok ? 'idToken OK (length ' + token.length + ')' : 'FAIL: idToken empty');
          setMsg(debug ? (ok ? 'Session token API: idToken OK' : 'Session token API: idToken empty') : 'Loading Tryon…');
          if (ok) sendProof(token, 'idToken');
        })
        .catch(function(e) {
          log('FAIL: idToken error ' + (e && e.message ? e.message : String(e)));
        });
    } else if (getSessionToken) {
      getSessionToken()
        .then(function(token) {
          var ok = token && typeof token === 'string' && token.length > 0;
          log(ok ? 'getSessionToken OK (length ' + token.length + ')' : 'FAIL: getSessionToken empty');
          setMsg(debug ? (ok ? 'Session token API: getSessionToken OK' : 'Session token API: getSessionToken empty') : 'Loading Tryon…');
          if (ok) sendProof(token, 'getSessionToken');
        })
        .catch(function(e) {
          log('FAIL: getSessionToken error ' + (e && e.message ? e.message : String(e)));
        });
    } else {
      log('Token API not exposed on window.shopify');
      if (debug) setMsg('Session token API: not exposed');
    }

    if (!debug) setTimeout(go, 400);
    else setTimeout(go, 5000);
  }
  var attempts = 0;
  function poll() {
    if (window.shopify) { run(); return; }
    attempts++;
    if (attempts < 60) setTimeout(poll, 200);
    else {
      log('FAIL: App Bridge global not ready after 60 attempts');
      setMsg('Session token: timeout');
      if (!debug) go();
      else log('(debug: waiting)');
    }
  }
  setTimeout(poll, 100);
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
