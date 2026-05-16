# PERSONA integration framework

Author: Claude (research pass)
Date: 2026-05-16
Status: research + design proposal. Nothing built yet.

## 0. Executive summary

We are adding a second avatar track on top of the existing 4D-Humans pipeline:

- **Anonymous** (existing): 4D-Humans on RunPod `tryonline`. SMPL body, textured neutral GLB, ~45 sec per avatar, $0.01-ish at cost. Always runs, always free, used for measurements.
- **Realistic** (new): PERSONA on a new RunPod endpoint `tryonline-persona`. SMPL-X + 3D Gaussian Splats hybrid. ~90 min per avatar on a single RTX A6000 (1h video synthesis + 30 min training). At RunPod serverless A6000 price (~$0.60/h) this is ~$0.90 GPU cost per avatar, before storage and I/O. Premium tier, opt-in.

The user picks at avatar-creation time. **4D-Humans runs in both cases** because it owns measurement extraction (already wired). PERSONA replaces only the visual avatar; measurements, garment fit, and the size recommender stay on the 4D-Humans SMPL path.

Draping survives the upgrade because PERSONA is **mesh-based under the hood** (SMPL-X body + 3DGS as decoration). We drape on the SMPL-X mesh exactly the way we drape on SMPL today; the Gaussians ride along skinned to the body, and we mask the clothing Gaussians inside the garment footprint.

Three hard problems we have to solve, in order:

1. **Clothing baked into Gaussians.** PERSONA does NOT recover an unclothed body. The visible clothing in the input photo gets baked into the 3DGS texture. For try-on we must hide or repaint that region so the new draped garment is what the shopper sees.
2. **Height in real units.** PERSONA outputs in SMPL-X canonical meters. We already isotropically rescale 4D-Humans to CLO's 180 cm. PERSONA goes the other direction: scale the 180 cm CLO drape result back to the shopper's true height (170, 175, 195 cm, etc.) before compositing with the avatar viewer.
3. **Per-subject training time and cost.** 90 min is unacceptable as a foreground UX. Avatar creation becomes async: queue, email-when-ready, dashboard polling. The Anonymous track stays sub-minute and synchronous.

The rest of this doc is the surgical breakdown.

## 1. What's on the planning queue (deprioritized)

From the 2026-05-14 status report. We are putting these behind PERSONA per your instruction:

- Brand dashboard remake (intended for showcase)
- Shopper lobby v0.2 (Fortnite-lobby sketch at `/dashboard/lobby`, open since 2026-05-02)
- General website bug pass
- Pitch deck citation cleanup (closed out 2026-05-14)

None are blocked by PERSONA work; they're paused but resumable.

## 2. Current avatar stack (origin/main)

Path: `avatar-creation/pipelines/`. Pipeline entry: `pipelines/handler.py` → `run_avatar_pipeline.run_pipeline()`.

Six steps, all run inside one RunPod serverless container:

1. **4D-Humans body extraction** — `4D-Humans-clean/demo_yolo.py --img_folder ... --out_folder ...`. Produces `*person0.obj` (SMPL mesh) + `*person0_params.npz` (SMPL betas + body_pose + global_orient).
2. **T-pose mesh** — `smplx.create("smpl", neutral)` + zeroed body_pose. For measurements only.
3. **SMPL-Anthropometry measurements** — `avatar-creation-measurements/measure.MeasureBody("smpl")`, height-normalized to the shopper's input cm. Returns the ~22 dimensions we map to `chest`, `waist`, `hips`, `inseam`, etc.
4. **A-pose mesh** — same SMPL, arms at 45°. This is the visualization mesh.
5. **CLO scale step** — `scale_avatar_for_clo3d.py`: rescale to 180 cm height so the garment OBJs we have in CLO 3D fit without size mismatch.
6. **Skin extraction + texture** — `extract_skin_from_body.py` pulls the dominant skin tone from the input photo, applies it to the avatar UV, exports `avatar_textured.glb`.

Output payload (`files_base64` dict, base64): `avatar_glb`, `skin_texture`, `original_mesh`, `smpl_params`, `tpose_mesh`, `apose_mesh`, `measurements`, `face_crop`, `avatar_texture`.

Endpoint id (production): `tryonline`. Hardware: shared RunPod GPU, ~45 s end-to-end after warm start. The Dockerfile is `avatar-creation/Dockerfile.runpod` (base `runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04`).

**Hard fact for the integration**: our measurement code is SMPL-only (`MeasureBody("smpl")`), while PERSONA is SMPL-X-only. We do NOT migrate measurements to SMPL-X; we keep two parallel body fits. 4D-Humans → SMPL → measurements. PERSONA's preprocess → SMPL-X → avatar.

## 3. PERSONA, surgically

Source: `mks0601/PERSONA_RELEASE` (ICCV 2025, "PERSONA: Personalized Whole-Body 3D Avatar with Pose-Driven Deformations from a Single Image", Sim & Moon). Arxiv 2508.09973.

### 3.1 What it actually is

Verbatim from the paper:

> Representation. We design PERSONA by combining the SMPL-X parametric model with 3D Gaussian Splatting (3DGS). SMPL-X enables whole-body animation, while 3DGS supports texture and geometry modeling along with rendering.

So the avatar is **two layers**:

- a posable SMPL-X mesh (skeleton + LBS),
- a 3DGS cloud rigged to the SMPL-X with diffused skinning weights, plus a triplane-conditioned MLP that predicts per-Gaussian non-rigid deformations from the input pose.

This is the key structural fact for us. The mesh layer is what we drape on. The Gaussian layer is the photoreal skin.

### 3.2 The pipeline (three stages)

PERSONA has three stages, each its own subfolder:

```
preprocess/   stage A. SMPL-X fit + masks + Sapiens depth/normal/seg + MimicMotion training video
avatar/       stage B. train.py / test.py / animation.py per subject
pose_track/   stage C. 3D pose tracking from a driving video (only for animation, not avatar creation)
```

Stage A is the heavy data-prep step. Stage B is the per-subject optimization. Stage C is for animation playback against external video, not relevant to the try-on flow.

### 3.3 Stage A: preprocess

`preprocess/README.md` requires this on-disk layout:

```
$ROOT/data/subjects/$SUBJECT_NAME/
├── captured/images/0.png      (the single input photo)
├── generated_0/               (MimicMotion synthesis batch 0)
├── generated_1/               (MimicMotion synthesis batch 1)
└── test/                      (optional, evaluation only)
```

Three preprocessing scripts:

- `run_captured.py --root_path $ROOT_PATH` — preprocess the single captured image.
- `run_generated.py --root_path $ROOT_PATH` — preprocess the MimicMotion-generated frames.
- `run_test.py --root_path $ROOT_PATH` — for NeuMan/X-Humans eval, NOT needed in production.

Each preprocess pass runs (according to `install.sh` deps): SMPLest-X for SMPL-X parameter fitting, Hand4Whole for refined hand pose, DECA for facial expression, SAM v1 + SAM 2 for foreground masks, Sapiens (Meta) for human-specific pose, depth, normal, and segmentation maps, ResShift for super-resolution upscaling. Output is a directory of per-frame {`image.png`, `mask.png`, `depth.npy`, `normal.npy`, `seg.png`, `smplx_params.npz`} for every synthesized frame + the captured one.

### 3.4 Stage A.5: MimicMotion + SVD (the slow part)

Verbatim from the paper:

> It takes approximately one hour to generate training videos, whereas avatar training itself additionally takes 30 minutes.
> All running times were measured under the same hardware setup using a single RTX A6000.
> since we use enough number of generated frames (approximately 1K) for optimizing PERSONA

What happens: MimicMotion (built on Stable Video Diffusion `stabilityai/stable-video-diffusion-img2vid-xt-1-1`) takes the single input image and two canned motion driver files (`motion_0.zip`, `motion_1.zip`, distributed by the repo, contain dance / rotation / punches / kicks SMPL-X sequences) and synthesizes ~1K frames of the input subject performing those motions from a fixed camera. These frames are what gives PERSONA its pose diversity to learn the deformation MLP.

This is the long tail. The ~1h cost is mostly SVD denoising over 1K frames at ~25fps.

### 3.5 Stage B: per-subject training

From `avatar/main/config.py` (the file we pulled):

```
end_epoch = 5                  # only 5 epochs over ~1K frames
lr = 1e-3
smplx_param_lr = 1e-3
batch_size = 1                 # forced by GS renderer
rgb_loss = 0.8
ssim_loss = 0.2
lpips_loss = 1.0
depth_loss = 0.01
triplane = (32, 128, 128)      # feature dim x H x W
face_patch = 256 x 256
smplx_uv = 1024 x 1024
triplane_extent = 2 x 2 x 2 m
num_workers = 8
num_gpus = 1
```

5 epochs over ~1K frames is ~5K iterations, batch 1, with the 3DGS rasterizer in the loop. 30 min on an A6000 is plausible at this scale.

Pre-trained avatars are provided for a few demo subjects at the [Google Drive](https://drive.google.com/drive/folders/1J0z0HBEYB03r9svgpeLO2AqAvV1YAzRk?usp=sharing) link. We cannot ship those — they're the authors' subjects, not our users — but they're useful for end-to-end pipeline validation without burning the training cost.

### 3.6 Outputs

- Per-subject model checkpoint: `output/model/$SUBJECT_ID/snapshot_X.pth.tar`. The trained triplane + deformation MLP + Gaussian parameters. Size unknown until measured; budget tens of MB minimum, possibly low hundreds.
- Animation: `python animation.py --subject_id ... --test_epoch 4 --motion_path $PATH` renders frames from an SMPL-X motion sequence. Output frames or video file (paper supplementary has MP4 at unspecified fps).
- Neutral pose: `python get_neutral_pose.py --subject_id ... --test_epoch 4` is the canonical query that gives us a static reposable avatar. **This is what we need for try-on** (one neutral A-pose render or splat dump).

### 3.7 Limitations the paper admits

Verbatim:

> Lack of dynamics. Despite its ability to represent pose-driven deformations, PERSONA cannot capture motion-dependent dynamics, which rely on velocity and acceleration. These dynamics are crucial for modeling complex deformations in loose-fitting clothing and hair.

> Blurry rendering for complex patterns in invisible regions. While our method produces plausible geometry and textures for these areas, intricate patterns remain difficult to render sharply due to inconsistencies in the generated frames used to train PERSONA.

Translation for us: PERSONA renders the subject as they were in the input photo, with reasonable pose-driven cloth wrinkles, but it cannot simulate fabric physics, and the back of the head / occluded sides will be soft. Both are acceptable for try-on; we're going to remove the input clothing anyway and let our XPBD drape carry the cloth dynamics.

### 3.8 Third-party dependency matrix

`install.sh` downloads these into `third_modules/`. License compatibility check is mandatory before we ship; the ones flagged here need a manual read.

| # | Module | Purpose in PERSONA | Where downloaded from | License risk |
|---|---|---|---|---|
| 1 | DECA | Facial expression fit | repo release | non-commercial typically — CHECK |
| 2 | Hand4Whole | Hand pose refinement | repo release | non-commercial typically — CHECK |
| 3 | Intrinsic | Image intrinsic decomp | repo release + setup.py install | CHECK |
| 4 | ResShift | Image super-resolution | repo release | MIT-ish, CHECK |
| 5 | mip-splatting | 3DGS renderer | upstream GitHub clone + diff-gaussian-rasterization | Inria license, non-commercial — **HIGH RISK** |
| 6 | MimicMotion + SVD | Training video synthesis | Tencent (MimicMotion 1-1) + Stability AI (SVD-XT-1-1) | SVD is Stability community license; commercial allowed for orgs under $1M revenue (we qualify today, won't at scale) — **MEDIUM RISK** |
| 7 | segment-anything (SAM v1) | Foreground mask | Facebook AI | Apache 2.0, fine |
| 8 | SAM 2 | Foreground mask (better) | Facebook AI | Apache 2.0, fine |
| 9 | Sapiens (1B) | Pose / depth / normal / seg | Meta via Hugging Face | Sapiens license — non-commercial research, **HIGH RISK** |
| 10 | SMPLest-X | SMPL-X regressor | repo release | CHECK |
| 11 | human_model_files | SMPL/SMPL-X/FLAME/MANO assets | gdown 1kk5NyLurez... | Max Planck SMPL license, commercial requires per-application license — **HIGH RISK** |
| 12 | torchgeometry bugfix | Patch | bundled | fine |

The SMPL/SMPL-X family license is the one we already deal with on the 4D-Humans side; the unresolved new ones are **3DGS rasterizer (Inria)**, **Sapiens (Meta non-commercial)**, and **SVD (Stability community)**. If any of these block commercial use, the realistic-avatar tier is research-preview only until we pay for licenses or swap for permissive alternatives (gsplat from gsplat-org under Apache 2.0 can replace mip-splatting's rasterizer; Sapiens can be swapped for SAM2 + DepthAnythingV2 + standard pose, with a quality hit).

Action: **legal pass on these three licenses before we burn engineering time**. Tag for follow-up.

### 3.9 Hardware envelope (production)

- VRAM: A6000 = 48GB. The paper uses one. 4090 = 24GB likely won't fit MimicMotion+SVD at 1K frames in one shot. A100 80GB has plenty of headroom and is widely available on RunPod serverless.
- Disk: ~30-40 GB of model weights baked into the image OR on a Network Volume. We'll Network Volume them, same pattern as `tryonline`.
- Wall time: 90 min cold, plus container start. Make it 100 min budget.
- Concurrency: 1 GPU per job. If we want 10 simultaneous avatars we pay for 10 GPUs concurrently.

## 4. Integration architecture

### 4.1 The fork

Both tracks share an entry point on the backend, which decides which RunPod endpoint to call.

```
POST /api/avatars/create
  body: { photo_url, height_cm, weight_kg, gender, mode }
  mode ∈ { "anonymous", "realistic" }

  if mode == "anonymous":
    enqueue → RunPod tryonline                        (sync, 45 s)
    return GLB + measurements                          (existing flow)

  if mode == "realistic":
    job_a = enqueue → RunPod tryonline                 (async, 45 s, for measurements)
    job_b = enqueue → RunPod tryonline-persona         (async, 90 min, for visual avatar)
    return { job_id, status: "processing", eta_min: 95 }
    poll → on both jobs complete, write to avatar table
    notify user (email + dashboard badge)
```

Why both jobs even for realistic: we want measurements immediately (so size recommendation works in the dashboard while the visual avatar trains). 4D-Humans is the source of truth for measurements; nothing in PERSONA's pipeline gives us the height-normalized SMPL-Anthropometry numbers we already plumb through to size recommendation.

### 4.2 What lives on `tryonline-persona`

New RunPod serverless endpoint, A6000 minimum (A100 if available), Network Volume of ~40 GB for weights.

```
avatar-creation-persona/                              ← new top-level dir
├── Dockerfile.runpod                                 (base: runpod/pytorch:2.4.0-py3.10-cuda12.1-devel)
├── handler.py                                        (RunPod entry, same lazy-import pattern as drape handler)
├── pipeline/
│   ├── stage_a_preprocess.py                         (wraps PERSONA's preprocess/run_captured.py)
│   ├── stage_a_mimicmotion.py                        (wraps the SVD synthesis)
│   ├── stage_b_train.py                              (wraps PERSONA's avatar/main/train.py)
│   ├── stage_c_export.py                             (neutral-pose render + splat .ply + SMPL-X body OBJ)
│   ├── garment_removal.py                            (clothing inpaint — see §5)
│   └── height_scale.py                               (rescale to user height — see §6)
├── PERSONA_RELEASE/                                  (git submodule, the upstream repo verbatim)
└── third_modules/                                    (pre-downloaded into the image during build)
```

Handler input mirrors `tryonline`:

```
{ photo_url, height_cm, gender, user_id, garment_removal: bool }
```

Handler output (all on Supabase storage URLs, NOT base64 — PERSONA artifacts exceed the 20MB RunPod cap):

```
{
  smplx_params_url:   "...smplx_params.npz",
  body_apose_obj_url: "...body_apose.obj",         (the mesh we drape on)
  splat_ply_url:      "...avatar.ply",             (the 3DGS cloud, scaled to height_cm)
  textured_glb_url:   "...avatar_textured.glb",    (fallback mesh-only render for Three.js)
  preview_png_url:    "...preview.png",            (single neutral-pose render for dashboard)
  measurements:       { ... }                       (forwarded from tryonline; this endpoint is body-only)
}
```

Reason for the URL pattern: `draped-artifacts` bucket already proved we can't ship large artifacts inline (memory: RunPod ~20 MB cap → status COMPLETED, output null). A 1K-frame splat .ply is easily 100-500 MB. Use Supabase storage from the start.

### 4.3 New Supabase storage layout

```
avatars/
  {user_id}/
    anonymous/
      avatar_textured.glb            (4D-Humans output, unchanged)
      body_apose.obj                 (drape input)
      smpl_params.npz
      measurements.json
    realistic/
      avatar.ply                     (3DGS cloud)
      avatar_textured.glb            (mesh fallback)
      body_apose.obj                 (drape input — same SMPL-X surface)
      smplx_params.npz
      preview.png
      measurements.json              (copy of anonymous for convenience)
```

User can have both. The active track is a column on `avatars` row: `active_track: "anonymous" | "realistic"`.

### 4.4 New table

```
avatar_jobs (
  id            uuid pk,
  user_id       uuid fk users,
  track         text check (track in ('anonymous','realistic')),
  status        text check (status in ('queued','preprocess','training','postprocess','complete','failed')),
  runpod_job_id text,
  eta_seconds   int,
  started_at    timestamptz,
  finished_at   timestamptz,
  error         text,
  created_at    timestamptz default now()
)
```

RLS: user can read own rows; service role can write.

Dashboard polls this. Frontend shows "Your realistic avatar is being created. ETA ~90 minutes. We'll email you when it's ready."

## 5. Clothing removal (the hardest problem)

PERSONA bakes the clothing in the input photo into the Gaussian cloud. The paper does not address this. For try-on we cannot show the new draped garment over the old garment.

Three options, ordered by quality and cost:

### Option A: pre-PERSONA undressing (clean but expensive)

Before sending the photo to PERSONA, run a clothing-removal diffusion pass:

- Segment garments with Sapiens-seg (we get this free, it's in the pipeline) or DensePose-based body part seg.
- Inpaint the garment region with a person-aware diffusion model that produces a naked-body equivalent. Candidates:
  - Stable Diffusion + body-aware ControlNet conditioned on DensePose, prompt = "person in skin-tone underwear, full body, neutral lighting".
  - OOTDiffusion in reverse mode (it's a virtual try-on model — running it with a "blank" garment produces a near-naked render).
  - CatVTON or IDM-VTON in undress mode.

Result: a single image of the same person without clothing (modesty layer: tight underwear). Feed THAT to PERSONA.

Pro: PERSONA learns the actual body underneath. Garments drape on a true skin surface. Maximum realism.

Con: extra ~30 s of diffusion before the 90 min PERSONA pass. Diffusion quality varies wildly by body type (loose clothing or full coverage = the inpainter has to invent a lot, and the invented anatomy may not match reality). Also: legal/PR risk of producing near-nude renders of users. Mitigations: server-side only, never returned to client, log retention zero, opt-in language explicit.

### Option B: post-PERSONA masking (cheap, hacky)

Train PERSONA as-is with clothing baked in. At try-on render time:

- Use the SMPL-X UV map + garment region rasterization to identify which Gaussians fall inside the garment footprint of the new draped garment.
- Suppress those Gaussians at render time (alpha = 0) and let the draped garment's render fill the gap.

Pro: zero training cost, no diffusion legal risk.

Con: the head/hands/legs that show *around* the new garment are still showing the OLD garment in those edge regions (think: original was a long-sleeve, new garment is short-sleeve — the forearms in the avatar are still wearing the old sleeve fabric, not skin). Acceptable only when the new garment fully covers the old. Fragile.

### Option C: hybrid — diffuse only the visible-edge region (recommended path)

Train PERSONA as in B. At render time:

- Compute the symmetric difference between OLD garment seg (from Sapiens-seg run on the input) and NEW draped garment footprint.
- Only inpaint Gaussians in that symmetric difference, using a small diffusion pass to repaint them as skin.
- Cache the inpainted Gaussians per garment.

Pro: realistic, no nudity rendered ever (because the only inpainted region is where the new garment is smaller than the old).

Con: more engineering. Cache invalidation on every new garment.

**Recommended**: start with Option B for the prototype (cheapest, ships fastest), then upgrade to Option C once we have one happy customer wearing PERSONA + a real garment. Avoid Option A unless the legal review on undressing diffusion clears unambiguously.

## 6. Height normalization

We have to land the PERSONA avatar at the shopper's true height (e.g., 195 cm) AND keep the garment drape (which was simulated at CLO's 180 cm body) fitting correctly. Two coupled scaling problems.

### 6.1 PERSONA avatar scaling

PERSONA outputs in SMPL-X canonical metres. The character's height depends on the SMPL-X betas the fit produced. The actual height of the rendered avatar can be measured from the body mesh (top-of-head Y minus bottom-of-foot Y in metres) — call this `h_persona`. The desired height is `h_user` (the cm value the shopper typed).

Isotropic scale factor `s = h_user / h_persona`. Apply to:

- Body mesh vertices (`body_apose.obj`): straightforward, multiply by `s`.
- Gaussian cloud: every Gaussian has position, scale, rotation. Multiply position by `s`, scales by `s`, rotations unchanged.
- Camera + render setup: nothing to do, scene-space.

The 4D-Humans pipeline already does this implicitly via the CLO scale step (180 cm). For PERSONA we go straight to the user's height, not to 180.

### 6.2 Garment drape on a non-180-cm body

Today every garment in the catalogue is draped on a 180 cm SMPL body in CLO. That's why `scale_avatar_for_clo3d.py` exists — it forces the avatar to 180 so the drape geometry fits.

For PERSONA we want the avatar at the user's true height. So we have two sub-options:

- **(i) Re-drape per user**: re-run the cloth simulator (NvidiaWarp+PyGarment, the `tryonline-drape` endpoint) with the body input set to the user-height SMPL-X mesh, not the 180 cm canonical. This is the correct answer. We already have the draping endpoint. The body input becomes `body_apose.obj` at `h_user` cm. Cache key becomes `(body_hash, garment_id, size, height_cm)` instead of `(body_hash, garment_id, size)`.
- **(ii) Post-hoc rescale**: drape at 180 cm as today, then isotropically rescale the resulting garment mesh by `s = h_user / 180`. Fast, no extra GPU. Acceptable for visualization, but it slightly distorts the fit because cloth doesn't scale linearly (a 195 cm body has wider shoulders proportionally, but the rescaled garment doesn't account for that). For try-on confidence this is the wrong answer.

**Recommended**: (i) — re-drape per body. Cost: one extra `tryonline-drape` job per (user, garment) pair, which already runs in 15-30 s on RTX 4000 and is cached. The cache invalidation is once per avatar, and the per-garment cache fills on first try-on per user.

This means the `draped_meshes` table cache key changes:

```
old: (body_hash, garment_id, size)
new: (body_hash, garment_id, size, height_cm_quantized_to_5cm)
```

Quantizing to 5 cm buckets keeps the cache hit rate high without distorting fit perception. Migration: add the column, default to 180 for old rows, recompute on first hit.

## 7. The user flow

### 7.1 Onboarding screen (avatar creation)

```
┌─────────────────────────────────────────────────────────────┐
│  Choose your avatar style                                    │
│                                                              │
│  ◯ Anonymous                                                 │
│    A neutral 3D body in your exact measurements.             │
│    Ready in ~1 minute. Free.                                 │
│                                                              │
│  ◯ Realistic     [Premium]                                   │
│    A photoreal 3D twin of you, learned from your photo.      │
│    Ready in ~90 minutes — we'll email you when it's done.    │
│    Best for trying on what you'll actually look like.        │
│    [included in Studio plan]                                 │
│                                                              │
│  [Continue]                                                  │
└─────────────────────────────────────────────────────────────┘
```

Copy notes:
- No em-dashes (use periods, commas, colons, parentheses).
- Don't oversell. "Best for trying on what you'll actually look like" is the honest pitch.
- The 90-min wait is a feature framing, not a bug: "we're growing your digital twin, this takes care".

### 7.2 During training

Dashboard card:

```
[Avatar creating — 47% complete]
[Stage: synthesizing motion video]
ETA: 53 minutes. We'll email you.
```

Stages we surface: `preprocess (5%)`, `training video (10-65%)`, `avatar training (65-95%)`, `final render (95-100%)`. We poll `avatar_jobs` every 30 s.

### 7.3 When it's done

Email + dashboard badge. The badge opens the avatar viewer with the realistic version active. Anonymous version is still available via a track-toggle on the avatar page.

## 8. Try-on rendering with splats

Three.js does not render Gaussian splats natively. Options:

- **mkkellogg/GaussianSplats3D** — Apache-2.0, the de facto three.js splat viewer. Active, supports `.ply` and `.splat` formats. Recommended.
- **antimatter15/splat** — WebGL splat renderer, simpler API, less polished UX.
- **Bundle a custom WebGPU rasterizer** — overkill for now.

Plan: add `GaussianSplats3D` as a dependency in `frontend/`, wrap it in a `<PersonaAvatarViewer>` component analogous to `TryOnViewer`. Same camera controls, same lighting. Render order: splat avatar first, then draped garment GLB on top with depth test enabled. The Gaussian rasterizer writes to the depth buffer correctly for this composition (verify on integration day; if it doesn't, fallback to a depth-pre-pass on the mesh).

Performance budget: 100K-300K Gaussians is fine at 60fps on modern laptops. PERSONA Gaussian counts aren't published; budget 200K and verify.

Fallback: every PERSONA job also exports a **textured mesh GLB** baked from the splats (project Gaussians onto the SMPL-X UV map, average colors per UV pixel, write `avatar_textured.glb`). Lower quality but renders in any browser; we serve it on devices where the splat viewer is too slow.

## 9. Risks and open questions

| # | Risk | Mitigation |
|---|---|---|
| R1 | License blockers on Sapiens / mip-splatting / SVD | Legal pass before engineering. Plan B: swap Sapiens for SAM2+DepthAnythingV2, swap mip-splatting for gsplat (Apache 2.0), swap SVD for Wan2.2-img2vid (Apache 2.0) at quality cost. |
| R2 | 90 min/avatar GPU cost makes the unit economics ugly | Price the realistic tier into Studio plan ($149/mo). At ~$0.90 GPU/avatar with one avatar per user the gross margin holds. Mass adoption means amortize via batched MimicMotion (multi-subject SVD). |
| R3 | Clothing removal (§5) produces uncanny results | Option B (post-render mask) ships first and is honest about limitations. Diffusion-based undressing (Option A) only if legal and quality both green. |
| R4 | PERSONA output quality varies on full-body photos taken in poor lighting | Onboarding photo guidelines: front-facing, full body in frame, A-pose preferred, even lighting. Reject photos failing a pre-check (Sapiens-pose confidence < threshold). |
| R5 | Drape on user-height (not 180) breaks any garment that was tuned for 180-only | Cache key bump (§6.2). For the first 5 SKUs verify drape quality at 160/170/180/195 cm before opening the feature beyond pilot users. |
| R6 | RunPod serverless container start on a 40GB-weight image is slow (cold start 60-120 s) | Network Volume for weights, slim image. Mirror the `tryonline` pattern. Acceptable in async flow. |
| R7 | Per-subject checkpoint size makes Supabase storage bills add up | Store full checkpoint short-term, drop to splat .ply + body OBJ + smplx_params long-term (we can re-train if needed but we'd need to re-store the 1K frames too — accept that re-train = re-photo). |
| R8 | User uploads a photo where they're wearing a coat / oversized clothing | PERSONA learns the coat shape as the body. Option A undressing needed for these, OR reject at onboarding ("please upload a photo in form-fitting clothes"). |
| R9 | The MimicMotion-driven training video may not match the user's actual body proportions, causing PERSONA to learn the wrong shape | The paper handles this via SMPL-X-conditioned generation. Verify on our subjects in stage 1; if poor, condition on our measurements. |

Open questions to answer in stage 1 of the build:

- Q1: What's the actual Gaussian count produced by PERSONA on a typical subject? Drives the splat viewer perf budget and Supabase storage estimate.
- Q2: Can we feed our 4D-Humans SMPL-X fit into PERSONA preprocess and skip SMPLest-X? (4D-Humans produces SMPL, not SMPL-X, but its body pose + betas could initialize an SMPL-X fit. May save some preprocess time.)
- Q3: Does MimicMotion + SVD support a smaller frame count (256 instead of 1K) at acceptable quality? Halving frames would halve the slow stage.
- Q4: Does the diffused skinning weights step (`tools/diffused_skinning_weights`) run per-subject or once? If per-subject, that's another minutes-long step we need to account for.
- Q5: Do we want to expose `animation.py` to users (full body motion playback against a stock motion library)? Probably yes as a "see yourself walk" novelty feature.

## 10. Phased implementation roadmap

Phasing is staged so we can kill the project at any phase boundary if a hard problem (license, quality, cost) breaks it.

### Phase 0 — Validation (1-3 days, no infra spend)

Goal: run PERSONA end-to-end on a single test subject locally or on a one-shot RunPod pod (not serverless). Confirm it produces a usable avatar from one of OUR test photos (Ramin Studios pilot user or self-portrait).

- Provision a 1-hour RunPod pod with A6000.
- Clone repo, run `install.sh`, run preprocess + train on one subject.
- Inspect output: splat .ply, render quality, check Gaussian count, check checkpoint size, time each stage.
- Gate: if quality on our photo is good and total time ≤ 2h, proceed. If not, kill or rework.

### Phase 1 — Endpoint (1-2 weeks)

Goal: `tryonline-persona` RunPod serverless endpoint live, returning Supabase URLs.

- New branch `feature/persona` off `main`.
- Build `avatar-creation-persona/` (Dockerfile, handler, pipeline stages, Network Volume).
- Wire to a new Supabase storage bucket `persona-avatars` (RLS: user_id path scoping).
- One-shot test from CLI against the live endpoint with a known photo.
- Gate: endpoint reliably produces an avatar inside 100 min wall time, returns valid URLs.

### Phase 2 — Backend (3-5 days)

Goal: `POST /api/avatars/create` with `mode`, `avatar_jobs` table, polling, fan-out to both endpoints when `mode=realistic`.

- Migration for `avatar_jobs` + `active_track` column on `avatars`.
- FastAPI route + Pydantic models.
- Background task: poll RunPod, write to Supabase on completion, send email via existing transactional provider.
- Gate: anonymous job and realistic job both complete cleanly from the API.

### Phase 3 — Frontend onboarding (3-5 days)

Goal: user picks Anonymous or Realistic in onboarding, sees ETA card, gets email + dashboard badge.

- Update onboarding flow: new selector screen (§7.1 copy).
- Dashboard card: ETA progress + stage label.
- Email template with "Your realistic avatar is ready" + deep link.
- Gate: real user (you) can pick realistic and land on a working avatar 90 min later.

### Phase 4 — Splat viewer (3-5 days)

Goal: `<PersonaAvatarViewer>` component renders the .ply, draped garment composites on top.

- Add `@mkkellogg/gaussian-splats-3d` to frontend deps.
- New component mirroring `TryOnViewer` API.
- Verify draped garment + splat depth interaction. Fallback to mesh GLB if perf bad.
- Gate: indistinguishable UX from anonymous viewer except the avatar is photoreal.

### Phase 5 — Garment removal (1-2 weeks)

Goal: option B (post-render masking) implemented in the viewer; new garment hides old garment Gaussians in the overlapping footprint.

- Compute garment footprint mask from draped GLB UV → SMPL-X surface point set.
- At splat load time, tag Gaussians inside the footprint, render with `alpha=0`.
- Edge cleanup: smooth alpha falloff at the mask boundary to avoid hard cutoffs.
- Gate: try-on on a tighter new garment over a looser old garment looks clean (no old-garment fabric showing).

### Phase 6 — Height + drape re-cache (1 week)

Goal: drape cache keyed on user height; PERSONA avatar rendered at true height; garments drape on the user-height SMPL-X body.

- Bump cache key on `draped_meshes` (§6.2).
- `height_scale.py` in the persona handler.
- Backfill drape cache lazily on first try-on per (user, garment).
- Gate: a 195 cm user and a 160 cm user wearing the same garment both look correct.

### Phase 7 — Pilot rollout (ongoing)

Goal: invite the Ramin Studios pilot user to opt into a realistic avatar. Measure: time, cost, conversion lift vs anonymous-only baseline. Iterate.

## 11. What we are NOT doing in this phase

Calling these out so we don't scope-creep:

- **Animation playback / dance-yourself** as a user-facing feature. PERSONA supports it via `animation.py`. Park it. Try-on first.
- **Multi-view photo input**. Single image is the brand promise. Multi-view PERSONA exists in spirit but the released code is single-image; don't drift.
- **Real-time fabric physics** on the splat avatar. PERSONA's own paper admits no velocity dynamics. We have the XPBD drape for the garment; the avatar body stays static-per-pose.
- **Migrating measurements to SMPL-X**. Keep 4D-Humans SMPL on the measurement path. Stable and validated.
- **Killing the anonymous track**. It's the always-free fallback and the measurement source. It survives.

## 12. Where this leaves us today (2026-05-16)

- Pre-PERSONA queue (brand dashboard, shopper lobby v0.2, website bugs) is paused.
- Next concrete action: **Phase 0 validation**. Spin up a $0.60/hr A6000 pod, clone PERSONA, run it on one of our test photos, document Gaussian count + checkpoint size + actual wall time on our subject.
- Before Phase 1 spend: legal pass on Sapiens + mip-splatting + SVD licenses. This is the single hardest "could kill the project" gate.
- Open the `feature/persona` branch when Phase 0 clears.

End of framework.
