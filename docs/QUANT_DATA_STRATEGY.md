# TryOn Quant Data Strategy — Research Synthesis & Recommendations

**Purpose:** Compare the deeplearning-provided structure to industry research, unify categorization, map variables to calculations, and recommend data storage format.  
**Audience:** Quant, data engineering, backend, and dashboard prioritization.

---

## 0. Scope & Non-Goals

**What TryOn does:** Digital avatars + 3D clothing + size recommendation + try-on experience. Shopper gets fit confidence; brand gets data.

**This system is designed to:**
- Quantify ROI and attribution from TryOn
- Improve size buying and fit confidence
- Surface early demand and fit trend signals
- Support regional allocation and clothing order optimization for buying teams

**Non-Goals:**
- Predicting fashion aesthetics or taste
- Identifying individual shoppers
- Replacing returns or post-purchase surveys (returns deferred at MVP; ROI via success stories later)

### Quant Goals → Categories

| Goal | Primary Category | Key Variables / Metrics |
|------|------------------|-------------------------|
| ROI measurement | A (ROI) | Revenue_attributed, AOV_TryOn, Revenue_per_TryOn |
| Trend forecasting | C (Trend) | Velocity, high try-on/low purchase, fit drift |
| Reduce returns (indirect) | B (Fit) | Recommendation acceptance, size exploration entropy |
| Regional size data | B, C | Regional fit curves, size demand by country/city |
| Optimize buying teams | B, C | Size curves, product×size×region, early signals |
| Clothing order optimization | B, C | Size demand distribution, regional divergence |
| Increase conversion rate | A | Funnel conversion, TryOn→ATC, TryOn→Purchase |

---

## 1. Research Summary

### ROI & Attribution

| Finding | Source | Relevance |
|---------|--------|-----------|
| Incrementality = treatment vs control for causal attribution | Northbeam, IAB, Lifesight | Gold standard; we don't have A/B yet — session-based attribution is our starting point. |
| TryOn drives 15–40% conversion lift, 10–25% AOV increase | Fytted, academic studies | Validates our ROI focus; we measure TryOn→purchase, AOV_TryOn. |
| Behavioral signals: dwell, try-on-to-conversion, order value | Admetrics, Springer | Our funnel events + session timestamps support this. |
| Purchase_with_TryOn (binary) via session_id in cart | Our design | Session-based attribution is industry-valid; join order to session. |

**Baseline strategy (pre-A/B):** Until formal incrementality testing is available, **non-TryOn PDP sessions for the same SKU × region × time window** can serve as baseline for ΔAOV and conversion comparisons (when brand provides PDP-level analytics).

### Fit Accuracy & Size Demand

| Finding | Source | Relevance |
|---------|--------|-----------|
| Size/fit as distinct demand dimension; "jeans fit sales" forecasting | IBM, arXiv fashion forecasting | Our size_recommended/viewed/selected/purchased + regional breakdown align. |
| Recommendation acceptance, misfit signals (viewed but not purchased) | Research + our design | Fit confidence, exploration entropy, regional fit curves are validated. |
| Cold start, sparse SKU data, regional divergence | Fashion forecasting lit | Trend forecasting must handle sparse product data; aggregates by product/region help. |

### Trend & Demand Forecasting

| Finding | Source | Relevance |
|---------|--------|-----------|
| TryOn velocity, purchase velocity as early signals | Our design + forecasting practice | Momentum metrics are standard. |
| High try-on / low purchase = early warning | Our design | Validated; signals product or fit issues. |
| Size stress, fit drift, regional divergence | Fashion lit | Declining recommendation acceptance, rising exploration = drift signals. |

### Variable Categorization (Dimensions vs Measures)

| Type | Role | Examples |
|------|------|----------|
| **Dimensions** | Slice, dice, filter, group | `user_id`, `session_id`, `product_id`, `brand_id`, `country`, `city`, `event_type`, `date` |
| **Measures** | Aggregate (sum, count, avg) | `amount`, event counts, `unique_users`, `unique_sessions` |
| **Entities** | Join keys between models | `user_id`, `session_id`, `product_id`, `brand_id`, `order_id` |

### Data Storage Format

| Format | Use case | Findings |
|--------|----------|----------|
| **PostgreSQL / Supabase** | Operational; real-time ingestion; app queries | Current design; keep for live events, API, dashboard. |
| **Parquet** | Analytical workloads; quant; exports; bulk queries | 5× smaller than JSON, 74× faster for columnar queries; columnar + compression; schema evolution. |
| **JSON** | Raw event ingestion (intermediate) | Acceptable for streaming; convert to Parquet for analysis. |
| **CSV** | Exports for brands, spreadsheets | Human-readable; use for dashboard export, not primary analytics store. |

**Recommendation:** Ingest into Postgres (Supabase); run batch export to Parquet for quant/ML workloads. Supabase Analytics Buckets (Iceberg/Parquet) or ETL (Airbyte, Estuary) to S3 Parquet.

---

## 2. Comparison: Deeplearning Doc vs Research

| Aspect | Deeplearning doc | Research | Verdict |
|--------|------------------|----------|---------|
| **Category A (ROI)** | Conversion, attribution, AOV, Revenue_per_TryOn, Time_to_Purchase | Aligns; session attribution validated; ΔAOV needs baseline (non-TryOn) | Strong; add note: ΔAOV requires control/baseline when available |
| **Category B (Fit)** | Recommended=Purchased, size distributions, misfit signals, regional curves | Validated; fit as distinct demand dimension | Strong |
| **Category C (Trend)** | Velocity, early warning, size stress, fit drift | Validated; momentum + stress signals standard | Strong |
| **Derived variable trees** | Clear hierarchy (Conversion → Attribution → Value → Efficiency) | Matches dimensions + measures pattern | Good structure |
| **Data quality filters** | `viewer_load_failed`, `viewer_error`, `avatar_failed` | Essential for clean analytics | Correct |
| **Raw datapoints** | Signal-only; no infra noise | Aligns with our DATA_INVENTORY_FOR_QUANT | Aligned |

**Summary:** The deeplearning structure is research-aligned. Main addition: explicitly note that **ΔAOV vs non-TryOn baseline** requires a control group or holdout when we can run incrementality tests.

---

## 2b. Comparison to What We Have (Current State)

| Component | What we have | Gap vs Quant Strategy |
|-----------|--------------|------------------------|
| **`analytics_events`** | `user_id`, `session_id`, `event_type`, `event_data` (JSONB), `shop_domain`, `product_id` | Missing: `brand_id`, `variant_id`, `country`, `city`; backend sends `garment_id` not `product_id` |
| **`tryon_sessions`** | `sizes_viewed[]`, `size_recommended`, `size_selected`, `shop_domain`, `product_id`, `purchase_order_id`, `purchase_amount` | Has fit context; no `country`/`city`; session_id links to analytics_events via `session_id` → tryon_sessions.id |
| **`analytics_daily`** | Not in schema yet | Need: brand_id, date, counts (tryons, add_to_carts, purchases, unique_users, unique_sessions), country, product_id grains |
| **Event wiring** | API exists (`POST /api/events/track`); frontend does *not* call it — embed uses `postMessage` only | Wire `trackEvent` in TryOnViewer, embed, onboarding; backend must add region |
| **Purchase attribution** | `purchase_order_id` in tryon_sessions; no webhook for orders/paid | Need Shopify `orders/paid` webhook; persist `session_id` in cart attributes; join order → session |
| **Region** | `users.country`, `users.city` exist; not on events | Add `country`, `city` to every event (from user profile or IP fallback) |
| **Body measurements** | In `fit_passports` (chest, waist, etc.) | Use aggregated only; no PII to brands — quant strategy aligns |
| **Parquet export** | None | Add batch job or Analytics Bucket for quant workloads |

**Key schema alignment (4.5 in Implementation Plan):** Backend `track_event` sends `brand_id`, `garment_id`, `metadata`; DB has `event_data`, `shop_domain`, `product_id`. Must unify before wiring.

---

## 2c. Why It Works — Deep Research for TryOn

*Our product: digital avatars + 3D clothing + size recommendation + try-on. Shopper gets fit confidence; brand gets data. Below: why each quant lever drives value.*

### ROI & Conversion

| Lever | Why it works |
|-------|--------------|
| **Session-based attribution** | TryOn session = intent; order with same session_id = causal link. Industry standard when A/B not feasible. |
| **TryOn → ATC / Purchase rates** | Virtual try-on reduces fit uncertainty (47% dislike online shopping for this; 77.6% cart abandonment driven by fit). Our funnel directly measures this lift. |
| **AOV_TryOn vs baseline** | Studies: VTO drives 10–25% AOV increase. Confidence in fit → multi-item and premium purchases. |
| **Revenue_per_TryOn** | Single metric brands understand: "€X revenue per try-on session." Efficiency of the widget. |
| **Time_to_Purchase** | Shorter = higher intent; longer = consideration. Correlates with conversion quality. |

### Fit Accuracy & Returns (Indirect)

| Lever | Why it works |
|-------|--------------|
| **Recommendation Acceptance Rate** | Recommended = Purchased. Core fit-model accuracy metric. VTO + sizing reduces returns 25–50%; acceptance rate proxies this. |
| **Size exploration entropy** | More sizes viewed = uncertainty. Low entropy + high conversion = confident fit. |
| **Viewed-not-purchased sizes** | Misfit signal: interest but no conversion. Indicates chart or recommendation issues. |
| **Regional fit curves** | Size demand varies by region (e.g. EU vs US). Buying teams use for allocation; we provide early, TryOn-sourced data. |

### Trend & Demand Forecasting

| Lever | Why it works |
|-------|--------------|
| **TryOn / Purchase velocity** | Leading indicator. TryOns precede purchases; velocity = momentum. |
| **High try-on / low purchase SKUs** | Product or fit problem. Early warning for merchandising. |
| **Size stress** | Sizes with interest but low conversion = allocation risk or fit issue. |
| **Fit drift** | Rising exploration entropy over time = declining fit confidence; fix recommendations or charts. |
| **Regional divergence** | Size demand differs by country/city. Critical for pack optimization and store allocation. |

### Clothing Order & Buying Team Optimization

| Lever | Why it works |
|-------|--------------|
| **Size demand distribution** | Basis for **size curves** — % demand per size. Retailers use for pack/prepack optimization (how many S, M, L per carton). |
| **Regional size curves** | Replace corporate averages with geo-specific demand. Poor optimization → stockouts of popular sizes, excess fringe sizes, markdowns. |
| **Product × size × region** | Granular view for initial allocation and replenishment. Two-phase: initial buy + ongoing replenishment. |
| **Early signals** | TryOn data arrives before sales. Buying teams can adjust orders before inventory lands. |

### Conversion Rate Optimization

| Lever | Why it works |
|-------|--------------|
| **Funnel step conversion** | Opened → Started → Size selected → ATC → Purchase. Each step = optimization point. |
| **Drop-off by step** | Identifies friction (e.g. widget_closed without tryon_started = wrong expectation). |
| **Dwell time** | Longer engagement correlates with conversion; technical failures (viewer_load_failed) kill it. |
| **Avatar funnel** | avatar_started → avatar_created → avatar_failed. More avatars = more try-ons = more conversions. |

**Sources:** Virtusize, Uwear.ai, MIT OR/MS (fit information experiment), Appit (AI size recommendations), Toolio, Antuit, o9 Solutions, Clarkston Consulting, Fytted, Springer.

---

## 3. Unified Categorization Strategy

### 3.1 Category A — ROI & Attribution

**Goal:** Quantify incremental revenue and conversion from TryOn.

**Raw datapoints → Dimensions / Measures:**

| Raw | Role | Used in |
|-----|------|---------|
| `user_id`, `session_id`, `brand_id`, `shop_domain`, `product_id`, `variant_id`, `order_id` | Entities (join) | All ROI calculations |
| `event_type` (widget_opened, tryon_started, size_selected, add_to_cart, purchase) | Dimension | Funnel, conversion |
| `amount`, `currency` | Measure | Revenue, AOV |
| `created_at` (event), session `created_at` / `completed_at` | Dimension (time) | Time_to_Purchase, trends |
| `country`, `city` | Dimension | Regional ROI |

**Derived variables (calculation map):**

| Derived | Formula / Logic | Raw inputs |
|---------|-----------------|------------|
| TryOn → ATC rate | `count(add_to_cart) / count(tryon_started)` | event_type, session_id |
| TryOn → Purchase rate | `count(purchase) / count(tryon_started)` | event_type, session_id |
| Purchase_with_TryOn | `order_id` in session with tryon_started | session_id, order_id, event_type |
| Revenue_attributed_to_TryOn | `sum(amount)` where Purchase_with_TryOn | amount, session_id, event_type |
| AOV_TryOn | `sum(amount) / count(purchase)` where TryOn | amount, event_type |
| Revenue_per_TryOn | `Revenue_attributed / count(tryon_started)` | amount, event_type |
| Time_to_Purchase | `purchase.created_at - tryon_started.created_at` | created_at, event_type |

---

### 3.2 Category B — Fit Accuracy & Buying Decisions

**Goal:** Optimize size buying, allocation, and recommendation quality.

**Raw datapoints → Dimensions / Measures:**

| Raw | Role | Used in |
|-----|------|---------|
| `size` (recommended, viewed, selected, purchased) | Dimension | Fit accuracy, demand |
| `sizes_viewed[]` | Dimension / Measure | Exploration, consideration |
| `product_id`, `product_name`, `variant_id` | Entity / Dimension | Product-level fit |
| `height`, `weight`, body measurements, `preferred_fit` | Dimension (user context) | Aggregated only; no PII to brands |
| `country`, `city` | Dimension | Regional fit curves |

**Derived variables (calculation map):**

| Derived | Formula / Logic | Raw inputs |
|---------|-----------------|------------|
| Recommended = Purchased | `size_recommended == size_purchased` (binary) | size from events |
| Recommendation Acceptance Rate | `count(match) / count(recommendations)` | size_recommended, size_selected or purchased |
| Size view/selection/purchase distributions | `group by size, count` | size, event_type |
| Size exploration entropy | Diversity of sizes_viewed per session | sizes_viewed[] |
| Sizes viewed but not purchased | Session had size_viewed, no purchase for that size | event_type, size |
| Regional fit curves | Size demand by country/city | size, country, city, product_id |

---

### 3.3 Category C — Trend & Demand Forecasting

**Goal:** Surface early trend and fit shifts for buying teams.

**Raw datapoints → Dimensions / Measures:**

| Raw | Role | Used in |
|-----|------|---------|
| `tryons_started`, `unique_sessions`, `unique_users` | Measure (aggregated) | Velocity |
| `created_at`, `date` | Dimension (time) | Trends, momentum |
| `product_id`, `brand_id`, `country`, `city` | Dimension | Product/region trends |
| `sizes_viewed[]`, `size_selected`, `size_purchased` | Dimension / Measure | Fit interaction |

**Derived variables (calculation map):**

| Derived | Formula / Logic | Raw inputs |
|---------|-----------------|------------|
| TryOn velocity | `count(tryon_started)` over rolling window (e.g. 7d) | event_type, created_at |
| Purchase velocity | `count(purchase)` over rolling window | event_type, created_at |
| High try-on / low purchase SKUs | `tryons / purchases` by product; flag if ratio high | product_id, event_type |
| Rising size exploration | Entropy or count(sizes_viewed) over time | sizes_viewed[], created_at |
| Size stress | Sizes with high interest, low conversion | size, event_type, product_id |
| Regional size divergence | Size demand differs by region | size, country, city |
| Declining recommendation acceptance | Acceptance rate over time | size_recommended, size_purchased, created_at |
| Fit drift | Increasing exploration entropy over time | sizes_viewed[], created_at |

---

## 4. Variable → Category → Calculation Matrix

| Variable | Category A (ROI) | Category B (Fit) | Category C (Trend) |
|----------|------------------|------------------|--------------------|
| `user_id` | Attribution | — | Cohorts |
| `session_id` | Attribution, funnel | Session-level fit | — |
| `brand_id`, `shop_domain` | ROI by brand | — | Trend by brand |
| `product_id`, `product_name` | Revenue by product | Fit by product | Trend by product |
| `variant_id` | — | Variant-level | — |
| `order_id` | Attribution | — | — |
| `event_type` | Funnel | Size events | Velocity |
| `size` (all) | — | Core | Trend |
| `sizes_viewed[]` | — | Exploration | Fit drift |
| `amount`, `currency` | Revenue, AOV | — | — |
| `country`, `city` | Regional ROI | Regional fit | Regional trend |
| `created_at`, `date` | Time_to_Purchase | — | Velocity, drift |
| Body measurements | — | Aggregated fit context | — |

---

## 5. Best File Type to Save Data

### Recommendation: **Hybrid — Postgres + Parquet**

| Layer | Format | Purpose |
|-------|--------|---------|
| **Primary (operational)** | PostgreSQL (Supabase) | Real-time event ingestion, API, app, dashboard queries |
| **Analytical (quant)** | Parquet | Batch exports for quant, ML, heavy aggregations |

### Why Parquet for analytical layer

- **Columnar:** Queries often need specific columns (e.g. `amount`, `event_type`, `country`); columnar = fewer I/O.
- **Compression:** ~5× smaller than JSON; lower storage and transfer cost.
- **Performance:** 35–74× faster than JSON for typical analytics queries.
- **Schema evolution:** Supports adding columns over time.
- **Ecosystem:** Works with DuckDB, Pandas, Spark, Supabase Analytics Buckets.

### Export pipeline options

1. **Supabase Analytics Buckets** — Native replication from Postgres to Iceberg/Parquet; real-time.
2. **ETL (Airbyte, Estuary)** — Postgres → S3 Parquet; configurable schedule.
3. **Custom batch job** — Nightly export of `analytics_events`, `analytics_daily` to Parquet in S3 or GCS.

### File naming and partitioning

- **Path pattern:** `analytics/events/year=YYYY/month=MM/day=DD/events.parquet`
- **Partitioning:** By `date` (or `created_at::date`) for efficient time-range queries. Avoid small files (<128MB); coalesce if needed.
- **Compression:** Snappy (default for Parquet); splittable for parallel processing.
- **Grain:** One file per day per `brand_id` if volume warrants; else one file per day with `brand_id` as column.
- **Timezone:** Use UTC consistently; convert for brand TZ only at dashboard display.

### When to use CSV

- **Brand-facing exports:** Dashboard "Export" button → CSV for spreadsheets.
- **Ad-hoc sharing:** Human-readable; not for primary quant storage.

---

## 6. Data Flow Summary & Visualization

See **[DATA_FLOW_SUMMARY.md](./DATA_FLOW_SUMMARY.md)** for a concise summary and Mermaid diagrams of the full flow: Sources → Capture → Ingest → Storage → Aggregate → Consume.

---

## 7. Summary: Categorise → Variables → Calculations → Storage

| Step | Output |
|------|--------|
| **1. Categorise** | A (ROI), B (Fit), C (Trend), Cross-cutting (joins, quality) |
| **2. Variables per category** | Raw datapoints → Dimensions / Measures / Entities (see Section 3) |
| **3. Calculations** | Derived variable trees with formulas (see Section 3.1–3.3) |
| **4. Storage** | Postgres (operational) + Parquet export (analytical); CSV for brand exports |

---

## 8. Next Steps (When Quant Friend Replies)

1. **Validate** categorization and derived variables with quant.
2. **Prioritise** which calculations to implement first (backend).
3. **Resolve schema alignment** (Section 2b) — brand_id, product_id, country, city on events.
4. **Wire events** — frontend `trackEvent` + backend region enrichment.
5. **Define** Parquet schema and export cadence (hourly/daily).
6. **Map** derived variables → dashboard visualisations.
7. **Implement** daily aggregation job → `analytics_daily`; Shopify webhook for purchases.

---

*Research sources: Northbeam, IAB, Lifesight, Fytted, IBM Research, arXiv fashion forecasting, Virtusize, Uwear.ai, MIT OR/MS, Appit, Toolio, Antuit, o9 Solutions, Clarkston Consulting, AWS Well-Architected, Supabase Analytics, Parquet benchmarks. Last updated: Jan 2026.*
