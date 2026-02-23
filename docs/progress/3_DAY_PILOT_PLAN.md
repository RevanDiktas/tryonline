# 3-Day Pilot Plan — Finish by Feb 26, 2026

**Goal:** Get the pilot live in 3 days (CORS verified → widget test → Shopify app on a dev store with webhook).

**Reference:** `docs/progress/2026-02-19_STATUS_REPORT.md`

---

## Day 1 — CORS + Widget test (today)

### 1.1 CORS (≈15 min)

- [ ] From **https://tryonline.vercel.app** sign in or hit any API (e.g. onboarding). Open DevTools → Console.
- [ ] If you see **CORS errors**:
  - Railway → **tryonline** / **heroic-celebration** → **Variables**
  - Set **CORS_ORIGINS** = `http://localhost:3000,https://tryonline.vercel.app` (add other origins if you use preview URLs).
  - **Redeploy** the backend (Railway will redeploy when you save variables, or trigger manually).
- [ ] Retest from the Vercel app; confirm no CORS errors.

### 1.2 Widget URL + CORS test (≈15 min)

- [ ] **Full experience (avatar + measurements):** Use a URL that includes `user_id` (and optionally `preferred_fit`). Example (replace with your user ID from Fit Passport / Supabase):  
  `https://tryonline.vercel.app/test-viewer.html?user_id=YOUR_USER_ID&preferred_fit=regular&product_id=demo-npc-tshirt&shop=demo.myshopify.com&variant_id=1&open=1`  
  Without `user_id`, the viewer shows the garment only and measurements stay "—".
- [ ] **CORS-only (no user):**  
  `https://tryonline.vercel.app/test-viewer.html?shop=demo.myshopify.com&product_id=demo-npc-tshirt&variant_id=1&open=1`
- [ ] Confirm: page loads; overlay opens; no CORS errors; with user_id, avatar and measurements load; API calls work.

**End of Day 1:** Frontend ↔ backend and widget URL are verified.

---

## Day 2 — Shopify Partner app + extension

### 2.1 Create Shopify Partner app (≈30 min)

- [ ] Log in to [Shopify Partners](https://partners.shopify.com).
- [ ] **Apps** → **Create app** → **Create app manually** (custom/private).
- [ ] Name it (e.g. "TryOn").
- [ ] Note: you’ll get an app that can have extensions; you’re not submitting to the App Store yet.

### 2.2 Connect repo and deploy extension (≈30 min)

- [ ] In the Partner dashboard, **configure** the app (or use Shopify CLI from this repo).
- [ ] From repo: `shopify_app/` already has:
  - **Theme app extension** `tryon-widget` with:
    - **Block:** `tryon-button.liquid` — "Try On" button → opens widget in modal iframe (widget URL already points to `https://tryonline.vercel.app/test-viewer.html?...`).
    - **App embed:** `tryon-cart-embed.liquid` — loads `tryon-cart.js` (listens for `TRYON_ADD_TO_CART`, adds to cart with `tryon_session_id`).
- [ ] Deploy extension:
  - `cd shopify_app && npm run deploy` (or use `deploy.sh` / Shopify CLI: `shopify app deploy`).
- [ ] If the app was created in Partners without this repo, add the extension by creating a theme app extension in the app and copying the contents of `extensions/tryon-widget/` (blocks + assets).

### 2.3 Install on dev store and add block (≈20 min)

- [ ] Create or pick a **development store** in Partners.
- [ ] **Install** the app on that store (Partners → your app → Test on development store / Install).
- [ ] In the store: **Online Store** → **Themes** → **Customize** (current theme).
- [ ] On a **product** template, add the **Try On** app block (from the app’s section).
- [ ] In **Theme settings** (or App embeds): enable **TryOn cart** embed so the cart listener runs on every page.
- [ ] Save. Open a product page; confirm the "Try On" button appears.

**End of Day 2:** App is on dev store; Try On button and cart embed are live.

---

## Day 3 — End-to-end test + webhook

### 3.1 Full flow test (≈30 min)

- [ ] On the dev store product page, click **Try On**.
- [ ] Widget opens in modal (iframe to tryonline.vercel.app).
- [ ] In the widget: do a try-on (or minimal flow) and trigger **Add to cart** (widget should post `TRYON_ADD_TO_CART` with `session_id`, `variantId`, etc.).
- [ ] Confirm item is in the store cart (and ideally that line item has `tryon_session_id` in properties).
- [ ] **Checkout** and complete a test order (use Shopify’s bogus gateway if needed).

### 3.2 Orders/paid webhook (≈20 min)

- [ ] In **Shopify Admin** (dev store): **Settings** → **Notifications** → **Webhooks** (or via Partners app configuration).
- [ ] Add webhook:
  - **Event:** Order payment paid (or equivalent: `orders/paid`).
  - **URL:** `https://heroic-celebration-production-9f72.up.railway.app/api/webhooks/shopify/orders-paid`
  - **Format:** JSON.
- [ ] Shopify will show a **signing secret** (or you get it when creating the webhook). Copy it.
- [ ] Railway → **heroic-celebration** → **Variables** → add **SHOPIFY_WEBHOOK_SECRET** = that secret.
- [ ] Redeploy backend so it picks up the new variable.
- [ ] Place another test order; confirm webhook is called (check Railway logs or your backend logs). Backend should write a `purchase` event (or equivalent) using `tryon_session_id` from the order.

### 3.3 Quick checklist

- [ ] Try On → iframe → add to cart → checkout works.
- [ ] No CORS errors when using the widget from the store.
- [ ] orders/paid webhook hits the backend; SHOPIFY_WEBHOOK_SECRET set and verification passes.
- [ ] Optional: run `backend/scripts/test_webhook_purchase.py` if you have it, to simulate an order payload.

**End of Day 3:** Pilot is live: store → Try On → cart → checkout → webhook → attribution.

---

## Summary checklist (pilot = done)

| # | Task | Day |
|---|------|-----|
| 1 | CORS: set CORS_ORIGINS in Railway, redeploy, verify from Vercel | 1 |
| 2 | Widget test: open test-viewer URL, no CORS, API works | 1 |
| 3 | Create Shopify Partner app (custom) | 2 |
| 4 | Deploy theme extension (Try On block + cart embed) | 2 |
| 5 | Install app on dev store; add block + enable cart embed | 2 |
| 6 | E2E: Try On → add to cart → checkout | 3 |
| 7 | Configure orders/paid webhook URL + SHOPIFY_WEBHOOK_SECRET | 3 |
| 8 | Verify webhook receives order and attribution works | 3 |

---

## Deferred (after pilot)

- **Domain:** Add custom domain in Vercel; add to CORS; update widget URL in extension (see `docs/LAUNCH_WHILE_DOMAIN_PENDING.md`).
- **App Store listing:** Icon, listing, compliance, submit for review (see `docs/SHOPIFY_APP_STORE_WIDGET_PLAN.md` or status report §5).

---

## Key URLs

| What | URL |
|------|-----|
| Frontend | https://tryonline.vercel.app |
| Backend | https://heroic-celebration-production-9f72.up.railway.app |
| Widget test (full) | https://tryonline.vercel.app/test-viewer.html?user_id=YOUR_USER_ID&preferred_fit=regular&product_id=demo-npc-tshirt&shop=demo.myshopify.com&variant_id=1&open=1 |
| Widget test (CORS only) | https://tryonline.vercel.app/test-viewer.html?shop=demo.myshopify.com&product_id=demo-npc-tshirt&variant_id=1&open=1 |
| orders/paid webhook | POST https://heroic-celebration-production-9f72.up.railway.app/api/webhooks/shopify/orders-paid |
| Shopify Partners | https://partners.shopify.com |

---

*Created from Feb 19 status report. Last updated: Feb 23, 2026.*
