#!/usr/bin/env python3
"""Phase 0.5: verify Garment-Warp fork + CUDA from inside the RunPod image."""
from __future__ import annotations

import os
import sys


def run_smoke() -> tuple[int, dict]:
    """
    Returns (exit_code, serializable_details) for RunPod handler / CLI.
    """
    os.environ.setdefault("CUDA_PATH", os.environ.get("CUDA_HOME", "/usr/local/cuda"))

    try:
        import warp as wp
    except ImportError as e:
        print("ERROR: warp import failed:", e, file=sys.stderr)
        return 1, {"warp_import_error": str(e)}

    wp.init()
    devices = wp.get_devices()
    device_strs = [str(d) for d in devices]
    print("Warp OK. Devices:", devices)

    cuda_devices = [d for d in devices if getattr(d, "is_cuda", False) or "cuda" in str(d).lower()]
    warn_cpu = False
    if not cuda_devices:
        print("WARNING: No CUDA Warp device listed; CPU-only fallback may be in use.")
        warn_cpu = True

    import numpy as np

    try:
        import torch

        t = torch.ones(256, device="cuda", dtype=torch.float32)
        a = wp.from_torch(t)
        t2 = wp.to_torch(a)
        if not torch.allclose(t2, torch.ones_like(t2)):
            print("ERROR: Warp <-> Torch round-trip failed.", file=sys.stderr)
            return 1, {"devices": device_strs, "round_trip": "torch_failed"}
        print("GPU smoke: wp.from_torch / wp.to_torch OK.")
        return 0, {
            "devices": device_strs,
            "round_trip": "torch",
            "warn_no_cuda_device": warn_cpu,
        }
    except AttributeError:
        x = wp.array(np.ones(256, dtype=np.float32), device="cuda")
        wp.synchronize()
        y = x.numpy()
        if not np.allclose(y, 1.0):
            print("ERROR: Warp GPU array .numpy() sanity check failed.", file=sys.stderr)
            return 1, {"devices": device_strs, "round_trip": "numpy_failed"}
        print("GPU smoke: wp.array on cuda + .numpy() OK.")
        return 0, {
            "devices": device_strs,
            "round_trip": "numpy",
            "warn_no_cuda_device": warn_cpu,
        }


def main() -> int:
    code, _ = run_smoke()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
