/**
 * TryOn Session in Cart — Shopify theme app extension asset
 * Listens for TRYON_ADD_TO_CART from the widget; adds item to cart with tryon_session_id when present.
 */
(function () {
  const ATTR_KEY = 'tryon_session_id';

  window.addEventListener('message', function (e) {
    if (e.data?.type !== 'TRYON_ADD_TO_CART' || !e.data?.payload) return;
    const { productId, variantId, size, shop, session_id } = e.data.payload;

    if (!variantId) {
      console.warn('[TryOn] Add to cart skipped: missing variantId');
      return;
    }

    var variantIdNum = parseInt(variantId, 10);
    if (Number.isNaN(variantIdNum)) {
      console.warn('[TryOn] Add to cart skipped: invalid variantId', variantId);
      return;
    }

    var properties = { _tryon_size: size || '' };
    if (session_id) properties[ATTR_KEY] = session_id;

    fetch('/cart/add.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: [{
          id: variantIdNum,
          quantity: 1,
          properties: properties,
        }],
      }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.status && data.status !== 422) {
          window.dispatchEvent(new CustomEvent('tryon:cart_added', { detail: data }));
          if (typeof window.tryonOnCartAdded === 'function') {
            window.tryonOnCartAdded(data);
          }
        } else {
          console.warn('[TryOn] Cart add response:', data);
        }
      })
      .catch(function (err) {
        console.warn('[TryOn] Cart add failed:', err);
      });
  });
})();
