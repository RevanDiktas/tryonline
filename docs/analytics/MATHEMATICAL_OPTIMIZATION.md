# Mathematical Optimization — Best-in-Class Functions

**Purpose:** Define the best mathematical functions for analytics, the encoding pipeline (raw → ordinal → derived values), and how each metric derives from encoded inputs. Ensures we use research-backed, optimizable math for the best results.

**Reference:** Implementation roadmaps A, B, C. [ANALYTICS_STRUCTURE_TREE.md](./ANALYTICS_STRUCTURE_TREE.md).

---

## 1. Encoding Pipeline: Raw → Ordinal → Normalized

All size-related math depends on this pipeline. **We must add numeric values to categorical data (sizes) before mathematical derivation.**

### 1.1 Pipeline Overview

```
raw size (text)  →  ordinal (integer)  →  normalized ordinal (0–1, optional)
     "M"                   2                        0.5
     "32"                  32                       0.33 (if range 28–36)
```

### 1.2 Step 1: Raw → Ordinal

| Size type | Raw examples | Ordinal encoding | Notes |
|-----------|--------------|------------------|-------|
| **Letter** | XS, S, M, L, XL | XXS=0, XS=1, S=2, M=3, L=4, XL=5, XXL=6 | Generic lookup. Add "Small"→S, "Medium"→M. |
| **Numeric** | 28, 30, 32, 34, 36 | Use value directly: 28, 30, 32... | Waist, inseam. Already numeric. |
| **Product-specific** | P, G, 1, 2, etc. | Custom mapping per product | `size_ordinal_map` table: (product_id, size_raw) → ordinal |

**Normalization before encoding:** Trim, uppercase letter sizes, alias lookup ("Small"→"S").

### 1.3 Step 2: Ordinal → Normalized (0–1) for Cross-Product Math

**Problem:** Product A uses S/M/L (ordinals 2,3,4). Product B uses 28–36 (ordinals 28–36). We cannot compare "size error" across products without a common scale.

**Solution — Min-max normalization per product:**

```
ordinal_normalized = (ordinal - ordinal_min) / (ordinal_max - ordinal_min)
```

- **Per product:** Use min/max of that product's size range. M in S–XL → (3-2)/(4-2) = 0.5.
- **Per category:** If all tops use S–XL, use category min/max.
- **Output:** 0 = smallest, 1 = largest. Enables cross-product comparisons.

**When to use:**
- **Ordinal (integer):** Size up/down, MAE, distributions within product, chart ordering.
- **Normalized (0–1):** Cross-product fit quality, aggregate "size error" across products, ML features.

### 1.4 preferred_fit Encoding

| Value | Ordinal | Use |
|-------|---------|-----|
| slim | 0 | Segment, optional correlation |
| regular | 1 | Default |
| loose | 2 | Segment |

---

## 2. Category A — Best Math for Conversion & Attribution

### 2.1 Conversion Rates: Wilson Score (Frequentist) + Beta-Binomial (Bayesian)

| Approach | Formula / Logic | When to use |
|----------|-----------------|-------------|
| **Wilson score interval** | Bounds for binomial proportion. Avoids Wald's poor coverage when n is small. | Display confidence: "12% (10–15%)" |
| **Beta-Binomial (Bayesian)** | Posterior: Beta(α, β) with α = successes + 1, β = failures + 1. Credible interval from inverse CDF. | A/B tests, probabilistic "chance to be best", peek-safe. |

**Bayesian conversion rate:**
```
Posterior: p ~ Beta(conversions + 1, non_conversions + 1)
Expected conversion = (conversions + 1) / (conversions + non_conversions + 2)
95% credible interval: [qbeta(0.025, α, β), qbeta(0.975, α, β)]
```

**Output:** Point estimate + uncertainty. Enables "we are 95% confident true conversion is between X and Y."

### 2.2 Time Metrics: Median (Robust)

- **Time_to_Purchase, Dwell time:** Use **median** (not mean). Mean is skewed by outliers (someone buys next week).
- **Formula:** `PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_seconds)`

---

## 3. Category B — Best Math for Fit (Ordinal-Derived)

### 3.1 Beyond Binary: Continuous Fit Quality

| Metric | Formula | Inputs (from encoding) | Output | Why best |
|--------|---------|------------------------|--------|----------|
| **Mean Absolute Size Error (MASE)** | `(1/n) Σ \|ordinal_purchased - ordinal_recommended\|` | Ordinal from pipeline | Avg size steps off | Penalizes "one size off" less than "three sizes off". Industry standard for ordinal regression. |
| **Macroaveraged MAE** | `(1/|classes|) Σ MAE_per_class` | Same | Robust to imbalance | When size M dominates, standard MAE is misleading. Macro-MAE weights each size equally. Use when sizes are imbalanced. |
| **Size error distribution** | `COUNT` where error = 0, 1, 2, ... | Ordinal diff | Histogram | Shows "70% exact, 25% one off, 5% two off" — richer than binary. |

### 3.2 Acceptance Rate (Binary) — Keep, Add Wilson

- Keep binary match for "did they buy our rec?" 
- Add **Wilson score interval** for uncertainty.
- **Optional:** Use **Bayesian Beta-Binomial** for posterior probability.

### 3.3 Size Up / Size Down (Ordinal-Derived)

| Variable | Formula | Encoding |
|----------|---------|----------|
| Size up rate | `COUNT(ordinal_selected > ordinal_recommended) / n` | Requires ordinal |
| Size down rate | `COUNT(ordinal_selected < ordinal_recommended) / n` | Requires ordinal |
| Mean size up/down | `(1/n) Σ (ordinal_selected - ordinal_recommended)` | Signed; positive = avg size up |

### 3.4 Exploration Entropy — Shannon + Normalized

| Formula | Use |
|---------|-----|
| **Shannon:** `H = -Σ p_i ln(p_i)` for p_i > 0 | Per-session or cross-session |
| **Normalized:** `E_H = H / ln(k)` where k = number of unique sizes | Compare across products with different k. 0 = focused, 1 = even. |

### 3.5 Regional Divergence — Jensen-Shannon Divergence

**Problem:** Chi-squared requires expected freq ≥ 5 per cell; fails on sparse data.

**Better:** **Jensen-Shannon (JS) divergence** between size distributions.

- **Symmetric:** JSD(P, Q) = ½ KL(P‖M) + ½ KL(Q‖M), M = ½(P+Q)
- **Bounded:** 0 (identical) to ln(2) (max different)
- **True metric:** sqrt(JSD) satisfies triangle inequality
- **Formula:** Compare distribution of size demand in Region A vs Region B. High JSD = regions buy different sizes.

**Use:** "US vs EU size divergence = 0.32" (on 0–ln(2) scale). Actionable: regions need different allocation.

---

## 4. Category C — Best Math for Trends & Forecasting

### 4.1 Velocity — Exponential Smoothing (Optional Enhancement)

| Approach | Formula | Use |
|----------|---------|-----|
| **Raw count** | `COUNT` in window | MVP. Simple. |
| **EWMA (Exponential Weighted Moving Average)** | `y_t = α·x_t + (1-α)·y_{t-1}` | Smoother trend. α ≈ 0.2–0.3. |
| **Holt-Winters** | Trend + seasonal components | When we have 12+ months; seasonal products. Defer. |

**MVP:** Raw counts. Add EWMA when dashboard needs smoother curves.

### 4.2 Trend Detection — Linear Regression Slope

- **Rising/declining:** Fit `y = β₀ + β₁·t` over time buckets.
- **Slope β₁:** Positive = rising, negative = declining.
- **R²:** Avoid flagging when fit is poor (noise).
- **Rule:** Flag only if |β₁| > threshold AND R² > 0.3 (configurable).

### 4.3 Demand Forecasting (Future)

- **Exponential smoothing** or **Holt-Winters** for tryon/purchase velocity.
- **Probabilistic forecast:** Output quantiles (e.g. 50th, 90th percentile) for inventory decisions.

---

## 5. Encoding → Math Derivation Summary

| Raw input | Encoding step | Derived math | Output |
|-----------|---------------|--------------|--------|
| size "M" | ordinal = 3 | MAE, size up/down, distributions | Fit quality, trends |
| size "32" | ordinal = 32 (or normalized) | Same | Same |
| conversions, n | Beta(α,β) | Credible interval | Conversion ± uncertainty |
| sessions | Wilson score | Interval | Rate ± uncertainty |
| sizes viewed | proportions p_i | Shannon H, normalized E_H | Exploration, fit drift |
| region A size dist, region B | P, Q as distributions | JSD(P,Q) | Regional divergence |
| tryon_velocity, purchase_velocity | Counts | Ratio, EWMA | Lag, momentum |
| acceptance over time | Rate per week | Slope β₁ | Fit drift |

---

## 6. Implementation Priority

| Priority | Metric | Encoding required | Complexity |
|----------|--------|-------------------|------------|
| P0 | Ordinal for size | size_ordinal_map | Medium |
| P0 | MASE (mean absolute size error) | Ordinal | Low |
| P0 | Wilson interval for rates | None | Low |
| P1 | Size up/down (ordinal diff) | Ordinal | Low |
| P1 | Normalized entropy E_H | None | Low |
| P1 | Bayesian conversion (Beta) | None | Low |
| P2 | Macroaveraged MAE | Ordinal, per-class | Medium |
| P2 | Jensen-Shannon regional | Distribution from counts | Medium |
| P2 | Ordinal normalized (0–1) | Per-product min/max | Medium |
| P3 | EWMA for velocity | None | Low |
| P3 | Holt-Winters | 12+ months data | High |

---

## 7. Cross-References

- **Category A roadmap:** Conversion formulas, Bayesian addition.
- **Category B roadmap:** Ordinal pipeline, MASE, macro-MAE, JS divergence.
- **Category C roadmap:** EWMA, slope-based trend.
- **ANALYTICS_STRUCTURE_TREE:** Brand-facing summary; this doc is the math spec.
