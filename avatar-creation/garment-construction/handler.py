"""
RunPod Serverless Handler — Garment Construction Service
========================================================

Photo(s) of a garment  ->  3D garment OBJ (with UVs + texture)  ready to hand to
the EXISTING cloth-draping service (avatar-creation/draping). This service does
NOT drape onto the user avatar; it CONSTRUCTS the garment asset that the drape
service later fits to the avatar (the "CLO3D export" equivalent, automated).

Pipeline (verified against ChatGarment + GarmentCodeRC source, 2026-05-31):

  STEP 1  photo -> GarmentCodeRC parametric JSON
          ChatGarment (LLaVA-1.5-7B, 2-step CoT).
          Replicated in-process from scripts/evaluate_garment_v2_imggen_1float.py
          (we do NOT shell out to the .sh, whose cluster env we cannot honour).

  STEP 2  JSON -> draped 3D garment OBJ + UVs
          run_garmentcode_sim.py: BoxMesh -> serialize(uv) -> run_sim
          (NvidiaWarp-GarmentCode XPBD drape on the bundled `mean_all` body).

  STEP 3  texture extraction (our code)
          pull fabric colour + logo from the source photos onto the UV layout,
          write {size}.mtl + texture PNG.

  OUTPUT  the file bundle the drape handler already accepts:
            {size}.obj  (UVs, mtllib line), {size}.mtl (basename map_Kd),
            <texture>.png ; uploaded to the garments bucket; URLs returned.

Expected input event:
{
  "input": {
    "image_urls":  ["https://...front.jpg", "https://...back.jpg"],
    "garment_id":  "uuid",
    "size":        "m",
    "garment_type_hint": "hoodie",   # optional, helps STEP-2 sim preset
    "upload":      true               # optional; if false, return base64
  }
}

Output:
{
  "garment_obj_url": "...", "garment_mtl_url": "...",
  "texture_urls": {...}, "pattern_json_url": "...",
  "garment_id": "...", "size": "...",
  "processing_time_seconds": ..., "is_stub": false, "success": true
}

LICENSE NOTE (prototype only): the drape engine inside STEP 2
(NvidiaWarp-GarmentCode) and SMPL-X are NON-COMMERCIAL. Accepted for pre-seed
validation; must be replaced before any paid use. See BUILD_SPEC.md.
"""

import os
import sys
import time
import json
import base64
import shutil
import tempfile
import traceback
from pathlib import Path

import numpy as np

# --- numpy<2.0 shim (same as the drape handler) -------------------------------
# NvidiaWarp-GarmentCode calls np.atan2 / np.pow / np.asin / np.acos / np.atan,
# which only exist in numpy>=2.0. The RunPod pytorch:2.1.0 base pins numpy<2, so
# alias the new names BEFORE any warp import.
for _new, _old in (("atan2", "arctan2"), ("pow", "power"),
                   ("asin", "arcsin"), ("acos", "arccos"), ("atan", "arctan")):
    if not hasattr(np, _new):
        setattr(np, _new, getattr(np, _old))


# =============================================================================
# Paths (baked by Dockerfile.base)
# =============================================================================
CHATGARMENT_ROOT = Path(os.environ.get("CHATGARMENT_ROOT", "/workspace/ChatGarment"))
GARMENTCODERC_ROOT = Path(os.environ.get("GARMENTCODERC_ROOT", "/workspace/GarmentCodeRC"))
WORK_ROOT = Path(os.environ.get("GARMENT_WORK_ROOT", "/workspace/jobs"))

# ChatGarment loads weights from a HARDCODED relative path (verified from source
# scripts/evaluate_garment_v2_imggen_1float.py:183):
#     checkpoints/try_7b_lr1e_4_v3_garmentcontrol_4h100_v4_final/pytorch_model.bin
# resolved against the process CWD (= CHATGARMENT_ROOT, which is where we run the
# eval subprocess from). No CLI/env arg controls it. So the file MUST appear at
# CHATGARMENT_ROOT/checkpoints/<EXP_NAME>/pytorch_model.bin. We back that dir with
# the network volume (see setup_storage) so the 14GB persists across cold starts.
EXP_NAME = "try_7b_lr1e_4_v3_garmentcontrol_4h100_v4_final"
# Checkpoint host: a PRIVATE Hugging Face repo (DC-independent, big-file native,
# fast CDN). Set CHATGARMENT_CKPT_HF_REPO + HF_TOKEN on the endpoint. The legacy
# plain-GET CHATGARMENT_CKPT_URL still works as a fallback.
CHATGARMENT_CKPT_HF_REPO = os.environ.get("CHATGARMENT_CKPT_HF_REPO", "")
CHATGARMENT_CKPT_HF_FILE = os.environ.get("CHATGARMENT_CKPT_HF_FILE", "pytorch_model.bin")
CHATGARMENT_CKPT_URL = os.environ.get("CHATGARMENT_CKPT_URL", "")
CHATGARMENT_CKPT_DIR = CHATGARMENT_ROOT / "checkpoints" / EXP_NAME
CHATGARMENT_CKPT_PATH = CHATGARMENT_CKPT_DIR / "pytorch_model.bin"

# RunPod serverless mounts the network volume here. We route the ~31GB of model
# weights (LLaVA-7B base, CLIP, the ChatGarment checkpoint) onto it so they
# persist across cold starts and don't overflow the 40GB container disk.
VOLUME_ROOT = Path(os.environ.get("GARMENT_VOLUME_ROOT", "/runpod-volume"))

# Base LLM + vision tower (HF; cached on the RunPod network volume across calls)
LLAVA_BASE = os.environ.get("LLAVA_BASE", "liuhaotian/llava-v1.5-7b")
VISION_TOWER = os.environ.get("VISION_TOWER", "openai/clip-vit-large-patch14-336")

# Supabase upload target (reuse the project bucket convention)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
GARMENT_BUCKET = os.environ.get("GARMENT_BUCKET", "garments")


def log(msg: str):
    print(f"[garment-construct] {msg}", flush=True)


# =============================================================================
# Generic download with retries (mirrors the drape handler's helper)
# =============================================================================
def download_file(url: str, dest: Path, timeout: int = 600) -> bool:
    """Stream a URL to disk with 3 retries. Returns True on success.
    Handles file:// for local testing (copies instead of HTTP)."""
    import requests
    dest.parent.mkdir(parents=True, exist_ok=True)
    if url.startswith("file://"):
        try:
            shutil.copy(url[7:], dest)
            return True
        except Exception as e:
            log(f"  local copy failed for {url}: {e}")
            return False
    # Many image hosts/CDNs (Wikimedia, catbox, some Shopify/Supabase edge
    # configs) 403 the default "python-requests" UA. Send a browser-like UA so
    # merchant-supplied URLs from arbitrary hosts download reliably.
    headers = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/124.0 Safari/537.36")}
    for attempt in range(3):
        try:
            with requests.get(url, stream=True, timeout=timeout, headers=headers) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8 << 20):
                        if chunk:
                            f.write(chunk)
            return True
        except Exception as e:
            log(f"  download attempt {attempt+1} for {url} failed: {e}")
            time.sleep(3)
    return False


# =============================================================================
# STEP 0 — ensure model weights present (cold-start bootstrap, _ensure_* pattern)
# =============================================================================
def setup_storage():
    """Route heavy weights onto the network volume so they persist across cold
    starts and don't fill the 40GB container disk.

    - HF cache (LLaVA-7B ~14GB + CLIP ~1.7GB) -> <volume>/hf via HF_HOME.
    - ChatGarment checkpoints dir -> <volume>/chatgarment/checkpoints by
      symlinking CHATGARMENT_ROOT/checkpoints. The eval script reads the
      hardcoded relative path checkpoints/<EXP_NAME>/pytorch_model.bin, so the
      symlink makes the volume-resident file visible at that exact path (and the
      runtime --output_dir under checkpoints/ also lands on the volume).

    Idempotent: safe to call every cold start. No-op (container disk only) if no
    volume is mounted, with a warning that weights won't persist.
    """
    if not VOLUME_ROOT.exists():
        log(f"no network volume at {VOLUME_ROOT}; using container disk "
            f"(weights re-download every cold start)")
        return

    hf = VOLUME_ROOT / "hf"
    hf.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(hf)
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(hf / "hub")
    os.environ["TRANSFORMERS_CACHE"] = str(hf / "hub")

    vol_ck = VOLUME_ROOT / "chatgarment" / "checkpoints"
    vol_ck.mkdir(parents=True, exist_ok=True)
    link = CHATGARMENT_ROOT / "checkpoints"
    if link.is_symlink():
        pass  # warm worker, already linked
    elif not link.exists():
        link.symlink_to(vol_ck, target_is_directory=True)
        log(f"linked {link} -> {vol_ck}")
    else:
        log(f"WARN: {link} exists as a real dir; checkpoint will NOT persist on "
            f"the volume (re-downloads each cold start)")


def ensure_chatgarment_checkpoint() -> bool:
    """Download the ChatGarment LoRA-merged checkpoint from our mirror if absent.

    The upstream weights live on an auth-gated SharePoint link that no server
    can fetch. We mirror pytorch_model.bin (~14-15 GB) to a bucket we control
    and pass that URL as CHATGARMENT_CKPT_URL. Cached on the RunPod network
    volume so it downloads once per cold worker, not per request.
    """
    if CHATGARMENT_CKPT_PATH.exists() and CHATGARMENT_CKPT_PATH.stat().st_size > 10 << 30:
        log(f"checkpoint present ({CHATGARMENT_CKPT_PATH.stat().st_size >> 30} GB)")
        return True

    CHATGARMENT_CKPT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    # Preferred path: pull from the private HF repo (resumable, CDN-backed).
    if CHATGARMENT_CKPT_HF_REPO:
        try:
            from huggingface_hub import hf_hub_download
        except ImportError:
            log("ERROR: huggingface_hub not importable for HF checkpoint download")
            return False
        log(f"downloading checkpoint from HF {CHATGARMENT_CKPT_HF_REPO}/{CHATGARMENT_CKPT_HF_FILE} ...")
        try:
            got = Path(hf_hub_download(
                repo_id=CHATGARMENT_CKPT_HF_REPO,
                filename=CHATGARMENT_CKPT_HF_FILE,
                token=os.environ.get("HF_TOKEN") or None,
                local_dir=str(CHATGARMENT_CKPT_DIR),
            ))
        except Exception as e:
            log(f"ERROR: HF checkpoint download failed: {e}")
            return False
        # hf_hub_download(local_dir=...) lands the file at local_dir/<filename>;
        # normalize to pytorch_model.bin if the repo filename differs.
        if got != CHATGARMENT_CKPT_PATH and got.exists():
            shutil.move(str(got), str(CHATGARMENT_CKPT_PATH))
        sz = CHATGARMENT_CKPT_PATH.stat().st_size
        log(f"checkpoint downloaded: {sz >> 30} GB in {time.time()-t0:.0f}s")
        if sz < 10 << 30:
            log("ERROR: checkpoint smaller than expected (>10 GB) — corrupt?")
            return False
        return True

    # Fallback path: plain-GET URL.
    if not CHATGARMENT_CKPT_URL:
        log("ERROR: neither CHATGARMENT_CKPT_HF_REPO nor CHATGARMENT_CKPT_URL set; checkpoint missing")
        return False
    log(f"downloading checkpoint -> {CHATGARMENT_CKPT_PATH} ...")
    ok = download_file(CHATGARMENT_CKPT_URL, CHATGARMENT_CKPT_PATH, timeout=3600)
    if ok:
        sz = CHATGARMENT_CKPT_PATH.stat().st_size
        log(f"checkpoint downloaded: {sz >> 30} GB in {time.time()-t0:.0f}s")
        if sz < 10 << 30:
            log("ERROR: checkpoint smaller than expected (>10 GB) — corrupt?")
            return False
    return ok


def patch_garmentcode_paths():
    """Rewrite the two hardcoded MPI-cluster paths in run_garmentcode_sim.py
    to our container layout. Idempotent (safe to call every cold start).

    Verified targets (REFERENCE_run_garmentcode_sim.py):
      L8:  sys.path.insert(1, '/is/cluster/fast/sbian/github/GarmentCodeV2/')
      L32: system_path='/is/cluster/fast/sbian/github/GarmentCodeV2/system.json'
    """
    run_sim = CHATGARMENT_ROOT / "run_garmentcode_sim.py"
    if not run_sim.exists():
        log(f"WARN: {run_sim} not found, cannot patch")
        return
    txt = run_sim.read_text()
    orig = txt
    txt = txt.replace(
        "/is/cluster/fast/sbian/github/GarmentCodeV2/system.json",
        str(GARMENTCODERC_ROOT / "system.json"),
    )
    txt = txt.replace(
        "/is/cluster/fast/sbian/github/GarmentCodeV2/",
        str(GARMENTCODERC_ROOT) + "/",
    )
    if txt != orig:
        run_sim.write_text(txt)
        log("patched run_garmentcode_sim.py cluster paths")


def ensure_garmentcode_system_json():
    """GarmentCodeRC needs a system.json pointing at its asset/output dirs.
    Mirror what the drape image already does for pygarment."""
    sysj = GARMENTCODERC_ROOT / "system.json"
    if sysj.exists():
        return
    cfg = {
        "output": str(WORK_ROOT / "gcrc_out"),
        "datasets_path": "",
        "datasets_sim": "",
        "sim_configs_path": str(GARMENTCODERC_ROOT / "assets" / "Sim_props"),
        "bodies_default_path": str(GARMENTCODERC_ROOT / "assets" / "bodies"),
        "body_samples_path": str(GARMENTCODERC_ROOT / "assets" / "bodies"),
    }
    sysj.parent.mkdir(parents=True, exist_ok=True)
    sysj.write_text(json.dumps(cfg, indent=2))
    log(f"wrote {sysj}")


# =============================================================================
# STEP 1 — photo -> GarmentCodeRC parametric JSON  (ChatGarment inference)
# =============================================================================
# We run ChatGarment's own eval python as a subprocess (NOT the .sh, whose
# cluster CUDA env we override). The .sh wraps:
#   deepspeed scripts/evaluate_garment_v2_imggen_1float.py --lora_enable True
#     --lora_r 128 --lora_alpha 256 --model_name_or_path <LLAVA_BASE>
#     --version v1 --data_path_eval <img_folder>
#     --vision_tower <VISION_TOWER> --mm_projector_type mlp2x_gelu
#     --image_aspect_ratio pad --bf16 True --model_max_length 3072 ...
# Output (verified from run_garmentcode_sim.py): the run folder contains
#   <run>/vis_new/all_json_spec_files.json  (list of per-garment spec paths)
#
# NOTE (needs GPU-run confirmation): the exact --output_dir -> run-folder
# mapping and whether single-GPU `python` works vs requiring `deepspeed` are
# confirmed only on a real GPU. We default to the deepspeed launcher the repo
# ships, single process, and capture the produced run folder by scanning.

def run_chatgarment_inference(image_paths: list, job_dir: Path) -> Path:
    """Run ChatGarment on the chosen garment photo(s); return the run folder
    that contains vis_new/all_json_spec_files.json. Raises on hard failure."""
    import subprocess

    # The eval script derives the output run-folder name from the basename of
    # --data_path_eval (<dataset>_img_recon). Use the unique job name so
    # concurrent / repeated requests on a warm worker don't collide in runs/.
    # (Avoid the literal 'img'/'imgs', which the script special-cases.)
    ds_name = job_dir.name
    img_folder = job_dir / ds_name
    img_folder.mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(image_paths):
        ext = Path(p).suffix or ".jpg"
        shutil.copy(p, img_folder / f"img_{i:02d}{ext}")

    env = dict(os.environ)
    # override the cluster CUDA env from the .sh with the base image's toolkit
    env["CUDA_HOME"] = "/usr/local/cuda"
    env["PATH"] = "/usr/local/cuda/bin:" + env.get("PATH", "")
    env["LD_LIBRARY_PATH"] = "/usr/local/cuda/lib64:" + env.get("LD_LIBRARY_PATH", "")
    env["EGL_DEVICE_ID"] = "0"
    env.setdefault("PYTHONPATH", f"{CHATGARMENT_ROOT}:{GARMENTCODERC_ROOT}")

    out_dir = job_dir / "cg_run"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Replicate ChatGarment's OWN launcher verbatim
    # (scripts/v1_5/evaluate_garment_v2_imggen_2step.sh). The eval script asserts
    # on several TrainingArguments (gradient_checkpointing, etc.) and reads many
    # others, so a hand-picked subset fails (verified on real GPU run 2026-06-01:
    # `assert training_args.gradient_checkpointing` tripped). Only deviations from
    # the .sh: --data_path_eval (our per-job img folder), --output_dir (our dir),
    # and --report_to none (the .sh uses wandb, which we have no creds for; the
    # script still writes results to ./runs via the hardcoded log_base_dir).
    cmd = [
        "deepspeed", "scripts/evaluate_garment_v2_imggen_1float.py",
        "--lora_enable", "True", "--lora_r", "128", "--lora_alpha", "256",
        "--mm_projector_lr", "2e-5",
        "--deepspeed", "./scripts/zero2.json",
        "--model_name_or_path", LLAVA_BASE,
        "--version", "v1",
        "--data_path", "./",
        "--data_path_eval", str(img_folder),
        "--image_folder", "./",
        "--vision_tower", VISION_TOWER,
        "--mm_projector_type", "mlp2x_gelu",
        "--mm_vision_select_layer", "-2",
        "--mm_use_im_start_end", "False",
        "--mm_use_im_patch_token", "False",
        "--image_aspect_ratio", "pad",
        "--group_by_modality_length", "True",
        "--bf16", "True",
        "--output_dir", str(out_dir),
        "--num_train_epochs", "1",
        "--per_device_train_batch_size", "16",
        "--per_device_eval_batch_size", "4",
        "--gradient_accumulation_steps", "1",
        "--evaluation_strategy", "no",
        "--save_strategy", "steps",
        "--save_steps", "50000",
        "--save_total_limit", "1",
        "--learning_rate", "2e-4",
        "--weight_decay", "0.",
        "--warmup_ratio", "0.03",
        "--lr_scheduler_type", "cosine",
        "--logging_steps", "1",
        "--tf32", "True",
        "--model_max_length", "3072",
        "--gradient_checkpointing", "True",
        "--dataloader_num_workers", "4",
        "--lazy_preprocess", "True",
        "--report_to", "none",
    ]
    log(f"STEP 1: ChatGarment inference on {len(image_paths)} image(s)")
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=str(CHATGARMENT_ROOT), env=env,
                          capture_output=True, text=True)
    log(f"STEP 1 finished in {time.time()-t0:.0f}s rc={proc.returncode}")
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.splitlines()[-40:])
        log("STEP 1 stderr tail:\n" + tail)
        raise RuntimeError("ChatGarment inference failed:\n" + tail)

    # The eval script writes outputs to ./runs/<EXP_NAME>/<dataset>_img_recon/
    # (relative to CWD = CHATGARMENT_ROOT), NOT under --output_dir and NOT under
    # our job_dir. Verified from source (evaluate_garment_v2_imggen_1float.py
    # :188-259). Prefer the exact expected path; fall back to the freshest match
    # under runs/ (handles any log_base_dir / dataset-name surprise).
    runs_root = CHATGARMENT_ROOT / "runs"
    expected = runs_root / EXP_NAME / f"{ds_name}_img_recon" / "vis_new" / "all_json_spec_files.json"
    if expected.exists():
        run_folder = expected.parent.parent
    else:
        hits = sorted(runs_root.rglob("vis_new/all_json_spec_files.json"),
                      key=lambda p: p.stat().st_mtime) if runs_root.exists() else []
        if not hits:
            log("STEP 1 stdout tail:\n" + "\n".join(proc.stdout.splitlines()[-40:]))
            raise RuntimeError(
                f"ChatGarment produced no all_json_spec_files.json under {runs_root} "
                f"(expected {expected})")
        run_folder = hits[-1].parent.parent
        log(f"STEP 1 expected path absent; using freshest match")
    log(f"STEP 1 run folder: {run_folder}")
    return run_folder


# =============================================================================
# STEP 1.5 — correct systematic ChatGarment prediction errors before draping
# =============================================================================
# Two source-traced defects (verified 2026-06-02 against biansy000/ChatGarment +
# GarmentCodeRC HEAD). Both are fixed by editing the per-garment design.yaml and
# RE-SERIALIZING the spec: the serialized *_specification.json is geometry-baked
# (concrete panel vertices/edges/stitches, no design params), so editing the JSON
# directly is inert (pygarment/pattern/core.py serialize -> json.dump(self.spec)).
#
#   1. Crop-top tees. Shirt body length = design['shirt']['length']['v'] *
#      body['waist_line'] (assets/garment_programs/tee.py:34). ChatGarment
#      systematically under-predicts the length float (template default v=1.2 ->
#      ~44cm; our Moncler tee came back v~1.38 -> 51cm crop-top). Floor it so a
#      labelled shirt never drapes shorter than a normal tee. length range is
#      [0.5,3.5] (assets/design_params/design_used.yaml).
#
#   2. Phantom standing collars. design['collar']['component']['style']='Turtle'
#      makes GarmentCode build a real StraightBandPanel turtleneck band
#      (collars.py Turtle) that is stitched on regardless of the crew f_collar/
#      b_collar. Null the style so getattr(collars, str(style), NoPanelsCollar)
#      (bodice.py:309) falls back to a plain neckline (collars has no 'None' attr).
#
# Non-fatal by design: any failure here logs and leaves the original spec, so a
# post-process bug can never turn the working pipeline into a hard failure.

SHIRT_LENGTH_FLOOR_V = 1.85          # ~68cm body on mean_all waist_line; tune on render
STANDING_COLLAR_STYLES = ("Turtle", "SimpleLapel", "Hood2Panels")


def _reserialize_design(design: dict, name: str, dest_spec: Path):
    """Rebuild dest_spec from an edited `design` dict via GarmentCode's own
    assembler (the same code path STEP-1 used successfully). Serializes into a
    temp dir, then copies the produced *_specification.json over dest_spec — this
    sidesteps guessing serialize()'s output-path/tag semantics. Runs in-process
    so the numpy<2 atan2/pow shim at module top covers assembly()."""
    cwd0 = os.getcwd()
    try:
        # assets.* / sub-component configs resolve relative to GarmentCodeRC root
        os.chdir(str(GARMENTCODERC_ROOT))
        from assets.garment_programs.meta_garment import MetaGarment
        from assets.bodies.body_params import BodyParameters
        body = BodyParameters(str(GARMENTCODERC_ROOT / "assets" / "bodies" / "mean_all.yaml"))
        pat = MetaGarment("valid_garment", body, design).assembly()
        tmp = dest_spec.parent / "_reserialized"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True, exist_ok=True)
        try:
            pat.serialize(str(tmp), tag=name, to_subfolder=True,
                          with_3d=False, with_text=False, view_ids=False)
        except TypeError:  # older/newer serialize signature
            pat.serialize(str(tmp), tag=name, to_subfolder=True)
        produced = sorted(tmp.rglob("*_specification.json"),
                          key=lambda p: p.stat().st_mtime)
        if not produced:
            raise RuntimeError("re-serialize produced no *_specification.json")
        shutil.copy(str(produced[-1]), str(dest_spec))
    finally:
        os.chdir(cwd0)


def postprocess_specs(run_folder: Path) -> list:
    """Floor shirt length + null phantom standing collars on every predicted
    garment, in place, before STEP-2 drape. Per-garment non-fatal. Returns a
    per-garment report (surfaced in the response diagnostics) so the outcome is
    visible without scraping worker logs."""
    import yaml
    report = []
    spec_list = run_folder / "vis_new" / "all_json_spec_files.json"
    if not spec_list.exists():
        log("STEP 1.5: no all_json_spec_files.json; skipping corrections")
        return [{"error": "all_json_spec_files.json missing"}]
    try:
        specs = json.loads(spec_list.read_text())
    except Exception as e:
        log(f"STEP 1.5: cannot read spec list ({e}); skipping")
        return [{"error": f"spec list unreadable: {e}"}]
    for sp in specs:
        sp = sp.replace("validate_garment", "valid_garment")  # mirror run_garmentcode_sim.py:78
        spec_path = Path(sp)
        # Paths in all_json_spec_files.json are RELATIVE to CHATGARMENT_ROOT (the
        # eval uses log_base_dir='./runs'). STEP-2 resolves them via its subprocess
        # cwd; we run in-process, so anchor them to CHATGARMENT_ROOT ourselves —
        # otherwise design.yaml "goes missing" and no correction is applied.
        if not spec_path.is_absolute():
            spec_path = CHATGARMENT_ROOT / spec_path
        folder = spec_path.parent
        name = folder.name.replace("valid_garment_", "")
        dy = folder / "design.yaml"
        rec = {"name": name}
        if not dy.exists():
            rec["status"] = f"design.yaml missing at {dy}"
            log(f"STEP 1.5 [{name}]: {rec['status']}; leaving spec as-is")
            report.append(rec); continue
        try:
            design = (yaml.safe_load(dy.read_text()) or {}).get("design")
            if not isinstance(design, dict):
                rec["status"] = "no 'design' block"
                report.append(rec); continue
            changed = []
            sh = design.get("shirt")
            if (isinstance(sh, dict) and isinstance(sh.get("length"), dict)
                    and sh["length"].get("v") is not None):
                rec["read_shirt_length_v"] = sh["length"]["v"]
                if float(sh["length"]["v"]) < SHIRT_LENGTH_FLOOR_V:
                    changed.append(f"shirt.length {sh['length']['v']}->{SHIRT_LENGTH_FLOOR_V}")
                    sh["length"]["v"] = SHIRT_LENGTH_FLOOR_V
            st = (design.get("collar") or {}).get("component", {}).get("style")
            if isinstance(st, dict) and st.get("v") in STANDING_COLLAR_STYLES:
                changed.append(f"collar.style {st['v']}->None")
                st["v"] = None
            if not changed:
                rec["status"] = "no change needed"
                report.append(rec); continue
            dy.write_text(yaml.dump({"design": design}))
            _reserialize_design(design, name, spec_path)
            rec["status"] = "re-serialized"
            rec["changed"] = changed
            log(f"STEP 1.5 [{name}]: {', '.join(changed)} (spec re-serialized)")
        except Exception as e:
            rec["status"] = f"failed: {e}"
            log(f"STEP 1.5 [{name}]: correction failed, keeping original spec ({e})")
        report.append(rec)
    return report


# =============================================================================
# STEP 2 — GarmentCodeRC JSON -> draped 3D garment OBJ + UVs
# =============================================================================
# Verified from REFERENCE_run_garmentcode_sim.py:
#   reads <run>/vis_new/all_json_spec_files.json -> list of *_specification.json
#   for each: BoxMesh(spec).load(); .serialize(uv_config=...); run_sim(...)
#   drapes on bundled body 'mean_all' (smpl_body=False); writes draped OBJ to
#   the spec's own folder. Output naming follows PathCofig (in_name = stem minus
#   trailing _<word>); the draped sim mesh lands as <name>_sim.obj.

def _select_garment_obj(candidates: list, garment_type_hint: str) -> Path:
    """ChatGarment may drape several components (upper/lower/wholebody) for one
    photo. Pick the one matching the garment type instead of blindly taking the
    last (which gave us the trousers of a predicted outfit for a t-shirt photo,
    2026-06-01). Falls back to the largest mesh if nothing matches the hint."""
    hint = (garment_type_hint or "").lower()
    TOPS = ("shirt", "tshirt", "t-shirt", "tee", "hoodie", "sweater", "sweat",
            "top", "jacket", "blouse", "polo", "coat")
    BOTTOMS = ("pants", "trouser", "short", "skirt", "jeans", "legging")
    def name(p): return p.name.lower()
    if any(h in hint for h in TOPS):
        want = ("upper", "wholebody", "whole")
    elif any(h in hint for h in BOTTOMS):
        want = ("lower",)
    else:
        want = ("wholebody", "whole", "upper")  # default: prefer a full/upper garment
    for key in want:
        hits = [c for c in candidates if key in name(c)]
        if hits:
            return max(hits, key=lambda p: p.stat().st_size)
    # no name match -> largest mesh (most complete garment)
    return max(candidates, key=lambda p: p.stat().st_size)


def run_garmentcode_sim(run_folder: Path, garment_type_hint: str = "") -> Path:
    """Invoke ChatGarment's run_garmentcode_sim.py over the run folder.
    Returns the path to the produced draped garment OBJ (with UVs)."""
    import subprocess

    env = dict(os.environ)
    env["CUDA_HOME"] = "/usr/local/cuda"
    env["PATH"] = "/usr/local/cuda/bin:" + env.get("PATH", "")
    env["LD_LIBRARY_PATH"] = "/usr/local/cuda/lib64:" + env.get("LD_LIBRARY_PATH", "")
    env.setdefault("PYTHONPATH", f"{GARMENTCODERC_ROOT}:{CHATGARMENT_ROOT}")

    cmd = ["python", "run_garmentcode_sim.py", "--all_paths_json", str(run_folder)]
    log("STEP 2: GarmentCodeRC drape (BoxMesh -> serialize uv -> run_sim)")
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=str(CHATGARMENT_ROOT), env=env,
                          capture_output=True, text=True)
    log(f"STEP 2 finished in {time.time()-t0:.0f}s rc={proc.returncode}")
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.splitlines()[-40:])
        log("STEP 2 stderr tail:\n" + tail)
        raise RuntimeError("GarmentCodeRC simulation failed:\n" + tail)

    # Find the draped sim OBJ. PathCofig writes <name>_sim.obj near the spec.
    # Prefer *_sim.obj; fall back to any new .obj with UV ('vt') lines.
    candidates = sorted(run_folder.rglob("*_sim.obj"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        candidates = [p for p in run_folder.rglob("*.obj")
                      if b"vt " in p.read_bytes()[:200000]]
    if not candidates:
        raise RuntimeError("STEP 2 produced no draped OBJ with UVs")
    log(f"STEP 2 produced {len(candidates)} garment(s): {[c.name for c in candidates]}")
    obj = _select_garment_obj(candidates, garment_type_hint)
    log(f"STEP 2 selected OBJ (hint={garment_type_hint!r}): {obj}")
    return obj


# =============================================================================
# STEP 3 — texture extraction onto the UV layout
# =============================================================================
# Scope (per product decision 2026-05-31): we do NOT bake a photoreal texture.
# Our existing drape model already does texture MAPPING; STEP 3 only EXTRACTS
# the right pixels and writes the file bundle the drape handler ingests:
#   {size}.obj (UVs + mtllib line), {size}.mtl (newmtl + Kd + map_Kd basename),
#   <texture>.png.
# v1: dominant fabric colour fill (rembg-masked) as the diffuse texture.
# v2 (follow-up, flagged): paste detected logo/print region at its UV location.

def _dominant_color(img_path: Path) -> tuple:
    """Mean RGB of the garment region (background removed via rembg if present)."""
    from PIL import Image
    im = Image.open(img_path).convert("RGB")
    arr = np.asarray(im).reshape(-1, 3).astype(np.float32)
    try:
        from rembg import remove
        cut = remove(im)  # RGBA with bg alpha=0
        rgba = np.asarray(cut.convert("RGBA")).reshape(-1, 4)
        mask = rgba[:, 3] > 16
        if mask.sum() > 100:
            arr = rgba[mask][:, :3].astype(np.float32)
    except Exception as e:
        log(f"  rembg unavailable, using full-image mean ({e})")
    rgb = arr.mean(axis=0) / 255.0
    return float(rgb[0]), float(rgb[1]), float(rgb[2])


def build_texture_bundle(garment_obj: Path, source_images: list,
                         out_dir: Path, size: str) -> dict:
    """Write {size}.obj + {size}.mtl + {size}_texture.png. Returns paths."""
    from PIL import Image

    out_dir.mkdir(parents=True, exist_ok=True)
    obj_out = out_dir / f"{size}.obj"
    mtl_out = out_dir / f"{size}.mtl"
    tex_out = out_dir / f"{size}_texture.png"
    mtl_name = f"fabric_{size}"

    # extract dominant fabric colour from the first usable photo
    r, g, b = (0.5, 0.5, 0.5)
    if source_images:
        try:
            r, g, b = _dominant_color(Path(source_images[0]))
        except Exception as e:
            log(f"  colour extraction failed, grey fallback ({e})")
    log(f"STEP 3: fabric colour rgb=({r:.2f},{g:.2f},{b:.2f})")

    # flat diffuse texture (1024x1024) of the fabric colour.
    # NOTE: drape model does the mapping; a flat fill is the honest v1. Logo
    # placement onto the UV island is the v2 follow-up.
    tex = Image.new("RGB", (1024, 1024),
                    (int(r * 255), int(g * 255), int(b * 255)))
    tex.save(tex_out)

    # copy the OBJ, ensuring a single mtllib line points at our MTL basename AND
    # that every usemtl references the material name we actually declare. STEP-2
    # ships the OBJ with `usemtl panels_texture`, which doesn't match our
    # `newmtl fabric_{size}`, so the texture never binds in a viewer (confirmed
    # 2026-06-02). Rewrite any existing usemtl to our name; if there is none,
    # insert one before the first face.
    obj_txt = garment_obj.read_text()
    obj_lines, inserted = [], False
    for ln in obj_txt.splitlines():
        if ln.startswith("mtllib"):
            continue
        if ln.startswith("usemtl"):
            ln = f"usemtl {mtl_name}"
            inserted = True
        elif ln.startswith("f ") and not inserted:
            obj_lines.append(f"usemtl {mtl_name}")
            inserted = True
        obj_lines.append(ln)
    header = [f"mtllib {mtl_out.name}"]
    obj_out.write_text("\n".join(header + obj_lines) + "\n")

    # MTL: basename map_Kd only (drape handler requires no absolute paths)
    mtl_out.write_text(
        f"newmtl {mtl_name}\n"
        f"Kd {r:.4f} {g:.4f} {b:.4f}\n"
        f"Ka 0 0 0\nKs 0 0 0\nd 1\nillum 1\n"
        f"map_Kd {tex_out.name}\n"
    )

    has_uv = "vt " in obj_txt
    if not has_uv:
        log("WARN: STEP-2 OBJ has no 'vt' UVs — texture will not map")
    return {"obj": obj_out, "mtl": mtl_out, "texture": tex_out, "has_uv": has_uv}


# =============================================================================
# Upload — Supabase Storage (matches backend/app/api/routes/garments.py)
# =============================================================================
# Path convention: {garment_id}/{size}/{size}.{ext}  in the `garments` bucket.
# POST storage/v1/object/{bucket}/{path} with x-upsert; public URL at
# storage/v1/object/public/{bucket}/{path}.

def upload_to_supabase(local: Path, dest_path: str, content_type: str) -> str:
    import requests
    if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY not set")
    url = f"{SUPABASE_URL}/storage/v1/object/{GARMENT_BUCKET}/{dest_path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "apikey": SUPABASE_SERVICE_KEY,
        "content-type": content_type,
        "x-upsert": "true",
    }
    with open(local, "rb") as f:
        r = requests.post(url, headers=headers, data=f, timeout=300)
    r.raise_for_status()
    return f"{SUPABASE_URL}/storage/v1/object/public/{GARMENT_BUCKET}/{dest_path}"


# =============================================================================
# Diagnostics — snapshot the (ephemeral) ChatGarment run folder
# =============================================================================
def collect_run_artifacts(run_folder: Path) -> dict:
    """What did ChatGarment actually predict, and what did STEP-2 drape?

    ChatGarment is trained on full-outfit photos, so from a single garment shot
    it often predicts a COMPLETE outfit (upperbody_garment + lowerbody_garment,
    or a wholebody_garment). The parser then builds one spec per component and
    STEP-2 drapes each into its own *_sim.obj. This returns the model's raw
    prediction text + every draped garment (verts/faces + its 2D sewing-pattern
    PNG, downscaled) so we can see which piece is which from one upload:false run.
    """
    diag = {"run_folder": str(run_folder), "model_predictions": [], "garments": []}
    for txt in sorted(run_folder.rglob("output.txt")):
        try:
            diag["model_predictions"].append({
                "path": str(txt.relative_to(run_folder)),
                "text": txt.read_text(errors="ignore")[:6000],
            })
        except Exception:
            pass
    for obj in sorted(run_folder.rglob("*_sim.obj")):
        try:
            t = obj.read_text(errors="ignore")
            entry = {"name": str(obj.relative_to(run_folder)),
                     "verts": t.count("\nv "), "faces": t.count("\nf "),
                     "has_uv": "vt " in t}
            pats = list(obj.parent.rglob("*_pattern.png"))
            if pats:
                from PIL import Image
                import io
                im = Image.open(pats[0]); im.thumbnail((1024, 1024))
                buf = io.BytesIO(); im.save(buf, "PNG")
                entry["pattern_png_base64"] = base64.b64encode(buf.getvalue()).decode()
                entry["pattern_file"] = pats[0].name
            diag["garments"].append(entry)
        except Exception as e:
            diag["garments"].append({"name": str(obj), "error": str(e)})
    return diag


# =============================================================================
# Main handler
# =============================================================================
def handler(event: dict) -> dict:
    t_start = time.time()
    inp = event.get("input", {}) or {}
    image_urls = inp.get("image_urls") or ([inp["image_url"]] if inp.get("image_url") else [])
    garment_id = inp.get("garment_id", "test-garment")
    size = (inp.get("size") or "m").lower().strip()
    do_upload = inp.get("upload", True)

    if not image_urls:
        return {"success": False, "error": "no image_urls provided"}

    job_dir = WORK_ROOT / f"{garment_id}_{size}_{int(t_start)}"
    job_dir.mkdir(parents=True, exist_ok=True)
    try:
        # STEP 0 — bootstrap
        setup_storage()  # route weights onto the network volume BEFORE any download
        if not ensure_chatgarment_checkpoint():
            return {"success": False, "error": "checkpoint unavailable"}
        ensure_garmentcode_system_json()
        patch_garmentcode_paths()

        # fetch source photos
        local_imgs = []
        for i, u in enumerate(image_urls):
            dst = job_dir / f"src_{i:02d}{Path(u).suffix or '.jpg'}"
            if not download_file(u, dst):
                return {"success": False, "error": f"could not download {u}"}
            local_imgs.append(dst)

        # STEP 1 — photo -> JSON (uses the first/best photo for geometry)
        run_folder = run_chatgarment_inference(local_imgs[:1], job_dir)

        # STEP 1.5 — correct systematic prediction errors (crop-top length +
        # phantom standing collar) by editing design.yaml and re-serializing the
        # baked spec, before the (paid) drape. Non-fatal; report surfaced below.
        step15_report = postprocess_specs(run_folder)

        # STEP 2 — JSON -> draped OBJ + UV (pick the component matching the type)
        garment_obj = run_garmentcode_sim(run_folder, (inp.get("garment_type_hint") or ""))

        # STEP 3 — texture extraction + bundle assembly
        bundle = build_texture_bundle(garment_obj, local_imgs, job_dir / "out", size)

        result = {
            "success": True,
            "garment_id": garment_id,
            "size": size,
            "is_stub": False,
            "has_uv": bundle["has_uv"],
            "step1_5": step15_report,
            "processing_time_seconds": round(time.time() - t_start, 1),
        }

        # Diagnostics: what ChatGarment predicted + every draped garment + its
        # 2D pattern image. On by default for non-upload (test) runs.
        if inp.get("debug", not do_upload):
            try:
                result["diagnostics"] = collect_run_artifacts(run_folder)
            except Exception as e:
                result["diagnostics_error"] = str(e)

        if do_upload:
            base = f"{garment_id}/{size}"
            result["garment_obj_url"] = upload_to_supabase(
                bundle["obj"], f"{base}/{size}.obj", "application/octet-stream")
            result["garment_mtl_url"] = upload_to_supabase(
                bundle["mtl"], f"{base}/{size}.mtl", "application/octet-stream")
            result["texture_urls"] = {
                bundle["texture"].name: upload_to_supabase(
                    bundle["texture"], f"{base}/{bundle['texture'].name}", "image/png")
            }
        else:
            result["garment_obj_base64"] = base64.b64encode(bundle["obj"].read_bytes()).decode()
            result["garment_mtl_base64"] = base64.b64encode(bundle["mtl"].read_bytes()).decode()
            result["texture_base64"] = {
                bundle["texture"].name: base64.b64encode(bundle["texture"].read_bytes()).decode()
            }
        return result

    except Exception as e:
        tb = traceback.format_exc()
        log("HANDLER ERROR:\n" + tb)
        # Surface the failure detail in the JSON response (visible via /status
        # output) so we can diagnose without scraping the worker console.
        return {"success": False, "error": str(e),
                "error_detail": "\n".join(tb.splitlines()[-30:]),
                "processing_time_seconds": round(time.time() - t_start, 1)}
    finally:
        # keep job_dir on failure for debugging; clean on success path is caller's choice
        pass


def runpod_handler(event):
    return handler(event)


HANDLER_BUILD = "garment-construction v0.1 (ChatGarment -> GarmentCodeRC -> texture)"

try:
    import runpod
    print(f"[garment-construct] === {HANDLER_BUILD} ===")
    runpod.serverless.start({"handler": runpod_handler})
except ImportError:
    print("[garment-construct] RunPod not installed — local/import mode")
except Exception as e:
    print(f"[garment-construct] startup error: {e}")
    traceback.print_exc()
    raise


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Test garment construction locally")
    ap.add_argument("--images", nargs="+", required=True, help="image paths/urls")
    ap.add_argument("--garment-id", default="test-garment")
    ap.add_argument("--size", default="m")
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()
    ev = {"input": {
        "image_urls": [u if "://" in u else f"file://{os.path.abspath(u)}" for u in args.images],
        "garment_id": args.garment_id, "size": args.size, "upload": not args.no_upload,
    }}
    out = handler(ev)
    print(json.dumps({k: v for k, v in out.items() if "base64" not in k}, indent=2))
