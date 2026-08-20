# FAILURES

Patterns we have already paid for. Each one cost real time, real money, or real review-cycle delay. If you are about to do something that matches one of these, stop and re-check. New entries go in only after the same failure has happened, not preemptively.

---

## F1. Verify before you push (especially RunPod)

**The pattern:** Make a code change based on a quick read, push to RunPod (or commit to a shared branch), and discover the change was wrong only after a 10–30 minute build cycle burns.

**Rule:** Before any non-trivial fix, trace the logic end-to-end against actual source. For RunPod handler changes, this is non-negotiable. The `runpod-handler-rigor` skill enforces this when editing `avatar-creation/**/handler.py` or running `build.sh`.

**Where it bites:** `avatar-creation/draping/handler.py`, `avatar-creation/draping/Dockerfile`, the `tryonline-drape` endpoint (`e86juazm1b4mig`).

---

## F2. OBJ-native pipeline. Do not reintroduce GLB injection.

**The pattern:** "Just convert it to GLB upstream" feels simpler, but the CLO3D-style GLB injection + nearest-vertex mapping path produced wrong drape topology and lost MTL/texture fidelity.

**Rule:** Stay OBJ + MTL + textures end-to-end through draping. Do not reintroduce a GLB-injection step or nearest-vertex mapping shortcut.

**Where it bites:** Anywhere in the draping pipeline, especially when adding a new garment ingest path. Reference test URLs are in `CLAUDE.md`.

---

## F3. When tweaking stops working, name the structural cause

**The pattern:** Two or three serial scalar/threshold/flag adjustments in a row ("try 0.01", "try 0.005", "try 1.5x"), each one regresses or stalls. The instinct is to keep tweaking. The instinct is wrong.

**Rule:** When the same parameter has been changed more than twice without progress, stop. Name the structural cause (wrong coordinate frame, wrong solver assumption, missing constraint, wrong topology) and propose the harder fix. The `structural-debug` skill triggers on this.

---

## F4. Shopify rejection on test credentials (rule 4.5.5)

**The pattern:** Submitted the Shopify app with Google SSO test accounts. App rejected on rule 4.5.5 because reviewers cannot use SSO accounts they do not own.

**Rule:** Test credentials in the listing must be dedicated email/password merchant + shopper accounts on the dev store (`tryon-9626.myshopify.com`). Testing instructions must point at the dev store. The `shopify-app-review-prep` skill encodes this and other App Store rejection patterns; run it before any submission or resubmission.

**Status:** Resubmitted 2026-05-01 with the fix. Do not repeat.

---

## F5. Em-dashes and "Palantir" leak into copy

**The pattern:** Em-dashes (`—`) make copy read as AI-generated. The word "Palantir" in user-facing copy is off-brand for our positioning.

**Rule:**
- Never use em-dashes in chat, code, copy, or commits. Use periods, commas, colons, parentheses. Sweep existing copy when you find one.
- Never use "Palantir" in user-facing copy. Describe analytics by concrete capability (cohort analysis, return-reason classification, fit confidence scoring).

**Where it bites:** Any landing-page edit, any new marketing component, any commit message.

---

## F6. Design system drift

**The pattern:** A new component ships with rounded corners, color accents beyond B/W, pill chrome, glassmorphism, or "PLAY"-style neon. Each individually feels small. Cumulatively they erode the brand.

**Rule:**
- Sharp corners only (`borderRadius: 0`).
- Black and white only. No neon glow, no yellow CTAs, no holographic rim.
- One shared nav (`SharedNav` for marketing, `DashboardShell.FloatingNav` matching it).
- Font stays Inter via `--display`.
- Brand and shopper hero tiles must be prominent (large 200px tiles side-by-side under the primary CTA).
- The lobby aesthetic comes from layout, not from skinning.

---

## F7. Touching production widgets without testing on the live store

**The pattern:** Edit `frontend/public/test-viewer.html` (the PDP widget on Ramin Studios) without first verifying the change on the live Shopify store.

**Rule:** Do not change the PDP widget without testing on Ramin Studios first. CLAUDE.md flags this in DO NOT.

---

## F8. Pushing untested code to shared branches

**The pattern:** Push to `main` or `feature/analytics` from an experimental branch (typically `drape`) and break Vercel auto-deploy.

**Rule:**
- Never push untested code to `main` or `feature/analytics`.
- Do not push from `drape` to Railway or Vercel; test in isolation on the drape RunPod endpoint first.
- Never `git push --force` on a shared branch.

---

## F9. The texture-data was empty for weeks because of a name mismatch

**The pattern:** CLO3D's OBJ has `mtllib mm.mtl` (two m's) but Supabase only hosts `m.mtl` (one m). Input-side download flow correctly falls back to `m.mtl`. But the output-side packager reads mtllib from the draped OBJ, gets "mm.mtl", looks for it on disk, fails, and SILENTLY skips the entire MTL+textures packaging block. Response went out with empty `draped_mtl_base64` and empty `draped_textures_base64` for weeks. v35-v38 frontend texture work could not possibly succeed because the backend was sending nothing.

**Rule:** When debugging a multi-stage pipeline, do not stop at the first stage that "appears to work." The input download log said `Downloaded MTL: m.mtl` and `Downloaded texture: 1.png/2.png`, which made the input look fine. The output packaging log was MISSING entirely. The absence of an expected log line is itself a diagnostic. Always check for both presence AND absence of expected log signals.

**Where it bites:** Any handler-side packaging step where a missing input is treated as "skip silently and ship a partial response." Add explicit warn logs to the SKIP path.

**Status:** Fixed in v39 (2026-05-03) with two-layer defense: (1) input-side aliases the downloaded MTL under the OBJ's mtllib reference name, (2) output-side falls back to glob `*.mtl` if the named file does not resolve.

---

## F10. Newton XPBD was the wrong layer for our use case

**The pattern:** v18-v35 ran NVIDIA Newton XPBD cloth simulation on top of the v26 retarget. cloth_reference_drag was a warmup force designed for FLAT 2D PATTERNS being guided to 3D body regions during initialization. Our pipeline starts with a CLO3D-DRAPED 3D garment that's already correctly positioned. Drag had no useful work to do but produced every visible artifact (hood-yanked-to-shoulder, sleeves crossed, pants flying, butt holes, panel mis-votes). Each version v18-v35 fixed one panel-assignment vote and exposed another.

**Rule:** When a sim or solver is producing artifacts and each fix exposes a new artifact, the sim itself may be the wrong layer. Don't tune the votes. Disable the force that uses them. Especially: when integrating an upstream solver written for a DIFFERENT input shape (their flat 2D pattern vs your already-draped 3D mesh), the solver's warmup phase is often misapplied to your input.

**Where it bites:** Any time you're integrating someone else's physics or constraint solver. Read what their solver assumes about input state, not just what it claims to produce.

**Status:** Fixed in v36 (2026-05-03). `SKIP_NEWTON_SIM = True` ships the v26 retarget directly. Newton path preserved beneath the early return for A/B but no longer the shipping path.

---

## F11. Coplanar surfaces need polygonOffset, not Kd hacks

**The pattern:** v26 retarget snaps every cloth vert to body+12mm. CLO3D's intentional layer offsets between print fabric, body fabric, and binding fabric collapse to coplanar geometry. The renderer's depth test picks one or the other arbitrarily per pixel, producing irregular black blobs covering prints, white rectangles behind logos, and disappearing zippers. v42's first attempt was to override material colors to mask the z-fighting visually. That worked for the print backing but killed the visible zipper.

**Rule:** When two surfaces are at the same depth and you need one to render on top, use `polygonOffset` (negative offset for "render in front", positive offset for "render behind"). Do not use color overrides to mask z-fighting; color overrides break legitimate uses of those materials elsewhere. polygonOffset is the standard technique 3D engines use for decals, shadow maps, and any coplanar geometry.

**Where it bites:** Any time a retarget, sim, or transform brings authoring-time-offset surfaces into coplanarity. CLO3D garments specifically: print panels, binding panels, body panels.

**Status:** Fixed in v43 (2026-05-03). Three z-layers via polygonOffset: PT_FABRIC offset -2 (front), Body/Sleeves/FABRIC_1 default, FABRIC_2 offset +1 (back). All materials keep CLO3D's original Kd values.

---

## F12. Three.js OBJLoader puts everything in one mesh when there are no `o` lines

**The pattern:** v44 looked up per-material vertex mappings via `c.material.name` during animation playback. Animation logs fired but cloth never moved.

CLO3D's OBJ has 26 `usemtl` blocks but no `o` (object) delimiters. Three.js OBJLoader without `o` lines puts ALL faces into ONE BufferGeometry on ONE Mesh, with the mesh's material set to an ARRAY (per-face groups index into it). `c.material.name` is undefined because Arrays have no `.name` property. Every traverse iteration silently skipped.

**Rule:** When working with three.js OBJLoader, do not assume one mesh per material. Check the actual structure produced. For per-vertex animation, build a single FLAT mapping in OBJ face-traversal order. Three.js OBJLoader's position attribute is laid out in the same order, so the flat mapping indexes into it directly without material-name lookup.

**Where it bites:** Any feature that walks the OBJLoader output expecting per-material meshes. The structure depends on whether the OBJ has `o` lines, which is brand-specific.

**Status:** Fixed in v44.2 (2026-05-03).

---

## F13. Fixing the data is not fixing the bug

**The pattern:** A bad value is found in production artifacts, the artifacts get
corrected in place, the symptom disappears, and the code that produced them is
left alone. The next run puts the bad value straight back.

On 2026-08-03 avatars were found to be pelvis-centred, which makes the drape
handler's `_is_prefitted` fail and `align_meshes` rescale garments by ~1.77x
while still reporting `body_collisions=0`. The fix re-zeroed the OBJ/GLB files
already in storage and repointed the database. Both handlers that emit those
files were untouched. On 2026-08-20 the photoreal endpoint was measured and found
to be emitting the exact same broken frame, and Stage 3 was about to bake
appearance on top of it.

**Rule:** when a data repair closes a symptom, say out loud which code path
produced the bad data and either fix it in the same session or write it down as
open. A repair that leaves the producer alone is a snooze, not a fix. If the
producer cannot be fixed yet, add an assertion or a self-check to the output so
the next occurrence is loud instead of silent.

**Where it bites:** anything that writes a coordinate frame, a unit, or an ID
convention into an artifact that something else reads later.

**Status:** producer fixed 2026-08-20 (`c9ce07c`), plus a `frame_check` block in
the response read back off the written arrays, plus a regression gate at
`avatar-creation-photoreal/scripts/verify_floor_frame.py`. Still open: the
`_is_prefitted` offset tolerance in the drape handler, which is the permanent
defence.

---

## F14. A test harness must mirror production units and layout, not your assumption

**The pattern:** The harness is written against what the data "obviously" is
rather than against what the production code actually does with it. It then
reports a confident number that means nothing.

On 2026-08-20 a harness checking the drape alignment divided both meshes by 1000
on the assumption that OBJs are millimetres. Body OBJs are. CLO3D garment OBJs
are already in **metres**. The result was a garment reported as 1.0 mm tall and a
scale factor of 1720x, which looked like a catastrophic bug and was purely the
harness. The production handler gets it right: `_normalize_to_meters` keys off
the height span and converts only the mesh that needs it.

**Rule:** in any verification harness, call the production helper rather than
reimplementing its assumption. Where that is impossible, print the intermediate
values and sanity-check them against a known-good artifact before trusting the
conclusion. This is the same trap as the v45 -> v45.1 trimesh directory-layout
lesson, one level up.

**Where it bites:** any local harness for the drape or avatar pipelines. Note
also that the working-tree `avatar-creation/draping/handler.py` on other branches
is around v45.x and has no `_is_prefitted`; the deployed v47.1 lives on `drape`.
Pull the logic with `git show drape:...`, do not read the copy next to you.

---

## How to add a new failure here

A new entry earns its place when:
1. The same mistake has happened at least twice, OR
2. A single mistake cost more than ~30 minutes of build/review/debug time AND the cause is not obvious from the code.

Speculative "what if we forget to X" rules do not belong here. Put those in `CLAUDE.md` under conventions instead.
