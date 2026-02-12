/**
 * TryOn Session in Cart — Shopify theme snippet
 * =============================================
 * Add this script to your Shopify theme (e.g. theme.liquid or a section)
 * so the session_id from the TryOn widget is stored in cart attributes.
 *
 * When the widget fires TRYON_ADD_TO_CART, this listener adds the item
 * to cart WITH the session_id as a line item property. That flows to
 * checkout and becomes a note_attribute on the order, which our webhook
 * reads for attribution.
 *
 * Usage: Include this file or paste the code into your theme.
 */
(function () {
  const ATTR_KEY = 'tryon_session_id';

  window.addEventListener('message', function (e) {
    if (e.data?.type !== 'TRYON_ADD_TO_CART' || !e.data?.payload) return;
    const { productId, variantId, size, shop, session_id } = e.data.payload;
    if (!variantId || !session_id) return;

    fetch('/cart/add.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: [{
          id: parseInt(variantId, 10),
          quantity: 1,
          properties: {
            [ATTR_KEY]: session_id,
            _tryon_size: size || '',
          },
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
        }
      })
      .catch(function (err) {
        console.warn('[TryOn] Cart add failed:', err);
      });
  });
})();
