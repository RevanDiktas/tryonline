#!/usr/bin/env python3
"""
RunPod Serverless entrypoint — single process, normal imports (all modules in /workspace).

Jobs: input.action == "smoke" (default), or "load_assets" with body_url + garment_url.
"""
from __future__ import annotations

import runpod

from load_assets import _load_mesh_from_url, mesh_stats
from worker_core import run_smoke


def handler(job):
    job = job or {}
    inp = job.get("input") or {}
    action = inp.get("action", "smoke")

    if action == "smoke":
        code, details = run_smoke()
        if code != 0:
            return {"error": "smoke_failed", **details}
        return {"ok": True, **details}

    if action == "load_assets":
        body_url = inp.get("body_url")
        garment_url = inp.get("garment_url")
        if not body_url or not garment_url:
            return {"error": "missing_urls", "need": ["body_url", "garment_url"]}
        try:
            body = _load_mesh_from_url(body_url, ".obj")
            garment = _load_mesh_from_url(garment_url, ".glb")
        except Exception as e:
            return {"error": "load_failed", "detail": str(e)}

        return {
            "ok": True,
            "body": mesh_stats("body", body),
            "garment": mesh_stats("garment", garment),
        }

    return {"error": "unknown_action", "action": action, "hint": "smoke | load_assets"}


runpod.serverless.start({"handler": handler})
