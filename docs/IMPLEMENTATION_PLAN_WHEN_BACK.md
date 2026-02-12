# TryOn MVP — Implementation Plan (When You’re Back)

**Purpose:** Structured, detailed plan to follow when you return. No code — plan only.  
**Focus:** Brand lead onboarding + data/tracking + analytics dashboard.  
**Philosophy:** Analytics = **revenue**. Try-on = **bait** to make brands want the product.

---

## Table of Contents

1. [Overview & Principles](#1-overview--principles)
2. [Brand Onboarding (Lead Capture)](#2-brand-onboarding-lead-capture)
3. [Data & Tracking](#3-data--tracking)
4. [Tracking Mechanism: Click API, Scripts, Storage, Algos](#4-tracking-mechanism-click-api-scripts-storage-algos)
5. [Event Wiring — What It Is and How We Do It](#5-event-wiring--what-it-is-and-how-we-do-it)  
    - [5.5 We Use vs Brand Gets](#55-we-use-vs-brand-gets--what-we-track-vs-what-the-brand-sees)
6. [Analytics Dashboard](#6-analytics-dashboard)
7. [Shopify Button, API Calls, and Webhooks](#7-shopify-button-api-calls-and-webhooks)
8. [Implementation Order & Phases](#8-implementation-order--phases)
9. [What Else Stays in the Plan](#9-what-else-stays-in-the-plan)
10. [Gaps to Address (Before/During Build)](#10-gaps-to-address-beforeduring-build)

---

## 1. Overview & Principles

### 1.1 Scope of This Plan

- **In scope:** Brand lead form (onboarding), event tracking, analytics schema, dashboard with time filters and region.
- **Out of scope (you handle separately):** Securing a brand partner. Keep it in the plan as a reminder; no implementation tasks for it here.

### 1.2 Guiding Principles

- **Daily grain first.** All reporting is built from **day-level** data. Week/month/quarter/year are **derived** via aggregation, not stored as primary.
- **Region is first-class.** Shopper region (country, optionally city) is stored and filterable — critical for buying teams (e.g. “shoppers near our boutiques”).
- **Brand leads ≠ brand accounts.** Lead form = contact info only. We reach out and plan a meeting. No auth, no dashboard access at lead stage.
- **Implement precisely.** Schema, events, and aggregations must be well-defined before coding.

### 1.3 Current State (Reference)

- **Shopper flow:** Signup → onboarding → dashboard. Stays as is.
- **Signup page:** “How will you use TryOn?” → **Shopper** | **Brand**. Today, both use the same form and create a user. That stops for brands.
- **Brand path (new):** Brand → **dedicated lead form** → submit → thank-you; we contact them. No account creation.

---

## 2. Brand Onboarding (Lead Capture)

### 2.1 Entry Point

- **Where:** The existing “How will you use TryOn?” step on the signup page (`/signup`, step `user_type`).
- **Change:** When user selects **“I’m a Brand”**, **do not** go to the current details form. Instead, **navigate to a new page** (e.g. `/brands/lead` or `/brand-lead`).
- **Shopper:** Unchanged. “I’m a Shopper” → existing details form → signup → onboarding.

### 2.2 Brand Lead Form Page

**Route:** e.g. `/brands/lead` (or `/brand-lead`). No auth required.

**Form fields — required:**

| Field | Type | Purpose |
|-------|------|---------|
| Brand / company name | Text | Who they are |
| Contact name | Text | Person we’ll reach out to |
| Email | Email | Primary contact |
| Phone | Tel | With country code selector (reuse signup pattern) |
| Country | Dropdown | Same list as signup |
| City | Text | For regional lead prioritization |

**Form fields — optional but valuable:**

| Field | Type | Purpose |
|-------|------|---------|
| Shopify store URL | URL | Qualify + prep for integration |
| Company size | Dropdown | e.g. 1–10, 11–50, 51–200, 200+ |
| Preferred contact method | Radio | Email / Phone / Either |
| Best time for a call | Text or dropdown | e.g. Morning / Afternoon / Evening, or free text |
| How did you hear about us? | Dropdown | Organic, Referral, Social, etc. |
| Message | Textarea | Short note, questions, etc. |

**Validation:**

- Required: non-empty, valid email, valid phone format.
- Optional: basic format checks (e.g. URL for Shopify).

**Submit behavior:**

1. Client sends POST to backend (e.g. `POST /api/brand-leads` or similar).
2. Backend validates, then inserts into `brand_leads` table (see 2.3).
3. No Supabase auth. No session. No login.
4. Success → **thank-you page** (e.g. `/brands/thank-you`): “Thanks! We’ll reach out within X days to schedule a call.”
5. Optional: show “Back to home” or “Explore TryOn as a shopper” link.

**Error handling:**

- Network/server errors: show clear message, keep form state so user can retry.
- Validation errors: inline per field, no full-page wipe.

### 2.3 Data Storage: `brand_leads` Table

**Recommendation:** New table `brand_leads` (separate from `brands`). `brands` = later, for actual customers with accounts.

**Suggested schema (define exactly before implementing):**

```
brand_leads:
  id                  UUID PK
  brand_name          TEXT NOT NULL
  contact_name        TEXT NOT NULL
  email               TEXT NOT NULL
  phone               TEXT NOT NULL
  country             TEXT NOT NULL
  city                TEXT NOT NULL
  shopify_url         TEXT
  company_size        TEXT
  preferred_contact   TEXT
  best_time           TEXT
  source              TEXT          -- e.g. 'signup_page'
  message             TEXT
  status              TEXT          -- 'new' | 'contacted' | 'meeting_scheduled' | 'converted' | 'lost'
  created_at          TIMESTAMPTZ
  updated_at          TIMESTAMPTZ
  internal_notes      TEXT          -- for your team only
```

- Indexes: `created_at`, `status`, optionally `country` for regional reports.
- RLS: only your backend (service role) writes. No public access. Optional: admin UI later to view/update leads.

### 2.4 Backend

- **Endpoint:** e.g. `POST /api/brand-leads` (or under `/api/brands/leads`).
- **Input:** JSON matching form fields.
- **Actions:** Validate → insert into `brand_leads` → return success/error.
- **Security:** Rate limit by IP (and optionally by email) to avoid abuse. No auth required for submit.

### 2.5 Optional Enhancements (Later)

- Email confirmation to the lead: “We received your request.”
- Internal notification (e.g. Slack/email) when a new lead submits.
- Simple admin view: list leads, filter by status/date, add internal notes.

---

## 3. Data & Tracking

### 3.1 Why This Matters

- **ROI, conversion, sizing, trends, add-to-carts** → all depend on **what we track** and **how we store it**.
- **Dashboard time filters** (today, WTD, MTD, QTD, YTD) → depend on **daily grain** and **aggregation rules**.
- **Region** → enables “shoppers near boutiques” and regional reports for buying teams.

### 3.2 Event Taxonomy (What We Track)

**Core events (implement first):**

| Event | When | Key payload (minimal) |
|-------|------|------------------------|
| `widget_opened` / `tryon_opened` | User opens try-on (embed or demo) | `user_id`, `session_id`, `brand_id` or `shop_domain`, `product_id`, `timestamp` |
| `avatar_created` | Avatar creation completes | `user_id`, `timestamp` |
| `tryon_started` | User enters try-on viewer for a product | `user_id`, `session_id`, `brand_id`, `product_id`, `timestamp` |
| `size_viewed` | User views a size (e.g. M) | `user_id`, `session_id`, `product_id`, `size`, `timestamp` |
| `size_recommended` | System recommends a size | `user_id`, `session_id`, `product_id`, `size`, `timestamp` |
| `size_selected` | User selects a size | `user_id`, `session_id`, `product_id`, `size`, `timestamp` |
| `add_to_cart` | User clicks Add to Cart | `user_id`, `session_id`, `product_id`, `size`, `timestamp` |
| `purchase` | Order confirmed (e.g. Shopify webhook) | `user_id`, `session_id`, `order_id`, `product_id`, `amount`, `currency`, `timestamp` |

*(Returns not tracked at MVP — 5.5.)*

**Context we must persist per event (or per session):**

- `user_id`, `session_id`, `brand_id` (or `shop_domain`), `product_id`, `variant_id` when relevant.
- **Region:** `country` (required), `city` (optional). Source: user profile (signup) and/or IP-derived fallback at event time.
- `created_at` (UTC).

### 3.3 Raw Events Storage

**Table:** `analytics_events` (or equivalent). One row per event.

**Suggested columns (align with backend and frontend before implementing):**

```
id            BIGSERIAL PK
user_id       UUID (nullable for anonymous)
session_id    UUID (nullable)
brand_id      UUID (nullable)
shop_domain   TEXT
product_id    TEXT
variant_id    TEXT

event_type    TEXT NOT NULL
event_data    JSONB         -- flexible payload: size, amount, etc.

country       TEXT          -- shopper region
city          TEXT

created_at    TIMESTAMPTZ
```

- Indexes: `(brand_id, created_at)`, `(event_type, created_at)`, `(user_id, created_at)`, `(country, created_at)` for dashboard queries.
- **Critical:** Every event used in reporting must have `created_at` and, where applicable, `brand_id` (or `shop_domain`) and `country`.

### 3.4 Region (Shopper Location)

- **Primary:** `users` (or `fit_passports`) already have `country` and `city` from signup. Use these for **user-level** region.
- **Per event:** Store `country` (and optionally `city`) on each event. Populate from:
  1. User profile when `user_id` is present.
  2. Else: IP-based geolocation at event time (e.g. server-side or via a small backend call).
- **Dashboard:** Filter and group by `country` (and `city` when useful). “Near boutiques” = future phase when we have store locations; for now, “region of shoppers” = country/city of shoppers.

### 3.5 Daily Grain (Foundation for All Time Filters)

**Principle:** Store **daily** aggregates. Week/month/quarter/year are **computed** from daily (or from raw events) at query time.

**Daily aggregates table:** e.g. `analytics_daily`

**Suggested structure (define precisely before implementing):**

```
analytics_daily:
  id            BIGSERIAL PK
  brand_id      UUID
  date          DATE         -- calendar date (UTC or brand TZ; decide explicitly)

  -- Counts (daily)
  avatars_created     INT DEFAULT 0
  tryons_started      INT DEFAULT 0
  size_views          INT DEFAULT 0
  add_to_carts        INT DEFAULT 0
  purchases           INT DEFAULT 0
  -- returns not at MVP (5.5)

  -- Conversions (denominators for rates)
  unique_users        INT DEFAULT 0
  unique_sessions     INT DEFAULT 0

  -- Optional: by region (daily)
  -- Option A: separate rows per (brand_id, date, country)
  country             TEXT

  -- Optional: by product (daily)
  product_id          TEXT
```

- **Grain:** One row per `(brand_id, date)` for global metrics; optionally per `(brand_id, date, country)` or `(brand_id, date, product_id)` for breakdowns.
- **Population:** Batch job (e.g. nightly or every hour) that reads `analytics_events` and upserts into `analytics_daily`. Only process new events (incremental) to avoid full rescans.

### 3.6 Aggregation Rules (WTD, MTD, QTD, YTD)

- **Today:** Use `analytics_daily` where `date = today` (or raw events for “today” if daily job hasn’t run yet).
- **Week-to-date (WTD):** Start of week (e.g. Monday) through today. Sum (or otherwise aggregate) daily rows in that range. Define week start (Monday vs Sunday) explicitly.
- **Month-to-date (MTD):** Start of month through today. Same idea.
- **Quarter-to-date (QTD):** Start of quarter (e.g. Jan 1, Apr 1, Jul 1, Oct 1) through today.
- **Year-to-date (YTD):** Jan 1 through today.

**Algorithm:**

1. Compute `start_date` and `end_date` from the chosen filter (Today, WTD, MTD, QTD, YTD).
2. Query `analytics_daily` (and raw events if needed) where `date BETWEEN start_date AND end_date`.
3. Sum counts, compute rates (e.g. conversion = purchases / tryons_started), etc.
4. **Individual days:** Always available from `analytics_daily` (or raw); dashboard can show day-level series (e.g. chart) and allow drill-down.

### 3.7 Metrics to Support (Detail)

**ROI (attributed purchases):**

- Revenue (from `purchase` events): sum of `amount` in selected period. We care about **what was bought through our widget**.
- Returns not tracked at MVP (see 5.5). Return-rate ROI can be in success stories later.

**Conversion:**

- Funnel: `tryon_opened` → `tryon_started` → `size_selected` → `add_to_cart` → `purchase`. Counts and conversion rates per step.
- Overall conversion rate: e.g. `purchases / tryons_started` or `purchases / add_to_carts` (define exactly).

**Shopper sizing:**

- Distribution of `size_recommended` and `size_selected` (XS–XL or actual size names).
- Optional: “recommended vs selected” (agree / size up / size down).

**Trend forecasting (what people buy):**

- Over time: which `product_id` (and optionally `variant_id`) are tried, added to cart, purchased.
- By size, by category (when we have it). Use daily (then WTD/MTD/QTD/YTD) for trend charts.

**Add-to-carts:**

- Count of `add_to_cart` events in period.
- Add-to-cart rate: e.g. `add_to_carts / tryons_started`.

**Region:**

- Counts and rates by `country` (and `city`). For buying teams: “Where do our try-on users and buyers live?” 

**Additional (track as events, aggregate in daily):**

- `avatar_created` → avatars created.
- `widget_opened` vs `tryon_started` → drop-off at entry.
- Any extra events you add later (e.g. `widget_closed`, `size_changed`) should follow the same pattern: event → daily → dashboard.

### 3.8 Event Wiring (Implementation Note)

- **Frontend:** Call `api.trackEvent(...)` (or equivalent) at the right moments: onboarding (avatar_created), embed/demo (tryon_opened, tryon_started, size_viewed, size_recommended, size_selected, add_to_cart).
- **Backend:** `POST /api/events/track` accepts these events, enriches with `country`/`city` if needed, writes to `analytics_events`.
- **Purchases:** From Shopify `orders/paid` webhook; backend writes `purchase` events. Returns not tracked at MVP (5.5).

---

## 4. Tracking Mechanism: Click API, Scripts, Storage, Algos

This section specifies **how** we measure each data point: the “click” API, where each event fires, how scripts are built and stored, and how algorithms turn raw events into dashboard metrics.

### 4.1 The “Click” API — What It Is

- **Concept:** Every tracked action (click, view, completion) triggers an **HTTP request** from frontend to our backend. We do **not** rely on Shopify or the parent page to log these; we own the pipeline.
- **Endpoint:** `POST /api/events/track` (already exists). Request body: JSON with `event_type`, `user_id`, `session_id`, `brand_id` / `shop_domain`, `product_id`, `variant_id`, and optional `metadata`.
- **Flow:** User does something → frontend calls `api.trackEvent({ ... })` → backend validates → writes one row to `analytics_events` → returns success. No batching for MVP; one request per action.
- **Idempotency:** Optional later (e.g. idempotency key for add_to_cart) to avoid double-counting. For MVP, we accept that rapid double-clicks may produce duplicate events; we can dedupe in aggregation if needed.

### 4.2 Per-Event Tracking Spec (Where + When + Payload)

For each event, we define: **where** it fires (which component, which handler), **when** (what user action or system event), and **what** we send. The **canonical list** of tracked actions (with research rationale and priority) is in **Section 5.4**; the table below aligns with that list for implementation.

| Event | Where it fires | When | Payload (minimal) |
|-------|----------------|------|-------------------|
| **`widget_opened`** | Embed page (`/embed`) or demo modal | When iframe loads OR when “Try On” opens the widget | `user_id`, `session_id`, `shop` / `brand_id`, `product_id`, `variant_id` |
| **`tryon_started`** | `TryOnViewer` | On mount (useEffect), once per session | `user_id`, `session_id`, `brand_id`, `product_id`; `metadata`: `product_name` |
| **`size_recommended`** | `TryOnViewer` | When we compute recommended size (on load, before user selects) | `user_id`, `session_id`, `product_id`, `metadata.size` |
| **`size_viewed`** | `TryOnViewer` | When user **clicks** a size (e.g. S, M, L) to view it | `user_id`, `session_id`, `product_id`, `metadata.size` |
| **`size_selected`** | `TryOnViewer` | Same as `size_viewed` for MVP, or when user “confirms” size if we add that step | `user_id`, `session_id`, `product_id`, `metadata.size` |
| **`add_to_cart`** | Embed/demo “Add to Cart” handler | When user **clicks** Add to Cart | `user_id`, `session_id`, `product_id`, `variant_id`, `metadata.size` |
| **`avatar_created`** | Onboarding page | When avatar creation **completes** (success callback from `createAvatarWithFallback`) | `user_id` only |
| **`purchase`** | Backend (webhook) | When we receive Shopify `orders/paid` webhook | `user_id`, `session_id`, `order_id`, `product_id`, `amount`, `currency` — from webhook |

**Notes:** *(Returns not tracked at MVP — see 5.5.)*

- **`size_viewed` vs `size_selected`:** We can collapse to one event (`size_selected`) for MVP: fire when user clicks a size. Later, “viewed” = hover or impression; “selected” = explicit confirm. **You will define the exact structure** when we do event wiring.
- **Session:** Create a `session_id` when the try-on widget opens (e.g. `crypto.randomUUID()` or from `POST /api/events/tryon-session`). Reuse for all events in that widget session. Enables funnel and attribution.
- **Region:** Backend adds `country` / `city` from user profile or IP before writing to `analytics_events`. Frontend does not send region.

### 4.3 How the Scripts Are Made and Where They’re Stored

**“Scripts” = the code that emits events and processes them.**

| Layer | What | Where it lives |
|-------|------|----------------|
| **Frontend — tracking calls** | `api.trackEvent({ event_type, user_id, session_id, ... })` | Inside React components: `TryOnViewer`, embed page, demo page, onboarding. Uses `lib/api.ts` → `POST /api/events/track`. |
| **Frontend — API client** | `TryOnAPI.trackEvent()`, `AnalyticsEvent` type | `frontend/lib/api.ts` |
| **Backend — HTTP API** | `POST /api/events/track`, `POST /api/events/tryon-session` | `backend/app/api/routes/events.py` |
| **Backend — event model** | `EventType` enum, `AnalyticsEvent` Pydantic model | `backend/app/models/events.py` |
| **Backend — persistence** | Insert into `analytics_events` | `backend/app/services/supabase.py` → `track_event()` |
| **Batch — daily rollup** | Job that reads `analytics_events`, aggregates by day, writes `analytics_daily` | New script (e.g. `backend/scripts/aggregate_daily.py` or Celery task). Run hourly or nightly. |
| **Backend — webhooks** | Receive Shopify `orders/paid`; map to `user_id`/`session_id`; insert `purchase` only (no returns at MVP — 5.5) | New route e.g. `POST /api/webhooks/shopify` |

**Storage:**

- **Raw events:** `analytics_events` table (Supabase). One row per tracked action.
- **Aggregated:** `analytics_daily` table. One row per `(brand_id, date)` (and optionally per region/product). Filled by the batch job.

### 4.4 Algorithms: Piecing Everything Together

**1. Daily aggregation (event → day)**

- **Input:** New rows in `analytics_events` since last run (or full scan for MVP).
- **Logic:** Group by `(brand_id, date(created_at))`. For each group:
  - Count `event_type = 'avatar_created'` → `avatars_created`
  - Count `tryon_started` → `tryons_started`
  - Count `size_viewed` or `size_selected` (as defined) → `size_views`
  - Count `add_to_cart` → `add_to_carts`
  - Count `purchase` → `purchases`; sum `amount` → revenue
  - Count distinct `user_id`, distinct `session_id` → `unique_users`, `unique_sessions`  
  *(No `returns` at MVP — 5.5.)*
- **Output:** Upsert into `analytics_daily` for that `(brand_id, date)`.
- **Optional:** Same logic per `(brand_id, date, country)` or `(brand_id, date, product_id)` if we add those grains.

**2. Time-window aggregation (WTD, MTD, QTD, YTD)**

- **Input:** `analytics_daily` + filter (Today / WTD / MTD / QTD / YTD).
- **Logic:**
  - **Today:** `date = today`; use daily row(s) for today.
  - **WTD:** `start_date = start of week (e.g. Monday)`, `end_date = today`. Sum all daily rows in `[start_date, end_date]`.
  - **MTD:** `start_date = first day of month`, `end_date = today`. Sum in range.
  - **QTD:** `start_date = first day of quarter`, `end_date = today`. Sum in range.
  - **YTD:** `start_date = Jan 1`, `end_date = today`. Sum in range.
- **Rates:** Conversion = `purchases / tryons_started`; add-to-cart rate = `add_to_carts / tryons_started`. Compute from summed counts. *(Return rate deferred — 5.5.)*

**3. Funnel, sizing, trends**

- **Funnel:** Count distinct `session_id` (or `user_id`) per event type in the window; compute drop-off between steps.
- **Sizing:** From raw `analytics_events`, filter `event_type IN ('size_recommended','size_selected')`, group by `metadata->>'size'`, count. Dashboard shows bar chart.
- **Trends:** Use `analytics_daily` (or raw) by `date`; time series of revenue, purchases, try-ons, add-to-carts. Product-level trends: group by `product_id` in raw events, then aggregate by day.

The **dashboard** reads from these algorithms’ outputs (daily tables + aggregated totals) and displays them. See **Section 6**.

### 4.5 Schema Alignment (Critical Before Build)

- Backend currently sends `brand_id`, `garment_id`, `metadata` to Supabase. Our schema uses `event_data` (JSONB), `shop_domain`, `product_id`. We must either:
  - **Option A:** Add `brand_id`, `garment_id` to `analytics_events` and keep `event_data` for extra keys (e.g. `size`, `amount`), or
  - **Option B:** Map `brand_id` → `shop_domain` (or store both), `garment_id` → `product_id` (or store both), and put the rest in `event_data`.
- Decide before implementing tracking. Use one consistent schema for both backend and batch job.

---

## 5. Event Wiring — What It Is and How We Do It

### 5.1 Definition

**Event wiring** = connecting each **user action** in the UI (clicks, page loads, completions) to a **call to our tracking API** (`POST /api/events/track`), so that every relevant action becomes a row in `analytics_events` and eventually feeds the dashboard.

Today we have the API and the client (`api.trackEvent`), but **no UI code actually calls it**. The embed only uses `postMessage` to the parent (Shopify); those messages are not sent to our backend. Wiring means **adding** `trackEvent` in the right places.

### 5.2 How We Do It (High Level)

1. **Create or reuse a session** when the try-on widget opens (e.g. call `POST /api/events/tryon-session` or generate `session_id` client-side and pass it to `track`).
2. **In each relevant component**, call `api.trackEvent({ event_type, user_id, session_id, ... })` at the right moment:
   - Embed: on load → `widget_opened`; when viewer mounts → `tryon_started`.
   - `TryOnViewer`: on mount → `tryon_started` (if not sent by embed); when fit is computed → `size_recommended`; when user clicks a size → `size_viewed` / `size_selected`; when Add to Cart is clicked → we still `postMessage` to Shopify **and** we call `trackEvent('add_to_cart', ...)`.
   - Onboarding: when avatar creation succeeds → `avatar_created`.
3. **Ensure** `user_id`, `session_id`, `brand_id`/`shop_domain`, `product_id` are available in each context (from auth, URL params, or parent).

### 5.3 Structure — You Define, We Implement

**You said you will define how we structure event wiring.** The **tracked actions** (what we measure) are now specified in **5.4** below, based on research focused on ROI, conversion optimization, fit intelligence, and merchandising. Remaining structure — **ownership** (who fires what), **session** rules, and **payload** per event — follows from that list and the per-event spec in **4.2**. Adjust 5.4 if you want to add/remove or rename events.

---

### 5.4 Tracked Actions (Research-Based)

List of **all tracked actions** that deliver the best data for **ROI**, **optimization**, **fit/sizing**, and **merchandising**. Sourced from e‑commerce funnel best practice, virtual try-on ROI studies, fashion analytics (fit/sizing, returns), and merchandising platforms (tried vs purchased, size distribution).

**Use:**  
- **Must-have (MVP):** Core funnel + fit + conversion. Needed for “proof of ROI” and basic optimisation.  
- **High-value:** Strong impact on optimisation or revenue; implement with MVP if feasible.  
- **Nice-to-have:** Deeper optimisation; add once MVP is stable.

---

#### A. Funnel & conversion (ROI proof + drop-off optimisation)

| # | Event | When / Where | Why track | Priority |
|---|-------|----------------|-----------|----------|
| 1 | **`widget_opened`** | User clicks “Try On” / embed iframe loads | Funnel top. Count how many *start* try-on; compare to PDP views for “Try On” CTR. | Must-have |
| 2 | **`widget_closed`** | User closes try-on (X, overlay click, back) | Drop-off without starting. “Opened but never tried” = friction or wrong expectation. | High-value |
| 3 | **`tryon_started`** | Viewer mounts; user sees avatar + garment | Real start of try-on. Funnel step: opened → started. Enables “start rate” and dwell. | Must-have |
| 4 | **`tryon_ended`** | User exits viewer (close, navigate away) | Session end. Use with `tryon_started` for **dwell time** (strong engagement/ROI signal). | High-value |
| 5 | **`size_recommended`** | System computes recommended size (on load) | Fit intelligence. Compare to `size_selected` and `size_purchased`; core for accuracy. | Must-have |
| 6 | **`size_viewed`** | User clicks a size (S, M, L …) to view it | Which sizes get attention. Sizing distribution, “considered but not chosen” sizing. | High-value |
| 7 | **`size_selected`** | User confirms/changes size (e.g. for ATC) | Chosen size. Recommended vs selected = fit accuracy. Feeds sizing analytics. | Must-have |
| 8 | **`add_to_cart`** | User clicks Add to Cart | Primary conversion signal. Try-on → ATC rate; product-level conversion; remarketing. | Must-have |
| 9 | **`checkout_started`** | User begins checkout (Shopify) | Funnel step. ATC → checkout → purchase. Locate drop-off (cart vs checkout). | High-value |
| 10 | **`purchase`** | Order paid (Shopify webhook) | Revenue, conversion, attribution. ROI, AOV, **what was bought through our widget**. | Must-have |

**Optimisation:** Funnel (opened → started → size selected → ATC → checkout → purchase), step conversion rates, drop-off by step. **ROI:** Conversion lift, revenue, attributed purchases. *(Returns deferred — see 5.5.)*

---

#### B. Fit & sizing (accuracy, merchandising)

| # | Event | When / Where | Why track | Priority |
|---|-------|----------------|-----------|----------|
| 12 | **`size_recommended`** | *(see A)* | — | — |
| 13 | **`size_selected`** | *(see A)* | — | — |
| 14 | **`size_purchased`** | Inferred from `purchase` (line item size) | Compare recommended vs selected vs **purchased**. Fit accuracy, “size up/down” behaviour. | Must-have |
| 15 | **`fit_feedback`** | User rates fit (e.g. “Too tight / Good / Too loose”) — *if we add UI* | Direct fit signal. Calibrate recommendations. | Nice-to-have |

**Optimisation:** Recommended vs selected vs purchased; size distribution; accuracy metrics. **ROI:** Better size charts, merchandising. *(Returns deferred — see 5.5.)*

---

#### C. Product & merchandising (trends, forecasting, buy depth)

| # | Event | When / Where | Why track | Priority |
|---|-------|----------------|-----------|----------|
| 16 | **`product_viewed`** | PDP view (when Try On available) | Interest. Product-level “views vs tried vs bought”; trending products. | High-value |
| 17 | **`tryon_started`** | *(see A)* | Product-level try-on count. “Most tried” vs “most purchased.” | — |
| 18 | **`add_to_cart`** | *(see A)* | Product-level ATC. Conversion by product. | — |
| 19 | **`purchase`** | *(see A)* | Product-level sales. Revenue by product, category. | — |

**Optimisation:** Product ranking (tried, ATC, purchased), “tried but not bought,” category performance. **ROI:** Merchandising, stock, trend forecasting.

---

#### D. Engagement (dwell, interaction depth)

| # | Event | When / Where | Why track | Priority |
|---|-------|----------------|-----------|----------|
| 20 | **`viewer_rotated`** | User rotates 3D model (orbit) | Interaction depth. More rotation ≈ higher engagement; correlate with conversion. | Nice-to-have |
| 21 | **`viewer_zoomed`** | User zooms in/out | Same as above. | Nice-to-have |
| 22 | **`garment_switched`** | User switches to another size (same product) | Size exploration. Count size switches per session; part of “consideration.” | High-value |

**Optimisation:** Dwell time, interaction depth, correlation with conversion. **ROI:** Improve UX where engagement predicts conversion.

---

#### E. Avatar & onboarding

| # | Event | When / Where | Why track | Priority |
|---|-------|----------------|-----------|----------|
| 23 | **`avatar_started`** | User starts avatar creation (photo upload) | Onboarding funnel. Started vs completed. | Must-have |
| 24 | **`avatar_created`** | Avatar creation succeeds | Completion. Funnel step; cohort “has avatar” vs conversion. | Must-have |
| 25 | **`avatar_failed`** | Avatar creation fails | Friction. Fix pipeline; reduce drop-off. | High-value |

**Optimisation:** Onboarding funnel, success rate. **ROI:** More completed avatars → more try-ons → more conversions.

---

#### F. Region & segments (buying teams, boutiques)

| # | Event | When / Where | Why track | Priority |
|---|-------|----------------|-----------|----------|
| — | **Context, not new event** | Attach `country`, `city` (and optionally `region`) to *all* events | Regional analytics. Performance by geography; “near boutiques”; buying teams. | Must-have |

**Optimisation:** Geo performance, local assortments. **ROI:** Regional strategy, physical store synergy.

---

#### G. Technical & errors (reliability, friction)

| # | Event | When / Where | Why track | Priority |
|---|-------|----------------|-----------|----------|
| 26 | **`viewer_load_failed`** | 3D viewer fails to load | Technical drop-off. Fix load failures; reduce “opened but never started.” | High-value |
| 27 | **`viewer_error`** | Runtime error in viewer (e.g. GLB load fail) | Same. Improve reliability. | Nice-to-have |

**Optimisation:** Uptime, error rate, impact on funnel. **ROI:** Fewer lost conversions from technical issues.

---

#### Summary: event list for implementation

**Must-have (MVP):**  
`widget_opened`, `tryon_started`, `size_recommended`, `size_selected`, `add_to_cart`, `purchase`, `avatar_started`, `avatar_created` + **region** on all events.  
*(`size_purchased` = derived from `purchase` payload. Returns not tracked at MVP — 5.5.)*

**High-value (add with or right after MVP):**  
`widget_closed`, `tryon_ended`, `size_viewed`, `checkout_started`, `product_viewed`, `garment_switched`, `avatar_failed`, `viewer_load_failed`.

**Nice-to-have (later):**  
`fit_feedback`, `viewer_rotated`, `viewer_zoomed`, `viewer_error`.

---

#### How this feeds optimisation & ROI

- **Funnel (A):** Opened → started → size selected → ATC → checkout → purchase. Step conversion, drop-off, try-on → purchase rate.
- **Fit (B):** Recommended vs selected vs purchased; size distribution. Improves recommendations and size charts.
- **Merchandising (C):** Product-level tried / ATC / purchased; “tried but not bought”; category trends. Informs buy depth and forecasting.
- **Engagement (D):** Dwell, rotation, zoom, size switching. Identifies high-intent behaviour and UX improvements.
- **Onboarding (E):** Avatar started → created → failed. Improves completion and pipeline.
- **Region (F):** All events by country/city. Supports buying teams and local strategy.
- **Technical (G):** Load/run errors. Reduces invisible friction and lost conversions.

---

### 5.5 We Use vs Brand Gets — What We Track vs What the Brand Sees

We track **all** events above for our own platform and product. The **brand dashboard** shows only a **subset**: what the brand cares about. They don’t care about our platform failures (e.g. avatar creation failed, viewer load failed); they care about **what happened on their store** — sizes selected, try-ons, add-to-carts, **what was bought through our widget**, and ROI.

**Structure:**

| Category | **We (TryOn) use** | **Brand gets** |
|----------|--------------------|----------------|
| **Funnel & conversion** | `widget_opened`, `widget_closed`, `tryon_started`, `tryon_ended`, `size_recommended`, `size_viewed`, `size_selected`, `add_to_cart`, `checkout_started`, `purchase`. Full funnel for **our** optimisation (drop-off, CTR, conversion). | **Try-ons started**, **size selected**, **add-to-carts**, **purchases** (attributed to widget), **revenue**, **conversion rate** (e.g. purchases / tryons_started), **add-to-cart rate**. Funnel steps that affect **their** ROI. |
| **Fit & sizing** | Same events; we analyse recommended vs selected vs purchased for **our** recommendation model. | **Size distribution** (what sizes were selected, recommended vs selected), **size_purchased** (from order). What **their** customers chose; merchandising and buy depth. |
| **Product & merchandising** | Product-level try-on, ATC, purchase for **our** insights. | **Top products** (tried, ATC, purchased), **“tried but not bought,”** trends. **Their** catalog performance. |
| **Engagement** | Dwell, rotation, zoom, `garment_switched` for **our** UX work. | We can expose **dwell time** or “sessions with size switch” later if useful; not required for MVP. |
| **Avatar & onboarding** | **`avatar_started`**, **`avatar_created`**, **`avatar_failed`**. We use these to fix **our** pipeline, reduce drop-off, improve success rate. | **Not shown.** The brand doesn’t care if avatar creation on our platform failed. |
| **Region** | We use region on every event for **our** analytics. | **Country/city** breakdown of try-ons, ATC, purchases. For **their** buying teams and “near boutiques.” |
| **Technical & errors** | **`viewer_load_failed`**, **`viewer_error`**. We use these to fix **our** reliability and reduce lost conversions. | **Not shown.** |

**Rule of thumb:**  
- **We use:** Everything we track. Platform health, funnel, fit, merchandising, engagement, errors.  
- **Brand gets:** Try-on behaviour on **their** products — sizes selected, add-to-carts, **purchases through our widget**, revenue, conversion, product performance, region. No avatar failures, no viewer errors, no internal platform metrics.

**Returns (deferred):** We are **not** tracking returns at MVP. Doing so would require access to the brand’s returns database, which we won’t have realistically. We focus on **attributed purchases through our widget** (what was bought via try-on). Return-rate ROI can be communicated later in **success stories** (e.g. “Brand X saw Y% return reduction with TryOn”) when we have case-study data — without building returns ingestion now.

---

## 6. Analytics Dashboard

### 6.1 Purpose

- **For us / brand partners:** See ROI, conversion, sizing, trends, add-to-carts, and region. **This is what generates cash.**
- **Audience:** Us first; later, brands (when they have accounts) see their own data only.
- **Dashboard showcases algo output:** All KPIs, charts, and exports come from the **aggregation algorithms** (Section 4.4): daily rollups, WTD/MTD/QTD/YTD totals, funnel, sizing, and trends. The dashboard **displays** these results; it does not recompute them. Raw events → batch job → `analytics_daily` → time-window aggregation → API → dashboard.

**We use vs Brand gets:** We **use** all tracked data internally (platform health, avatar failures, viewer errors, full funnel). The **brand dashboard** shows only what the brand cares about: **try-ons, size selected, add-to-carts, purchases (attributed to our widget), revenue, conversion, product performance, sizing, region**. No avatar failures, no viewer errors. See **5.5**.

### 6.2 Time Filters (Required)

**Exactly five presets:**

| Filter | Definition | Use case |
|--------|------------|----------|
| **Today** | From 00:00:00 today (UTC or brand TZ) to now | Real-time-ish |
| **Week-to-date (WTD)** | Start of week through today | Weekly performance |
| **Month-to-date (MTD)** | Start of month through today | Monthly performance |
| **Quarter-to-date (QTD)** | Start of quarter through today | Quarterly |
| **Year-to-date (YTD)** | Jan 1 through today | Yearly |

- **Implementation:** Same as 3.6: compute `start_date` and `end_date`, then aggregate from daily (and raw if needed).
- **UI:** Dropdown or tabs: “Today | WTD | MTD | QTD | YTD”. All charts and KPI cards respect the selected filter.

### 6.3 Granularity and Drill-Down

- **Stored granularity:** Day (see 3.5).
- **Dashboard:**
  - Show **time series** (e.g. line chart) by **day** over the selected range. So for “MTD” you see each day in the month, not just a single MTD number.
  - Allow **drill-down** into a specific day (e.g. click a point) to see day-level detail.
- **WTD/MTD/QTD/YTD:** Both (a) **totals** for the period and (b) **daily breakdown** within that period.

### 6.4 Metrics to Display

**Split by audience (5.5):**

| **We (TryOn) use** | **Brand gets** |
|--------------------|----------------|
| Avatars created, try-ons started, add-to-carts, purchases, revenue, conversion rate, add-to-cart rate, funnel, sizing, products, region. **Plus:** avatar failures, viewer load failures, full funnel drop-off (widget opened vs started, etc.). | **Try-ons started**, **size selected**, **add-to-carts**, **purchases** (attributed to widget), **revenue**, **conversion rate** (e.g. purchases / tryons_started), **add-to-cart rate**. **Funnel** (tryon → size selected → ATC → purchase). **Sizing** distribution. **Top products** (tried, ATC, purchased). **Region**. No avatar failures, no viewer errors. |

**Top-level KPIs (cards):**

- Avatars created *(we use; optionally hide from brand)*
- Try-ons started
- Add-to-carts
- Purchases (attributed to widget)
- Revenue
- Conversion rate (e.g. purchases / tryons_started)
- Add-to-cart rate

**Charts:**

- **Funnel:** tryon_opened → … → purchase (counts + conversion % per step).
- **Trends over time:** Daily series for key metrics (revenue, purchases, try-ons, add-to-carts) in the selected period.
- **Sizing:** Bar chart of `size_recommended` / `size_selected` (and `size_purchased` from orders) distribution.
- **Products:** Top products by try-ons, add-to-carts, purchases (table or chart).
- **Region:** Map or table of counts/revenue by country (and city if we store it). Filterable.

### 6.5 Region and “Near Boutiques”

- **Now:** Dashboard filter “By region” (country, optionally city). Show metrics per region. Export (e.g. CSV) for buying teams.
- **Later:** When we have **brand store locations** (e.g. boutiques), we can add “shoppers near boutiques” (e.g. same city or within X km). Out of scope for this implementation phase; keep in backlog.

### 6.6 Filtering and Export

- **Filters:** Time preset (Today / WTD / MTD / QTD / YTD), brand (when multi-brand), region (country/city).
- **Export:** CSV (or similar) of the current view (e.g. daily series, or regional breakdown) for use in spreadsheets and buying decisions.

### 6.7 Tech Notes (No Code Here)

- Dashboard can be a dedicated app (e.g. Next.js) or a set of routes under existing frontend.
- Auth: only us (or later, brand users) can access. Brand sees only its own `brand_id` data.
- API: e.g. `GET /api/analytics/kpis?filter=MTD&brand_id=...`, `GET /api/analytics/series?filter=WTD&metric=...`, etc. Backend uses `analytics_daily` + raw events as per 3.5–3.6 and **algorithm outputs** (Section 4.4).

---

## 7. Shopify Button, API Calls, and Webhooks

The Try On button and embed must work with **proper API calls** and **webhooks** so we can attribute try-ons to sessions and track **purchases** (what was bought through our widget). Returns are not in scope for MVP (5.5).

### 7.1 Current State

- **Embed** (`/embed`): Loads in iframe with `product_id`, `variant_id`, `shop`, `user_id` from URL. On Add to Cart, it **only** `postMessage`s to parent (`TRYON_ADD_TO_CART`, `TRYON_SIZE_SELECTED`). No calls to our backend for tracking.
- **Try On button on Shopify:** Typically added via Theme App Extension / App Embed. It opens our iframe with the right query params. The button itself may not call our API today.

### 7.2 What Must Be Fixed

**1. Try On button (Shopify PDP)**

- **Behavior:** Clicking “Try On” opens our embed iframe with `shop`, `product_id`, `variant_id`, and (when logged in) `user_id`.
- **API calls:**
  - **Option A:** Button or embed on load calls our `POST /api/events/tryon-session` (or similar) to create a session, get `session_id`, then use it for all `track` calls. Store maps `product_id` → our `garment_id` / brand.
  - **Option B:** Embed generates `session_id` client-side, passes it in all `track` calls; no pre-call. Simpler but we may want server-side session for validation.
- **Requirement:** Ensure we have a stable `session_id` and `brand_id`/`shop_domain` for every try-on so we can attribute events and purchases.

**2. Embed → our backend (tracking)**

- **Today:** Embed uses `postMessage` only. **Change:** Embed must **also** call `POST /api/events/track` for `widget_opened`, `tryon_started`, `size_viewed`/`size_selected`, `add_to_cart` (see Section 4.2).
- **Add to Cart:** Keep `postMessage` so the Shopify store can add the item to cart (Storefront API or form submit). **In addition**, call `trackEvent('add_to_cart', ...)` so we log it.

**3. Webhooks (Shopify → our backend)**

- **Orders:** Subscribe to `orders/paid` (and optionally `orders/created`). Our backend receives webhook, parses order line items, matches to `session_id` (e.g. via cart attribute or redirect param storing `session_id`).
- **Logic:** For each paid order, insert `purchase` events (one per line item or one per order, as we define) into `analytics_events` with `user_id`, `session_id`, `order_id`, `product_id`, `amount`, etc. **Returns:** Not tracked at MVP (5.5).

**4. Attribution (session ↔ order)**

- Store `session_id` (or try-on token) in the cart when user clicks Add to Cart (e.g. cart attribute, or redirect URL param when sending user to checkout). When webhook fires, we match order to session and user so we can attribute revenue to try-on.

### 7.3 Summary of Fixes

| Piece | Fix |
|-------|-----|
| Try On button | Opens embed with correct params; optionally create session via API |
| Embed | Call our `track` API for all relevant events; keep `postMessage` for Add to Cart |
| Add to Cart | `postMessage` to Shopify **and** `trackEvent('add_to_cart')` to us |
| Webhooks | `POST /api/webhooks/shopify` for `orders/paid`; insert `purchase` only (no returns at MVP — 5.5) |
| Attribution | Persist `session_id` in cart/checkout; use in webhook to join order → session |

---

## 8. Implementation Order & Phases

### Phase 1: Brand Lead Flow (you email brands; garments TBD from there)

1. Add `brand_leads` table (schema as in 2.3).
2. Implement `POST /api/brand-leads` (validation, insert, rate limit).
3. Create `/brands/lead` page with form (2.2). Thank-you page `/brands/thank-you`.
4. Update signup: **Brand** → redirect to `/brands/lead` instead of details form. **Shopper** unchanged.

### Phase 2: Event Wiring + Events & Daily Grain

1. **Use tracked actions** (Section 5.4) and wire per 5.2; extend 4.2 where/when/payload for new events.
2. Finalize `analytics_events` schema (3.3, 4.5) and align backend + frontend.
3. Wire frontend to `trackEvent` at all points in 4.2 (onboarding, embed, demo).
4. Add `country`/`city` to events (from user profile + optional IP fallback).
5. Create `analytics_daily` and batch job (Section 4.4) to aggregate from `analytics_events`.
6. Implement WTD/MTD/QTD/YTD logic (Section 4.4).

### Phase 3: Dashboard (Algo Output)

1. Dashboard layout: time filter (Today / WTD / MTD / QTD / YTD), KPI cards, charts.
2. API endpoints that **serve algo output** (daily + WTD/MTD/QTD/YTD, funnel, sizing, trends) — Section 6.7.
3. Funnel, trends, sizing, top products, region views.
4. Export (CSV) and region filter.

### Phase 4: Shopify Button, API Calls, Webhooks

1. Fix Try On button + embed: API calls for session + tracking (Section 7).
2. Webhooks: `orders/paid` → `purchase` events only; attribution via `session_id`. No returns at MVP (5.5).
3. Optional: admin view for `brand_leads`, internal notes, status updates.
4. Optional: “Shoppers near boutiques” when store locations exist.

### Phase 5 (Future — After A, B, C)

ABC first. These four come next. See [ANALYTICS_STRUCTURE_TREE.md](analytics/ANALYTICS_STRUCTURE_TREE.md) § Future Plan.

| Category | What |
|----------|------|
| **D. Funnel visualization** | Step-by-step drop-off: widget → tryon → size rec → size selected → ATC → purchase. "Where do we lose people?" |
| **E. Product leaderboard** | Ranked list: most try-ons, best conversion, highest TryOn-attributed revenue per product. |
| **F. Shopper / audience** | New vs returning, device, engagement depth. |
| **G. Satisfaction / feedback** | Post-purchase surveys, NPS, ratings. |

---

## 9. What Else Stays in the Plan

These remain part of the overall “when you’re back” plan:

- **Brand partner outreach:** You handle this. You email brands yourself; garment creation is determined from there. Keep as a parallel track.
- **Shopify integration:** Section 7 covers **fixes** (button, API calls, webhooks). App setup, product sync, and going live still depend on a brand partner.
- **Event schema alignment (4.5):** Ensure `analytics_events` columns match what the backend sends. Resolve before Phase 2.
- **Garment creation:** Upload, CLO3D → GLB, product mapping. You drive which garments to build from brand outreach; lower priority for eng; manual upload OK for MVP.
- **Brand dashboard access:** Later, when leads convert to customers, they get login and see **their** analytics only. Auth and scoping are separate.

---

## 10. Gaps to Address (Before/During Build)

Address these before or during implementation so the plan is fully build-ready:

**1. Privacy / consent**

- **What:** Consent before collecting photos/avatars; retention and deletion rules for avatars, measurements, and events; privacy policy for widget users.
- **Why:** Try-on uses body/photos; GDPR and trust depend on clear rules. Define lawful basis, minimisation, and user rights (access, delete, etc.).
- **Where:** Onboarding (photo upload), widget (embed context), and any policy/ToS linked from our app.

**2. Rate limiting on `POST /api/events/track`**

- **What:** Rate limit the track endpoint (e.g. by IP and/or `user_id` / `session_id`) so abuse can’t inflate metrics or overload the API.
- **Why:** Brand-lead form is rate-limited; track is not. Without limits, fake or runaway events distort analytics and create load.
- **Where:** Backend middleware or route handler for `/api/events/track`. Define limits (e.g. X requests per minute per IP/session) before Phase 2.

**3. Timezone for “Today” / WTD / MTD / QTD / YTD**

- **What:** Decide whether “today” and week/month/quarter boundaries use **UTC** or **brand timezone** (or store timezone per brand).
- **Why:** “Today” and WTD/MTD differ by location. Left undefined, dashboards and algos will be inconsistent.
- **Where:** Section 4.4 (algos), Section 6.2 (time filters), and `analytics_daily.date` definition. Lock the choice before Phase 3.

**4. Who can access our internal dashboard**

- **What:** Define how **we** access the internal dashboard (auth, VPN, internal-only URL, etc.). Brand dashboard access is “later”; our own access is not yet specified.
- **Why:** We need a clear, secure way to view “we use” metrics (avatar failures, full funnel, etc.) without exposing them to brands.
- **Where:** Section 6.7 (tech notes), Phase 3. Add auth (e.g. simple login or internal-only) and optionally IP allowlist or VPN.

---

## Summary

- **Brand onboarding:** Lead form only. “Brand” on signup → `/brands/lead` → submit → thank-you. Store in `brand_leads`. We contact them and plan a meeting.
- **Tracking:** “Click” API = `POST /api/events/track`. Per-event spec in **Section 4.2** (where/when/payload). Scripts = frontend components + backend routes + batch job. Storage = `analytics_events` → `analytics_daily`. Algos = daily rollup + WTD/MTD/QTD/YTD (**Section 4.4**).
- **Event wiring:** Connect each UI action to `trackEvent` (**Section 5**). **Tracked actions** = canonical list in **5.4** (research-based; ROI, fit, merchandising). Ownership, session, payload follow from that.
- **Dashboard:** Displays **algo output** (Section 6.1). **We use vs Brand gets** (5.5): we use all data (including avatar failures, errors); brand sees only try-ons, size selected, ATC, purchases, revenue, conversion, sizing, region. No returns at MVP; focus on **attributed purchases through our widget**. Export for buying teams.
- **Shopify:** Button + embed use API calls; webhooks for `orders/paid` only — `purchase` events (**Section 7**). No returns at MVP (5.5).
- **Order:** Brand leads → event wiring + events + daily + algos → dashboard → Shopify button + webhooks.

When you’re back, follow **Phases 1 → 2 → 3 → 4** and use this doc as the single source of truth. **Tracked actions** are in **5.4**; wire them per 5.2 and extend 4.2 (where/when/payload) as needed for Phase 2.
