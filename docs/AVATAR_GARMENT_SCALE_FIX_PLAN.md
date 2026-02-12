# Avatar–Garment Scale Fix — Research & Implementation Plan

## Executive Summary

The TryOn widget displays the garment (t-shirt) too large relative to the avatar because **the avatar and garment use different coordinate systems**:

| Asset | Source | Units | Typical Values |
|-------|--------|-------|----------------|
| **Avatar** | 4D-Humans / SMPL / RunPod pipeline | **Meters** | Height ~1.8 units |
| **Garment** | CLO 3D export | **Millimeters** | Height ~500–1800 units |

When both are normalized in the widget, scaling from different bases causes size mismatches. The fix is to align them at pipeline time, not at display time.

---

## Key Script Located

**`expansion/avatar-creation/scale_avatar_for_clo3d.py`**

### What It Does

1. Loads avatar OBJ (4D-Humans/SMPL output in **meters**).
2. Scales to **millimeters** for CLO 3D compatibility:
   - Default: 1000× (meters → mm)
   - Or: `--target-height 192` → scales so avatar is 192 cm (1920 mm) tall
   - Or: `--clo-default` → 180 cm (1800 mm), CLO 3D default
3. Aligns bottom to ground (Y=0).
4. Exports OBJ (or PLY) in mm.

### CLO 3D Unit Convention

- CLO 3D imports OBJ with **"mm (Default)"** unit setting.
- Garments exported from CLO 3D are in **millimeters**.
- Avatar must be in mm to match garment coordinate space.

### Usage Example

```bash
python scale_avatar_for_clo3d.py \
  --input body_apose.obj \
  --output body_apose_clo3d.obj \
  --target-height 192
```

---

## Current Pipeline Flow (RunPod)

**Location:** `mvp_pipeline/avatar-creation/pipelines/run_avatar_pipeline.py`

| Step | Output | Units |
|------|--------|-------|
| 1. 4D-Humans body extraction | body_person0.obj, params | Meters |
| 2. (T-pose for measurements) | — | — |
| 3. Measurements | measurements.json | cm |
| 4. A-pose generation | **body_apose.obj** | **Meters** |
| 5. Skin extraction | skin_texture.png | — |
| 6. GLB export | **avatar_textured.glb** | **Meters** (from body_apose.obj) |

**Handler** (`handler.py`) encodes `apose_mesh` and `avatar_glb` from `results["outputs"]` and sends them to the backend for Supabase upload.

**Missing step:** No call to `scale_avatar_for_clo3d` anywhere in the pipeline.

---

## CLO 3D Garment Flow

**Source:** `expansion/avatar-creation/output/clo3d_garments/tshirt_{xs,s,m,l,xl}.obj`

- Exported from CLO 3D with **mm** units.
- Converted to GLB via `mvp_pipeline/scripts/obj_to_glb.py` (no scale change).
- Uploaded to Supabase `garments` bucket.
- Widget loads avatar + garment GLBs from Supabase.

**Result:** Avatar (m) + garment (mm) → 1000× scale mismatch.

---

## Implementation (DONE ✓)

Scale step added to RunPod pipeline as Step 4b. Flow: body_apose.obj → scale → body_apose_clo3d.obj → texture → avatar_textured.glb.

**Update:** Avatar is scaled to CLO default height (180 cm) so it matches demo CLO garments. Fit algo still uses user's actual height for size recommendation.

---

## Implementation Plan (Reference)

### Option A: Scale in RunPod Pipeline (IMPLEMENTED)

**Where:** `run_avatar_pipeline.py`, between Step 4 (A-pose) and Step 6 (GLB).

**Flow:**
1. Step 4: Create `body_apose.obj` (meters).
2. **NEW Step 4b:** Run `scale_avatar_for_clo3d`:
   - Input: `body_apose.obj`
   - Output: `body_apose_clo3d.obj` (mm, target height = user's `height_cm`)
   - Use `--target-height {height_cm}` from pipeline input.
3. Step 6: Use `body_apose_clo3d.obj` instead of `body_apose.obj` for textured GLB creation.
4. Result: `avatar_textured.glb` is in mm, matching CLO garments.

**Files to Modify:**
- `mvp_pipeline/avatar-creation/pipelines/run_avatar_pipeline.py`
- Copy or symlink `scale_avatar_for_clo3d.py` into `mvp_pipeline/avatar-creation/` if not present.

### Option B: Two Outputs (Original + CLO-Scaled)

Keep both:
- `body_apose.obj` (meters) — e.g. for measurements, compatibility.
- `body_apose_clo3d.obj` / `avatar_clo3d.glb` (mm) — for TryOn widget.

Store `avatar_clo3d.glb` URL in `avatar_url` and/or `pipeline_files.avatar_glb_clo3d`.

### Option C: Backend Post-Processing

After RunPod returns, backend could:
1. Decode `apose_mesh` base64.
2. Run `scale_avatar_for_clo3d` (or equivalent) in Python.
3. Convert scaled OBJ to GLB.
4. Upload CLO-scaled GLB to Supabase.

**Downside:** Adds backend dependencies (trimesh) and CPU work; better done in RunPod.

---

## Recommended Plan (Step-by-Step)

### Phase 1: Add Scaling to RunPod Pipeline

1. Copy `scale_avatar_for_clo3d.py` from `expansion/avatar-creation/` to `mvp_pipeline/avatar-creation/` (or add to Docker image).
2. Add `step4b_scale_for_clo3d()` in `run_avatar_pipeline.py`:
   - Input: `body_apose.obj`, `height_cm`
   - Output: `body_apose_clo3d.obj`
   - Call `scale_avatar_for_clo3d()` with `target_height_cm=height_cm`.
3. Change Step 6 input from `apose_path` to `apose_clo3d_path`.
4. Ensure `avatar_textured.glb` is built from the CLO-scaled mesh.

### Phase 2: Ensure Garments Are Consistent

- Confirm CLO 3D export uses **mm** (per `CLO3D_EXPORT_GUIDE.md`).
- Document that garment OBJs/GLBs must be in mm for correct compositing.

### Phase 3: Backward Compatibility

- Existing avatars in Supabase (meters) will still mismatch.
- Options:
  - Re-run pipeline for affected users, or
  - Add a `model_units` field (e.g. `"m"` vs `"mm"`) and have the widget apply inverse scale when units differ.

### Phase 4: Widget Simplification (Optional)

- Once all avatars are CLO-scaled (mm), the widget can assume both avatar and garment are in mm.
- Normalization in the viewer can be simplified or removed if sizes are consistent.

---

## File Locations Summary

| File | Path | Purpose |
|------|------|---------|
| Scale script | `expansion/avatar-creation/scale_avatar_for_clo3d.py` | Meters → mm for CLO 3D |
| RunPod pipeline | `mvp_pipeline/avatar-creation/pipelines/run_avatar_pipeline.py` | Where to add step 4b |
| RunPod handler | `mvp_pipeline/avatar-creation/pipelines/handler.py` | Encodes outputs for backend |
| Garment conversion | `mvp_pipeline/scripts/obj_to_glb.py` | OBJ → GLB (no scale) |
| CLO export guide | `expansion/avatar-creation/CLO3D_EXPORT_GUIDE.md` | Garment units (mm) |
| CLO grading | `expansion/avatar-creation/CLO3D_GRADING_MEASUREMENTS_CM.txt` | Size chart reference |

---

## Dependencies

- `scale_avatar_for_clo3d.py` uses `trimesh` and `numpy`.
- `run_avatar_pipeline.py` already uses `trimesh` in Step 6.
- No new pip packages required.

---

## Testing Checklist

1. Run pipeline locally with `--height 192`.
2. Inspect `body_apose_clo3d.obj` — height in mm (e.g. ~1920).
3. Compare with garment OBJ — both in mm, similar scale.
4. Upload avatar + garment to Supabase, test in TryOn widget.
5. Verify avatar and garment appear at correct relative size.
6. Test with different heights (e.g. 165, 180, 200).

---

## Notes

- `expansion/avatar-creation/combine_clo3d_with_blender.sh` expects `body_person0_neutral_textured_clo3d.obj` — a CLO-scaled avatar. That file is produced manually or by a separate flow; the RunPod pipeline does not create it today.
- `change_to_apose.py` (4D-Humans-clean) scales to `target_height_cm` but outputs in meters. `scale_avatar_for_clo3d` is the correct step for CLO 3D (meters → mm).
- The widget’s current normalization helps when units differ, but aligning at the pipeline avoids fragile runtime heuristics.
