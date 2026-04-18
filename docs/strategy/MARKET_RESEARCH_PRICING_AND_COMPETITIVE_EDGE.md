# TryOn Market Research: Pricing, Competition & Path to Market Dominance

> Last updated: 2026-04-15
> Status: Strategic research — NOT a to-do list. Do not edit programmatically.

---

## 1. The Problem We Solve (and Why Brands Will Pay)

### The Returns Crisis

Fashion e-commerce has a $850B problem. In 2025, U.S. retail returns totaled **$849.9 billion**. Fashion is the worst offender:

| Metric | Value | Source |
|---|---|---|
| Average fashion return rate | 25–40% | AlixPartners, Ringly.io |
| Fit/sizing as primary return reason | 45% of all returns | Capital One Shopping |
| Consumers who "bracket" (buy multiple sizes) | 63% | Ringly.io |
| Cost per return to retailer | $10–65 per item | Ringly.io, UWear |
| Return cost as % of item price | 20–65% of COGS | UWear |
| Projected return reduction with effective VTO | 25–50% | UWear |

### What This Means in Revenue Terms

For a mid-size fashion brand doing 5,000 orders/month at $80 AOV with a 30% return rate:
- **1,500 returns/month** × $25 avg cost per return = **$37,500/month lost**
- If TryOn reduces returns by just 20%: **$7,500/month saved**
- If TryOn increases conversion by 15%: additional **$60,000/month revenue** (750 extra orders × $80)

That's **$67,500/month in value** from a single integration. This is why brands will pay.

---

## 2. Market Size & Growth

| Source | 2025 Market Size | 2030 Projection | CAGR |
|---|---|---|---|
| Grand View Research | $9.17B (2023) | $46.42B | 26.4% |
| Mordor Intelligence | $15.18B | $48.10B | 25.95% |
| Market.us | $10.93B (2024) | $108.5B (2034) | 25.8% |
| The Business Research Company | — | $38.92B | 26.3% |

**Bottom line:** This market is growing at ~26% CAGR. Even conservative estimates put it at $40B+ by 2030. This is not a niche — it's becoming standard retail infrastructure.

---

## 3. Competitive Landscape: Who We're Up Against

### 3.1 Lower End ($0–99/month) — Size Chart & Basic Recommendation

| Company | Price | Tech | Threat Level |
|---|---|---|---|
| Kiwi Sizing | $6–29/mo | Size chart widget | None |
| EasySize | $19–99/mo | Questionnaire-based sizing | None |
| Sizefox | $29–79/mo | Basic size recommendation | None |
| Fit Finder | Free–$199/mo | ML size matching | Low |

**Why they don't matter:** No 3D, no body scanning, no virtual try-on, no real analytics. They're solving the "what size should I pick" question with a quiz. We're solving "does this garment look and fit right on MY body." Completely different value proposition.

### 3.2 Mid Market ($500–5,000/month) — Real Fit-Tech

| Company | Price | Tech | Moat | Threat Level |
|---|---|---|---|---|
| 3DLOOK (YourFit) | $500–3K/mo + $2–10K setup | AI body scanning from photos | Mobile-first body measurement | Medium |
| Bold Metrics | $1K–5K/mo | AI fit prediction algorithms | Enterprise data security focus | Medium |
| Perfitly | $500–2.5K/mo | Virtual fitting rooms | — | Low |
| Reactive Reality (PICTOFiT) | $1.5–5K/mo | AR-based 3D try-on | Per-asset pricing, good 3D | Medium-High |
| Revery.ai | $1–4K/mo | AI outfit generation | Generative AI for styling | Medium |
| Style3D | $1–5K/mo | 3D simulation + AI body mapping | Design-to-try-on pipeline | Medium-High |

**Key insight:** These companies either do sizing OR 3D visualization. Nobody combines both with cross-store consumer identity and attribution analytics at this price point.

### 3.3 Upper End ($5,000–50,000+/month) — Enterprise

| Company | Price | Tech | Moat | Threat Level |
|---|---|---|---|---|
| True Fit | $10K–50K/mo | "Fashion Genome" — 350M SKUs | Massive data network, 62.7% market share in size-fit engines | High (data moat) |
| Vue.ai | $5K–50K/mo | Multi-module AI platform | Full-stack retail AI | Medium |
| Veesual | $5K–20K/mo | AI model photography | Realistic on-model imaging | Low |
| Fit:Match | $15K–40K/mo + $50K setup | In-store 3D scanning hardware | Physical retail integration | Low (different market) |

**Key insight:** True Fit is the only company with a real data moat. But they don't do 3D try-on — they only do size recommendations. Their value is in the network (180+ brands feeding fit data). Their weakness is that they're expensive, enterprise-only, and invisible to the consumer.

### 3.4 Big Tech — The Platform Players

| Company | Price | Strategy | Threat Level |
|---|---|---|---|
| Google VTO | Free (ads ecosystem) | Diffusion-model try-on in Google Shopping | High (distribution) |
| Snap AR/ARES | Shut down (2023) | Acquired Fit Analytics for $124M, then divested | Low (retreated) |
| Amazon | Internal | Proprietary fit tools for Amazon.com only | Low (walled garden) |
| Walmart/Zeekit | Internal (acquired ~$200M) | Virtual try-on for walmart.com only | Low (walled garden) |

**Google is the biggest threat — and also the biggest validation.** They're spending billions to make virtual try-on a standard shopping feature. But their approach is fundamentally different from ours:

| | Google VTO | TryOn |
|---|---|---|
| Technology | 2D diffusion model (generates a flat image) | Real 3D avatar + 3D garment (actual geometry) |
| Accuracy | "Plausible" — looks good, doesn't measure fit | Physics-based — actual body measurements inform draping |
| Size recommendation | No | Yes (body-aware) |
| Consumer identity | None (anonymous, per-search) | Persistent avatar + fit passport across stores |
| Analytics for brands | Google Ads metrics only | Full funnel + fit intelligence + return prediction |
| Data ownership | Google owns everything | Brand retains data, we provide insights |

**Google commoditizes the "looks okay" try-on. We own the "actually fits" try-on.** As Forbes noted (April 2026): specialists argue Google's outputs "lack the precision required for luxury fashion, such as accurate fabric drape, motion dynamics, and brand-specific styling logic."

---

## 4. Technology Comparison: Do We Cover Everything?

### What the market offers vs. what we have:

| Capability | TryOn (us) | True Fit | 3DLOOK | Google VTO | Reactive Reality | Style3D |
|---|---|---|---|---|---|---|
| 3D body avatar (SMPL) | YES | No | Yes (scan only) | No | Partial | Partial |
| CLO3D-grade 3D garments | YES | No | No | No | Yes | Yes |
| Size recommendation | YES | Yes | Yes | No | No | Partial |
| Virtual try-on (3D) | YES | No | No | 2D only | Yes | Yes |
| Cross-store consumer identity | YES | Yes (network) | No | No | No | No |
| Wishlist/closet across brands | YES | No | No | No | No | No |
| Attribution analytics | YES | Partial | No | Ads metrics | No | Basic |
| Return risk prediction | YES | No | No | No | No | No |
| Fit-to-purchase correlation | YES | Partial | No | No | No | No |
| Time-series trend analysis | YES | Enterprise only | No | Google Analytics | No | No |
| Device/platform breakdown | YES | No | No | GA4 | No | No |
| Shopify-native (theme extension) | YES | No | No | N/A | No | No |
| Consumer dashboard (free) | YES | No | No | No | No | No |

### What we're missing (and whether it matters):

| Missing Capability | Who Has It | Priority | Why |
|---|---|---|---|
| AI-generated 2D try-on images | Google, DressX, Revery | LOW | Our 3D approach is more accurate; 2D is "good enough" for marketing but fails at fit |
| In-store hardware integration | Fit:Match, Bods/Aetrex | LOW | Our market is online-first; in-store is a future add-on |
| PLM/supply-chain integration | Lectra, Browzwear | MEDIUM | Matters for enterprise upsell; not critical for Shopify brands |
| Multi-language/accessibility | Most enterprise players | MEDIUM | Needed for EU expansion |
| Video try-on (motion) | Google Veo3, some AR tools | LOW-MEDIUM | Cool for marketing; not critical for conversion |
| Style recommendation engine | Stitch Fix, Amazon | HIGH | This is the "personalization layer" — our closet/wishlist data enables this |
| Fabric/material simulation | CLO3D (design-side), Veriprajna | MEDIUM | We use CLO3D garments which already have physics; real-time simulation is future |

**Verdict:** We cover the core stack better than anyone in the $0–5K/month range. The only capability gap that matters strategically is the **style recommendation engine** — and we have the foundation data (closet, wishlist, body measurements, cross-store behavior) to build it.

---

## 5. Pricing Analysis: Full Market Spectrum

### 5.1 Per-Event Pricing Models

| Event Type | Market Rate | Who Charges This |
|---|---|---|
| Size recommendation served | $0.02–0.10 | True Fit, EasySize |
| 3D try-on session opened | $0.05–0.25 | 3DLOOK, Reactive Reality |
| Add to Cart (attributed) | $0.50–2.00 | Secret Sauce Partners |
| Purchase (attributed) | 2–5% of order value | Emerging (almost nobody yet) |
| Return prevented (modeled) | $2–5 credited | **Nobody does this — opportunity** |

### 5.2 SaaS Tier Benchmarks (Monthly)

| Tier | Sessions/mo | Market Range | Common Features |
|---|---|---|---|
| Free/Trial | 100–500 | $0 | Basic widget, limited analytics |
| Starter/SMB | 1,000–2,000 | $49–299 | Full widget, basic dashboard |
| Growth | 5,000–10,000 | $299–999 | Advanced analytics, priority support |
| Pro | 25,000–50,000 | $1,500–3,000 | Full analytics, API access, custom branding |
| Enterprise | Unlimited | $5,000–50,000 | Dedicated support, custom integrations, SLA |

### 5.3 Recommended TryOn Pricing

| | Spark (Free) | Growth ($199/mo) | Pro ($499/mo) | Enterprise (Custom) |
|---|---|---|---|---|
| Try-on sessions | 200/mo | 2,000/mo | 10,000/mo | Unlimited |
| 3D garment uploads | 3 SKUs | 25 SKUs | 100 SKUs | Unlimited |
| Analytics | Basic funnel only | Full Palantir dashboard | + Time-series, fit correlation, return risk | + API, exports, white-label |
| Size recommendation | Yes | Yes | Yes | Yes |
| Consumer dashboard/closet | Yes (always free) | Yes | Yes | Yes |
| Support | Self-serve | Email (48h) | Priority (24h) | Dedicated CSM |
| 3D garment creation | Self-upload only | 5 included/mo | 15 included/mo | Unlimited |
| Overage | Hard cap | $0.10/session | $0.08/session | Negotiated |

**Why this structure wins:**
- **Free tier hooks them.** 200 sessions = ~1 week for a moderately trafficked store. They'll see the conversion data and upgrade.
- **$199 is impulse pricing for a Shopify brand.** Less than their Klaviyo bill. Way less than one influencer post.
- **$499 unlocks the analytics moat.** This is where they see the Palantir dashboard, fit intelligence, return risk. This is where they realize we're not a widget — we're their analytics infrastructure.
- **Enterprise is where the real money is.** Custom integrations, API access, white-label. This is the True Fit competitor tier.

### 5.4 Revenue Projections

| Scenario | Brands | Avg MRR | Monthly Revenue | ARR |
|---|---|---|---|---|
| Early (6 months) | 20 brands (15 free, 5 paid) | $250 | $1,250 | $15K |
| Growth (12 months) | 100 brands (60 free, 30 Growth, 10 Pro) | $220 | $10,900 | $131K |
| Scale (24 months) | 500 brands (300 free, 120 Growth, 70 Pro, 10 Enterprise) | $350 | $73,800 | $886K |
| Dominance (36 months) | 2,000 brands | $400 | $280,000 | $3.4M |

---

## 6. The Kill Strategy: How We Win

### 6.1 Phase 1: "The Shopify Trojan Horse" (Now – 6 months)

**Strategy:** Be the easiest, cheapest, most beautiful virtual try-on for Shopify brands. Period.

- Free tier with 200 sessions — enough to show value, not enough to run on
- 5-minute install (theme app extension, no code)
- Analytics that no competitor at this price point offers
- The dashboard IS the sales tool — when a brand sees "37.4% ATC rate from TryOn users" they'll never uninstall

**Who we beat:** Every $6–99/month size chart widget. They can't compete with 3D try-on + analytics.

### 6.2 Phase 2: "The Data Flywheel" (6–18 months)

**Strategy:** Every brand that installs feeds our fit graph. Every consumer who creates an avatar feeds our body graph. The more brands, the more consumers, the better the recommendations, the more brands want in.

- Cross-store fit intelligence: "Shoppers who wear M in Brand A consistently wear L in Brand B"
- Anonymized benchmark reports: "Your return rate is 28%, the TryOn average is 12%"
- Predictive sizing that gets smarter with every try-on session across every brand

**Who we beat:** 3DLOOK, Bold Metrics, Reactive Reality. They have per-brand data. We have network data. Network always wins.

### 6.3 Phase 3: "The Consumer Platform" (12–24 months)

**Strategy:** tryon.global becomes the consumer destination. Shoppers come to browse, try on, and buy from their closet/wishlist across all integrated stores.

- Style recommendation engine powered by closet data + body measurements + purchase history
- "Similar items that fit you" — cross-store product discovery
- One-click purchase from the dashboard (checkout via Shopify Storefront API)
- Social features: share your avatar wearing outfits, style challenges

**Who we beat:** This is the Stitch Fix killer. They charge $20/styling fee and mark up clothes. We're free for consumers and take commission from brands. Better selection (any brand, not curated), better fit (3D body, not a quiz), lower friction.

### 6.4 Phase 4: "The Infrastructure Layer" (24–36 months)

**Strategy:** Become the identity layer for fashion e-commerce. Every brand plugs into TryOn for fit, every consumer uses their TryOn avatar everywhere.

- "Sign in with TryOn" — a shopper's body passport for any online store
- API for non-Shopify platforms (WooCommerce, Magento, headless)
- Fit certification: "TryOn Certified" badge on products with high fit confidence
- Return insurance: brands pay a flat fee per TryOn-attributed order, we guarantee a return rate below X%
- Data licensing: anonymized fit/trend data sold to brands, manufacturers, and supply chain companies

**Who we beat:** True Fit. They have 350M SKUs but no consumer relationship. We'll have the consumer AND the brand AND the data. That's the full stack.

---

## 7. What Could Kill Us (Honest Assessment)

| Threat | Probability | Severity | Mitigation |
|---|---|---|---|
| Google makes VTO standard and free | HIGH | MEDIUM | They commoditize "looks okay"; we own "actually fits." Differentiate on accuracy + analytics + consumer identity. |
| True Fit moves downmarket | MEDIUM | HIGH | They're enterprise DNA — moving to SMB is culturally hard. We need to lock in Shopify brands fast before they try. |
| Shopify builds native try-on | LOW-MEDIUM | CRITICAL | Partner closely, become the de-facto Shopify try-on. Get into the Shopify App Store fast with reviews and case studies. |
| CLO3D raises prices or restricts assets | LOW | MEDIUM | Build garment digitization pipeline; support Browzwear and open-source alternatives. |
| Consumer privacy backlash (body data) | MEDIUM | HIGH | Transparent data practices, GDPR compliance, on-device processing where possible, clear consent flows. |
| A well-funded startup copies us | MEDIUM | MEDIUM | Our moat is the data flywheel — network effects compound. First-mover with data wins. |

---

## 8. Brands That Could Outplay Us (and Why They Won't)

### True Fit
- **Their edge:** 350M SKU database, 180+ brand partnerships, 62.7% market share in fit engines
- **Their weakness:** No 3D visualization, no consumer-facing product, enterprise-only pricing, slow innovation
- **Why they won't win:** They're a B2B data company. They don't own the consumer relationship. When we have the consumer AND the data, their network advantage erodes.

### Google
- **Their edge:** Infinite distribution, massive AI research budget, Shopping Graph with billions of listings
- **Their weakness:** No fit accuracy (diffusion models hallucinate fit), no persistent consumer identity, no brand-level analytics, no size recommendation
- **Why they won't win:** They'll commoditize basic try-on. That helps us — it trains consumers to expect try-on everywhere. We're the premium layer on top: "Google shows you what it looks like. TryOn tells you if it fits."

### Style3D
- **Their edge:** Strong 3D simulation tech, design-to-try-on pipeline, growing brand partnerships
- **Their weakness:** No consumer platform, no cross-store identity, focused on design workflow not shopping experience
- **Why they won't win:** They're a tool for designers, not a platform for shoppers. Different market.

### Snap (Fit Analytics)
- **Their edge:** $124M invested, strong ML, recently re-independent
- **Their weakness:** Lost momentum during Snap ownership, no clear go-to-market post-divestiture, damaged brand trust
- **Why they won't win:** They had the chance and fumbled it. Snap shut down ARES because the economics didn't work for them. Fit Analytics is rebuilding — they're 2 years behind.

---

## 9. The Unfillable Moat: Why We Can Be the Biggest

No one else has all four of these simultaneously:

1. **The Body Graph** — SMPL avatars + fit passports for every consumer, getting smarter with every try-on
2. **The Fit Graph** — Per-brand, per-garment, per-body-shape fit data, with return correlation
3. **The Taste Graph** — Closet + wishlist + browsing behavior across multiple stores
4. **The Attribution Engine** — Full-funnel analytics proving ROI to brands, creating switching costs

True Fit has #2 (partially). Google has distribution. Stitch Fix had #3 (via surveys, not behavior). Nobody has all four.

**The company that connects a consumer's body, their taste, and a brand's inventory with provable ROI will own fashion e-commerce.** That's TryOn.

---

## 10. The Three Missing Weapons (Technical Moonshots)

The current stack is strong enough to win the Shopify SMB market. But to kill the entire market — to make TryOn the only platform that matters — we need three technical breakthroughs. These are the weapons nobody else has, and building them first is how we become unkillable.

### 10.1 Weapon 1: Photorealistic Avatars from a Single Selfie

**What we have now:** SMPL parametric avatars. They're geometrically accurate (correct body shape, measurements) but visually abstract — they don't look like the shopper.

**What we need:** A shopper uploads one selfie → within seconds they see a photorealistic 3D version of themselves that looks like them (skin tone, hair, face, body) wearing the garment.

**Why this is the kill shot:** The moment a shopper sees THEMSELVES — not a mannequin, not a generic avatar — in a garment, the emotional connection to the product skyrockets. This is the difference between "I think this might fit" and "I can see myself wearing this." Stitch Fix's "Vision" tool (generative AI outfit images) already proved this increases engagement dramatically. We do it in real 3D.

**State of the art (April 2026):**

| Method | What It Does | Speed | Quality | Status |
|---|---|---|---|---|
| IDOL (CVPR 2025) | Feed-forward transformer → 3D Gaussian avatar from single image | <1 second | High (full body, animatable) | Research, code available |
| HumanLift (SIGGRAPH Asia 2025) | Multi-view diffusion + 3D Gaussian Splatting with SMPL-X guidance | ~30 seconds | Very high (facial detail, free-view) | Research |
| HumanWan-DiT | Diffusion transformer that synthesizes multi-view RGB + normals from single photo | ~10 seconds | High (3D-consistent views) | Research |
| ETRI Framework | Hyper-realistic talking face from single photo | Real-time | Very high (face only) | Deployed in Korea |
| StyleAvatar (SIGGRAPH 2023) | Compositional face+body decomposition for real-time rendering | Real-time | High (portrait focus) | Research, partially open |

**Our execution plan:**

We have access to the **Persona repo** — a photorealistic avatar generation pipeline. The plan is to deploy this on our own dedicated server infrastructure, giving us full control over the pipeline, latency, and quality.

1. **Phase A (Now – 2 months):** Deploy the Persona pipeline on a dedicated GPU server (e.g., Railway GPU, Hetzner dedicated, or a cloud A100 instance). Wire it into the TryOn onboarding flow: shopper uploads selfie → Persona generates photorealistic 3D avatar → stored and used across all try-on sessions.
2. **Phase B (2–6 months):** Fine-tune the Persona model on our own data. Every avatar we generate is training data. Optimize for fashion-specific requirements: full-body quality (not just face), consistent lighting for garment draping, and accurate body proportions matching the SMPL fit passport.
3. **Phase C (6–12 months):** Real-time rendering with pose/expression. Shopper sees themselves moving, turning, posing in the garment. The "digital mirror" experience.

**Why self-hosted:** Third-party APIs add latency, cost per call, and dependency risk. Owning the inference server means we control quality, speed, and cost. As volume scales, per-avatar cost drops to near zero.

**Who's doing this today:** Nobody in production for fashion e-commerce. Google VTO uses 2D diffusion (flat image, not 3D). 3DLOOK does body scanning but not visual appearance. Reactive Reality does AR overlay but not true 3D reconstruction. This is genuinely unoccupied territory.

**Infra cost estimate:** Dedicated GPU server (A100 or equivalent): $1.5K–3K/month. Handles thousands of avatar generations per day. Scales horizontally when needed.

---

### 10.2 Weapon 2: Interaction Heatmaps & Attention Analytics

**What we have now:** Funnel analytics (opened → tried on → carted → purchased), dwell time, device breakdown. We know WHAT happened.

**What we need:** Visual heatmaps showing WHERE shoppers look, WHAT they interact with, and HOW they engage with the 3D garment. We need to know if they're staring at the collar, rotating to check the back, zooming into the fabric, or immediately scrolling away.

**Why this is the kill shot:** This is the data that product designers and merchandisers would kill for. Currently they rely on surveys, focus groups, and gut instinct. With heatmaps, we can tell a brand: "72% of shoppers who viewed this jacket spent >5 seconds examining the back panel, but only 12% added to cart. Your back design is getting attention but not converting." That's actionable intelligence no one else provides.

**We build this ourselves. No third-party tools. Our own stressmaps.**

The term "stressmap" is more accurate than "heatmap" for what we're building — it captures not just where shoppers look, but where the garment is under stress (fit tension), where attention concentrates, and where the decision breaks down. Three layers:

| Layer | What It Tracks | Value | How We Build It |
|---|---|---|---|
| **Garment Stressmap** | Where on the 3D garment shoppers rotate, zoom, touch, and linger | Shows which design features attract attention or cause concern | Instrument our Three.js viewer: track raycasted mesh intersection points, orbit angles, zoom events, touch durations. Aggregate per-vertex across all sessions into a heat-colored 3D mesh. |
| **Fit Stressmap** | Where the garment is tight, loose, or deforming on the avatar | Shows fit problems before they become returns | Compute per-vertex distance between garment mesh and body mesh. Visualize tension zones (red = tight, blue = loose). This is the data CLO3D shows designers — we show it to brands automatically. |
| **Decision Stressmap** | Which size/color combinations get explored vs. purchased vs. abandoned | Shows exactly where shoppers hesitate | We already track size_viewed, size_selected, add_to_cart events. Visualize as an interactive matrix (product × size × action) with color intensity proportional to drop-off. |

**Our execution plan:**

1. **Phase A (1–2 months):** Garment interaction stressmap. Instrument the Three.js viewer to emit raycasted touch/hover coordinates on the 3D mesh surface. Store as analytics events with mesh UV coordinates. Build an aggregation endpoint that returns per-vertex heat values. Render as a colored 3D mesh overlay in the brand dashboard. This is pure engineering — no ML, no external dependencies.
2. **Phase B (2–4 months):** Fit stressmap. Compute garment-to-body mesh proximity after draping. Requires vertex-level distance calculation between the garment and SMPL avatar surfaces. Visualize tension/gap zones. This turns every try-on session into a fit engineering report.
3. **Phase C (4–8 months):** Decision stressmap + combined dashboard. Unify all three layers into a single "Product Intelligence" view per garment. Brand sees: the 3D garment color-coded by shopper attention, the fit tension zones, and the size exploration funnel — all in one place.

**Why we build in-house:** Hotjar and FullStory track 2D page clicks. That's useless for 3D. Nobody has 3D garment interaction analytics because nobody else has the 3D try-on viewer + the analytics pipeline + the body mesh data. We have all three. Building this ourselves means it's deeply integrated, fast, and becomes a proprietary data asset.

**Who's doing this today:** Absolutely nobody. Not Hotjar. Not Google Analytics. Not any fashion-tech company. 3D interaction analytics for fashion garments does not exist as a product category yet. We create the category.

**Cost:** This is engineering, not research. Phase A: 2–4 weeks of frontend + backend work. Phase B: 2–4 weeks of geometry computation. Phase C: 2–4 weeks of dashboard visualization. Total: 2–3 months of focused engineering. No external spend.

---

### 10.3 Weapon 3: AI-Powered 3D Garment Generation (The CLO3D Killer)

**What we have now:** Brands upload professionally made CLO3D garments (.glb files). This works but creates a massive onboarding bottleneck — CLO3D garments take hours to create per SKU, require specialist skills, and cost $50–200 per garment to produce.

**What we need:** A brand uploads product photos (the same ones on their Shopify store) → our AI generates a physics-accurate 3D garment mesh within minutes → ready for try-on. No CLO3D expertise needed. No manual work. 99.9% of the quality at 0.1% of the effort.

**Why this is the kill shot:** This single capability removes the #1 barrier to adoption. Right now, every brand we onboard has to either (a) already have 3D garments (almost nobody does) or (b) we create them manually (doesn't scale). If we automate this, any brand with product photos can have 3D try-on in 24 hours. That unlocks the entire market.

**State of the art (April 2026):**

| Method | Input | Output | Quality | Speed | Status |
|---|---|---|---|---|---|
| GarmentDiffusion (IJCAI 2025) | Multimodal (text + sketch + image) | Vectorized sewing patterns | High accuracy, 100x faster than SewingGPT | Seconds | Research |
| GarmentCrafter (CMU, 2026) | Single product image | Editable 3D mesh with multi-view consistency | Good (progressive depth prediction) | Minutes | Research |
| GarmentDreamer | Text/image prompt | 3D Gaussian textured mesh (simulation-ready) | Medium-High | Minutes | Research |
| Guo & Sun (2025) | Product image → diffusion → 3D recon → sewing pattern | Full 2D→3D→2D pipeline | High (validated against manual patterns, 19% lower error than NeuralTailor) | Minutes | Research |
| fashionINSTA | AI image → .DXF sewing pattern | Production-ready patterns from AI visuals | Connects to actual garment geometry | — | Commercial (early) |
| Style3D | 3D simulation + AI body mapping | Design-to-try-on pipeline | High (physics-based) | — | Commercial |

**The key insight:** The research has converged on a clear pipeline:
```
Product photo → Multi-view diffusion (generate front/back/side views)
    → 3D mesh reconstruction (from multi-view images)
    → Sewing pattern extraction (for physics simulation)
    → Physics draping on body (using SMPL avatar)
```

Each of these steps has recent, high-quality research implementations. Nobody has combined them into a single production pipeline for fashion e-commerce.

**This is our biggest bet. We raise money and hire a dedicated team to build this.**

**Why this requires a team and funding:**
- This isn't a feature you bolt on. It's a new AI system — a "CLO3D but fully automated" — that requires custom model training, massive compute, and deep expertise in 3D reconstruction, physics simulation, and generative AI.
- The quality bar is 99.9%. Fashion brands will not accept "good enough" 3D garments. The seams need to be right. The fabric weight needs to feel right. The collar needs to drape correctly. This is precision engineering meets ML research.
- The payoff is proportional: if we nail this, every fashion brand on Earth with product photos (which is all of them) can have 3D try-on overnight. The onboarding bottleneck disappears. The TAM explodes.

**Our execution plan:**

**Phase A — Raise & Recruit (0–3 months):**
- Raise a seed/pre-seed round. This capability is the core pitch: "We're building the AI that turns product photos into physics-accurate 3D garments. Combined with our existing try-on platform, analytics, and consumer identity layer, this makes us the infrastructure layer for fashion e-commerce."
- Hire 2–3 specialists: (1) 3D reconstruction / generative AI researcher, (2) physics simulation engineer (cloth sim, FEA), (3) ML infrastructure / training pipeline engineer.
- Set up dedicated GPU cluster for training (8× A100 or H100 equivalent).

**Phase B — Semi-Automated Pipeline (3–9 months):**
- Build the first version: brand uploads front + back product photos → multi-view diffusion generates remaining views → 3D mesh reconstruction → texture mapping → human QA pass → ready for try-on.
- Target: reduce per-garment creation time from 4+ hours (manual CLO3D) to 30 minutes (AI + QA).
- Quality target: 90–95%. Acceptable for most garment types (t-shirts, hoodies, pants, jackets).
- Every garment we create becomes training data for the next phase.

**Phase C — Full Automation (9–18 months):**
- Fine-tune GarmentDiffusion / GarmentCrafter architectures on our own dataset (hundreds of CLO3D garments + the semi-automated outputs from Phase B).
- Integrate sewing pattern extraction for physics accuracy (garment panels, stitch lines, fabric properties).
- Target: brand uploads photos → production-ready 3D garment in <5 minutes, no human intervention.
- Quality target: 95–99%. Handles complex garments (layered jackets, draped dresses, structured collars).

**Phase D — Physics Engine & The Endgame (18–30 months):**
- Real-time physics simulation: garments drape, stretch, and move based on inferred fabric properties (weight, elasticity, stiffness).
- Combined with photorealistic avatar (Weapon 1): shopper sees themselves in a garment that behaves like real clothing.
- Quality target: 99.9%+. Indistinguishable from a photograph.
- This is the moment we kill the market. Every brand. Every garment. Every body. Perfect fit, perfect look, zero returns.

**Who's doing this today:**
- **fashionINSTA:** Closest commercial player (AI images → DXF patterns), but focused on design/production, not consumer try-on.
- **Style3D:** Strong 3D simulation but still requires manual garment creation input.
- **Google:** Uses diffusion models but generates flat 2D images, not 3D meshes. No physics, no fit accuracy.
- **Nobody** has the full image-to-3D-to-physics-to-tryon pipeline in production.

**Funding estimate:**
- Seed round target: $500K–1.5M
- Team (3 specialists × 18 months): $400K–700K
- Compute (GPU cluster): $100K–250K
- Dataset & tooling: $50K–100K
- Total for Phase A–C: $550K–1.05M
- Phase D (physics engine): additional $500K–1M (or Series A territory)

**The pitch to investors:** "Fashion e-commerce loses $250B/year to returns. 45% are fit-related. We've built the only platform that combines 3D body avatars, virtual try-on, cross-store consumer identity, and full-funnel attribution analytics — already live on Shopify. The missing piece is automated 3D garment generation: the technology that turns any product photo into a physics-accurate 3D garment ready for try-on. This unlocks every fashion brand as a customer. We're raising to build the AI team that makes this real."

---

### 10.4 Combined Impact: The Full Stack Nobody Else Has

When all three weapons are deployed, the TryOn stack looks like this:

```
Shopper takes a selfie
    → Persona server generates photorealistic 3D avatar (Weapon 1 — our server)

Brand uploads product photos
    → Our AI team's pipeline generates physics-accurate 3D garment (Weapon 3 — funded team)

Shopper opens try-on
    → Their realistic avatar wearing the actual garment, draping correctly
    → Size recommendation based on body measurements
    → Every interaction tracked: stressmaps on the mesh surface (Weapon 2 — built in-house)

Brand dashboard shows:
    → 3D stressmap: "Shoppers spend 8x longer looking at the collar — zooming in, rotating around it"
    → Fit stressmap: "The shoulder area shows tension in sizes S and M — suggest updating fit guide"
    → Decision stressmap: "72% of shoppers view size M but 40% switch to L before carting"
    → Time-series: conversion climbing week over week
    → Fit-to-purchase: "When recommendation is followed, return rate drops from 23% to 2%"
```

**No company on Earth has this stack.** Google has distribution but no accuracy. True Fit has data but no visualization. CLO3D has garment quality but no consumer platform. 3DLOOK has body scanning but no garments. Stitch Fix had personalization but no 3D.

TryOn has: body + garment + visualization + personalization + analytics + network.

That's how you kill the market.

---

### The Execution Summary

| Weapon | How We Build It | Timeline | Cost |
|---|---|---|---|
| **Photorealistic Avatars** | Deploy Persona repo on our own GPU server. Fine-tune on our data. | 0–12 months | $1.5K–3K/month (server) |
| **Stressmaps** | Build in-house. Instrument Three.js viewer. Pure engineering. | 0–8 months | $0 (engineering time only) |
| **AI 3D Garments** | Raise money. Hire a dedicated 3-person AI team. Build the CLO3D killer. | 0–30 months | $550K–1.5M (seed round) |

**Stressmaps are the cheapest and fastest win** — pure frontend + backend engineering with no ML, no compute costs, and no external dependencies. This should start immediately alongside everything else.

**Persona avatars are the next fastest** — deploy existing tech on a server. The infrastructure cost is minimal. Fine-tuning is iterative and uses data we're already generating.

**AI garment generation is the biggest bet** — it requires capital, a team, and time. But it's also the biggest payoff. This is what makes TryOn the infrastructure layer for all of fashion e-commerce.

---

### The Endgame

---

## 11. The Data Flywheel: What Pattern + Preference + Stress Data Unlocks

The three weapons are not just features. They are **data generators**. Every garment we process produces pattern geometry. Every try-on session produces stress data. Every purchase/return produces preference signals. When these three datasets are linked, they create something that has never existed in fashion — a universal intelligence layer connecting garment construction to human bodies to purchase behavior.

Here's what becomes possible:

### 11.1 Pre-Launch Return Prediction

A brand uploads a new garment design. Before it ships a single unit, we simulate it on our body database (thousands of real body shapes from real shoppers). We compute the stress zones per size. We cross-reference against historical stress-to-return correlations.

**Output:** "Size M will have a 28% return rate for hourglass body types due to hip tension. Widen the hip panel by 1.5cm to drop returns to 8%."

The brand fixes the pattern before manufacturing. Returns prevented before they exist. This alone saves brands millions.

### 11.2 Automated Pattern Optimization

We feed the stress + return correlation data back into the pattern itself. The system suggests specific geometric changes:

- "Move this seam 4mm outward"
- "Add 2cm to the back panel for sizes L-XL"
- "This collar angle causes 72% of shoppers to zoom in but only 12% to buy — the proportion is off"

We become the system that makes garments **fit better**, not just the system that shows how they look. Brands go from guessing to engineering their fit.

### 11.3 Cross-Brand Fit Translation (The Universal Fit Passport)

We know the pattern geometry of Brand A's medium shirt and Brand B's medium shirt. We know the shopper's exact body. We can say:

> "You're a perfect M in Zara's slim-fit, but you need an L in H&M's relaxed cut — and here's exactly why, based on the actual 3D pattern overlap with your body."

Not based on size charts. Based on real geometry. This is the fit passport taken to its final form — it works across every brand we've ever processed.

### 11.4 Trend Detection from Attention + Preference

If thousands of shoppers across multiple brands are consistently spending 5+ seconds zooming into oversized collars, and conversion on those garments is climbing — that's a **design trend signal** weeks or months before it shows in sales data. We see what shoppers *want to want*.

Brands would pay a fortune for: "Oversized collar attention is up 340% this month across all brands. The top 3 garments by zoom-attention share these pattern characteristics."

### 11.5 Generative Design — "Design for This Body"

Given a body shape profile and that person's preference history (what patterns they bought, what stress zones they tolerated, what styles they gravitated to), we can **generate a garment pattern optimized specifically for them**.

Not "size M" — a pattern shaped for that individual body. This is where mass customization meets AI generation. We're no longer showing people clothes that exist. We're designing clothes that *should* exist.

### 11.6 Fabric Intelligence

Stress data tells us where the garment is under tension. Pattern data tells us the construction. Combined:

> "This jacket's shoulder panel shows consistent stress for athletic builds. The current fabric (95% cotton, 5% elastane) doesn't have enough give. Recommend 92% cotton, 8% elastane for sizes L-XXL."

We advise brands on material science using real fit data at scale. No more guessing fabric composition — let the stress data tell you what the garment needs.

### 11.7 The Fit Graph

Every garment pattern → linked to every body shape that tried it → linked to every stress point → linked to every purchase/return outcome → linked to every preference signal.

A universal knowledge graph. Like Google's search index, but for the relationship between human bodies and clothing. The more data flows in, the smarter every prediction gets. This is an **exponential flywheel** that no competitor can replicate without simultaneously having all three data sources (patterns, stress, preferences) at scale.

### 11.8 Brand Intelligence as a Service

We stop being "a try-on widget." We become the analytics and design intelligence platform. Brands subscribe for:

- "Tell me what to design next"
- "Tell me which sizes to stock more of"
- "Tell me which garments will have the highest return rate before I manufacture them"
- "Tell me where my competitor's fit weaknesses are"
- "Optimize my patterns to reduce returns by 40%"

This is Palantir for fashion, built on proprietary data nobody else can collect.

---

## 12. The Final Endgame: Social Commerce & The 3D Shopping Feed

Everything above is about Shopify stores and brand dashboards. That's Phase 1. The real endgame is bigger.

### 12.1 The Vision: Scrolling Becomes 3D Shopping

Imagine a shopper scrolling Instagram or Facebook. Instead of flat product photos, they see **themselves** — their photorealistic avatar — wearing the garment. Personalized to their body shape, their style preferences, their fit history. Powered by the Fit Graph.

```
Shopper opens Instagram
    → Feed shows personalized 3D try-on cards
    → Each card: their avatar wearing a garment from a brand they'd like
    → Swipe right: "I want this" → saved to TryOn wishlist
    → Tap: full 3D try-on experience opens inline
    → Buy: one-tap checkout, perfect size pre-selected
    → The garment arrives. It fits. No return.
```

This isn't science fiction. Every piece of this exists or is being built:
- Meta already has 3D ad formats and AR try-on experiments
- Instagram Shopping already embeds product cards in feeds
- We already have the avatar, the garment, the fit engine, and the consumer identity
- The missing piece was the data layer that makes it personalized and accurate — which is exactly what Sections 10 and 11 build

### 12.2 The Integration: TryOn as Meta's Fit Layer

Meta's business model is advertising. Fashion brands are their biggest ad spenders. If TryOn can prove that "personalized 3D try-on ads convert 5x better than flat image ads with 60% fewer returns," Meta has every incentive to integrate us.

**The play:**
1. Build a Meta Shops integration — brands connect their TryOn garment library to their Instagram/Facebook shop
2. Shoppers who have a TryOn avatar see personalized 3D cards in their feed
3. Every interaction feeds back into the Fit Graph — the scroll, the pause, the zoom, the save, the purchase
4. We become the **fit and personalization layer** that sits between Meta's ad platform and fashion brands' catalogs

**Revenue model at this stage:**
- Per-impression fee for personalized 3D cards (fraction of a cent × billions of impressions)
- Revenue share on purchases driven through personalized try-on
- Premium analytics tier for brands running Meta campaigns through our fit layer

### 12.3 The Consumer Loop: Personalized Commerce at Scale

The Fit Graph doesn't just serve brands. It serves consumers:

- **Personalized discovery:** "Based on your body, your style preferences, and garments that people shaped like you loved, here are 12 pieces you'll want this week." Not based on browsing history — based on 3D fit compatibility.
- **Cross-platform identity:** Shopper tries on at Zara's Shopify store, sees recommendations on Instagram, checks their closet on tryon.global, buys from H&M through a Meta ad — all connected through one body, one identity, one fit passport.
- **Zero-friction checkout:** Size is pre-selected. Fit is guaranteed. One tap. No size anxiety. No returns.

This is what "personalized shopping, just like how AI is personalized" actually looks like when you build it from 3D body data up.

### 12.4 Why This Is Ours to Take

Meta doesn't have the 3D garment data. Google doesn't have the body data at consumer scale. Shopify doesn't have the fit intelligence. Amazon doesn't have the stressmaps. Stitch Fix is dead. True Fit has data but no visualization.

We are the **only company** building all four layers simultaneously:

| Layer | What It Is | Who Else Has It |
|---|---|---|
| **Consumer Identity** | 3D body + fit passport + preference history | Nobody at consumer scale |
| **Garment Intelligence** | Pattern data + AI generation + physics | Nobody automated |
| **Interaction Intelligence** | Stressmaps + attention + decision analytics | Nobody in 3D |
| **Commerce Integration** | Shopify + Meta + cross-store wishlist + checkout | Nobody with fit data |

The convergence of these four layers is a new category. Not "virtual try-on." Not "fashion analytics." Not "social commerce."

**It's the personalization infrastructure for fashion.**

And it's free for consumers. Always.

---

## 13. The Path

### Phase 0: Prove It with Ramin Studios (NOW — before raising)

Before we raise a cent, we need data. Real data from a real brand with real shoppers making real purchases. Ramin Studios is that brand. Everything we've built — the Shopify widget, the analytics pipeline, the consumer dashboard, the fit engine — gets validated here.

**What we need from Ramin Studios before we raise:**
- **Conversion lift:** TryOn sessions → add-to-cart rate vs. baseline (non-TryOn shoppers)
- **Return reduction:** Return rate for TryOn-assisted purchases vs. standard purchases
- **Engagement depth:** Average dwell time, size exploration patterns, repeat visitor rates
- **Attribution clarity:** % of purchases that touched TryOn, same-session vs. return-visit
- **Consumer adoption:** Onboarding completion rate, avatar creation rate, wishlist usage

This is the pitch deck data. "Ramin Studios saw X% conversion lift and Y% fewer returns in Z weeks with TryOn." That's what opens checkbooks.

**The focus is singular: make the Ramin Studios pilot airtight. Every bug fixed. Every metric tracked. Every interaction captured.**

### The Roadmap

```
NOW (This week)
  │
  ├── Ramin Studios pilot live on Shopify
  ├── Analytics dashboard capturing all events
  ├── Consumer dashboard (closet, wishlist, cross-store try-on)
  ├── Webhook tracking purchases + returns
  ├── Focus: polish, fix bugs, ensure data quality
  │
  ▼ AFTER FRIDAY (Next week)
  │
  ├── Deploy Persona avatar server on RunPod (photorealistic avatars)
  ├── Wire into TryOn onboarding: selfie → realistic 3D avatar
  ├── Continue collecting Ramin Studios data
  │
  ▼ WEEKS 2–8: DATA COLLECTION + STRESSMAPS
  │
  ├── Accumulate Ramin Studios metrics (conversion, returns, engagement)
  ├── Build garment interaction stressmaps (instrument Three.js viewer)
  ├── Build fit stressmaps (garment-to-body mesh proximity)
  ├── Build decision stressmaps (size exploration visualization)
  ├── Fine-tune Persona on real shopper data
  │
  ▼ MONTH 3: FUNDRAISE
  │
  ├── Pitch deck backed by Ramin Studios data
  ├── Live demo: photorealistic avatar + stressmaps + full analytics
  ├── Raise seed round ($500K–1.5M) for AI garment generation team
  │
  ▼ MONTHS 3–12: BUILD THE TEAM + SCALE
  │
  ├── Hire 3 AI specialists (3D reconstruction, physics, ML infra)
  ├── Semi-automated garment generation pipeline (photos → 3D in 30 min)
  ├── Fit Graph v1: pattern + stress + preference linked per garment
  ├── Onboard 5–10 more brands using semi-automated pipeline
  │
  ▼ MONTHS 12–24: AUTOMATE + EXPAND
  │
  ├── Fully automated garment generation (<5 min, no human)
  ├── Pre-launch return prediction (simulate on body database)
  ├── Cross-brand fit translation (universal fit passport)
  ├── Trend detection from aggregated attention data
  ├── Meta Shops integration (personalized 3D cards in feed)
  │
  ▼ MONTHS 24–36: DOMINATE
  │
  ├── Real-time physics engine (garments drape and move realistically)
  ├── Generative design ("Design for This Body")
  ├── Social commerce at scale (scrolling = 3D shopping)
  ├── Brand Intelligence as a Service
  │
  ▼ THE ENDGAME
  │
  └── TryOn is the personalization infrastructure for all of fashion.
      Every brand. Every garment. Every body. Every platform.
      Free for consumers. Always.
```

---

*This document is strategic research for internal use. Market data sourced from Grand View Research, Mordor Intelligence, Ringly.io, Forbes, TechCrunch, Vogue, Capital One Shopping, CVPR 2025, SIGGRAPH 2025, IJCAI 2025, CMU GarmentCrafter, and primary competitive analysis. Last updated 2026-04-15.*
