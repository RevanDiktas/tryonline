# Status report 2026-05-13 (Wed)

## Headline

Rebuilt the shopper-side 3D viewer twice today. The Shopify iframe popup (`frontend/public/test-viewer.html`) lost 200+ lines of positional / anti-skin-poke / multi-light compensation logic and was ported onto the website hero's render path (PMREM RoomEnvironment, per-mesh meters detection, group-level fit-to-1.8m with feet on `FLOOR_Y = -0.9`, AvatarHero light rig). The `/demo` page got the same treatment: a new `embed-viewer.html` that loads the test@gmail.com avatar plus the Blanc zipup draped onto that body straight from Supabase, with the product card retitled to "Originals · Zipup" and a new product image. All shipped to `feature/analytics`.

## What happened

### 1. Iframe popup viewer rebuild (test-viewer.html)

Started with a Ramin Studios PDP screenshot of the iframe popup. The avatar was framing tight (head cropped, garment dim), and on top of that the file had accumulated a lot of compensation logic that the user wanted gone. Worked through it in passes, each pushed to `feature/analytics` and verified visually on Vercel.

**Pass 1 (commit `8a8f0d1`)**: stripped positional shifts: `TRYON_GARMENT_Z_PUSHBACK = -0.012`, `alignStackedGarmentToAvatar` (feet-align / category-landmark anchor), `TRYON_GARMENT_Y_NUDGE_BY_SIZE`, the whole-group recenter (`position.x = -center.x` etc), the mobile `*1.6` multiplier. Also dropped the anti-skin-poke pair: `prepareStackedAvatarNoBodyDepthWrite` (body torso `depthWrite=false` so garment wins) and the garment `polygonOffset = -17/-17`. Lighting collapsed from ambient 2.0 + 6 directionals + hemisphere to ambient 0.6 + 1 key directional + hemisphere. Avatar and garment now both at `position.set(0,0,0)`; per-root scaling (`1.8/rawA`) preserved.

**Pass 2 (commit `671dfbc`)**: bump lights. Ambient 0.6 → 1.1, key 1.0 → 1.6, hemi 0.5 → 0.8, plus a soft fill (0.8) from the opposite side.

**Pass 3 (commit `e4641b5`, then reverted `f22ed9c`)**: misread "scale is perfect" as "the scaling code is correct" and stripped the per-root `1.8/rawA` scaling. The result was an invisible avatar because the underlying GLBs ship in mismatched units (avatar mm vs garment m). Reverted the same commit minutes later. Memory entry `feedback_plain_viewer_means_plain.md` written so I do not repeat this read.

**Pass 4 (commit `ed9b77d`)**: pulled `frontend/components/redesign/AvatarHero.tsx` apart and ported its render path into the iframe. The user wanted the website hero's "pop" plus head-to-toe framing.
- Materials: `RoomEnvironment` baked through `PMREMGenerator` set as `scene.environment`. PBR garments now get IBL reflections. `toneMappingExposure` 1 → 1.25. Light rig replaced with AvatarHero's: ambient 0.45 + key 1.6 at (5,5,5) + fill 0.7 at (-3,3,-3).
- Framing: replaced per-root `1.8/rawA` with a per-mesh `metersScaleFor` (size.y > 100 means mm, divide by 1000). Then a group-level fit to `TRYON_TARGET_HEIGHT = 1.8` with the combined min Y anchored to `TRYON_FLOOR_Y = -0.9`. Feet land on the floor every render, head fits in the camera frame.
- Camera moved to `(0, 0.05, 3.6)` FOV 30 desktop / `(0, 0.05, 4.6)` FOV 36 mobile; controls target `(0, 0, 0)`.
- Dead helpers dropped: `normalizeBindHeightToMeters`, `garmentRefBindHeightY`, `TRYON_GARMENT_CLEARANCE`, the post-display debug bbox block.

**Pass 5 (commit `28eb0a8`)**: M-size regression. After pass 4 the avatar rendered correctly but the M garment did not show on any of the 6 Ramin SKUs — bare nude avatar with M selected. Pass 4 had cut `resetSkinnedBindPose` + `fixDegenerateNodeScales` along with the rest of the "dead" helpers, and that turned out to break CLO-exported GLBs whose non-bone node world scales collapse to ~0 after `detachFromParent` + reparent. Restored both helpers, threaded them into `displayModel` between the position/scale reset and the meters detect, reset avatar/garment scale to (1,1,1) before unit detection (so stale scales from a prior render don't bias `metersScaleFor`), and put `frustumCulled = false` back on garment meshes so skinned-mesh world AABB mismatches don't cull the draw. Added a per-display console log:
```
[TryOn] Garment {key} live bbox: X.XXX×Y.YYY×Z.ZZZ | meshes: N
```
M renders correctly on all SKUs. Memory entry `feedback_keep_clo_defense_helpers.md` written.

### 2. Demo page viewer swap (embed-viewer.html + /demo)

The `/demo` page on tryon.global was still using the original locally-bundled `models/avatar_with_tshirt_*.glb` set (bald NPC avatar) via a separate 7KB `embed-viewer.html` running the old 6-light setup. User asked for the polished test-viewer flow plus a swap to the test@gmail.com avatar wearing the Blanc Ramin zipup.

**Supabase lookups** to assemble the URLs (no codebase paths available):
- `users` → `test@gmail.com` is user_id `aa6d2670-4e41-4de7-9450-07d487825644`
- `garments` ILIKE `*blanc*` → two rows: `769981ba-…` "blanc zipup" (tops, S/M/L) and `ed2b4387-…` "blanc sweats" (bottoms, S/M/L). User wanted the zipup.
- `fit_passports?user_id=eq.{test}` → height 175 / weight 70 / chest 93 / waist 80 / hips 90 / male.
- Ran the actual backend helper to derive the body hash:
  ```python
  from app.services.body_clustering import compute_body_hash
  compute_body_hash('aa6d2670-...', {...passport...}) → '6301199c3bb5bdc8'
  ```
- `draped_meshes?garment_id=eq.769981ba…&body_hash=eq.6301199c3bb5bdc8` returned 3 rows: S/M/L draped under `c06b18d9337a44dc:v45.3:v45.12` cache key from 2026-05-06.

**embed-viewer.html rewrite (commit `0acb7df` bundled in the same push)** mirrored the new test-viewer.html: import `RoomEnvironment`, define `metersScaleFor` / `geometryWorldBounds` / `resetSkinnedBindPose` / `fixDegenerateNodeScales` / `detachFromParent` / `prepareGarment`, AvatarHero light rig + tone-mapping 1.25, FLOOR_Y anchor, `frustumCulled = false`, PMREM env. Garment URLs are the 3 draped GLBs above keyed by size; size is read from the URL hash (`#s`, `#m`, `#l`).

**Demo page UI** (`frontend/app/demo/page.tsx`):
- Size selector trimmed `['xs','s','m','l','xl']` → `['s','m','l']` because the cache only has those.
- Title "Black T-shirt" → "Zipup"; subtitle "Originals · Black T-shirt" → "Originals · Zipup".
- Product image swapped from `/redesign/originals-black-tshirt.png` to `/redesign/zipup_demo.webp`.
- `.gitignore` got a `!frontend/public/**/*.webp` allow rule so the new image could be tracked.

User verified the live deploy: test-user avatar wearing the Blanc zipup, head-to-toe framing, material pops, S/M/L switching works.

### 3. Memory updates

- `feedback_plain_viewer_means_plain.md` — "import at 0,0,0" / "scale is perfect" means as-authored, not "our scaling code is correct".
- `feedback_keep_clo_defense_helpers.md` — never drop `fixDegenerateNodeScales` + `resetSkinnedBindPose` + `frustumCulled=false` when simplifying a draped-mesh viewer; cutting them made M-size garments invisible across all 6 SKUs.

## What did not happen today

- **No drape pipeline work.** v45.12.1 cache is still the source of truth; no SKU has threatened the 20MB cap so the cherry-pick to feature/analytics is still deferred.
- **No PDP spot-check on the live Ramin store** against the cached v45.12.1 drapes. Yesterday's punch list still has this open.
- **Brand dashboard remake, shopper lobby v0.2** still queued.
- **Deck slide 12 / 13 / 14 source-citation verification** still queued from 2026-05-12.
- **`/demo` product copy fully synced**, but `mockPassport` (98/78/92) in `demo/page.tsx` does not match the test user's real measurements (93/80/90). Cosmetic only; flagged for follow-up.

## Lessons (memory updates)

1. "Plain GLTF viewer" and "scale is perfect" mean trust the file as-authored: no `1.8/rawA`, no normalization, no per-root scale formula. The right way to make a heterogeneous-units viewer behave is per-mesh unit-detection plus group-level fit, not per-root normalize. Saved as `feedback_plain_viewer_means_plain`.
2. CLO-exported GLBs need three defensive guards (`fixDegenerateNodeScales`, `resetSkinnedBindPose`, `frustumCulled = false`) regardless of how plain the viewer is. They are not anti-skin-poke, they are anti-zero-scale-invisible-mesh and anti-AABB-mismatch-culling. Saved as `feedback_keep_clo_defense_helpers`.
3. The shopper iframe and the demo viewer should share one render path. They now do; if a future change to draping demands a viewer change, both files need the same patch (no abstraction yet because two siblings is not three).

## Tomorrow

User said they don't know yet what's next. Default options if nothing else comes in:

- **PDP spot-check on Ramin Studios live store** against the v45.12.1 cache (open since 2026-05-11).
- **Verify the new iframe on a real Ramin product** — today's verification was on the dashboard popup and the /demo page. Production PDP path through tryonline-drape may still have edge cases.
- **Deck source-citation cleanup** on slides 12 / 13 / 14 (still best-effort from 2026-05-12).
- **Sync `mockPassport` in /demo** to the test user's actual measurements (93/80/90 vs current 98/78/92).
- **Brand dashboard remake / shopper lobby v0.2** if appetite for design work.
