import { NextRequest, NextResponse } from 'next/server';

const SHOPIFY_CLIENT_ID = process.env.NEXT_PUBLIC_SHOPIFY_CLIENT_ID || 'ec47b40d60204a8d7cf80aa50e313d19';
const APP_BRIDGE_URL = 'https://cdn.shopify.com/shopifycloud/app-bridge.js';

/**
 * Embedded app entry: Shopify loads tryon.global/app?shop=...&host=... in an iframe.
 * We must serve a document where App Bridge is the FIRST script (no async/defer).
 * Next.js cannot guarantee that, so we return minimal HTML here and load the real
 * app inside an iframe; this document gets the session token and posts it to the iframe.
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
  const iframeSrc = queryString ? `/?${queryString}` : '/';

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="shopify-api-key" content="${escapeHtml(SHOPIFY_CLIENT_ID)}"/>
  <script src="${APP_BRIDGE_URL}"></script>
</head>
<body>
  <iframe id="tryon-app" src="${escapeHtml(iframeSrc)}" style="position:fixed;inset:0;width:100%;height:100%;border:0;"></iframe>
  <script>
(function(){
  function getTokenFn(){
    if (window.shopify && typeof window.shopify.getSessionToken === 'function')
      return window.shopify.getSessionToken.bind(window.shopify);
    return null;
  }
  function sendToken(token) {
    var iframe = document.getElementById('tryon-app');
    if (iframe && iframe.contentWindow)
      iframe.contentWindow.postMessage({ type: 'tryon-session-token', token: token }, window.location.origin);
  }
  function run() {
    var getToken = getTokenFn();
    if (getToken) {
      getToken().then(function(token) { sendToken(token); }).catch(function(){});
      try { fetch('shopify:admin/api/2024-01/shop.json').catch(function(){}); } catch(e) {}
    }
  }
  var attempts = 0;
  function poll() {
    if (getTokenFn()) { run(); return; }
    attempts++;
    if (attempts < 60) setTimeout(poll, 200);
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
