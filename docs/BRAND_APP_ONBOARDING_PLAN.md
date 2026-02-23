# Brand app onboarding — Full plan (robust)

**Goal:** A Shopify app that **is** the brand onboarding. Brands install the app → complete onboarding in the app → get the Try On widget on their store. The widget is already linked to our backend and to **their garments** (CLO-made by you at first; later automated). Shoppers with a Fit Passport can go to the brand’s site, log in to TryOn in the widget, and try on that brand’s clothing. We use Shopify for **marketing and distribution** so more brands discover and onboard.

---

## 1. Vision and flow

### 1.1 End-to-end flow (target)

```
Brand side (Shopify)
  → Brand finds Tryon in App Store (or install link)
  → Installs app
  → Opens app in Shopify admin → sees onboarding (our embedded app)
  → Onboarding: confirm store, (optional) create/link Tryon account, "Add Try On button" (deep link), garment setup
  → Widget appears on their product pages (theme block + cart embed)
  → Garments for their products live in our DB (you make in CLO at first; later automated)
  → Brand dashboard on our website (tryonline.vercel.app/brand) shows their analytics

Shopper side (already working)
  → Has Fit Passport + avatar (our site)
  → Visits brand’s store → clicks Try On on a product
  → Logs in to TryOn in widget (or already logged in)
  → Widget calls our backend with shop + product_id
  → Backend returns garment (model URLs, size chart) from garments table (shopify_product_id)
  → Shopper tries on, gets size recommendation, adds to cart
  → Events and orders attributed to shop/brand; brand sees analytics on /brand
```

### 1.2 Why the app (not only a snippet)

- **App = onboarding.** Brands get one place to install, set up, and get the button. We can show steps, deep link to theme editor, and later add garment setup and dashboard link.
- **Shopify = marketing.** Listing in the App Store (and install link) gets more brands to try us. A snippet alone doesn’t give that discovery or guided setup.
- **Snippet as fallback.** A single line of code (script + div) could be offered for stores that can’t or won’t use the app (e.g. theme limits). For the first test run and beyond, **the app is the primary path**; build it when the first test run is active. Use a snippet only if we need a quick test on a store without the app.

### 1.3 Pacing: slow start → later automate

- **Now / first test run:** Onboarding is deliberately slow. You make clothing in CLO and link garments to the brand’s Shopify product IDs in our DB. The app’s job is to onboard the brand (store, widget, account) and set expectations (“We’ll set up your products for try-on”).
- **Later:** Garment flow can become self-serve or automated (e.g. brand connects store → we sync products → they or we add 3D assets; or we generate from photos). The app and backend are designed so that once garments exist for a `shopify_product_id`, the widget works without change.

---

## 2. What we already have

### 2.1 Shopper flow (working)

| Piece | Status | Notes |
|-------|--------|--------|
| Signup / Fit Passport | Done | user_type shopper/brand; onboarding (photo, measurements). |
| Avatar pipeline | Done | RunPod, 4D-Humans; avatar stored, status in fit_passports. |
| Dashboard | Done | Shopper dashboard, “Open widget with my account” for testing. |
| Widget (try-on) | Done | test-viewer.html + embed; loads avatar + garment from API. |
| Backend: avatar, events, sessions | Done | GET /api/avatar/{user_id}, track_event, create_tryon_session. |
| Backend: product config | Done | GET /api/products/{product_id}/tryon-config → garments by shopify_product_id. |
| Size recommendation | Done | recommendSize(measurements, sizeChart, preferredFit). |
| Add to cart (storefront) | Done | TRYON_ADD_TO_CART → cart with tryon_session_id; webhook orders/paid. |

So: **for shoppers, everything works** as long as (1) they have a Fit Passport and (2) the product has a garment in our DB.

### 2.2 Brand side (what exists)

| Piece | Status | Notes |
|-------|--------|--------|
| brands table | Exists | id, name, email, shopify_domain, plan, Stripe, etc. |
| garments table | Exists | brand_id, shopify_product_id, sizes (URLs per size), size_chart. |
| Backend: brand_id from shop | Done | _resolve_brand_id(shop_domain) for analytics. |
| Backend: tryon-config | Done | Looks up garments by shopify_product_id; no brand_id in query (product_id is global). |
| Brand dashboard (/brand) | Done | Analytics (ROI, fit, trend) by shop filter. Not yet wired to “logged-in brand” or app install. |
| Shopify app (Tryon) | Done | Theme app extension: Try On block + TryOn cart embed (tryon-3). |
| Widget on store | Done | Block + embed; merchant must add block and enable embed manually. |

So: **widget and backend are ready**. Gaps: (1) no in-Shopify onboarding (embedded app), (2) no automatic “create brand on install” and no guided “add widget” (deep link), (3) no in-app garment setup flow (we rely on you adding garments in DB for now).

### 2.3 Garment ↔ widget link (already there)

- Store product page has `product_id` (Shopify product id) and `variant_id`.
- Widget is opened with `?shop=...&product_id=...&variant_id=...`.
- Widget (or embed) calls `GET /api/products/{product_id}/tryon-config`.
- Backend: `garments` table, `WHERE shopify_product_id = product_id`, returns `sizes` (model URLs) and `size_chart`.
- If no garment: 404 (or demo for demo-npc-tshirt). So **widget is already linked to backend and to garments**; we only need rows in `garments` with the right `shopify_product_id` (and optionally `brand_id`).

---

## 3. What we need (gaps)

| Need | Have | Missing |
|------|------|--------|
| App = brand onboarding | Theme extension only; App URL = main site | Embedded app UI in Shopify admin (onboarding steps). |
| Widget on product page | Block + embed exist | Merchant adds them by hand | Guided “Add Try On” (deep link) from onboarding. |
| Store → brand in DB | brands.shopify_domain, _resolve_brand_id | Create/update brand on app install (OAuth/webhook). |
| Garments for brand’s products | garments table, tryon-config by product_id | Process: you make CLO → we add garment rows; later automate. |
| First test run | Most code in place | App onboarding live; persona/avatar update; first CLO garments linked. |
| App Store listing | — | Icon, copy, compliance, submit. |
| **Shopper login in widget** | Widget works with `user_id` in URL (e.g. from dashboard) | **Login button in widget** so shoppers can log in to TryOn from the store (personalized avatar/size). Not in scope for first pilot; plan for later. |

---

## 4. Snippet vs app (recommendation)

- **Use the app** as the main way brands get the widget. Build the embedded onboarding app when the **first test run** is active (so the first real brand goes through install → onboarding → widget).
- **Snippet (one line of code):** Optional. We can provide a small script + div that injects the Try On button and opens the same widget URL. Use only for quick tests on a store that can’t install the app (e.g. theme doesn’t support app blocks) or for non-Shopify. Do **not** rely on snippet for the main onboarding story; the app is the product.

---

## 5. Robust plan (phases)

### Phase 0 — Prep for first test run

**Goal:** First real brand can try the full flow (widget + their garments + shoppers).

| Step | What | Owner |
|------|------|--------|
| 0.1 | **Persona / avatar pipeline** | Update avatar pipeline or persona so avatars are correct for the first test (you mentioned “update to persona for the avatars”). |
| 0.2 | **First brand + garments** | Pick first test brand/store. Create CLO garments for 1–2 products; insert into `garments` with correct `shopify_product_id` (and `brand_id` once brand exists). Optionally create `brands` row with `shopify_domain` = their store. |
| 0.3 | **Smoke test** | On a dev store: add Try On block + embed, use product_id that has a garment; shopper with Fit Passport tries on. Confirm widget loads garment and add-to-cart works. |

**Outcome:** Backend + widget + garments verified for one store; avatar/persona ready.

---

### Phase 1 — Embedded app = brand onboarding

**Goal:** When a brand installs Tryon and opens the app in Shopify admin, they see **our** onboarding (not the public site), then get the widget in one click.

| Step | What | Deliverable |
|------|------|-------------|
| 1.1 | **Embedded app host** | New route in existing Next.js (e.g. `/app` or `/shopify-admin`) that loads only when opened inside Shopify admin (embedded). Use Shopify App Bridge + session token to get `shop` (and optionally merchant). |
| 1.2 | **Onboarding UI** | Simple flow: (1) Welcome, “Get started with Try On”; (2) “Add Try On button to your store” → button that opens theme editor via **deep link** to add the Try On block; (3) “Enable cart” → deep link to activate TryOn cart embed; (4) “Done” + link to “We’ll set up your products” or to brand dashboard. |
| 1.3 | **Deep links** | Use Shopify app block deep link: `https://<shop>/admin/themes/current/editor?template=product&addAppBlockId=<client_id>/tryon-button&target=mainSection`. App embed: `...?context=apps&activateAppId=<client_id>/tryon-cart-embed`. Get `client_id` from Partners (Tryon app). |
| 1.4 | **App URL and redirect** | In Partners, set App URL to the embedded app URL (e.g. `https://tryonline.vercel.app/app`). Set redirect URL(s) for OAuth to the same. So opening Tryon in Apps shows onboarding, not the public Fit Passport page. |
| 1.5 | **Install → brand** | On app install, call our backend (OAuth callback or Shopify webhook). Backend creates or updates `brands` with `shopify_domain` = shop. Optional: create `users` and link to brand for “brand account” later. |

**Outcome:** Brand installs app → opens app → sees onboarding → one click adds Try On block and enables cart. Store is linked to a brand in our DB.

---

### Phase 2 — Garment setup in the flow (manual first)

**Goal:** Onboarding explains that we set up their products for try-on; we have a clear process so you can add garments (CLO) and link them to the right products.

| Step | What | Deliverable |
|------|------|-------------|
| 2.1 | **In-app copy** | In embedded app: “We’ll set up your products for virtual try-on. Share your product list or store link; we’ll add try-on to selected products.” (Or a short form: store URL already known from install.) |
| 2.2 | **Internal process** | You (or ops): receive new brand’s store/product list; create garments in CLO; insert/update `garments` with `shopify_product_id` and `brand_id`. Optional: simple internal UI or script to “add garment for product X” for the brand we just onboarded. |
| 2.3 | **Dashboard link** | In embedded app, “View analytics” → link to `https://tryonline.vercel.app/brand?shop=<shop>` (or token-based). Brand dashboard already works by shop filter. |

**Outcome:** Brand knows we handle product setup; you have a clear way to add garments for new brands. No automation required yet.

---

### Phase 3 — App Store listing

**Goal:** Tryon is discoverable in the Shopify App Store so more brands can install and onboard.

| Step | What | Deliverable |
|------|------|-------------|
| 3.1 | **Listing** | Icon 1200×1200, description, screenshots, support/emergency contact, compliance webhooks. |
| 3.2 | **Submit** | Fix automated checks, submit for review. |
| 3.3 | **Post-approval** | New stores find Tryon in the App Store; same onboarding (Phase 1) and garment flow (Phase 2). |

**Outcome:** Shopify is the marketing channel; more brands discover and install Tryon.

---

### Phase 4 — Automate garment flow (later)

**Goal:** Reduce manual CLO work; brands or system can add/update garments.

| Step | What | Notes |
|------|------|--------|
| 4.1 | **Product sync** | After install, sync store’s products (Admin API). Show in app: “Select products for try-on.” |
| 4.2 | **Garment upload or link** | Option A: Brand uploads 3D assets (per product/size); we save to storage and create `garments` rows. Option B: We generate from photos (future). Option C: We keep CLO production but you use an internal tool that reads “pending products” for a brand and you create garments and link them. |
| 4.3 | **Status in app** | In embedded app: “Products with try-on: 3 live, 2 in setup.” |

**Outcome:** Scalable garment pipeline; app stays the single place for brand onboarding and widget setup.

---

## 6. Technical details

### 6.1 Widget ↔ backend ↔ garments (no change)

- Widget URL: `https://tryonline.vercel.app/test-viewer.html?shop=...&product_id=...&variant_id=...` (and optional user_id, preferred_fit).
- Frontend/embed calls `GET /api/products/{product_id}/tryon-config`. Backend queries `garments` where `shopify_product_id = product_id`, returns `model_urls` and `size_chart`. If none, 404 (or demo). So **widget is already linked to backend and garments**; we only need correct data in `garments`.

### 6.2 Embedded app stack

- **Host:** Same Next.js app (tryonline.vercel.app), new route e.g. `/app`.
- **Auth:** Shopify App Bridge + session token (JWT). Backend can validate token and return shop/merchant if needed.
- **Deep links:** Use `client_id` from Tryon app (Partners) and block handle `tryon-button`, embed handle `tryon-cart-embed`.

### 6.3 Install → create brand

- On install (OAuth redirect or `app/uninstalled` / custom install webhook): backend receives `shop` (myshopify domain). Insert or update `brands`: `shopify_domain` = shop, name/email from Shopify API or leave for onboarding form. Then `_resolve_brand_id(shop_domain)` in analytics works.

### 6.4 Optional: snippet (one line of code)

- If we ever offer a “paste this code” option: one script tag + one div; script builds button and on click opens `https://tryonline.vercel.app/test-viewer.html?shop=...&product_id=...&variant_id=...` in a modal or new tab. Same widget, no theme extension. Not the main path.

---

## 7. Order of work (summary)

| Phase | When | What |
|-------|------|------|
| **0** | Before first test | Persona/avatar update; first CLO garments for one brand; smoke test widget + garment. |
| **1** | First test run | Embedded app (onboarding) + deep links + App URL; install → create brand. |
| **2** | With first test | In-app copy for “we set up your products”; internal process to add garments; dashboard link. |
| **3** | When ready for growth | App Store listing and submit. |
| **4** | Later | Automate product sync and garment creation/upload. |

---

## 8. Summary

- **App = brand onboarding.** Brands download the app (install link now, App Store later) → open it in Shopify admin → go through onboarding → get the Try On widget via deep link. Same theme extension as today; we add the embedded app and point the App URL to it.
- **Widget is already linked to backend and garments.** Backend resolves try-on config by `shopify_product_id`. We only need `garments` rows for their products (you create in CLO at first; later we can automate).
- **Shoppers:** Already working (Fit Passport, avatar, widget, add to cart, analytics). No change.
- **Brand dashboard:** Already on the website; we link it from the app and tie brands to stores via `brands.shopify_domain`.
- **Recommendation:** Build the **app** (embedded onboarding) for the first test run; use a **snippet** only if we need a quick test without the app. Shopify is for marketing so more brands discover and onboard; the app is how they get the widget and how we scale.
