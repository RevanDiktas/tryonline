# Status Report — 2026-05-31

Two workstreams today: (1) finished the LHM splat-to-mesh task and parked the
realistic-avatar work, then (2) kicked off a brand-new workstream — automated
garment construction from merchant photos.

---

## WIN 1 — LHM splat PLY -> watertight mesh OBJ (DONE, then parked)

Continued from 2026-05-30. Turned the `tryonline-lhm` Gaussian-splat point
cloud into a real surface mesh.

- **Output:** `splats_mesh.obj` — 52,152 verts / 102,750 faces, per-vertex
  colour, watertight, ~8.8 MB. Poisson reconstruction (depth 9, density-trim
  3%) from yesterday's 20k-point `splats.obj`.
- **Quality:** a clean, recognizable human body in T-pose, NOT a blob. Honest
  artifacts: hair = inflated blob, mild torso lumpiness, melted hands/feet.
- **Env gotcha solved:** default `python3` here is 3.13 (x86_64) and open3d has
  no cp313 wheel. Built a py3.12 venv (`~/Downloads/splatenv`) to run it.
  open3d's offscreen renderer can't run headless on macOS, so used matplotlib
  for sanity renders.

### Parked cleanly
User decided to park realistic-avatar to focus on the higher-priority garment
pipeline. All outputs + scripts moved into `mvp_pipeline/realistic-avatar/`
(scripts/ outputs/ renders/ + a README with the resume runbook). Verified
byte-identical to the Downloads originals before the user deleted those.

---

## WIN 2 — Automated garment construction pipeline (NEW, kicked off)

Goal: merchants stop hand-building garments in CLO3D. New flow takes garment
photos -> 3D garment OBJ automatically. **Draping stays on our existing system
unchanged** — construction just produces the file bundle the drape service
already accepts.

Branch: `feature/garment-construction` (new, isolated). Target: a NEW RunPod
serverless endpoint (`tryonline-garment`), separate from tryonline /
tryonline-lhm / tryonline-drape.

### Research win: verified a Claude-on-Chrome roadmap against primary sources
The roadmap (`~/Downloads/TRYON_ROADMAP.md`) was directionally right but wrong
on load-bearing specifics. Fanned out 4 research agents + direct repo reads.
Findings (full audit: `docs/research/GARMENT_PIPELINE_VERIFICATION_2026-05-31.md`):

- **ChatGarment** (Apache-2.0, CVPR'25): real. Takes a SINGLE worn photo (not
  3-5), outputs a GarmentCodeRC parametric JSON program (not polygon vertices).
  LoRA on LLaVA-1.5-7B.
- **GarmentCodeRC + the Warp fork** do the 2D->3D drape. The sim engine
  (`NvidiaWarp-GarmentCode`) is NON-COMMERCIAL — accepted for prototype, flagged
  to replace before paid use (joins DECA/Multi-HMR on that list).
- **DressCode Stage-4 was hallucinated** — it's a text->pattern generator, no
  photo input, no `generate_texture.py`. Dropped. (User's instinct was right:
  our drape model already does texture MAPPING; we only need to EXTRACT.)
- **Panelformer** repo is an empty stub; **SewFormer** is a viable fallback but
  has no license file. Every shell command in the roadmap was fabricated — got
  the real ones by reading the actual source.

### Key reuse win
The existing `avatar-creation/draping/Dockerfile` (v18) ALREADY compiles
`NvidiaWarp-GarmentCode` + pygarment on the same `runpod/pytorch:2.1.0-cu118`
base, with hard-won flags. The single hardest dependency in the whole stack is
already solved in our repo — the base image reuses that recipe verbatim.

### Architecture simplification
ContourCraft-CG is NOT needed: `run_garmentcode_sim.py` already drapes via the
Warp fork on the bundled `mean_all` body (`smpl_body=False`), so construction
needs no SMPL-X. The roadmap's 5 stages collapse to 2 real steps + texture.

### Code written this session (all compiles, grounded in real source)
In `avatar-creation/garment-construction/`:
- `handler.py` (545 lines): STEP 0 bootstrap -> STEP 1 ChatGarment ->
  STEP 2 GarmentCodeRC drape -> STEP 3 texture extract -> Supabase upload.
- `Dockerfile.base` + `build_base.sh` (compile heavy deps once on a GPU pod).
- `Dockerfile` (thin serverless layer FROM base, fast build).
- `BUILD_SPEC.md`, `PROCESS.md` (runbooks), `.gitignore`, and `REFERENCE_*`
  copies of the upstream scripts the handler is built against.

### Decisions locked (user, today)
1. Sim backend = ChatGarment-native (GarmentCodeRC).
2. Texture = extract only (drape model maps it); no AI texture baker.
3. Deploy = straight to a new isolated serverless endpoint, via a pre-built
   base image (avoids RunPod's 30-min CPU-only build cap).

---

## In flight / blocking next steps
- **Checkpoint download — DONE** (18:01). `pytorch_model.bin` = 13.96 GB on the
  external disk at `weights/chatgarment/`, validated as a real torch zip (PK
  magic bytes, not an error page). Auth-gated SharePoint link, pulled via the
  logged-in browser (no public mirror exists). Remaining steps all need a GPU
  pod / bucket, none doable on the Mac.

## Pick up next session (garment pipeline)
1. Checkpoint finishes -> mirror to a bucket -> set `CHATGARMENT_CKPT_URL`.
2. Spin up a GPU pod -> `bash build_base.sh push` (compiles the Warp fork,
   ~30-60 min, no cap on a pod).
3. Build + deploy the thin serverless image -> create the `tryonline-garment`
   endpoint -> test one real garment end-to-end.
4. Confirm the open risks on first GPU run (deepspeed-vs-python launcher,
   ChatGarment run-folder mapping, `*_sim.obj` output name) — handler already
   scans robustly rather than assuming.
