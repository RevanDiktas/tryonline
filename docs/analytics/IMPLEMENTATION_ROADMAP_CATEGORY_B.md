# Category B — Fit Accuracy & Buying Decisions: Implementation Roadmap

**Purpose:** Step-by-step plan for implementing Category B (Fit Accuracy & Buying Decisions). Defines, for every variable and data point: where data comes from, how we label/encode it, and the implementation order.

**Reference:** [DATA_FLOW_SUMMARY.md](../DATA_FLOW_SUMMARY.md), [QUANT_DATA_STRATEGY.md](../QUANT_DATA_STRATEGY.md), [IMPLEMENTATION_ROADMAP_CATEGORY_A.md](./IMPLEMENTATION_ROADMAP_CATEGORY_A.md), [MATHEMATICAL_OPTIMIZATION.md](./MATHEMATICAL_OPTIMIZATION.md).

---

## 1. Category B — Structure

**Goal:** Optimize size buying, allocation, and recommendation quality.

### 1.1 Derived Variable Tree

| Branch | Variable | Formula / Logic |
|--------|----------|-----------------|
| **Recommendation Quality** | Recommended = Purchased | Binary: `size_recommended == size_purchased` per session |
| **Recommendation Quality** | Recommendation Acceptance Rate | `count(match) / count(recommendations)` |
| **Size Demand** | Size view/selection/purchase distributions | `GROUP BY size, COUNT` per event type |
| **Fit Confidence** | Number of sizes viewed | `COUNT(DISTINCT sizes_viewed[])` per session |
| **Fit Confidence** | Size exploration entropy | Shannon entropy of sizes viewed per session |
| **Misfit Signals** | Sizes viewed but not purchased | Session had size_viewed, no purchase for that size |
| **Misfit Signals** | Size selected but not purchased | Session had size_selected, no purchase |
| **Regional Fit Curves** | Size demand by country/city | Size distribution `GROUP BY country`, `GROUP BY city` |
| **Recommendation quality** | Mean Absolute Size Error (MASE) | `(1/n) Σ \|ordinal_purchased - ordinal_recommended\|` | Continuous fit quality. **Requires ordinal encoding.** |
| **Preferred Fit (segment)** | All above, by fit preference | Same formulas, `GROUP BY preferred_fit`. Acceptance rate, size demand, size-up/down behaviour by slim / regular / loose. Core for personalisation. |
| **Size up/down** | Size up rate, Size down rate | Ordinal difference: selected − recommended. Positive = size up, negative = size down. % each. **Requires ordinal.** |

---

## 2. Data Points → Variables → Implementation

### 2.1 Recommendation Quality Branch

#### Variable: Recommended = Purchased (binary)

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| `size_recommended` | Event | `analytics_events` WHERE `event_type='size_recommended'`, `event_data->>'size'` | **Ordinal or string match.** See Section 3. | Per session (last or first) |
| `size_purchased` | Purchase event | `purchase` event; from order line item. `event_data->>'size'` or line item | Same encoding as recommended | Must extract from webhook |

**Encoding for size comparison:**
- **Option A (string):** Store as-is (`S`, `M`, `L`). Compare with `LOWER(TRIM())` for consistency. Works when labels match exactly.
- **Option B (ordinal):** Map to numeric. Same ordinal = match. Handles `S` vs `Small` if we normalize first.
- **Recommended:** Store raw `size` (TEXT). For match: normalize to canonical form (e.g. uppercase, trim), then compare. Use ordinal only when computing "size up/down" (e.g. selected M, recommended S → size up).

**Implementation steps:**
1. Fire `size_recommended` with `size` in `event_data` when fit is computed.
2. Webhook extracts size from order line item (Shopify: `line_item.variant_title` or custom property). Store in `purchase` event `event_data`.
3. Join session: get `size_recommended` and `size_purchased` per session. Compare.

---

#### Variable: Recommendation Acceptance Rate

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| Match count | Derived | Sessions where `size_recommended == size_purchased` | Binary aggregate | |
| Recommendation count | Derived | Sessions with `size_recommended` AND `purchase` | Denominator | Exclude sessions without purchase |

**Formula:**  
`COUNT(sessions WHERE size_recommended = size_purchased) / NULLIF(COUNT(sessions WHERE size_recommended AND purchase), 0)`

**Implementation steps:**
1. Same as Recommended = Purchased.
2. Aggregate: count matching sessions / total sessions with both recommendation and purchase.

---

#### Variable: Mean Absolute Size Error (MASE)

*Best-in-class ordinal metric. Requires size ordinal encoding. See [MATHEMATICAL_OPTIMIZATION.md](./MATHEMATICAL_OPTIMIZATION.md).*

| Data point | Source | Encoding | Notes |
|------------|--------|----------|-------|
| `ordinal_recommended` | size_recommended | Via size_ordinal_map | Per (session, product) |
| `ordinal_purchased` | size_purchased | Same | Same |

**Formula:** `MASE = (1/n) Σ |ordinal_purchased - ordinal_recommended|` over sessions with both.

**Output:** Avg "size steps" off. 0 = perfect. 0.5 = half a size off on average. Enables continuous fit quality (not just binary).

**When sizes are imbalanced:** Use **macroaveraged MAE** — compute MAE per size class, then average. Robust to M dominating.

---

### 2.2 Size Demand Branch

#### Variable: Size view/selection/purchase distributions

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| `size` | Events | `event_data->>'size'` | **Store TEXT.** For distribution: group by raw value. For ordering: use ordinal. | |
| `event_type` | Events | `analytics_events.event_type` | Filter: `size_viewed`, `size_selected`, `size_purchased` | |

**Encoding for size in distributions:**
- **Display:** Use raw labels (`S`, `M`, `L`, `32`, `34`, etc.). Bar chart shows counts per size.
- **Ordering (chart axis):** Use **ordinal encoding** so bars appear in logical order (XS→S→M→L→XL, or numeric 32→34→36). Create lookup: `size_ordinal` per product/category.
- **Cross-product:** Sizes vary by product. Option: (a) product-specific ordinals, (b) generic mapping for letter sizes, (c) store as-is, sort at display time.

**Ordinal lookup (example):**

| size_raw | size_ordinal (letter) | size_ordinal (numeric) |
|----------|------------------------|------------------------|
| XS, XXS  | 0 | — |
| S        | 1 | — |
| M        | 2 | — |
| L        | 3 | — |
| XL, XXL  | 4 | — |
| 30       | — | 30 |
| 32       | — | 32 |
| 34       | — | 34 |
| 36       | — | 36 |
| ...      | — | ... |

Store in config table or JSON. Apply when building charts. Unknown sizes: append at end or use max+1.

**Implementation steps:**
1. Ensure `size_viewed`, `size_selected` fire with `size` in `event_data`.
2. Ensure `purchase` includes per-line-item size.
3. Query: `SELECT event_data->>'size' AS size, event_type, COUNT(*) FROM analytics_events WHERE event_type IN (...) GROUP BY 1, 2`.
4. Dashboard: bar chart, ordered by `size_ordinal` when available.

---

### 2.3 Fit Confidence Branch

#### Variable: Number of sizes viewed per session

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| `sizes_viewed[]` | Session or events | `tryon_sessions.sizes_viewed` or aggregate from `size_viewed` events | **Array of TEXT.** Count distinct. | |
| `session_id` | Events | `analytics_events.session_id` | UUID as-is | |

**Logic:**  
Per session: count distinct sizes in `sizes_viewed` (or count of `size_viewed` events with distinct size).  
Aggregate: avg per session, or distribution (how many sessions viewed 1, 2, 3+ sizes).

**Implementation steps:**
1. Option A: `tryon_sessions.sizes_viewed` — append on each `size_viewed` (dedupe).  
2. Option B: From events — `SELECT session_id, COUNT(DISTINCT event_data->>'size') FROM analytics_events WHERE event_type='size_viewed' GROUP BY session_id`.
3. Use Option B if we don't persist to tryon_sessions; ensures single source of truth.

---

#### Variable: Size exploration entropy

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| `sizes_viewed[]` | Same as above | Same | Same | Per session |
| Proportion per size | Derived | `p_i` = count of sessions that viewed size i / total sessions | For entropy | |

**Formula (Shannon entropy):**  
`H = -Σ(p_i × ln(p_i))` where `p_i` = proportion. **By convention, 0×ln(0) = 0** — skip or treat p_i=0 as zero contribution.  
- **Per-session entropy (preferred for fit drift):** p_i = 1/k for each of k sizes viewed in that session (equal weight). E.g. [S, M, L] → p_i = 1/3 each → H = ln(3) ≈ 1.1. Single size → H = 0.  
- **Cross-session entropy:** p_i = proportion of all size-view events that were size i (across sessions). Use for "which sizes get attention."

**Normalized entropy (0–1):**  
`E_H = H / ln(k)` where k = number of unique sizes in the set. 1 = even; 0 = focused on one. Use when comparing across different k.

**Encoding:**  
Sizes stay as labels for computing p_i. No encoding needed for entropy itself; output is numeric.

**Implementation steps:**
1. Get per-session `sizes_viewed` (array or aggregated from events).
2. Compute H per session: for each session, p_i = 1/len(sizes_viewed) for each size (equal weight), or weight by view count.
3. Aggregate: avg entropy per session over time window. Or: single entropy across all sessions (p_i = global proportion of views per size).
4. Track over time for "fit drift" (rising entropy = more uncertainty).

---

### 2.4 Misfit Signals Branch

#### Variable: Sizes viewed but not purchased

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| `sizes_viewed` | Events | `size_viewed` events per session | Same | |
| `size_purchased` | Purchase | Same as above | Same | |
| `session_id` | Events | Same | Same | |

**Logic:**  
Sessions where: (a) had at least one `size_viewed`, (b) had `purchase`, (c) `size_purchased` NOT IN `sizes_viewed`.  
Or: list of sizes that were viewed (across all sessions) but never purchased. Aggregate by product/size.

**Implementation steps:**
1. Join sessions with size_viewed and purchase.
2. For each session: if `size_purchased` not in `sizes_viewed`, flag. Or: for each (product, size), count views vs purchases; flag if views >> purchases and few purchases.

---

#### Variable: Size selected but not purchased

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| `size_selected` | Event | `size_selected` with `event_data->>'size'` | Same | |
| `purchase` | Event | Same | Same | Per session |

**Logic:**  
Sessions with `size_selected` but no `purchase` in that session. Count or % of sessions that selected but didn't buy.

**Implementation steps:**
1. Sessions with `size_selected` event.
2. Left join to `purchase` on session_id.
3. Count where purchase is null.

---

### 2.5 Regional Fit Curves Branch

#### Variable: Size demand by country/city

| Data point | Source | Table/Column | Encoding / Label | Notes |
|------------|--------|--------------|------------------|-------|
| `size` | Events | Same | Same | |
| `country` | Event context | `analytics_events.country` | **ISO 3166-1 alpha-2.** | |
| `city` | Event context | `analytics_events.city` | Text as-is | |
| `product_id` | Event context | `analytics_events.product_id` | Text as-is | |

**Logic:**  
`GROUP BY country, size` (or city, product_id). Show distribution of size demand per region. Enables "EU prefers M, US prefers L" etc.

**Regional divergence (best math):** Use **Jensen-Shannon divergence** between size distributions (P for region A, Q for region B). Symmetric, bounded 0–ln(2). High JSD = regions buy different sizes. Better than chi-squared for sparse data. See [MATHEMATICAL_OPTIMIZATION.md](./MATHEMATICAL_OPTIMIZATION.md) §3.5.

**Encoding:**  
- `country`: ISO 3166-1 alpha-2. For display: use full name. For grouping: code is sufficient.  
- `city`: Free text. Normalize (trim, title case) for grouping. Watch for duplicates (e.g. "New York" vs "new york").

**Implementation steps:**
1. Ensure `country`, `city` on all events (from user or IP).
2. Query: `SELECT country, event_data->>'size' AS size, COUNT(*) FROM analytics_events WHERE event_type IN ('size_selected','size_purchased') GROUP BY 1, 2`.
3. Dashboard: stacked bar or heatmap (country × size).

---

## 3. Size Encoding — Deep Specification

**Problem:** Sizes like `S`, `M`, `32`, `34` cannot go directly into mathematical operations. We need a consistent encoding strategy.

### 3.0 Preferred Fit — User Preference

**What it is:** Shopper preference for how clothes fit: slim, regular, or loose/oversized. Stored in `fit_passports.preferred_fit`.

**Why it matters:** Someone who likes slim t-shirts may size down; someone who likes oversized pants may size up. Recommendation should consider preferred_fit (e.g. suggest size up for "loose" preferrers on certain garments). *Implementation of recommendation logic (widget detects product fit type, applies preference) comes later.* For analytics: we segment all fit metrics by preferred_fit so brands see "slim preferrers accept our recs at X%, loose at Y%."

**Future:** Per-garment preference (slim tops, loose bottoms). Schema would add `preferred_fit_tops`, `preferred_fit_bottoms` or similar. Default: single `preferred_fit` for now.

### 3.1 When to Encode

| Use case | Encoding needed? | Approach |
|----------|------------------|----------|
| **Comparison (recommended = purchased)** | Optional | String compare (normalize case/trim). Ordinal only for "size up/down". |
| **Distribution (bar chart)** | Display: no. Ordering: yes | Ordinal lookup for axis order. |
| **Entropy** | No | Proportions work on counts; size is categorical. |
| **Regional curves** | No | Group by raw size. |
| **Size up/down analysis** | Yes | Ordinal: selected - recommended. Positive = size up. |
| **Regression / ML (future)** | Yes | Ordinal or one-hot. |

### 3.2 Ordinal Encoding Scheme

**Letter sizes (generic):**

```
XXS=0, XS=1, S=2, M=3, L=4, XL=5, XXL=6, XXXL=7
```

**Numeric sizes (e.g. waist, inseam):**

```
Store as integer. 28, 30, 32, 34, 36 → use value directly for ordering.
```

**Product-specific:**  
If a product uses nonstandard sizes (e.g. "P", "G", "1", "2"), create a product-specific mapping table. Default: store as-is, ordinal = NULL; sort alphabetically at display.

### 3.3 Normalization Before Encoding

1. **Trim** whitespace.
2. **Uppercase** for letter sizes (S, M, L).
3. **Handle variants:** "Small" → "S", "Medium" → "M" (optional lookup).
4. **Store raw** in DB; derive ordinal at aggregation/display.

### 3.4 Normalized Ordinal (0–1) for Cross-Product Math

**When:** Comparing fit quality across products with different size ranges (letter vs numeric).

**Formula:** `ordinal_normalized = (ordinal - min) / (max - min)` per product or category. Output 0–1. See [MATHEMATICAL_OPTIMIZATION.md](./MATHEMATICAL_OPTIMIZATION.md) §1.3.

---

## 4. Cross-Cutting Data Points for Category B

| Data point | Type | Encoding / Label | Storage | Notes |
|------------|------|------------------|---------|-------|
| `size` | Text | Raw + optional ordinal | `event_data->>'size'` | See Section 3 |
| `sizes_viewed[]` | Array | Array of size strings | `tryon_sessions.sizes_viewed` or derived from events | |
| `product_id` | Text | As-is | TEXT | Product-level fit |
| `product_name` | Text | As-is | TEXT | Display |
| `variant_id` | Text | As-is | TEXT | Variant-level |
| `height`, `weight` | Integer | As-is (cm, kg) | `fit_passports` | Aggregated only; no PII to brands |
| Body measurements | Integer | As-is (cm) | `fit_passports` | Same |
| `preferred_fit` | Text | `slim`/`regular`/`loose` | TEXT | **Core for Category B.** From fit_passports. Ordinal optional: slim=0, regular=1, loose=2. *Future: per-garment (slim tops, loose bottoms).* |
| `country` | Text | ISO 3166-1 alpha-2 | TEXT | |
| `city` | Text | As-is | TEXT | |

**Body measurements:** Never send raw to brands. Use only for aggregated insights (e.g. "customers who bought M have avg waist X"). Binned or aggregated only.

---

## 5. Schema Requirements for Category B

### 5.1 `analytics_events` (additions)

| Column/Path | Required for B | Notes |
|-------------|----------------|-------|
| `event_data->>'size'` | ✓ | For size_recommended, size_viewed, size_selected |
| `event_data` (purchase) | ✓ | Must include size. For single-item orders: `size`. For multi-item: `line_items` JSON array with `{product_id, size, amount}` per item for size stress & distributions |
| `preferred_fit` | ✓ | From fit_passport via user_id. Add to event or join at query. Enables segment analysis. |
| `country`, `city` | ✓ | Regional fit curves |
| `product_id` | ✓ | Product-level fit |

### 5.2 `tryon_sessions` (optional)

| Column | Use |
|--------|-----|
| `sizes_viewed` | Pre-aggregated array; else derive from events |
| `size_recommended` | Snapshot; else get from events |
| `size_selected` | Snapshot; else get from events |

### 5.3 Size Ordinal Lookup (new)

| Table/Config | Purpose |
|--------------|---------|
| `size_ordinal_map` or JSON config | Map size label → ordinal for ordering. Product-specific or generic. |

---

## 6. Implementation Order

| Phase | Task | Output |
|-------|------|--------|
| **1. Size in events** | Fire `size_recommended`, `size_viewed`, `size_selected` with `size` in `event_data`. | Size data in events |
| **2. Size in purchase** | Webhook extracts size from line items. Store in purchase `event_data`. | size_purchased |
| **3. sizes_viewed** | Either persist to tryon_sessions or derive from size_viewed events. | Array per session |
| **4. Recommendation match** | Join size_recommended + size_purchased per session. Compute match. | Binary + rate |
| **5. Size distributions** | Aggregate by size, event_type. Build bar chart. | Dashboard |
| **6. Entropy** | Implement Shannon entropy for sizes_viewed per session. | Fit confidence metric |
| **7. Misfit signals** | Queries for viewed-not-purchased, selected-not-purchased. | Alerts / reports |
| **8. Regional curves** | Group by country, city, size. | Regional dashboard |
| **9. Size ordinal** | Create lookup; apply for chart ordering and size-up/down. | Polished viz |

---

## 7. Encoding Summary (Quick Reference)

| Data point | Encoding | Use in equations? |
|------------|----------|-------------------|
| `size` | TEXT raw. Ordinal for order/size-up/down. | Comparison: string. Order: ordinal. |
| `sizes_viewed[]` | Array of TEXT | Count, entropy. No encoding. |
| `country` | ISO 3166-1 alpha-2 | Group only. |
| `city` | Text, normalize | Group only. |
| Body measurements | Integer, aggregated only | Binned/aggregated. No PII. |
| `preferred_fit` | Text or ordinal 0,1,2 | Optional for correlation. |

---

---

## 8. Review & Algorithm Specification (Post-Research)

*Added after research review. Corrects potential errors and specifies best-practice algorithms.*

### 8.1 Corrections & Clarifications

| Issue | Correction |
|-------|------------|
| **Shannon entropy p=0** | `0×ln(0)` is undefined; **by convention = 0**. In code: only compute term when `p_i > 0`. Skip zero probabilities. |
| **Per-session vs per-product** | If multiple products per tryon session: use **(session_id, product_id)** for size_recommended and match. Single-product flow: session is sufficient. |
| **Recommendation match logic** | Compare `size_recommended` to `size_purchased` (not size_selected). Acceptance = when they bought the recommended size. Use normalized string comparison (uppercase, trim) before ordinal. |
| **sizes_viewed derivation** | Prefer deriving from `size_viewed` events (single source of truth) over tryon_sessions.sizes_viewed. Aggregation: `array_agg(DISTINCT event_data->>'size')` per session. |

### 8.2 Canonical Algorithms

**Per-session entropy (Shannon):**
```python
# For each session, sizes_viewed = [s1, s2, ...]. p_i = 1/len(sizes_viewed) for each.
# H = -sum(p_i * log(p_i)) for p_i > 0. Skip p_i = 0.
import math
def entropy_per_session(sizes_viewed):
    n = len(sizes_viewed)
    if n <= 1: return 0.0
    p = 1.0 / n
    return -n * (p * math.log(p))  # = log(n)
```

**Recommendation acceptance rate:**
```sql
WITH sessions_with_rec AS (
  SELECT session_id, event_data->>'size' AS size_rec
  FROM analytics_events WHERE event_type = 'size_recommended'
),
sessions_with_purchase AS (
  SELECT session_id, event_data->>'size' AS size_purch
  FROM analytics_events WHERE event_type = 'purchase'
)
SELECT COUNT(*) FILTER (WHERE UPPER(TRIM(s.size_rec)) = UPPER(TRIM(p.size_purch)))::FLOAT
       / NULLIF(COUNT(*), 0) AS acceptance_rate
FROM sessions_with_rec s
JOIN sessions_with_purchase p ON s.session_id = p.session_id;
```

**Size stress (product × size with low conversion):**
```sql
-- Flag where views >> purchases. Minimum sample to avoid noise.
-- Requires purchase events with (product_id, size) per line item, or aggregated source.
SELECT product_id, size, count_viewed, count_purchased,
       count_purchased::FLOAT / NULLIF(count_viewed, 0) AS conversion
FROM aggregated_product_size_counts  -- build from events; schema TBD for line-item level
WHERE count_viewed >= 5
  AND (count_purchased = 0 OR conversion < 0.1);
```
*(Note: Purchase schema must support product_id + size per line item for this metric. See Section 5.)*

### 8.3 Edge Cases

| Edge case | Handling |
|-----------|----------|
| Session with no size_recommended | Exclude from acceptance denominator. |
| Multiple size_recommended per session | Use first or last; document. For multi-product, use (session, product). |
| Size label mismatch (e.g. "S" vs "Small") | Normalize via lookup before comparison. |
| Empty sizes_viewed | Entropy = 0. Skip session or return 0. |
| Single size viewed | Entropy = 0 (no exploration). |

---

## 9. Senior Research Review (2040 Standard)

*Rigorous improvements from an enterprise analytics perspective.*

### 9.1 Statistical Rigor

| Improvement | Detail |
|-------------|--------|
| **Acceptance rate: confidence interval** | Use Wilson score interval. Show e.g. "72% (68–76%)" so brands see uncertainty. Suppress when denominator < 30. |
| **Size distributions: minimum counts** | For regional curves, suppress cells with count < 5 (chi-sq assumption). Flag "Low sample" in UI. |
| **Normalized entropy for comparison** | When comparing entropy across products/regions with different k (sizes available), use `E_H = H / ln(k)` so 0–1 scale is comparable. |

### 9.2 Multi-Product Sessions

| Improvement | Detail |
|-------------|--------|
| **Grain for size_recommended** | If one session can try multiple products: use **(session_id, product_id)**. One recommendation per (session, product). Match size_purchased per line item to size_recommended for that product. |
| **Acceptance rate denominator** | Sessions with at least one (size_recommended AND purchase for same product). Exclude sessions that bought a product they never tried. |

### 9.3 Size Comparison Robustness

| Improvement | Detail |
|-------------|--------|
| **Canonical size mapping** | Create `size_canonical` lookup: "Small"→"S", "Medium"→"M", "32 waist"→"32". Apply before comparison. Reduces false mismatches. |
| **Size equivalence (EU/US)** | EU 36 ≈ US S in some contexts. Product-level size chart may define equivalences. Document if we support cross-system comparison. |
| **Variant title parsing** | Shopify variant_title often includes size in free text ("Blue / M"). Extract size via regex or Shopify metafields. Document extraction logic. |

### 9.4 Data Quality

| Improvement | Detail |
|-------------|--------|
| **Empty size in events** | If size is null/empty, exclude from acceptance and distributions. Count separately for "missing size" monitoring. |
| **Purchase event: line-item schema** | For multi-item orders, store `event_data: { line_items: [{ product_id, variant_id, size, amount }] }`. Enables product×size attribution. |

### 9.5 Missing Variable: Size Up/Down Rate

| Variable | Formula | Why add |
|----------|---------|---------|
| **Size up rate** | % of sessions where size_selected > size_recommended (ordinal) | Loose preferrers may size up. Trend signal. |
| **Size down rate** | % where size_selected < size_recommended | Slim preferrers may size down. |
| **Size match rate** | Same as acceptance; explicit name. | — |

### 9.6 Semantic Contracts

| Term | Definition |
|------|------------|
| **Recommendation match** | size_recommended (normalized) equals size_purchased (normalized) for same (session, product). |
| **Acceptance rate** | Sessions with match / sessions with (recommendation + purchase). Excludes no-purchase. |
| **Per-session entropy** | H = -Σ(p_i × ln p_i), p_i = 1/k for k sizes viewed. Single size → H=0. |

---

*Depends on: Category A (events, webhook, session_id). Next: Category C.*
