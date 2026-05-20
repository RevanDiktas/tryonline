# Status report 2026-05-20 (Wed)

## Headline

End-to-end DECA + measurements test at 21:00 returned the bundle but with
two structural failures: DECA face mapping never ran (gcc-7 ccbin pin in
upstream smplx-deca renderer.py kills the JIT compile on CUDA 12.1 + gcc
11), and LHM's internal splat pass crashed with a shape-broadcast error
we couldn't see (handler swallowed the traceback). Two follow-up
Dockerfile patches were tried (771245f, c84b884), both exceeded RunPod's
30-min build cap and got killed at cache export, the second one
poisoning a layer ref. User called the pivot at 22:55: park realistic
avatar entirely, strip DECA + LHM splat stack from the image, produce
the same artifact set as production 4DHumans on SMPL-X geometry via
LHM's Multi-HMR pose estimator standalone. That ship was 8626154
(~12-15 min build budget projection). 07faeb7 followed minutes later
adding cheek-zone + HSV skin filter for cleaner face-median color (only
COPY handler.py rebuilds on top, ~2 min). End-to-end test deferred to
2026-05-21.

## What actually shipped (keep)

1. **Avatar bundle is now 4DHumans-equivalent on SMPL-X**, no DECA, no
   splats. cmd_avatar produces:
   - body_apose.obj
   - body_tpose.obj  (NEW)
   - avatar_textured.glb (A-pose, uniform face-median skin)
   - skin_texture.png
   - measurements.json (T-pose-derived, 16 standardized + 17 raw,
     height-normalized when height_cm supplied)
   - smplx_params.npz
   - face_crop.png

2. **Standalone PoseEstimator + FaceDetector singletons.** New
   _get_pose_estimator and _get_face_detector replace _get_inferrer.
   Both import their classes from LHM directly without going through
   HumanLRMInferrer. Same model weights, same SMPL-X output, fraction
   of the import graph. Reasoning is now documented inline in the
   handler.

3. **Cheek-zone + HSV skin filter.**
   _sample_face_median_color_v2 now does:
   stage 1 - face bbox crop (clothes can't leak in),
   stage 2 - cheek zone (y in 40-70%, x in 20-80% excludes eyes/lips/hair),
   stage 3 - HSV filter (H<=25, S 15-70%, V 30-90% excludes shadows /
            makeup / facial hair).
   Safety net falls back to unfiltered cheek pixels if HSV keeps <5%.

4. **Dockerfile stripped 94 lines.** Dropped sam2 + diff-gaussian +
   simple-knn (3 heavy CUDA compiles, ~10-13 min build time) plus the
   DECA stack (chumpy, face-alignment, kornia, yacs, fvcore,
   scikit-image, smplx-deca clone, FLAME correspondence wget, DECA
   smoke test). Kept pytorch3d (Multi-HMR's SMPL-X ops), xformers,
   rembg, basicsr. Projected build time ~12-15 min total, comfortably
   inside RunPod's 30-min cap.

5. **Disk crisis handled.** Local Mac was at 99% / 142Mi free at the
   start of the session, which started ENOSPC'ing the Bash tool's
   output dir. Walked the user through APFS local snapshot thin,
   Library/Caches purge, Adobe-Microsoft-Google nukes,
   Cursor/Chrome/Spyder caches. Final state: 77% / 3.5Gi free.

## What did not work today (do not repeat)

1. **DECA failed first run for a fixable but non-obvious reason.**
   smplx_deca_main/deca/decalib/utils/renderer.py line 42 hardcodes
   `extra_cuda_cflags=['-std=c++14', '-ccbin=$$(which gcc-7)']`. On
   CUDA 12.1 + Ubuntu 22.04 base, gcc-7 isn't installed, $(which gcc-7)
   expands to empty, nvcc dies with "Failed to preprocess host
   compiler properties". The pin is a CUDA 10.2 era carryover (their
   own comment says so). Fix is one-line: strip the flag. Either at
   build time via sed/python-regex patch on the file, or at runtime via
   a `_patch_smplx_deca_ccbin()` function called before any DECA
   import. We chose runtime patch in c84b884 to avoid full image
   rebuilds for tiny changes.

2. **771245f exceeded 30-min build cap.** Bumped CACHEBUST near the top
   of the Dockerfile to invalidate everything downstream of FROM,
   which forced full recompile of pytorch3d / sam2 / diff-gaussian /
   simple-knn. Killed at cache export. Poisoned the final layer ref
   sha256:22ba0fb...

3. **c84b884 also exceeded the cap.** Reverted Dockerfile to dc154c7's
   exact content + moved the ccbin patch to handler.py. Expectation:
   cache hits all heavy layers since Dockerfile content was identical
   to a previously-successful build. Reality: RunPod recompiled heavy
   layers anyway (some cache miss we don't fully understand, possibly
   the poisoned ref from 771245f). 30-min cap killed it at exactly
   1800s.

4. **Splat broadcast bug is INSIDE LHM, not our handler.** Error
   `operands could not be broadcast together with shapes (2361,1417,3)
   (2977,1417,1)`. Our k-NN code uses k=5 hardcoded, can't produce
   K=1417 in any tensor. Pinning it would need LHM-internal trace,
   which we tried to surface via traceback.format_exc in 771245f /
   c84b884 but never got to see because both builds failed. Moot now
   because we no longer call inferrer.infer_mesh in the pivot.

5. **"Cache hot rebuild" theory was wrong.** We assumed a Dockerfile
   byte-identical to a previously-successful build would hit RunPod's
   registry cache and finish in <5 min. Empirically, c84b884
   recompiled everything from scratch. Don't make architectural
   decisions ("just push, it'll be cache-hot") based on theory
   about RunPod's cache model when we haven't validated it.

6. **Realistic avatar is parked.** DECA + HairStep + Hand4Whole etc.
   were the realistic-avatar roadmap. We do not have the team /
   research capacity to ship that at the quality bar user wants
   (Avaturn-class). Returning to 4DHumans-equivalent SMPL-X output
   was the user's call. Probably needs dedicated researcher hire
   before resuming.

## Tomorrow's plan (locked)

1. **End-to-end test of 07faeb7.** Fire the avatar command against
   tryonline-lhm (lo2s3qevrvfotn) with:
   - image_url: existing Supabase URL (user_001.jpg)
   - height_cm: 192, weight_kg: 85, gender: male
   - NO selfie_url anymore - that's gone with DECA
   Verify the response contains URLs to all 7 expected artifacts
   (body_apose.obj, body_tpose.obj, avatar_textured.glb,
   skin_texture.png, measurements.json, smplx_params.npz,
   face_crop.png).
   Visual checks:
   - face_crop.png matches the face in the body photo
   - avatar_textured.glb skin tone matches user's actual skin tone
     (no clothing bleed, no shadow contamination)
   - body_apose.obj loads cleanly in a viewer
   - body_tpose.obj loads cleanly in a viewer
   - measurements.json has 16 standardized + 17 raw, height ~= 192

2. **If skin tone is still off**, inspect skin_rgb in the JSON
   response. The handler stdout has `[face_median_v2] HSV kept
   X/Y cheek pixels`. Low ratio means the HSV filter rejected too
   much. Bump V's upper bound or relax H to <=30.

3. **Wire backend + frontend to the new endpoint.** Once artifacts
   look right:
   - backend: add an endpoint (or extend existing) that POSTs to
     `tryonline-lhm /run` with the photo URL + height/weight/gender,
     waits for COMPLETED, and returns the artifact URLs.
   - frontend: avatar-creation flow consumes the URLs the same way
     it consumes 4DHumans's bundle today. No realistic-face flow.

4. **Do not push without py_compile.** Both today's pushes had
   py_compile gates that returned clean and shipped. Keep the
   discipline.

## Endpoint + asset state at end of session

- `tryonline-lhm` = `lo2s3qevrvfotn`: building commit 07faeb7 on top
  of 8626154. Previously rolled out: dc154c7 (broken: DECA fails,
  splats fail, returns uniform skin GLB + measurements only).
- `tryonline-drape` = `e86juazm1b4mig`: untouched.
- `tryonline` = `dca4hvdv72f28j` (production 4DHumans): untouched.
- LHM SHA in image: still pinned to 4f88aaeb (2026-03-17 release).
- DECA assets: removed from build path. Will be re-added when realistic
  avatar resumes.
- Supabase lhm-artifacts bucket: holds today's test artifacts at
  avatars/1779303623/ (uniform-skin GLB + measurements, no face),
  inputs at inputs/2026-05-20/ (selfie + user_001).

## Lessons (for future sessions)

1. **Don't bump CACHEBUST when iterating on small fixes.** CACHEBUST
   at top of the Dockerfile triggers a full rebuild of every layer
   downstream including 4 heavy CUDA compiles totalling ~20 minutes.
   When the change is a one-line patch to an already-installed
   package, prefer a runtime patch in the handler.

2. **30-min cap covers RUN + image-layer export + cache export.** Pre-
   build minute estimates need concrete per-step numbers vs the
   known-good baseline, with margin >=5 min before pushing.

3. **Verify-before-push has a "verify infrastructure assumption"
   corollary.** We assumed RunPod's BuildKit cache would hit on a
   byte-identical Dockerfile. It didn't. When the assumption is about
   infrastructure (cache, deploy, build), validate it BEFORE
   architecting around it.

4. **The clean fix for a transitive hard import is to NOT import the
   thing that pulls it in.** When LHM's HumanLRMInferrer transitively
   hard-imports diff_gaussian_rasterization, the answer wasn't to keep
   the splat stack. It was to import PoseEstimator and FaceDetector
   directly and bypass HumanLRMInferrer. Read the import graph before
   accepting "we need this dep."

5. **Pivot ruthlessly when the bar isn't reachable.** Realistic avatar
   needs researchers + months. 4DHumans-equivalent on SMPL-X ships
   tonight. Park the dream, deliver the working product.

## Commits

- `771245f` - fix(lhm): strip DECA -ccbin gcc-7 flag + surface LHM
  traceback on splat fail. (BUILD FAILED at 30-min cap, poisoned a
  layer ref.)
- `c84b884` - fix(lhm): move DECA ccbin patch from Dockerfile to
  handler runtime. (BUILD FAILED at 30-min cap, even with revert to
  dc154c7's Dockerfile content.)
- `8626154` - feat(lhm): produce 4DHumans-equivalent SMPL-X bundle,
  drop splat+DECA stack. (Building; central-50% face sampling.)
- `07faeb7` - feat(lhm): cheek-zone + HSV skin filter for face-median
  color. (Building on top of 8626154; cheek-only + HSV filter.)

All on `origin/feature/lhm`.
