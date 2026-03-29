# Warp heatmap: Phase 0 → Phase 1 (testing)

**Locked assumptions**

- **Units:** Keep **millimeters** end-to-end (same as `body_apose.obj` + CLO-scaled GLBs). Material parameters (stiffness, bending, density, thickness) must be expressed **consistently in mm–kg–s** (or normalized first; see spike notes).
- **Pose:** **A-pose** body mesh only for v1 collision.
- **Garment:** Start with **`m.glb`**, then **L → S → XS → XL** (or your preferred order) to observe stress evolution.
- **Hardware:** **RunPod GPU** only (no local GPU requirement).
- **Throughput target (aspirational):** Five sizes **in parallel**, roughly **10–30 s wall-clock** for five heatmaps + exports (validate in Phase 1; depends on mesh resolution, substeps, and GPU).

---

## Phase 0 — Where we are now

- Avatars in storage: `body_apose.obj` (CLO/mm scale), `avatar_textured.glb`, `measurements.json`, `smpl_params.npz`, etc.
- Garments: per-size **`xs.glb` … `xl.glb`**.
- Widget / backend try-on path exists; **no** dedicated cloth-sim worker or heatmap artifact yet.
- Decision: **NVIDIA Warp** (+ evaluate **NvidiaWarp-GarmentCode** for body/self-collision helpers).

**Exit criteria for Phase 0:** agreement on inputs (URLs or local paths), output format (GLB with vertex colors and/or heatmap texture), and branch name for the worker.

---

## Phase 0.5 — Worker skeleton (no physics sophistication yet)

Starter layout in-repo: **`heatmap-worker/`** (see `heatmap-worker/README.md`).

1. **Branch** (e.g. `feature/heathmap`) — worker code can live in `avatar-creation/` or new top-level `heatmap-worker/` (single responsibility: sim + export).
2. **Dockerfile** — CUDA **devel** image; clone **NvidiaWarp-GarmentCode**, `python build_lib.py`, `pip install -e .`; plus `trimesh` / `requests` (see `heatmap-worker/Dockerfile`).
3. **RunPod smoke test** — one-shot script: `import warp as wp`; allocate a tiny array on GPU; log success.
4. **Asset pull** — script accepts **signed URLs** or local paths; downloads **`body_apose.obj`** + **`m.glb`**; loads vertices/faces; logs **bounding box** and **vertex count** (sanity: heights ~order 10³ mm).
5. **Coordinate check** — assert garment and body **overlap plausibly** in the same frame (no accidental meters vs mm mix).

**Exit criteria:** Container runs on RunPod; loads real Supabase-exported assets; no simulation yet.

---

## Phase 1 — Physics spike + export + parallel five sizes

### 1.1 Single size (medium only)

6. **Rest configuration** — use uploaded **m.glb** mesh as cloth **rest** (initial world positions as starting pose, or offset slightly outside body if initialization penetrates — tune one strategy and document it).
7. **Body collider** — **`body_apose.obj`** as **kinematic** collision mesh (same mm frame).
8. **XPBD cloth** — Warp (or GarmentCode fork if import path works): stretch + bend; **self-collision** if needed for sleeves.
9. **Settle** — run until velocity threshold or **max substeps/frames** cap; record wall time.
10. **Scalar field (v1 heatmap)** — per-triangle or per-vertex **stretch ratio** vs rest edges (CLO *strain-map* analogue); optional v2: weight by contact.
11. **Export** — write **output GLB** (garment mesh + **vertex colors** and/or **ORM/secondary texture** for heat); keep **JSON** sidecar with `min`/`max` for consistent color scale in the viewer.

### 1.2 Size sweep + parallel

12. Repeat 6–11 for **`s.glb`**, **`xs.glb`**, **`l.glb`**, **`xl.glb`** with **same body**.
13. **Parallel driver** — one process **five GPU streams** vs **five separate jobs** (RunPod serverless often = five jobs simpler); measure **total wall time** vs your 10–30 s goal.
14. **A/B (later in Phase 1):** same pipeline with **OBJ** garment export if GLB triangulation or materials differ.

### 1.3 Minimal integration touchpoint (still Phase 1)

15. **Input contract** — JSON: `{ "body_url", "garment_urls": { "xs": "...", ... }, "units": "mm" }`.
16. **Output contract** — JSON: `{ "per_size": { "m": { "glb_url" | path, "stats": {...} } } }` (actual upload to Supabase can be Phase 2).

**Exit criteria for Phase 1:** Reproducible RunPod run: **A-pose + five GLBs → five heatmap GLBs (+ stats)** within measured time; documented timings and any failure modes (interpenetration, explode mesh).

---

## Explicitly after Phase 1 (not in scope here)

- Backend enqueue + polling; widget toggle; merchant aggregation.
- PERSONA swap; SMPL-driven body (only if OBJ insufficient).

---

## Risk notes (short)

- **mm physics:** Solvers are agnostic; **inconsistent stiffness** vs real cloth is the usual issue — start with **tunable** scalars and compare **relative** stress across sizes before chasing absolute kPa.
- **10–30 s for five parallel:** plausible for moderate meshes; **high-res** garments or many substeps can exceed — parallel jobs + early termination help.

---

*Created: 2026-03-29 — Phase 0 → Phase 1 testing plan.*
