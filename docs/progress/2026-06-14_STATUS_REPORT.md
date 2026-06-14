# Status Report — 2026-06-14

Headline: **Rewrote the size-recommendation algorithm from a broken ease-matcher into a
true-to-fit, body-anchored engine, and shipped v1 to `feature/analytics` (Vercel).** The
old engine told a 192cm / 85kg shopper he was a size S on an oversized jacket. The new one
correctly says L (regular), M (slim), XL (loose), and explains why. Verified live in the
browser across tops / outerwear / bottoms / dresses, male + female, slim / regular /
oversized. Next session: verify the universality architecture note below (v1 vs v2) and
decide the v2 build.

Branch context: size-engine v1 committed to `feature/analytics` (deploys to Vercel).
Day-to-day work + this report stay on `feature/garment-construction`. The 4 fit files
remain as working-tree modifications on `feature/garment-construction` (same carryover
pattern as the Step-2 fix on 2026-06-13); harmless.

---

## WHAT SHIPPED TODAY — size recommendation v1 (true-to-fit)

Files committed to `feature/analytics`:
- `frontend/lib/sizeRecommendation.ts` — core rewrite
- `frontend/components/TryOnViewer.tsx` — new `measurementConvention` + `gender` props; girth
  conversion in the in-widget fit display
- `frontend/app/embed/page.tsx` — passes `flat` convention + `gender` from the avatar
- `frontend/components/DashboardTryOnModal.tsx` — passes `flat` + `gender` from the passport

### The three bugs that were fixed

**1. Flat vs circumference convention (silent, catastrophic).**
Merchant size charts are FLAT / half (e.g. 1/2 chest = pit-to-pit ~52cm). Body measurements
are full circumference (~104cm). The engine subtracted one from the other directly, so every
real garment read as ~50cm too tight and it recommended the biggest size (or garbage). Fix:
`convention: 'flat' | 'circumference'` param. When flat, girth fields (chest/waist/hips/
thigh/neck) are doubled before comparison; length/structural fields are never doubled. The
demo chart is circumference and unchanged (engine default), real callers pass `flat`.

**2. One ease target applied to every measurement.**
The old engine scored chest, shoulder, sleeve, torso all against the same girth ease target
(e.g. +8cm). A correctly-fitting shoulder seam (0 ease) read as "8cm too tight." Fix:
structural fields (shoulder/sleeve/inseam/torso) are now scored as length MATCHES (target
~0), not ease.

**3. THE BIG ONE — oversized garments shrank the shopper.**
The engine picked the size whose absolute ease was closest to a target. An intentionally
oversized garment (sample M = 130cm chest circ) gives every size huge ease, so the SMALLEST
size won the target. Result: a 192cm/85kg body got S. Ease-matching structurally cannot do
true-to-fit on oversized garments; it cancels the designer's oversize by shrinking you.

### The new model (true-to-fit, body-anchored)

1. Anchor on the shopper's REAL body (we extract 16 SMPL-Anthropometry measurements at avatar
   creation). A gender-aware standard scale (`BODY_SIZE_SCALE`) maps chest (tops/outerwear)
   or waist (bottoms) to a native size.
2. Recommended = native size mapped to the garment's matching LABEL. The garment's `fit_type`
   (oversized/slim) drives the EXPLANATION only, never the size. An oversized M is recommended
   as M for a native-M body.
3. Preference shifts by whole sizes: slim -1, regular 0, loose +1, clamped to available sizes.
4. Frame / length nudge: a shopper notably taller than the typical wearer of their girth size
   is sized up (tall-and-lean builds need the next size for length). Calibrated to Revan's
   real body: chest 102 + height 192 -> L; control chest 102 + height 178 -> stays M.
5. Reasoning copy spells out the why: "This is an oversized jacket. Based on your measurements
   you are a size L, so we recommend L for the intended relaxed fit." / slim -> "We recommend
   M because you chose a slim fit."

### Verified
- Logic tests against the REAL DAZ CANVAS HOODED JACKET and DAZ ESS WIDE PANTALON specs.
- Live in a real browser (temp `/fittest` page, since removed) across tops / outerwear /
  bottoms / dresses, male + female, slim / regular / oversized. All correct.
- Female control (168cm) -> M with no false height bump (gender-aware nudge).
- `npx tsc --noEmit` clean.

Revan's real extracted measurements (calibration anchor; dashboard shows 10 of 16):
height 192, chest 102, waist 88, hips 99, inseam 83, shoulder 38, arm 58, neck 38, thigh 48,
torso 71. Self-reported: wears M-to-L, mostly L due to length + shoulders. The engine now
matches this.

---

## LAFAM CHARTS — examined, and they reinforce the rebuild

Lafam's public size charts (`lafamamsterdam.com/pages/size-charts`) are 6 product-specific
IMAGES (Zippers, Jogging pants, Varsity Jacket, Pants, Spencer, Rico Tee) on their Shopify
CDN (store id `0642/5015/1152`). Read the Pants, Jogging pants, and Rico Tee images directly:
- **All alpha sizing** (XS-XXL / S-XL). No numeric. So the numeric-size gap (below) is NOT
  pilot-blocking.
- The charts are genuinely bad: only 3-4 rows of FLAT garment measurements each, missing key
  fields (Pants has no hips, no inseam), with broken grading (Pants waist = 35, 39, 40, 42,
  44). A tee "sleeve = 26cm" is not comparable to a body arm of 58cm.
- **Key point:** true-to-fit v1 is IMMUNE to bad charts because it anchors on the body, not
  the garment numbers. That uneven grading would have wrecked the old ease-matcher. This is
  the upgrade.
- What we actually need from Lafam per SKU is tiny: category + fit_type (their tees read
  oversized) + the size run. Chart measurements are optional polish.

---

## UNIVERSALITY — honest architecture note (verify next session)

The founder's requirement: the algorithm must be UNIVERSAL — "these measurements of this
human fit best with the measurements for this garment in this size," not specific to Lafam or
Ramin, and the shopper also sees it drape on their SMPL.

Honest state:
- **v1 (shipped):** universal ACROSS BRANDS (nothing hardcoded to Lafam/Ramin; takes any
  garment's category + fit_type + size run + body). Correct for the pilot. BUT the size
  DECISION is driven by body -> standard scale -> garment label. It uses the garment's
  measurements for the drape + fit description, not as the deciding factor.
- Why not pure measurement-to-measurement yet: (a) merchant charts are unreliable (Lafam
  proves it), and (b) garment girth alone cannot pick a size for an oversized piece without
  knowing its intended ease (the original S bug).
- **v2 (the truly universal version):** match the GARMENT MESH measurements (which we already
  construct in the garment pipeline) to the SMPL BODY measurements in the SAME frame
  (chest width, length, sleeve, inseam). Chart-independent, brand-agnostic, reliable for any
  garment. This is a build (garment-mesh measurement extraction), not a tweak.

**NEXT SESSION (2026-06-15 evening):** verify this v1-vs-v2 distinction together (founder
could not read the full write-up before leaving), then scope/build v2.

---

## OPEN / DEFERRED

- **v2 universal mesh-measurement matching** — next session priority.
- **Numeric / EU-numeric sizing** (28/30/32, 46/48/50) returns all-first-size today; engine
  only understands XS-XXL labels. Not pilot-blocking (Lafam is alpha). Needs a size-key
  normalizer + measurement/rank matching.
- **Part C — broaden upload schema:** `embed/page.tsx` narrows uploaded charts to
  {chest, waist, hips}, dropping shoulder/sleeve/inseam/thigh even though the engine can use
  them. Widen when folding in the size packs.
- **Elastic waistbands:** pantalon spec has relaxed AND stretched waist; we use one number, so
  "snug around waist" can mislead.
- **Tall-person length flag** for bottoms (Revan's 83cm inseam exceeds even the pantalon XXL).
- **Tune `BODY_SIZE_SCALE` bands** per brand (currently held up against Revan's anchor; the
  one accuracy knob).

## LAFAM ONBOARDING (carried from 2026-06-13)

- **Step 1 still blocked:** need Lafam's `.myshopify.com` handle (NOT lafamamsterdam.com, the
  vanity domain). Founder asks the Lafam team 2026-06-15. Then add it to `SHOPIFY_PILOT_SHOPS`
  + confirm webhook/CORS. (Their Shopify CDN store id is `0642/5015/1152` if useful.)
- Steps 2-3 done (2026-06-13). Step 5 (founder builds Lafam garments in CLO3D) starts Mon
  2026-06-15. Critical path is still the founder's CLO3D turnaround.
