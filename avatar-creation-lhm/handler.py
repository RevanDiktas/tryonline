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

# Cached singleton inferrer; built on first cmd_avatar call. Survives across
# invocations on the same worker, dies when the worker shuts down.
_INFERRER = None


def _get_inferrer(model_name: str):
    """Lazy-construct + cache the LHM HumanLRMInferrer.

    Hacks sys.argv to satisfy LHM's parse_configs(). This is the documented
    way to call `python -m LHM.launch infer.human_lrm model_name=... \
    image_input=... ...` as a Python call instead of subprocess.

    Returns the inferrer. Raises on construction failure.
    """
    global _INFERRER
    if _INFERRER is not None and getattr(_INFERRER, "_cached_model_name", None) == model_name:
        return _INFERRER

    sys.path.insert(0, str(LHM_ROOT))
    # HumanLRMInferrer.__init__ loads FaceDetector / PoseEstimator with paths
    # relative to CWD (`./pretrained_models/...`). The CLI sets cwd=LHM_ROOT;
    # we must mirror that or instantiation fails. Stay in LHM_ROOT for the
    # rest of the worker lifetime so subsequent infer_mesh calls also work.
    os.chdir(str(LHM_ROOT))

    # parse_configs() reads sys.argv for the runner name + model_name. Set them
    # so HumanLRMInferrer.__init__ -> parse_configs() picks up the right model.
    # image_input is needed as a valid arg even though we don't use the CLI
    # infer() entry point; we call methods directly.
    placeholder_image_dir = str(LHM_ROOT / "train_data" / "example_imgs")
    saved_argv = sys.argv[:]
    sys.argv = [
        "launch.py", "infer.human_lrm",
        f"model_name={model_name}",
        f"image_input={placeholder_image_dir}",
        "export_video=False",
        "export_mesh=True",
        f"motion_seqs_dir={MOTION_DEFAULT}",
        "motion_img_dir=None",
        "vis_motion=true",
        "motion_img_need_mask=true",
        "render_fps=30",
        "motion_video_read_fps=30",
    ]
    try:
        from LHM.runners.infer.human_lrm import HumanLRMInferrer
        inferrer = HumanLRMInferrer()
    finally:
        sys.argv = saved_argv

    inferrer._cached_model_name = model_name
    _INFERRER = inferrer
    return inferrer


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
    """Crop the face region from the photo, return median RGB as (r, g, b) ints.

    Falls back to a neutral tan if face detection fails so the artifact set
    is always complete.
    """
    import numpy as np
    try:
        rgb_face = inferrer.crop_face_image(image_path)  # HxWx3 uint8
        if rgb_face is None or rgb_face.size == 0:
            raise ValueError("empty face crop")
        # Drop hair / background pixels: use the central 50% of the crop
        h, w = rgb_face.shape[:2]
        cy0, cy1 = h // 4, 3 * h // 4
        cx0, cx1 = w // 4, 3 * w // 4
        central = rgb_face[cy0:cy1, cx0:cx1].reshape(-1, 3)
        if central.shape[0] == 0:
            central = rgb_face.reshape(-1, 3)
        med = np.median(central, axis=0).astype(np.uint8)
        return int(med[0]), int(med[1]), int(med[2])
    except Exception:
        return (210, 175, 145)  # neutral tan fallback


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


def cmd_avatar(inp: dict, started: float) -> dict:
    """Build the Phase 0 SMPL-X avatar bundle from a single photo.

    Input:
      image_url:   required, photo to reconstruct
      gender:      "neutral" (default), "male", or "female"
      model_name:  LHM checkpoint to use for the splat pass (default LHM-MINI)
      include_splats: bool (default true). Set false to skip the LHM splat
                      pass and only return geometry-only artifacts (~10s
                      faster).

    Returns the 5-artifact bundle (see module header).
    """
    started_inner = _now()
    image_url = inp.get("image_url")
    if not image_url:
        return _err("avatar", "missing 'image_url'", started)
    gender = inp.get("gender", "neutral")
    if gender not in ("neutral", "male", "female"):
        return _err("avatar", f"invalid gender '{gender}'", started)
    model_name = inp.get("model_name", DEFAULT_MODEL)
    include_splats = bool(inp.get("include_splats", True))

    # Ensure prior_model + motion data are present. On a Network Volume worker
    # this is a no-op after first call.
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

        # 1) Build / fetch the cached HumanLRMInferrer
        t_load_start = _now()
        try:
            inferrer = _get_inferrer(model_name)
        except Exception as e:
            return _err(
                "avatar", f"failed to instantiate LHM inferrer: {e}", started,
                extra={"traceback": traceback.format_exc()[-3000:]},
            )
        t_load = round(_now() - t_load_start, 2)

        # 2) Pose estimation -> SMPL-X β
        t_pose_start = _now()
        try:
            shape_pose = inferrer.pose_estimator(str(img_path))
        except Exception as e:
            return _err(
                "avatar", f"pose estimation crashed: {e}", started,
                extra={"traceback": traceback.format_exc()[-3000:]},
            )
        if shape_pose.beta is None:
            return _err("avatar", f"pose estimator returned no human: {shape_pose.msg}",
                        started, extra={"is_full_body": shape_pose.is_full_body})
        beta_np = shape_pose.beta
        t_pose = round(_now() - t_pose_start, 2)

        # 3) Build SMPL-X mesh pair: A-pose (drape-friendly) + T-pose (matches
        #    splat coordinate frame for color sampling)
        t_mesh_start = _now()
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            verts_apose_m, verts_tpose_m, faces, smplx_params = _build_smplx_mesh_pair(
                beta_np=beta_np, gender=gender, device=device,
            )
            import numpy as np
            verts_apose_mm = (verts_apose_m * 1000.0).astype(np.float32)
        except Exception as e:
            return _err(
                "avatar", f"SMPL-X forward pass failed: {e}", started,
                extra={"traceback": traceback.format_exc()[-3000:]},
            )
        t_mesh = round(_now() - t_mesh_start, 2)

        # 4) Run the LHM splat pass. We need the splats whether or not the
        #    caller asked to keep them as an artifact, because per-vertex
        #    color sampling depends on them. If splats fail, fall back to
        #    a uniform face-median color so the GLB is still produced.
        ply_path = None
        t_splat = None
        splat_error = None
        t_splat_start = _now()
        try:
            dump_tmp = tmp_path / "lhm_dump_tmp"
            dump_mesh = tmp_path / "lhm_dump_mesh"
            dump_tmp.mkdir(exist_ok=True)
            dump_mesh.mkdir(exist_ok=True)
            inferrer.infer_mesh(
                image_path=str(img_path),
                dump_tmp_dir=str(dump_tmp),
                dump_mesh_dir=str(dump_mesh),
                shape_param=beta_np,
            )
            splat_candidates = list(dump_mesh.rglob("*.ply"))
            if splat_candidates:
                ply_path = splat_candidates[0]
        except Exception as e:
            ply_path = None
            splat_error = f"{e}"
        t_splat = round(_now() - t_splat_start, 2)

        # 5) Per-vertex color from splats (region-aware skin segmentation)
        #    + extract hair splats for the optional hair.ply overlay artifact.
        t_color_start = _now()
        vertex_colors = None
        skin_rgb_diag = None
        color_stats = None
        hair_splat_mask = None
        color_source = "face_median_fallback"
        face_median_rgb = _sample_face_median_color(inferrer, str(img_path))

        # Holders for splat data so the UV texture baker (below) can reuse
        # what the per-vertex sampler loaded + classified.
        splat_pos_arr = None
        splat_rgb_arr = None
        splat_skin_mask = None
        if ply_path is not None and ply_path.exists():
            try:
                splat_pos_arr, splat_rgb_arr = _load_splat_colors(ply_path)
                # Classify once up front so per-vert sampling and UV baking
                # share the result.
                scalp_y_top_m = float(verts_tpose_m[:, 1].max())
                splat_skin_mask, hair_splat_mask = _classify_splats(
                    splat_pos=splat_pos_arr,
                    splat_rgb=splat_rgb_arr,
                    face_median_rgb=face_median_rgb,
                    scalp_y=scalp_y_top_m,
                )
                (
                    vertex_colors,
                    skin_rgb_diag,
                    color_stats,
                    hair_splat_mask,
                ) = _vertex_colors_region_aware(
                    verts_tpose_m=verts_tpose_m,
                    splat_pos=splat_pos_arr,
                    splat_rgb=splat_rgb_arr,
                    face_median_rgb=face_median_rgb,
                    k=5,
                    splat_skin_mask=splat_skin_mask,
                    splat_hair_mask=hair_splat_mask,
                )
                color_source = f"splats_region_aware_n{splat_pos_arr.shape[0]}"
            except Exception as e:
                splat_error = (splat_error or "") + f" | color sample failed: {e}"
                vertex_colors = None

        if vertex_colors is None:
            # Fallback: uniform face-median color across all verts
            skin_rgb_diag = face_median_rgb
            import numpy as np
            vertex_colors = np.tile(
                np.array([skin_rgb_diag[0], skin_rgb_diag[1], skin_rgb_diag[2]], dtype=np.uint8),
                (verts_apose_mm.shape[0], 1),
            )
        t_color = round(_now() - t_color_start, 2)

        # 6) Write geometry artifacts to tmp
        obj_path = tmp_path / "body_apose.obj"
        glb_path = tmp_path / "avatar_textured.glb"
        png_path = tmp_path / "skin_texture.png"
        npz_path = tmp_path / "smplx_params.npz"

        _write_obj_no_mtl(verts_apose_mm, faces, obj_path)

        # Tier 3a: try to bake a UV-mapped diffuse texture. Falls back to
        # per-vertex color if SMPL-X UV layout is unavailable or baking fails.
        uv_obj_path = (
            LHM_ROOT / "pretrained_models" / "human_model_files"
            / "smplx" / "smplx_uv" / "smplx_uv.obj"
        )
        uv_baked = False
        uv_coverage_pct = None
        uv_texture_size = 1024
        if (
            uv_obj_path.exists()
            and splat_pos_arr is not None
            and splat_skin_mask is not None
        ):
            t_uv_start = _now()
            try:
                vt, faces_v_obj, faces_vt_obj = _load_smplx_uv_obj(str(uv_obj_path))
                texture_rgb, _, uv_coverage_pct = _bake_uv_diffuse_texture(
                    verts_tpose_m=verts_tpose_m,
                    faces_v=faces_v_obj,
                    vt=vt,
                    faces_vt=faces_vt_obj,
                    splat_pos=splat_pos_arr,
                    splat_rgb=splat_rgb_arr,
                    splat_skin_mask=splat_skin_mask,
                    splat_hair_mask=hair_splat_mask,
                    texture_size=uv_texture_size,
                    k=5,
                )
                _write_glb_with_uv_texture(
                    verts_3d_m=verts_apose_m,
                    faces_v=faces_v_obj,
                    vt=vt,
                    faces_vt=faces_vt_obj,
                    texture_rgb=texture_rgb,
                    out_path=glb_path,
                )
                from PIL import Image as _PIL_Image
                _PIL_Image.fromarray(texture_rgb).save(png_path)
                uv_baked = True
                color_source = (
                    f"uv_texture_{uv_texture_size}_"
                    f"cov{uv_coverage_pct:.1f}pct_"
                    f"{color_source}"
                )
                t_uv_bake = round(_now() - t_uv_start, 2)
            except Exception as e:
                splat_error = (splat_error or "") + f" | uv bake failed: {e}"
                t_uv_bake = round(_now() - t_uv_start, 2)
        else:
            t_uv_bake = 0.0

        if not uv_baked:
            _write_textured_glb(verts_apose_mm, faces, vertex_colors, glb_path)
            _write_skin_texture_png(skin_rgb_diag, png_path)

        import numpy as np
        np.savez(npz_path, **{k: v for k, v in smplx_params.items() if k != "gender"})

        # 7) Upload all artifacts. Rename the splat PLY to splats.ply for
        #    the contract; LHM internally names it after the input stem.
        remote_subdir = f"avatars/{int(started)}"
        artifacts = [
            _collect_artifact(obj_path, remote_subdir),
            _collect_artifact(npz_path, remote_subdir),
            _collect_artifact(glb_path, remote_subdir),
            _collect_artifact(png_path, remote_subdir),
        ]
        if include_splats and ply_path is not None and ply_path.exists():
            splats_renamed = tmp_path / "splats.ply"
            try:
                shutil.copy(ply_path, splats_renamed)
                artifacts.append(_collect_artifact(splats_renamed, remote_subdir))
            except Exception:
                artifacts.append(_collect_artifact(ply_path, remote_subdir))

        # Tier 2: hair.ply (subset of LHM splats classified as hair). Same
        # format as splats.ply so the viewer can render with the same loader.
        # Only attempt if classification produced any hair splats; otherwise
        # the subject is bald or hair classification failed silently.
        hair_count = 0
        if (
            hair_splat_mask is not None
            and ply_path is not None
            and ply_path.exists()
            and hair_splat_mask.any()
        ):
            try:
                hair_path = tmp_path / "hair.ply"
                hair_count = _write_hair_splats_ply(ply_path, hair_path, hair_splat_mask)
                if hair_count > 0:
                    artifacts.append(_collect_artifact(hair_path, remote_subdir))
            except Exception as e:
                splat_error = (splat_error or "") + f" | hair extract failed: {e}"

        result = {
            "image_url": image_url,
            "gender": gender,
            "model_name": model_name,
            "beta_shape": list(beta_np.shape),
            "is_full_body": bool(shape_pose.is_full_body),
            "body_ratio": float(getattr(shape_pose, "ratio", 0.0)),
            "skin_rgb": list(skin_rgb_diag),
            "color_source": color_source,
            "color_stats": color_stats,
            "hair_splat_count": hair_count,
            "uv_baked": uv_baked,
            "uv_coverage_pct": uv_coverage_pct,
            "uv_texture_size": uv_texture_size if uv_baked else None,
            "pose_convention": smplx_params["pose_convention"],
            "smplx_vertex_count": int(verts_apose_mm.shape[0]),
            "smplx_face_count": int(faces.shape[0]),
            "artifacts": artifacts,
            "timings": {
                "inferrer_load_s": t_load,
                "pose_estimation_s": t_pose,
                "smplx_mesh_s": t_mesh,
                "splat_pass_s": t_splat,
                "color_sample_s": t_color,
                "uv_bake_s": t_uv_bake,
                "total_inner_s": round(_now() - started_inner, 2),
            },
        }
        if splat_error:
            result["splat_error"] = splat_error
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
