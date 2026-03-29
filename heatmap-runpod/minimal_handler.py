"""Tiny RunPod handler — no Warp/CUDA. Use with Dockerfile.minimal to test RunPod's GitHub builder."""
from __future__ import annotations

import runpod


def handler(job):
    return {"ok": True, "minimal": True, "input": (job or {}).get("input")}


runpod.serverless.start({"handler": handler})
