# TryOn Data Flow — Summary & Visualization

**Purpose:** Clear summary and visualization of how data flows from shopper actions to analytics outputs.

---

## In 5th Grader Language

**Imagine you're playing a video game, and the game counts everything you do.**

1. **You do stuff.** You open the Try-On, pick a size, add a shirt to the cart, or buy it. Every time you do one of these things, the game "taps us on the shoulder" and says, "Hey, the shopper just did this!"

2. **We write it down.** Our computer gets that tap and writes it in a big notebook (the `analytics_events` table). It also remembers where you're from (country, city) so we know if people in Paris like different sizes than people in New York.

3. **When you buy something.** You don't buy on our site — you buy on the store's site (Shopify). When you pay, their computer tells ours: "Someone just bought something, and we think it was from a Try-On session." We match it up and add "purchase" to our notebook.

4. **We add up the numbers.** Every night (or every hour), a robot looks at our notebook and makes a shorter summary: "Today: 100 people tried on, 20 added to cart, 5 bought." That goes into a different notebook (`analytics_daily`).

5. **We show the store.** The brand (the store) opens a dashboard. It's like a report card: "Here's how many people tried on, how many bought, what sizes they liked, and where they're from." They can also download a spreadsheet (CSV) or we save files for number-crunchers (Parquet).

**Bottom line:** You try on clothes → we count it → we add it up → the store sees how well it's working. The store gets happier because they know the Try-On is helping people buy more and choose the right size.

---

## Summary

**End-to-end flow:** Shopper interacts with TryOn (or avatar onboarding) → frontend fires events to our API → backend enriches with region, writes to `analytics_events` → batch job aggregates into `analytics_daily` → dashboard and quant tools consume. Purchases arrive via Shopify webhook and join the same pipeline.

| Stage | What happens | Output |
|-------|--------------|--------|
| **1. Capture** | Shopper clicks, views, adds to cart; embed/onboarding call `trackEvent()` | HTTP POST to `/api/events/track` |
| **2. Ingest** | Backend adds `country`/`city` (user or IP), validates, inserts | Row in `analytics_events` |
| **3. Purchase** | Shopify sends `orders/paid` webhook; we match `session_id` from cart | `purchase` event in `analytics_events` |
| **4. Aggregate** | Nightly/hourly job reads events, groups by day/brand/region/product | Rows in `analytics_daily` |
| **5. Derive** | Dashboard + APIs compute rates, funnel, trends from daily + raw | Metrics (ROI, conversion, fit, velocity) |
| **6. Export** | Batch export to Parquet; dashboard "Export" to CSV | Quant files; brand downloads |

**Key principle:** Raw events = source of truth. Daily aggregates = performance layer. Derived metrics = computed at read time (or cached).

---

## Visualization 1 — High-Level Flow

```mermaid
flowchart LR
    subgraph SOURCES["Sources"]
        A[Shopper<br/>Embed / Onboarding]
        B[Shopify<br/>orders/paid webhook]
        C[User profile<br/>country, city]
    end

    subgraph CAPTURE["Capture"]
        D["POST /api/events/track"]
        E["POST /api/webhooks/shopify"]
    end

    subgraph INGEST["Ingest (Backend)"]
        F[Enrich region<br/>user or IP]
        G[Validate & insert]
    end

    subgraph STORAGE["Storage"]
        H[(analytics_events<br/>raw events)]
        I[(analytics_daily<br/>daily rollups)]
    end

    subgraph PROCESS["Process"]
        J[Batch job<br/>hourly/nightly]
    end

    subgraph CONSUME["Consume"]
        K[Brand Dashboard]
        L[Parquet export<br/>quant / ML]
        M[CSV export]
    end

    A --> D
    B --> E
    E --> G
    D --> F
    F --> G
    C -.-> F
    G --> H
    H --> J
    J --> I
    I --> K
    H --> L
    I --> M
```

---

## Visualization 2 — Event Journey (Sequence)

```mermaid
sequenceDiagram
    participant S as Shopper
    participant FE as Frontend (Embed / TryOnViewer)
    participant API as Backend API
    participant DB as Supabase
    participant SH as Shopify
    participant Job as Batch Job
    participant Dash as Dashboard

    Note over S,Dash: Try-On Session
    S->>FE: Opens widget
    FE->>API: trackEvent(widget_opened)
    API->>DB: INSERT analytics_events
    S->>FE: Sees avatar, clicks size, adds to cart
    FE->>API: trackEvent(tryon_started, size_selected, add_to_cart)
    API->>DB: INSERT analytics_events (×3)
    FE->>SH: postMessage → Add to cart (with session_id)
    S->>SH: Completes checkout
    SH->>API: Webhook orders/paid (order + cart attributes)
    API->>DB: INSERT analytics_events (purchase, session_id matched)

    Note over S,Dash: Aggregation
    Job->>DB: SELECT events since last run
    Job->>Job: Group by brand, date, (country, product)
    Job->>DB: UPSERT analytics_daily

    Note over S,Dash: Consumption
    Dash->>DB: SELECT analytics_daily + raw events
    Dash->>Dash: Compute rates, funnel, trends
    Dash->>S: Display KPIs, charts, export CSV
```

---

## Visualization 3 — Data Layers

```mermaid
flowchart TB
    subgraph LAYER1["Layer 1: Raw (Source of Truth)"]
        E[analytics_events]
        T[tryon_sessions]
    end

    subgraph LAYER2["Layer 2: Aggregated"]
        D[analytics_daily<br/>by brand, date, country, product]
    end

    subgraph LAYER3["Layer 3: Derived (Computed)"]
        R[Conversion rates<br/>TryOn→ATC, TryOn→Purchase]
        V[Revenue_attributed<br/>AOV_TryOn, Revenue_per_TryOn]
        F[Fit metrics<br/>Recommendation acceptance<br/>Size distributions]
        TR[Trend metrics<br/>Velocity, fit drift<br/>High try-on / low purchase]
    end

    subgraph LAYER4["Layer 4: Output"]
        BR[Brand Dashboard]
        PQ[Parquet files]
        CS[CSV export]
    end

    E --> D
    T --> D
    D --> R
    D --> V
    E --> F
    D --> F
    E --> TR
    D --> TR
    R --> BR
    V --> BR
    F --> BR
    TR --> BR
    E --> PQ
    D --> PQ
    D --> CS
```

---

## Visualization 4 — Event → Metric Mapping

```mermaid
flowchart LR
    subgraph EVENTS["Events (analytics_events)"]
        e1[widget_opened]
        e2[tryon_started]
        e3[size_recommended]
        e4[size_selected]
        e5[add_to_cart]
        e6[purchase]
    end

    subgraph METRICS["Derived Metrics"]
        m1[Funnel conversion]
        m2[Revenue_attributed]
        m3[AOV_TryOn]
        m4[Recommendation acceptance]
        m5[Size demand curve]
        m6[TryOn velocity]
    end

    e1 --> m1
    e2 --> m1
    e2 --> m6
    e4 --> m1
    e5 --> m1
    e6 --> m1
    e6 --> m2
    e6 --> m3
    e3 --> m4
    e4 --> m4
    e6 --> m4
    e4 --> m5
    e6 --> m5
```

---

## Quick Reference: What Flows Where

| Source | Destination | When |
|--------|-------------|------|
| Shopper action (embed/onboarding) | `POST /api/events/track` | Real-time |
| Backend + user profile / IP | `analytics_events` | On each track |
| Shopify webhook | `analytics_events` (purchase) | On order paid |
| `analytics_events` | `analytics_daily` | Batch (hourly/nightly) |
| `analytics_daily` + `analytics_events` | Dashboard API | On load / filter |
| `analytics_events` + `analytics_daily` | Parquet files | Batch export |
| Dashboard | CSV | On "Export" click |

---

---

## Reference: Categories, Variables, Data Points & Dashboard

### Categories We Track

| Category | Goal |
|----------|------|
| **A. ROI & Attribution** | Does TryOn drive revenue? How much? |
| **B. Fit Accuracy & Buying** | Which sizes to buy? Is our recommendation good? |
| **C. Trend & Demand** | What's changing? Early warnings for buying teams? |

---

### Variables per Category

| Category | Raw variables | Derived variables |
|----------|---------------|-------------------|
| **A. ROI** | `user_id`, `session_id`, `order_id`, `product_id`, `brand_id`, `event_type`, `amount`, `created_at`, `country`, `city` | TryOn→ATC rate, TryOn→Purchase rate, Purchase_with_TryOn, Revenue_attributed, AOV_TryOn, Revenue_per_TryOn, Time_to_Purchase |
| **B. Fit** | `size` (recommended/viewed/selected/purchased), `sizes_viewed[]`, `product_id`, body measurements (aggregated), `country`, `city` | Recommendation match, Acceptance rate, Size demand distribution, Exploration entropy, Regional fit curves |
| **C. Trend** | `tryons_started`, `unique_sessions`, `created_at`, `date`, `product_id`, `country`, size interactions | TryOn velocity, Purchase velocity, High try-on/low purchase SKUs, Size stress, Fit drift, Regional divergence |

---

### Data Points (Raw Events)

| Event | When fired | Key data |
|-------|------------|----------|
| `widget_opened` | User opens Try-On | session_id, product_id |
| `tryon_started` | Viewer loads, user sees avatar+garment | session_id, product_id |
| `size_recommended` | We compute recommended size | size |
| `size_viewed` | User clicks a size to view | size |
| `size_selected` | User picks size (e.g. for ATC) | size |
| `add_to_cart` | User clicks Add to Cart | product_id, variant_id, size |
| `purchase` | Order paid (webhook) | order_id, amount, currency |
| `avatar_created` | Avatar creation succeeds | user_id |

*Plus context on every event: `user_id`, `session_id`, `brand_id`/`shop_domain`, `product_id`, `country`, `city`, `created_at`.*

---

### What We Show on the Dashboard

**Time filter:** Today | WTD | MTD | QTD | YTD (all charts respect it)

**KPI cards:**
- Avatars created *(we use; brand may not see)*
- Try-ons started
- Add-to-carts
- Purchases (attributed to widget)
- Revenue
- Conversion rate (purchases / tryons_started)
- Add-to-cart rate

**Charts:**
- **Funnel** — widget_opened → tryon_started → size_selected → add_to_cart → purchase (counts + % per step)
- **Trends over time** — daily line chart of revenue, purchases, try-ons, add-to-carts
- **Sizing** — bar chart of size_recommended / size_selected / size_purchased distribution
- **Products** — table of top products by try-ons, ATC, purchases
- **Region** — metrics by country (and city); map or table

**Filters:** Time preset, brand (when multi-brand), region (country/city)

**Export:** CSV of current view

**We use vs Brand gets:** We see avatar failures, viewer errors, full drop-off. Brand sees only: try-ons, sizes, ATC, purchases, revenue, conversion, products, region — no internal platform issues.

---

*See also: [QUANT_DATA_STRATEGY.md](./QUANT_DATA_STRATEGY.md) for variable categorization and derived metrics; [IMPLEMENTATION_PLAN_WHEN_BACK.md](./IMPLEMENTATION_PLAN_WHEN_BACK.md) for tracking spec and event wiring.*
