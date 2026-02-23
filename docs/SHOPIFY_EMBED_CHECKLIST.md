# Shopify embed — what to check and common errors

Use this when testing the TryOn app on a Shopify store (dev or live).

---

## Before testing

- [ ] **App installed** on the store and **Try On** block added to a product section.
- [ ] **TryOn cart** app embed is **enabled** (Theme → Customize → Theme settings → App embeds → TryOn cart → On).
- [ ] **Frontend deployed** with the latest changes (iframe headers, cart script). Redeploy Vercel after changing `next.config.js` or the widget.

---

## 1. Widget loads in the iframe

**What to do:** On a product page, click **Try On**. The modal should open and the iframe should show the TryOn viewer.

**If you see:** “Refused to display in a frame” or “X-Frame-Options” in the console:

- The widget page must allow being embedded. The frontend sets `Content-Security-Policy: frame-ancestors *` for `/test-viewer.html` in `next.config.js`.
- **Fix:** Redeploy the frontend (Vercel) so the new headers are live. If the host adds its own `X-Frame-Options`, you may need to override it (e.g. in `vercel.json` or your host’s config).

**If the iframe is blank or “Loading…” forever:**

- Open DevTools → **Console** (and optionally **Network**) on the **store page**.
- Check for errors in the **iframe’s** context: DevTools → top dropdown that says the store URL → switch to the iframe (e.g. `tryonline.vercel.app`). Inspect console/network there.
- Typical causes: JS error in the widget, or API (session/create) failing. Session is created when the overlay opens; if the backend is down or CORS blocks the request, the widget can still open but some features may fail.

---

## 2. Session and API (no CORS from store)

The widget runs inside an iframe whose origin is **tryonline.vercel.app**. Its `fetch('/api/...')` calls go to tryonline.vercel.app (same origin for the iframe), then Next.js rewrites to the backend. So the **store page** never talks to your API directly; CORS is not involved for the iframe’s API calls.

**If session creation fails** (e.g. network error, 5xx):

- The widget can still open, but **Add to cart** might not send a `session_id`. The cart script is written to **still add the item** without `session_id` (attribution is then missing for that add). Check the backend and Vercel logs if you need session creation to succeed.

---

## 3. Add to cart from the widget

**What to do:** In the widget, choose a size and click **ADD TO CART**. The modal closes and the store’s cart should include the item.

**If nothing happens (no item in cart):**

- **TryOn cart** embed must be enabled (see above). Without it, the store page never receives `TRYON_ADD_TO_CART`.
- In the **store page** console, look for:
  - `[TryOn] Add to cart skipped: missing variantId` → the widget URL or config didn’t pass a valid `variant_id` (check the Try On block and Liquid: `product.selected_or_first_available_variant.id`).
  - `[TryOn] Add to cart skipped: invalid variantId` → `variant_id` isn’t a number (e.g. wrong param from theme).
  - `[TryOn] Cart add response: {...}` with a non-2xx or 422 → Shopify’s `/cart/add.js` rejected the request (e.g. invalid variant id, sold out, or store rules). Check the response body.
- In the **iframe** console, confirm there are no JS errors when you click Add to cart (e.g. `postMessage` or config).

**If the item is added but without TryOn attribution:**

- That’s expected when `session_id` is missing (e.g. session creation failed). The cart script still adds the line item; only the `tryon_session_id` property is omitted.

---

## 4. Variant ID

The **Try On** block passes `variant_id` from Liquid: `product.selected_or_first_available_variant.id`. That must be the **numeric** Shopify variant ID (e.g. `40123456789`). The widget sends it in the `TRYON_ADD_TO_CART` payload; the cart script uses it as `id` in `/cart/add.js`. If the theme or block passes something else (e.g. option value or SKU), cart add can fail or add the wrong variant.

---

## 5. Quick checklist

| Check | Where | Pass? |
|-------|--------|------|
| Try On opens modal + iframe | Store product page | ☐ |
| No “Refused to display in a frame” | Store or iframe console | ☐ |
| Widget loads (3D / size selector visible) | Iframe | ☐ |
| Add to cart adds item to store cart | Store cart | ☐ |
| Console: no “[TryOn] Add to cart skipped” (or invalid variantId) | Store console | ☐ |
| Optional: line item has `tryon_session_id` property | Cart or checkout attributes | ☐ |

---

## 6. After changing code

- **Frontend (Next.js, test-viewer.html, headers):** Redeploy on Vercel. Clear cache or hard-refresh the store page when testing.
- **Extension (Try On block, cart script):** Run `npm run deploy` (or `shopify app deploy`) from `shopify_app/`. In the store theme editor, confirm the app block/embed are still present and save if needed.

---

*Last updated: Feb 2026*
