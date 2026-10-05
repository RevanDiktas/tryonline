# Status: 2026-10-05 night

Follows `2026-10-05_EVENING_HANDOFF.md`. Done in Claude Code on the Mac.

## Live now (`feature/analytics` @ `0ddc366`, Railway + Vercel verified)

| What | Where |
|---|---|
| **Find my size block released** to the Ramin pilot app (`tryonraminpilot-19`, then `-20`). Placed on the pilot store's product template; onboarding tested by Revan on the store and it works. | `shopify_app/.../find-my-size.liquid` |
| **No size button on gift cards or non-size products.** A single option counts as sizes only if every value looks like a clothing size (XS–5XL, One size, 20–60, 32/34). | `7061efa` |
| **One onboarding for both buttons.** Try On without a finished avatar opens the Find my size card (`size-finder.html?flow=tryon`): account, details, photo, build, size first, then "See it on you" opens the 3D viewer. The old new-tab sign-up is no longer used. | `4a90d27` |
| **Only a completed passport counts as an avatar.** `/api/avatar/{id}` returned an avatar URL for all 20 `pending` passports (none have a GLB); those shoppers now get onboarding instead of a broken viewer. All 33 `completed` passports have their GLB. | `4a90d27` |
| **Drape queue honours priority.** The dispatcher only gives RunPod as many jobs as it can run (`DRAPE_MAX_IN_FLIGHT`, default 2 = drape endpoint max workers), counted from RunPod `/health`, with a 15-min DB fallback. Before: 39 jobs in RunPod's FIFO, ~23 min queue for a 30–75 s drape. | `8b6c7d6` |
| **Garment on screen first.** `/api/draping/request` moves the shopper's existing `drape_jobs` row to priority 0 (size on screen) / 1 (other sizes) and wakes the dispatcher; returns `job:<id>` polled via `/status`. The old runsync path (duplicate work, no storage key) is removed. | `8b6c7d6` |
| **Product they onboarded from drapes first.** The card sends `product_id` to `/api/avatar/create`; after the fan-out, `drape_product_first` puts that garment's sizes at priority 0. | `0ddc366` |
| **Viewer never stacks an undraped garment on the avatar.** Until the drape for the size on screen lands: avatar alone + "Fitting <product> to your body…". On failure: "We couldn't fit … yet". | `0ddc366` |

Checks: new `backend/scripts/check_drape_priority.py` (39 checks) passes; the 5 other backend check scripts and `frontend/scripts/check_size_estimator.mjs` (Node 20) pass.

**Measured live (sign-up `719aec87`, 19:37 UTC):** avatar done 19:37:32 → its product ("rs bow zipup") L and M dispatched 19:37:48 → first size draped 19:41:57 (~4.5 min, mostly RunPod cold start; sim ~1 min).

## Open: skin shows through the drapes (job for 2026-10-06)

Seen on TEST (`cdec2430…`, RS Zip Up `2663d739…`, S/M/L). Files and renders in `~/Downloads/tryon-drape-check/`.

**Not the viewer.** `avatar_textured.glb` is identical to `body_apose.obj` (≤0.0001 mm); the cloth was simulated on that body scaled to 1.80 m feet-at-0, which is exactly what the viewer does. Every scale/offset tried made it worse.

Two causes, both in the drape handler (`drape` branch, `avatar-creation/draping/handler.py`, endpoint `e86juazm1b4mig`):

1. **Speckled skin over the forearms: sleeve cloth ~1 mm off the arm.** `SLEEVE_OFFSET_M = 0.001` (v45.7). A post-sim pass pushing cloth to ≥3 mm off the skin removed nearly all speckle in renders; cloth moved median 2 mm on ~6% of verts. Script: `clearance.py`.
2. **Real holes on the back of the lower forearm, near the cuff, and at the ankle: seams split open.** They stay even with cloth pushed 15 mm out. Each sleeve leaves the sim as one boundary loop (an unjoined flat panel, not a tube): seam edges coincide (0 mm) along the arm but separate up to 30–40 mm near the cuff. The cylindrical-seam weld was disabled in v45.8 (it merged pairs up to 15 mm apart and distorted size S). Ankle holes are on `FABRIC_1_FRONT_2743` (rib cuff). Script: `slit.py`.

**Plan (agreed to do tomorrow, nothing changed yet):**
1. Post-sim minimum clearance 3 mm, motion-capped per iteration (skill lesson v45.3).
2. Weld only seam boundary pairs already <1 mm apart, before the sim, so sleeves/cuffs are closed tubes.
3. `runpod-handler-rigor`: re-read the handler, `py_compile`, run locally on TEST body + RS Zip Up S/M/L, measure (`poke2.py`, `slit.py`) and render back views before/after, show Revan, then build.
4. A handler version bump invalidates the drape cache: all avatars × garments × sizes re-drape in the background; with the new queue this never blocks a new shopper. Consider raising drape `workersMax` 2→4 (and `DRAPE_MAX_IN_FLIGHT=4` on Railway) for the backlog.

## Other open items

- Not tested by Revan yet: closing the card mid-build and reopening; an existing account going straight to the viewer.
- Dead code in `test-viewer.html`: the old gate steps (choose / signin / signup-wait / avatar) are no longer reached; remove once the new flow has run a few days.
- Widget token not yet sent by `test-viewer.html` (the card sends it); `WIDGET_AUTH_REQUIRED` stays off until it does.
- Design pass on the card (focus ring outline on open, button weights) once real screenshots of each step exist.
- `feature/widget-onboarding` (`a69bc77`, Mac only) is superseded by the one-onboarding change; keep for reference, don't merge.
- Still open from the evening handoff: delete stored files of `tryingon@gmail.com` and test accounts; privacy policy (IP → country/city); raw IP column; RLS on `brands`/`garments`; public `photos` bucket; LHM avatar data fetch (~55 s of each cold build).

## Local test harness (Mac)

- Widget on :3000: `node <scratchpad>/widget-server.mjs` serves a worktree's `frontend/public`, proxies `/api` to production Railway, `/widget-config` from tryon.global, `/auth/me` → 401.
- Mock store on :8080 (RS Zip Up, `ph2360-eq`). The old `~/Downloads/tryon-widget-qa/mockstore/` is gone; recreate from the same contract if needed.
- Check scripts: Python via `/usr/local/bin/python3.13` with `PYTHONPATH=backend/venv/lib/python3.13/site-packages` (the venv's own python links to the unmounted `/Volumes/Expansion`); `.mjs` via Node 20.
