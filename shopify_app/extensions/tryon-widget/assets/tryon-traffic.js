/*
  TryOn: store traffic for the conversion comparison. Loaded by both blocks on product pages.

  - visit(): once per visitor per day, tells TryOn a shopper saw a product page that has
    our button.
  - used(): once per visitor per day, when the widget showed this shopper a size or the
    3D try-on; also tags the cart, so the order counts as a widget order whichever
    Add to cart button they use.

  The visitor id is a random id kept in this store's localStorage. No account, no cookie,
  nothing personal. Nothing is sent or stored when the shopper has refused analytics in
  the store's cookie banner (Shopify Customer Privacy API).
*/
(function () {
  if (window.TryonTraffic) return;
  var script = document.currentScript;
  var SHOP = (script && script.getAttribute('data-shop')) || '';
  var PRODUCT = (script && script.getAttribute('data-product')) || '';
  var BASE = (script && script.getAttribute('data-base')) || 'https://tryon.global';
  var VID_KEY = 'tryon_vid';
  var CART_ATTR = '_tryon_visitor_id';

  function allowed() {
    try {
      var cp = window.Shopify && window.Shopify.customerPrivacy;
      if (cp && typeof cp.analyticsProcessingAllowed === 'function') return !!cp.analyticsProcessingAllowed();
    } catch (e) {}
    return true;
  }

  function visitorId() {
    try {
      var v = localStorage.getItem(VID_KEY);
      if (v && /^[A-Za-z0-9_-]{8,64}$/.test(v)) return v;
      var bytes = new Uint8Array(16);
      (window.crypto || window.msCrypto).getRandomValues(bytes);
      v = 'v_' + Array.prototype.map.call(bytes, function (b) { return ('0' + b.toString(16)).slice(-2); }).join('');
      localStorage.setItem(VID_KEY, v);
      return v;
    } catch (e) { return null; }   // storage blocked: this shopper is not counted
  }

  function today() { return new Date().toISOString().slice(0, 10); }

  // One beacon per type per day. text/plain keeps it a "simple" request: no CORS preflight.
  function send(type) {
    if (!SHOP || !allowed()) return false;
    var vid = visitorId();
    if (!vid) return false;
    var dayKey = 'tryon_sent_' + type;
    try { if (localStorage.getItem(dayKey) === today()) return true; } catch (e) {}
    var body = JSON.stringify({ t: type, shop: SHOP, vid: vid, product_id: PRODUCT });
    var url = BASE + '/api/events/store-beacon';
    var ok = false;
    try {
      if (navigator.sendBeacon) ok = navigator.sendBeacon(url, new Blob([body], { type: 'text/plain;charset=UTF-8' }));
    } catch (e) {}
    if (!ok) {
      try { fetch(url, { method: 'POST', mode: 'no-cors', keepalive: true, headers: { 'Content-Type': 'text/plain;charset=UTF-8' }, body: body }); ok = true; } catch (e) {}
    }
    if (ok) { try { localStorage.setItem(dayKey, today()); } catch (e) {} }
    return ok;
  }

  var tagged = false;
  function tagCart() {
    if (tagged || !allowed()) return;
    var vid = visitorId();
    if (!vid) return;
    tagged = true;
    var root = (window.Shopify && window.Shopify.routes && window.Shopify.routes.root) || '/';
    var attributes = {};
    attributes[CART_ATTR] = vid;
    fetch(root + 'cart/update.js', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin',
      body: JSON.stringify({ attributes: attributes })
    }).catch(function () { tagged = false; });
  }

  window.TryonTraffic = {
    visit: function () { send('visit'); },
    used: function () { send('visit'); send('used'); tagCart(); }
  };

  // A shopper whose answer changed in the cookie banner is picked up on the next page.
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', window.TryonTraffic.visit);
  else window.TryonTraffic.visit();
})();
