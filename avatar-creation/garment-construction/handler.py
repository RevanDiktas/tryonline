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

# Checkpoint: mirrored off SharePoint to a bucket we control. Runtime-download.
CHATGARMENT_CKPT_URL = os.environ.get("CHATGARMENT_CKPT_URL", "")
CHATGARMENT_CKPT_DIR = CHATGARMENT_ROOT / "checkpoints" / "try_7b_lr1e_4_v3_garmentcontrol_4h100_v4_final"
CHATGARMENT_CKPT_PATH = CHATGARMENT_CKPT_DIR / "pytorch_model.bin"

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
    for attempt in range(3):
        try:
            with requests.get(url, stream=True, timeout=timeout) as r:
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
    if not CHATGARMENT_CKPT_URL:
        log("ERROR: CHATGARMENT_CKPT_URL not set and checkpoint missing")
        return False
    log(f"downloading checkpoint -> {CHATGARMENT_CKPT_PATH} ...")
    t0 = time.time()
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

    img_folder = job_dir / "input_imgs"
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

    cmd = [
        "deepspeed", "scripts/evaluate_garment_v2_imggen_1float.py",
        "--lora_enable", "True", "--lora_r", "128", "--lora_alpha", "256",
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
        "--bf16", "True",
        "--output_dir", str(out_dir),
        "--model_max_length", "3072",
        "--report_to", "none",
    ]
    log(f"STEP 1: ChatGarment inference on {len(image_paths)} image(s)")
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=str(CHATGARMENT_ROOT), env=env,
                          capture_output=True, text=True)
    log(f"STEP 1 finished in {time.time()-t0:.0f}s rc={proc.returncode}")
    if proc.returncode != 0:
        log("STEP 1 stderr tail:\n" + "\n".join(proc.stderr.splitlines()[-40:]))
        raise RuntimeError("ChatGarment inference failed")

    # locate the produced all_json_spec_files.json under the job dir
    hits = list(job_dir.rglob("vis_new/all_json_spec_files.json"))
    if not hits:
        raise RuntimeError("ChatGarment produced no all_json_spec_files.json")
    run_folder = hits[0].parent.parent
    log(f"STEP 1 run folder: {run_folder}")
    return run_folder


# =============================================================================
# STEP 2 — GarmentCodeRC JSON -> draped 3D garment OBJ + UVs
# =============================================================================
# Verified from REFERENCE_run_garmentcode_sim.py:
#   reads <run>/vis_new/all_json_spec_files.json -> list of *_specification.json
#   for each: BoxMesh(spec).load(); .serialize(uv_config=...); run_sim(...)
#   drapes on bundled body 'mean_all' (smpl_body=False); writes draped OBJ to
#   the spec's own folder. Output naming follows PathCofig (in_name = stem minus
#   trailing _<word>); the draped sim mesh lands as <name>_sim.obj.

def run_garmentcode_sim(run_folder: Path) -> Path:
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
        log("STEP 2 stderr tail:\n" + "\n".join(proc.stderr.splitlines()[-40:]))
        raise RuntimeError("GarmentCodeRC simulation failed")

    # Find the draped sim OBJ. PathCofig writes <name>_sim.obj near the spec.
    # Prefer *_sim.obj; fall back to any new .obj with UV ('vt') lines.
    candidates = sorted(run_folder.rglob("*_sim.obj"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        candidates = [p for p in run_folder.rglob("*.obj")
                      if b"vt " in p.read_bytes()[:200000]]
    if not candidates:
        raise RuntimeError("STEP 2 produced no draped OBJ with UVs")
    obj = candidates[-1]
    log(f"STEP 2 draped OBJ: {obj}")
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

    # copy the OBJ, ensuring a single mtllib line points at our MTL basename
    obj_txt = garment_obj.read_text()
    obj_lines = [ln for ln in obj_txt.splitlines() if not ln.startswith("mtllib")]
    has_usemtl = any(ln.startswith("usemtl") for ln in obj_lines)
    header = [f"mtllib {mtl_out.name}"]
    if not has_usemtl:
        # insert a usemtl before the first face so the material binds
        new_lines, inserted = [], False
        for ln in obj_lines:
            if ln.startswith("f ") and not inserted:
                new_lines.append(f"usemtl {mtl_name}")
                inserted = True
            new_lines.append(ln)
        obj_lines = new_lines
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

        # STEP 2 — JSON -> draped OBJ + UV
        garment_obj = run_garmentcode_sim(run_folder)

        # STEP 3 — texture extraction + bundle assembly
        bundle = build_texture_bundle(garment_obj, local_imgs, job_dir / "out", size)

        result = {
            "success": True,
            "garment_id": garment_id,
            "size": size,
            "is_stub": False,
            "has_uv": bundle["has_uv"],
            "processing_time_seconds": round(time.time() - t_start, 1),
        }

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
        log("HANDLER ERROR:\n" + traceback.format_exc())
        return {"success": False, "error": str(e),
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
