/**
 * TryOn cart embed — listens for TRYON_ADD_TO_CART from widget iframe,
 * adds item to cart with tryon_session_id for order attribution.
 */
(function () {
  function onMessage(event) {
    if (!event.data || event.data.type !== 'TRYON_ADD_TO_CART') return;
    var p = event.data.payload || {};
    var variantId = p.variantId || p.variant_id;
    var sessionId = p.session_id;
    var size = p.size || '';
    if (!variantId) return;
    var props = {};
    if (sessionId) props.tryon_session_id = String(sessionId);
    if (size) props._tryon_size = String(size);
    fetch('/cart/add.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: [{ id: variantId, quantity: 1, properties: props }]
      })
    }).then(function (r) { return r.json(); })
      .catch(function () {});
  }
  window.addEventListener('message', onMessage);
})();
