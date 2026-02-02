# Category C — Trend & Demand Forecasting: Implementation Roadmap

**Purpose:** Step-by-step plan for implementing Category C (Trend & Demand Forecasting). Defines, for every variable and data point: where data comes from, how we label/encode it, and the implementation order.

**Reference:** [DATA_FLOW_SUMMARY.md](../DATA_FLOW_SUMMARY.md), [QUANT_DATA_STRATEGY.md](../QUANT_DATA_STRATEGY.md), [IMPLEMENTATION_ROADMAP_CATEGORY_A.md](./IMPLEMENTATION_ROADMAP_CATEGORY_A.md), [IMPLEMENTATION_ROADMAP_CATEGORY_B.md](./IMPLEMENTATION_ROADMAP_CATEGORY_B.md), [MATHEMATICAL_OPTIMIZATION.md](./MATHEMATICAL_OPTIMIZATION.md).

---

## 1. Category C — Structure

**Goal:** Surface early trend and fit shifts for buying teams.

### 1.1 Derived Variable Tree

| Branch | Variable | Formula / Logic |
|--------|----------|-----------------|
| **Demand Momentum** | TryOn velocity | `count(tryon_started)` over rolling window (e.g. 7d) |
| **Demand Momentum** | Purchase velocity | `count(purchase)` over rolling window |
| **Early Warning** | High try-on / low purchase SKUs | Flag products where tryons / purchases ratio exceeds threshold |
| **Early Warning** | Rising size exploration | Increasing entropy or count(sizes_viewed) over time |
| **Size Stress** | Sizes with interest but low conversion | High views/selection, low purchases for that size |
| **Size Stress** | Regional size divergence | Size demand differs by region |
| **Fit Drift** | Declining recommendation acceptance | Acceptance rate ↓ over time |
| **Fit Drift** | Increasing exploration entropy over time | Entropy ↑ over time |
| **Preferred Fit (segment)** | All above, by fit preference | Velocity, early warning, trends by preferred_fit. Preferred fit distribution over time: is the mix of slim/regular/loose shifting? |
| **Lag indicator** | TryOn-to-Purchase velocity ratio | `purchase_velocity / tryon_velocity` over same window. Lag and conversion momentum. |

---

## 2. Data Points → Variables → Implementation

### 2.1 Demand Momentum Branch

#### Variable: TryOn velocity

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| `tryon_started` count | Events | `analytics_events` WHERE `event_type='tryon_started'` | **None.** Count. | |
| `created_at` | Events | `analytics_events.created_at` | **TIMESTAMPTZ UTC.** | For time window |
| Rolling window | Config | e.g. 7 days | **Days (integer).** | |

**Formula:**  
`COUNT(DISTINCT session_id)` or `COUNT(*)` WHERE `event_type='tryon_started'` AND `created_at >= :window_start`.  
*(Sessions = unique try-on starts; raw count = total try-on interactions. Use sessions for "reach," raw for "engagement.")*

**Smoothing (best math):** **EWMA** (Exponential Weighted Moving Average): `y_t = α·x_t + (1-α)·y_{t-1}`. α ≈ 0.2–0.3. Smoother trend lines. See [MATHEMATICAL_OPTIMIZATION.md](./MATHEMATICAL_OPTIMIZATION.md) §4.1.

**Encoding for time:**
- Store `created_at` as UTC. All aggregations in UTC.
- Rolling window: `created_at >= (end_date - window_days)`. Window options: 1d, 7d, 14d, 30d.
- For **velocity trend** (velocity over time): compute velocity per day, then plot time series. E.g. velocity_day_t = count on day t; or rolling sum centered on t.

**Implementation steps:**
1. Query: count tryon_started in date range.
2. Support configurable window (7d default).
3. Dashboard: single number (current velocity) or time series (velocity per day).

---

#### Variable: Purchase velocity

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| `purchase` count | Events | Same pattern | Same | |
| `created_at` | Same | Same | Same | |

**Formula:**  
Same as TryOn velocity, with `event_type='purchase'`.

**Implementation steps:**
1. Same as TryOn velocity.
2. Optional: plot both on same chart (TryOn vs Purchase velocity) for lag insight.

---

### 2.2 Early Warning Branch

#### Variable: High try-on / low purchase SKUs

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| `tryon_started` count | Events | Per `product_id` | Count | |
| `purchase` count | Events | Per `product_id` | Count | |
| `product_id` | Event context | `analytics_events.product_id` | Text as-is | |

**Formula:**  
For each product: `ratio = tryons / NULLIF(purchases, 0)`; when purchases=0, ratio = ∞.  
`conversion = purchases / NULLIF(tryons, 0)`.  
**Flag if:** `tryons >= min_tryons` (e.g. 5) AND (`purchases = 0` OR `conversion < threshold` e.g. 0.05). Minimum tryons avoids flagging new/untested SKUs.

**Encoding:**  
No encoding. Ratio is numeric. Threshold and min_tryons are configurable.

**Implementation steps:**
1. Aggregate by product_id: count tryon_started, count purchase.
2. Compute ratio or conversion.
3. Filter: products where ratio > X or conversion < Y.
4. Dashboard: table of "at-risk" SKUs. Sort by ratio desc.

---

#### Variable: Rising size exploration

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| `sizes_viewed[]` or `size_viewed` events | Events / sessions | Same as Category B | Same | |
| `created_at` / `date` | Events | `analytics_events.created_at` | TIMESTAMPTZ | |
| Entropy (from B) | Derived | Per session, per time bucket | Numeric | |

**Formula:**  
- **Option A:** Avg count(sizes_viewed) per session, by week. Plot over time. Rising = more exploration.
- **Option B:** Avg entropy per session, by week. Rising = more uncertainty (fit drift).

**Implementation steps:**
1. Reuse Category B entropy or sizes_viewed count.
2. Bucket by week (or day): `date_trunc('week', created_at)`.
3. Compute metric per bucket. Plot time series.
4. Flag if slope is positive and significant (optional: simple diff or linear regression).

---

### 2.3 Size Stress Branch

#### Variable: Sizes with interest but low conversion

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| `size` (viewed/selected) | Events | `event_data->>'size'` | Same as B | |
| `size` (purchased) | Purchase | Same | Same | |
| `product_id` | Events | Same | Same | |

**Logic:**  
Per (product_id, size): count views, count purchases. Flag sizes where views >> purchases (e.g. views > 5× purchases, and views > 10). Indicates size may be mis-fit or allocation issue.

**Implementation steps:**
1. Aggregate: `product_id`, `size`, count(size_viewed + size_selected), count(size_purchased).
2. Filter: high interest (views/selection) + low conversion (purchases).
3. Dashboard: table of (product, size) with "stress" score or flag.

---

#### Variable: Regional size divergence

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| `size` | Events | Same | Same | |
| `country` | Events | Same | Same | ISO 3166-1 |
| `city` | Events | Same | Same | |

**Logic:**  
Compare size distribution across regions. E.g. "US: 40% M, 35% L; EU: 50% M, 25% L." Divergence = distributions differ.

**Best math — Jensen-Shannon divergence:** JSD(P,Q) between region size distributions. Symmetric, bounded 0–ln(2). High JSD = regions buy different sizes. Better than chi-squared for sparse data. See [MATHEMATICAL_OPTIMIZATION.md](./MATHEMATICAL_OPTIMIZATION.md) §3.5. Fallback: % diff or chi-squared when sample ≥ 5 per cell.

**Encoding:**  
No new encoding. Use size and country as dimensions. Output: table or heatmap.

**Implementation steps:**
1. Aggregate: country × size, count.
2. Compute % per size per country.
3. Compare distributions (manual or chi-sq).
4. Dashboard: side-by-side bar charts or heatmap (country × size).

---

### 2.4 Fit Drift Branch

#### Variable: Declining recommendation acceptance over time

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| Recommendation Acceptance Rate | Category B | Same | Same | |
| `date` / `created_at` | Events | Same | Same | |

**Logic:**  
Compute acceptance rate per week (or month). Plot over time. Declining = fit model may need recalibration.

**Implementation steps:**
1. Reuse Category B acceptance rate.
2. Compute per time bucket (week/month).
3. Plot time series. Flag if recent < previous period.

---

#### Variable: Increasing exploration entropy over time

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| Size exploration entropy | Category B | Same | Same | |
| `date` / `created_at` | Same | Same | Same | |

**Logic:**  
Same as "Rising size exploration" — entropy over time. Increasing = users less confident in recommendation.

**Implementation steps:**
1. Same as 2.2 "Rising size exploration" (Option B).

---

## 3. Time Encoding — Deep Specification

Category C is time-centric. All variables depend on `created_at` or `date`.

### 3.1 Time Storage

| Field | Type | Encoding | Notes |
|-------|------|----------|-------|
| `created_at` | TIMESTAMPTZ | UTC | Per event |
| `date` | DATE | Calendar date (UTC or brand TZ) | In analytics_daily |

### 3.2 Time Buckets for Trends

| Bucket | SQL | Use case |
|--------|-----|----------|
| Day | `date_trunc('day', created_at)` | Daily series |
| Week | `date_trunc('week', created_at)` (Monday start) | Weekly trends |
| Month | `date_trunc('month', created_at)` | Monthly |
| Quarter | `date_trunc('quarter', created_at)` | Quarterly |

**Week start:** Define explicitly (Monday vs Sunday). Recommend Monday for B2B.

### 3.3 Rolling Windows

| Window | Definition | Use |
|--------|------------|-----|
| 7d | Last 7 full days | TryOn velocity, Purchase velocity |
| 14d | Last 14 days | Smoother trend |
| 30d | Last 30 days | Monthly momentum |

**Boundary:**  
- **Include today:** "Live" feel; counts may rise through the day. Use for real-time dashboard.  
- **Through yesterday:** Stable; aligns with batch jobs. Use for reported KPIs.  
Document the choice. For velocity trend charts, use calendar days (full days only) to avoid partial-day bias.

---

## 4. Cross-Cutting Data Points for Category C

| Data point | Type | Encoding / Label | Notes |
|------------|------|------------------|-------|
| `tryons_started` | Count | Pre-aggregated in analytics_daily | |
| `unique_sessions` | Count | Same | |
| `unique_users` | Count | Same | |
| `created_at` | Timestamp | UTC | |
| `date` | Date | Calendar | |
| `product_id` | Text | As-is | |
| `brand_id` | UUID | As-is | |
| `country`, `city` | Text | ISO / as-is | |
| `size` | Text | Same as B | |
| `sizes_viewed[]` | Array | Same as B | |
| `preferred_fit` | Text | slim / regular / loose | Segment. From fit_passport. |

---

## 5. Schema Requirements for Category C

### 5.1 Uses Existing Tables

- `analytics_events` — for raw counts, product_id, size, country, created_at
- `analytics_daily` — for pre-aggregated tryons, purchases, unique_sessions, date

### 5.2 Optional: Time-Series Materialized View

| Purpose | Structure |
|---------|-----------|
| Daily metrics per product | `(date, product_id, tryons, purchases, ...)` |
| Daily metrics per region | `(date, country, tryons, purchases, ...)` |

Speeds up velocity and trend queries. Populate from batch job.

---

## 6. Implementation Order

| Phase | Task | Output |
|-------|------|--------|
| **1. Prerequisites** | Category A (events) and B (size, entropy) in place | — |
| **2. Velocity** | TryOn and Purchase velocity queries (rolling window) | KPIs |
| **3. High try-on / low purchase** | Product-level ratio, flag threshold | SKU alert table |
| **4. Rising exploration** | Entropy or sizes_viewed count over time buckets | Time series |
| **5. Size stress** | Product × size interest vs conversion | Stress table |
| **6. Regional divergence** | Country × size distribution | Heatmap data |
| **7. Fit drift** | Acceptance rate + entropy over time | Trend charts |
| **8. Dashboard** | Wire all to dashboard with time filters | Full Category C viz |

---

## 7. Encoding Summary (Quick Reference)

| Data point | Encoding | Use in equations? |
|------------|----------|-------------------|
| `created_at` | TIMESTAMPTZ UTC | Yes. Buckets, windows. |
| `date` | DATE | Yes. Grouping. |
| `product_id` | Text | Group/filter. |
| `brand_id` | UUID | Group/filter. |
| `country`, `city` | ISO / Text | Group/filter. |
| `size` | Same as B | Group. |
| `preferred_fit` | slim / regular / loose | Segment. |
| Counts | Integer | Yes. Ratios, velocity. |
| Entropy | Numeric (from B) | Yes. Trend. |

---

## 8. Dependencies

| Category C Variable | Depends On |
|---------------------|------------|
| TryOn velocity | Category A (tryon_started events) |
| Purchase velocity | Category A (purchase events) |
| High try-on / low purchase | Category A (events, product_id) |
| Rising size exploration | Category B (sizes_viewed, entropy) |
| Size stress | Category B (size in events) |
| Regional divergence | Category B (size, country) |
| Declining acceptance | Category B (acceptance rate) |
| Fit drift (entropy) | Category B (entropy) |

**Order:** Implement A first, then B, then C. C reuses A and B outputs.

---

---

## 9. Review & Algorithm Specification (Post-Research)

*Added after research review. Corrects potential errors and specifies best-practice algorithms.*

### 9.1 Corrections & Clarifications

| Issue | Correction |
|-------|------------|
| **Velocity: sessions vs count** | `COUNT(DISTINCT session_id)` = reach (unique try-ons). `COUNT(*)` = engagement (total interactions). Report both; document which is primary. |
| **High try-on / low purchase: zero purchases** | When purchases=0, ratio = ∞. Add **min_tryons** threshold (e.g. 5) to avoid flagging new SKUs with no data. |
| **Rolling window small samples** | Use `min_periods` when computing rolling metrics: require minimum N observations before returning value; else NULL. Avoids noisy early-period estimates. |
| **Regional divergence: chi-squared** | Requires expected freq ≥ 5 per cell. For sparse data, use % comparison or defer statistical test. |
| **Fit drift: significance** | **Linear regression slope:** Fit y = β₀ + β₁·t over time buckets. Flag only if |β₁| > threshold AND R² > 0.3. Avoid over-interpreting noise. See [MATHEMATICAL_OPTIMIZATION.md](./MATHEMATICAL_OPTIMIZATION.md) §4.2. |

### 9.2 Canonical Algorithms

**TryOn velocity (rolling, with min_periods):**
```sql
-- Daily counts, then rolling sum. min_periods = 1 for partial windows.
SELECT date, SUM(tryons) OVER (
  ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
) AS velocity_7d
FROM analytics_daily
WHERE date >= :start_date;
```

**High try-on / low purchase (with thresholds):**
```sql
SELECT product_id, tryons, purchases,
       tryons::FLOAT / NULLIF(purchases, 0) AS ratio,
       purchases::FLOAT / NULLIF(tryons, 0) AS conversion
FROM (
  SELECT product_id,
         COUNT(*) FILTER (WHERE event_type='tryon_started') AS tryons,
         COUNT(DISTINCT order_id) FILTER (WHERE event_type='purchase') AS purchases
  FROM analytics_events
  WHERE created_at BETWEEN :start AND :end
  GROUP BY product_id
) t
WHERE tryons >= 5  -- min_tryons
  AND (purchases = 0 OR purchases::FLOAT / NULLIF(tryons, 0) < 0.05);
```

**Rising exploration (slope over time):**
```sql
-- Compute avg entropy per week, then compare recent vs prior.
WITH weekly AS (
  SELECT date_trunc('week', created_at) AS week, AVG(entropy) AS avg_entropy
  FROM per_session_entropy GROUP BY 1
)
SELECT week, avg_entropy,
       avg_entropy - LAG(avg_entropy) OVER (ORDER BY week) AS entropy_change
FROM weekly;
```

### 9.3 Edge Cases

| Edge case | Handling |
|-----------|----------|
| Product with 0 tryons | Exclude from high try-on / low purchase. |
| Sparse days (0 events) | Velocity = 0 for that day. Rolling window includes zeros. |
| Single region | Regional divergence N/A. Show distribution only. |
| Short time series (< 2 periods) | Cannot compute trend; show raw values. |

---

## 10. Senior Research Review (2040 Standard)

*Rigorous improvements from an enterprise analytics perspective.*

### 10.1 Statistical Rigor

| Improvement | Detail |
|-------------|--------|
| **Trend significance** | For "rising" or "declining": require at least 2 periods of data. Optional: simple linear regression slope; flag only if |slope| > threshold and R² reasonable. Avoid over-interpreting noise. |
| **Velocity: year-over-year** | For seasonal products, compare to same period last year (YoY) not just prior period. Add when we have 12+ months data. |
| **Confidence for sparse products** | High try-on / low purchase: when tryons < 10, flag "Low confidence" in UI. Ratio can be noisy. |

### 10.2 Time-Series Robustness

| Improvement | Detail |
|-------------|--------|
| **Exclude partial current period** | For "MTD" or "this week", either include today (live) or exclude (stable). Document. For trend charts, use complete periods only to avoid partial-day bias. |
| **Week definition** | ISO week (Monday start) for B2B. Configurable. |
| **min_periods for rolling** | When computing rolling velocity, use min_periods=1 for first day, else NaN. Or use min_periods=7 and accept NaN for first 6 days. Document. |

### 10.3 Early Warning: Actionable Thresholds

| Improvement | Detail |
|-------------|--------|
| **Configurable thresholds** | min_tryons (default 5), conversion_threshold (default 0.05). Store in config; allow brand override. |
| **Severity tiers** | Flag products as "Critical" (0 purchases, 10+ tryons), "Warning" (conversion < 5%), "Watch" (conversion 5–10%). Actionable prioritisation. |
| **Exclude discontinued** | If product is out of stock or discontinued, don't flag. Requires product status from Shopify. Future. |

### 10.4 Fit Drift: Definition

| Improvement | Detail |
|-------------|--------|
| **"Declining" definition** | Acceptance rate in period T < acceptance in period T-1. Or: 3-period moving average declining. Document. |
| **Minimum periods for drift** | Require at least 4 weeks (or 2 months) of data before computing drift. Avoid false signals from launch variance. |
| **Segment by product** | Fit drift may be product-specific (new product, bad size chart). Add product filter for drill-down. |

### 10.5 Semantic Contracts

| Term | Definition |
|------|------------|
| **Velocity** | Count of events in rolling window. Use DISTINCT session_id for tryon velocity (reach). |
| **High try-on / low purchase** | Product where tryons ≥ min_tryons AND (purchases=0 OR conversion < threshold). |
| **Fit drift** | Time series of acceptance rate or entropy; "declining" or "rising" per defined rule. |
| **Regional divergence** | Size distribution differs across regions. Use % diff or chi-sq when sample sufficient. |

### 10.6 Missing: Velocity Ratio (TryOn-to-Purchase Lag)

| Variable | Formula | Why add |
|----------|---------|---------|
| **TryOn-to-Purchase velocity ratio** | `purchase_velocity_7d / tryon_velocity_7d` | Lag indicator. If ratio < 1, purchases lag tryons (expected). If declining over time, may signal conversion slowdown. |

---

*Foundation only. No code yet. Ready for implementation when A and B are in place.*
