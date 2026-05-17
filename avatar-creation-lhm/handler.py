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
# baked into the image. Each tarball extracts into LHM_ROOT; we don't rely on
# knowing the internal layout and instead use a marker file in LHM_ROOT to
# record successful extraction.
ALIYUN_BASE = "https://virutalbuy-public.oss-cn-hangzhou.aliyuncs.com/share/aigc3d/data/LHM"
DATA_FILES = [
    {"name": "LHM_prior_model.tar", "url": f"{ALIYUN_BASE}/LHM_prior_model.tar"},
    {"name": "motion_video.tar",    "url": f"{ALIYUN_BASE}/motion_video.tar"},
]

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

    Idempotent. Safe to call from every inference. First call on a fresh worker
    pays ~5 min (aria2c parallel download + tar extract). Subsequent calls are
    a few-microsecond marker-file check.

    Marker pattern: after a tarball is successfully extracted, we touch
    `<LHM_ROOT>/.<tarname>.extracted`. We don't rely on knowing the internal
    layout of the tarball.

    Raises RuntimeError on download/extract failure.
    """
    for item in DATA_FILES:
        name = item["name"]
        marker = LHM_ROOT / f".{name}.extracted"
        if marker.exists():
            if log is not None:
                log.append(f"{name}: already present (marker found)")
            continue

        if log is not None:
            log.append(f"{name}: downloading from {item['url']}")
        tar_path = LHM_ROOT / name
        # aria2c is installed in the image; the same -x 16 -s 16 flags that
        # cut Aliyun download time from ~31min to ~5min at build time work
        # the same way at runtime.
        dl = subprocess.run(
            ["aria2c", "-x", "16", "-s", "16",
             "--max-tries=5", "--retry-wait=10",
             "--console-log-level=warn",
             "--allow-overwrite=true",
             "-d", str(LHM_ROOT),
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
            log.append(f"{name}: extracting")
        ex = subprocess.run(
            ["tar", "-xf", str(tar_path)],
            cwd=str(LHM_ROOT), capture_output=True, text=True, timeout=600,
        )
        if ex.returncode != 0:
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
    info["data_files"] = {
        d["name"]: (LHM_ROOT / f".{d['name']}.extracted").exists()
        for d in DATA_FILES
    }

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
