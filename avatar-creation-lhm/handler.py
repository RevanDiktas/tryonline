"""
RunPod Serverless Handler for LHM (Large Animatable Human Reconstruction Model)
================================================================================

Phase 0 dev-mode handler. Implements a small dispatch table of commands so we
can iterate on inference, file inspection, and model management WITHOUT
rebuilding the Docker image for every change.

Input shape:
{
  "input": {
    "command":   "info" | "ls" | "cat" | "init" | "download_model"
               | "inference" | "inference_mesh" | "shell",
    ...command-specific args...
  }
}

The "init" command pre-downloads + extracts the LHM data tarballs
(LHM_prior_model.tar, motion_video.tar) that are NOT baked into the image
because of RunPod's 30-min build-export budget. Run it once per fresh worker
after deploy to avoid paying the ~5-min cost on the first inference request.
Inference commands also call this lazily, so it is optional.

Output shape (all commands):
{
  "ok": true/false,
  "command": "<the command>",
  "data": { ... },              # command-specific payload
  "error": "<msg if ok=false>",
  "elapsed_seconds": <float>
}

Output artifacts strategy:
- Small (<10 MB): returned inline as base64 in `data.files_base64`
- Large: uploaded to Supabase 'lhm-artifacts' bucket, returned as public URLs
- Either way the keys in `data` are the same so the client doesn't need to
  branch on size.

Env vars expected on the RunPod endpoint:
- SUPABASE_URL                 (e.g. https://cykwthsbrylonconqlfz.supabase.co)
- SUPABASE_SERVICE_KEY         (service-role key, NOT anon)
- LHM_BUCKET                   (defaults to 'lhm-artifacts')
- LHM_DEFAULT_MODEL            (defaults to 'LHM-MINI'; baked into image)
- LHM_ALLOW_SHELL              ('1' to allow the `shell` command; off by default)
"""

import os
import sys
import time
import json
import base64
import shutil
import tempfile
import subprocess
import traceback
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths & config
# ---------------------------------------------------------------------------
LHM_ROOT = Path("/workspace/LHM")
MODELS_DIR = LHM_ROOT / "pretrained_models" / "huggingface"
MOTION_DEFAULT = LHM_ROOT / "train_data" / "motion_video" / "mimo1" / "smplx_params"
INLINE_MAX_BYTES = 10 * 1024 * 1024  # 10 MB

# Lazy-downloaded Aliyun tarballs. See Dockerfile.runpod for why they're not
# baked into the image. Each tarball extracts into DATA_DIR; we don't rely on
# knowing the internal layout and instead use a marker file in DATA_DIR to
# record successful extraction.
#
# DATA_DIR resolution:
#   1. /runpod-volume/lhm-data  (if a RunPod Network Volume is mounted and
#      writable — the production path; shared across all workers, one-shot
#      download for the lifetime of the volume)
#   2. /workspace/LHM           (fallback for local testing / pre-volume
#      setups; pays the 5-min Aliyun download per cold worker)
ALIYUN_BASE = "https://virutalbuy-public.oss-cn-hangzhou.aliyuncs.com/share/aigc3d/data/LHM"
DATA_FILES = [
    {"name": "LHM_prior_model.tar", "url": f"{ALIYUN_BASE}/LHM_prior_model.tar"},
    {"name": "motion_video.tar",    "url": f"{ALIYUN_BASE}/motion_video.tar"},
]


def _resolve_data_dir() -> Path:
    """Pick the runtime data dir. See comment block above DATA_FILES."""
    volume = Path("/runpod-volume")
    if volume.is_dir() and os.access(volume, os.W_OK):
        d = volume / "lhm-data"
        d.mkdir(parents=True, exist_ok=True)
        return d
    return LHM_ROOT


DATA_DIR = _resolve_data_dir()
USING_VOLUME = DATA_DIR != LHM_ROOT

DEFAULT_MODEL = os.environ.get("LHM_DEFAULT_MODEL", "LHM-MINI")
ALLOW_SHELL = os.environ.get("LHM_ALLOW_SHELL", "0") == "1"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_BUCKET = os.environ.get("LHM_BUCKET", "lhm-artifacts")

# Lazy imports: keep container startup cheap. Heavy stuff loads only when its
# command runs.
try:
    import httpx
    HAVE_HTTPX = True
except ImportError:
    HAVE_HTTPX = False
    import urllib.request  # fallback

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now() -> float:
    return time.time()


def _ok(command: str, data: dict, started: float) -> dict:
    return {
        "ok": True,
        "command": command,
        "data": data,
        "elapsed_seconds": round(_now() - started, 2),
    }


def _err(command: str, msg: str, started: float, extra: dict | None = None) -> dict:
    payload = {
        "ok": False,
        "command": command,
        "error": msg,
        "elapsed_seconds": round(_now() - started, 2),
    }
    if extra:
        payload["data"] = extra
    return payload


def _download_to(path: Path, url: str, timeout: float = 120.0) -> None:
    """Download a URL into a local file. Used for inference input images."""
    if url.startswith("file://"):
        shutil.copy(url[7:], path)
        return
    if HAVE_HTTPX:
        with httpx.Client(timeout=timeout, follow_redirects=True) as c:
            r = c.get(url)
            r.raise_for_status()
            path.write_bytes(r.content)
    else:
        urllib.request.urlretrieve(url, path)


def _upload_supabase(local_path: Path, remote_path: str) -> str:
    """Upload a file to Supabase storage, return its public URL.

    Raises RuntimeError on failure. Caller is responsible for catching.
    """
    if not (SUPABASE_URL and SUPABASE_KEY):
        raise RuntimeError("Supabase credentials not configured")
    if not HAVE_HTTPX:
        raise RuntimeError("httpx required for Supabase upload")

    url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{remote_path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "x-upsert": "true",
        "Content-Type": "application/octet-stream",
    }
    with httpx.Client(timeout=300.0) as c:
        r = c.post(url, headers=headers, content=local_path.read_bytes())
        if r.status_code not in (200, 201):
            raise RuntimeError(
                f"Supabase upload failed {r.status_code}: {r.text[:300]}"
            )
    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{remote_path}"


def _collect_artifact(local_path: Path, remote_subdir: str) -> dict:
    """Return {url|base64, size_bytes, name} for one artifact.

    Inline if small + no Supabase, uploaded otherwise. The client always sees
    either `url` or `base64` populated, never both.
    """
    size = local_path.stat().st_size
    name = local_path.name
    if size <= INLINE_MAX_BYTES and not (SUPABASE_URL and SUPABASE_KEY):
        return {
            "name": name,
            "size_bytes": size,
            "base64": base64.b64encode(local_path.read_bytes()).decode("ascii"),
        }
    # Either too big for inline OR Supabase is configured: try upload.
    try:
        url = _upload_supabase(local_path, f"{remote_subdir}/{name}")
        return {"name": name, "size_bytes": size, "url": url}
    except Exception as e:
        # Fall back to inline if upload fails AND it's small enough.
        if size <= INLINE_MAX_BYTES:
            return {
                "name": name,
                "size_bytes": size,
                "base64": base64.b64encode(local_path.read_bytes()).decode("ascii"),
                "upload_error": str(e),
            }
        return {"name": name, "size_bytes": size, "upload_error": str(e)}


def _ensure_lhm_data(log: list[str] | None = None) -> None:
    """Download + extract Aliyun-hosted LHM data tarballs if not already present.

    Idempotent. Safe to call from every inference. On a Network-Volume-backed
    deployment the download is amortized across every worker that ever attaches
    to the volume; on a fallback (LHM_ROOT) deployment, every fresh worker pays
    the ~5-min cost.

    Marker pattern: after a tarball is successfully extracted, we touch
    `<DATA_DIR>/.<tarname>.extracted`. We don't rely on knowing the internal
    layout of the tarball.

    When DATA_DIR is the volume (i.e. NOT LHM_ROOT), we also stitch the
    extracted content into LHM_ROOT via symlinks so LHM's CLI finds files at
    the paths its scripts expect.

    Raises RuntimeError on download/extract failure.
    """
    for item in DATA_FILES:
        name = item["name"]
        marker = DATA_DIR / f".{name}.extracted"
        if marker.exists():
            if log is not None:
                log.append(f"{name}: already present at {DATA_DIR} (marker found)")
            continue

        if log is not None:
            log.append(f"{name}: downloading to {DATA_DIR}")
        tar_path = DATA_DIR / name
        # aria2c is installed in the image; the same -x 16 -s 16 flags that
        # cut Aliyun download time from ~31min to ~5min at build time work
        # the same way at runtime (152 MiB/s observed from a CA worker).
        dl = subprocess.run(
            ["aria2c", "-x", "16", "-s", "16",
             "--max-tries=5", "--retry-wait=10",
             "--console-log-level=warn",
             "--allow-overwrite=true",
             "-d", str(DATA_DIR),
             "-o", name,
             item["url"]],
            capture_output=True, text=True, timeout=1800,
        )
        if dl.returncode != 0:
            raise RuntimeError(
                f"aria2c failed for {name} (rc={dl.returncode}): "
                f"{dl.stderr[-1000:] or dl.stdout[-1000:]}"
            )

        if log is not None:
            log.append(f"{name}: extracting in {DATA_DIR}")
        ex = subprocess.run(
            ["tar", "-xf", str(tar_path)],
            cwd=str(DATA_DIR), capture_output=True, text=True, timeout=600,
        )
        if ex.returncode != 0:
            # don't leave the half-extracted tar on disk to bloat the volume
            try:
                tar_path.unlink()
            except OSError:
                pass
            raise RuntimeError(
                f"tar -xf failed for {name} (rc={ex.returncode}): "
                f"{ex.stderr[-1000:]}"
            )
        try:
            tar_path.unlink()
        except OSError:
            pass
        marker.touch()
        if log is not None:
            log.append(f"{name}: done")

    # On a fresh worker that mounts a previously-populated volume, the
    # tarball check above skips download/extract, but the worker's LHM_ROOT
    # has no symlinks to the volume contents yet. So always (re)stitch.
    if USING_VOLUME:
        _stitch_volume_into_lhm_root(log=log)


def _stitch_volume_into_lhm_root(log: list[str] | None = None) -> None:
    """Make /workspace/LHM/<x> point to /runpod-volume/lhm-data/<x>.

    Top-level entries that already exist as real directories in LHM_ROOT
    (e.g. `pretrained_models/` with its `huggingface/` child from the image
    build) get merged one level deep: we walk the volume's subentries and
    symlink each one that doesn't already exist in LHM_ROOT.

    Entries that don't exist in LHM_ROOT at all get symlinked whole.

    Existing symlinks are left alone (idempotent across worker restarts).
    """
    for entry in DATA_DIR.iterdir():
        if entry.name.startswith("."):
            continue  # marker files
        target = LHM_ROOT / entry.name
        if target.is_symlink():
            continue  # already stitched
        if entry.is_dir() and target.exists() and target.is_dir():
            # merge: link grandchildren that don't exist in the image dir
            for sub in entry.iterdir():
                sub_target = target / sub.name
                if sub_target.exists() or sub_target.is_symlink():
                    continue
                try:
                    sub_target.symlink_to(sub)
                    if log is not None:
                        log.append(f"linked {sub_target} -> {sub}")
                except OSError as e:
                    if log is not None:
                        log.append(f"symlink failed {sub_target} -> {sub}: {e}")
        elif not target.exists():
            try:
                target.symlink_to(entry)
                if log is not None:
                    log.append(f"linked {target} -> {entry}")
            except OSError as e:
                if log is not None:
                    log.append(f"symlink failed {target} -> {entry}: {e}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_info(_inp: dict, started: float) -> dict:
    """Return container + GPU + disk + model info. No GPU needed."""
    import platform

    info: dict[str, Any] = {
        "hostname": platform.node(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cwd": str(Path.cwd()),
        "lhm_root_exists": LHM_ROOT.exists(),
        "default_model": DEFAULT_MODEL,
        "allow_shell": ALLOW_SHELL,
        "supabase_configured": bool(SUPABASE_URL and SUPABASE_KEY),
    }
    # torch / CUDA
    try:
        import torch
        info["torch"] = torch.__version__
        info["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            info["cuda_version"] = torch.version.cuda
            info["gpu_count"] = torch.cuda.device_count()
            info["gpu_name"] = torch.cuda.get_device_name(0)
            free, total = torch.cuda.mem_get_info(0)
            info["gpu_mem_total_gb"] = round(total / 1024**3, 2)
            info["gpu_mem_free_gb"] = round(free / 1024**3, 2)
    except Exception as e:
        info["torch_error"] = str(e)

    # Disk usage at workspace
    try:
        usage = shutil.disk_usage("/workspace")
        info["disk_total_gb"] = round(usage.total / 1024**3, 2)
        info["disk_free_gb"] = round(usage.free / 1024**3, 2)
    except Exception:
        pass

    # Installed model variants
    info["models_present"] = []
    if MODELS_DIR.exists():
        for repo_dir in MODELS_DIR.iterdir():
            if repo_dir.is_dir():
                info["models_present"].append(repo_dir.name)

    # Lazy-downloaded data files (see _ensure_lhm_data).
    info["data_dir"] = str(DATA_DIR)
    info["using_volume"] = USING_VOLUME
    info["data_files"] = {
        d["name"]: (DATA_DIR / f".{d['name']}.extracted").exists()
        for d in DATA_FILES
    }
    # Quick volume sanity if mounted.
    if USING_VOLUME:
        try:
            v_usage = shutil.disk_usage("/runpod-volume")
            info["volume_total_gb"] = round(v_usage.total / 1024**3, 2)
            info["volume_free_gb"] = round(v_usage.free / 1024**3, 2)
        except Exception:
            pass

    # Repo files at LHM_ROOT (top level only)
    if LHM_ROOT.exists():
        info["lhm_root_files"] = sorted(p.name for p in LHM_ROOT.iterdir())

    return _ok("info", info, started)


def cmd_ls(inp: dict, started: float) -> dict:
    target = Path(inp.get("path", str(LHM_ROOT)))
    if not target.exists():
        return _err("ls", f"path not found: {target}", started)
    if target.is_file():
        return _ok("ls", {"path": str(target), "is_file": True,
                          "size_bytes": target.stat().st_size}, started)
    entries = []
    for p in sorted(target.iterdir()):
        try:
            st = p.stat()
            entries.append({
                "name": p.name,
                "is_dir": p.is_dir(),
                "size_bytes": st.st_size if p.is_file() else None,
            })
        except Exception:
            pass
    return _ok("ls", {"path": str(target), "entries": entries}, started)


def cmd_cat(inp: dict, started: float) -> dict:
    path = inp.get("path")
    if not path:
        return _err("cat", "missing 'path'", started)
    p = Path(path)
    if not p.exists() or not p.is_file():
        return _err("cat", f"not a file: {p}", started)
    max_bytes = int(inp.get("max_bytes", 256_000))
    raw = p.read_bytes()[:max_bytes]
    # Try utf-8 decode; fall back to base64 for binary
    try:
        text = raw.decode("utf-8")
        return _ok("cat", {"path": str(p), "size_bytes": p.stat().st_size,
                           "truncated": p.stat().st_size > max_bytes,
                           "text": text}, started)
    except UnicodeDecodeError:
        return _ok("cat", {"path": str(p), "size_bytes": p.stat().st_size,
                           "truncated": p.stat().st_size > max_bytes,
                           "base64": base64.b64encode(raw).decode("ascii")}, started)


def cmd_download_model(inp: dict, started: float) -> dict:
    """Download a model variant from HuggingFace into pretrained_models/."""
    repo_id = inp.get("repo_id", "3DAIGC/LHM-500M-HF")
    from huggingface_hub import snapshot_download
    try:
        local = snapshot_download(repo_id=repo_id, cache_dir=str(MODELS_DIR))
    except Exception as e:
        return _err("download_model", f"snapshot_download failed: {e}", started,
                    extra={"repo_id": repo_id})
    return _ok("download_model", {"repo_id": repo_id, "local_path": local}, started)


def _run_inference_cli(
    model_name: str,
    image_input: Path,
    motion_seqs_dir: Path | None,
    export_video: bool,
    export_mesh: bool,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess:
    """Invoke LHM's CLI inference. Mirrors inference.sh / inference_mesh.sh."""
    cmd = [
        sys.executable, "-m", "LHM.launch", "infer.human_lrm",
        f"model_name={model_name}",
        f"image_input={image_input}",
        f"export_video={'True' if export_video else 'False'}",
        f"export_mesh={'True' if export_mesh else 'False'}",
        f"motion_seqs_dir={motion_seqs_dir if motion_seqs_dir else 'None'}",
        "motion_img_dir=None",
        "vis_motion=true",
        "motion_img_need_mask=true",
        "render_fps=30",
        "motion_video_read_fps=30",
    ]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(
        cmd, cwd=str(LHM_ROOT), capture_output=True, text=True, timeout=1500,
    )


def _common_inference(
    inp: dict, started: float, command: str, export_video: bool, export_mesh: bool
) -> dict:
    """Shared body for inference / inference_mesh."""
    model_name = inp.get("model_name", DEFAULT_MODEL)
    image_url = inp.get("image_url")
    if not image_url:
        return _err(command, "missing 'image_url'", started)
    motion_seqs_dir = inp.get("motion_seqs_dir") or str(MOTION_DEFAULT)
    extra_args = inp.get("extra_args") or []

    # First-call-on-this-worker bootstrap. No-op if already done.
    try:
        _ensure_lhm_data()
    except Exception as e:
        return _err(command, f"LHM data bootstrap failed: {e}", started)

    with tempfile.TemporaryDirectory(prefix="lhm_input_") as tmp:
        tmp_path = Path(tmp)
        # Download input image. LHM accepts an image OR a folder; we always
        # write into a folder for consistency.
        image_dir = tmp_path / "input_images"
        image_dir.mkdir()
        img_path = image_dir / "input.png"
        try:
            _download_to(img_path, image_url)
        except Exception as e:
            return _err(command, f"failed to download image: {e}", started)

        try:
            proc = _run_inference_cli(
                model_name=model_name,
                image_input=image_dir,
                motion_seqs_dir=Path(motion_seqs_dir) if motion_seqs_dir != "None" else None,
                export_video=export_video,
                export_mesh=export_mesh,
                extra_args=extra_args,
            )
        except subprocess.TimeoutExpired:
            return _err(command, "LHM inference timed out (>25 min)", started)
        except Exception as e:
            return _err(command, f"LHM inference crashed: {e}", started)

        # Discover output artifacts. LHM writes under exps/* by default. We
        # collect everything written in the last 10 minutes under exps/.
        exps_dir = LHM_ROOT / "exps"
        artifacts: list[dict] = []
        if exps_dir.exists():
            # Walk and collect all files created recently
            cutoff = started - 5
            for path in exps_dir.rglob("*"):
                try:
                    if path.is_file() and path.stat().st_mtime >= cutoff:
                        rel = path.relative_to(exps_dir)
                        artifacts.append(
                            _collect_artifact(path, f"runs/{int(started)}/{rel.parent}")
                        )
                except Exception:
                    pass

        result = {
            "model_name": model_name,
            "image_url": image_url,
            "motion_seqs_dir": str(motion_seqs_dir),
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-3000:] if proc.stdout else "",
            "stderr_tail": proc.stderr[-3000:] if proc.stderr else "",
            "artifacts": artifacts,
        }
        if proc.returncode != 0:
            return _err(command, f"LHM exit {proc.returncode}", started, extra=result)
        return _ok(command, result, started)


def cmd_inference(inp: dict, started: float) -> dict:
    return _common_inference(inp, started, "inference",
                             export_video=inp.get("export_video", True),
                             export_mesh=inp.get("export_mesh", False))


def cmd_inference_mesh(inp: dict, started: float) -> dict:
    return _common_inference(inp, started, "inference_mesh",
                             export_video=False, export_mesh=True)


def cmd_init(_inp: dict, started: float) -> dict:
    """Pre-download + extract LHM data tarballs. Call once per worker after
    deploy to avoid paying the ~5-min cost on the first inference request."""
    log: list[str] = []
    try:
        _ensure_lhm_data(log=log)
    except Exception as e:
        return _err("init", str(e), started, extra={"log": log})
    return _ok("init", {"log": log, "data_files": [d["name"] for d in DATA_FILES]}, started)


def cmd_shell(inp: dict, started: float) -> dict:
    """Run arbitrary bash. DEV ONLY. Gated by LHM_ALLOW_SHELL=1 env."""
    if not ALLOW_SHELL:
        return _err("shell", "shell disabled (set LHM_ALLOW_SHELL=1 to enable)", started)
    cmd = inp.get("cmd")
    if not cmd:
        return _err("shell", "missing 'cmd'", started)
    timeout = int(inp.get("timeout", 120))
    try:
        proc = subprocess.run(
            ["bash", "-lc", cmd], capture_output=True, text=True,
            timeout=timeout, cwd=str(LHM_ROOT),
        )
    except subprocess.TimeoutExpired:
        return _err("shell", f"command timed out after {timeout}s", started)
    return _ok("shell", {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-50_000:],
        "stderr": proc.stderr[-50_000:],
    }, started)


# ---------------------------------------------------------------------------
# SMPL-X avatar command (Phase 0 contract)
# ---------------------------------------------------------------------------
# Builds the 5-artifact avatar bundle from a single photo:
#   body_apose.obj        - SMPL-X 10,475 verts, A-pose, mm
#   smplx_params.npz      - betas, pose, expr (canonical inputs)
#   avatar_textured.glb   - SMPL-X mesh with per-vertex face-median skin color
#   skin_texture.png      - 4x4 PNG of the face-median RGB
#   splats.ply            - LHM's 20K Gaussian splats (bonus rendering)
#
# Architecture per project memory:
# - 4DHumans pipeline stays untouched. This endpoint produces ONLY photoreal
#   avatar artifacts. No measurements; drape keeps using 4DHumans SMPL.
# - We instantiate HumanLRMInferrer once per worker (cached) to reuse its
#   pose_estimator + LHM model loader for the splat output. Setting sys.argv
#   before construction satisfies LHM's parse_configs() argparse.
# - SMPL-X mesh is built directly via the `smplx` package (NOT via LHM's
#   get_neutral_pose_human, which returns the Chinese "大 pose" / star pose).
#   A-pose is built by rotating each shoulder ~45 deg around Z.
# - Per-vertex color (not UV+texture) for skin. UVs are deferred to Phase 1
#   when we add region-specific texturing (face vs torso vs limbs).
APOSE_SHOULDER_RAD = 45.0 * 3.141592653589793 / 180.0  # 45 deg in radians

# Cached singletons; built lazily on first cmd_avatar call. Survive across
# invocations on the same worker, die when the worker shuts down.
#
# 2026-05-20 pivot: we no longer instantiate the full HumanLRMInferrer because
# it transitively imports gs_renderer.py which hard-imports diff_gaussian_-
# rasterization at module load. We strip that dep from the image to fit the
# 30-min build cap. PoseEstimator and FaceDetector are usable standalone with
# only torch + torchvision + einops + roma. Same model weights, same outputs,
# fraction of the import graph.
_POSE_ESTIMATOR = None
_FACE_DETECTOR = None


def _get_pose_estimator():
    """Lazy PoseEstimator singleton. Loads multiHMR_896_L.pt via
    engine.pose_estimation.pose_estimator.PoseEstimator. Returns the
    estimator. Raises on construction failure.

    Paths inside PoseEstimator are relative to cwd; we chdir into LHM_ROOT
    once and stay there for the worker's lifetime (matches the LHM CLI's
    cwd assumption).
    """
    global _POSE_ESTIMATOR
    if _POSE_ESTIMATOR is not None:
        return _POSE_ESTIMATOR
    sys.path.insert(0, str(LHM_ROOT))
    os.chdir(str(LHM_ROOT))
    from engine.pose_estimation.pose_estimator import PoseEstimator
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    _POSE_ESTIMATOR = PoseEstimator(
        "./pretrained_models/human_model_files/", device=device,
    )
    return _POSE_ESTIMATOR


def _get_face_detector():
    """Lazy FaceDetector singleton. Loads vgg_heads_l.trcd for head bbox
    detection. Used to crop the face region for skin-color sampling.
    Returns the detector. Raises on construction failure.
    """
    global _FACE_DETECTOR
    if _FACE_DETECTOR is not None:
        return _FACE_DETECTOR
    sys.path.insert(0, str(LHM_ROOT))
    os.chdir(str(LHM_ROOT))
    from LHM.utils.face_detector import FaceDetector
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    _FACE_DETECTOR = FaceDetector(
        model_path="./pretrained_models/gagatracker/vgghead/vgg_heads_l.trcd",
        device=device,
    )
    return _FACE_DETECTOR


def _build_apose_body_pose(device, dtype):
    """Build the SMPL-X body_pose tensor for canonical A-pose.

    SMPL-X body_pose shape: [1, 21, 3] axis-angle. body_pose [0..20] = joints 1..21.
    Shoulders: body_pose[15] = L_Shoulder, body_pose[16] = R_Shoulder.

    SMPL-X T-pose convention:
      L arm points in +X (model's left, viewer's right when facing model)
      R arm points in -X (model's right, viewer's left)

    Rotation around Z (right-hand rule, thumb in +Z = out of model's chest):
      L_Shoulder NEGATIVE Z: +X rotates toward -Y. Arm goes DOWN. ✓
      R_Shoulder POSITIVE Z: -X rotates toward -Y. Arm goes DOWN. ✓

    Previously had signs reversed which produced a Y-pose (arms up).
    """
    import torch
    body_pose = torch.zeros((1, 21, 3), dtype=dtype, device=device)
    body_pose[0, 15, 2] = -APOSE_SHOULDER_RAD  # L_Shoulder rot Z: arm down
    body_pose[0, 16, 2] = +APOSE_SHOULDER_RAD  # R_Shoulder rot Z: arm down
    return body_pose


def _build_smplx_mesh_pair(beta_np, gender: str, device):
    """Forward-pass the SMPL-X layer for both T-pose and A-pose.

    T-pose verts match the coordinate frame LHM emits its splats in (zero
    body pose), so we sample splat colors against the T-pose mesh. The
    A-pose verts use the same betas but with A-pose shoulders, used for
    the final GLB / OBJ artifacts (drape-friendly canonical pose).

    Returns (verts_apose_m, verts_tpose_m, faces, smplx_params).
    """
    import torch
    import numpy as np
    import smplx

    smplx_dir = str(LHM_ROOT / "pretrained_models" / "human_model_files")
    layer = smplx.create(
        smplx_dir,
        model_type="smplx",
        gender=gender,
        use_pca=False,
        flat_hand_mean=True,
        num_betas=beta_np.shape[-1],
    ).to(device).eval()

    dtype = torch.float32
    betas = torch.from_numpy(np.asarray(beta_np)).reshape(1, -1).to(device=device, dtype=dtype)
    body_pose_apose = _build_apose_body_pose(device=device, dtype=dtype)
    body_pose_tpose = torch.zeros((1, 21, 3), dtype=dtype, device=device)

    with torch.no_grad():
        out_a = layer(betas=betas, body_pose=body_pose_apose, return_verts=True)
        out_t = layer(betas=betas, body_pose=body_pose_tpose, return_verts=True)

    verts_apose_m = out_a.vertices[0].detach().cpu().numpy()  # meters
    verts_tpose_m = out_t.vertices[0].detach().cpu().numpy()  # meters
    faces = layer.faces.astype("int32")

    smplx_params = {
        "betas": betas.cpu().numpy()[0],
        "body_pose": body_pose_apose.cpu().numpy()[0],
        "global_orient": np.zeros(3, dtype="float32"),
        "jaw_pose": np.zeros(3, dtype="float32"),
        "leye_pose": np.zeros(3, dtype="float32"),
        "reye_pose": np.zeros(3, dtype="float32"),
        "left_hand_pose": np.zeros((15, 3), dtype="float32"),
        "right_hand_pose": np.zeros((15, 3), dtype="float32"),
        "expression": np.zeros(10, dtype="float32"),
        "gender": gender,
        "pose_convention": f"a_pose_shoulder_z_{APOSE_SHOULDER_RAD:.4f}rad",
        "units": "mm",
    }
    return verts_apose_m, verts_tpose_m, faces, smplx_params


def _load_splat_colors(ply_path):
    """Read a 3D Gaussian Splat PLY file, return (positions [N,3] float32,
    rgb [N,3] uint8). LHM emits DC-only spherical harmonics (f_dc_0/1/2),
    converted to sRGB via the standard SH_C0 = 1/(2*sqrt(pi)) factor:
        rgb = clamp(0.5 + 0.28209479 * f_dc, 0, 1)
    """
    import numpy as np

    with open(ply_path, "rb") as f:
        # Read header line-by-line
        properties = []
        n_verts = 0
        line = b""
        while True:
            line = f.readline()
            if not line:
                raise RuntimeError(f"premature EOF in PLY header: {ply_path}")
            ls = line.decode("ascii", errors="replace").strip()
            if ls.startswith("element vertex"):
                n_verts = int(ls.split()[-1])
            elif ls.startswith("property "):
                # property float NAME
                parts = ls.split()
                if len(parts) >= 3 and parts[1] in ("float", "float32"):
                    properties.append(parts[2])
            elif ls == "end_header":
                break

        # Read binary payload
        rec_count = len(properties)
        raw = np.frombuffer(f.read(n_verts * rec_count * 4), dtype="<f4")
        if raw.size != n_verts * rec_count:
            raise RuntimeError(
                f"PLY payload size mismatch: got {raw.size} floats, expected "
                f"{n_verts}*{rec_count}={n_verts*rec_count}"
            )
        arr = raw.reshape(n_verts, rec_count)

    idx_x = properties.index("x")
    idx_y = properties.index("y")
    idx_z = properties.index("z")
    idx_r = properties.index("f_dc_0")
    idx_g = properties.index("f_dc_1")
    idx_b = properties.index("f_dc_2")

    positions = arr[:, [idx_x, idx_y, idx_z]].astype("float32")
    SH_C0 = 0.28209479177387814  # 1 / (2 * sqrt(pi))
    rgb_f = np.clip(0.5 + SH_C0 * arr[:, [idx_r, idx_g, idx_b]], 0.0, 1.0)
    rgb_u8 = (rgb_f * 255.0).astype("uint8")
    return positions, rgb_u8


def _classify_splats(splat_pos, splat_rgb, face_median_rgb, scalp_y,
                     skin_rgb_threshold: float = 45.0):
    """Classify each splat as skin / hair / other based on color + position.

    skin: RGB euclidean distance to face-crop median color < threshold.
    hair: above the SMPL-X scalp top in Y AND not skin-classified.
    other: clothing, shadows, background residue.

    Returns (skin_mask, hair_mask) boolean arrays of length N_splats.
    """
    import numpy as np
    face = np.asarray(face_median_rgb, dtype=np.float32)
    color_dist = np.linalg.norm(splat_rgb.astype(np.float32) - face, axis=1)
    skin_mask = color_dist < skin_rgb_threshold
    # Hair: above the SMPL-X scalp top (so we exclude splats embedded INSIDE
    # the scalp itself; only ones that extend ABOVE the bald skull are hair).
    # A small (~2cm) margin below the scalp top catches hair attached to it.
    hair_mask = (splat_pos[:, 1] > (scalp_y - 0.02)) & (~skin_mask)
    return skin_mask, hair_mask


def _classify_smplx_vert_regions(verts_tpose_m):
    """Region-classify SMPL-X T-pose verts by position. Returns 3 boolean masks
    summing to all verts: scalp, face, body.

    scalp: top ~3.5cm of head Y range (where hair would be).
    face:  next ~12cm below scalp, with z > 0 (front of head, i.e. facial).
    body:  everything else (neck, torso, arms, legs, hands, feet, back of head).

    Position-based heuristic. Coarse but works for canonical SMPL-X topology.
    """
    import numpy as np
    y = verts_tpose_m[:, 1]
    z = verts_tpose_m[:, 2]
    y_max = float(y.max())
    scalp_mask = y > (y_max - 0.035)  # top 3.5cm
    face_mask = (
        (y <= (y_max - 0.035)) &
        (y > (y_max - 0.16)) &  # face roughly 12cm tall
        (z > 0.04)              # front-of-head (Z>0 is forward in SMPL-X)
    )
    body_mask = ~(scalp_mask | face_mask)
    return scalp_mask, face_mask, body_mask


def _vertex_colors_region_aware(verts_tpose_m, splat_pos, splat_rgb,
                                face_median_rgb, k: int = 5,
                                splat_skin_mask=None, splat_hair_mask=None):
    """Per-region color sampling:
    - body  verts <- K nearest SKIN-class splats (clean skin tone)
    - scalp verts <- K nearest HAIR-class splats (preserves hair color)
    - face  verts <- K nearest of ALL splats (preserves eye / lip / beard
                     features)

    Falls back to all splats for a region if its dedicated pool is empty
    (e.g. bald subject -> no hair splats, scalp verts use all splats).

    splat_skin_mask / splat_hair_mask: optional precomputed classification.
    If not provided, classifies internally (preserves backwards compat).

    Returns (vertex_colors [N, 3] uint8, diag_median_rgb, classification_stats,
             hair_splat_mask).
    """
    import numpy as np
    from scipy.spatial import cKDTree

    scalp_v, face_v, body_v = _classify_smplx_vert_regions(verts_tpose_m)
    scalp_y_top = float(verts_tpose_m[:, 1].max())

    if splat_skin_mask is None or splat_hair_mask is None:
        splat_skin_mask, splat_hair_mask = _classify_splats(
            splat_pos=splat_pos,
            splat_rgb=splat_rgb,
            face_median_rgb=face_median_rgb,
            scalp_y=scalp_y_top,
        )
    skin_splat_mask = splat_skin_mask
    hair_splat_mask = splat_hair_mask

    def _pool(pos_mask):
        if pos_mask.any():
            return splat_pos[pos_mask], splat_rgb[pos_mask]
        return splat_pos, splat_rgb  # fall back to all

    skin_pos, skin_rgb_pool = _pool(skin_splat_mask)
    hair_pos, hair_rgb_pool = _pool(hair_splat_mask)
    all_pos, all_rgb_pool = splat_pos, splat_rgb

    N = verts_tpose_m.shape[0]
    vertex_colors = np.zeros((N, 3), dtype=np.uint8)

    for vert_mask, pool_pos, pool_rgb in [
        (body_v, skin_pos, skin_rgb_pool),
        (scalp_v, hair_pos, hair_rgb_pool),
        (face_v, all_pos, all_rgb_pool),
    ]:
        if not vert_mask.any():
            continue
        tree = cKDTree(pool_pos)
        k_eff = min(k, pool_pos.shape[0])
        queries = verts_tpose_m[vert_mask]
        dists, idxs = tree.query(queries, k=k_eff)
        if k_eff == 1:
            dists = dists[:, None]
            idxs = idxs[:, None]
        eps = 1e-6
        weights = 1.0 / (dists + eps)
        weights = weights / weights.sum(axis=1, keepdims=True)
        sampled = pool_rgb[idxs].astype(np.float32)
        blended = (sampled * weights[..., None]).sum(axis=1)
        vertex_colors[vert_mask] = np.clip(blended, 0, 255).astype(np.uint8)

    median_rgb = np.median(vertex_colors, axis=0).astype(np.uint8)
    stats = {
        "splats_total": int(splat_pos.shape[0]),
        "splats_skin": int(skin_splat_mask.sum()),
        "splats_hair": int(hair_splat_mask.sum()),
        "verts_scalp": int(scalp_v.sum()),
        "verts_face":  int(face_v.sum()),
        "verts_body":  int(body_v.sum()),
        "scalp_y_top_m": round(scalp_y_top, 4),
    }
    return (
        vertex_colors,
        (int(median_rgb[0]), int(median_rgb[1]), int(median_rgb[2])),
        stats,
        hair_splat_mask,  # passed back so cmd_avatar can write hair.ply
    )


def _load_smplx_uv_obj(obj_path):
    """Parse SMPL-X UV layout OBJ. Returns
    (vt [N_uv, 2], faces_v [F, 3], faces_vt [F, 3]).

    Expected file structure (Blender-exported smplx_uv.obj from LHM tarball):
      - 10,475 'v' lines (canonical SMPL-X 3D positions, ignored, we use our
        beta-deformed verts instead),
      - 11,313 'vt' lines (UV coords in [0, 1], more than 10475 due to seam
        duplication on the UV unwrap),
      - 20,908 'f' lines in 'v_idx/vt_idx' format.
    """
    import numpy as np
    vt_list = []
    fv_list = []
    fvt_list = []
    with open(obj_path) as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("vt "):
                parts = line.split()
                vt_list.append([float(parts[1]), float(parts[2])])
            elif line.startswith("f "):
                parts = line.split()[1:]
                if len(parts) != 3:
                    continue
                v_idx, vt_idx = [], []
                for p in parts:
                    sub = p.split("/")
                    v_idx.append(int(sub[0]) - 1)
                    if len(sub) > 1 and sub[1]:
                        vt_idx.append(int(sub[1]) - 1)
                if len(v_idx) == 3 and len(vt_idx) == 3:
                    fv_list.append(v_idx)
                    fvt_list.append(vt_idx)
    return (
        np.array(vt_list, dtype=np.float32),
        np.array(fv_list, dtype=np.int32),
        np.array(fvt_list, dtype=np.int32),
    )


def _bake_uv_diffuse_texture(
    verts_tpose_m,
    faces_v,
    vt,
    faces_vt,
    splat_pos,
    splat_rgb,
    splat_skin_mask,
    splat_hair_mask,
    texture_size=1024,
    k=5,
):
    """Tier 3a: bake a 1024x1024 diffuse PBR texture by per-texel splat sampling.

    Pipeline:
      1. Rasterize the SMPL-X UV layout via pytorch3d's MeshRasterizer using
         an orthographic top-down camera. Output: per-pixel (face_id,
         barycentric).
      2. For each valid texel, interpolate the 3D position using the
         corresponding 3D V-indices (NOT the VT-indices; the seam-duplicated
         UV verts share a single 3D position per V-vert).
      3. Classify the interpolated 3D point into scalp / face / body region
         using the same heuristic as _classify_smplx_vert_regions.
      4. Sample from the appropriate splat pool (skin for body, hair for
         scalp, all-splats for face) via KD-tree (K=5 inverse-distance).
      5. Write to texture, flip Y (pytorch3d render Y-up vs image Y-down).

    Returns (texture_rgb [H, W, 3] uint8, valid_mask [H, W] bool, coverage_pct).
    """
    import numpy as np
    import torch
    from pytorch3d.renderer import (
        MeshRasterizer, RasterizationSettings, FoVOrthographicCameras,
    )
    from pytorch3d.structures import Meshes
    from scipy.spatial import cKDTree

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # UV in [0,1] -> NDC [-1,1]. Embed in 3D at z=0.
    vt_ndc = np.zeros((vt.shape[0], 3), dtype=np.float32)
    vt_ndc[:, 0] = vt[:, 0] * 2.0 - 1.0
    vt_ndc[:, 1] = vt[:, 1] * 2.0 - 1.0

    mesh = Meshes(
        verts=[torch.from_numpy(vt_ndc).to(device)],
        faces=[torch.from_numpy(faces_vt).long().to(device)],
    )

    cameras = FoVOrthographicCameras(
        device=device,
        znear=0.01,
        zfar=10.0,
        min_x=-1.0, max_x=1.0, min_y=-1.0, max_y=1.0,
        R=torch.eye(3, device=device)[None],
        T=torch.tensor([[0.0, 0.0, 2.0]], device=device),
    )

    raster_settings = RasterizationSettings(
        image_size=texture_size,
        blur_radius=0.0,
        faces_per_pixel=1,
        perspective_correct=False,
        cull_backfaces=False,
    )
    rasterizer = MeshRasterizer(cameras=cameras, raster_settings=raster_settings)

    with torch.no_grad():
        fragments = rasterizer(mesh)
    pix_to_face = fragments.pix_to_face[0, ..., 0].cpu().numpy()
    bary = fragments.bary_coords[0, ..., 0, :].cpu().numpy()

    H = W = texture_size
    texture = np.zeros((H, W, 3), dtype=np.uint8)
    valid_mask = (pix_to_face >= 0)
    ys, xs = np.where(valid_mask)
    if ys.size == 0:
        return texture, valid_mask, 0.0

    tri_ids = pix_to_face[ys, xs]
    bary_pix = bary[ys, xs]

    # Interpolate 3D position via V-indices
    tri_v = faces_v[tri_ids]                   # [M, 3]
    tri_verts = verts_tpose_m[tri_v]           # [M, 3, 3]
    pixels_3d = (tri_verts * bary_pix[..., None]).sum(axis=1)  # [M, 3]

    # Region classification per pixel (matches _classify_smplx_vert_regions)
    y_max = float(verts_tpose_m[:, 1].max())
    pix_y = pixels_3d[:, 1]
    pix_z = pixels_3d[:, 2]
    pix_scalp = pix_y > (y_max - 0.035)
    pix_face = (
        (pix_y <= (y_max - 0.035))
        & (pix_y > (y_max - 0.16))
        & (pix_z > 0.04)
    )
    pix_body = ~(pix_scalp | pix_face)

    # Sampling pools
    def _pool(mask):
        if mask.any():
            return splat_pos[mask], splat_rgb[mask]
        return splat_pos, splat_rgb

    skin_p, skin_c = _pool(splat_skin_mask)
    hair_p, hair_c = _pool(splat_hair_mask)
    all_p, all_c = splat_pos, splat_rgb

    def _knn_blend(tree, rgb_pool, pts, k):
        if pts.shape[0] == 0:
            return np.zeros((0, 3), dtype=np.uint8)
        k_eff = min(k, rgb_pool.shape[0])
        d, idx = tree.query(pts, k=k_eff)
        if k_eff == 1:
            d = d[:, None]; idx = idx[:, None]
        w = 1.0 / (d + 1e-6)
        w = w / w.sum(axis=1, keepdims=True)
        s = rgb_pool[idx].astype(np.float32)
        return np.clip((s * w[..., None]).sum(axis=1), 0, 255).astype(np.uint8)

    skin_tree = cKDTree(skin_p)
    hair_tree = cKDTree(hair_p)
    all_tree = cKDTree(all_p)

    colors_out = np.zeros((ys.shape[0], 3), dtype=np.uint8)
    colors_out[pix_body] = _knn_blend(skin_tree, skin_c, pixels_3d[pix_body], k)
    colors_out[pix_scalp] = _knn_blend(hair_tree, hair_c, pixels_3d[pix_scalp], k)
    colors_out[pix_face] = _knn_blend(all_tree, all_c, pixels_3d[pix_face], k)

    texture[ys, xs] = colors_out
    # Y-flip so the GLB renders right-side-up (pytorch3d Y-up, image Y-down)
    texture = np.flipud(texture).copy()

    coverage = float(valid_mask.sum()) / float(H * W) * 100.0
    return texture, valid_mask, coverage


def _write_glb_with_uv_texture(verts_3d_m, faces_v, vt, faces_vt,
                               texture_rgb, out_path):
    """Write a textured GLB. SMPL-X has 10,475 V verts but 11,313 VT verts
    due to seam duplication. trimesh's TextureVisuals needs verts and UVs
    of the same length, so we expand to a "seamed" mesh: one expanded vert
    per UV vert, each positioned at the 3D location of its corresponding
    V vert.

    Note: image V axis is already flipped by the texture baker so trimesh's
    default V-flip cancels out and the texture maps right side up.
    """
    import numpy as np
    import trimesh
    from PIL import Image

    n_uv = vt.shape[0]
    vt_to_v = np.full(n_uv, -1, dtype=np.int32)
    for f_v, f_vt in zip(faces_v, faces_vt):
        vt_to_v[f_vt[0]] = f_v[0]
        vt_to_v[f_vt[1]] = f_v[1]
        vt_to_v[f_vt[2]] = f_v[2]
    expanded_verts = verts_3d_m[vt_to_v].astype(np.float32)

    image_pil = Image.fromarray(texture_rgb).convert("RGB")
    visual = trimesh.visual.TextureVisuals(uv=vt.astype(np.float32), image=image_pil)
    mesh = trimesh.Trimesh(
        vertices=expanded_verts,
        faces=faces_vt.astype(np.int32),
        visual=visual,
        process=False,
    )
    mesh.export(out_path, file_type="glb")


def _write_hair_splats_ply(src_ply_path, dst_ply_path, hair_mask):
    """Copy just the hair-class splats to a new PLY, preserving LHM's full
    Gaussian splat format (positions + normals + DC SH + opacity + scale +
    rotation) so any 3DGS WebGL viewer can render them as photoreal hair.

    Returns the number of splats written.
    """
    import numpy as np
    with open(src_ply_path, "rb") as f:
        header_lines = []
        while True:
            line = f.readline()
            if not line:
                raise RuntimeError(f"PLY EOF in header: {src_ply_path}")
            header_lines.append(line)
            if line.strip() == b"end_header":
                break
        properties = []
        n_verts = 0
        for line in header_lines:
            s = line.decode("ascii", errors="replace").strip()
            if s.startswith("element vertex"):
                n_verts = int(s.split()[-1])
            elif s.startswith("property "):
                parts = s.split()
                if len(parts) >= 3 and parts[1] in ("float", "float32"):
                    properties.append(parts[2])
        rec_count = len(properties)
        raw = np.frombuffer(f.read(n_verts * rec_count * 4), dtype="<f4")
        arr = raw.reshape(n_verts, rec_count)

    if hair_mask.shape[0] != n_verts:
        raise RuntimeError(
            f"hair_mask shape {hair_mask.shape} != n_verts {n_verts}"
        )
    arr_hair = arr[hair_mask]
    n_hair = arr_hair.shape[0]

    new_header = []
    for line in header_lines:
        s = line.decode("ascii", errors="replace")
        if s.startswith("element vertex"):
            new_header.append(f"element vertex {n_hair}\n".encode())
        else:
            new_header.append(line)

    with open(dst_ply_path, "wb") as f:
        for line in new_header:
            f.write(line)
        f.write(arr_hair.astype("<f4").tobytes())
    return n_hair


def _sample_face_median_color(inferrer, image_path: str) -> tuple:
    """LEGACY: depended on HumanLRMInferrer.crop_face_image. Unused in the
    post-2026-05-20 path. Kept for reference. Use
    _sample_face_median_color_v2(face_detector, ...) instead.
    """
    import numpy as np
    try:
        rgb_face = inferrer.crop_face_image(image_path)
        if rgb_face is None or rgb_face.size == 0:
            raise ValueError("empty face crop")
        h, w = rgb_face.shape[:2]
        cy0, cy1 = h // 4, 3 * h // 4
        cx0, cx1 = w // 4, 3 * w // 4
        central = rgb_face[cy0:cy1, cx0:cx1].reshape(-1, 3)
        if central.shape[0] == 0:
            central = rgb_face.reshape(-1, 3)
        med = np.median(central, axis=0).astype(np.uint8)
        return int(med[0]), int(med[1]), int(med[2])
    except Exception:
        return (210, 175, 145)


def _sample_face_median_color_v2(face_detector, image_path: str,
                                  out_crop_path: Path | None = None) -> tuple:
    """Detect the face in the body photo with LHM's standalone FaceDetector,
    crop it, and return the median skin RGB as (r, g, b) ints.

    Writes the cropped face to `out_crop_path` (PNG) when provided so the
    client can ship a `face_crop.png` artifact mirroring the 4DHumans bundle.

    Skin sampling is on the CENTRAL 50% of the face crop (so we skip hair
    above the brow + background at the edges of the bbox).

    Falls back to a neutral tan (210, 175, 145) on any failure so the
    avatar GLB still ships a complete artifact set.
    """
    import numpy as np
    try:
        if face_detector is None:
            raise RuntimeError("face detector not loaded")
        from PIL import Image
        import torch
        rgb = np.array(Image.open(image_path).convert("RGB"))
        rgb_t = torch.from_numpy(rgb).permute(2, 0, 1)
        bbox = face_detector(rgb_t)
        if bbox is None or len(bbox) < 4:
            raise ValueError("face detector returned no bbox")
        x0, y0, x1, y1 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        H, W = rgb.shape[:2]
        x0 = max(0, min(W - 1, x0))
        x1 = max(x0 + 1, min(W, x1))
        y0 = max(0, min(H - 1, y0))
        y1 = max(y0 + 1, min(H, y1))
        face_rgb = rgb[y0:y1, x0:x1]
        if face_rgb.size == 0:
            raise ValueError("empty face crop")
        if out_crop_path is not None:
            Image.fromarray(face_rgb).save(out_crop_path)
        h, w = face_rgb.shape[:2]
        cy0, cy1 = h // 4, 3 * h // 4
        cx0, cx1 = w // 4, 3 * w // 4
        central = face_rgb[cy0:cy1, cx0:cx1].reshape(-1, 3)
        if central.shape[0] == 0:
            central = face_rgb.reshape(-1, 3)
        med = np.median(central, axis=0).astype(np.uint8)
        return int(med[0]), int(med[1]), int(med[2])
    except Exception as e:
        print(f"[face_median_v2] fallback to neutral tan: {type(e).__name__}: {e}")
        return (210, 175, 145)


def _write_textured_glb(verts_mm, faces, vertex_colors_rgb, glb_path):
    """Write a GLB with per-vertex color. SMPL-X has 10,475 verts.

    vertex_colors_rgb: either an [N, 3] uint8 array (per-vertex colors)
    OR a 3-tuple/list for a single uniform color applied to every vert.
    """
    import numpy as np
    import trimesh
    verts_m = (verts_mm / 1000.0).astype(np.float32)
    n = verts_m.shape[0]
    arr = np.asarray(vertex_colors_rgb)
    if arr.ndim == 1:
        # Uniform color across all verts
        rgba = np.tile(np.array([arr[0], arr[1], arr[2], 255], dtype=np.uint8), (n, 1))
    else:
        # Per-vertex colors, [N, 3] -> [N, 4] with alpha 255
        rgba = np.concatenate([arr.astype(np.uint8), np.full((n, 1), 255, dtype=np.uint8)], axis=1)
    mesh = trimesh.Trimesh(
        vertices=verts_m,
        faces=faces,
        vertex_colors=rgba,
        process=False,
    )
    mesh.export(glb_path, file_type="glb")


def _write_obj_no_mtl(verts_mm, faces, obj_path):
    """Write a plain SMPL-X OBJ in mm with no MTL. Geometry only."""
    with open(obj_path, "w") as f:
        f.write("# SMPL-X A-pose, mm\n")
        for v in verts_mm:
            f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")
        for tri in faces:
            f.write(f"f {tri[0]+1} {tri[1]+1} {tri[2]+1}\n")


def _write_skin_texture_png(rgb, png_path, size: int = 4):
    """Write a tiny PNG of the skin color for future region-texturing pipelines."""
    import numpy as np
    from PIL import Image
    arr = np.tile(np.array([rgb[0], rgb[1], rgb[2]], dtype=np.uint8), (size, size, 1))
    Image.fromarray(arr).save(png_path)


# ---------------------------------------------------------------------------
# SMPL-Anthropometry measurements (DavidBoja/SMPL-Anthropometry)
# ---------------------------------------------------------------------------
# Same package the 4DHumans pipeline uses. Takes a [10475, 3] SMPL-X T-pose
# mesh (in meters), returns 17 raw measurements in cm; standardized via the
# same MEASUREMENT_MAPPING dict the production handler uses (16 unique API
# keys matching STANDARD_LABELS A-P). Height-normalized to the user-supplied
# height so LHM's beta-only scale gets calibrated to the real human.

ANTHROPOMETRY_ROOT = Path("/workspace/anthropometry")
_MEASURER = None

# Vendored from main:avatar-creation/pipelines/handler.py to preserve the
# exact API contract that the rest of the stack (backend size recommendation
# v2, dashboard) expects. Both arms map to the same `arm_length` key with
# first-set-wins semantics.
MEASUREMENT_MAPPING = {
    "height": "height",
    "chest circumference": "chest",
    "waist circumference": "waist",
    "hip circumference": "hips",
    "hip circumference max height": "hips",
    "inside leg height": "inseam",
    "shoulder breadth": "shoulder_width",
    "arm left length": "arm_length",
    "arm right length": "arm_length",
    "arm length (shoulder to elbow)": "arm_length",
    "arm length (spine to wrist)": "arm_length",
    "neck circumference": "neck",
    "thigh left circumference": "thigh",
    "thigh right circumference": "thigh",
    "shoulder to crotch height": "torso_length",
    "crotch height": "crotch_height",
    "bicep right circumference": "bicep",
    "forearm right circumference": "forearm",
    "wrist right circumference": "wrist",
    "calf left circumference": "calf",
    "ankle left circumference": "ankle",
    "head circumference": "head",
}


def _standardize_measurements(raw: dict) -> dict:
    """Convert SMPL-Anthropometry raw measurement names to the API short
    keys the rest of the stack (size rec v2, dashboard) consumes. First
    match wins (so arm_left then arm_right -> arm_left value chosen,
    matching production behaviour)."""
    out = {}
    for name, value in raw.items():
        key = name.lower()
        mapped = MEASUREMENT_MAPPING.get(key)
        if mapped is None:
            for k, m in MEASUREMENT_MAPPING.items():
                if k in key or key in k:
                    mapped = m
                    break
        if mapped is None:
            continue
        if mapped in out:
            continue
        try:
            out[mapped] = round(float(value), 1)
        except (ValueError, TypeError):
            continue
    return out


def _get_measurer():
    """Lazy MeasureSMPLX singleton. Symlinks LHM's baked SMPL-X .npz files
    into the anthropometry data dir on first call so the upstream class
    (which expects data/smplx/SMPLX_<GENDER>.npz relative to its own root)
    resolves. ~100ms one-time cost."""
    global _MEASURER
    if _MEASURER is not None:
        return _MEASURER

    _deca_numpy_shim()  # SMPL-Anthropometry also reaches for np.bool / np.int

    # Symlink LHM's SMPL-X .npz files into the anthropometry data dir so the
    # upstream MeasureSMPLX __init__ (which loads `data/smplx/SMPLX_NEUTRAL.npz`
    # relative to cwd == anthropometry root) finds them. Idempotent across
    # worker restarts.
    smplx_src = LHM_ROOT / "pretrained_models" / "human_model_files" / "smplx"
    smplx_dst = ANTHROPOMETRY_ROOT / "data" / "smplx"
    smplx_dst.mkdir(parents=True, exist_ok=True)
    for g in ("NEUTRAL", "MALE", "FEMALE"):
        src = smplx_src / f"SMPLX_{g}.npz"
        dst = smplx_dst / f"SMPLX_{g}.npz"
        if src.exists() and not dst.exists() and not dst.is_symlink():
            try:
                dst.symlink_to(src)
            except OSError:
                # Symlink may fail on certain volumes; fall back to copy.
                shutil.copy(src, dst)

    import sys
    if str(ANTHROPOMETRY_ROOT) not in sys.path:
        sys.path.insert(0, str(ANTHROPOMETRY_ROOT))

    prev = os.getcwd()
    try:
        os.chdir(str(ANTHROPOMETRY_ROOT))
        from measure import MeasureBody
        _MEASURER = MeasureBody("smplx")
    finally:
        os.chdir(prev)
    return _MEASURER


def _compute_measurements(verts_tpose_m, height_cm, gender):
    """Run SMPL-Anthropometry on a T-pose SMPL-X mesh.

    Args:
      verts_tpose_m: numpy [10475, 3] in meters, T-pose
      height_cm: user's actual height in cm (used for proportional scaling;
                 raw measurements are intrinsic-beta-scale until normalized)
      gender: "neutral" | "male" | "female"

    Returns:
      dict with keys:
        raw_cm: {raw_name: cm float}, 17 entries
        standardized_cm: {api_short_name: cm float}, 16 entries
        labeled_cm: {A-P: cm float}, 16 entries
        intrinsic_height_cm: SMPL-X height before normalization
        normalization_factor: ratio applied to scale-to-target
        input_height_cm: echo of input
        input_gender: echo of input
    """
    import torch
    measurer = _get_measurer()

    verts_t = torch.from_numpy(verts_tpose_m.astype("float32"))

    # Reset measurer state in case this isn't the first call this worker
    measurer.verts = None
    measurer.joints = None
    measurer.measurements = {}
    measurer.height_normalized_measurements = {}
    measurer.labeled_measurements = {}
    measurer.height_normalized_labeled_measurements = {}

    prev = os.getcwd()
    try:
        os.chdir(str(ANTHROPOMETRY_ROOT))
        measurer.from_verts(verts_t)
        measurer.measure(measurer.all_possible_measurements)

        raw_intrinsic = {k: float(v) for k, v in measurer.measurements.items()}
        intrinsic_h = float(measurer.measurements.get("height", 0.0))

        # Height-normalize: all measurements scaled by target/intrinsic
        if height_cm and intrinsic_h > 1e-3:
            measurer.height_normalize_measurements(height_cm)
            norm = float(height_cm) / intrinsic_h
            measurements_cm = {
                k: float(v) for k, v in measurer.height_normalized_measurements.items()
            }
        else:
            norm = 1.0
            measurements_cm = raw_intrinsic

        # Standard A-P labels via measurer's label_measurements (writes
        # height_normalized_labeled_measurements when normalized_measurements
        # is populated).
        labeled = {}
        try:
            from measurement_definitions import STANDARD_LABELS
            measurer.label_measurements(STANDARD_LABELS)
            src = (
                measurer.height_normalized_labeled_measurements
                if measurer.height_normalized_labeled_measurements
                else measurer.labeled_measurements
            )
            labeled = {k: float(v) for k, v in src.items()}
        except Exception:
            pass

        standardized = _standardize_measurements(measurements_cm)
        if height_cm:
            standardized["height"] = float(round(float(height_cm), 1))

        return {
            "raw_cm": {k: round(v, 2) for k, v in measurements_cm.items()},
            "standardized_cm": standardized,
            "labeled_cm": {k: round(v, 2) for k, v in labeled.items()},
            "intrinsic_height_cm": round(intrinsic_h, 2),
            "normalization_factor": round(norm, 4),
            "input_height_cm": height_cm,
            "input_gender": gender,
        }
    finally:
        os.chdir(prev)


# ---------------------------------------------------------------------------
# DECA face mapping (selfie -> SMPL-X face region)
# ---------------------------------------------------------------------------
# Selfie -> identity-preserving SMPL-X face via DECA + Javisda/smplx-deca
# (vendored at /workspace/smplx-deca by the Dockerfile). The pipeline matches
# Javisda's demo_build_body.py for a single identity photo, no expression
# transfer:
#   1. DECA encode(selfie) -> FLAME shape/exp/pose codes + UV face albedo
#   2. Zero out exp + pose, re-decode -> neutral-pose FLAME head
#   3. transfer_texture_information: paste UV albedo from posed onto neutral
#   4. 4-pair head alignment chain (DECA-head -> DECA-neutral -> SMPLX-neutral
#      -> SMPLX-with-our-betas) accumulating per-vertex offsets via gradient
#      descent on the gravity-center
#   5. Apply offset to SMPL-X v_template[head_idxs] + neck/head smoothing
#   6. Tint the static SMPL-X body albedo PNG by the LHM-derived skin RGB,
#      then merge side-by-side with DECA's face PNG into one 8192x4096 texture
#   7. Write GLB using the smplx-addon.obj UV layout (different from the
#      stock smplx_uv.obj used in Tier 3a)
#
# Vendoring strategy: we inline the small set of utility functions we need
# from smplx-deca/Demos/{utils.py, uv_mixing_utils.py} instead of importing
# them at runtime. That sidesteps three problems with the upstream source:
#   - cwd-relative paths (Neck_masks/, UV_mixing_resources/)
#   - mandatory tensorboard + open3d imports (unused on a headless GPU)
#   - np.float / np.int / np.bool aliases (removed in numpy 1.24+)
# The repo is still required on disk for the binary assets (smplx-addon.obj,
# head_template.obj, smplx_texture_m_alb.png, Neck_masks/smoothing_mask_1).

SMPLX_DECA_ROOT = Path("/workspace/smplx-deca")
SMPLX_DECA_DEMOS = SMPLX_DECA_ROOT / "Demos"
DECA_DATA_DIR = SMPLX_DECA_ROOT / "smplx_deca_main" / "deca" / "data"
SMPLX_FLAME_VERTEX_IDS_PATH = Path("/workspace/SMPL-X__FLAME_vertex_ids.npy")
SMPLX_BODY_ALBEDO_PATH = SMPLX_DECA_DEMOS / "UV_mixing_resources" / "smplx_texture_m_alb.png"
SMPLX_ADDON_OBJ = SMPLX_DECA_DEMOS / "UV_mixing_resources" / "smplx-addon.obj"
FLAME_HEAD_TEMPLATE_OBJ = SMPLX_DECA_DEMOS / "UV_mixing_resources" / "head_template.obj"
NECK_SMOOTHING_MASK = SMPLX_DECA_DEMOS / "Neck_masks" / "smoothing_mask_1"

# DECA model assets are downloaded lazily on first selfie_url call. Total
# ~510 MB; baking them into the image pushed build #79336fb past RunPod's
# 30-min cap during cache export. Same pattern as _ensure_lhm_data: marker
# file gates the (re-)download.
DECA_ASSETS_BASE_URL = (
    "https://huggingface.co/camenduru/show/resolve/main/models/models_deca/data"
)
DECA_ASSET_FILES = [
    ("deca_model.tar", 434),          # MB (approximate sanity sizes)
    ("generic_model.pkl", 53),
    ("fixed_displacement_256.npy", 1),
    ("head_template.obj", 1),
    ("landmark_embedding.npy", 1),
    ("mean_texture.jpg", 1),
    ("texture_data_256.npy", 7),
    ("uv_face_eye_mask.png", 1),
    ("uv_face_mask.png", 1),
]

_DECA = None  # cached singleton built on first cmd_avatar w/ selfie_url


def _ensure_deca_data(log: list[str] | None = None) -> None:
    """Download DECA model assets (~510 MB) to the path DECA's hardcoded
    config (cfg.deca_dir + '/data/') expects. Idempotent via marker file.

    Raises RuntimeError on any download failure so the caller can surface
    `measurements_error` / `deca_error` in the avatar response cleanly.
    """
    DECA_DATA_DIR.mkdir(parents=True, exist_ok=True)
    marker = DECA_DATA_DIR / ".deca_assets.downloaded"
    if marker.exists():
        if log is not None:
            log.append(f"deca assets: marker present at {marker}")
        return

    # Per-file check: existing non-stub files are kept (allows operator to
    # pre-stage by hand or via a network volume mount).
    pending = []
    for name, _ in DECA_ASSET_FILES:
        dst = DECA_DATA_DIR / name
        if dst.exists() and dst.stat().st_size > 4096:
            continue
        pending.append(name)

    if not pending:
        marker.touch()
        if log is not None:
            log.append("deca assets: all files already present, marker set")
        return

    if log is not None:
        log.append(f"deca assets: downloading {len(pending)} files to {DECA_DATA_DIR}")
    for name in pending:
        url = f"{DECA_ASSETS_BASE_URL}/{name}?download=true"
        dst = DECA_DATA_DIR / name
        # Try aria2c first (apt-installed for the LHM tarball path); fall
        # back to httpx on any error. aria2c with -x 8 -s 8 saturates HF's
        # CDN at ~100 MB/s, so a 510 MB cold-start adds ~10 s on a warm
        # worker, ~30 s on a cold one with TLS handshake overhead.
        try:
            dl = subprocess.run(
                ["aria2c", "-x", "8", "-s", "8",
                 "--max-tries=5", "--retry-wait=5",
                 "--console-log-level=warn",
                 "--allow-overwrite=true",
                 "-d", str(DECA_DATA_DIR),
                 "-o", name,
                 url],
                capture_output=True, text=True, timeout=900,
            )
            if dl.returncode != 0:
                raise RuntimeError(
                    f"aria2c rc={dl.returncode}: "
                    f"{dl.stderr[-800:] or dl.stdout[-800:]}"
                )
        except (FileNotFoundError, RuntimeError) as e:
            if log is not None:
                log.append(f"{name}: aria2c path failed ({e}); falling back to httpx")
            if not HAVE_HTTPX:
                raise RuntimeError(
                    f"DECA asset {name} download failed and httpx unavailable"
                ) from e
            with httpx.Client(timeout=900.0, follow_redirects=True) as c:
                r = c.get(url)
                r.raise_for_status()
                dst.write_bytes(r.content)
        if log is not None:
            log.append(f"deca asset {name}: {dst.stat().st_size} bytes")
    marker.touch()
    if log is not None:
        log.append("deca assets: marker set")


def _deca_numpy_shim():
    """Restore the np.float / np.int / np.bool aliases that DECA + chumpy
    code reaches for. Removed in numpy 1.24+. Safe to call multiple times."""
    import numpy as np
    if not hasattr(np, "float"):
        np.float = float  # type: ignore[attr-defined]
    if not hasattr(np, "int"):
        np.int = int  # type: ignore[attr-defined]
    if not hasattr(np, "bool"):
        np.bool = bool  # type: ignore[attr-defined]


def _silence_tensorboard():
    """Monkey-patch torch.utils.tensorboard.SummaryWriter to a no-op. The
    smplx-deca utility functions instantiate writers and add scalars without
    a way to disable them; we don't want them touching disk on RunPod."""
    class _NoopWriter:
        def __init__(self, *a, **k): pass
        def add_scalar(self, *a, **k): pass
        def add_scalars(self, *a, **k): pass
        def close(self): pass
        def flush(self): pass
    try:
        import torch.utils.tensorboard as _tb
        _tb.SummaryWriter = _NoopWriter  # type: ignore[assignment]
    except Exception:
        pass


def _patch_smplx_deca_ccbin() -> str:
    """Strip the historical -ccbin=$$(which gcc-7) JIT-compile flag from
    smplx-deca's renderer.py before DECA imports it.

    Why: upstream's renderer pins gcc-7 as a CUDA-10.2 / gcc-9 workaround
    (see their own comment on the line). We run CUDA 12.1 + gcc 11; the pin
    is obsolete. gcc-7 is not in the Ubuntu 22.04 base, so $(which gcc-7)
    expands to empty and nvcc dies with "Failed to preprocess host compiler
    properties" the first time DECA tries to JIT-compile standard_rasterize.

    Runs at module init of _get_deca (before any decalib import). Idempotent
    via a marker file so repeat calls on the same worker are no-ops. If the
    patch fails (file moved, regex no longer matches), we log and continue,
    so the original ccbin error surfaces with its full traceback rather than
    being hidden behind a silent patch failure.
    """
    import re
    target = Path("/workspace/smplx-deca/smplx_deca_main/deca/decalib/utils/renderer.py")
    marker = target.parent / ".ccbin_patched"
    if marker.exists():
        return "skip:already_patched"
    if not target.exists():
        return f"skip:source_missing:{target}"
    src = target.read_text()
    patched = re.sub(
        r"'-std=c\+\+14',\s*'-ccbin=\$\$\(which gcc-7\)'",
        "'-std=c++14'",
        src,
    )
    if patched == src:
        return "skip:pattern_not_found"
    target.write_text(patched)
    marker.touch()
    return "patched"


def _get_deca():
    """Lazy DECA singleton. Constructed once per worker; survives across
    invocations. First construction compiles the standard_rasterize CUDA
    extension via torch.utils.cpp_extension.load (~30 s on a cold worker)
    AND lazy-downloads ~510 MB of DECA model assets (~10-30 s on HF)."""
    global _DECA
    if _DECA is not None:
        return _DECA

    _deca_numpy_shim()
    _silence_tensorboard()
    try:
        ccbin_status = _patch_smplx_deca_ccbin()
        print(f"[DECA] ccbin patch: {ccbin_status}")
    except Exception as e:
        print(f"[DECA] ccbin patch failed (continuing): {type(e).__name__}: {e}")

    # Download DECA model assets to the path cfg.deca_dir + '/data/' resolves
    # to. Raises RuntimeError on download failure; caller wraps in try/except
    # and surfaces `deca_error` in the avatar response.
    _ensure_deca_data()

    import sys
    if str(SMPLX_DECA_ROOT) not in sys.path:
        sys.path.insert(0, str(SMPLX_DECA_ROOT))
    # DECA's encode/decode + datasets.TestData read configs via cwd-relative
    # paths. Stay in the Demos dir for this worker's lifetime (the LHM CLI
    # entry point also chdirs to LHM_ROOT, which we already do in _get_inferrer).
    # We do NOT chdir here because cmd_inference / cmd_inference_mesh expect
    # cwd == LHM_ROOT. Instead, we chdir into Demos only around the DECA call
    # in _deca_face_pass.

    from smplx_deca_main.deca.decalib.deca import DECA
    from smplx_deca_main.deca.decalib.utils.config import cfg as deca_cfg
    deca_cfg.model.extract_tex = True
    deca_cfg.model.use_tex = False           # FLAME albedo model not on disk
    deca_cfg.rasterizer_type = "standard"
    _DECA = DECA(config=deca_cfg, device="cuda", use_renderer=True)
    return _DECA


# ---------------------- vendored from smplx-deca/Demos --------------------
def _sd_get_mesh_root(mesh):
    """Vendored: utils.get_mesh_root. Centroid (mean) of a vertex set."""
    import torch
    if not torch.is_tensor(mesh):
        mesh = torch.from_numpy(mesh)
    return torch.tensor([
        torch.mean(mesh[:, 0]),
        torch.mean(mesh[:, 1]),
        torch.mean(mesh[:, 2]),
    ])


def _sd_optimize_head_alignment(mesh1, mesh2, step_size=1e-8, max_iters=200,
                                max_iters_without_improvement=20):
    """Vendored: utils.optimize_head_alignment. Adam-optimize a translation
    of mesh1's centroid to minimize squared distance to mesh2. Returns the
    best-aligned mesh1 plus number of steps. No tensorboard."""
    import torch
    if not torch.is_tensor(mesh1):
        mesh1 = torch.from_numpy(mesh1)
    if not torch.is_tensor(mesh2):
        mesh2 = torch.from_numpy(mesh2)

    root1 = _sd_get_mesh_root(mesh1)
    coords_to_optimize = torch.tensor(
        [root1[0], root1[1], root1[2]], requires_grad=True
    )
    optimizer = torch.optim.Adam([coords_to_optimize], lr=step_size)
    best_loss = float("inf")
    best = mesh1.clone()
    no_improve = 0
    step = 0
    for step in range(max_iters):
        mesh1[:, 0] += coords_to_optimize[0] - root1[0]
        mesh1[:, 1] += coords_to_optimize[1] - root1[1]
        mesh1[:, 2] += coords_to_optimize[2] - root1[2]
        loss = (mesh1 - mesh2).pow(2).sum()
        optimizer.zero_grad()
        loss.backward(retain_graph=True)
        optimizer.step()
        if loss.item() < best_loss:
            best_loss = loss.item()
            best = mesh1.clone()
            no_improve = 0
        else:
            no_improve += 1
        if no_improve >= max_iters_without_improvement:
            break
    coords_to_optimize.requires_grad = False
    return best, step


def _sd_transfer_texture_information(id_opdict, auxiliar_opdict):
    """Vendored: utils.transfer_texture_information."""
    for k in (
        "uv_texture_gt", "rendered_images", "alpha_images",
        "normal_images", "albedo", "uv_texture", "normals",
        "uv_detail_normals", "displacement_map",
    ):
        if k in auxiliar_opdict:
            id_opdict[k] = auxiliar_opdict[k]
    return id_opdict


def _sd_head_smoothing(deca_head, smplx_head, mask_path=NECK_SMOOTHING_MASK):
    """Vendored: utils.head_smoothing. Linear blend between DECA head vertices
    and SMPL-X head vertices using a fixed per-vertex weight mask loaded from
    Neck_masks/smoothing_mask_1 (float32 binary, 5023 entries — one per
    FLAME head vertex; subset of SMPL-X head_idxs)."""
    import torch
    import numpy as np
    weights = np.fromfile(str(mask_path), dtype="float32")
    head_weights = torch.tensor(weights, dtype=torch.float32)
    n = min(deca_head.shape[0], head_weights.shape[0])
    if not torch.is_tensor(deca_head):
        deca_head = torch.from_numpy(deca_head)
    if not torch.is_tensor(smplx_head):
        smplx_head = torch.from_numpy(smplx_head)
    out = deca_head.clone().float()
    w = head_weights[:n].unsqueeze(1)
    out[:n] = smplx_head[:n].float() * w + deca_head[:n].float() * (1.0 - w)
    return out


# Hardcoded neck seam vertex pairs from smplx-deca/Demos/utils.py
# (SMPL-X 1.1 / 10,475 verts only). Snaps each outer/inner pair to its midpoint
# to flatten the seam ring that the head replacement opens up.
_SD_NECK_OUTER_IDXS = [
    3218, 3219, 3236, 3237, 3329, 3330, 4427, 4428, 4436, 4437,
    4438, 5350, 5450, 5453, 5454, 5533, 5981, 5982, 5999, 6000,
    6092, 6093, 7163, 7164, 7172, 7173, 7174, 8184, 8187, 8188,
]
_SD_NECK_INNER_IDXS = [
    3936, 3937, 3239, 3238, 3939, 3938, 4429, 3376, 4434, 3378,
    3379, 3831, 5656, 3941, 3942, 5621, 6684, 6685, 6002, 6001,
    6687, 6686, 7165, 6137, 7170, 6139, 6140, 8350, 6689, 6690,
]


def _sd_neck_smoothing_for_textures(smplx_body):
    """Vendored: utils.neck_smoothing_for_textures. Pin each (outer, inner)
    pair to their midpoint to close the neck seam ring."""
    for o, i in zip(_SD_NECK_OUTER_IDXS, _SD_NECK_INNER_IDXS):
        mid = smplx_body[o] * 0.5 + smplx_body[i] * 0.5
        smplx_body[o] = mid
        smplx_body[i] = mid
    return smplx_body


def _sd_read_uv_coords_from_obj(fname):
    """Vendored: uv_mixing_utils.read_uv_coordinates_from_obj."""
    import numpy as np
    res = []
    with open(fname) as f:
        for line in f:
            if line.startswith("vt "):
                parts = line.split()
                res.append([float(parts[1]), float(parts[2])])
    return np.array(res, dtype=np.float32)


def _sd_read_uv_faces_from_obj(fname):
    """Vendored: uv_mixing_utils.read_uv_faces_id_from_obj."""
    import numpy as np
    res = []
    with open(fname) as f:
        for line in f:
            if line.startswith("f "):
                parts = line.split()
                if "/" not in parts[1]:
                    raise RuntimeError(f"not a textured obj: {fname}")
                tri = [int(p.split("/")[1]) for p in parts[1:4]]
                res.append(tri)
    return np.array(res, dtype=np.int32) - 1  # OBJ is 1-indexed


def _sd_read_vertex_faces_from_obj(fname):
    """Vendored: uv_mixing_utils.read_vertex_faces_id_from_obj."""
    import numpy as np
    res = []
    with open(fname) as f:
        for line in f:
            if line.startswith("f "):
                parts = line.split()
                if "/" in parts[1]:
                    tri = [int(p.split("/")[0]) for p in parts[1:4]]
                else:
                    tri = [int(p) for p in parts[1:4]]
                res.append(tri)
    return np.array(res, dtype=np.int32) - 1


def _sd_read_verts_from_obj(fname):
    """Vendored: uv_mixing_utils.read_vertex_from_obj."""
    import numpy as np
    res = []
    with open(fname) as f:
        for line in f:
            if line.startswith("v "):
                parts = line.split()
                res.append([float(parts[1]), float(parts[2]), float(parts[3])])
    return np.array(res, dtype=np.float32)


def _sd_generate_mixed_uvs(smplx_addon_obj, flame_template_obj, correspondences_npy):
    """Vendored: utils.generate_mixed_uvs (inlined cross-correspondence logic
    from uv_mixing_utils.get_smplx_flame_crossrespondence_face_ids).
    Returns per-vertex UV [N_uv, 2] in the merged 2x-wide layout, where body
    UVs live in u in [0, 0.5] and face UVs live in u in [0.5, 1.0].
    """
    import numpy as np
    s_f_ids = _sd_read_vertex_faces_from_obj(smplx_addon_obj)
    s_f_uvs = _sd_read_uv_faces_from_obj(smplx_addon_obj)
    s_uv = _sd_read_uv_coords_from_obj(smplx_addon_obj)
    s_uv[:, 1] = 1.0 - s_uv[:, 1]  # OBJ y-up -> image v-down

    f_verts = _sd_read_verts_from_obj(flame_template_obj)
    f_f_ids = _sd_read_vertex_faces_from_obj(flame_template_obj)
    f_uv = _sd_read_uv_coords_from_obj(flame_template_obj)
    f_uv[:, 1] = 1.0 - f_uv[:, 1]

    sf_ids = np.load(correspondences_npy)

    # SMPL-X vertex-tuple -> face id
    smplx_face_by_tri = {}
    for j, (v1, v2, v3) in enumerate(s_f_ids):
        key = f"{v1}_{v2}_{v3}"
        smplx_face_by_tri[key] = j

    flame_to_smplx_uv_face = {}
    for fid, ftri in enumerate(f_f_ids):
        v1 = sf_ids[ftri[0]] if ftri[0] < sf_ids.shape[0] else -1
        v2 = sf_ids[ftri[1]] if ftri[1] < sf_ids.shape[0] else -1
        v3 = sf_ids[ftri[2]] if ftri[2] < sf_ids.shape[0] else -1
        key = f"{v1}_{v2}_{v3}"
        if key in smplx_face_by_tri:
            flame_to_smplx_uv_face[fid] = smplx_face_by_tri[key]

    # Halve the body UVs to occupy [0, 0.5]; remap face triangles to [0.5, 1.0]
    s_uv[:, 0] = s_uv[:, 0] * 0.5
    for fid, sid in flame_to_smplx_uv_face.items():
        flame_idx = f_f_ids[fid]
        smplx_idx = s_f_uvs[sid]
        for k in range(3):
            s_uv[smplx_idx[k], 1] = 1.0 - f_uv[flame_idx[k], 1]
            s_uv[smplx_idx[k], 0] = (f_uv[flame_idx[k], 0] * 0.5) + 0.5
    return s_uv


def _tint_body_albedo(static_png_path, target_rgb):
    """Linearly scale the static SMPL-X body albedo PNG so its mean RGB
    matches target_rgb. Returns a [H, W, 3] uint8 array. Cheap and good
    enough: the static PNG is uniformly pale-skin tone with minor detail."""
    import numpy as np
    from PIL import Image
    pil = Image.open(str(static_png_path)).convert("RGB")
    arr = np.asarray(pil).astype(np.float32)
    mean = arr.reshape(-1, 3).mean(axis=0)
    target = np.asarray(target_rgb, dtype=np.float32)
    scale = (target / np.clip(mean, 1.0, None)).reshape(1, 1, 3)
    return np.clip(arr * scale, 0.0, 255.0).astype(np.uint8)


def _merge_side_by_side(body_rgb_uint8, face_png_path, half_size=4096):
    """Resize body + face textures to half_size x half_size each and paste
    side-by-side into a (2*half_size) x half_size RGB image."""
    import numpy as np
    from PIL import Image
    body_pil = Image.fromarray(body_rgb_uint8).resize((half_size, half_size))
    face_pil = Image.open(str(face_png_path)).convert("RGB").resize((half_size, half_size))
    merged = Image.new("RGB", (half_size * 2, half_size))
    merged.paste(body_pil, (0, 0))
    merged.paste(face_pil, (half_size, 0))
    return np.asarray(merged)


def _write_glb_with_addon_uv(verts_3d_m, faces_v_addon, vt, faces_vt_addon,
                              texture_rgb, out_path):
    """Write a GLB using the smplx-addon UV layout (8192x4096 merged texture).
    Same vt-seam-expansion trick as _write_glb_with_uv_texture but the addon
    obj has its own face indices distinct from smplx_uv.obj."""
    import numpy as np
    import trimesh
    from PIL import Image
    n_uv = vt.shape[0]
    vt_to_v = np.full(n_uv, -1, dtype=np.int32)
    for f_v, f_vt in zip(faces_v_addon, faces_vt_addon):
        vt_to_v[f_vt[0]] = f_v[0]
        vt_to_v[f_vt[1]] = f_v[1]
        vt_to_v[f_vt[2]] = f_v[2]
    expanded = verts_3d_m[vt_to_v].astype(np.float32)
    img = Image.fromarray(texture_rgb).convert("RGB")
    visual = trimesh.visual.TextureVisuals(uv=vt.astype(np.float32), image=img)
    mesh = trimesh.Trimesh(
        vertices=expanded,
        faces=faces_vt_addon.astype(np.int32),
        visual=visual,
        process=False,
    )
    mesh.export(out_path, file_type="glb")


def _deca_face_pass(
    selfie_path: Path,
    smplx_betas_np,
    body_skin_rgb,
    smplx_model_dir: str,
    out_dir: Path,
):
    """Run the DECA + smplx-deca pipeline for one selfie.

    Returns dict with:
      v_template_with_head: torch [10475, 3] — the modified v_template, fed
                            back into the SMPL-X forward pass to bake the
                            DECA head offset + neck smoothing into A-pose
                            output
      merged_texture: np  uint8 [4096, 8192, 3]
      uv_coords: np float32 [N_uv, 2] in the addon layout
      uv_faces: np int32 [N_f, 3]
      faces_v_addon: np int32 [N_f, 3]
      head_idxs: np int [5023]
      deca_head_obj_path / deca_head_tex_path: for debugging
    """
    import torch
    import numpy as np
    import pickle

    _deca_numpy_shim()
    _silence_tensorboard()
    deca = _get_deca()  # may chdir to LHM_ROOT internally; we'll guard below

    import sys
    if str(SMPLX_DECA_ROOT) not in sys.path:
        sys.path.insert(0, str(SMPLX_DECA_ROOT))

    from smplx_deca_main.deca.decalib.datasets import datasets

    # DECA's TestData + face_alignment write/read cache files into cwd.
    # Wrap the DECA-heavy section in a chdir-guard so we don't leave the
    # worker's cwd somewhere unexpected for subsequent commands.
    prev_cwd = os.getcwd()
    head_idxs = np.load(str(SMPLX_FLAME_VERTEX_IDS_PATH))
    try:
        os.chdir(str(SMPLX_DECA_DEMOS))

        # 1) DECA encode/decode the selfie
        testdata = datasets.TestData(
            str(selfie_path), iscrop=True, face_detector="fan"
        )
        if len(testdata) == 0:
            raise RuntimeError("DECA TestData found no face in selfie")
        images = testdata[0]["image"].to("cuda")[None, ...]
        with torch.no_grad():
            code = deca.encode(images)
        aux_op, _ = deca.decode(code)
        code["exp"] = torch.zeros((1, 50)).to("cuda")
        code["pose"] = torch.zeros((1, 6)).to("cuda")
        id_op, _ = deca.decode(code)
        id_op = _sd_transfer_texture_information(id_op, aux_op)

        # 2) Save DECA OBJ + PNG (saves <name>.obj + <name>.png + <name>.mtl
        #    in the SAME directory; we point at a fresh dir under tmp).
        deca_head_dir = out_dir / "deca_head"
        deca_head_dir.mkdir(exist_ok=True)
        deca_obj_path = deca_head_dir / "head.obj"
        deca.save_obj(str(deca_obj_path), id_op)
        deca_tex_path = deca_head_dir / "head.png"
        if not deca_tex_path.exists():
            raise RuntimeError(
                f"DECA did not write {deca_tex_path}; extractTex pipeline broken"
            )

        # 3) Build smplx model via our LHM-baked .npz files
        import smplx as smplx_pkg
        smpl_model = smplx_pkg.create(
            smplx_model_dir,
            model_type="smplx",
            gender="neutral",
            ext="npz",
            use_pca=False,
            flat_hand_mean=True,
            num_betas=10,
        )
        betas_t = torch.from_numpy(np.asarray(smplx_betas_np, dtype="float32")).reshape(1, -1)
        if betas_t.shape[1] >= 10:
            betas_t = betas_t[:, :10]
        else:
            pad = torch.zeros(1, 10 - betas_t.shape[1])
            betas_t = torch.cat([betas_t, pad], dim=1)
        smpl_output = smpl_model(betas=betas_t, return_verts=True)
        smpl_body_generated = smpl_output["v_shaped"].squeeze(0).detach()

        # 4) Load DECA neutral head template (FLAME 2020 v_template)
        with open(str(DECA_DATA_DIR / "generic_model.pkl"), "rb") as f:
            generic_deca = pickle.load(f, encoding="latin1")
        deca_neutral_verts = generic_deca["v_template"].astype(np.float32)

        # 5) 3-pair alignment chain (we skip the expression head pair from
        #    Javisda's demo because we don't accept an expression photo).
        gen_deca_head = id_op["verts"].detach().clone().squeeze(0).cpu()
        deca_neutral_head = torch.from_numpy(deca_neutral_verts)
        smplx_neutral_head = smpl_model.v_template[head_idxs].clone().detach()
        gen_smplx_head = smpl_body_generated[head_idxs].clone()

        heads = [gen_deca_head, deca_neutral_head, smplx_neutral_head, gen_smplx_head]
        total_offset = torch.zeros_like(smplx_neutral_head, dtype=torch.float32)
        for i in range(len(heads) - 1):
            h1 = heads[i].clone()
            h2 = heads[i + 1].clone()
            gc1 = _sd_get_mesh_root(h1)
            gc2 = _sd_get_mesh_root(h2)
            h1_aligned = h1 - (gc1 - gc2)
            best, _ = _sd_optimize_head_alignment(h1_aligned, h2, max_iters=200)
            shape_offset = torch.sub(best, h2).squeeze(0)
            total_offset = total_offset + shape_offset

        # 6) Replace SMPL-X head verts with DECA-derived + smooth the seam
        smplx_body = smpl_body_generated.clone()
        smplx_head_with_offsets = smplx_body[head_idxs] + total_offset
        smplx_body[head_idxs] = _sd_head_smoothing(
            smplx_head_with_offsets.float(), smplx_body[head_idxs].float(),
        )
        smplx_body = _sd_neck_smoothing_for_textures(smplx_body)

        # 7) Generate merged UVs + load UV faces
        uv_coords = _sd_generate_mixed_uvs(
            str(SMPLX_ADDON_OBJ),
            str(FLAME_HEAD_TEMPLATE_OBJ),
            str(SMPLX_FLAME_VERTEX_IDS_PATH),
        )
        uv_faces = _sd_read_uv_faces_from_obj(str(SMPLX_ADDON_OBJ))
        faces_v_addon = _sd_read_vertex_faces_from_obj(str(SMPLX_ADDON_OBJ))

        # 8) Build the merged 8192x4096 texture (body left, face right).
        body_tex_uint8 = _tint_body_albedo(SMPLX_BODY_ALBEDO_PATH, body_skin_rgb)
        merged_texture = _merge_side_by_side(
            body_tex_uint8, deca_tex_path, half_size=4096,
        )

        return {
            "v_template_with_head": smplx_body.detach(),
            "merged_texture": merged_texture,
            "uv_coords": uv_coords,
            "uv_faces": uv_faces,
            "faces_v_addon": faces_v_addon,
            "head_idxs": head_idxs,
            "deca_head_obj_path": deca_obj_path,
            "deca_head_tex_path": deca_tex_path,
        }
    finally:
        os.chdir(prev_cwd)


def cmd_avatar(inp: dict, started: float) -> dict:
    """Build the 4DHumans-equivalent SMPL-X avatar bundle from a single photo.

    2026-05-20 scope: realistic-face mapping (DECA, HairStep) is parked. This
    command produces the same artifact set as production 4DHumans, but on
    SMPL-X geometry via LHM's pose estimator (Multi-HMR) for β prediction.

    Input:
      image_url:   required, body photo URL
      height_cm:   optional float, height-normalizes SMPL-Anthropometry
                   measurements. When omitted, raw intrinsic-beta-scale
                   values are returned (LHM cannot know real-world scale
                   from a photo alone). Required for size-recommendation
                   v2 downstream; matches the production 4DHumans contract.
      weight_kg:   optional float. Captured in response but does NOT
                   influence measurements (matches production behaviour).
      gender:      "neutral" (default), "male", or "female"

    Returns the bundle:
      body_apose.obj            - A-pose SMPL-X mesh (mm)
      body_tpose.obj            - T-pose SMPL-X mesh (mm)
      avatar_textured.glb       - A-pose GLB with uniform face-median skin
      skin_texture.png          - 4x4 PNG of the face-median skin RGB
      measurements.json         - 16 standardized + 17 raw measurements
                                  (height-normalized when height_cm given)
      smplx_params.npz          - SMPL-X betas + pose params used
      face_crop.png             - the face region detected from the body photo
    """
    started_inner = _now()
    image_url = inp.get("image_url")
    if not image_url:
        return _err("avatar", "missing 'image_url'", started)
    gender = inp.get("gender", "neutral")
    if gender not in ("neutral", "male", "female"):
        return _err("avatar", f"invalid gender '{gender}'", started)

    def _coerce_float(v):
        if v is None or v == "":
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    height_cm = _coerce_float(inp.get("height_cm"))
    weight_kg = _coerce_float(inp.get("weight_kg"))

    try:
        _ensure_lhm_data()
    except Exception as e:
        return _err("avatar", f"LHM data bootstrap failed: {e}", started)

    with tempfile.TemporaryDirectory(prefix="lhm_avatar_") as tmp:
        tmp_path = Path(tmp)
        img_path = tmp_path / "input.png"
        try:
            _download_to(img_path, image_url)
        except Exception as e:
            return _err("avatar", f"failed to download image: {e}", started)

        # 1) Pose estimation -> SMPL-X β
        t_pose_start = _now()
        try:
            pose_estimator = _get_pose_estimator()
        except Exception as e:
            return _err(
                "avatar", f"failed to load pose estimator: {e}", started,
                extra={"traceback": traceback.format_exc()[-3000:]},
            )
        try:
            shape_pose = pose_estimator(str(img_path))
        except Exception as e:
            return _err(
                "avatar", f"pose estimation crashed: {e}", started,
                extra={"traceback": traceback.format_exc()[-3000:]},
            )
        if shape_pose.beta is None:
            return _err(
                "avatar", f"pose estimator returned no human: {shape_pose.msg}",
                started, extra={"is_full_body": shape_pose.is_full_body},
            )
        beta_np = shape_pose.beta
        t_pose = round(_now() - t_pose_start, 2)

        # 2) Build SMPL-X A-pose + T-pose meshes from β
        t_mesh_start = _now()
        try:
            import torch
            import numpy as np
            device = "cuda" if torch.cuda.is_available() else "cpu"
            verts_apose_m, verts_tpose_m, faces, smplx_params = _build_smplx_mesh_pair(
                beta_np=beta_np, gender=gender, device=device,
            )
            verts_apose_mm = (verts_apose_m * 1000.0).astype(np.float32)
            verts_tpose_mm = (verts_tpose_m * 1000.0).astype(np.float32)
        except Exception as e:
            return _err(
                "avatar", f"SMPL-X forward pass failed: {e}", started,
                extra={"traceback": traceback.format_exc()[-3000:]},
            )
        t_mesh = round(_now() - t_mesh_start, 2)

        # 3) Face crop + skin-median color from the body photo. Face detector
        #    failure is tolerated: skin RGB falls back to a neutral tan and
        #    face_crop.png is just omitted from the artifact list.
        t_color_start = _now()
        face_crop_path = tmp_path / "face_crop.png"
        face_detector = None
        face_detector_error = None
        try:
            face_detector = _get_face_detector()
        except Exception as e:
            face_detector_error = f"{type(e).__name__}: {e}"
        skin_rgb_diag = _sample_face_median_color_v2(
            face_detector, str(img_path), out_crop_path=face_crop_path,
        )
        import numpy as np
        vertex_colors = np.tile(
            np.array(
                [skin_rgb_diag[0], skin_rgb_diag[1], skin_rgb_diag[2]],
                dtype=np.uint8,
            ),
            (verts_apose_mm.shape[0], 1),
        )
        t_color = round(_now() - t_color_start, 2)

        # 4) Write geometry artifacts
        obj_apose_path = tmp_path / "body_apose.obj"
        obj_tpose_path = tmp_path / "body_tpose.obj"
        glb_path = tmp_path / "avatar_textured.glb"
        png_path = tmp_path / "skin_texture.png"
        npz_path = tmp_path / "smplx_params.npz"

        _write_obj_no_mtl(verts_apose_mm, faces, obj_apose_path)
        _write_obj_no_mtl(verts_tpose_mm, faces, obj_tpose_path)
        _write_textured_glb(verts_apose_mm, faces, vertex_colors, glb_path)
        _write_skin_texture_png(skin_rgb_diag, png_path)
        np.savez(npz_path, **{k: v for k, v in smplx_params.items() if k != "gender"})

        # 5) Measurements via SMPL-Anthropometry on the T-pose mesh. T-pose is
        #    the required reference pose (DavidBoja/SMPL-Anthropometry computes
        #    geodesic distances along T-pose vertex paths).
        t_meas_start = _now()
        measurements_block = None
        measurements_error = None
        try:
            measurements_block = _compute_measurements(
                verts_tpose_m=verts_tpose_m,
                height_cm=height_cm,
                gender=gender,
            )
        except Exception as e:
            measurements_error = f"{e.__class__.__name__}: {e}"
        t_meas = round(_now() - t_meas_start, 2)

        meas_path = tmp_path / "measurements.json"
        meas_payload = {
            "input": {
                "height_cm": height_cm,
                "weight_kg": weight_kg,
                "gender": gender,
            },
            "measurements_cm": (measurements_block or {}).get("raw_cm", {}),
            "standardized_cm": (measurements_block or {}).get("standardized_cm", {}),
            "labeled_cm": (measurements_block or {}).get("labeled_cm", {}),
            "intrinsic_height_cm": (measurements_block or {}).get("intrinsic_height_cm"),
            "normalization_factor": (measurements_block or {}).get("normalization_factor"),
            "error": measurements_error,
            "source_mesh": "smplx_tpose_lhm_betas",
        }
        meas_path.write_text(json.dumps(meas_payload, indent=2))

        # 6) Upload
        remote_subdir = f"avatars/{int(started)}"
        artifacts = [
            _collect_artifact(obj_apose_path, remote_subdir),
            _collect_artifact(obj_tpose_path, remote_subdir),
            _collect_artifact(glb_path, remote_subdir),
            _collect_artifact(png_path, remote_subdir),
            _collect_artifact(meas_path, remote_subdir),
            _collect_artifact(npz_path, remote_subdir),
        ]
        if face_crop_path.exists():
            artifacts.append(_collect_artifact(face_crop_path, remote_subdir))

        result = {
            "image_url": image_url,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "gender": gender,
            "beta_shape": list(beta_np.shape),
            "is_full_body": bool(shape_pose.is_full_body),
            "body_ratio": float(getattr(shape_pose, "ratio", 0.0)),
            "skin_rgb": list(skin_rgb_diag),
            "face_detector_error": face_detector_error,
            "measurements": (measurements_block or {}).get("standardized_cm"),
            "measurements_raw": (measurements_block or {}).get("raw_cm"),
            "measurements_labeled": (measurements_block or {}).get("labeled_cm"),
            "measurements_meta": {
                "intrinsic_height_cm": (measurements_block or {}).get("intrinsic_height_cm"),
                "normalization_factor": (measurements_block or {}).get("normalization_factor"),
                "input_height_cm": height_cm,
                "input_weight_kg": weight_kg,
                "source_mesh": "smplx_tpose_lhm_betas",
            },
            "measurements_error": measurements_error,
            "pose_convention": smplx_params["pose_convention"],
            "smplx_vertex_count": int(verts_apose_mm.shape[0]),
            "smplx_face_count": int(faces.shape[0]),
            "artifacts": artifacts,
            "timings": {
                "pose_estimation_s": t_pose,
                "smplx_mesh_s": t_mesh,
                "face_color_s": t_color,
                "measurements_s": t_meas,
                "total_inner_s": round(_now() - started_inner, 2),
            },
        }
        return _ok("avatar", result, started)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
COMMANDS = {
    "info": cmd_info,
    "ls": cmd_ls,
    "cat": cmd_cat,
    "init": cmd_init,
    "download_model": cmd_download_model,
    "inference": cmd_inference,
    "inference_mesh": cmd_inference_mesh,
    "avatar": cmd_avatar,
    "shell": cmd_shell,
}


def handler(event: dict) -> dict:
    started = _now()
    job_input = event.get("input", {}) or {}
    command = job_input.get("command", "info")
    fn = COMMANDS.get(command)
    if not fn:
        return _err(command, f"unknown command '{command}'. "
                             f"available: {sorted(COMMANDS)}", started)
    try:
        return fn(job_input, started)
    except Exception as e:
        return _err(command, f"unhandled exception: {e}", started,
                    extra={"traceback": traceback.format_exc()[-3000:]})


# ---------------------------------------------------------------------------
# RunPod boot
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        import runpod
        print(f"[LHM Handler] booting. default_model={DEFAULT_MODEL} "
              f"allow_shell={ALLOW_SHELL} supabase={bool(SUPABASE_URL)}")
        runpod.serverless.start({"handler": handler})
    except ImportError:
        # Local dry-run
        print("[LHM Handler] runpod not installed, doing local dry-run of cmd_info")
        print(json.dumps(handler({"input": {"command": "info"}}), indent=2))
