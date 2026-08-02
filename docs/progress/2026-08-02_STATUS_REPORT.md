# Status Report — 2026-08-02

La Fam draping went from "never worked once" to all three wearable garments
draping correctly at every size tested. Four separate bugs, all in our code,
plus one infrastructure problem on RunPod's side.

Branches touched: `drape` (handler v46 → v47.1), `feature/analytics`
(dispatcher + auth fix).

---

## WIN 1 — La Fam garments now drape (v46 → v47.1)

Before today, zero drape jobs had ever been created for a La Fam garment, and
forcing one by hand produced a shredded mess. Four distinct causes.

### 1a. Files were in Supabase but not in the database

The OBJ/MTL/PNG assets were uploaded straight into the storage bucket via
Supabase Studio. Storage and the DB are separate: `garments.sizes` and
`garments.obj_sizes` were both empty, and those columns are the *only* thing
the pipeline reads.

- `drape_dispatcher._build_runpod_payload()` reads `obj_sizes.get(size)` →
  `None` → nothing ever dispatched.
- `/api/products/{id}/tryon-config` returned `{"detail":"No model URLs for
  this garment"}` live against Railway.
- The `/sync` endpoint could not have rescued this: it only matches exactly
  `{size}.glb` and *overwrites* `sizes` wholesale.

**Fixed:** registered all 21 OBJs into `obj_sizes`; corrected
`denim slogan jeans` from `tops` to `bottoms`.

### 1b. Texture filenames with spaces (handler)

Every `map_*`/`bump` line was parsed with `line.split()[-1]`. CLO3D wrote:

```
map_Kd ChatGPT Image Jul 14, 2026, 04_26_05 PM.png
```

which resolved to `PM.png` → 404 → garment draped untextured. **All 120
`map_*` lines across all 24 La Fam MTLs** were affected.

**Fixed:** new `_mtl_map_filename()` takes everything after the keyword and
skips MTL option flags (`-bm`, `-s`, `-o`, …). Added `_encode_url_path()` —
httpx rejects a raw space before the request is even made. Added AppleDouble
(`._*`) guards on all three MTL glob fallbacks; this drive is exFAT-adjacent
and a stray `._m.mtl` would silently poison material lookup.

Confirmed live in RunPod logs:
`Downloaded texture: chatgpt_image_jul_14_2026_04_26_05_pm.png (1400.0 KB)`

### 1c. Partial garments stretched to body height + sleeves deleted (v46)

`align_meshes` rescaled by `body_h / garm_h` whenever the ratio fell outside
0.8–1.2. Ramin's tracksuits sit at 1.0185 so it never fired. The La Fam tee is
0.5817 m (ratio 0.3232) and was blown up **3.09×** into a 1.8 m shirt spanning
floor to crown. Units were never this function's job — `_normalize_to_meters`
already handles mm→m, so 0.32 is a t-shirt, not a unit error.

Separately, `_drop_small_intra_material_components` presupposes CLO3D's
`Body_*`/`Sleeves_*` naming. The tee names its entire shell
`FABRIC_1_FRONT_2633`, so its **sleeves** (449 and 399 faces, 17.8% and 15.8%
of the largest component) fell under the 0.20 cutoff and were deleted on every
run — the 848 faces in the production log.

Size ratio cannot separate sleeves from Ramin's real pocket bags (14.3–15.9%);
the distributions overlap. **Stitch-share can:** bags share 0.5–5.3% of their
verts with the outside world, sleeves 11.1–12.3%. Threshold moved 0.20 → 0.08,
and the rule is skipped entirely when no structural material exists.

### 1d. THE big one — we were mangling garments that arrived already fitted (v47)

CLO3D exports a garment one of two ways. Ramin's arrive **at the origin** and
need aligning. La Fam's arrive **in world coordinates, already draped on our
avatar**.

```
LAFAM tee   raw Y [0.972, 1.553]   Z [-0.127, 0.176]
BODY (as m)     Y [0.000, 1.800]   Z [-0.122, 0.173]
```

Measured with `trimesh.contains`:

| | verts inside body | max penetration |
|---|---|---|
| tee **as exported** | 1 / 4052 | **0.1 mm** |
| tee **after `align_meshes`** | 934 / 4052 | **74.0 mm** |
| longsleeve as exported | 0 / 35837 | 0.0 mm |
| longsleeve after align | 6510 / 35837 | 71.4 mm |

`align_meshes` drove a perfectly-placed garment 9.5 cm into the chest, then the
SDF retarget hurled 878 verts back out. **That was the shredding at the
shoulders and sleeve caps — our own misalignment being violently undone, not a
simulation failure.** The body of the shirt looked fine because those verts
were never buried.

**Fixed (v47):** `_is_prefitted()` — ≥60% of verts within 50 mm of the body AND
Y within the body's span → identity transform, no scale, no translation.

**v47.1:** v45.11's shoulder-align then ran anyway and undid it, shifting the
blue tee down 3.2 cm and the longsleeve 2.5 cm. It only triggers on garments
carrying a `Sleeves_*` material, which is why the black tee escaped. Shoulder-
align exists to correct a feet-matching artifact; a pre-fitted garment is never
feet-matched, so there is nothing to correct. Both paths now gate on
`_is_prefitted`.

### Final results — all six, on RunPod v91

| garment | before | after |
|---|---|---|
| blue tee XS | −37.3 mm, 3244 pushed | **+1.87 mm, 607 pushed** |
| blue tee M | −27.6 mm, 3048 pushed | **+1.78 mm, 634 pushed** |
| longsleeve XS | −28.0 mm, 4733 pushed | **+1.81 mm, 912 pushed** |
| longsleeve M | −20.8 mm, 4307 pushed | **+1.60 mm, 879 pushed** |
| black tee XS/M | already clean | unchanged |

All six now report `translation: [0, 0, 0]`, `scale: 1`, and a **positive**
starting SDF — the garment never intersects the body at all. Every one lands in
Y ≈ 0.96–1.55 on a 1.80 m avatar. Visually confirmed: stripes, both prints,
correct colours, correct silhouette.

**Zero regression on Ramin**, verified by A/B against pristine v45.12.1:
52607 → 52607 faces, y=[0.000, 1.833], scale 1.0 — bit-identical. Ramin size S
is also safe under v47.1: its raw Y starts at 0.0574, and feet-align used to
shift it down by exactly that 5.74 cm, which is the shift v45.11 was written to
undo. With no shift there is nothing to correct.

---

## WIN 2 — Frontend + backend fixes (`feature/analytics`)

- **`42a68d9`** — consent checkbox was double-toggling itself. The visible span
  carried its own `onClick` while sitting inside the `<label>` that also
  activates the hidden input, so one click flipped `agreed` twice. With the
  submit button gated on it, brand sign-up was unreachable.
- **`6be2dd8`** — dispatcher and `/draping/test-run` now send the garment
  `category`, which v46 needs to anchor partial garments anatomically.
- OBJ upload in the garment tab: the file input was `accept=".glb"` and always
  posted to `/upload` (GLB-only, 400s on `.obj`). Now routes by extension to
  `/upload-obj`, and size buttons track GLB and OBJ independently.

---

## Infrastructure — RunPod GPU incompatibility (cost ~40 min)

Workers were being scheduled onto **PRO 6000 MIG 24GB** (Blackwell, sm_120).
Our image is CUDA 11.8, which has no kernels for Blackwell:

```
Fitness check failed: _cuda_init_check
CUDA error: no kernel image is available for execution on the device
Worker is unhealthy, exiting.
```

Workers boot, fail the check, exit, and jobs queue forever — presenting as
"2 idle workers, 1 job in queue" with no error anywhere.

**Mitigation:** deselect every `PRO` GPU tier on the endpoint. Compatible:
A5000 (sm_86), RTX 4090 (sm_89), H100 SXM (sm_90). **This is not fully applied
— a PRO 6000 worker still respawns on each rollout.**

Also worth knowing: RunPod's `runsync` has a ~90 s synchronous window. Past it
it returns the job as still in-progress with no `output`, and the backend's
`if not output.get("success")` turns that into a misleading 500 "Unknown
error". Production uses async `/run` + webhook, so it is not affected.

---

## NOT DONE — carried forward

1. **Denim jeans — re-export required, then drape.** All 6 sizes are uploaded
   but each is 179–218 MB. The first 3 MB of `dsj_xs.obj` alone holds 100,178
   vertices; the entire working Ramin garment is 27,696. **~100× too dense.**
   The drape does 25 passes over every vertex, so this would run for hours per
   size per avatar. Needs re-export from CLO3D at the same density as the
   t-shirts (target <10 MB/size). Once re-exported: register `obj_sizes`,
   re-activate the garment, drape and verify. Code already handles it as
   `bottoms` (waistband anchored to hip crest rather than shoulder).

2. **Viewer + La Fam button wiring — verify end to end.** Confirm the draped
   result renders correctly in the actual viewer, and that the try-on button on
   the La Fam storefront resolves to the right garment and size. Not yet tested
   beyond raw GLB inspection.

3. **Fire the backfill.** 3 garments × 6 sizes × 16 avatars = up to 288 jobs,
   ~20 min across the fleet. Park the jeans first (`is_active=False`) so they
   do not starve the queue. Machinery already exists — `/api/draping/backfill`
   for existing avatars; new avatars auto-enqueue via `avatar.py:416`.

4. **Upload the 18 source GLBs.** Generated from the OBJ+MTL+textures already
   in the bucket and validated (correct topology, UVs, embedded textures,
   1.3–4.1 MB — Ramin's working `m.glb` is 3.5 MB). Until these land,
   `tryon-config` returns 404 and the try-on button shows nothing. Script ready
   at `scratchpad/upload_glbs.py --apply`.

5. **Size charts are empty on all four garments.** Size recommendation is
   running on the hardcoded stub at `products.py:186`
   (`m: chest 100, waist 84, hips 98`). Needs the real chart from La Fam —
   these numbers drive what real shoppers order and must not be invented.

6. **Finish the GPU config change** so PRO/Blackwell workers stop respawning.

7. **Consider a CUDA 12.4+ base image** so GPU selection stops mattering at
   all. Not urgent, but it is the root fix for item 6.

---

## Method note

Two wrong diagnoses were shipped before the right one: a "T-pose mismatch"
theory built on a sleeve-axis measurement that was actually measuring the whole
shirt (the tee names everything `FABRIC_1_*`), and a "the pipeline can't drape,
have the brand re-export" conclusion drawn from metrics that separated the
working and broken cases by only 1.3×. The rigor rule was right: **if the
metric does not separate broken from working by a wide margin, the metric is
wrong.** Printing the raw bounding boxes of body and garment — four numbers —
would have found the real bug immediately.
