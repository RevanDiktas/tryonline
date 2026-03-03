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

    var sectionIds = getCartSectionIds();
    var sectionsList = sectionIds.slice(0, 5).join(',');
    var body = {
      items: [{ id: Number(variantId), quantity: 1, properties: properties }],
      sections: sectionsList,
      sections_url: (window.location.pathname || '/').split('?')[0],
    };
    var cartAddUrl = (typeof window.Shopify !== 'undefined' && window.Shopify.routes && window.Shopify.routes.root) ? window.Shopify.routes.root + 'cart/add.js' : '/cart/add.js';

    fetch(cartAddUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.items) {
          console.log('[TryOn] Added to cart:', size.toUpperCase(), '— variant', variantId);
          if (data.sections) {
            var keys = Object.keys(data.sections).filter(function (k) { return data.sections[k]; });
            console.log('[TryOn] Add response had sections:', keys.length ? keys.join(', ') : 'all null');
          }
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

  /** Discover cart-related section IDs (Dawn: data-id on #main-cart-items; or wrapper id from shopify-section-*). */
  function getCartSectionIds() {
    var ids = [];
    var seen = {};
    function add(id) {
      if (id && !seen[id]) { seen[id] = true; ids.push(id); }
    }
    var nodes = document.querySelectorAll('[id^="shopify-section-"]');
    for (var i = 0; i < nodes.length; i++) {
      var sectionId = nodes[i].id.replace(/^shopify-section-/, '');
      if (/cart|drawer|bubble|icon|main-cart/.test(sectionId)) add(sectionId);
    }
    var mainCart = document.getElementById('main-cart-items');
    if (mainCart && mainCart.dataset && mainCart.dataset.id) add(mainCart.dataset.id);
    var cartDrawerEl = document.querySelector('cart-drawer, [id*="cart-drawer"], [id*="CartDrawer"]');
    if (cartDrawerEl) {
      var wrapper = cartDrawerEl.closest('[id^="shopify-section-"]');
      if (wrapper) add(wrapper.id.replace(/^shopify-section-/, ''));
    }
    if (ids.length) return ids;
    return ['main-cart-items', 'cart-drawer', 'cart-icon-bubble', 'cart-items', 'cart-footer'];
  }

  /**
   * Update cart sections from add response (Dawn-aligned).
   * Per Shopify + Dawn: only update innerHTML of the section wrapper so the wrapper
   * and theme behavior (custom elements, listeners) stay intact. Replacing the whole
   * node can break the basket and prevent instant cart updates.
   * @see https://shopify.dev/docs/api/ajax/reference/cart#bundled-section-rendering
   * @see https://nickdrishinski.com/blogs/shopify/how-dawn-theme-uses-section-rendering-api-for-cart-refresh
   */
  function renderSections(sections) {
    if (!sections || typeof sections !== 'object') return 0;
    var replaced = 0;
    for (var key in sections) {
      if (!sections.hasOwnProperty(key)) continue;
      var html = sections[key];
      if (!html || typeof html !== 'string') continue;
      var wrap = document.createElement('div');
      wrap.innerHTML = html.trim();
      var newEl = wrap.querySelector('[id^="shopify-section-"]') || wrap.firstElementChild;
      if (!newEl) continue;
      var newId = newEl.id;
      var keySlug = key.replace(/^template--\d+__/, '');
      var existing = (newId && document.getElementById(newId)) || document.querySelector('[id^="shopify-section-"][id*="' + keySlug + '"]');
      if (!existing || !existing.parentNode) continue;
      try {
        existing.innerHTML = newEl.innerHTML;
        replaced++;
      } catch (e) {}
    }
    return replaced;
  }

  /** Dawn-style: fetch section as HTML and replace specific cart elements. Returns a Promise that resolves when cart-drawer and cart-icon-bubble fetches finish. */
  function refreshCartDrawerDawn() {
    var path = (window.location.pathname || '/').split('?')[0];
    var base = (typeof window.Shopify !== 'undefined' && window.Shopify.routes && window.Shopify.routes.root) ? window.Shopify.routes.root.replace(/\/$/, '') : '';
    var sep = path.indexOf('?') >= 0 ? '&' : '?';

    function replaceSectionHtml(sectionId) {
      var url = (base || path) + sep + 'section_id=' + encodeURIComponent(sectionId);
      return fetch(url)
        .then(function (r) { return r.text(); })
        .then(function (htmlText) {
          if (!htmlText || htmlText.length < 10) return;
          var doc = new DOMParser().parseFromString(htmlText, 'text/html');
          var sectionWrap = doc.querySelector('[id^="shopify-section-"]') || doc.body.firstElementChild;
          if (!sectionWrap || !sectionWrap.id) return;
          var existing = document.getElementById(sectionWrap.id) || document.querySelector('[id^="shopify-section-"][id*="' + sectionId + '"]');
          if (existing) {
            try {
              existing.innerHTML = sectionWrap.innerHTML;
            } catch (e) {
              try {
                existing.parentNode.replaceChild(sectionWrap.cloneNode(true), existing);
              } catch (e2) {}
            }
          }
        })
        .catch(function () {});
    }

    var drawerPromise = fetch((base || path) + sep + 'section_id=cart-drawer')
      .then(function (r) { return r.text(); })
      .then(function (htmlText) {
        if (!htmlText || htmlText.length < 10) return;
        var doc = new DOMParser().parseFromString(htmlText, 'text/html');
        var selectors = ['cart-drawer-items', '.cart-drawer__footer', '.drawer__contents', '.cart-drawer__form'];
        for (var i = 0; i < selectors.length; i++) {
          var source = doc.querySelector(selectors[i]);
          var target = document.querySelector(selectors[i]);
          if (source && target) {
            try {
              target.replaceWith(source.cloneNode(true));
            } catch (e) {}
          }
        }
      })
      .catch(function () {});

    var bubblePromise = replaceSectionHtml('cart-icon-bubble');
    return Promise.all([drawerPromise, bubblePromise]);
  }

  /** Fetch section HTML via Section Rendering API (GET) and replace in DOM. */
  function fetchAndRenderSections() {
    var ids = getCartSectionIds().slice(0, 5);
    var q = ids.join(',');
    var path = (window.location.pathname || '/').split('?')[0];
    var sep = path.indexOf('?') >= 0 ? '&' : '?';
    var url = path + sep + 'sections=' + encodeURIComponent(q);
    fetch(url, { headers: { Accept: 'application/json' } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data && typeof data === 'object' && renderSections(data) > 0) return;
        var root = (typeof window.Shopify !== 'undefined' && window.Shopify.routes && window.Shopify.routes.root) ? window.Shopify.routes.root.replace(/\/$/, '') : '';
        var rootUrl = (root || '/') + (root ? '?' : '?') + 'sections=' + encodeURIComponent(q);
        if (rootUrl === url) return;
        fetch(rootUrl, { headers: { Accept: 'application/json' } })
          .then(function (r2) { return r2.json(); })
          .then(function (data2) {
            if (data2 && typeof data2 === 'object') renderSections(data2);
          })
          .catch(function () {});
      })
      .catch(function () {});
  }

  function refreshCartUI(addResponse) {
    var didReplace = addResponse && addResponse.sections ? renderSections(addResponse.sections) : 0;
    if (didReplace > 0) console.log('[TryOn] Replaced', didReplace, 'section(s) from add response');
    if (!didReplace) fetchAndRenderSections();
    function updateCountAndOpenDrawer(cart) {
      var countStr = String(cart.item_count);
      ['.cart-count-bubble span', '[data-cart-count]', '.cart-count', '#cart-icon-bubble span[aria-hidden]', '.cart-count-bubble', 'span.cart-count', '.cart-drawer__count', '[id*="cart"] span'].forEach(function (sel) {
        try {
          document.querySelectorAll(sel).forEach(function (el) {
            if (el.tagName === 'SPAN' || el.tagName === 'SMALL') el.textContent = countStr;
            else if (el.classList && el.classList.contains('cart-count-bubble')) el.textContent = countStr;
            else if (el.getAttribute && el.getAttribute('data-cart-count') !== null) el.textContent = countStr;
          });
        } catch (err) {}
      });
      if (typeof window.Shopify !== 'undefined' && typeof window.Shopify.onCartUpdate === 'function') window.Shopify.onCartUpdate(cart);
      document.dispatchEvent(new CustomEvent('cart:refresh', { detail: cart }));
      window.dispatchEvent(new CustomEvent('tryon:cart_added', { detail: cart }));
      var t = document.querySelector('[data-cart-drawer-toggle], cart-drawer summary, .js-drawer-open-right, [aria-controls="cart-drawer"]');
      if (t) t.click();
    }
    var cartJsUrl = (typeof window.Shopify !== 'undefined' && window.Shopify.routes && window.Shopify.routes.root) ? window.Shopify.routes.root + 'cart.js' : '/cart.js';
    var cartPromise = fetch(cartJsUrl).then(function (r) { return r.json(); });
    refreshCartDrawerDawn()
      .then(function () { return new Promise(function (r) { setTimeout(r, 250); }); })
      .then(function () { return cartPromise; })
      .then(updateCountAndOpenDrawer)
      .catch(function () { cartPromise.then(updateCountAndOpenDrawer).catch(function () {}); });
  }
})();
