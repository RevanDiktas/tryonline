# TryOn Data Inventory — Summary for Quant

**Purpose:** Exhaustive list of **individual datapoints** we gather, in three categories, so a quant can design a robust data/analytics plan.  
**Source:** Implementation plan, Supabase schema, tracked events, and we-use vs brand-gets split.

---

## Signal only (noise filtered) — use this for the robust plan

*Below: **only datapoints that matter** for modelling, ROI, conversion, sizing, attribution, and regional analysis. Infrastructure, duplicates, and implementation detail are excluded. Full list and “excluded as noise” are in the appendix.*

### Category 1: User data (signal only)

| # | Datapoint | Type | Why it matters |
|---|-----------|------|----------------|
| 1 | `user_id` | UUID | Join key; attribution; cohorts. |
| 2 | `email` | Text | Identity; optional for LTV/comms. |
| 3 | `name` | Text | Identity; support. |
| 4 | `country` | Text | Region; buying teams; “near boutiques”. |
| 5 | `city` | Text | Region; granular geo. |
| 6 | `date_of_birth` | Date | Age (derive); demographics. |
| 7 | `gender` | Text | Fit/sizing; segmentation. |
| 8 | `height` | Integer (cm) | Body; sizing; recommendations. |
| 9 | `weight` | Integer (kg) | Body; optional sizing / health segment. |
| 10 | `chest` | Integer (cm) | Body measurements → fit model. |
| 11 | `waist` | Integer (cm) | Same. |
| 12 | `hips` | Integer (cm) | Same. |
| 13 | `inseam` | Integer (cm) | Same. |
| 14 | `shoulder_width` | Integer (cm) | Same. |
| 15 | `arm_length` | Integer (cm) | Same. |
| 16 | `neck` | Integer (cm) | Same. |
| 17 | `thigh` | Integer (cm) | Same. |
| 18 | `torso_length` | Integer (cm) | Same. |
| 19 | `preferred_fit` | Text | `slim` \| `regular` \| `loose`; fit preference. |
| 20 | `avatar_url` | Text | URL of avatar GLB; link to 3D asset. |
| 21 | `avatar_thumbnail_url` | Text | Thumbnail URL; UI / quick lookup. |
| 22 | `pipeline_files` | JSONB | Pipeline output URLs (e.g. `avatar_glb`, `face_crop`); traceability. |
| 23 | `created_at` (signup) | Timestamptz | Cohorts; tenure. |
| 24 | `updated_at` | Timestamptz | Last profile/passport change; recency. |
| 25 | Avatar outcome | Binary / event | `avatar_created` vs `avatar_failed`; onboarding funnel. |

*`user_type` (shopper vs brand) matters for **streamflow** (routing at signup, who sees what), not for data gathering: we always collect from shoppers and provide to brands.*  
*Photo-level detail omitted (photos deleted post-processing).*

---

### Category 2: Brand-page TryOn data (signal only)

| # | Datapoint | Type | Why it matters |
|---|-----------|------|----------------|
| 26 | `user_id` | UUID | Attribution; user-level behaviour. |
| 27 | `session_id` | UUID | Join events in a try-on; attribution. |
| 28 | `brand_id` / `shop_domain` | UUID / Text | Brand scope; per-store metrics. |
| 29 | `product_id` | Text | Product-level performance; trends. |
| 30 | `product_name` | Text | Product label; reporting; merchandising. |
| 31 | `variant_id` | Text | Variant-level where relevant. |
| 32 | `event_type` | Text | Funnel: `widget_opened` → `tryon_started` → `size_selected` → `add_to_cart` → `purchase`. |
| 33 | `size` (recommended) | Text | Fit model; recommended vs selected vs purchased. |
| 34 | `size` (viewed/selected) | Text | Sizing distribution; choice behaviour. |
| 35 | `size` (purchased) | Text | From order; fit accuracy. |
| 36 | `amount` | Decimal | Revenue; AOV; attribution. |
| 37 | `currency` | Text | Amount context. |
| 38 | `order_id` | Text | Join to order; dedupe. |
| 39 | `country` | Text | Region; same as user or IP-derived. |
| 40 | `city` | Text | Region. |
| 41 | `created_at` (event) | Timestamptz | Funnel timing; dwell; trends. |
| 42 | Session `created_at` / `completed_at` | Timestamptz | Dwell; session length. |
| 43 | `sizes_viewed` | Text[] | Consideration set; size exploration. |
| 44 | Aggregates | — | `avatars_created`, `tryons_started`, `add_to_carts`, `purchases`, `unique_users`, `unique_sessions`, `date`, `country`, `product_id` for daily/region/product breakdowns. |

*One canonical `session_id` per try-on; no need for `session_token` in the quant plan.*

---

### Category 3: Data we keep ourselves (signal only)

| # | Datapoint | Why it matters |
|---|-----------|----------------|
| 45 | `avatar_started` | Onboarding funnel. |
| 46 | `avatar_created` | Success; cohort “has avatar”. |
| 47 | `avatar_failed` | Funnel drop-off; pipeline health. |
| 48 | `widget_opened` | Funnel top. |
| 49 | `widget_closed` | Early exit; intent vs bounce. |
| 50 | `tryon_ended` | Session end; dwell. |
| 51 | `viewer_load_failed` | Technical drop-off. |
| 52 | `viewer_error` | Reliability. |
| 53 | Drop-off metrics (derived) | e.g. opened vs started; started vs size selected; we use, brand doesn’t. |

*Excluded from signal: `user_agent`, `ip_address` (we have country/city), `internal_notes`, `session_token`, surrogate `id`s.*

---

## Excluded as noise

*Not needed for modelling, ROI, or a robust data plan.*

| Excluded | Reason |
|----------|--------|
| `user_type` | Matters for **streamflow** (routing shopper vs brand at signup); we always gather from shoppers and provide to brands, so not a data-gathering datapoint. |
| Surrogate keys (`id` bigserial, table UUIDs) | Use `user_id`, `session_id`, `brand_id`, `order_id` for joins. |
| `processing_started_at`, `processing_completed_at` | Implementation detail; avatar outcome suffices for funnel. |
| `phone` | Unless used for LTV/comms modelling. |
| `status` (fit_passport) | Captured by `avatar_created` / `avatar_failed`. |
| `photo_url`, `photo_type`, `is_processed`, `delete_after_processing` | Photos deleted; we only care that avatar was created or failed. |
| `session_token` | Use `session_id`; token is implementation. |
| `action` (tryon_sessions) | Redundant with `event_type`. |
| `user_agent`, `ip_address` | Country/city sufficient for region; device rarely used. |
| `internal_notes`, `status` (brand_leads) | Qualitative/CRM; not quant. |

---

## Full inventory (reference)

*Unfiltered list of all datapoints we collect. Use **Signal only** above for the robust plan.*

---

## Category 1: User Data (Personal Information from the User)

*Collected when the user signs up and onboard on **our** platform (TryOn): account creation, photo upload, avatar creation, fit passport. Stored in `users`, `fit_passports`, `user_photos`.*

### 1.1 Account / profile (`users`)

| # | Datapoint | Type | Description |
|---|-----------|------|-------------|
| 1 | `id` | UUID | User ID (links to auth). |
| 2 | `email` | Text | Email address. |
| 3 | `name` | Text | Full name. |
| 4 | `phone` | Text | Phone (with country code). |
| 5 | `date_of_birth` | Date | Date of birth. |
| 6 | `country` | Text | Country (from signup). |
| 7 | `city` | Text | City (from signup). |
| 8 | `user_type` | Text | `shopper` \| `brand`. |
| 9 | `created_at` | Timestamptz | Account creation time. |
| 10 | `updated_at` | Timestamptz | Last profile update. |

### 1.2 Fit passport / body (`fit_passports`)

| # | Datapoint | Type | Description |
|---|-----------|------|-------------|
| 11 | `user_id` | UUID | Links to `users`. |
| 12 | `height` | Integer | Height (cm). |
| 13 | `weight` | Integer | Weight (kg), optional. |
| 14 | `gender` | Text | `male` \| `female` \| `other`. |
| 15 | `avatar_url` | Text | URL of avatar GLB in storage. |
| 16 | `avatar_thumbnail_url` | Text | URL of avatar thumbnail. |
| 17 | `pipeline_files` | JSONB | All pipeline output URLs (e.g. `avatar_glb`, `face_crop`, …). |
| 18 | `chest` | Integer | Chest measurement (cm). |
| 19 | `waist` | Integer | Waist (cm). |
| 20 | `hips` | Integer | Hips (cm). |
| 21 | `inseam` | Integer | Inseam (cm). |
| 22 | `shoulder_width` | Integer | Shoulder width (cm). |
| 23 | `arm_length` | Integer | Arm length (cm). |
| 24 | `neck` | Integer | Neck (cm). |
| 25 | `thigh` | Integer | Thigh (cm). |
| 26 | `torso_length` | Integer | Torso length (cm). |
| 27 | `preferred_fit` | Text | `slim` \| `regular` \| `loose`. |
| 28 | `status` | Text | `pending` \| `processing` \| `completed` \| `failed`. |
| 29 | `processing_started_at` | Timestamptz | When processing started. |
| 30 | `processing_completed_at` | Timestamptz | When processing finished. |
| 31 | `created_at` | Timestamptz | Fit passport creation. |
| 32 | `updated_at` | Timestamptz | Last update. |

### 1.3 User photos (`user_photos`)

*Photos are deleted after processing (privacy); we may still log that they existed.*

| # | Datapoint | Type | Description |
|---|-----------|------|-------------|
| 33 | `user_id` | UUID | Links to `users`. |
| 34 | `fit_passport_id` | UUID | Links to `fit_passports`. |
| 35 | `photo_url` | Text | Storage URL (before deletion). |
| 36 | `photo_type` | Text | `front` \| `side` \| `back`. |
| 37 | `is_processed` | Boolean | Whether processing ran. |
| 38 | `delete_after_processing` | Boolean | Delete-after-processing flag. |
| 39 | `created_at` | Timestamptz | Upload time. |

---

## Category 2: Data from the User on the Brand-Page Using TryOn

*Collected when the user uses the **try-on widget** on a brand’s product page (embed): events + session context. Stored in `analytics_events`, `tryon_sessions`, and derived in `analytics_daily`.*

### 2.1 Event-level (per action, `analytics_events`)

| # | Datapoint | Type | Description |
|---|-----------|------|-------------|
| 40 | `id` | Bigint | Event ID. |
| 41 | `user_id` | UUID | User (nullable if anonymous). |
| 42 | `session_id` | UUID | Try-on session. |
| 43 | `brand_id` | UUID | Brand (when we have it). |
| 44 | `shop_domain` | Text | Shopify store domain. |
| 45 | `product_id` | Text | Shopify product ID. |
| 46 | `variant_id` | Text | Shopify variant ID. |
| 47 | `event_type` | Text | e.g. `widget_opened`, `tryon_started`, `size_recommended`, `size_viewed`, `size_selected`, `add_to_cart`, `purchase`, `widget_closed`, `tryon_ended`, `checkout_started`, `product_viewed`, `garment_switched`. |
| 48 | `event_data` | JSONB | Event-specific payload, e.g. `size`, `amount`, `currency`, `order_id`, `product_name`. |
| 49 | `country` | Text | Shopper region (user profile or IP). |
| 50 | `city` | Text | City (user profile or IP). |
| 51 | `user_agent` | Text | Browser User-Agent (if stored). |
| 52 | `ip_address` | Inet | IP (if stored). |
| 53 | `created_at` | Timestamptz | Event time (UTC). |

### 2.2 Event payload — `event_data` fields (by `event_type`)

| Event | Datapoints in `event_data` |
|-------|----------------------------|
| `size_recommended`, `size_viewed`, `size_selected` | `size` (e.g. XS, S, M, L, XL) |
| `add_to_cart` | `size` |
| `tryon_started` | `product_name` (optional) |
| `purchase` | `order_id`, `amount`, `currency`; also `product_id`, `variant_id` at top level |

### 2.3 Session-level (`tryon_sessions`)

| # | Datapoint | Type | Description |
|---|-----------|------|-------------|
| 54 | `id` | UUID | Session ID. |
| 55 | `session_token` | Text | Unique session token. |
| 56 | `user_id` | UUID | User. |
| 57 | `shop_domain` | Text | Store. |
| 58 | `product_id` | Text | Product. |
| 59 | `product_name` | Text | Product name. |
| 60 | `variant_id` | Text | Variant. |
| 61 | `sizes_viewed` | Text[] | Sizes viewed in session, e.g. `['S','M','L']`. |
| 62 | `size_recommended` | Text | Recommended size. |
| 63 | `size_selected` | Text | Size user selected. |
| 64 | `action` | Text | `opened` \| `viewed` \| `tried_on` \| `added_to_cart` \| `purchased`. |
| 65 | `purchase_order_id` | Text | Shopify order ID if purchased. |
| 66 | `purchase_amount` | Decimal | Order amount. |
| 67 | `created_at` | Timestamptz | Session start. |
| 68 | `completed_at` | Timestamptz | Session end. |

### 2.4 Derived / aggregated (`analytics_daily`)

*Built from events; used for dashboard. Not “raw” user input, but we gather and store them.*

| # | Datapoint | Type | Description |
|---|-----------|------|-------------|
| 69 | `brand_id` | UUID | Brand. |
| 70 | `date` | Date | Calendar day (UTC or brand TZ). |
| 71 | `avatars_created` | Int | Count of `avatar_created` that day. |
| 72 | `tryons_started` | Int | Count of `tryon_started`. |
| 73 | `size_views` | Int | Count of `size_viewed` / `size_selected`. |
| 74 | `add_to_carts` | Int | Count of `add_to_cart`. |
| 75 | `purchases` | Int | Count of `purchase`. |
| 76 | `unique_users` | Int | Distinct `user_id`. |
| 77 | `unique_sessions` | Int | Distinct `session_id`. |
| 78 | `country` | Text | For region-level rows. |
| 79 | `product_id` | Text | For product-level rows (if used). |

---

## Category 3: Data We Keep Ourselves (Internal Only, Not Shared with Brands)

*We use these for platform health, product, and ops. **Brand dashboard never sees them.***

### 3.1 Onboarding / avatar pipeline

| # | Datapoint | Source | Description |
|---|-----------|--------|-------------|
| 80 | `avatar_started` | Event | User started avatar creation (photo upload). |
| 81 | `avatar_created` | Event | Avatar creation succeeded. |
| 82 | `avatar_failed` | Event | Avatar creation failed. |
| 83 | `processing_started_at` | `fit_passports` | When pipeline started. |
| 84 | `processing_completed_at` | `fit_passports` | When pipeline finished. |
| 85 | `status` | `fit_passports` | `pending` \| `processing` \| `completed` \| `failed`. |
| 86 | `pipeline_files` | `fit_passports` | All pipeline output file URLs (internal). |

### 3.2 Technical / viewer

| # | Datapoint | Source | Description |
|---|-----------|--------|-------------|
| 87 | `viewer_load_failed` | Event | 3D viewer failed to load. |
| 88 | `viewer_error` | Event | Runtime error in viewer (e.g. GLB load). |

### 3.3 Funnel we use (brand sees only a subset)

*We store and use full funnel; brand gets aggregated try-on → size → ATC → purchase only.*

| # | Datapoint | Source | Description |
|---|-----------|--------|-------------|
| 89 | `widget_opened` | Event | User opened try-on. |
| 90 | `widget_closed` | Event | User closed try-on without completing. |
| 91 | `tryon_ended` | Event | User exited viewer (for dwell). |
| 92 | Drop-off metrics | Derived | e.g. opened vs started, started vs size selected; we compute, brand doesn’t see raw. |

### 3.4 Device / request (if we store but don’t expose)

| # | Datapoint | Source | Description |
|---|-----------|--------|-------------|
| 93 | `user_agent` | `analytics_events` | Browser User-Agent. |
| 94 | `ip_address` | `analytics_events` | IP address. |

### 3.5 Brand leads (internal)

| # | Datapoint | Source | Description |
|---|-----------|--------|-------------|
| 95 | `internal_notes` | `brand_leads` | Our notes on the lead. |
| 96 | `status` | `brand_leads` | `new` \| `contacted` \| `meeting_scheduled` \| `converted` \| `lost`. |

### 3.6 Identifiers we use but don’t expose to brands

| # | Datapoint | Source | Description |
|---|-----------|--------|-------------|
| 97 | `session_token` | `tryon_sessions` | Internal session token. |
| 98 | Raw `user_id` in events | `analytics_events` | We use for attribution; brand sees aggregated counts, not per-user. |

---

## Quick reference

| Category | Signal (use for plan) | Full inventory |
|----------|------------------------|----------------|
| **1. User data** | `user_id`, email, name, country, city, DoB, gender, body measurements (incl. `weight`), `preferred_fit`, `avatar_url`, `avatar_thumbnail_url`, `pipeline_files`, signup `created_at`, `updated_at`, avatar outcome. *`user_type` = streamflow only, not data gathering.* | `users`, `fit_passports`, `user_photos` |
| **2. Brand-page TryOn** | `user_id`, `session_id`, brand/shop, `product_id`, `product_name`, variant, `event_type`, size (rec/viewed/selected/purchased), amount, order_id, country, city, event/session times, aggregates | `analytics_events`, `tryon_sessions`, `analytics_daily` |
| **3. We keep ourselves** | `avatar_started`/`created`/`failed`, `widget_opened`/`closed`, `tryon_ended`, `viewer_load_failed`, `viewer_error`, drop-off metrics | Events + internal fields |

---

## Notes for the quant

- **Use “Signal only”** for the robust plan; treat the full inventory as reference.
- **Region:** `country` and `city` come from (1) user profile when logged in, or (2) IP-derived when on brand page. Same fields in user data and events.
- **Attribution:** `session_id` links events to a try-on; we use it to attribute `purchase` to try-on (cart/checkout → webhook).
- **Returns:** Not tracked at MVP. No return-related datapoints.
- **Brand leads:** Brand contact form data is **brand** info, not **user** data; omitted from Categories 1–3. Can add a separate “Brand lead data” section if needed.
