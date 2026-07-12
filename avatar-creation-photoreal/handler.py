#!/usr/bin/env python3
"""
Photoreal Avatar - RunPod serverless handler (v0.2).

Stage 1 (v0.1) proved the self-contained image builds on RunPod's farm and that
every CUDA-kernel extension (pytorch3d / gsplat / diff_gaussian_rasterization /
simple_knn / pointops) plus the LHM++ PoseEstimator load on a GPU worker. That
health probe is preserved here as `{"input": {"ping": true}}`.

Stage 2b (this version) adds `cmd_avatar_photoreal`: it reproduces today's
production output contract from a single front photo, but off LHM++ instead of
the SMPL-X-licensed 4DHumans / LHM path:

    photo_url --> LHM++ PoseEstimator (Multi-HMR) --> SMPL-X betas (HIDDEN)
              --> SMPL-X A-pose + T-pose mesh (smplx layer)
              --> SMPL-Anthropometry 16-key measurement bundle
              --> flat base64 artifact set (apose/tpose OBJ, GLB, skin PNG, npz)

The output shape is byte-for-byte the flat contract `cmd_avatar_production`
returns on the live LHM endpoint (see avatar-creation-lhm/handler.py:2429 and
backend/app/services/supabase.py:406), so the backend upload + DB path needs no
change when we flip Railway's RUNPOD_ENDPOINT_ID.

What Stage 2b deliberately does NOT do yet (later stages, per
~/.claude/plans/humming-hugging-parrot.md):
  - Stage 3: LHM++ multi-image Gaussian splat --> real photoreal appearance
    baked onto the mesh. Until then the GLB ships a UNIFORM skin tint. LHM++
    bundles no face-detector wrapper, so skin RGB here is the neutral-tan
    fallback, NOT sampled from the photo. This is intentional: the splat
    appearance replaces the tint wholesale in Stage 3, so investing in a
    face-crop skin sampler now would be throwaway work.
  - Stage 4: clean watertight drape mesh + real drape gate.
  - Stage 5/6: SCHP clothing strip + painted underwear.

Model weights (LHM++ prior: human_model_files with Multi-HMR + SMPL-X) are NOT
baked into the image. They are runtime-downloaded on first avatar request from
HuggingFace `3DAIGC/LHMPP-Prior` (ModelScope `Damo_XR_Lab/LHMPP-Prior`
fallback), fetching only the `human_model_files/**` subset (skips the multi-GB
voxel_grid / BiRefNet / arcface priors we don't need until Stage 3). Amortized
onto a Network Volume when one is attached, else re-fetched per cold worker.

Input contracts:
  {"input": {"ping": true}}                       -> health/selftest dict
  {"input": {"photo_url": ..., "height": ...}}     -> avatar (flat contract)
  {"input": {"command": "avatar", "photo_url": ...}}  -> same
"""

import os
import sys
import time
import base64
import shutil
import subprocess
import tempfile
import traceback
from pathlib import Path

import runpod

# ---------------------------------------------------------------------------
# Paths & config
# ---------------------------------------------------------------------------
# The Dockerfile clones LHM++ here and puts it (plus lib/, engine/pose_estimation)
# on PYTHONPATH, so `import engine...` resolves regardless of cwd. We still chdir
# into it before constructing the estimator, matching LHM++'s cwd assumptions for
# any relative asset loads inside the Multi-HMR model.
LHMPP_ROOT = Path("/workspace/LHM-plusplus")
ANTHROPOMETRY_ROOT = Path("/workspace/SMPL-Anthropometry")

# LHM++ prior model source (human_model_files: Multi-HMR ckpt + SMPL-X models).
# HuggingFace first, ModelScope fallback, mirroring LHM++'s own AutoModelQuery.
HF_PRIOR_REPO = "3DAIGC/LHMPP-Prior"
MS_PRIOR_REPO = "Damo_XR_Lab/LHMPP-Prior"
# Fetch ONLY the ~2.15 GB Stage-2b needs (Multi-HMR ckpt 1.29 GB + SMPL-X models
# 846 MB + smpl_mean_params 1 KB). The full human_model_files/** is ~4 GB: the
# extra ~1.85 GB is FLAME (a 1.26 GB texture + 6 FLAME .pkl) and SMPL .pkl that
# the pose/mesh/measure path never loads. That bloat blew a cold download past
# the endpoint's 600 s execution cap (job e2a41140 FAILED "executionTimeout
# exceeded" at 611 s). Narrowing lands a cold call at ~370 s. Later stages that
# need FLAME/SMPL widen this list.
PRIOR_ALLOW_PATTERNS = [
    "human_model_files/pose_estimate/**",
    "human_model_files/smplx/**",
    "human_model_files/smpl_mean_params.npz",
]

# A-pose shoulder rotation (identical convention to the live LHM endpoint so the
# draper sees the same canonical pose it was tuned against).
APOSE_SHOULDER_RAD = 45.0 * 3.141592653589793 / 180.0  # 45 deg

PHOTOREAL_BUILD = os.environ.get("PHOTOREAL_BUILD", "unknown")

# Lazy singletons: heavy model loads happen on the first avatar request, not at
# worker boot, so the cold-start selftest stays cheap.
_POSE_ESTIMATOR = None
_MEASURER = None
_PRIOR_DIR = None  # resolved pretrained_models dir (volume or image-local)

# httpx if present (LHM++ deps pull it in), else stdlib urllib.
try:
    import httpx
    HAVE_HTTPX = True
except ImportError:
    HAVE_HTTPX = False
    import urllib.request  # noqa: F401


def _now() -> float:
    return time.time()


# ---------------------------------------------------------------------------
# Cold-start GPU self-test (preserved from v0.1)
# ---------------------------------------------------------------------------
def _gpu_selftest() -> dict:
    """Import the runtime-critical deps and report what loaded. Never raises;
    returns a dict so a partial failure is visible in the job output instead of
    killing the worker."""
    report = {}
    try:
        import torch
        report["torch"] = torch.__version__
        report["cuda_version"] = torch.version.cuda
        report["cuda_available"] = torch.cuda.is_available()
        report["gpu"] = (
            torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        )
    except Exception as e:  # noqa: BLE001
        report["torch_error"] = repr(e)

    for name, mod in [
        ("pytorch3d", "pytorch3d"),
        ("gsplat", "gsplat"),
        ("diff_gaussian_rasterization", "diff_gaussian_rasterization"),
        ("simple_knn", "simple_knn._C"),
        ("pointops", "pointops"),
        ("lhmpp_pose_estimator", "engine.pose_estimation.pose_estimator"),
        ("smpl_anthropometry", "measure"),
    ]:
        try:
            __import__(mod)
            report[name] = "ok"
        except Exception as e:  # noqa: BLE001
            report[name] = f"FAIL: {repr(e)}"
    return report


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------
def _download_to(path: Path, url: str, timeout: float = 120.0) -> None:
    """Download a URL into a local file. Used for the input body photo."""
    if url.startswith("file://"):
        shutil.copy(url[7:], path)
        return
    if HAVE_HTTPX:
        with httpx.Client(timeout=timeout, follow_redirects=True) as c:
            r = c.get(url)
            r.raise_for_status()
            path.write_bytes(r.content)
    else:
        import urllib.request
        urllib.request.urlretrieve(url, path)


def _resolve_prior_dir() -> Path:
    """Pick where the LHM++ prior (human_model_files) lives.

    Prefer a writable RunPod Network Volume so the download is amortized across
    every worker that ever attaches. Otherwise fall back to the image-local
    pretrained_models dir (every fresh worker re-pays the one-time download).
    """
    volume = Path("/runpod-volume")
    if volume.is_dir() and os.access(volume, os.W_OK):
        d = volume / "lhmpp-prior" / "pretrained_models"
        d.mkdir(parents=True, exist_ok=True)
        return d
    d = LHMPP_ROOT / "pretrained_models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _human_model_files() -> Path:
    global _PRIOR_DIR
    if _PRIOR_DIR is None:
        _PRIOR_DIR = _resolve_prior_dir()
    return _PRIOR_DIR / "human_model_files"


def _ensure_lhmpp_prior(log: list | None = None) -> Path:
    """Idempotently fetch the `human_model_files/**` subset of the LHM++ prior.

    Returns the human_model_files dir. Raises RuntimeError if neither HF nor
    ModelScope yields the Multi-HMR checkpoint + SMPL-X models we need.

    We only pull `human_model_files/**` (Multi-HMR ckpt + SMPL-X models), not
    the full prior (voxel_grid / BiRefNet / arcface), which we don't touch until
    the Stage-3 splat bake. Skips work when the marker files already exist.
    """
    hmf = _human_model_files()
    prior_dir = hmf.parent
    ckpt = hmf / "pose_estimate" / "multiHMR_896_L.pt"
    smplx_neutral = hmf / "smplx" / "SMPLX_NEUTRAL.npz"

    if ckpt.exists() and smplx_neutral.exists():
        if log is not None:
            log.append(f"prior: present at {hmf}")
        return hmf

    # huggingface_hub is pulled in by LHM++'s deps; install on the off chance
    # it isn't importable (mirrors LHM++'s AutoModelQuery bootstrap).
    try:
        from huggingface_hub import snapshot_download as hf_snapshot
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "huggingface_hub==0.23.2"]
        )
        from huggingface_hub import snapshot_download as hf_snapshot

    errors = []
    # 1) HuggingFace
    try:
        if log is not None:
            log.append(f"prior: downloading {PRIOR_ALLOW_PATTERNS} from HF {HF_PRIOR_REPO}")
        hf_snapshot(
            repo_id=HF_PRIOR_REPO,
            allow_patterns=PRIOR_ALLOW_PATTERNS,
            local_dir=str(prior_dir),
            token=os.environ.get("HF_TOKEN") or None,
        )
    except Exception as e:  # noqa: BLE001
        errors.append(f"HF: {e}")
        # 2) ModelScope fallback
        try:
            if log is not None:
                log.append(f"prior: HF failed ({e}); trying ModelScope {MS_PRIOR_REPO}")
            try:
                from modelscope import snapshot_download as ms_snapshot
            except ImportError:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "modelscope", "--no-deps"]
                )
                from modelscope import snapshot_download as ms_snapshot
            ms_snapshot(
                model_id=MS_PRIOR_REPO,
                allow_patterns=PRIOR_ALLOW_PATTERNS,
                local_dir=str(prior_dir),
            )
        except Exception as e2:  # noqa: BLE001
            errors.append(f"ModelScope: {e2}")

    if not (ckpt.exists() and smplx_neutral.exists()):
        raise RuntimeError(
            "LHM++ prior download did not yield the expected files "
            f"({ckpt} / {smplx_neutral} missing). Errors: {' | '.join(errors)}"
        )
    if log is not None:
        log.append(f"prior: ready at {hmf}")
    return hmf


# ---------------------------------------------------------------------------
# Pose estimation (LHM++ Multi-HMR) -> SMPL-X betas
# ---------------------------------------------------------------------------
def _get_pose_estimator():
    """Lazy LHM++ PoseEstimator singleton.

    engine.pose_estimation.pose_estimator.PoseEstimator loads
    `{model_path}/pose_estimate/multiHMR_896_L.pt` and passes model_path through
    to the Multi-HMR Model as smplx_dir, so model_path must be human_model_files
    (which holds both `pose_estimate/` and `smplx/`). We chdir into LHMPP_ROOT
    first; imports resolve via PYTHONPATH but the model may load relative assets.
    """
    global _POSE_ESTIMATOR
    if _POSE_ESTIMATOR is not None:
        return _POSE_ESTIMATOR
    hmf = _ensure_lhmpp_prior()
    os.chdir(str(LHMPP_ROOT))
    if str(LHMPP_ROOT) not in sys.path:
        sys.path.insert(0, str(LHMPP_ROOT))
    from engine.pose_estimation.pose_estimator import PoseEstimator
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    _POSE_ESTIMATOR = PoseEstimator(str(hmf), device=device)
    return _POSE_ESTIMATOR


# ---------------------------------------------------------------------------
# SMPL-X mesh build
# ---------------------------------------------------------------------------
def _build_apose_body_pose(device, dtype):
    """SMPL-X body_pose [1,21,3] axis-angle for canonical A-pose. Shoulders
    rotate about Z so both arms drop to ~45 deg. Signs match the live LHM
    endpoint (getting them reversed produces a Y-pose)."""
    import torch
    body_pose = torch.zeros((1, 21, 3), dtype=dtype, device=device)
    body_pose[0, 15, 2] = -APOSE_SHOULDER_RAD  # L_Shoulder rot Z: arm down
    body_pose[0, 16, 2] = +APOSE_SHOULDER_RAD  # R_Shoulder rot Z: arm down
    return body_pose


def _build_smplx_mesh_pair(beta_np, gender: str, device):
    """Forward the SMPL-X layer for both T-pose (drape/appearance frame) and
    A-pose (final artifact pose). Returns (verts_apose_m, verts_tpose_m, faces,
    smplx_params). Vertices in meters."""
    import torch
    import numpy as np
    import smplx

    smplx_dir = str(_human_model_files())
    layer = (
        smplx.create(
            smplx_dir,
            model_type="smplx",
            gender=gender,
            use_pca=False,
            flat_hand_mean=True,
            num_betas=int(np.asarray(beta_np).shape[-1]),
        )
        .to(device)
        .eval()
    )

    dtype = torch.float32
    betas = (
        torch.from_numpy(np.asarray(beta_np))
        .reshape(1, -1)
        .to(device=device, dtype=dtype)
    )
    body_pose_apose = _build_apose_body_pose(device=device, dtype=dtype)
    body_pose_tpose = torch.zeros((1, 21, 3), dtype=dtype, device=device)

    with torch.no_grad():
        out_a = layer(betas=betas, body_pose=body_pose_apose, return_verts=True)
        out_t = layer(betas=betas, body_pose=body_pose_tpose, return_verts=True)

    verts_apose_m = out_a.vertices[0].detach().cpu().numpy()
    verts_tpose_m = out_t.vertices[0].detach().cpu().numpy()
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


# ---------------------------------------------------------------------------
# Skin color (Stage 2b: neutral-tan fallback; replaced by splat appearance in
# Stage 3). LHM++ ships no face-detector wrapper, so there is nothing to sample
# with. We keep the interface so a Stage-3 sampler drops in cleanly.
# ---------------------------------------------------------------------------
NEUTRAL_TAN = (210, 175, 145)


def _skin_rgb_placeholder() -> tuple:
    return NEUTRAL_TAN


# ---------------------------------------------------------------------------
# Artifact writers (self-contained; identical to the live LHM endpoint)
# ---------------------------------------------------------------------------
def _write_obj_no_mtl(verts_mm, faces, obj_path):
    with open(obj_path, "w") as f:
        f.write("# SMPL-X, mm\n")
        for v in verts_mm:
            f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")
        for tri in faces:
            f.write(f"f {tri[0] + 1} {tri[1] + 1} {tri[2] + 1}\n")


def _write_textured_glb(verts_mm, faces, vertex_colors_rgb, glb_path):
    import numpy as np
    import trimesh
    verts_m = (verts_mm / 1000.0).astype(np.float32)
    n = verts_m.shape[0]
    arr = np.asarray(vertex_colors_rgb)
    if arr.ndim == 1:
        rgba = np.tile(
            np.array([arr[0], arr[1], arr[2], 255], dtype=np.uint8), (n, 1)
        )
    else:
        rgba = np.concatenate(
            [arr.astype(np.uint8), np.full((n, 1), 255, dtype=np.uint8)], axis=1
        )
    mesh = trimesh.Trimesh(
        vertices=verts_m, faces=faces, vertex_colors=rgba, process=False
    )
    mesh.export(glb_path, file_type="glb")


def _write_skin_texture_png(rgb, png_path, size: int = 4):
    import numpy as np
    from PIL import Image
    arr = np.tile(
        np.array([rgb[0], rgb[1], rgb[2]], dtype=np.uint8), (size, size, 1)
    )
    Image.fromarray(arr).save(png_path)


# ---------------------------------------------------------------------------
# Measurements (SMPL-Anthropometry)
# ---------------------------------------------------------------------------
# Vendored from the live LHM endpoint to preserve the exact key contract the
# rest of the stack (backend size rec v2, dashboard) consumes.
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


def _deca_numpy_shim():
    """Restore np.float / np.int / np.bool aliases some upstream code reaches
    for (removed in numpy 1.24+). Safe to call repeatedly."""
    import numpy as np
    if not hasattr(np, "float"):
        np.float = float  # type: ignore[attr-defined]
    if not hasattr(np, "int"):
        np.int = int  # type: ignore[attr-defined]
    if not hasattr(np, "bool"):
        np.bool = bool  # type: ignore[attr-defined]


def _standardize_measurements(raw: dict) -> dict:
    """Map SMPL-Anthropometry raw names to the API short keys the stack
    consumes. First match wins (matches production)."""
    out = {}
    for name, value in raw.items():
        key = name.lower()
        mapped = MEASUREMENT_MAPPING.get(key)
        if mapped is None:
            for k, m in MEASUREMENT_MAPPING.items():
                if k in key or key in k:
                    mapped = m
                    break
        if mapped is None or mapped in out:
            continue
        try:
            out[mapped] = round(float(value), 1)
        except (ValueError, TypeError):
            continue
    return out


def _ensure_smplx_pkl():
    """Give SMPL-Anthropometry the .pkl SMPL-X models it hardcodes.

    measure.py loads SMPL-X two ways, BOTH pinned to `ext="pkl"`:
      - MeasureSMPLX.__init__:  smplx.SMPLX(data/smplx, ext="pkl").faces
      - get_joint_regressor:    smplx.create(data, "smplx", ext="pkl")  (in from_verts)
    We only ship the LHM++ prior's .npz SMPL-X models. Rather than patch those
    call sites (fragile: a kwarg the Dockerfile sed can't reach, an unpinned
    clone, and a sys.modules cache race with the health-ping selftest - all of
    which defeated builds v0.4-v0.7), convert the .npz to .pkl once. smplx feeds
    both `np.load(npz)` and `pickle.load(pkl)` into the same `Struct(**data)`, so
    the .pkl is an equivalent model and the real code path runs unpatched.
    Idempotent. Writes into data/smplx/ next to the shipped segmentation json.
    """
    import numpy as np
    import pickle
    src_dir = _human_model_files() / "smplx"
    dst_dir = ANTHROPOMETRY_ROOT / "data" / "smplx"
    dst_dir.mkdir(parents=True, exist_ok=True)
    for g in ("NEUTRAL", "MALE", "FEMALE"):
        npz = src_dir / f"SMPLX_{g}.npz"
        pkl = dst_dir / f"SMPLX_{g}.pkl"
        if pkl.exists() or not npz.exists():
            continue
        data = dict(np.load(npz, allow_pickle=True))
        with open(pkl, "wb") as f:
            pickle.dump(data, f)


def _get_measurer():
    """Lazy MeasureBody('smplx') singleton. Ensures the .pkl SMPL-X models exist
    (converted from our .npz) so measure.py's hardcoded ext="pkl" loads resolve,
    then constructs the measurer with the real, unpatched code path."""
    global _MEASURER
    if _MEASURER is not None:
        return _MEASURER

    _deca_numpy_shim()
    _ensure_smplx_pkl()

    if str(ANTHROPOMETRY_ROOT) not in sys.path:
        sys.path.insert(0, str(ANTHROPOMETRY_ROOT))

    prev_cwd = os.getcwd()
    try:
        os.chdir(str(ANTHROPOMETRY_ROOT))
        from measure import MeasureBody
        _MEASURER = MeasureBody("smplx")
    finally:
        os.chdir(prev_cwd)
    return _MEASURER


def _compute_measurements(verts_tpose_m, height_cm, gender):
    """Run SMPL-Anthropometry on a T-pose SMPL-X mesh. Returns the raw /
    standardized / labeled cm bundle the backend expects."""
    import torch
    measurer = _get_measurer()

    verts_t = torch.from_numpy(verts_tpose_m.astype("float32"))

    # Reset per-call state (worker reuses the singleton across requests).
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

        if height_cm and intrinsic_h > 1e-3:
            measurer.height_normalize_measurements(height_cm)
            norm = float(height_cm) / intrinsic_h
            measurements_cm = {
                k: float(v)
                for k, v in measurer.height_normalized_measurements.items()
            }
        else:
            norm = 1.0
            measurements_cm = raw_intrinsic

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
# Avatar command (flat contract, matches live LHM cmd_avatar_production)
# ---------------------------------------------------------------------------
def cmd_avatar_photoreal(inp: dict, started: float) -> dict:
    """LHM++ drop-in for the production avatar contract. See module docstring.

    Output (FLAT, no `data` wrapper), file-key map matches
    backend/app/services/supabase.py:406:
      apose_mesh   -> body_apose.obj
      tpose_mesh   -> body_tpose.obj
      avatar_glb   -> avatar_textured.glb
      skin_texture -> skin_texture.png
      smpl_params  -> smpl_params.npz
    """
    image_url = inp.get("photo_url") or inp.get("image_url")
    if not image_url:
        return {"error": "missing 'photo_url'"}

    gender = inp.get("gender", "neutral")
    if gender not in ("neutral", "male", "female"):
        return {"error": f"invalid gender '{gender}'"}

    def _coerce_float(v):
        if v is None or v == "":
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    height_cm = _coerce_float(inp.get("height", inp.get("height_cm")))
    weight_kg = _coerce_float(inp.get("weight", inp.get("weight_kg")))
    user_id = inp.get("user_id")

    try:
        _ensure_lhmpp_prior()
    except Exception as e:
        return {"error": f"LHM++ prior bootstrap failed: {e}",
                "traceback": traceback.format_exc()[-3000:]}

    with tempfile.TemporaryDirectory(prefix="lhmpp_avatar_") as tmp:
        tmp_path = Path(tmp)
        img_path = tmp_path / "input.png"
        try:
            _download_to(img_path, image_url)
        except Exception as e:
            return {"error": f"failed to download image: {e}"}

        # 1) Pose estimation -> SMPL-X beta (hidden)
        try:
            pose_estimator = _get_pose_estimator()
        except Exception as e:
            return {"error": f"failed to load pose estimator: {e}",
                    "traceback": traceback.format_exc()[-3000:]}
        try:
            shape_pose = pose_estimator(str(img_path))
        except Exception as e:
            return {"error": f"pose estimation crashed: {e}",
                    "traceback": traceback.format_exc()[-3000:]}
        if getattr(shape_pose, "beta", None) is None:
            return {"error": "pose estimator returned no human",
                    "is_full_body": bool(getattr(shape_pose, "is_full_body", False))}
        beta_np = shape_pose.beta

        # 2) SMPL-X mesh build (A-pose + T-pose)
        try:
            import numpy as np
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            verts_apose_m, verts_tpose_m, faces, smplx_params = _build_smplx_mesh_pair(
                beta_np=beta_np, gender=gender, device=device,
            )
            verts_apose_mm = (verts_apose_m * 1000.0).astype(np.float32)
            verts_tpose_mm = (verts_tpose_m * 1000.0).astype(np.float32)
        except Exception as e:
            return {"error": f"SMPL-X forward pass failed: {e}",
                    "traceback": traceback.format_exc()[-3000:]}

        # 3) Skin color (Stage 2b: neutral-tan placeholder; splat appearance is
        #    Stage 3). Uniform tint across all verts.
        skin_rgb = _skin_rgb_placeholder()
        vertex_colors = np.tile(
            np.array([skin_rgb[0], skin_rgb[1], skin_rgb[2]], dtype=np.uint8),
            (verts_apose_mm.shape[0], 1),
        )

        # 4) Write artifacts to tmp (backend uploads, not us)
        obj_apose_path = tmp_path / "body_apose.obj"
        obj_tpose_path = tmp_path / "body_tpose.obj"
        glb_path = tmp_path / "avatar_textured.glb"
        png_path = tmp_path / "skin_texture.png"
        npz_path = tmp_path / "smpl_params.npz"

        _write_obj_no_mtl(verts_apose_mm, faces, obj_apose_path)
        _write_obj_no_mtl(verts_tpose_mm, faces, obj_tpose_path)
        _write_textured_glb(verts_apose_mm, faces, vertex_colors, glb_path)
        _write_skin_texture_png(skin_rgb, png_path)
        np.savez(npz_path, **{k: v for k, v in smplx_params.items() if k != "gender"})

        # 5) Measurements (SMPL-Anthropometry on T-pose)
        measurements_block = None
        measurements_error = None
        try:
            measurements_block = _compute_measurements(
                verts_tpose_m=verts_tpose_m, height_cm=height_cm, gender=gender,
            )
        except Exception as e:
            measurements_error = f"{e.__class__.__name__}: {e}"

        # 6) Base64-encode. Backend decodes + uploads.
        path_by_key = {
            "apose_mesh": obj_apose_path,
            "tpose_mesh": obj_tpose_path,
            "avatar_glb": glb_path,
            "skin_texture": png_path,
            "smpl_params": npz_path,
        }
        files_base64 = {}
        file_sizes = {}
        for key, p in path_by_key.items():
            data = p.read_bytes()
            files_base64[key] = base64.b64encode(data).decode("ascii")
            file_sizes[key] = len(data)

        meas_standardized = (measurements_block or {}).get("standardized_cm") or {}
        if not meas_standardized and height_cm:
            meas_standardized = {"height": int(round(height_cm))}

        return {
            "measurements": meas_standardized,
            "files_base64": files_base64,
            "file_sizes": file_sizes,
            "processing_time_seconds": round(_now() - started, 2),
            "skin_rgb": list(skin_rgb),
            "skin_rgb_source": "neutral_tan_placeholder_stage2b",
            "beta_shape": list(np.asarray(beta_np).shape),
            "is_full_body": bool(getattr(shape_pose, "is_full_body", False)),
            "pose_convention": smplx_params["pose_convention"],
            "measurements_error": measurements_error,
            "measurements_raw": (measurements_block or {}).get("raw_cm"),
            "measurements_labeled": (measurements_block or {}).get("labeled_cm"),
            "measurements_meta": {
                "intrinsic_height_cm": (measurements_block or {}).get("intrinsic_height_cm"),
                "normalization_factor": (measurements_block or {}).get("normalization_factor"),
                "input_height_cm": height_cm,
                "input_weight_kg": weight_kg,
                "source_mesh": "smplx_tpose_lhmpp_betas",
            },
            "smplx_vertex_count": int(verts_apose_mm.shape[0]),
            "smplx_face_count": int(faces.shape[0]),
            "photo_url": image_url,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "gender": gender,
            "user_id": user_id,
            "endpoint": "photoreal-stage2b",
            "build": PHOTOREAL_BUILD,
        }


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
def handler(event):
    """RunPod serverless entry.

      {"ping": true}   -> health probe + GPU selftest
      photo_url set    -> cmd_avatar_photoreal (flat contract)
    """
    started = _now()
    inp = (event or {}).get("input", {}) or {}
    command = inp.get("command")

    if inp.get("ping") or command == "ping":
        return {
            "status": "photoreal endpoint alive",
            "build": PHOTOREAL_BUILD,
            "echo": inp,
            "selftest": _gpu_selftest(),
        }

    # Pre-populate the LHM++ prior (Multi-HMR + SMPL-X) without running inference.
    # Run this once against a volume-backed endpoint so the first real avatar
    # request doesn't pay the download inside its execution window.
    if command == "warm":
        log: list = []
        try:
            hmf = _ensure_lhmpp_prior(log=log)
            sizes = {}
            for f in ("pose_estimate/multiHMR_896_L.pt", "smplx/SMPLX_NEUTRAL.npz",
                      "smpl_mean_params.npz"):
                p = hmf / f
                sizes[f] = p.stat().st_size if p.exists() else None
            return {
                "status": "prior ready",
                "human_model_files": str(hmf),
                "on_volume": str(hmf).startswith("/runpod-volume"),
                "file_sizes": sizes,
                "log": log,
                "elapsed_seconds": round(_now() - started, 2),
                "build": PHOTOREAL_BUILD,
            }
        except Exception as e:  # noqa: BLE001
            return {"error": f"warm failed: {e}",
                    "traceback": traceback.format_exc()[-3000:], "log": log}

    if command in ("avatar", "avatar_photoreal") or (command is None and inp.get("photo_url")):
        try:
            return cmd_avatar_photoreal(inp, started)
        except Exception as e:  # noqa: BLE001
            return {
                "error": f"avatar unhandled exception: {e}",
                "traceback": traceback.format_exc()[-3000:],
                "elapsed_seconds": round(_now() - started, 2),
            }

    # Default: health probe (keeps a bare {} invocation useful).
    return {
        "status": "photoreal endpoint alive",
        "build": PHOTOREAL_BUILD,
        "hint": "send {ping:true} for selftest, or {photo_url, height, gender} for an avatar",
        "echo": inp,
    }


if __name__ == "__main__":
    try:
        print(f"[boot] runpod {runpod.__version__} build={PHOTOREAL_BUILD} "
              f"- starting serverless worker", flush=True)
        runpod.serverless.start({"handler": handler})
    except Exception:  # noqa: BLE001
        print("[boot] FATAL: worker failed to start", flush=True)
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        raise
