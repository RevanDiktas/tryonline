/**
 * TryOn Cart — Shopify theme app extension asset
 * Listens for TRYON_ADD_TO_CART from the widget iframe; resolves the correct
 * variant for the selected size via __tryonSizeVariantMap (set by Liquid block),
 * adds item to cart with tryon_session_id, and refreshes the cart UI.
 */
(function () {
  var ATTR_KEY = 'tryon_session_id';
  var lastAddKey = '';
  var lastAddTime = 0;
  var DEBOUNCE_MS = 2000;

  window.addEventListener('message', function (e) {
    if (!e.data || e.data.type !== 'TRYON_ADD_TO_CART' || !e.data.payload) return;
    var payload = e.data.payload;
    var size = (payload.size || '').toLowerCase().trim();

    /* Resolve variant: prefer size→variant map from Liquid (try exact key + common aliases), fall back to message variantId */
    var map = window.__tryonSizeVariantMap || {};
    var fallback = window.__tryonFallbackVariantId || parseInt(payload.variantId, 10);
    var sizeAliases = { xs: ['xs', 'extra small'], s: ['s', 'small'], m: ['m', 'medium'], l: ['l', 'large'], xl: ['xl', 'extra large'] };
    var keysToTry = sizeAliases[size] ? sizeAliases[size] : [size];
    var variantId = null;
    for (var i = 0; i < keysToTry.length; i++) {
      if (map[keysToTry[i]] != null) { variantId = map[keysToTry[i]]; break; }
    }
    if (variantId == null) variantId = fallback;

    if (!variantId || Number.isNaN(Number(variantId))) {
      console.warn('[TryOn] Add to cart skipped: no variant for size', size);
      return;
    }

    /* Debounce: avoid duplicate add if same variant added very recently */
    var addKey = variantId + '-' + size;
    var now = Date.now();
    if (addKey === lastAddKey && (now - lastAddTime) < DEBOUNCE_MS) {
      console.warn('[TryOn] Add to cart ignored (duplicate within ' + DEBOUNCE_MS + 'ms)');
      return;
    }
    lastAddKey = addKey;
    lastAddTime = now;

    /* Line item properties: _tryon_size (lowercase for logic), Size (display in cart: XS, S, M, L, XL) */
    var sizeDisplay = (size === 'xs' ? 'XS' : size === 'xl' ? 'XL' : size.length ? size.charAt(0).toUpperCase() + size.slice(1) : size);
    var properties = { _tryon_size: size, Size: sizeDisplay };
    if (payload.session_id) properties[ATTR_KEY] = payload.session_id;

    fetch('/cart/add.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: [{ id: Number(variantId), quantity: 1, properties: properties }],
      }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.items) {
          console.log('[TryOn] Added to cart:', size.toUpperCase(), '— variant', variantId);
          refreshCartUI();
        } else {
          console.warn('[TryOn] Cart add rejected (variant ' + variantId + '):', data.message || data.description || data);
          if (window.__tryonSizeVariantMap) console.warn('[TryOn] Size map keys:', Object.keys(window.__tryonSizeVariantMap).join(', '));
        }
      })
      .catch(function (err) {
        console.error('[TryOn] Cart add failed:', err);
      });
  });

  function refreshCartUI() {
    fetch('/cart.js')
      .then(function (r) { return r.json(); })
      .then(function (cart) {
        /* Update cart count badges (Dawn theme + common selectors) */
        var selectors = [
          '.cart-count-bubble span',
          '[data-cart-count]',
          '.cart-count',
          '#cart-icon-bubble span[aria-hidden]',
        ];
        selectors.forEach(function (sel) {
          document.querySelectorAll(sel).forEach(function (el) {
            el.textContent = cart.item_count;
          });
        });

        /* Fire Shopify events for themes that listen */
        if (typeof window.Shopify !== 'undefined') {
          if (typeof window.Shopify.onCartUpdate === 'function') {
            window.Shopify.onCartUpdate(cart);
          }
        }
        document.dispatchEvent(new CustomEvent('cart:refresh'));
        window.dispatchEvent(new CustomEvent('tryon:cart_added', { detail: cart }));

        /* Open cart drawer/notification if theme supports it */
        var cartDrawerToggle = document.querySelector('[data-cart-drawer-toggle], cart-drawer summary, .js-drawer-open-right');
        if (cartDrawerToggle) cartDrawerToggle.click();
      })
      .catch(function () {});
  }
})();
