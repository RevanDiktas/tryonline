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

    /* Request cart sections so we get fresh HTML and can update UI without full page refresh (Shopify bundled section rendering) */
    var sectionsList = 'cart-icon-bubble,cart-drawer,cart-items';
    var body = {
      items: [{ id: Number(variantId), quantity: 1, properties: properties }],
      sections: sectionsList,
    };

    fetch('/cart/add.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.items) {
          console.log('[TryOn] Added to cart:', size.toUpperCase(), '— variant', variantId);
          refreshCartUI(data);
        } else {
          console.warn('[TryOn] Cart add rejected (variant ' + variantId + '):', data.message || data.description || data);
          if (window.__tryonSizeVariantMap) console.warn('[TryOn] Size map keys:', Object.keys(window.__tryonSizeVariantMap).join(', '));
        }
      })
      .catch(function (err) {
        console.error('[TryOn] Cart add failed:', err);
      });
  });

  /**
   * Replace DOM elements with section HTML from Shopify (bundled section rendering).
   * This is why the cart updates without refresh — we swap in the new HTML.
   */
  function renderSections(sections) {
    if (!sections || typeof sections !== 'object') return;
    var sectionIds = ['cart-icon-bubble', 'cart-drawer', 'cart-items'];
    for (var i = 0; i < sectionIds.length; i++) {
      var id = sectionIds[i];
      var html = sections[id];
      if (!html || typeof html !== 'string') continue;
      var wrap = document.createElement('div');
      wrap.innerHTML = html.trim();
      var newEl = wrap.firstElementChild;
      if (!newEl || !newEl.id) continue;
      var existing = document.getElementById(newEl.id);
      if (existing && existing.parentNode) {
        existing.parentNode.replaceChild(newEl, existing);
      }
    }
  }

  function refreshCartUI(addResponse) {
    /* If add response included sections (bundled section rendering), replace DOM first — cart updates without refresh */
    if (addResponse && addResponse.sections) {
      renderSections(addResponse.sections);
    }

    fetch('/cart.js')
      .then(function (r) { return r.json(); })
      .then(function (cart) {
        /* Fallback: update cart count badges if section replace didn’t run or theme uses different IDs */
        var selectors = [
          '.cart-count-bubble span',
          '[data-cart-count]',
          '.cart-count',
          '#cart-icon-bubble span[aria-hidden]',
          '.cart-count-bubble',
        ];
        selectors.forEach(function (sel) {
          try {
            document.querySelectorAll(sel).forEach(function (el) {
              if (el.tagName === 'SPAN' || el.tagName === 'SMALL') el.textContent = cart.item_count;
              else if (el.classList && el.classList.contains('cart-count-bubble')) el.textContent = cart.item_count;
            });
          } catch (err) {}
        });

        if (typeof window.Shopify !== 'undefined') {
          if (typeof window.Shopify.onCartUpdate === 'function') {
            window.Shopify.onCartUpdate(cart);
          }
        }
        document.dispatchEvent(new CustomEvent('cart:refresh', { detail: cart }));
        window.dispatchEvent(new CustomEvent('tryon:cart_added', { detail: cart }));

        var cartDrawerToggle = document.querySelector('[data-cart-drawer-toggle], cart-drawer summary, .js-drawer-open-right, [aria-controls="cart-drawer"]');
        if (cartDrawerToggle) cartDrawerToggle.click();
      })
      .catch(function () {});
  }
})();
