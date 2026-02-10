# Category A — Step-by-Step Guide

Do these in order.

---

## Step 1: Run the schema migration

1. Open **Supabase Dashboard** → your project → **SQL Editor**
2. **(Optional)** Clear test data: run `frontend/supabase-clear-test-data.sql` first
3. Run the migration: copy `frontend/supabase-migration-analytics-category-a.sql` → paste → **Run**
4. Confirm no errors ("Success")

**Note:** The `brands` table must exist. If you haven't run the main schema (`frontend/supabase-schema.sql`), run that first.

---

## Step 2: Backend (done ✓)

- Event models updated
- `create_tryon_session` implemented
- `track_event` aligned to DB schema
- API routes updated

---

## Step 3: Frontend event wiring (done ✓)

- **Embed page** (React): creates session on load, tracks events
- **test-viewer.html** (GLB widget): same analytics, uses NPC t-shirt GLBs. Canonical widget for brands.

Both:
- Create session on widget open
- Track: `widget_opened`, `tryon_started`, `size_recommended`, `size_selected`, `add_to_cart`, `tryon_ended`
- `session_id` in Add to Cart payload for Shopify attribution

---

## Step 4: Test locally

**Option A — test-viewer widget (GLB models):**
1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Open `http://localhost:3000/test-viewer.html?product_id=p1&variant_id=v1&shop=demo.myshopify.com`
4. Click TRY ON, pick a size, click ADD TO CART

**Option B — React embed page:**
1. Same as above
2. Open the **TryOn widget** (product page + TRY ON): `http://localhost:3000/test-viewer.html?product_id=demo-npc-tshirt&shop=demo.myshopify.com` — or use the dashboard link "Open widget with my account". (Note: `/embed` is for iframe embedding on Shopify; use test-viewer for direct testing.)

**With your account:** From the dashboard, click **"Open widget with my account"** to test with `user_id` and `preferred_fit` — events will be attributed to you and preferred_fit auto-filled from your Fit Passport.

**Verify:** Supabase → `analytics_events` and `tryon_sessions` should have new rows.

---

## Step 5: Session in cart (Shopify theme)

When the Shopify theme receives `TRYON_ADD_TO_CART` via `postMessage`, it should add `session_id` to cart (line-item property `tryon_session_id`) so the webhook can attribute the order.

**Ready-to-use snippet:** `frontend/public/shopify-tryon-cart-snippet.js` — include in theme or paste the logic.

---

## Step 6: Webhook (done ✓)

- `POST /api/webhooks/shopify/orders-paid` — handles `orders/paid`
- Reads `session_id` from `note_attributes` or line-item `properties` (key: `tryon_session_id`)
- Idempotent by `order_id`
- Set `SHOPIFY_WEBHOOK_SECRET` in `.env` for HMAC verification

---

## Step 7: Aggregation job (done ✓)

- `backend/scripts/aggregate_analytics_daily.py`
- Run: `python scripts/aggregate_analytics_daily.py` (yesterday) or `python scripts/aggregate_analytics_daily.py 2026-01-15`
- Cron: `0 1 * * * cd /path/to/backend && python scripts/aggregate_analytics_daily.py`

---

## Step 8: Metrics API (done ✓)

- `GET /api/analytics/metrics?start=&end=&shop=&brand_id=`
- Returns: tryons_started, add_to_carts, purchases, tryon_atc_rate, tryon_purchase_rate, revenue_attributed, revenue_per_tryon, unique_sessions

---

## Step 9: Preferred fit (done ✓)

- **Dashboard:** Fit preference selector (Slim | Regular | Loose) in Measurements card. Saves to `fit_passports.preferred_fit`.
- **Algorithm:** `lib/sizeRecommendation.ts` — `recommendSize(measurements, sizeChart, preferredFit)` biases recommendation (slim = tighter, loose = roomier).
- **TryOnViewer & test-viewer:** Use preferred_fit in size recommendation. Initial recommended size reflects user preference.
- **Backend:** `track_event` enriches events with `preferred_fit` from `fit_passports` when `user_id` present.

---

## Step 10: Dashboard UI (done ✓)

Analytics section on the dashboard: KPI cards for tryons_started, add_to_carts, purchases, unique_sessions, tryon→ATC rate, tryon→purchase rate, attributed revenue, revenue per try-on. Date range (7d/30d) and shop filter.

---

## Category A status

| Item | Status |
|------|--------|
| Schema + migration | ✓ |
| Backend events API | ✓ |
| Frontend event wiring | ✓ |
| User + preferred_fit | ✓ |
| Size recommendation algo | ✓ |
| Webhook (orders/paid) | ✓ |
| Session-in-cart snippet | ✓ |
| Aggregation job | ✓ |
| Metrics API | ✓ |
| Brand dashboard UI | ✓ |
| Shopify (real store) | Later |

---

## Category B — Fit Accuracy (done ✓)

- **Webhook:** Extracts `_tryon_size` from line item properties; stores `event_data.items` = [{ session_id, size, quantity, price }] per tryon-attributed line item.
- **API:** `GET /api/analytics/fit-metrics` — size distributions (recommended/selected/purchased), acceptance rate, size up/down rates, MASE.
- **Dashboard:** Fit Accuracy section with acceptance rate, size up/down, MASE, and size distribution cards.

### Dynamic data (user + product)

- **User:** When `user_id` in URL, fetch `/api/avatar/{user_id}` for measurements + avatar_url. Used in recommendSize and displayed. Avatar supports both OBJ and GLB (OBJLoader + GLTFLoader).
- **Product:** Fetch `/api/products/{product_id}/tryon-config` for model_urls (GLBs) and size_chart.
- **Garments table:** `shopify_product_id`, `sizes` (JSONB), `size_chart` (JSONB). See `supabase-migration-garments-demo.sql`.
- **Embed & test-viewer:** Both fetch and use real data. Fallback to demo when API fails.

### Avatar + garment loading (production)

- **Separate GLBs:** Avatar and garment always fetched separately. No combined files.
- **On widget open:** Preload avatar + all garment sizes in parallel.
- **Instant size switching:** All models cached at open; size change = instant swap.
- **Modes:** `model_type: "combined"` (demo — one full model per size) | `model_type: "garment_only"` (avatar + garment per size).

### B Robustness & Verification

- **MASE:** Uses purchased vs recommended (per roadmap)
- **Size normalization:** XS/xs, Large→L, numeric 30/32/34 supported
- **Webhook test:** `python backend/scripts/test_webhook_purchase.py -s <session_id> --size M`
- **Checklist:** `docs/analytics/CATEGORY_B_VERIFICATION.md`
