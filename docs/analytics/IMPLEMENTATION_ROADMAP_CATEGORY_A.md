# Category A — ROI & Attribution: Implementation Roadmap

**Purpose:** Step-by-step plan for implementing Category A (ROI & Attribution). Defines, for every variable and data point: where data comes from, how we label/encode it, and the implementation order.

**Reference:** [DATA_FLOW_SUMMARY.md](../DATA_FLOW_SUMMARY.md), [QUANT_DATA_STRATEGY.md](../QUANT_DATA_STRATEGY.md), [IMPLEMENTATION_PLAN_WHEN_BACK.md](../IMPLEMENTATION_PLAN_WHEN_BACK.md), [MATHEMATICAL_OPTIMIZATION.md](./MATHEMATICAL_OPTIMIZATION.md).

---

## 1. Category A — Structure

**Goal:** Quantify incremental revenue and conversion from TryOn.

### 1.1 Derived Variable Tree

| Branch | Variable | Formula / Logic |
|--------|----------|-----------------|
| **Conversion** | TryOn → ATC rate | `count(add_to_cart) / count(tryon_started)` |
| **Conversion** | TryOn → Purchase rate | `count(purchase) / count(tryon_started)` |
| **Attribution** | Purchase_with_TryOn | Binary: order linked to session that had tryon_started |
| **Attribution** | Revenue_attributed_to_TryOn | `sum(amount)` where Purchase_with_TryOn |
| **Value** | AOV_TryOn | `sum(amount) / count(purchase)` where TryOn |
| **Value** | ΔAOV | AOV_TryOn − AOV_nonTryOn *(requires baseline; deferred)* |
| **Efficiency** | Revenue_per_TryOn | Revenue_attributed / count(tryon_started) |
| **Efficiency** | Time_to_Purchase | `purchase.created_at` − `tryon_started.created_at` |
| **Efficiency** | Dwell time | `tryon_ended.created_at` − `tryon_started.created_at` (engagement signal) |
| **Segment (preferred_fit)** | All above, by fit preference | Same formulas, `GROUP BY preferred_fit` (slim / regular / loose). Compare conversion, AOV, revenue across shopper fit preferences. |

---

## 2. Data Points → Variables → Implementation

For each variable, we list: **data points** (raw inputs), **where they come from**, **how we encode them**, and **implementation steps**.

---

### 2.1 Conversion Branch

#### Variable: TryOn → ATC rate

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| `add_to_cart` count | Event | `analytics_events` WHERE `event_type = 'add_to_cart'` | **None.** Count rows. `event_type` is a filter, not encoded. | Denominator = sessions with tryon_started |
| `tryon_started` count | Event | `analytics_events` WHERE `event_type = 'tryon_started'` | **None.** Count distinct `session_id`. | Sessions, not raw events (one tryon per session) |
| `session_id` | Event context | `analytics_events.session_id` | **UUID as-is.** Used for grouping/joining, not in math. | Must be non-null for funnel events |

**Formula in code:**  
`COUNT(DISTINCT session_id WHERE event_type='add_to_cart' AND session_id IN tryon_sessions) / NULLIF(COUNT(DISTINCT session_id WHERE event_type='tryon_started'), 0)`  
*(Restrict numerator to sessions that had tryon_started. In our flow, ATC implies tryon; the join is for robustness.)*

**Implementation steps:**
1. Ensure `widget_opened` and `tryon_started` fire and persist `session_id`.
2. Ensure `add_to_cart` fires with same `session_id`.
3. In aggregation: count distinct sessions per event type in time window.

---

#### Variable: TryOn → Purchase rate

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| `purchase` count | Event (webhook) | `analytics_events` WHERE `event_type = 'purchase'` | **None.** Count rows (or distinct sessions). | |
| `tryon_started` count | Same as above | Same | Same | |
| `session_id` | Event context | `analytics_events.session_id` | **UUID as-is.** | Purchase must have `session_id` from cart attribution |

**Formula:**  
`COUNT(DISTINCT session_id WHERE event_type='purchase' AND session_id IN tryon_sessions) / NULLIF(COUNT(DISTINCT session_id WHERE event_type='tryon_started'), 0)`  
*(Cohort: sessions with tryon in time window. Conversions: purchases with matching session_id, regardless of purchase date. See Section 7.)*

**Implementation steps:**
1. Shopify webhook sends `orders/paid` with line items.
2. Cart must include `session_id` in cart attributes (or note) so we can match.
3. Backend writes `purchase` event with `session_id`, `order_id`, `amount`, `currency`.

---

### 2.2 Attribution Branch

#### Variable: Purchase_with_TryOn

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| `session_id` | Events | `analytics_events.session_id` | **UUID as-is.** | Join key |
| `order_id` | Purchase event | `analytics_events.event_data->>'order_id'` or column | **Text as-is.** Shopify order ID. | |
| `event_type` | Events | `analytics_events.event_type` | **None.** Filter: `purchase` and `tryon_started`. | |

**Logic:**  
A purchase is "with TryOn" if the `session_id` on the `purchase` event appears in a `tryon_started` event (same session). Binary: yes/no per order.

**Implementation steps:**
1. Persist `session_id` in Shopify cart (cart attributes / note) when Add to Cart is clicked.
2. Webhook reads `session_id` from order/cart, writes `purchase` event with it.
3. Query: `SELECT order_id FROM analytics_events e1 WHERE event_type='purchase' AND EXISTS (SELECT 1 FROM analytics_events e2 WHERE e2.session_id = e1.session_id AND e2.event_type = 'tryon_started')`.

---

#### Variable: Revenue_attributed_to_TryOn

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| `amount` | Purchase event | `analytics_events.event_data->>'amount'` or column | **Numeric (DECIMAL).** Store as decimal, no encoding. | Per line item or order total |
| `currency` | Purchase event | `analytics_events.event_data->>'currency'` | **ISO 4217.** e.g. `USD`, `EUR`, `GBP`. | For display; conversion optional |
| `session_id` | Same as Purchase_with_TryOn | Same | Same | Filter to TryOn-attributed only |

**Encoding for `amount`:**  
- Store raw value and currency. For single-currency brands, sum directly.  
- For multi-currency: either (a) convert to brand base currency at write time, or (b) store both; aggregate in dashboard with conversion table (ISO 4217 + daily rates). MVP: assume single currency per brand.

**Encoding for `currency`:**  
- Store as ISO 4217 alpha-3 (`USD`, `EUR`). No numeric encoding needed for sum; use for display and conversion.

**Formula:**  
`SUM(amount)` WHERE Purchase_with_TryOn.

**Implementation steps:**
1. Webhook extracts `total_price` (or line-item sums) and `currency` from Shopify order.
2. Store in `event_data` or dedicated columns: `amount` DECIMAL, `currency` TEXT.
3. Aggregate: sum amount where session has tryon_started.

---

### 2.3 Value Branch

#### Variable: AOV_TryOn

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| `amount` | Same as Revenue_attributed | Same | Same | |
| `purchase` count | Same as TryOn→Purchase | Same | Same | Only purchases with TryOn |

**Formula:**  
`SUM(amount) / NULLIF(COUNT(DISTINCT order_id), 0)` WHERE Purchase_with_TryOn.  
*(Use order_id to dedupe; one purchase event per order. See Section 7.)*

---

#### Variable: ΔAOV (deferred)

Requires non-TryOn baseline (control group or PDP sessions without TryOn). Out of scope for initial implementation. Document for future.

---

### 2.4 Efficiency Branch

#### Variable: Revenue_per_TryOn

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| Revenue_attributed | Same as above | Same | Same | |
| tryon_started count | Same as above | Same | Same | |

**Formula:**  
`Revenue_attributed_to_TryOn / COUNT(DISTINCT session_id WHERE event_type='tryon_started')`

---

#### Variable: Time_to_Purchase

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| `created_at` (tryon_started) | Event | `analytics_events.created_at` | **Timestamp (TIMESTAMPTZ).** Store UTC. | Per session |
| `created_at` (purchase) | Event | `analytics_events.created_at` | Same | Per order |
| `session_id` | Events | Same | Same | Join tryon_started to purchase by session |

**Encoding for `created_at`:**  
- Store as `TIMESTAMPTZ` (UTC). For calculations: use epoch seconds or interval.  
- Formula: `EXTRACT(EPOCH FROM (purchase.created_at - tryon_started.created_at))` → seconds.  
- For display: convert to minutes/hours in dashboard.

**Implementation steps:**
1. Get `tryon_started.created_at` for session (first event of type in session).
2. Get `purchase.created_at` for same session.
3. Compute difference. Handle multiple purchases per session (e.g. first purchase, or sum across).

---

#### Variable: Dwell time

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| `tryon_started.created_at` | Event | `analytics_events.created_at` | TIMESTAMPTZ UTC | |
| `tryon_ended.created_at` | Event | Same | Same | Requires `tryon_ended` event |
| `session_id` | Events | Same | Same | Join |

**Formula:** `tryon_ended - tryon_started` per session. Report median (robust to outliers). Aggregate: avg or median across sessions in window.

**Why:** Strong engagement signal. Longer dwell = higher intent; correlates with conversion. Add to dashboard.

---

## 3. Cross-Cutting Data Points: Encoding & Schema

These data points feed **multiple** variables. Define encoding once, use everywhere.

| Data point | Type | Encoding / Label | Storage | Rationale |
|------------|------|------------------|---------|-----------|
| `user_id` | UUID | **As-is.** No encoding. | UUID | Join key only. |
| `session_id` | UUID | **As-is.** | UUID | Join key. |
| `order_id` | Text | **As-is.** Shopify ID. | TEXT | Dedupe, join. |
| `product_id` | Text | **As-is.** Shopify product ID. | TEXT | Filter, group. |
| `variant_id` | Text | **As-is.** | TEXT | Variant-level when needed. |
| `brand_id` | UUID | **As-is.** | UUID | Scope. |
| `shop_domain` | Text | **As-is.** e.g. `store.myshopify.com` | TEXT | Fallback when no brand_id. |
| `event_type` | Enum/Text | **Fixed set.** No encoding for math. | TEXT | `widget_opened`, `tryon_started`, `size_recommended`, `size_selected`, `add_to_cart`, `purchase`, etc. |
| `amount` | Decimal | **Numeric.** | DECIMAL(10,2) | Sum, avg. |
| `currency` | Text | **ISO 4217.** | TEXT | Display, conversion. |
| `created_at` | Timestamp | **UTC TIMESTAMPTZ.** | TIMESTAMPTZ | Time math, filtering. |
| `country` | Text | **ISO 3166-1 alpha-2.** e.g. `US`, `NL`, `DE` | TEXT | Region filter; no numeric encoding for ROI. |
| `city` | Text | **As-is.** | TEXT | Optional drill-down. |
| `preferred_fit` | Text | **slim / regular / loose** (from fit_passports) | TEXT | Segment: how do conversion, AOV, revenue differ by shopper fit preference? Add to events via user_id → fit_passport join, or denormalize at write. |

**Size (for Category B, referenced here):**  
- **Ordinal encoding** when used in equations: XS=0, S=1, M=2, L=3, XL=4.  
- **Product-specific:** Sizes vary by product (e.g. 32/34 vs S/M). Use lookup table: `size_label` → `size_ordinal` per product or globally.  
- **Storage:** Keep raw `size` (TEXT) in `event_data`; derive `size_ordinal` in aggregation if needed.  
- Category A does not use size in formulas; encoding specified for B/C.

---

## 4. Schema Requirements for Category A

### 4.1 `analytics_events` (target)

| Column | Type | Required for A | Notes |
|--------|------|----------------|-------|
| `id` | BIGSERIAL | ✓ | PK |
| `user_id` | UUID | ✓ | Nullable for anonymous |
| `session_id` | UUID | ✓ | **Critical** for attribution |
| `brand_id` | UUID | ✓ | Or `shop_domain` |
| `shop_domain` | TEXT | ✓ | When no brand_id |
| `product_id` | TEXT | Optional | Product-level ROI |
| `variant_id` | TEXT | Optional | Variant-level |
| `event_type` | TEXT | ✓ | |
| `event_data` | JSONB | ✓ | `size`, `amount`, `currency`, `order_id` |
| `country` | TEXT | ✓ | ISO 3166-1 alpha-2 |
| `city` | TEXT | Optional | |
| `preferred_fit` | TEXT | Optional | slim / regular / loose. From fit_passport. Enables segment analysis. |
| `created_at` | TIMESTAMPTZ | ✓ | UTC |

**Gaps vs current backend:**  
Backend sends `garment_id` → map to `product_id`. Add `country`, `city` (from user or IP). Add `amount`, `currency`, `order_id` to `event_data` for purchase events.

### 4.2 `analytics_daily` (for performance)

| Column | Type | Purpose |
|--------|------|---------|
| `brand_id` | UUID | Scope |
| `date` | DATE | Grain |
| `tryons_started` | INT | Pre-aggregated |
| `add_to_carts` | INT | Pre-aggregated |
| `purchases` | INT | Pre-aggregated |
| `revenue` | DECIMAL | Sum of amount |
| `unique_sessions` | INT | For rates |

---

## 5. Implementation Order

| Phase | Task | Output |
|-------|------|--------|
| **1. Schema** | Align `analytics_events` with above. Add `country`, `city`, ensure `event_data` holds `amount`, `currency`, `order_id`. | Migration |
| **2. Event wiring** | Wire `widget_opened`, `tryon_started`, `size_selected`, `add_to_cart` in frontend. Backend enriches with region. | Events in DB |
| **3. Session in cart** | Add `session_id` to Shopify cart attributes when Add to Cart. | Attribution possible |
| **4. Webhook** | `POST /api/webhooks/shopify` for `orders/paid`. Extract `session_id`, `order_id`, `amount`, `currency`. Write `purchase` event. | Purchase events |
| **5. Aggregation** | Batch job: `analytics_events` → `analytics_daily`. Count by event_type, sum amount. | Daily table |
| **6. Derived vars** | API or SQL: compute TryOn→ATC, TryOn→Purchase, Revenue_attributed, AOV_TryOn, Revenue_per_TryOn, Time_to_Purchase. | Dashboard metrics |
| **7. Dashboard** | Display KPIs, funnel, trends. | Brand-facing output |

---

## 6. Encoding Summary (Quick Reference)

| Data point | Encoding | Use in equations? |
|------------|----------|-------------------|
| `user_id`, `session_id`, `order_id`, `product_id`, `variant_id`, `brand_id` | As-is (UUID/Text) | No. Join/group only. |
| `event_type` | Fixed enum | No. Filter only. |
| `amount` | DECIMAL | Yes. Sum, avg. |
| `currency` | ISO 4217 | Display. Convert if multi-currency. |
| `created_at` | TIMESTAMPTZ UTC | Yes. Intervals, time windows. |
| `country` | ISO 3166-1 alpha-2 | Filter/group. No encoding. |
| `city` | Text | Filter/group. |
| `preferred_fit` | slim / regular / loose | Segment. From fit_passports. |
| `size` | TEXT + optional ordinal (B) | Category B. |

---

---

## 7. Review & Algorithm Specification (Post-Research)

*Added after research review. Corrects potential errors and specifies best-practice algorithms.*

### 7.1 Corrections & Clarifications

| Issue | Correction |
|-------|------------|
| **Conversion denominator scope** | Cohort by **tryon_started date**: sessions where `tryon_started` occurred in the time window. Count conversions (ATC, purchase) for those sessions **regardless of when** the conversion happened. Attribution follows the session, not the event date. |
| **Purchase event granularity** | **One purchase event per order** (not per line item). `amount` = order total. `COUNT(purchase)` = count of orders. Critical for AOV. |
| **AOV formula** | `AOV = SUM(amount) / COUNT(DISTINCT order_id)` where Purchase_with_TryOn. Use `order_id` not event count if one order could theoretically produce multiple events (defensive). |
| **Time_to_Purchase** | Use `MIN(created_at)` for `tryon_started` per session (first tryon in session), and `created_at` for purchase. Typically one of each per session. |
| **Division by zero** | All rate formulas must use `NULLIF(denominator, 0)` or equivalent. Return `NULL` or `0` when denominator is 0; never raise. |

### 7.2 Canonical Algorithms (SQL-Like Pseudocode)

**TryOn → ATC rate (session-based):**
```sql
WITH tryon_sessions AS (
  SELECT DISTINCT session_id FROM analytics_events
  WHERE event_type = 'tryon_started' AND created_at BETWEEN :start AND :end
),
atc_sessions AS (
  SELECT DISTINCT e.session_id FROM analytics_events e
  INNER JOIN tryon_sessions t ON e.session_id = t.session_id
  WHERE e.event_type = 'add_to_cart'
)
SELECT COUNT(atc_sessions)::FLOAT / NULLIF(COUNT(tryon_sessions), 0) AS rate;
```

**TryOn → Purchase rate (cohort attribution):**
```sql
-- Cohort: sessions with tryon in window. Conversions: purchases with matching session_id within attribution window.
-- Attribution window: e.g. 30 days. Purchase must be within 30d of tryon.
WITH tryon_sessions AS (
  SELECT DISTINCT session_id, MIN(created_at) AS first_tryon
  FROM analytics_events WHERE event_type = 'tryon_started' AND created_at BETWEEN :start AND :end
  GROUP BY session_id
),
purchase_sessions AS (
  SELECT DISTINCT e.session_id FROM analytics_events e
  INNER JOIN tryon_sessions t ON e.session_id = t.session_id
  WHERE e.event_type = 'purchase'
    AND e.created_at <= t.first_tryon + INTERVAL '30 days'  -- attribution window
)
SELECT COUNT(*)::FLOAT / NULLIF((SELECT COUNT(*) FROM tryon_sessions), 0) AS rate
FROM purchase_sessions;
```

**Revenue_attributed_to_TryOn:**
```sql
-- Apply attribution window: purchase within 30d of tryon.
WITH tryon_first AS (
  SELECT session_id, MIN(created_at) AS first_tryon
  FROM analytics_events WHERE event_type = 'tryon_started' GROUP BY session_id
)
SELECT COALESCE(SUM(e.amount), 0) FROM analytics_events e
INNER JOIN tryon_first t ON e.session_id = t.session_id
WHERE e.event_type = 'purchase'
  AND e.created_at <= t.first_tryon + INTERVAL '30 days';
```

**AOV_TryOn:**
```sql
-- Use order_id for deduplication; amount is per order.
SELECT SUM(amount) / NULLIF(COUNT(DISTINCT order_id), 0) AS aov
FROM analytics_events WHERE event_type = 'purchase' AND ... /* Purchase_with_TryOn */;
```

**Time_to_Purchase (median, robust to outliers):**
```sql
-- Per session: purchase_ts - min(tryon_started_ts). Then aggregate.
SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY (p.created_at - t.first_tryon)) AS median_seconds
FROM (...) t JOIN (...) p ON t.session_id = p.session_id;
```

### 7.3 Edge Cases

| Edge case | Handling |
|-----------|----------|
| Session with multiple add_to_cart | Count session once. Use DISTINCT session_id. |
| Order spans multiple TryOn sessions | Not possible: one cart, one session_id. |
| Anonymous users (no user_id) | Use session_id only. Rates and revenue still valid. |
| Webhook delay | Purchase event may arrive after TryOn. Use eventual consistency; allow up to 24–48h for "today" metrics to stabilize. |
| Currency mix | Sum in brand base currency. Convert at write or at read; document choice. |

---

## 8. Senior Research Review (2040 Standard)

*Rigorous improvements from an enterprise analytics perspective.*

### 8.1 Statistical Rigor

| Improvement | Detail |
|-------------|--------|
| **Confidence intervals for rates** | Use **Wilson score interval** (not Wald) for conversion rates. Avoids erratic coverage when n is small. Display as e.g. "12% (10–15%)" so brands see uncertainty. |
| **Bayesian option (best math)** | **Beta-Binomial:** Posterior p ~ Beta(conversions+1, non_conversions+1). Expected rate = (conv+1)/(conv+non_conv+2). Credible interval from qbeta. Peek-safe for A/B tests. See [MATHEMATICAL_OPTIMIZATION.md](./MATHEMATICAL_OPTIMIZATION.md) §2.1. |
| **Minimum sample size** | Suppress or flag rates when denominator < 30. Unstable otherwise. Optional: show "Insufficient data" instead of a rate. |
| **Time_to_Purchase: use median** | Mean is skewed by outliers (someone buys next day). Median is robust. Report both if useful. |

### 8.2 Data Quality & Robustness

| Improvement | Detail |
|-------------|--------|
| **Idempotency for purchase webhook** | Use `order_id` as idempotency key. Before insert, `SELECT WHERE order_id = X`; if exists, skip. Shopify may retry; avoid duplicate revenue. |
| **Webhook deduplication** | Store `X-Shopify-Webhook-Id` (or equivalent) and reject duplicates. Per Shopify docs. |
| **Null session_id on purchase** | If webhook arrives without session_id (cart attribute missing), log for debugging; do not attribute. Track "unattributed purchases" separately. |

### 8.3 Temporal Logic (Critical)

| Improvement | Detail |
|-------------|--------|
| **Attribution window** | Define explicitly: e.g. **30 days**. Purchase attributed to TryOn only if `purchase.created_at - tryon_started.created_at <= 30 days`. Prevents crediting TryOn for purchases months later. Document and make configurable. |
| **Cohort time boundary** | For "January conversion": cohort = tryon_started in January. Include purchases for those sessions **only if within attribution window**. E.g. tryon Jan 31, purchase Feb 15 → counts in January cohort (within 30d). |
| **Session boundary** | Define session end: e.g. 30 min inactivity, or on widget_closed. For Time_to_Purchase: use first tryon_started to purchase in same session. Multi-session journeys: out of scope for MVP. |

### 8.4 Multi-Item Order Handling

| Scenario | Handling |
|----------|----------|
| Order has 1 item from TryOn | Full order amount attributed. Simple. |
| Order has 2+ items, mix of TryOn and non-TryOn | **Option A (MVP):** Full order attributed if any line item has session_id. **Option B (strict):** Attribute only line-item revenue for items with session_id. Document choice; Option A is simpler. |
| Same session, multiple ATC, one checkout | One order, one purchase event. Correct. |

### 8.5 Missing Variable: Dwell Time

| Variable | Formula | Why add |
|----------|---------|---------|
| **Dwell time** | `tryon_ended.created_at - tryon_started.created_at` (or MIN tryon_started to MAX tryon_ended) | Strong engagement signal. Longer dwell = higher intent. Correlates with conversion. Add to Efficiency branch. |

### 8.6 Semantic Contracts

| Term | Definition |
|------|------------|
| **TryOn session** | One widget open. session_id created on widget_opened. All events in that widget share session_id. |
| **Cohort** | Set of sessions where tryon_started occurred in time window W. |
| **Conversion** | For cohort, count of those sessions that also had ATC (or purchase) within attribution window. |
| **Attribution window** | Max days between tryon and purchase for credit. Default 30. |

---

*Next: Same structure for Category B (Fit) and Category C (Trend). No code yet — foundation only.*
