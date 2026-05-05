# Draping Status Report — 2026-04-21 (end of day)

## TL;DR for picking up later

- Pivoted away from NVIDIA Newton (v4–v16, two days of NaN fights) to
  **NvidiaWarp-GarmentCode + PyGarment** (v17 → v18.9).
- Branch `drape`, tip `33b34da`. RunPod endpoint `tryonline-drape` unchanged.
- v18.9 is pushed but **has not been test-run yet**. Everything through v18.8
  compiled and built; v18.8 ran PyGarment far enough to hit a YAML-parsing bug
  in our own sim_props that crashed at frame 1. v18.9 fixes that one line.
- When you come back: auto-build v18.9 → Run Draping → paste log.

## Commit ladder (drape branch, most recent first)

| Commit | Tag | What it changes | Verified in a run? |
|---|---|---|---|
| `33b34da` | v18.9 | YAML `1.0e7` → `10000000.0` so it parses as float not string | **pending** |
| `1650e22` | v18.8 | Monkey-patch Cloth to disable CUDA graph capture (Warp fork race) | yes, got past graph capture; then frame-1 YAML crash |
| `b0d5240` | v18.7 | Feed welded mesh to PyGarment (so stitching springs fire); un-weld on output. Scale parity (body in m, cloth in cm). Enable `cloth_reference_drag`. | yes, built; runtime crashed before sim on graph-capture race |
| `7ee5b1e` | v18.5 | SameFileError fix + pre-write minimal pattern spec JSON for `_load_panel_labels()` | yes, got past it |
| `c45c82a` | v18.4 | Replace `pygarment/__init__.py` with a stub (original imports cairosvg) + build-time sanity check | yes, imports clean |
| `2fd5fa4` | v18.3 | Enable CUDA in Warp build (env `CUDA_HOME`, `--cuda_path`); skip GarmentCode pip install, use PYTHONPATH | yes, CUDA now enabled |
| `dd12677` | v18.2 | Scope `(chmod || true)` subshell so it doesn't mask earlier failures | yes |
| `a75c242` | v18.1 | `--no_standalone` on Warp build (skip LLVM CPU backend — needs packman, wasted 15 min of build) | yes |
| `3a87a20` | v18 | **Rip out Newton entirely** — delete 1072 lines. PyGarment is the only GPU path | yes |
| `e3d1221` | v17 | First PyGarment integration (handler, Dockerfile, assets, seg generator, pygarment_drape) | yes |

## What actually works right now

Everything from preparation to sim start works. The v18.8 log proves these
pieces all operate correctly on the real Ramin hoodie + SMPL body:

- Supabase downloads: body + garment + mtl + 1.png + 2.png ✓
- Scale normalization: `body mm → m` ✓
- Alignment: `body_h=1.8000 garment_h=1.8333 ratio=1.0185` ✓
- Weld pass: `27696 → 26396 verts, 1125 welded groups, 2425 stitch verts` ✓
- Cloth segmentation generated per-welded-vert, correct panel breakdown:
  `Body_B_FRONT:8633, Sleeves:6544, Body_F:5227, FABRIC_1:3358, ...` ✓
- **PyGarment panel_assignment labels are CORRECT now** (v18.8 log lines 580–589):
  ```
  Body_B_FRONT_2724:body
  Sleeves_FRONT_2731:right_arm
  FABRIC_1_FRONT_2710:body
  Body_F_FRONT_2717:body
  ...
  ```
  This is the single biggest proof the v18.6/v18.7 scale-parity fix landed —
  prior runs had body panels mapped to arms because the in-sim scales were
  100× mismatched.
- CUDA graph capture no longer fires (v18.8 disabled it) → no more
  `Cannot free memory while graph capture is active` error spam.

## The exact frame-1 crash in v18.8

```
Traceback (most recent call last):
  File "pygarment/meshgen/simulation.py", line 143, in sim_frame_sequence
    _run_frame_with_timeout(garment, ...)
  File "pygarment/meshgen/garment.py", line 440, in run_frame
    self.update(self.frame)
  File "pygarment/meshgen/garment.py", line 395, in update
    self._sim_frame_with_substeps()
  File "pygarment/meshgen/garment.py", line 356, in _sim_frame_with_substeps
    self.integrator.simulate(self.model, self.state_0, self.state_1, ...)
  File "warp/sim/integrator_xpbd.py", line 2500, in simulate
    wp.launch(...)
  ...
  RuntimeError: Error launching kernel, unable to pack kernel parameter
    type <class 'str'> for param reference_k, expected
    <class 'warp.types.float32'>
```

Verified with `python3 -c "import yaml; print(yaml.safe_load('x: 1.0e7'))"`:
returns `{'x': '1.0e7'}` — a STRING. YAML 1.1 float grammar requires the
explicit sign (`1.0e+7`). PyYAML carried the string through SimConfig →
`model.cloth_reference_k` → the XPBD integrator kernel, where type coercion
raised. v18.9 replaces with `10000000.0`.

## Why skin is still visible in the v18.8 screenshot

The user asked specifically about this. Three distinct artifacts, not one:

### 1. Chest patch showing skin — FIT mismatch, not a sim bug

CLO3D designed this hoodie on a CLO3D reference body (the "woman_default" or
"mean_all" figure). Our SMPL avatar has different proportions — wider
shoulders, different bust contour. At the moment the cloth OBJ is loaded, the
front hoodie panel has a neckline/chest region that sits a few cm away from
the SMPL body (gap between cloth and skin). No amount of gravity simulation
can close that gap — it's a pre-existing pose/size-target mismatch.

**This is a garment retargeting problem, not a cloth-sim problem.**
CLO3D addresses it with their "Auto-Fit" feature (skin-suit weight-map
interpolation — warp the garment shape to match a new avatar BEFORE sim).
We don't do that yet. Parked as a future feature.

**What will partially close the gap:** `cloth_reference_drag` (already
enabled in v18.7+) pulls each panel toward its assigned body part. Once v18.9
runs and the sim actually progresses, panels labeled `body` get tugged toward
the torso. Won't fully eliminate the gap on a significantly different body
shape, but will tighten it.

### 2. Left thigh / pocket area — same FIT issue

Inseam and pocket depth of the pants don't quite match the avatar's hip
geometry. Same retargeting gap story as #1.

### 3. Tiny gaps at panel seams — SHOULD be fixed by v18.9 running

v18.5/v18.6 had the panels SEPARATED across seams because we were feeding
PyGarment the pre-weld mesh (v18.7 fixed this). v18.8 log confirms we now
feed the welded mesh with 1125 stitch verts. Once v18.9 sim runs for >0 frames,
the sewing-spring path inside `add_cloth_mesh_sewing_spring` exercises the
stitch triangles properly and seams close tight.

The single frame that did run in v18.8 was basically the INITIAL STATE
(boxmesh at t=0), not a draped result. The screenshot is the garment before
any cloth physics took effect. Static shape = CLO3D-designed shape = gap
wherever the designed shape doesn't match the new body.

## Known issues still to triage (after v18.9 actually runs)

1. **Deprecation-era junk at handler end**: the `__main__` argparse block
   fires after `runpod.serverless.start()` returns. Cosmetic; error is
   logged but doesn't affect the returned response. Low priority.
2. **`Detected non-manifold edge` spam** (~500 lines per run): warnings
   from PyGarment's `MeshAdjacency` for welded seam verts shared by 3+
   triangles. Informational only — add_cloth_mesh_sewing_spring handles
   them (verified by the successful seg setup). Could silence via
   `warnings.filterwarnings` but not urgent.
3. **`no original length dict found`**: optional file, absence is safe
   (PyGarment falls back to generic springs). Could improve stitching
   quality by computing from UV×1e-3 edge lengths. Future enhancement.
4. **Cold-start cost** (~1 min first run after scale-down): kernel compile
   + warp import. Unavoidable on RunPod serverless.
5. **Retargeting for body-shape mismatch**: the real fit problem (#1/#2
   above). Needs a skin-suit or SMPL-based warp step. Separate feature.

## Files changed today (only on `drape` branch, nothing merged)

| File | Net change |
|---|---|
| `avatar-creation/draping/handler.py` | +1300/-1000 (ripped Newton, added pygarment_drape, weld/unweld, monkey-patches) |
| `avatar-creation/draping/Dockerfile` | Complete rewrite — clones NvidiaWarp-GarmentCode from source, builds with `--no_standalone --cuda_path`, clones GarmentCode and puts on PYTHONPATH |
| `avatar-creation/draping/pygarment_assets/smpl_vert_segmentation.json` | NEW — 108 KB shipped from GarmentCode repo |
| `avatar-creation/draping/pygarment_assets/default_sim_props.yaml` | NEW — tuned sim config (ground on, velocity clamp 20, zero-gravity 10 frames, cloth_reference_drag on) |
| `frontend/public/drape-test.html` | +1 line — updated a stale "Newton 2–3 min" comment |

Total git log for the day: 10 commits (v17 through v18.9).

## When you come back — three steps

1. **Wait for v18.9 auto-build** (~3-7 min; most layers cached from v18.8).
2. **Run the drape** via drape-test.html (same URLs, same endpoint).
3. **Paste the log.** We expect:
   - `[PyGarment] Starting run_sim` → `------ Frame 1 ------` → `------ Frame 2 ------` ... (no crash at frame 1 this time)
   - Either auto-terminates when the static_threshold is met, or hits
     max_sim_steps=300 at the yaml cap
   - `[PyGarment] Success: N frames, X.Xs, body_collisions=?, self_collisions=?`
   - Visually: seams closed, panels on avatar, fit gaps in chest/thigh
     region smaller than v18.8 but still present (that's the retargeting
     problem)

If v18.9 crashes somewhere new: the monkey-patch list to try next is in
the v18.8 commit message. Otherwise we iterate on the sim output quality.

## State of the mental model

After a LOT of whack-a-mole, we now understand:

- **PyGarment / NvidiaWarp-GarmentCode is the right engine** for CLO3D
  garments on arbitrary bodies — the only XPBD cloth system with
  body-part drag + attachment + particle velocity clamp built in. Newton
  lacked all of those and fought us for two days.
- **The PyGarment repo has multiple structural gotchas** for non-design
  use cases: `package_dir = =pygarment` in setup.cfg, `pygarment/__init__.py`
  pulling in the full pattern-design toolchain, `create_graph`'s
  capture-state race, YAML float-grammar footguns, hardcoded `b_scale=100`
  body scaling, dependency on `paths.g_specs` even when no pattern was
  provided. Each required a distinct mitigation. They're all documented
  in commit messages.
- **Our fixes are isolated monkey-patches** — we don't fork PyGarment
  itself. Upgrading to a newer PyGarment release later is a matter of
  re-evaluating which patches are still needed; the architecture of
  `pygarment_drape()` doesn't change.
- **Retargeting (CLO3D Auto-Fit equivalent) is a separate feature**, not a
  cloth-sim feature. Bookmark for later.
