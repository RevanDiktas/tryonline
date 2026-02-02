# Analytics Structure Tree — Full Overview for Brand Dashboard

**Purpose:** Complete structure tree for all three categories, with math per variable and plain-language "what it means to the brand." For brand login dashboard.

**Reference:** Implementation roadmaps A, B, C. [DATA_FLOW_SUMMARY.md](../DATA_FLOW_SUMMARY.md). [MATHEMATICAL_OPTIMIZATION.md](./MATHEMATICAL_OPTIMIZATION.md) — encoding pipeline & best-in-class math.

---

## What We're Optimising

1. **The brand** — Better size buying, assortment, regional allocation.
2. **The product** — Which products and sizes sell, what to reorder.
3. **The shopper** — Personal fit (recommendation, preferred fit) so they buy with confidence.

---

## Category A — ROI & Attribution

**Data points we use:** `session_id`, `event_type` (widget_opened, tryon_started, add_to_cart, purchase), `amount`, `currency`, `order_id`, `created_at`, `country`, `city`, `preferred_fit`.

### Structure Tree

| Branch | Variable | Math (function) | What it means to the brand |
|--------|----------|-----------------|----------------------------|
| **Conversion** | TryOn → Add-to-Cart rate | `sessions with ATC / sessions with tryon` + Wilson interval or Beta-Binomial credible interval | Of people who tried on, what % added to cart? Higher = TryOn works. Best math: Bayesian credible interval. |
| **Conversion** | TryOn → Purchase rate | Same + Wilson or Beta-Binomial | Of people who tried on, what % bought? Core conversion proof. |
| **Attribution** | Purchase with TryOn | Binary: order linked to a TryOn session | Did this sale come from our widget? Yes/no per order. |
| **Attribution** | Revenue attributed | `SUM(amount)` for Purchase_with_TryOn | Total € or $ from TryOn. Your TryOn-driven revenue. |
| **Value** | AOV (TryOn) | `Revenue attributed / number of orders` | Average order value when they used TryOn. Compare to site average. |
| **Efficiency** | Revenue per TryOn | `Revenue attributed / tryon sessions` | € per try-on. How much each TryOn session is worth. |
| **Efficiency** | Time to Purchase | `purchase time − tryon start time` | How fast they bought after trying. Shorter = higher intent. Report **median** (robust to outliers). |
| **Efficiency** | Dwell time | `tryon_ended − tryon_started` | How long they spent in TryOn. Longer = higher engagement. Strong conversion correlate. |
| **Segment** | All above by preferred_fit | Same math, split by slim / regular / loose | Do slim-preferrers convert better? Do loose-preferrers spend more? Segment insights. |

---

## Category B — Fit Accuracy & Buying Decisions

**Data points we use:** `size` (recommended, viewed, selected, purchased), `sizes_viewed[]`, `product_id`, `country`, `city`, `preferred_fit`, body measurements (aggregated only).

### Structure Tree

| Branch | Variable | Math (function) | What it means to the brand |
|--------|----------|-----------------|----------------------------|
| **Recommendation quality** | Recommended = Purchased | Binary: `size_recommended == size_purchased` | Did they buy the size we suggested? |
| **Recommendation quality** | Acceptance rate | `sessions where match / sessions with rec + purchase` | % of time our recommendation was right. Core fit accuracy. |
| **Recommendation quality** | MASE (Mean Absolute Size Error) | `(1/n) Σ \|ordinal_purchased - ordinal_recommended\|` | **Ordinal-derived.** Continuous fit quality. 0 = perfect. Requires size encoding. |
| **Size demand** | Size distributions | `COUNT` by size (viewed, selected, purchased) | How many S, M, L (etc.) viewed, chosen, bought. Basis for buying. |
| **Fit confidence** | Sizes viewed per session | `COUNT(DISTINCT sizes)` per session | How many sizes they looked at. Fewer = more confident. |
| **Fit confidence** | Exploration entropy | Shannon: `H = -Σ(p × ln(p))`, p = share per size | Even exploration = high entropy. Focused = low. Rising = less confidence. |
| **Misfit signals** | Viewed but not purchased | Sizes they looked at but didn't buy | Which sizes get interest but no sale? Fix chart or product. |
| **Misfit signals** | Selected but not purchased | Had size_selected, no purchase | Considered buying, didn't. Cart/checkout friction? |
| **Regional curves** | Size demand by country/city | Same distributions, `GROUP BY country` | What sizes sell in US vs EU vs your boutiques' cities. |
| **Regional curves** | Regional divergence | **Jensen-Shannon divergence** between size distributions | How different are region size demands? 0 = same, ln(2) = max. Best math for sparse data. |
| **Size up/down** | Size up rate, Size down rate | Ordinal: selected − recommended. % sessions that sized up or down | Do loose-preferrers size up? Trend signal for recommendation calibration. |
| **Preferred fit** | All above by fit preference | Same math, split by slim / regular / loose | Do slim-preferrers accept our recs more? What sizes do loose-preferrers buy? Personalisation insight. |

---

## Category C — Trend & Demand Forecasting

**Data points we use:** Same as A and B, plus `created_at` / `date` for time. `tryons_started`, `purchases`, `product_id`, `size`, `country`, `preferred_fit`.

### Structure Tree

| Branch | Variable | Math (function) | What it means to the brand |
|--------|----------|-----------------|----------------------------|
| **Momentum** | TryOn velocity | `COUNT(tryons)` over window. **EWMA** for smoothing. | How many try-ons lately? Speeding up or slowing down? Best math: EWMA for trend. |
| **Momentum** | Purchase velocity | Same + **EWMA** | How many sales from TryOn lately? |
| **Early warning** | High try-on / low purchase SKUs | `tryons / purchases` per product; flag if ratio > threshold | Products people try but don't buy. Fix product, price, or fit. |
| **Early warning** | Rising size exploration | Entropy or sizes_viewed count over time | Are people less sure about fit? Model may need update. |
| **Size stress** | Interest but low conversion (size) | Views/selection vs purchases per product×size | Which sizes get interest but few buys? Allocation or fit issue. |
| **Regional divergence** | Size demand differs by region | Compare distributions (%, or chi-squared) | Does US buy different sizes than EU? Adjust buying per region. |
| **Fit drift** | Declining acceptance | Acceptance rate over time. **Slope β₁** from linear regression. | Is our recommendation getting worse? Recalibrate. Best math: slope + R² threshold. |
| **Fit drift** | Rising exploration entropy | Entropy over time | Same signal: less confidence in fit. |
| **Preferred fit** | All above by fit preference | Same math, split by slim / regular / loose | Velocity, stress, drift by shopper preference. Is the slim/loose mix changing? |
| **Lag indicator** | TryOn-to-Purchase velocity ratio | `purchase_velocity / tryon_velocity` over same window | Conversion momentum. Declining ratio = purchases lagging tryons. |

---

## Encoding Pipeline (Required for Size Math)

**All size-derived metrics require encoding:** `raw size (text) → ordinal (integer) → optional normalized (0–1)`.

| Step | Input | Output | Use |
|------|-------|--------|-----|
| 1. Ordinal | "M", "32" | 3, 32 | MASE, size up/down, distributions |
| 2. Normalized | ordinal, product min/max | 0–1 | Cross-product comparison |

See [MATHEMATICAL_OPTIMIZATION.md](./MATHEMATICAL_OPTIMIZATION.md) for full spec.

---

## Math Reference — Functions per Variable

| Variable | Function | Inputs | Output |
|----------|----------|--------|--------|
| TryOn → ATC rate | Division | sessions_with_ATC, sessions_with_tryon | Rate (0–1) |
| TryOn → Purchase rate | Division | sessions_with_purchase, sessions_with_tryon | Rate (0–1) |
| Purchase_with_TryOn | Existence check | session_id in tryon_sessions | Boolean |
| Revenue attributed | Sum | amount WHERE Purchase_with_TryOn | Currency |
| AOV_TryOn | Division | Revenue, order_count | Currency |
| Revenue per TryOn | Division | Revenue, tryon_sessions | Currency |
| Time to Purchase | Subtraction | purchase_ts, tryon_ts | Seconds (or interval) |
| Recommended = Purchased | Equality | size_recommended, size_purchased | Boolean |
| Acceptance rate | Division | match_count, rec_with_purchase_count | Rate (0–1) |
| Size distributions | Count, GroupBy | size, event_type | Count per size |
| Sizes viewed per session | Count distinct | sizes_viewed array | Integer |
| Exploration entropy | Shannon H | p_i (proportions) | Numeric |
| Velocity | Count, filter by date | events, created_at, window | Integer |
| High try-on / low purchase | Division, threshold | tryons, purchases per product | Flag (boolean) |
| Regional divergence | Jensen-Shannon divergence | P(size|country A), Q(size|country B) | 0–ln(2) |
| MASE | Mean absolute error | ordinal_purchased, ordinal_recommended | Avg size steps off |
| Fit drift | Time series comparison | metric over time buckets | Slope or diff |
| Dwell time | Subtraction | tryon_ended_ts, tryon_started_ts | Seconds |
| Size up/down rate | Ordinal diff, Division | size_selected, size_recommended; count / total | Rate |
| Velocity ratio | Division | purchase_velocity, tryon_velocity | Ratio |

---

## Robustness (2040 Standard)

| Practice | Application |
|----------|-------------|
| **Confidence intervals** | Use Wilson score for all rates. Show e.g. "12% (10–15%)". Suppress when n < 30. |
| **Attribution window** | Purchases attributed only if within **30 days** of tryon. Configurable. |
| **Idempotency** | Purchase webhook: dedupe by `order_id`. Reject duplicate Shopify webhook deliveries. |
| **Median for time metrics** | Time_to_Purchase, Dwell time: report median (robust to outliers). |
| **Multi-item orders** | MVP: full order attributed if any item from TryOn. Future: line-item attribution. |
| **Trend significance** | Fit drift: require 4+ weeks data. Avoid over-interpreting noise. |

---

## Preferred Fit — How It Fits In

**What it is:** Shopper preference: slim, regular, or loose. From `fit_passports`. Default can be "regular" if not set.

**Where it goes:**
- **A:** Segment conversion, revenue, AOV by preferred_fit. "Slim preferrers convert at X%, loose at Y%."
- **B:** Segment acceptance, size demand, size-up/down by preferred_fit. "Do loose-preferrers size up more?"
- **C:** Segment velocity and trends by preferred_fit. "Is the mix of slim/regular/loose shifting over time?"

**Future:** Per-garment preference (slim tops, loose bottoms). Schema and recommendation logic come later.

---

## What Might Be Missing

| Gap | Why it matters | When to add |
|-----|----------------|-------------|
| **Product fit type** | Product is "oversized" or "slim" — widget could match to preferred_fit. | When we tag products with fit type and update recommendation logic. |
| **Garment category** | Tops vs bottoms vs dresses — different size logic. | When we have category on products. |
| **New vs returning** | First-time TryOn vs repeat. Conversion may differ. | When we can distinguish (user_id + prior sessions). |
| **Device / channel** | Mobile vs desktop. Different behaviour. | When we store device or have enough volume. |
| **Promotion / discount** | Were they on sale? Affects AOV and conversion. | When we get promo data from Shopify. |
| **ΔAOV vs non-TryOn** | True incrementality. Need baseline (PDP without TryOn). | When we have A/B or control data. |

---

## Future Plan (After A, B, C)

*ABC first. These four come next.*

| Category | What it is | Why it matters |
|----------|------------|----------------|
| **D. Funnel visualization** | Step-by-step drop-off: widget opened → tryon started → size recommended → size selected → add to cart → purchase | Shows exactly where we lose people. "Where do shoppers bail?" |
| **E. Product leaderboard** | Ranked list: most try-ons, best conversion, highest TryOn-attributed revenue per product | Which products does TryOn help most? Promote or restock those. |
| **F. Shopper / audience insights** | New vs returning, device (mobile/desktop), engagement depth | Who uses TryOn? Helps targeting and UX. |
| **G. Satisfaction / feedback** | Post-purchase surveys, NPS, ratings | Direct feedback on TryOn experience. |

---

## Brand Dashboard — Summary

Brands log in and see:

- **Category A:** How much money TryOn drives, conversion rates, revenue per try-on. Filter by time, region, preferred_fit.
- **Category B:** How good our size recommendation is, which sizes sell, misfit signals, regional curves. Segment by preferred_fit.
- **Category C:** Velocity, at-risk products, fit drift, trends. Segment by preferred_fit.

**Goal:** Optimise the brand (buying, allocation), the product (what sells), and the shopper (personal fit).

---

## Best-in-Class Math Summary

| Domain | Best function | Replaces / augments |
|--------|---------------|---------------------|
| Conversion rates | Beta-Binomial credible interval | Wilson (both ok); peek-safe |
| Fit quality | MASE (ordinal) | Binary match only |
| Imbalanced sizes | Macroaveraged MAE | Standard MAE |
| Regional divergence | Jensen-Shannon | Chi-squared (sparse) |
| Velocity trend | EWMA | Raw counts |
| Fit drift | Linear slope β₁ + R² | Simple diff |
| Entropy comparison | Normalized E_H = H/ln(k) | Raw H across products |

---

## Cross-References

- **MATHEMATICAL_OPTIMIZATION.md** — Encoding pipeline, formulas, implementation priority.
- Implementation roadmaps A, B, C: **Senior Research Review** sections (2040 Standard) for full robustness specs.
- DATA_FLOW_SUMMARY: data flow and pipeline.
- IMPLEMENTATION_PLAN_WHEN_BACK: event wiring, schema, gaps.
