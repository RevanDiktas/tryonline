# Category A — Step-by-Step Implementation

## Step 1: Run schema migration ✓ (You do this)

1. Open **Supabase Dashboard** → your project
2. Go to **SQL Editor**
3. Open `frontend/supabase-migration-analytics-category-a.sql`
4. Copy the full contents and paste into the editor
5. Click **Run**
6. Confirm no errors

---

## Step 2: Backend — align track_event + create_tryon_session ✓

- [x] Update event models (new event types, optional user_id)
- [x] Implement create_tryon_session (insert into tryon_sessions)
- [x] Align track_event to DB schema (event_data, product_id, etc.)
- [x] Add Request to get IP, user_agent

---

## Step 3: Frontend — event wiring ✓

- [x] Create session on widget open (call create_tryon_session)
- [x] Track widget_opened, tryon_started, size_recommended, size_selected, add_to_cart
- [x] Pass session_id in Add to Cart payload (for Shopify)

---

## Step 4: Session in cart (Shopify)

- [ ] Include session_id in cart attributes when Add to Cart

---

## Step 5: Webhook orders/paid

- [ ] POST /api/webhooks/shopify
- [ ] Parse orders/paid, extract session_id, write purchase event

---

## Step 6: Aggregation job

- [ ] Batch: analytics_events → analytics_daily
- [ ] WTD/MTD/QTD/YTD logic

---

## Step 7: Derived metrics API

- [ ] Endpoints for TryOn→ATC, TryOn→Purchase, revenue, AOV, etc.

---

## Step 8: Dashboard

- [ ] KPI cards, charts, time filters
