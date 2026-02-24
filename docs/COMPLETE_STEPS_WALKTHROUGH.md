# Complete steps walkthrough — App Store + brand onboarding

**Purpose:** One ordered checklist of every step we need for (1) brand onboarding to work when brands install, and (2) the app to be on the Shopify App Store and work well. Execute in order.

**References:**  
- Onboarding detail: `docs/BRAND_APP_ONBOARDING_PLAN.md`  
- App Store / extension: `docs/SHOPIFY_APP_STORE_WIDGET_PLAN.md`  
- Priorities: `docs/progress/NEXT_PRIORITIES_APP_AND_ONBOARDING.md`

---

## Prerequisites (already in place)

- **Frontend:** Next.js on Vercel (e.g. `tryonline.vercel.app`), `test-viewer.html`, brand dashboard `/brand`.
- **Backend:** FastAPI (e.g. Railway/Render), `GET /api/products/{product_id}/tryon-config`, `_resolve_brand_id(shop_domain)`, webhook `orders/paid`, CORS and PORT from env.
- **DB:** `brands` (with `shopify_domain`), `garments` (with `shopify_product_id`), analytics tables.
- **Shopify app:** Partner app (Tryon), `client_id` in `shopify_app/shopify.app.toml`, theme extension: Try On block + TryOn cart embed; `application_url` currently `https://tryonline.vercel.app` (will point to embedded app).
- **Widget:** Block builds widget URL with `shop`, `product_id`, `variant_id`; cart embed uses `shopify-tryon-cart-snippet.js` logic; full viewer on our domain.

---

## Phase 0 — Prep for first test run (optional but recommended)

Do this so the first real brand has a smooth experience.

| # | Step | Details |
|---|------|--------|
| 0.1 | **Persona / avatar pipeline** | Update avatar pipeline or persona so avatars are correct for the first test. |
| 0.2 | **First brand + garments** | Pick first test store. Create 1–2 CLO garments; insert into `garments` with correct `shopify_product_id`. Optionally create `brands` row with `shopify_domain` = their store. |
| 0.3 | **Smoke test** | On a dev store: add Try On block + enable cart embed; use a product that has a garment. Shopper with Fit Passport: try-on → add to cart. Confirm widget loads garment and add-to-cart works. |

**Outcome:** Backend + widget + garments verified for one store; avatar ready.

---

## Phase 1 — Embedded app = brand onboarding

**Goal:** When a brand installs Tryon and opens the app in Shopify admin, they see our onboarding (not the public site) and add the widget in one click.

### 1.1 Embedded app host (route + App Bridge)

| # | Step | Details |
|---|------|--------|
| 1.1.1 | **Add route** | New route in Next.js, e.g. `/app` or `/shopify-admin`, that is the **only** content when opened inside Shopify admin (embedded). |
| 1.1.2 | **App Bridge + session** | Use Shopify App Bridge and session token (JWT) so the page knows it’s in Shopify admin and can read `shop` (and optionally merchant). Backend can validate the token and return shop/merchant if needed. |
| 1.1.3 | **Embedded-only behavior** | This route should render the onboarding UI when loaded inside the admin iframe; avoid redirecting to the public site when `shop` is present (or when embedded). |

**Deliverable:** A page at e.g. `https://tryonline.vercel.app/app` that loads inside Shopify admin and has access to `shop` via App Bridge/session.

### 1.2 Onboarding UI (steps)

| # | Step | Details |
|---|------|--------|
| 1.2.1 | **Step 1 — Welcome** | “Get started with Try On” / short intro. |
| 1.2.2 | **Step 2 — Add Try On button** | One button: “Add Try On button to your store” that opens the **theme editor** via deep link to add the Try On **block**. |
| 1.2.3 | **Step 3 — Enable cart** | One button: “Enable cart for try-on” that deep links to activate the **TryOn cart embed** in the theme. |
| 1.2.4 | **Step 4 — Done** | “You’re all set” + link to “We’ll set up your products for try-on” and/or link to brand dashboard. |

**Deliverable:** Simple linear flow: Welcome → Add block (deep link) → Enable embed (deep link) → Done + dashboard link.

### 1.3 Deep links (concrete)

| # | Step | Details |
|---|------|--------|
| 1.3.1 | **Block deep link** | Use: `https://<shop>/admin/themes/current/editor?template=product&addAppBlockId=<client_id>/tryon-button&target=mainSection`. Replace `<shop>` with merchant’s myshopify domain, `<client_id>` with Tryon app client_id from Partners (e.g. from `shopify_app/shopify.app.toml`: `daf4359349b8033a4165df358aa6e05c`). Block handle in extension: `tryon-button`. |
| 1.3.2 | **App embed deep link** | Use: `https://<shop>/admin/themes/current/editor?context=apps&activateAppId=<client_id>/tryon-cart-embed`. Embed handle: `tryon-cart-embed` (confirm in extension: `tryon-widget` extension, embed block name). |

**Deliverable:** Two buttons in the onboarding that open these URLs in the same tab or new tab so the merchant can add the block and enable the embed in one click each.

### 1.4 App URL and OAuth redirect (Partners)

| # | Step | Details |
|---|------|--------|
| 1.4.1 | **Set App URL** | In Shopify Partners → Tryon app → App setup: set **App URL** to the embedded app URL, e.g. `https://tryonline.vercel.app/app`. So opening Tryon from “Apps” loads this page inside the admin. |
| 1.4.2 | **Redirect URLs** | Set **Allowed redirection URL(s)** to include the same URL (e.g. `https://tryonline.vercel.app/app`) so OAuth redirects back to the embedded app after install/authorize. |

**Deliverable:** App URL and redirect both point to `/app`; no “Shopify” or “Example” in domain (App Store rule).

### 1.5 Install → create/update brand (backend)

| # | Step | Details |
|---|------|--------|
| 1.5.1 | **Hook on install** | On app install, backend must create or update a row in `brands`. Trigger: either (A) OAuth callback (when you exchange code for session and have `shop`), or (B) Shopify webhook `app/uninstalled` is not enough for “create on install”—use OAuth callback or a custom “install” webhook if available. Prefer OAuth callback: when merchant completes OAuth, your backend receives `shop`; immediately after token exchange, call “create or update brand.” |
| 1.5.2 | **Upsert brand** | Insert or update `brands` with `shopify_domain` = shop (myshopify domain). Set name/email from Shopify API if you have them, or leave blank for later. Ensure `_resolve_brand_id(shop_domain)` used in analytics continues to find this brand. |

**Deliverable:** Every install (or first OAuth) creates/updates `brands` for that shop; analytics and brand dashboard can resolve by `shop`.

---

## Phase 2 — In-app copy and dashboard link (with first test)

**Goal:** Brand knows we set up their products; they can open the brand dashboard.

| # | Step | Details |
|---|------|--------|
| 2.1 | **In-app copy** | In the embedded app (e.g. on “Done” or a separate step): “We’ll set up your products for virtual try-on. Share your store link; we’ll add try-on to selected products.” (Store is already known from install.) |
| 2.2 | **Dashboard link** | “View analytics” → link to `https://tryonline.vercel.app/brand?shop=<shop>`. Brand dashboard already filters by `shop`; no change needed if it uses query param. |
| 2.3 | **Internal process** | Internal: when a new brand onboardes, you (or ops) get their store/product list; create garments in CLO; insert/update `garments` with `shopify_product_id` and `brand_id`. Optional: small internal tool to “add garment for product X” for the new brand. |

**Outcome:** Clear expectations; brand can open dashboard; you have a repeatable way to add garments for new brands.

---

## Phase 3 — App Store listing and submit

**Goal:** Tryon is discoverable in the Shopify App Store; new brands install and go through Phase 1 onboarding.

### 3.1 Listing and assets

| # | Step | Details |
|---|------|--------|
| 3.1.1 | **Icon** | App icon **1200×1200** px; no “Shopify” or “Example” in the image. |
| 3.1.2 | **Description** | Accurate app description; no unsubstantiated claims. |
| 3.1.3 | **Screenshots** | Per Shopify requirements (see App Store listing docs). |
| 3.1.4 | **Support / emergency contact** | Set in Partners; no “Shopify” or “Example” in app URLs or API contact email. |

### 3.2 Compliance and webhooks

| # | Step | Details |
|---|------|--------|
| 3.2.1 | **Compliance webhooks** | Subscribe to required compliance webhooks in Partners (e.g. GDPR, shop redact, etc.). Implement handlers on backend if required. |
| 3.2.2 | **Emergency contact** | Set and keep up to date in app configuration. |

### 3.3 Checks and submit

| # | Step | Details |
|---|------|--------|
| 3.3.1 | **Automated checks** | Run all automated checks on the App Store review page; fix any failures (extension size, OAuth, URLs, etc.). |
| 3.3.2 | **Submit for review** | Submit the app; respond promptly to reviewer; fix “Paused” items and resubmit. |
| 3.3.3 | **Post-approval** | New stores find Tryon in the App Store; same onboarding (Phase 1) and garment flow (Phase 2). |

**Outcome:** App is on the Shopify App Store; installs flow through onboarding and get the widget in one click.

---

## Phase 4 — Refine (after first test / listing)

| # | Step | Details |
|---|------|--------|
| 4.1 | **More products on real store** | Add more garments to `garments` for the real store (CLO + `shopify_product_id`). |
| 4.2 | **Orders/paid webhook** | Ensure `SHOPIFY_WEBHOOK_SECRET` is set in production and `orders/paid` webhook is subscribed and working for attribution. |
| 4.3 | **Optional** | Custom domain for frontend/backend; analytics daily cron; UX polish; shopper login in widget (later). |

---

## Execution order (summary)

1. **Phase 0** — Prep: persona/avatar, first brand + garments, smoke test (optional but recommended).
2. **Phase 1** — Embedded app: route + App Bridge (1.1) → onboarding UI (1.2) → deep links (1.3) → App URL + redirect in Partners (1.4) → install → brand in backend (1.5).
3. **Phase 2** — In-app copy, dashboard link, internal garment process (can overlap with first test).
4. **Phase 3** — App Store: listing assets (3.1) → compliance webhooks + emergency contact (3.2) → automated checks → submit (3.3).
5. **Phase 4** — Refine: more products, webhook verification, polish.

---

## Quick reference

- **Embedded app URL:** `https://tryonline.vercel.app/app` (after you build it).
- **Client ID (Tryon):** From `shopify_app/shopify.app.toml` (e.g. `daf4359349b8033a4165df358aa6e05c`).
- **Block handle:** `tryon-button` (product block). **Embed handle:** `tryon-cart-embed` (confirm in extension).
- **Deep link — add block:** `https://<shop>/admin/themes/current/editor?template=product&addAppBlockId=<client_id>/tryon-button&target=mainSection`
- **Deep link — enable embed:** `https://<shop>/admin/themes/current/editor?context=apps&activateAppId=<client_id>/tryon-cart-embed`
- **Brand dashboard (by shop):** `https://tryonline.vercel.app/brand?shop=<shop>`

Use this doc as the single checklist; refer to the other docs for deeper technical detail.
