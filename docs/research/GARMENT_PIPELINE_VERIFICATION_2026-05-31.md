# Garment Construction Pipeline — Roadmap Verification (2026-05-31)

Verification of `TRYON_ROADMAP.md` (Claude-on-Chrome draft) against PRIMARY
sources (GitHub repos, arXiv, HF model cards), before any RunPod build.

**Scope locked by Revan:** photo -> 2D pattern -> 3D garment OBJ (textured).
Draping onto the user avatar STAYS on our existing system. So only roadmap
Stages 1-5 matter; Stages 6-7 (avatar gen, user draping, browser) are OUT.

---

## Verdicts per component

### Stage 1 — ChatGarment (pattern extraction) — REAL, with corrections
- Repo real: `github.com/biansy000/ChatGarment`, **Apache-2.0**, CVPR 2025
  (Bian et al., MPI/SJTU/EPFL). arXiv 2412.17811.
- **Input is a SINGLE worn-garment photo** (and/or text), trained on
  clothed-human images, NOT flat-lays, NOT "3-5 photos fed together." The
  roadmap's multi-photo-into-Stage-1 assumption is wrong.
- **Output is a GarmentCodeRC parametric JSON program** (76 floats + categorical
  garment types), NOT raw 2D polygon panel vertices. The roadmap's "unified
  polygon schema" intermediate does not match reality.
- Weights = a LoRA on **LLaVA-1.5-7B**, distributed via a **SharePoint link**
  (NOT a HF model repo; the HF `sy000/ChatGarmentDataset` is data only). Needs
  base LLaVA-1.5-7B + CLIP-L/14-336 + **SMPL-X (non-commercial, gated)**.
- The real entry script `scripts/v1_5/evaluate_garment_v2_imggen_2step.sh`
  DOES exist (2-step chain-of-thought), wired through deepspeed/cluster paths
  that must be stripped for serverless.
- Designed to feed its own forks: **GarmentCodeRC** (JSON -> 3D decode) +
  **ContourCraft-CG** (drape sim). Hard dependency.
- RunPod: feasible on one 24-48 GB GPU after removing the deepspeed wrapper.

### Stage 3 — GarmentCode + simulator — REAL, but NC sim + wrong CLI
- `github.com/maria-korosteleva/GarmentCode`, **MIT**, ETH IGL. Pattern DSL
  (SIGGRAPH Asia 2023) PLUS the GarmentCodeData draping pipeline folded in
  (ECCV 2024). The 2023 DSL alone does not drape.
- **The real simulator is NOT stock NVIDIA Warp.** It is a private fork
  `maria-korosteleva/NvidiaWarp-GarmentCode` (XPBD on Warp v1.0.0-beta.6),
  licensed **NVSCL = NON-COMMERCIAL ONLY**. Stock `warp-lang` (Apache-2.0)
  lacks the collision/XPBD changes the drape needs.
- **Runs headless on Linux + CUDA GPU** (no Maya on the Warp path; Maya/Qualoth
  is legacy code only). RunPod-deployable, but you must compile the Warp fork in
  the Docker image (CUDA-extension build hurdle).
- `pattern_data_sim.py` exists but is a **batch/dataset** tool with
  `--data <dataset> --config <yaml> [--default_body]` — the roadmap's
  `--design/--body/--output` flags are fabricated.
- Output = OBJ **with UVs + textures**, draped on a bundled SMPL body OBJ.
- Per-garment sim time undocumented — must benchmark.

### Stage 4 — DressCode (texture) — HALLUCINATED. Do not use as described.
- `github.com/IHe-KaiI/DressCode` is a **text -> sewing-pattern + text -> PBR**
  generator (SIGGRAPH 2024, SewingGPT + tuned SD). **No photo input**, **no
  `nn/generate_texture.py`**, **no LICENSE file**. Every load-bearing clause in
  the roadmap's Stage 4 is wrong (the `generate_texture.py` name was likely
  borrowed from the unrelated **Text2Tex** repo).
- Right tools for "merchant photo -> textured garment OBJ" (needs the merchant's
  ACTUAL fabric/print/logo, not a hallucination):
  - **PRIMARY: deterministic UV reprojection** (camera-fit + rasterize + sample
    the photo per UV texel + seam-fill). Pixel-exact, no ML, sub-second,
    permissive deps, trivially headless. Best when the photo is a flat-ish
    front/back product shot.
  - **HARD-CASE LIFT: FabricDiffusion** (`humansensinglab/fabric-diffusion`,
    SIGGRAPH Asia 2024, CMU+Google, **X11 ~= MIT, commercial-OK**, HF weights).
    Purpose-built: normalizes a real clothing photo into a tileable
    distortion-free texture + extracts prints/logos + emits PBR. Single-GPU,
    headless.
  - Avoid: TEXTure (per-garment fine-tune), Text2Tex (text-only + NC),
    SyncMVD (text-only), Paint3D (IP-Adapter = style not exact logo).

### Stage 1 fallbacks
- **SewFormer** (`sail-sg/sewformer`): REAL, HF checkpoint `liulj/sewformer`,
  SIGGRAPH Asia 2023, single worn photo -> NeuralTailor-style panels (needs a
  format adapter to GarmentCode). BUT **no LICENSE file** (all-rights-reserved
  by default). Runs single-GPU. Viable fallback once license cleared.
- **Panelformer** (`ericsujw/Panelformer`): paper real (WACV 2024) but the repo
  is an **empty 2-file stub — no code, no weights**. NOT usable. Drop it.

---

## Net architectural corrections vs the roadmap

1. **No custom "unified polygon JSON" intermediate.** ChatGarment emits
   GarmentCodeRC JSON that GarmentCodeRC consumes directly. Simpler + correct.
2. **Two candidate construction (sim) backends**, both downstream of ChatGarment:
   - (A) ChatGarment's native **GarmentCodeRC + ContourCraft-CG** — least
     integration friction (ChatGarment outputs exactly what it wants).
   - (B) Vanilla **GarmentCode + NvidiaWarp-GarmentCode fork** — needs a JSON
     adapter and is non-commercial.
   Recommend (A) for first build; check ContourCraft-CG license separately.
3. **Single photo drives the pattern.** Pick the best garment photo for
   ChatGarment; use the other photos for texture. The merchant can still upload
   3-5; we route them by role.
4. **License reality (pre-seed posture: NC OK during validation, must flag):**
   SMPL-X (NC), the Warp fork (NC), SewFormer (no license), ChatGarment code
   (Apache but pulls LLaMA-2 terms). The construction stack is NOT commercially
   clean yet. Acceptable to validate now, must be cleared before paid use.
5. **The roadmap's shell commands/flags are mostly fabricated** — treat the
   roadmap as a stack-selection guide, rebuild implementation from real repos.

## Proposed construction flow (to confirm)
```
merchant photos
  -> pick best garment photo
  -> ChatGarment (single img) -> GarmentCodeRC parametric JSON
  -> GarmentCodeRC decode + drape on neutral body  ->  garment OBJ + UV
  -> texture: UV reprojection from photos (FabricDiffusion for hard cases)
  -> textured garment OBJ  ==> HANDED TO EXISTING DRAPE SYSTEM (unchanged)
(bonus) GarmentCodeRC JSON -> SVG panels for merchant download
```
Deploy as a single RunPod serverless endpoint (photo in -> textured OBJ URL out),
weights runtime-downloaded (LLaVA LoRA from our mirror, SMPL-X, FabricDiffusion).
