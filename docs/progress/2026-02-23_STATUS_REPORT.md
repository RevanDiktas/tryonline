# Status Report — February 23, 2026

**Summary:** Try-on widget is working on the Shopify PDP (Basic black tshirt). Sign-in, avatar, and garment load correctly. Remaining work: add more products to `garments`, optional polish, and post-pilot items.

---

## Current state

| Component | Status | Note |
|-----------|--------|------|
| **Frontend** | ✅ Live | tryonline.vercel.app / tryonline-cx1g.vercel.app |
| **Backend** | ✅ Live | Railway (heroic-celebration-production-9f72) |
| **Supabase** | ✅ In use | Auth, Storage (GARMENTS, AVATARS), garments + fit_passports |
| **Shopify app** | ✅ Deployed | tryon-6; Try On block on product pages |
| **Widget on PDP** | ✅ Working | Sign-in (popup), avatar + garment load, measurements, add to cart |

---

## What we did today

### Widget & PDP
- **Transparent overlay:** No grey square behind the widget; body/overlay and Shopify modal use transparent background when `open=1`.
- **Sign-in on PDP:** Sign-in opens in a **popup** when the widget is in an iframe (avoids third-party cookie blocking). After login, popup closes and iframe reloads with `user_id`.
- **Session memory:** `GET /auth/me` returns current user from Supabase session (cookies). Widget checks this before showing the login gate so returning users don’t have to sign in again.
- **Supabase-only data:** No demo GLBs. Avatar from `/api/avatar/:userId`, garment from `/api/products/:productId/tryon-config`. Error states: “Avatar not ready” / “Product try-on not available” when API has no data.
- **Smaller sign-in card** and sign-in as a real `<a href="...">` link.
- **Loading:** Show 3D as soon as the **current size** (and avatar if needed) has loaded; preload other sizes in the background. Error message if avatar/garment fails to load.

### Config & data
- **Vercel env:** `NEXT_PUBLIC_API_URL` (Railway), `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` (anon key, not service_role). Documented in `docs/WIDGET_DEPLOY_AND_ENV.md`.
- **Supabase Auth:** Redirect URLs set for tryonline.vercel.app and tryonline-cx1g.vercel.app so sign-in redirect works.
- **Supabase Storage:** Public read (SELECT) policies added for **GARMENTS** and **AVATARS** buckets so the widget can load GLBs.
- **Product ID fix:** `garments.shopify_product_id` set to **9174253764826** for “Basic black tshirt” so the backend finds the garment when the store sends that product ID.

### Docs
- **WIDGET_DEPLOY_AND_ENV.md:** Env vars, backend vs Vercel keys, Supabase redirect URLs, product ID mismatch, storage policies, popup sign-in on PDP.

---

## What still needs to get done

### 1. More products with try-on
- For each Shopify product that should have try-on:
  - Get the **product ID** from the Shopify admin URL (e.g. `.../products/9174253764826` → `9174253764826`).
  - In Supabase **Table Editor → garments**, add or edit a row:
    - **shopify_product_id** = that numeric ID (as text).
    - **sizes** = JSON with keys `xs`, `s`, `m`, `l`, `xl` (or the sizes you use) and values = full Supabase Storage URLs to the GLB for each size.
  - Ensure those GLB files exist in the GARMENTS bucket and the bucket has a public read policy.

### 2. Shopify extension / theme
- After code changes to the extension (e.g. Liquid or widget URL), run `./deploy.sh` from `shopify_app` and **save/publish the theme** in Shopify so the store uses the new block.

### 3. Webhook (if not already done)
- **Orders/paid webhook** to the backend (e.g. `POST /api/webhooks/shopify/orders-paid`) and **SHOPIFY_WEBHOOK_SECRET** set in Railway for attribution/analytics.

### 4. Optional polish
- Custom domain on Vercel and add that origin to backend CORS if you switch from \*.vercel.app.
- Loading copy (e.g. “Loading your size…”) is in place; adjust if you want different wording.
- If you see slow loads, confirm GLB sizes and Supabase region vs users.

### 5. Analytics daily (if you use it)
- **analytics_daily** is filled by a batch job. Run e.g. `backend/scripts/aggregate_analytics_daily.py 2026-02-23` with `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` set; or schedule it (e.g. cron) for production.

---

## Optional / future (not blocking)

- **More brands/stores:** Add brands and link garments to `brand_id` if you need it for analytics or filtering.
- **App Store listing:** When pilot is stable: listing, icon, compliance, submit for review.
- **Shopper login in widget:** Already in place (popup sign-in on PDP); any further UX (e.g. “Sign in opens in new window”) is optional.
- **Checkout profile API, regional size viz, etc.:** See `docs/NEXT_STEPS_PLAN.md` and related docs.

---

## Key references

| What | Where |
|------|--------|
| Widget deploy & env | `docs/WIDGET_DEPLOY_AND_ENV.md` |
| Product ID / garments | Same doc, “Product ID mismatch” section |
| Launch / domain | `docs/LAUNCH_WHILE_DOMAIN_PENDING.md`, `docs/SHOPIFY_APP_STORE_WIDGET_PLAN.md` |
| Next steps | `docs/NEXT_STEPS_PLAN.md` |

---

*Last updated: February 23, 2026.*
