# Status Report — 2026-04-10

## Summary

Virtual try-on for the Ramin zip-up (stacked avatar + garment in the Shopify iframe) went from invisible / broken scaling to a **stable, good-looking fit** across S / M / L after systematic fixes (unit mismatch, per-root scale, alignment, depth, clearance). Today was frustrating mid-flight but **ended in a strong visual result**.

---

## Wins today (Try On viewer + theme)

- **Garment visibility:** Root cause was mixed units (avatar ~mm, garment ~m) and uniform parent scaling; fixed with **per-root scale** and a shared garment ref height.
- **Logo / alpha:** Removed forcing materials opaque so RAMIN artwork no longer shows a white box (glTF alpha preserved).
- **Alignment:** **Y-only foot match** + shared **X** origin (no bbox XZ center slide) + small **`TRYON_GARMENT_Z_PUSHBACK`** so the shell matches the rig without drifting “forward.”
- **Skin bleed / back view:** Combination of **garment clearance scale**, **polygon offset**, and **selective avatar `depthWrite`** (torso off, head kept) so the face stays visible and cloth wins where it should.
- **Code** lives mainly in `frontend/public/test-viewer.html`; theme iframe cache buster in `shopify_app/extensions/tryon-widget/blocks/tryon-button.liquid` (increment `v=` on deploy).

---

## What must happen next (priority order)

### 1. Fix **Add to cart** from the Try On modal

- **Today:** The iframe posts `TRYON_ADD_TO_CART` to the parent; **`tryon-cart.js`** performs `POST /cart/add.js` with size → variant resolution via `__tryonSizeVariantMap`.
- **Gap:** Cart script historically loaded only from the optional **“TryOn cart” app embed**. We added `"javascript": "tryon-cart.js"` to the **Try On block schema** and a **single-bind guard** (`__tryonCartMessageBound`) so duplicate listeners do not double-add lines — **this still needs verification on a live theme deploy** (some themes may not inject block `javascript`; fallback: keep app embed enabled or inline a minimal handler in the block).
- **Acceptance:** Clicking **ADD TO CART** in the viewer reliably adds the correct variant, updates drawer / count, and does not depend on a hidden setup step.

### 2. **Checkout / paid** webhook → **Supabase** (investor-ready ROI)

- **Why:** Brands and investors need proof that try-on **drives revenue**, not only sessions. That requires attributing **completed purchases** (and ideally revenue) to try-on / fit-passport context stored in our DB.
- **What to build (outline):**
  - Subscribe to Shopify **`orders/paid`** (and/or `checkouts/completed` if needed for attribution shape) via **Shopify webhooks** on the app or a secure backend endpoint.
  - **Verify HMAC** (already a pattern elsewhere in the backend for compliance webhooks).
  - Parse line items; match **line item properties** (e.g. `tryon_session_id` / `_tryon_size` already set in `tryon-cart.js`) to **`tryon_sessions`** or related tables.
  - **Upsert** into Supabase: e.g. purchase event, `order_id`, `shop`, `revenue`, `currency`, `tryon_session_id`, timestamps — so dashboards can show **conversion from try-on → paid order** and **ROI narratives for brands**.
- **Acceptance:** A test checkout on a pilot store creates a row (or event) in Supabase that ties the order to try-on data; analytics / brand dashboard can aggregate it.

---

## Continue tomorrow evening

1. **Ship + test** latest `test-viewer.html` + theme extension; confirm **Add to cart** end-to-end; if the block’s `javascript` field is ignored by the theme, document “enable TryOn cart embed” or implement inline fallback.
2. **Design + implement** the **orders/paid** (or equivalent) **webhook → Supabase** pipeline for purchase attribution and ROI reporting.

---

## Files / branches (reference)

| Area | Location |
|------|----------|
| Viewer | `frontend/public/test-viewer.html` |
| PDP block + iframe URL | `shopify_app/extensions/tryon-widget/blocks/tryon-button.liquid` |
| Cart listener | `shopify_app/extensions/tryon-widget/assets/tryon-cart.js` |
| Optional embed | `shopify_app/extensions/tryon-widget/blocks/tryon-cart-embed.liquid` |
| Branch | `feature/analytics` |

---

## Note for past self

You pushed through a long debugging arc (units, skinning vs static mesh, depth, alignment). The product **does** look way better now — next is **closing the loop** on cart + **proving money** with webhooks and Supabase.
