#!/usr/bin/env python3
"""Phase 0.5: verify Garment-Warp fork + CUDA from inside the RunPod image."""
from __future__ import annotations

import os
import sys


def main() -> int:
    os.environ.setdefault("CUDA_PATH", os.environ.get("CUDA_HOME", "/usr/local/cuda"))

    try:
        import warp as wp
    except ImportError as e:
        print("ERROR: warp import failed:", e, file=sys.stderr)
        return 1

    wp.init()
    devices = wp.get_devices()
    print("Warp OK. Devices:", devices)

    cuda_devices = [d for d in devices if getattr(d, "is_cuda", False) or "cuda" in str(d).lower()]
    if not cuda_devices:
        print("WARNING: No CUDA Warp device listed; CPU-only fallback may be in use.")

    import numpy as np

    try:
        import torch

        t = torch.ones(256, device="cuda", dtype=torch.float32)
        a = wp.from_torch(t)
        t2 = wp.to_torch(a)
        if not torch.allclose(t2, torch.ones_like(t2)):
            print("ERROR: Warp <-> Torch round-trip failed.", file=sys.stderr)
            return 1
        print("GPU smoke: wp.from_torch / wp.to_torch OK.")
    except AttributeError:
        x = wp.array(np.ones(256, dtype=np.float32), device="cuda")
        wp.synchronize()
        y = x.numpy()
        if not np.allclose(y, 1.0):
            print("ERROR: Warp GPU array .numpy() sanity check failed.", file=sys.stderr)
            return 1
        print("GPU smoke: wp.array on cuda + .numpy() OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
