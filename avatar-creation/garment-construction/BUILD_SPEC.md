# Garment Construction — RunPod Serverless Build Spec

Photo → 3D garment OBJ (with UVs + texture), handed to the EXISTING drape system.
All commands below are VERIFIED against the real repos (2026-05-31). See
`docs/research/GARMENT_PIPELINE_VERIFICATION_2026-05-31.md` for the audit.

## Stack (verified)

| Step | Repo | License | Role |
|---|---|---|---|
| 1. Photo → pattern JSON | `biansy000/ChatGarment` | Apache-2.0 | LLaVA-1.5-7B, 2-step CoT, single photo |
| 2. JSON → 3D garment OBJ+UV | `biansy000/GarmentCodeRC` | MIT | builds panels, writes UVs, drapes on neutral body |
| (sim engine inside step 2) | `maria-korosteleva/NvidiaWarp-GarmentCode` | **NVSCL non-commercial** | XPBD cloth drape — PROTOTYPE ONLY, replace for commercial (use our Newton) |
| 3. Texture extraction | our code | ours | fabric color/logo from photos → texture.png + .mtl on the UV layout |
| (not used) | `biansy000/ContourCraft-CG` | MIT (but pulls NC CCCollisions) | neural re-sim over motion — NOT needed for our deliverable |

Final drape onto user avatar = our EXISTING system, unchanged.

## Verified end-to-end command chain (inside container)

```bash
# one-time setup (baked or symlinked in image):
#   checkpoints/try_7b_lr1e_4_v3_garmentcontrol_4h100_v4_final/pytorch_model.bin   (~14-15GB, mirror off SharePoint)
#   ln -s <GarmentCodeRC>/assets assets

# STEP 1: photo folder -> GarmentCode JSON specs
./scripts/v1_5/evaluate_garment_v2_imggen_2step.sh <image_folder>
#   internally: deepspeed scripts/evaluate_garment_v2_imggen_1float.py \
#     --lora_enable True --lora_r 128 --lora_alpha 256 \
#     --model_name_or_path liuhaotian/llava-v1.5-7b --version v1 \
#     --data_path_eval <image_folder> \
#     --vision_tower openai/clip-vit-large-patch14-336 \
#     --mm_projector_type mlp2x_gelu --image_aspect_ratio pad --bf16 True \
#     --model_max_length 3072 ...
#   OUTPUT: runs/<exp>/<dataset>_img_recon/vis_new/all_json_spec_files.json
#           (+ per-garment valid_garment_<id>/output.txt)

# STEP 2: JSON -> draped 3D garment OBJ with UVs
python run_garmentcode_sim.py --all_paths_json runs/<exp>/<dataset>_img_recon
#   internally: BoxMesh(spec).serialize(uv_config=...)  -> writes UVs
#               run_sim(...) NVIDIA-Warp XPBD drape on body_name='mean_all'
#   OUTPUT: runs/<...>/valid_garment_<id>/<garment>_sim.obj   <-- THE 3D GARMENT
```

## Weights to handle at runtime (~31 GB total, do NOT bake big ones)

| Asset | Size | Source | Strategy |
|---|---|---|---|
| LLaVA-1.5-7B base | ~14 GB | HF `liuhaotian/llava-v1.5-7b` | runtime download (cached vol) |
| CLIP-L/14-336 | ~1.7 GB | HF `openai/clip-vit-large-patch14-336` | runtime download |
| ChatGarment checkpoint | ~14-15 GB | **SharePoint (auth)** → mirror to OUR bucket | **USER must download once; I re-host** |
| SMPL-X | ~1 GB | smpl-x.is.tue.mpg.de (gated, NC) | runtime download from our mirror |
| GarmentCodeRC assets | small | repo | bake |

DO NOT fetch ChatGarmentDataset (389 GB training data, not needed).

## Build pins (verified from ccraft.yml / installation docs)
- Python 3.10.16, PyTorch 2.5.1, torchvision 0.20.1, CUDA 12.4 (nvcc 12.4.131)
- CUDA extensions needing nvcc at build (set `TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0"` + `FORCE_CUDA=1`):
  - pytorch3d (git stable), flash-attn (`--no-build-isolation`),
    NvidiaWarp-GarmentCode (`python build_lib.py` then `pip install -e .`)
  - pyg stack via wheels: `data.pyg.org/whl/torch-2.5.0+cu124.html`
- deepspeed required even for inference (launch script uses it)
- system libs: libgl1 / EGL (pyrender, aitviewer offscreen)

## Hardcoded paths to PATCH (authors left MPI-cluster paths)
- ChatGarment `scripts/v1_5/*.sh`: `/is/software/nvidia/cuda-12.1/...`, `EGL_DEVICE_ID`
- ChatGarment checkpoint path is SharePoint-only → repoint to our mirror
- GarmentCodeRC: `system.json` path config → set to container paths
- (ContourCraft-CG `/is/cluster/fast/sbian/...`, `/ps/scratch/...` — only if we ever add it)

## GPU tier
48 GB (L40S / A6000) recommended. 24 GB works if stages run sequentially and the
LLM is freed before the sim, but tight with flash-attn + 2048-token decode.

## Output contract (must match EXISTING drape system — verified from handler.py)
Produce per garment+size, in the Supabase garments bucket:
```
garments/{garment_id}/{size}/
  {size}.obj      meters or mm, Y-up, ~1.8m scale, v/vt faces (UVs required),
                  CLO-style seam-split verts OK (handler welds at 1mm),
                  mtllib line must match the .mtl filename
  {size}.mtl      newmtl + Kd + map_Kd <basename-only> (no absolute paths)
  <texture>.png   one per map_Kd, <10MB, same folder
```
The drape handler takes `garment_obj_url` (+ optional `garment_glb_url`) and does
the rest. No changes to the drape system.

## Phases
- A. Base image (GPU pod): compile CUDA exts, push to registry. Once.
- B. Mirror ChatGarment checkpoint off SharePoint (needs USER).
- C. Serverless handler.py: run chain + texture extract + emit contract bundle + patch paths.
- D. Deploy + test one real garment end-to-end.

## Hardcoded paths to PATCH (VERIFIED from real source 2026-05-31)

Reference copies saved: `REFERENCE_run_garmentcode_sim.py`, `REFERENCE_eval_2step.sh`.

**run_garmentcode_sim.py (STEP 2):**
- line 8: `sys.path.insert(1, '/is/cluster/fast/sbian/github/GarmentCodeV2/')`
  → `/workspace/GarmentCodeRC`
- line 32: `system_path='/is/cluster/fast/sbian/github/GarmentCodeV2/system.json'`
  → `/workspace/GarmentCodeRC/system.json` (we generate this, like the drape image does)
- body: `body_name='mean_all', smpl_body=False` → needs `assets/bodies/mean_all*`
  (ships in GarmentCodeRC repo; reachable via the `assets` symlink)
- sim config (relative): `assets/Sim_props/default_sim_props.yaml`
- input read: `{all_paths_json}/vis_new/all_json_spec_files.json`
- output: draped OBJ written to `os.path.dirname(json_spec_file)` per garment

**evaluate_garment_v2_imggen_2step.sh (STEP 1):**
- `LD_LIBRARY_PATH/PATH/CUDA_HOME/CPATH=/is/software/nvidia/cuda-12.1/...`
  + cudnn paths → `/usr/local/cuda` (our base image)
- `EGL_DEVICE_ID=$GPU_DEVICE_ORDINAL` → set to 0 (single-GPU serverless)
- invokes `deepspeed scripts/evaluate_garment_v2_imggen_1float.py`
- positional `$1` = image folder; checkpoint dir name = the exp folder under runs/
- HANDLER STRATEGY: don't shell out to the .sh; replicate its python call directly
  with our patched env, so we control paths + output dir cleanly.

**Assets already owned (skip re-download):**
- `draping/pygarment_assets/{default_sim_props.yaml, smpl_vert_segmentation.json}`
- SMPL-X .pkl present in conda envs (4D-humans / avatar_pipeline) — locate at build.

## License posture
Prototype accepts NC (Warp fork, SMPL-X) per pre-seed posture. MUST replace the
Warp drape with our own Newton solver (or stock Apache Warp) before any paid use.
Tracked alongside DECA/Multi-HMR.
