#!/usr/bin/env python3
"""
Photoreal Avatar - RunPod serverless handler (v0.1 SKELETON / health probe).

This first version does NOT build an avatar. It exists to validate, cheaply,
that the heavy self-contained image builds on RunPod's farm within the cap and
that a worker boots and runs a handler. It also serves as the GPU-side
cold-start self-test: it imports the CUDA-kernel extensions the Dockerfile could
not check on the farm build host (diff_gaussian_rasterization, simple_knn,
pointops, gsplat) and reports what actually loaded on the GPU.

Once this is green on the new endpoint, later versions add:
  cmd_avatar_photoreal -> SMPL-X betas + measurements (LHM++ PoseEstimator)
  -> LHM++ multi-image splat -> clean drape mesh -> clothing strip -> underwear.

Input contract (health probe): {"input": {"ping": true}} or {} -> status dict.
"""

import os
import sys
import traceback

import runpod


def _gpu_selftest():
    """Import the runtime-critical deps and report what loaded. Never raises;
    returns a dict so a partial failure is visible in the job output instead of
    killing the worker."""
    report = {}

    try:
        import torch
        report["torch"] = torch.__version__
        report["cuda_version"] = torch.version.cuda
        report["cuda_available"] = torch.cuda.is_available()
        report["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    except Exception as e:  # noqa: BLE001
        report["torch_error"] = repr(e)

    # CUDA-kernel extensions (real init only works on a GPU worker, not the farm).
    for name, mod in [
        ("pytorch3d", "pytorch3d"),
        ("gsplat", "gsplat"),
        ("diff_gaussian_rasterization", "diff_gaussian_rasterization"),
        ("simple_knn", "simple_knn._C"),
        ("pointops", "pointops"),
    ]:
        try:
            __import__(mod)
            report[name] = "ok"
        except Exception as e:  # noqa: BLE001
            report[name] = f"FAIL: {repr(e)}"

    # LHM++ pipeline entry points we will call in later versions.
    for name, mod in [
        ("lhmpp_pose_estimator", "engine.pose_estimation.pose_estimator"),
        ("smpl_anthropometry", "measure"),
    ]:
        try:
            __import__(mod)
            report[name] = "ok"
        except Exception as e:  # noqa: BLE001
            report[name] = f"FAIL: {repr(e)}"

    return report


def handler(event):
    """RunPod serverless entry. v0.1 is a health probe only."""
    inp = (event or {}).get("input", {}) or {}
    return {
        "status": "photoreal endpoint alive",
        "build": os.environ.get("PHOTOREAL_BUILD", "unknown"),
        "echo": inp,
        "selftest": _gpu_selftest(),
    }


if __name__ == "__main__":
    # Boot loudly. A dep conflict inside runpod.serverless (e.g. fastapi/pydantic
    # too old) raises HERE, and the plain `import runpod` build-smoke test cannot
    # see it. Print a flushed traceback before the exit(1) so the worker log shows
    # the real cause instead of a bare "worker exited with exit code 1".
    try:
        print(f"[boot] runpod {runpod.__version__} - starting serverless worker",
              flush=True)
        runpod.serverless.start({"handler": handler})
    except Exception:  # noqa: BLE001
        print("[boot] FATAL: worker failed to start", flush=True)
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        raise
