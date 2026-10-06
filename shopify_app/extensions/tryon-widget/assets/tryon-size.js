/*
  TryOn: the "Find my size" card opener, shared by the Find my size block and the Try On block
  (which shows it on products without a 3D garment). Mounts on a [data-tryon-size-root] element
  holding a [data-tryon-size-config] JSON, a [data-tryon-size-open] button and a
  [data-tryon-size-label]. Plain JavaScript, no Liquid: the blocks pass everything in the JSON.
*/
(function () {
  if (window.TryonSizeCard) return;

  function mount(root) {
    if (!root || root.__tryonSizeBound) return;
    root.__tryonSizeBound = true;
    var cfg;
    try { cfg = JSON.parse(root.querySelector('[data-tryon-size-config]').textContent); } catch (e) { return; }
    var btn = root.querySelector('[data-tryon-size-open]');
    var labelEl = root.querySelector('[data-tryon-size-label]');
    if (!btn || !cfg || cfg.sizePos < 0) return;

    var KNOWN_KEY = 'tryon_size_known';
    var VERSION = '2';
    var iframe = null;
    var ready = false;
    var isOpen = false;
    var wantOpen = false;
    var fallbackTimer = null;
    var closeBtn = null;

    function selectedVariantId() {
      var fromUrl = parseInt(new URLSearchParams(window.location.search).get('variant'), 10);
      if (fromUrl) return fromUrl;
      var input = document.querySelector('form[action*="/cart/add"] [name="id"]');
      var fromForm = input ? parseInt(input.value, 10) : NaN;
      return fromForm || cfg.variantId;
    }

    // The sizes of the colour the shopper is looking at, in the store's order, with stock.
    function sizesNow() {
      var selId = selectedVariantId();
      var base = null;
      for (var i = 0; i < cfg.variants.length; i++) { if (cfg.variants[i].id === selId) { base = cfg.variants[i]; break; } }
      base = base || cfg.variants[0];
      var order = [];
      var byKey = {};
      cfg.variants.forEach(function (v) {
        for (var j = 0; j < v.options.length; j++) {
          if (j !== cfg.sizePos && base && v.options[j] !== base.options[j]) return;
        }
        var label = String(v.options[cfg.sizePos] || '').trim();
        var key = label.toLowerCase();
        if (!key) return;
        if (!byKey[key]) { byKey[key] = { label: label, available: false, variantId: v.id }; order.push(key); }
        if (v.available) { byKey[key].available = true; byKey[key].variantId = v.id; }
      });
      return order.map(function (k) { return byKey[k]; });
    }

    function hasTryonBlock() { return !!document.querySelector('[data-tryon-open]'); }

    function post(type, payload) {
      if (!iframe || !iframe.contentWindow) return;
      try { iframe.contentWindow.postMessage(payload ? { type: type, payload: payload } : { type: type }, '*'); } catch (e) {}
    }
    // The picture of what the shopper is looking at: the selected colour's own image when
    // the variant has one, else the product's main image.
    function imageNow() {
      var selId = selectedVariantId();
      for (var i = 0; i < cfg.variants.length; i++) {
        var v = cfg.variants[i];
        if (v.id === selId && v.featured_image && v.featured_image.src) return v.featured_image.src;
      }
      return cfg.productImage || '';
    }

    function sendProduct() {
      post('TRYON_SIZE_PRODUCT', {
        sizes: sizesNow().map(function (s) { return { label: s.label, available: s.available }; }),
        image: imageNow(),
        hasTryon: hasTryonBlock()
      });
    }

    // The card wears the store's look: text and page colours, the add-to-cart button's
    // colours and corner radius, and the page font (when the shopper's device has it).
    function storeLook() {
      var out = {};
      try {
        var body = getComputedStyle(document.body);
        out.ink = body.color;
        out.font = body.fontFamily;
        var bg = body.backgroundColor;
        if (bg && bg !== 'transparent' && !/rgba\([^)]*,\s*0\)$/.test(bg)) out.paper = bg;
        var atc = document.querySelector('form[action*="/cart/add"] [type="submit"], form[action*="/cart/add"] button[name="add"]');
        if (atc) {
          var s = getComputedStyle(atc);
          var abg = s.backgroundColor;
          if (abg && abg !== 'transparent' && !/rgba\([^)]*,\s*0\)$/.test(abg)) { out.btn_bg = abg; out.btn_fg = s.color; }
          out.radius = parseFloat(s.borderTopLeftRadius) || 0;
        }
      } catch (e) {}
      if (cfg.accentBg) out.btn_bg = cfg.accentBg;
      if (cfg.accentFg) out.btn_fg = cfg.accentFg;
      return out;
    }

    function buildSrc(silent) {
      var p = new URLSearchParams({
        shop: cfg.shop, product_id: cfg.productId, product_name: cfg.productName || '',
        product_type: cfg.productType || '', variant_id: String(selectedVariantId() || ''),
        country: cfg.country || '', brand_name: cfg.brandName || '', return_url: cfg.returnUrl || '',
        product_image: imageNow(), v: VERSION
      });
      if (cfg.look === 'store') {
        var look = storeLook();
        p.set('look', 'store');
        Object.keys(look).forEach(function (k) { if (look[k] !== undefined && look[k] !== '') p.set(k, String(look[k])); });
      }
      if (silent) p.set('silent', '1');
      return cfg.widgetBase + '/size-finder.html?' + p.toString();
    }

    function ensureFrame(silent) {
      if (iframe) return;
      iframe = document.createElement('iframe');
      iframe.title = 'Find your size';
      iframe.setAttribute('allowtransparency', 'true');
      iframe.style.cssText = 'display:none;position:fixed;inset:0;width:100%;height:100%;z-index:999999;border:none;background:transparent;';
      // On <body>, so position:fixed escapes any transformed ancestor in the theme.
      document.body.appendChild(iframe);
      iframe.src = buildSrc(silent);
    }

    function show() {
      isOpen = true;
      iframe.style.display = 'block';
      document.body.style.overflow = 'hidden';
      sendProduct();
      post('TRYON_SIZE_OPEN');
      try { iframe.focus({ preventScroll: true }); } catch (e) {}
    }

    function close(fromCard) {
      if (!isOpen && !wantOpen) return;
      isOpen = false;
      wantOpen = false;
      clearTimeout(fallbackTimer);
      if (iframe) iframe.style.display = 'none';
      if (closeBtn) closeBtn.style.display = 'none';
      document.body.style.overflow = '';
      if (!fromCard) post('TRYON_SIZE_HIDE');
      try { btn.focus({ preventScroll: true }); } catch (e) {}
    }

    // If the card has not answered after 4s (slow network, blocked), offer a way out.
    function armFallback() {
      clearTimeout(fallbackTimer);
      fallbackTimer = setTimeout(function () {
        if (!wantOpen || ready) return;
        if (!closeBtn) {
          closeBtn = document.createElement('button');
          closeBtn.type = 'button';
          closeBtn.setAttribute('aria-label', 'Close');
          closeBtn.textContent = '✕';
          closeBtn.style.cssText = 'position:fixed;top:12px;right:12px;z-index:1000000;width:40px;height:40px;border-radius:50%;border:none;background:rgba(255,255,255,0.92);color:#1a1a1a;font-size:18px;cursor:pointer;';
          closeBtn.addEventListener('click', function () { close(false); });
          document.body.appendChild(closeBtn);
        }
        closeBtn.style.display = 'block';
        iframe.style.display = 'block';
      }, 4000);
    }

    btn.addEventListener('click', function () {
      if (isOpen) return;
      ensureFrame(false);
      if (ready) show();
      else { wantOpen = true; armFallback(); }
    });

    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && (isOpen || wantOpen)) close(false); });

    function setResult(size) {
      if (!size || !labelEl) return;
      var text = (cfg.resultLabel || 'Your size: [size]').replace('[size]', String(size).toUpperCase());
      labelEl.textContent = text;
      btn.setAttribute('data-has-size', '');
      try { localStorage.setItem(KNOWN_KEY, '1'); } catch (e) {}
    }

    function cartRoot() { return (window.Shopify && window.Shopify.routes && window.Shopify.routes.root) || '/'; }

    function addToCart(payload) {
      var want = String(payload.size || '').toLowerCase().trim();
      var match = null;
      sizesNow().forEach(function (s) { if (s.label.toLowerCase() === want) match = s; });
      if (!match || !match.available) { console.warn('[TryOn size] No in-stock variant for size', want); return; }
      var props = { _tryon_size: want, _tryon_source: 'size_finder' };
      if (payload.session_id) props._tryon_session_id = payload.session_id;
      var body = { items: [{ id: Number(match.variantId), quantity: 1, properties: props }] };
      var themeCart = document.querySelector('cart-drawer') || document.querySelector('cart-notification');
      if (themeCart && typeof themeCart.getSectionsToRender === 'function') {
        try {
          body.sections = themeCart.getSectionsToRender().map(function (s) { return s.id; }).slice(0, 5).join(',');
          body.sections_url = window.location.pathname.split('?')[0];
        } catch (e) {}
      }
      fetch(cartRoot() + 'cart/add.js', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin', body: JSON.stringify(body)
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (!data.items) { console.warn('[TryOn size] Cart rejected:', data.message || data.description || ''); return; }
          if (themeRefreshesItself()) return;
          if (themeCart && typeof themeCart.renderContents === 'function' && data.sections) {
            try { themeCart.renderContents(data); document.dispatchEvent(new CustomEvent('cart:refresh', { detail: data })); return; } catch (e) {}
          }
          return fetch(cartRoot() + 'cart.js').then(function (r) { return r.json(); }).then(function (cart) {
            var c = String(cart.item_count);
            ['.cart-count-bubble span', '[data-cart-count]', '.cart-count', '#cart-icon-bubble span[aria-hidden]'].forEach(function (sel) {
              try { document.querySelectorAll(sel).forEach(function (el) { el.textContent = c; }); } catch (e) {}
            });
            document.dispatchEvent(new CustomEvent('cart:refresh', { detail: cart }));
            var toggle = document.querySelector('[data-cart-drawer-toggle], cart-drawer summary, [aria-controls="cart-drawer"], a[href="/cart"]');
            if (toggle) { try { toggle.click(); } catch (e) {} }
          });
        })
        .catch(function (err) { console.error('[TryOn size] Cart add failed:', err); });
    }

    window.addEventListener('message', function (e) {
      if (!iframe || e.source !== iframe.contentWindow || !e.data) return;
      var d = e.data;
      if (d.type === 'TRYON_SIZE_READY') {
        ready = true;
        clearTimeout(fallbackTimer);
        if (closeBtn) closeBtn.style.display = 'none';
        sendProduct();
        // isOpen: the card reloaded itself while showing (sign-in fallback); open it again.
        if (wantOpen || isOpen) { wantOpen = false; show(); }
      }
      if (d.type === 'TRYON_SIZE_RESULT' && d.payload) setResult(d.payload.size);
      // Signed in: load the card quietly on later product pages, so a measurement still
      // being made is picked up and the size appears by itself.
      if (d.type === 'TRYON_SIZE_ACCOUNT') { try { localStorage.setItem(KNOWN_KEY, '1'); } catch (e2) {} }
      if (d.type === 'TRYON_SIZE_CLOSE') close(true);
      if (d.type === 'TRYON_SIZE_ADD_TO_CART' && d.payload) addToCart(d.payload);
      if (d.type === 'TRYON_SIZE_OPEN_TRYON') {
        close(true);
        var tryon = document.querySelector('[data-tryon-open]');
        if (tryon) tryon.click();
      }
    });

    // Colour or variant changed: the sizes and stock on offer may have too.
    document.addEventListener('change', function (e) {
      if (ready && e.target && e.target.closest && e.target.closest('form[action*="/cart/add"], variant-selects, variant-radios')) {
        setTimeout(sendProduct, 50);
      }
    });

    // A shopper who has used the size finder before gets their size for this product
    // straight away: load the card hidden once the page is idle and let it answer.
    var known = false;
    try { known = localStorage.getItem(KNOWN_KEY) === '1'; } catch (e) {}
    if (known) {
      var preload = function () { ensureFrame(true); };
      if ('requestIdleCallback' in window) window.requestIdleCallback(preload, { timeout: 3000 });
      else setTimeout(preload, 1500);
    }
  }

  // Themes that re-read the cart themselves when told (their own count, drawer and opening). Baseline (Pixel Union, La Fam) listens for this event. True when such a theme took over.
  function themeRefreshesItself() {
    var t = window.Shopify && window.Shopify.theme;
    if ((t && t.schema_name === 'Baseline') || (document.querySelector('[data-cart-drawer]') && window.Spruce)) {
      document.body.dispatchEvent(new CustomEvent('baseline:modalcart:afteradditem'));
      return true;
    }
    return false;
  }

  window.TryonSizeCard = { mount: mount };
  function mountAll() { document.querySelectorAll('[data-tryon-size-root]').forEach(mount); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mountAll);
  else mountAll();
})();
