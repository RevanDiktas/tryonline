# Step B — MORE DATA: Proposal & Implementation Plan

**Purpose:** Make analytics events **complete and schema-aligned** so dashboards, quant work, and regional reports use the right dimensions. Step B is about **what** extra data we capture and **where** it comes from; Step 3 (later) is about derived calculations and daily aggregation.

---

## 1. What “more data” means (the gaps we fill)

Today we already store:

- `user_id`, `session_id`, `event_type`, `shop_domain`, `product_id`, `variant_id`, `preferred_fit`, `event_data`, `user_agent`, `ip_address`

The **gaps** (from QUANT_DATA_STRATEGY and current schema):

| Data point | What it is | Why we need it | Current state |
|------------|------------|----------------|----------------|
| **country** | Shopper’s country (e.g. for regional reports) | Filter/group by region; “average size per country”; allocation | Column exists; often **empty** (frontend only sends if URL has `?country=`) |
| **city** | Shopper’s city (optional, for finer region) | City-level reports when useful | Column exists; often **empty** |
| **brand_id** | Which TryOn brand this event belongs to | Join to brands; per-brand dashboards; ROI per brand | Column exists; usually **empty** (frontend doesn’t send it; we have `shop_domain` but don’t resolve to brand) |

So **“more data” in Step B** = reliably filling **country**, **city**, and **brand_id** on every event where we can.

---

## 2. Where each piece of data comes from

### 2.1 Country & city

- **When we have `user_id` (logged-in shopper)**  
  - **Source:** `users` table (`users.country`, `users.city`) or, if missing, the user’s **default address** in `user_addresses` (country, city).  
  - **Logic:** Backend looks up user by `user_id`; if `users.country` / `users.city` are set, use them; else use default address if any; else leave null and fall back to IP (below).

- **When we don’t have `user_id` or profile has no country/city**  
  - **Source:** **IP geolocation** (GeoIP) using the request’s IP (we already capture `ip_address` in events).  
  - **Logic:** Backend calls a GeoIP lookup (e.g. free tier of a service, or a small local DB) and sets `country` (and optionally `city`) on the event before insert.  
  - **Privacy:** We only store country (and optionally city), not the raw IP in analytics for reporting; IP is already stored for abuse/security if needed.

**Summary:** Backend **enriches** every event: first try user profile (users + default address), then GeoIP fallback. Frontend can still send `country`/`city` when it has them (e.g. embed `?country=NL`); backend uses that if present, otherwise applies the enrichment.

### 2.2 brand_id

- **Source:** We have `shop_domain` on the event (e.g. `demo.myshopify.com`). The **brands** table has `shopify_domain` (unique).  
- **Logic:** Backend looks up `brand_id` from `brands` where `shopify_domain = shop_domain`. If no row exists (e.g. demo or unonboarded shop), leave `brand_id` null.  
- **When:** On every `track_event` call that has `shop_domain`; if the client didn’t send `brand_id`, we resolve it before insert.

**Summary:** Backend **resolves** `brand_id` from `shop_domain` so we don’t rely on the frontend or on brands passing it.

---

## 3. What we do *not* change in Step B

- **Event types or funnel:** No new events; we only enrich existing ones.  
- **Frontend event list:** We don’t remove any events; we only ensure the backend fills in the new fields.  
- **analytics_daily / Parquet / Step 3:** Out of scope for Step B; that’s “Step 3 of MORE DATA” later.

---

## 4. Structured implementation plan

### Phase B1 — Backend enrichment (country, city, brand_id)

| Task | Description |
|------|-------------|
| **B1.1** | **User profile lookup:** In `track_event`, when `user_id` is present and `country`/`city` are missing, fetch `users.country`, `users.city`; if null, fetch default `user_addresses.country`, `user_addresses.city` for that user. Set event `country`/`city` from this. |
| **B1.2** | **GeoIP fallback:** When event still has no country (and optionally no city) after B1.1, call a GeoIP service with request IP. Use a free/small dependency (e.g. `geoip2` with MaxMind DB, or a single HTTP call to a free API with rate limits). Set event `country` (and optionally `city`) from result. If GeoIP fails or is skipped (no IP), leave null. |
| **B1.3** | **brand_id resolution:** In `track_event`, when `shop_domain` is present and `brand_id` is not, query `brands` for `shopify_domain = shop_domain` and set `brand_id` on the event. If no brand row, keep `brand_id` null. |
| **B1.4** | **Order of operations:** Enrichment runs before insert: (1) preferred_fit (already done), (2) country/city from user profile, (3) country/city from GeoIP if still missing, (4) brand_id from shop_domain. Use frontend-supplied values when already present (don’t overwrite). |

### Phase B2 — Event wiring audit (no schema change)

| Task | Description |
|------|-------------|
| **B2.1** | **Embed:** Confirm embed sends all key funnel events (widget_opened, tryon_started, size_recommended, size_selected, add_to_cart, checkout_started when applicable). Add any missing events. Optionally pass `country`/`city` from URL if we want to prefer frontend over backend for that page. |
| **B2.2** | **test-viewer.html (widget):** Same audit: ensure every important action calls `track(...)` with the right event type. Add `country`/`city` to the payload only if we have them (e.g. from URL params); otherwise rely on backend enrichment. |
| **B2.3** | **Onboarding:** If onboarding triggers any try-on or funnel events, ensure they call the track API with at least session_id and context; backend will add country/city/brand_id when possible. |

### Phase B3 — Configuration and docs

| Task | Description |
|------|-------------|
| **B3.1** | **Config:** Add optional env vars for GeoIP (e.g. path to MaxMind DB or API key for a free service). If not set, skip GeoIP and only use user profile for country/city. |
| **B3.2** | **Docs:** Update QUANT_DATA_STRATEGY or DATA_FLOW with “Step 2 done: events enriched with country, city (user + GeoIP), brand_id (shop_domain → brands).” |

---

## 5. Suggested order of implementation

1. **B1.1** — User profile enrichment (country/city from users + default address).  
2. **B1.3** — brand_id resolution (shop_domain → brands).  
3. **B1.2** — GeoIP fallback (so anonymous or incomplete-profile events still get country/city when possible).  
4. **B2.1, B2.2, B2.3** — Wiring audit and small fixes.  
5. **B3.1, B3.2** — Config and docs.

This order gives you **region and brand** on events quickly (B1.1 + B1.3) without adding an external dependency first; then we add GeoIP for better coverage, then clean up wiring and docs.

---

## 6. Summary table: “more data” we add

| Field    | Source when available                    | Fallback        | Implemented in |
|----------|------------------------------------------|-----------------|----------------|
| country  | users or default user_addresses          | GeoIP from IP   | Backend (B1.1, B1.2) |
| city     | users or default user_addresses          | GeoIP from IP   | Backend (B1.1, B1.2) |
| brand_id | Resolved from shop_domain → brands table | None (null)     | Backend (B1.3) |

No new columns; we only **fill** existing ones in the backend and optionally pass them from the frontend when we already have them.

---

*Next: implement B1.1 and B1.3 first, then B1.2, then B2 and B3.*
