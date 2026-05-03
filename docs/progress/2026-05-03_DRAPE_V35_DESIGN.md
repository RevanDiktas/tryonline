# Drape v35, Design Doc

**Date:** 2026-05-03
**Branch:** `drape`
**Audit basis:** v18-v32 EOD docs, full read of `avatar-creation/draping/handler.py`, full read of `frontend/public/drape-test.html`, Explore-agent audit of frontend rendering chain, research into PyGarment OBJ writer (`save_frame` in `pygarment/meshgen/garment.py`) and CLO3D OBJ/MTL export conventions.

---

## TL;DR

v31+v32 (already on `drape` tip `3b3650a`) made structural fixes to sim quality (component-level pant tag, 6-group SMPL with `head` as first-class group, shoulders into arms). Those have **never been verified.**

Independently, **the texture-rendering pipeline is broken at the frontend, not the handler.** The handler packages MTL + textures correctly. `drape-test.html` calls MTLLoader in the wrong order, materials are iterated before they exist, and preload() loads from an empty baseUrl, 404-ing every texture silently. This bug is not new and is the actual reason the user reports "no texture at all."

v35 fixes the frontend texture path. v35 does **not** change sim code. Sim quality is verified by the same v35 push (RunPod rebuild forces a fresh run with the v31+v32 sim fixes).

If sim quality passes after v35 lands, draping is shippable to the cache architecture defined in `docs/strategy/DRAPING_SHIPPABLE_REQUIREMENTS.md`.

If sim quality fails, v36 addresses the specific structural cause we observe (the EOD-V31-V32 doc's "if partially works" branches are still valid).

---

## Structural causes (named)

### Cause 1, Frontend MTLLoader sequence error

**File:** `frontend/public/drape-test.html:534-549`

**The bug:**
```js
const mtlLoader = new MTLLoader();
materials = mtlLoader.parse(mtlText, '');               // populates materialsInfo, NOT materials
for (const [name, mat] of Object.entries(materials.materials)) {   // empty object, loop never runs
  if (mat.map && mat.map.sourceFile && textureBlobUrls[mat.map.sourceFile]) {
    mat.map = new THREE.TextureLoader().load(textureBlobUrls[mat.map.sourceFile]);
  }
}
materials.preload();                                    // textures loaded with baseUrl '' → 404 silently
```

**Why this never worked:**

1. In three.js r160 `MTLLoader.parse()`, the MaterialCreator stores raw MTL data in `materialsInfo`. The `materials` property stays `{}` until `preload()` (or `create()`) is called.
2. `Object.entries(materials.materials)` is an empty iteration. The blob-URL swap loop is dead code.
3. `materials.preload()` then resolves each `map_Kd basename.png` against `baseUrl=''`, producing relative URLs that resolve to the current page origin. Three.js TextureLoader fetches them, gets 404, calls onError silently. Material constructed with `map = null`.
4. OBJ renders with the un-mapped material. Flat black.

**The fix:** rewrite the MTL text inline with blob: URLs **before** parsing. MTLLoader natively handles absolute URLs (including `blob:`) without needing baseUrl tricks.

```js
let rewrittenMtl = mtlText;
for (const [filename, blobUrl] of Object.entries(textureBlobUrls)) {
  const escaped = filename.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  rewrittenMtl = rewrittenMtl.replace(
    new RegExp(`^(\\s*(?:map_\\w+|bump|disp|decal|refl)\\s+)(?:.*[/\\\\])?(${escaped})\\s*$`, 'gmi'),
    `$1${blobUrl}`
  );
}
const materials = mtlLoader.parse(rewrittenMtl, '');
materials.preload();
for (const [name, mat] of Object.entries(materials.materials)) {
  mat.side = THREE.DoubleSide;
  if (mat.map) mat.map.needsUpdate = true;
}
```

Plus diagnostic logging so future failures are loud, not silent:

```js
log(`MTL: ${Object.keys(materials.materialsInfo).length} materials, ${Object.keys(textureBlobUrls).length} blob URLs`, 'info');
for (const [matName, info] of Object.entries(materials.materialsInfo || {})) {
  for (const key of ['map_kd', 'map_ka', 'map_ks', 'map_d', 'bump']) {
    const ref = info[key];
    if (ref && !ref.startsWith('blob:')) {
      log(`  ${matName}.${key} unresolved: ${ref}`, 'warn');
    }
  }
}
```

### Cause 2, Sim quality verification has not happened

**File:** `avatar-creation/draping/handler.py` (v31+v32 already in place)

**State:** v31 (component-level pant tag) and v32 (6-group SMPL with `head`) were pushed 2026-04-24 and never tested. Nine days idle.

**Expected on a clean v31+v32 run** (per `docs/progress/2026-04-24_EOD_DRAPE_V31-V32.md`):

- `panel_assignment` log: hood components vote `:head` (not `:body`); pant components vote specific `:right_leg`/`:left_leg` (not merged `:legs`); hoodie hem NOT tagged `_pant`.
- Sim metrics: `body_collisions < 150`, `self_collisions < 150` (loose pre-target; shipping bar in DRAPING_SHIPPABLE_REQUIREMENTS.md is < 50/50).
- Visual: no upper-back skin bib, no pant hip/butt holes, hood drapes naturally.

**v35 contains no sim code changes.** Pushing v35 forces a RunPod rebuild that picks up the existing v31+v32 sim with the fixed frontend. We test both at once.

### Cause 3, Silent error swallowing on the texture path

**File:** `frontend/public/drape-test.html` (multiple sites)

**The pattern:** the OBJ+MTL+texture path has a try/catch at line 511-600 that catches ANY error and logs "OBJ loading failed, falling back to GLB." Many texture errors are async (after the initial parse), so they don't trip the catch, they just produce a flat-textured material with no visible error.

**The fix:** add explicit logging at every decision point:
- "MTL parsed: N materials"
- "Textures decoded: K blob URLs"
- "Materials preloaded: M of N have valid map"
- "Materials with no map: [list]"

This doesn't fix bugs but makes the next bug findable in seconds rather than hours.

### Cause 4, Index parity between sim output and OBJ template (verified correct, no change needed)

**Concern from the audit:** PyGarment's `save_frame` is a passthrough writer that walks `v ` lines by index. If the template has different vertex count than the simulated array, UVs and faces silently misalign.

**Why this is correct in our handler** (`avatar-creation/draping/handler.py:1546-1577`):

1. Original CLO3D OBJ has ~27,718 verts.
2. `_drop_small_intra_material_components` drops orphan v/vt/vn lines and remaps face indices coherently. Cleaned OBJ has e.g. ~25,800 verts (after dropping pocket-bag components).
3. `_weld_duplicate_vertices` welds seam pairs. Returns `(welded_verts, welded_faces, orig_to_welded)` where `orig_to_welded` is a length-25,800 array mapping each cleaned-OBJ vert to a welded canonical index.
4. Sim runs on welded mesh. Output `paths.g_sim` has welded count.
5. Handler **un-welds** via `final_verts_m = welded_draped_m[orig_to_welded]` → produces 25,800 positions, one per cleaned-OBJ vert.
6. `write_obj_with_new_verts(garment_obj, final_verts_out, output_obj)` writes against the cleaned OBJ as template, which has 25,800 `v ` lines, matching the array length.

The chain is correct. UVs, mtllib, usemtl, and face references survive intact. **No change needed in v35.**

The audit confirmed our pipeline does not have the structural bug that affects naive PyGarment users (passthrough writer + mismatched template). We get this right. The texture failure was always downstream.

---

## What v35 changes

| File | Change | Lines |
|---|---|---|
| `frontend/public/drape-test.html` | Replace MTL parse-then-swap loop with text-rewrite-before-parse. Add diagnostic logging. | ~534-549 (~30 line diff) |
| `avatar-creation/draping/handler.py` | HANDLER_BUILD banner update to mark v35. No sim code changes. | one constant update |

**No new dependencies.** **No new endpoints.** **No new tables.** **No backend changes.**

---

## What v35 does NOT change

- Sim quality (v31+v32 in place, will be verified with the same push)
- Backend API surface
- Cache architecture (separate workstream per `DRAPING_SHIPPABLE_REQUIREMENTS.md`)
- Production `feature/analytics` branch in any way

---

## Verification plan after v35 lands

In strict order:

1. **Push v35 to `drape` branch.** RunPod rebuild kicks in (~5-10 min).
2. **Confirm RunPod build banner shows v35** in worker startup logs.
3. **Spin up local server for `drape-test.html`** and fire a test job using the URLs in `CLAUDE.md`.
4. **Inspect three things in the resulting console:**
   - "MTL: N materials, K blob URLs", confirms text rewrite ran
   - "Materials preloaded: M of N have valid map", confirms textures applied
   - Visual: garment renders with CLO3D textures (denim, logo print) instead of flat black
5. **Inspect sim quality** in the same render:
   - No upper-back skin bib
   - No pant hip/butt holes
   - Hood drapes naturally (no torso drag)
   - Sim metrics (in handler log): body_collisions, self_collisions
6. **Decide next move:**
   - Textures + sim both pass → move on to caching architecture
   - Textures pass + sim fails → diagnose specific sim regression, design v36 around named cause (no tweaks)
   - Textures still flat → check rewrite regex (probably basename mismatch, check console for "unresolved" warnings)

---

## Risks

| Risk | Mitigation |
|---|---|
| MTL text rewrite regex misses an edge case (unusual quoting, tabs, comment after path) | Logged unresolved refs become visible in the diagnostic warnings; we patch and reship |
| MTLLoader r160 has a different code path than expected (path resolution semantics changed) | We have logging on all decision points; first bad run reveals the actual behavior |
| v31+v32 sim quality regressed on something we didn't anticipate | EOD-V31-V32 doc has a complete "if partially works" branch tree; we follow it |
| RunPod build fails because the handler banner update doesn't trigger a rebuild | Force rebuild via dashboard if banner alone doesn't invalidate the layer |

---

## What this gets us

A drape that:

- Renders with the brand's actual CLO3D materials (denim, prints, ribbing).
- Has the v31+v32 sim quality baked in (clean panel assignment, no torso-yanked hood, no pants holes).
- Loads in `drape-test.html` for the first time with both quality and textures verified together.

That is the precondition for caching, for the iframe wiring, and for showing a paying brand a believable shopper experience.

---

## Sequencing after v35 verifies

If v35 verifies (textures + sim both clean):

1. Re-test on 2-3 additional Ramin SKUs to confirm the panel-assignment fixes generalize beyond the test garment.
2. Begin implementing the cache architecture from `DRAPING_SHIPPABLE_REQUIREMENTS.md` section 4-7. This is the path to "almost instantly" in the iframe.
3. Move sim-quality work to a maintenance stream: tighten thresholds, expand garment-type coverage, but no longer the main blocker.

If v35 verifies textures but reveals a sim-quality regression:

1. Diagnose against the EOD-V31-V32 expected-log table.
2. Name the structural cause (do not tweak scalars).
3. Design v36 as a single targeted fix; commit; re-run.

If v35 fails to fix textures (rewrite regex missed something):

1. Read the diagnostic warnings from the console.
2. Identify the actual mismatch (case? hidden char? unusual MTL syntax?).
3. Targeted regex patch in v35.1.
