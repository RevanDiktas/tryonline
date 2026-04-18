# Revenue, payment, and scale — lock-in (2026-04-03)

**Purpose:** Cut noise. Pick how we **get paid first**, how we **compound to real scale**, and where **tokenization / chain** fit without vapor.  
**Principle:** Shoppers do not pay TryOn for try-on. **Merchants and partners** pay. Same class as maps: free surface, B2B money.

---

## 1) Get paid first (do this in order)

### 1.1 Primary: merchant billing on the wedge you already chose

- **Shopify:** Use **Shopify Billing** (recurring app charges + optional usage components if/when the API supports your model). Money flows **brand → Shopify → you**. Shoppers never see a TryOn invoice.
- **Why first:** Lowest friction for a Shopify app, standard for App Store, reconcilable, no PCI for your core SKU.

### 1.2 Price shape (simple, defensible)

- **Base subscription** — platform, widget, dashboard, support floor (covers fixed cost and relationship).
- **Overage / usage** — avatars processed, try-on sessions, or GPU-weighted units above plan (aligns bill to COGS).
- **Optional later:** **success component** — % of **TryOn-attributed** revenue, contractually defined (harder ops; powerful story once attribution is bulletproof).

Do not launch with all three. Launch with **subscription + clear limits**; add usage meters when limits bite; add success fee when you have **clean session → order** proof brands trust.

### 1.3 What is *not* “payment first”

- **Shoppers paying per try-on** — kills adoption; contradicts the product story.
- **Building your own card vault / processor** before **merchant scale** — PCI, licensing, distraction (`SHOPPER_PASSPORT_VISION_AND_PLAN.md` already flags this). Passport can stay **addresses-first**; saved payment only when legal and product clearly need it.
- **A token or chain as the billing rail** — not the fastest path to dollars. Treat chain as a **layer**, not the merchant checkout.

**Lock-in sentence:** **Shopify Billing (and later Stripe Billing for non-Shopify brands) + subscription + usage overage** is payment first. Everything else is additive.

---

## 2) Tokenization, blockchain, BlackRock — where it actually helps (and when)

**Reality check:** Institutions talk “tokenization” mostly for **assets, settlement, and liquidity** (e.g. funds, RWAs), not so your fitting-room widget mints a coin.

**Useful mappings for TryOn (only if each solves a problem you already have):**

| Idea | What it could mean | When it’s worth engineering |
|------|--------------------|-----------------------------|
| **Payment tokenization** | PCI tokens via Stripe/Shopify — not blockchain | Already: use platforms; don’t roll your own card storage. |
| **Usage / entitlement tokens** | Internal credits for API/try-ons | Product pricing metaphor; can stay **off-chain**. |
| **Provenance / authenticity** | Garment or digital twin attestation | If luxury or compliance **pays** for verifiable lineage — **B2B**, not shopper coins. |
| **Cross-brand portable identity** | User-controlled fit profile | Your **account + legal agreements** are the MVP; chain only if partners refuse centralized trust **and** someone pays for that integration. |
| **Settlement / rev-share** | Automated splits with agencies or multi-party deals | **Late**; when partner volume justifies legal + engineering. |

**Lock-in sentence:** **Be “on the blockchain” when a specific counterpart requires trust-minimized settlement, provenance, or portability — and pays for it.** Until then, **win on merchant ROI, distribution, and data**; don’t lead with chain in the pitch or the stack.

---

## 3) How this becomes a multi-billion-dollar company (no fairy tales)

A multi-billion outcome is not “cool avatars.” It is **infrastructure + distribution**:

1. **Default try-on layer** on a large share of apparel PDPs (Shopify wedge → more platforms).
2. **Garment supply at scale** — automation so onboarding isn’t founder-artisan bound (`TRYON_FUTURE_VISION.md`: scale unlock).
3. **Network data** — fit and demand signals that improve recommendations and **merchant/buying** decisions (quant strategy).
4. **Expand revenue lines** — subscriptions + usage; later **enterprise APIs**, **data/analytics products** (aggregated), **services** where margin is high.

**Lock-in sentence:** Billions = **ubiquitous merchant adoption × recurring platform revenue × optional high-margin data/API**. Blockchain is optional accelerant, not the thesis.

---

## 4) Next steps this year (from 2026-04-03)

Phase right now: **Shopify MVP submitted** → focus is **real usage + proof**, not forcing revenue before the listing/install path is ready.

**Near-term deadline — YC:** **YC application due end of April 2026.** Traction and metrics matter **for that application**, not only for “later Series A.” Even **small but real** numbers on **one live merchant** beat vague multi-brand plans: sessions, funnel, anything you can cite honestly (friends + early customers still count if the product is live and behavior is real).

Ordered for **traction and a fundable story**:

1. **Single launch brand (only one for now):** **Ramin Studios** goes live **~two weeks** from early April 2026. There is **no second/third brand** in parallel for this phase—everything orbits **getting real people through TryOn on Ramin** (beyond the ~17 friend testers once the store is public).
2. **Prove ROI you can show** — **try-on session → order in production** is already built; before/submitting YC, capture **whatever slice of data exists**: counts, one attributed path, qualitative “they came back” if N is tiny. Honest > inflated.
3. **Prepare paid path** — **Shopify Billing** + one or two tiers when Partner / listing allows; **zero paying merchants** during review/pilot is fine in the story if usage and tech proof are strong.
4. **Tighten onboarding** — sub-10-minute merchant path; fewer manual steps per garment over time.
5. **Analytics that sell** — dashboards that answer “what do I do next?” not only charts (`QUANT_DATA_STRATEGY.md` direction).
6. **Defer heatmap to add-on** — monetize after core widget + analytics are sold and stable.
7. **Revisit chain/token** only after traction + a **named** B2B use case that pays for it.

**Funding lens:** **YC (end of month)** is the immediate **packaging** deadline for narrative + data. Longer term, **Series A (or equivalent)** still keys off **people like it + data + attribution**; revenue helps but isn’t the only lever if the product loop is convincing.

---

## 5) Where we are right now (founder update ~2026-04-03)

| Topic | Status |
|--------|--------|
| **Paying merchants** | **None** — intentional beat: MVP **handed in to Shopify**; testing / listing phase. |
| **Shopify Billing** | **Not the active milestone** until install / commercialization path is clear (align implementation with post-review reality). |
| **Users (~17)** | **Friends** testing TryOn ahead of **Ramin Studios** going live; push is **more real sessions on Ramin** once the store launches (~two weeks). |
| **Brands (pilot)** | **Only Ramin Studios** for now — **sole** launch brand; **~two weeks** to go live (as of early April 2026). No parallel second/third brand in this phase. |
| **Attribution** | **Yes — try-on sessions → order tied in production** (strong for ROI narrative, YC, and later raises). |
| **YC** | **Application: end of April 2026** — data and a crisp story **for YC** are the urgent reason to maximize honest traction before submit. |
| **Constraints** | No single “must ship by EOY” commercial requirement; **must** build toward the long-term plan with discipline. |

---

## 6) Open questions (optional — when useful)

1. **Ramin Studios** — exact launch URL / Shopify domain (for internal tracking only)?
2. **First dollar** — target month once app is **live and billable** on Shopify?
3. **Raise** — bootstrapped until proof, or active **Seed** conversations in parallel?
4. **Pricing taboos** — any line you won’t cross (e.g. never % of sales)?

---

*This doc is the operating lock-in until evidence changes it. Revise when listing status, first paid merchant, or pilot metrics materially move.*
