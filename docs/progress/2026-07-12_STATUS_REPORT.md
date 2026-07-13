# Status Report - 2026-07-12

## Photoreal avatar Stage 2b: real avatar pipeline runs end-to-end on LHM++

Picked up from 2026-07-11 with Build #4's health probe green. Goal for the day:
close out Stage 1 and stand up **Stage 2b** - a real `cmd_avatar_photoreal` that
reproduces today's production avatar contract off **LHM++** instead of the
SMPL-X-licensed LHM path. We got the full pipeline running and GPU-verified in
33 s; one measurement bug remains, its fix is building.

Endpoint: `avatar-creation-photoreal`, RunPod ID **`bun2qr20qvnre5`**, branch
`feature/photoreal-avatar`. **No Network Volume** (deliberate - see below).

---

## What shipped

1. **Stage 1 closed out.** Build #4 health ping is fully green on an A40 (sm_86):
   every CUDA ext (`pytorch3d`, `gsplat`, `diff_gaussian_rasterization`,
   `simple_knn`, `pointops`) + `lhmpp_pose_estimator` + `smpl_anthropometry` load.

2. **Stage 2b handler written and source-verified** (commit `c415951`).
   `cmd_avatar_photoreal`:
   `photo_url -> LHM++ Multi-HMR PoseEstimator -> hidden SMPL-X betas ->
   SMPL-X A-pose + T-pose mesh (smplx) -> SMPL-Anthropometry 16-key bundle ->
   flat base64 artifact set` (apose/tpose OBJ, tinted GLB, skin PNG, npz). The
   output is the exact flat contract today's backend already uploads, so flipping
   the endpoint later needs **no backend change**. Prior models
   (`human_model_files`: Multi-HMR + SMPL-X) are runtime-pulled from HF
   `3DAIGC/LHMPP-Prior`. Verified against LHM++ source that every file the
   estimator loads is present (`multiHMR_896_L.pt`, `smpl_mean_params.npz`,
   `smplx/*.npz`).

3. **e2e VERIFIED on GPU (the milestone).** A real photo job COMPLETED in **33 s**:
   - Multi-HMR pose est: `beta_shape [10]`, `is_full_body true`
   - SMPL-X mesh: **10475 verts / 20908 faces** (correct topology), A-pose `z_0.7854rad`
   - all 5 artifacts written (apose 654 KB, tpose 649 KB, GLB 420 KB, skin PNG, npz),
     2.3 MB total, under the ~20 MB inline cap.

---

## Bugs hit and fixed (in order)

- **Cold-download timeout (job e2a41140 FAILED "executionTimeout exceeded" @ 611 s).**
  First avatar call blew the endpoint's ~600 s execution cap *while still
  downloading* a ~4 GB prior - inference never started. Two fixes:
  - **Narrowed the download** (`6273acd`): `human_model_files/**` 4 GB -> ~2.15 GB
    by fetching only `pose_estimate/` + `smplx/` + `smpl_mean_params.npz`,
    dropping a 1.26 GB FLAME texture + ~490 MB of FLAME/SMPL `.pkl` we never load.
  - **hf_transfer** (`1f8ecc1`): Rust parallel downloader + `HF_HUB_ENABLE_HF_TRANSFER=1`,
    so the pull saturates the worker link (~200+ MB/s) instead of ~6.7 MB/s HTTP.
    Result: cold job dropped from 611 s (timeout) to **33 s**, WITHOUT a volume.
  Added a `warm` command to pre-populate the prior on demand.

- **Measurements assert `SMPLX_NEUTRAL.pkl does not exist` (FIXED at v0.9, `2acf013`).**
  A five-build rabbit hole. `measure.py` loads SMPL-X at TWO sites, both pinned
  `ext="pkl"`: `MeasureSMPLX.__init__` AND `get_joint_regressor` (`smplx.create`,
  called from `from_verts`, outside any `__init__` patch scope). We only ship
  `.npz` models. Every ext-patch attempt failed: the Dockerfile `sed s/.pkl/.npz/`
  can't reach a dotless kwarg; a broadened sed to convert `ext="pkl"` **cached
  nondeterministically** on RunPod (the assert flipped from `.pkl` to `.npz`
  between v0.7 and v0.8, proving the layer only rebuilt intermittently); a runtime
  source-patch lost to a **sys.modules cache race** with the health-ping selftest's
  `__import__("measure")`; and a `smplx.SMPLX` monkeypatch only covered the
  `__init__` site, not `from_verts`. **Structural fix that stuck:** stop betting on
  the ext - place the SMPL-X model under **BOTH** extensions in `data/smplx/`
  (`.npz` symlinked from the LHM++ prior we already load; `.pkl` converted from it,
  since smplx feeds `np.load(npz)` and `pickle.load(pkl)` into the same
  `Struct(**data)`). Load resolves whichever ext the build lands on. **v0.9 e2e:
  `measurements_error: None`, full 16-key bundle populated** (chest 97.6, waist
  82.1, hips 101.5, inseam 78.7, neck 35.2, ... for a 178 cm subject), 30.7 s.

---

## State at end of session - STAGE 2b COMPLETE (v0.9, Build #11)

- **`cmd_avatar_photoreal` is fully working end-to-end**, matching today's
  production flat contract: Multi-HMR -> hidden SMPL-X betas -> A/T-pose mesh
  (10475 verts) -> **populated 16-key measurements** -> 5-file base64 set, ~31 s
  cold, no Network Volume. Endpoint `bun2qr20qvnre5` healthy on A40.
- Skin is a **neutral-tan placeholder** by design (LHM++ has no face-detector
  wrapper; Stage 3's multi-image splat appearance replaces the tint wholesale).
- Sample output decoded for inspection:
  `avatar-creation-photoreal/test_outputs/v0.9-stage2b__neutral_h178__4e6e2edf/`
  (open `avatar_textured.glb`).

## Next session (pick up here) - 2026-07-13

1. **VERIFY THE OUTPUT visually (top priority per Revan).** Open the decoded
   `avatar_textured.glb` / OBJs and actually *look*: pose, proportions, body shape
   vs the source photo. Output correctness is what matters most. (Current test used
   an old LHM selfie; re-run on a known subject to judge fidelity.)
2. **Make the model MULTI-IMAGE input.** Revan will provide the test images.
   Extend `cmd_avatar_photoreal` (or a new path) to accept 3-4 guided photos ->
   LHM++ multi-image reconstruction. Bridge to Stage 3 (photoreal splat
   appearance). LHM++ `to_gs_ply.py` supports multi-view; the pose estimator
   currently takes one front photo for betas.

## Guardrails reaffirmed

- **No Network Volume** (Revan's call): the prior re-downloads per cold worker, so
  hf_transfer + the narrowed 2.15 GB set are load-bearing - do not widen
  `PRIOR_ALLOW_PATTERNS` without re-checking the cold-start budget.
- Keep the endpoint off Blackwell (sm_120) GPUs; 48 GB + 80 GB PRO only.
- Never touch live `tryonline-lhm` (`lo2s3qevrvfotn`). Flip Railway
  `RUNPOD_ENDPOINT_ID` only after e2e + drape smoke test.

Full staged plan + reuse map: `~/.claude/plans/humming-hugging-parrot.md`.
Test photo: `.../lhm-artifacts/inputs/2026-05-20/user_001.jpg`.
