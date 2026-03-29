#!/usr/bin/env python3
"""
Submit a smoke job to the heatmap RunPod serverless endpoint and poll until completion.

Uses backend/.env (RUNPOD_API_KEY, RUNPOD_HEATMAP_ENDPOINT_ID). Run from repo anywhere:

  cd backend && python scripts/smoke_runpod_heatmap.py

Default payload is {"action": "smoke"} (minimal image ignores it; full worker runs GPU smoke).
Use --action none to send {}. RunPod worker logs "missing field(s): id or input" on some polls when
their API returns a non-job JSON body; that is usually harmless if your jobs still complete.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

# Backend package root
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BACKEND_ROOT)
os.chdir(_BACKEND_ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test RunPod heatmap endpoint")
    parser.add_argument(
        "--action",
        default="smoke",
        help='input.action sent to the worker (default: smoke). Use "none" to send {}.',
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Max seconds to wait (full Warp cold start can be slow)",
    )
    parser.add_argument("--interval", type=float, default=2.0, help="Poll interval seconds")
    args = parser.parse_args()

    try:
        from app.services.runpod import RunPodService
        from app.config import get_settings
    except ImportError as e:
        print(f"Import failed (run from backend/ with deps installed): {e}")
        return 1

    s = get_settings()
    if not (s.runpod_api_key and s.runpod_heatmap_endpoint_id.strip()):
        print("Set RUNPOD_API_KEY and RUNPOD_HEATMAP_ENDPOINT_ID in backend/.env")
        return 1

    if args.action.lower() == "none":
        inp = {}
    else:
        inp = {"action": args.action}

    async def run() -> int:
        svc = RunPodService()
        job_id = await svc.submit_heatmap_job(inp)
        if not job_id:
            return 1
        deadline = asyncio.get_event_loop().time() + args.timeout
        while asyncio.get_event_loop().time() < deadline:
            st = await svc.get_heatmap_job_status(job_id)
            status = st.get("status")
            print(f"  status={status}")
            if status in ("COMPLETED", "FAILED", "CANCELLED", "ERROR"):
                out = st.get("output")
                err = st.get("error")
                if err:
                    print(f"  error: {err}")
                print("output:")
                print(json.dumps(out, indent=2, default=str)[:4000])
                if isinstance(out, dict) and out.get("minimal") is True:
                    print(
                        "\n[!] Endpoint is still the MINIMAL diagnostic image. "
                        "Switch RunPod to heatmap-runpod/Dockerfile or GHCR …/tryonline-heatmap:latest — "
                        "see heatmap-runpod/README.md (section C).\n"
                    )
                return 0 if status == "COMPLETED" and not err else 1
            await asyncio.sleep(args.interval)
        print("Timed out waiting for job")
        return 1

    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
