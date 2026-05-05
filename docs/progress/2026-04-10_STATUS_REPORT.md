# Status Report — 2026-04-10 → 2026-04-15 (updated Apr 15)

## Summary

Since the last report (Apr 10), the platform went from "viewer works, cart is broken" to a **fully functional end-to-end system**: Add to Cart working, purchase webhooks tracking, Wishlist/Closet feature live, shopper dashboard overhauled, brand analytics expanded to Palantir-for-fashion level with 15+ new metrics, and a comprehensive market research & strategy document completed. The Ramin Studios pilot is now the sole focus for data collection before fundraising.

---

## Completed since Apr 10

### Add to Cart (PDP widget) — DONE
- Fixed the `TRYON_ADD_TO_CART` postMessage flow with inline fallback in `tryon-button.liquid` (no longer depends on external `tryon-cart.js` loading)
- Variant resolution via `__tryonSizeVariantMap`, cart UI refresh via Section Rendering API
- Verified working on the live Ramin Studios Shopify theme

### Shopify Webhooks — DONE
- **`orders/paid`** webhook integrated: HMAC-verified, tracks purchases in `analytics_events`, enriches with `brand_id`, `user_id`, `tryon_session_id`
- **`refunds/create`** webhook added: tracks returns with refund line item details
- Bracketing detection (multiple sizes of same product in one order) implemented
- Purchased items auto-populate the shopper's "Closet" via `saved_items` table

### Wishlist / Closet Feature — DONE
- New `saved_items` table with RLS policies (`list_type`: wishlist or closet)
- Heart button on PDP widget to save items to wishlist (with fallback `user_id` auth for cross-origin iframe)
- Shopper dashboard sidebar with **My Closet** (purchased items) and **Wishlist** (saved items) tabs
- "Try On" from dashboard opens modal with full 3D viewer
- "View on Store" redirect button to PDP for checkout

### TryOn Viewer (Dashboard) — DONE
- Ported geometry-based scaling from `test-viewer.html` (bounding box normalization, foot alignment, Z pushback)
- Static models (removed breathing animation)
- White background, no floor shadow
- Interactive controls: one-finger rotate, scroll zoom, two-finger pan
- `GARMENT_Z_PUSHBACK = -0.010` on both dashboard and PDP widget
- Robust close button (external to iframe, z-index 1000000)
- WebGL context loss/restoration handling for avatar persistence across tab switches

### Brand Analytics Dashboard — DONE (15+ new metrics)

**Phase 1 — Core enhancements:**
- Full funnel visualization (widget opens → try-on → ATC → purchase)
- Cart abandonment rate, same-session conversion %, avg time to purchase
- `size_viewed` event emission from widget

**Phase 2 — Returns & bracketing:**
- Return tracking (total returns, return rate, revenue lost, avg days to return)
- Bracket order detection and rate
- TryOn cohort vs baseline comparison
- Return risk scoring per order

**Phase 3 — Engagement & device:**
- Dwell time analytics (avg seconds, histogram buckets)
- Device/browser breakdown
- Repeat visitor tracking

**Phase 4 — Fit intelligence:**
- Per-product fit confidence scores
- Body shape insights (measurements → recommendations → purchased sizes)
- **Time-series trends** (weekly conversion %, ATC %, return rate, revenue)
- **Fit-to-purchase correlation** (accepted recommendation vs. deviated → purchase/return rates)

**Frontend:** 5-tab brand dashboard (ROI & Attribution, Fit Intelligence, Trend & Demand, Returns & Risk, Engagement) with Recharts visualizations, metric grids, and detailed data tables.

### Market Research & Strategy Document — DONE
- Created `docs/strategy/MARKET_RESEARCH_PRICING_AND_COMPETITIVE_EDGE.md` (719 lines)
- Competitive landscape analysis (lower/mid/upper tier + big tech)
- Feature-by-feature comparison matrix against all major competitors
- Pricing strategy with per-event model and SaaS tier benchmarks
- 4-phase "Kill Strategy" for market dominance
- **Section 10: Three Weapons** — Photorealistic avatars (Persona repo on RunPod), Stressmaps (built in-house), AI 3D garment generation (funded team)
- **Section 11: Data Flywheel** — What pattern + preference + stress data unlocks (pre-launch return prediction, automated pattern optimization, cross-brand fit translation, trend detection, generative design, Fit Graph)
- **Section 12: Social Commerce Endgame** — Meta integration, personalized 3D shopping feeds, TryOn as the fit layer for social commerce
- **Section 13: The Path** — Concrete roadmap from Ramin Studios pilot → fundraise → scale

---

## Current Focus (This Week)

**Ramin Studios pilot = data collection priority.** Everything is live. The goal is to accumulate real metrics:
- Conversion lift (TryOn sessions → ATC rate vs. baseline)
- Return reduction (TryOn-assisted vs. standard purchases)
- Engagement depth (dwell time, size exploration, repeat visitors)
- Attribution (% purchases touching TryOn)

**After Friday:** Deploy Persona avatar server on RunPod (photorealistic avatars from selfie).

---

### Size Recommendation Engine v2 — DONE
- Rewrote `sizeRecommendation.ts` with category-aware measurement weighting, garment-type ease profiles, asymmetric penalty scoring (tight penalised 1.5x more than loose), and confidence scoring (0–100)
- Backend API now returns `category` and `fit_type` from garment metadata to widget
- Both PDP widget and dashboard viewer consume the new algorithm
- **Future:** Train this logic on real purchase/return data from Ramin Studios pilot to continuously improve accuracy

### Cloth Simulation (Physics Draping) — IN PROGRESS

- **Problem:** CLO3D garments are sculpted on a single avatar body. When a different body shape loads, the static mesh doesn't re-drape — skin pokes through at areas where the new body is larger than the original.
- **Solution:** Dedicated RunPod serverless endpoint that runs geometric draping (XRTailor GPU sim when available, geometric fallback for now). Completely isolated from production — separate branch, separate endpoint, separate test page.

**What was built today (Apr 15):**

1. **RunPod Draping Endpoint** — new serverless Docker image (`avatar-creation/draping/`)
   - `handler.py`: orchestrates download → align → drape → convert → return base64 GLB
   - XRTailor GPU path (ready for when binary is deployed) + geometric fallback
   - RunPod endpoint ID: `e86juazm1b4mig`

2. **Auto-alignment system** (`align_meshes()`)
   - Compares body and garment height ranges, auto-scales if >20% mismatch
   - Centers garment XZ onto body XZ, aligns feet (bottom Y)
   - Undoes alignment after draping so vertex indices still match original OBJ for texture mapping

3. **Texture-preserving GLB conversion** (`inject_verts_into_glb()`)
   - Downloads the original garment GLB alongside the OBJ
   - After draping, injects the new vertex positions into the original GLB
   - Preserves all materials, textures, UVs, face topology — the logo stays visible
   - Falls back to bare trimesh conversion if original GLB isn't available

4. **Backend draping routes** (`backend/app/api/routes/draping.py`)
   - `POST /api/draping/request` — initiates draping, checks cache first
   - `GET /api/draping/status/{request_id}` — polls job status
   - `GET /api/draping/check` — checks cache for existing draped meshes
   - `POST /api/draping/precompute` — batch pre-computation for body shape clusters
   - `POST /api/draping/test-run` — direct RunPod call for isolated testing

5. **Body shape clustering** (`backend/app/services/body_clustering.py`)
   - Quantizes measurements into buckets for cache efficiency
   - Same body shape + same garment + same size → reuse cached draped mesh

6. **Supabase migration** (`backend/migrations/003_draping_tables.sql`)
   - `draped_meshes` table (cache: body_hash + garment_id + size → GLB URL)
   - `draping_requests` table (job tracking: status, RunPod job ID, timestamps)
   - `obj_sizes` and `fabric_config` columns added to `garments` table

7. **PDP Widget integration** (`frontend/public/test-viewer.html`)
   - Client-side draping request + polling + hot-swap of draped mesh
   - "Optimizing fit for your body..." indicator while draping runs
   - Falls back to static GLB if draping unavailable

8. **Dashboard integration** (`DashboardTryOnModal.tsx`)
   - Merges `draped_urls` from API into `model_urls` seamlessly
   - Viewer automatically displays draped mesh if cached

9. **Standalone test page** (`frontend/public/drape-test.html`)
   - Calls RunPod directly (bypasses Railway — safe for production)
   - Three.js viewer with normalizeModel() matching PDP widget scaling
   - Fields for RunPod API Key, Endpoint ID, Body OBJ, Garment OBJ, Garment GLB, Avatar GLB

10. **Deployment docs** (`avatar-creation/draping/DEPLOY.md`)
    - Full step-by-step: build Docker → push → create RunPod endpoint → test → wire to backend

---

## What Still Needs to Be Done (Priority Order)

1. **Test the updated draping build** — RunPod is rebuilding now with alignment + texture fixes. Verify `vertices_fixed > 0` in logs and that the logo/textures are preserved in the output GLB.
2. **Wire draping into production** — once verified, merge `drape` branch changes into `feature/analytics`, add `RUNPOD_DRAPING_ENDPOINT_ID` to Railway, deploy.
3. **Ensure data quality** — verify all analytics events firing correctly on live Ramin Studios store.
4. **Persona server on RunPod** — deploy photorealistic avatar pipeline, wire into onboarding flow.
5. **Garment interaction stressmaps** — instrument Three.js viewer with raycasted mesh coordinates.
6. **Fit stressmaps** — garment-to-body mesh proximity computation.
7. **Train size recommendation** — use real purchase/return data from Ramin Studios to improve v2 algorithm accuracy.
8. **Fundraise prep** — pitch deck backed by Ramin Studios live data + demo.

---

## Test URLs (Saved for Future Reference)

**Body OBJ (avatar T-pose mesh):**
```
https://cykwthsbrylonconqlfz.supabase.co/storage/v1/object/public/avatars/ca5808a9-99bd-45a2-86ec-f3f0f90db831/body_apose.obj
```

**Garment OBJ (CLO3D export — small-logo hoodie, size M):**
```
https://cykwthsbrylonconqlfz.supabase.co/storage/v1/object/public/garments/27ca6be1-55f6-4e94-b13f-49de33ac959a/small-logo/m.obj
```

**Garment GLB (Three.js visual preview — small-logo hoodie, size M):**
```
https://cykwthsbrylonconqlfz.supabase.co/storage/v1/object/public/garments/27ca6be1-55f6-4e94-b13f-49de33ac959a/small-logo/m.glb
```

**Avatar GLB (textured avatar for viewer):**
```
https://cykwthsbrylonconqlfz.supabase.co/storage/v1/object/public/avatars/ca5808a9-99bd-45a2-86ec-f3f0f90db831/avatar_textured.glb
```

### Local Test Commands

```bash
# Start the drape test page locally
cd frontend && npx serve public -p 3333
# Then open: http://localhost:3333/drape-test.html

# Build and push draping Docker image
cd avatar-creation/draping && bash build.sh

# Test draping handler locally (requires OBJ files on disk)
cd avatar-creation/draping && python handler.py --body-obj /path/to/body.obj --garment-obj /path/to/garment.obj

# Test with real Supabase data locally
cd avatar-creation/draping && python test_with_supabase.py
```

---

## Files / Branches (Reference)

| Area | Location |
|------|----------|
| PDP Viewer | `frontend/public/test-viewer.html` |
| PDP block + iframe | `shopify_app/extensions/tryon-widget/blocks/tryon-button.liquid` |
| Cart listener | `shopify_app/extensions/tryon-widget/assets/tryon-cart.js` |
| Webhooks (backend) | `backend/app/api/routes/webhooks.py` |
| Analytics (backend) | `backend/app/api/routes/analytics.py` |
| Wishlist (backend) | `backend/app/api/routes/wishlist.py` |
| Draping (backend) | `backend/app/api/routes/draping.py` |
| Body clustering | `backend/app/services/body_clustering.py` |
| Draping handler (RunPod) | `avatar-creation/draping/handler.py` |
| Draping Dockerfile | `avatar-creation/draping/Dockerfile` |
| Draping deploy guide | `avatar-creation/draping/DEPLOY.md` |
| Drape test page | `frontend/public/drape-test.html` |
| DB migration (draping) | `backend/migrations/003_draping_tables.sql` |
| Supabase service | `backend/app/services/supabase.py` |
| Brand dashboard | `frontend/app/brand/page.tsx` |
| Shopper dashboard | `frontend/app/dashboard/page.tsx` |
| TryOn viewer (dashboard) | `frontend/components/TryOnViewer.tsx` |
| Dashboard TryOn modal | `frontend/components/DashboardTryOnModal.tsx` |
| Saved items grid | `frontend/components/SavedItemsGrid.tsx` |
| Analytics charts | `frontend/components/analytics/Charts.tsx` |
| Size recommendation | `frontend/lib/sizeRecommendation.ts` |
| API client | `frontend/lib/api.ts` |
| Backend config | `backend/app/config.py` |
| Strategy doc | `docs/strategy/MARKET_RESEARCH_PRICING_AND_COMPETITIVE_EDGE.md` |
| Branch (analytics) | `feature/analytics` |
| Branch (draping) | `drape` |

---

## Note for Future Self

The platform is feature-complete for the pilot. Cloth draping is the last major technical gap — once the RunPod endpoint is verified with alignment + texture preservation, wire it into production and let it run. Ramin Studios is the proving ground — conversion lift and return reduction numbers are what open checkbooks. Persona server goes up after Friday on RunPod. The strategy doc is the fundraise playbook. Don't forget to test with the saved URLs above when the RunPod build finishes.
