# Status Report — 2026-08-04

Three workstreams, all closed: (1) finished and audited the La Fam drape
backfill, (2) found and fixed the reason the PDP widget could never reach any of
it, (3) shipped outfit pairing so the avatar is never half-dressed. Everything
below is live in production and verified against artifacts, not against
counters.

**One thing blocks launch, and it is not engineering: the size charts are
empty.** Detail at the bottom.

---

## WIN 1 — Drape coverage closed at 714/714

Started the day at 713/714 with one failure and a lot of unverified assumptions.

- **The gap:** `stripped long sleeve` / xxl / avatar `0682a313`, failed with
  `executionTimeout exceeded` — the largest mesh in the set at 40,907 verts, so
  a genuine timeout, not the texture bug. Requeued by resetting
  `drape_jobs.status='queued'`, `attempts=0`, `priority=1`. The live dispatcher
  claimed it in under 30 s; it completed in ~5 min at exactly 40,907 verts.
- **Audit of the other 713:** downloaded all 42 source OBJs and compared vertex
  counts against every cached row. **All 713 matched exactly.**
  `simulation_method=pygarment` throughout, no geometric fallbacks.
- **The 4 pelvis-centred avatars did NOT corrupt anything.** Measured real GLB
  bounding boxes for `399e9d9c`, `89b1c8bb`, `0682a313`, `56c9b64c` against a
  known-good control: jeans 1.024–1.040 m, tees 0.574–0.594 m, all within ~15 mm
  of control. Nothing near 1.8 m. The `align_meshes` handler bug is still latent
  but did not bite this backfill.
- **The 12 poisoned rows on `621f21356dd266c6` are gone** — the re-drape
  upserted over them via `on_conflict=garment_id,size,body_hash`.
- **Ramin's 52 failures left no holes.** They are the old
  `RunPod status=COMPLETED` empty-output bug, but every affected combo has a
  good row from a later attempt. 51/51 on all six garments.

---

## WIN 2 — The widget was 404ing on every La Fam product. It was a data gap.

All 407 draped meshes were unreachable from the storefront, and had been all
along.

- **Cause:** `/api/products/{pid}/tryon-config` builds `model_urls` from
  `garments.sizes` (GLB paths), **not** from `obj_sizes`. La Fam had 6 OBJs and
  **zero GLBs** per garment, so the endpoint returned
  `404 "No model URLs for this garment"` before it ever reached the draping
  lookup.
- **How it was isolated:** Ramin's six garments returned 200 the entire time.
  That contrast proved the pipeline was healthy and only La Fam's data was
  short — no code was at fault.
- **Fix:** generated the 24 base GLBs from the OBJs already in storage using
  `handler.py`'s own `_obj_to_glb_textured`, **extracted verbatim rather than
  reimplemented**, so base and draped GLBs come from identical code. Only the
  JPEG textures the MTLs actually reference were pulled; the stale PNGs in those
  folders are dead weight.
- **Verified before upload, not after:** every GLB re-opened and measured —
  vertex count vs source OBJ, bbox height in a garment-scale range, at least one
  textured material. All 24 passed; nothing was uploaded unverified. Then
  re-downloaded all 24 from the public URLs the API hands out: **24/24 match
  source vertex counts exactly.**

| Garment | Verts (xs→xxl) | Height | Size each |
|---|---|---|---|
| denim slogan jeans | 31,214 → 38,810 | 1.000–1.023 m | 5.72–6.08 MB |
| diamond t-shirt black | 9,321 → 12,407 | 0.552–0.626 m | 1.45–1.59 MB |
| diamond t-shirt blue | 34,420 → 46,399 | 0.553–0.616 m | 3.00–3.57 MB |
| stripped long sleeve | 32,759 → 40,907 | 0.590–0.681 m | 3.35–3.75 MB |

Filename matters: `garments/{brand}/{folder}/{size}.glb` exactly, because
`garments.py` `/sync` matches on `{size}.glb`.

---

## WIN 3 — Outfit pairing: no half-dressed avatars (commit `8835a3d`)

Jeans PDP showed jeans and a bare torso; a tee PDP showed a tee and bare legs.

- **Model:** `garments.companion_garment_id` — nullable, self-referencing,
  `ON DELETE SET NULL` (migration `005_outfit_pairing.sql`). Directional: the
  jeans point at the black tee, each top points at the jeans. A garment with no
  companion renders exactly as before, which is what keeps every other brand
  untouched.
- **One request, whole outfit:** `/tryon-config` resolves both halves off the
  same `body_hash` and returns a `companion` object shaped like the primary.
- **Sizing stays in the frontend engine.** The backend ships the companion's
  per-size maps and chart rather than growing a second implementation. The
  companion is pinned to the shopper's recommended size and held, so cycling
  sizes moves only the garment being bought.
- **Fails soft by design:** a missing, deleted or mesh-less companion logs and
  renders the primary alone. A broken pairing must never take down the product
  page it hangs off.

### Bonus fix found on the way

`TryOnViewer.tsx` scaled every garment to `TARGET_HEIGHT` unconditionally —
stretching a 0.583 m draped tee **3.2x**. This is the frontend twin of the
handler's `align_meshes` bug. It was latent because La Fam had no `sizes` and
the endpoint 404'd; populating `sizes` in WIN 2 made it reachable. Combined
full-body models (garment height ≥85% of avatar) keep the old normalisation;
separate pieces now take the avatar's scale factor and keep true proportions.

---

## Deployment

Railway's stale-build problem is **resolved**. `/version` returns
`{"commit":"8835a3d552b3","branch":"feature/analytics"}` — 73 routes, was 72.

Verified through the exact path a shopper takes (`tryon.global` → Vercel
rewrite → Railway):

| PDP | companion returned |
|---|---|
| denim-slogan-jeans | diamond t-shirt black (tops) |
| diamond-t-shirt-black | denim slogan jeans (bottoms) |
| diamond-t-shirt-blue | denim slogan jeans (bottoms) |
| striped long sleeve | denim slogan jeans (bottoms) |

Regression: Ramin `bow-sweats` still returns `companion: null`, unchanged.

---

## BLOCKER — size charts are empty (not an engineering task)

`size_chart` is `{}` on all four La Fam garments. `tryon-config` substitutes a
hardcoded `{"m": {chest:100, waist:84, hips:98}}`, so **size recommendation runs
on invented measurements**. A 192 cm / 102 cm-chest avatar was recommended L on
one tee and XXL on another purely from those fabricated numbers — and the fit
copy states it with full confidence ("YOUR BEST MATCH — FITS TRUE TO SIZE").

The 3D try-on is unaffected and genuinely good. But returns reduction is the
pitch, and until real charts land the size advice is noise. **Plan: Revan sits
down with the La Fam owner to fill the charts in, then go live.** If anything
ships before that, hide the recommendation rather than show a fabricated one.

---

## Open, non-blocking

1. `download_file` (handler.py:181) has **no retry** — one GET, one transient
   blip, job lost. Cost 3 jeans jobs in the first 50.
2. `_is_prefitted` offset tolerance — the permanent fix for pelvis-centred
   avatars. Latent, did not bite, but still there.
3. Ramin's garment textures are still oversized PNGs. Converting them to JPEG
   (as done for La Fam: 11.20 MB → 2.19 MB) would stop the wasted retries. No
   coverage impact.
4. 3 La Fam drape rows carry a stale `garment_version_hash` (jeans xl/xs/xxl on
   `621f21356dd266c6`). Geometry correct; `/check` ignores the field.
5. Three garments have no OBJ at all (CODY MEIJER jacket, RS tshirt, Ramin Basic
   Black Tshirt) — nothing to drape until meshes are uploaded.
6. `backend/.env` carries `HF_TOKEN`, which `Settings` rejects as an extra
   field, so `uvicorn` will not boot from `backend/` as-is. Railway is
   unaffected (that var is not in its list), but it blocks local dev.

---

## Two traps worth remembering

- **`products.py` memoises its column probe.** After a migration that adds a
  column it reads, the backend must be **restarted** or it keeps serving as if
  the column were absent.
- **Verify a deploy by SHA off `/version`, never by "Online" in the dashboard.**
  A stale container answers 200 on `/health` just as happily as a fresh one —
  that ambiguity is exactly what `/version` exists to remove.
