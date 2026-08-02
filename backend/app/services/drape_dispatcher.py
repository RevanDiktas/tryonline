"""
Drape dispatcher
================

Background loop that wakes every TICK_SECONDS, atomically claims up to
DISPATCH_BATCH queued jobs (via the `claim_drape_jobs` RPC), and POSTs each to
RunPod's async endpoint with a webhook back to our callback route.

The actual upload-and-cache step happens in the webhook handler, not here. This
module's only job is "queued -> dispatched (running on RunPod)".

Configuration via env:
  - RUNPOD_DRAPING_ENDPOINT_ID  (required; otherwise dispatcher logs and skips)
  - BACKEND_PUBLIC_URL          (required; used to build webhook URL)
  - DRAPE_DISPATCHER_INTERVAL   (seconds, default 30)
  - DRAPE_DISPATCH_BATCH        (max jobs claimed per tick, default 4)
"""

from __future__ import annotations

import asyncio
import os
from typing import Optional

import httpx

from app.config import get_settings
from app.services.supabase import supabase_service

settings = get_settings()


TICK_SECONDS = int(os.getenv("DRAPE_DISPATCHER_INTERVAL", "30"))
DISPATCH_BATCH = int(os.getenv("DRAPE_DISPATCH_BATCH", "4"))


def _resolve_storage_url(path: str) -> str:
    if not path:
        return ""
    if path.startswith("http"):
        return path
    base = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/public"
    return f"{base}/{path.lstrip('/')}"


def _webhook_url() -> Optional[str]:
    base = (settings.backend_public_url or "").rstrip("/")
    if not base:
        return None
    return f"{base}/api/draping/runpod-callback"


def _build_runpod_payload(job: dict) -> Optional[dict]:
    """Look up the live body OBJ + garment OBJ for this job and build the
    RunPod input payload. Returns None if either side is missing (caller marks
    the job failed)."""
    user_id = job["user_id"]
    garment_id = job["garment_id"]
    size = job["size"]

    fp = supabase_service.client.table("fit_passports").select(
        "pipeline_files,avatar_url"
    ).eq("user_id", user_id).limit(1).execute()
    if not fp.data:
        return None
    pf = fp.data[0].get("pipeline_files") or {}
    body_obj = pf.get("apose_mesh") or pf.get("tpose_mesh") or pf.get("original_mesh")
    if not body_obj:
        return None

    g = supabase_service.client.table("garments").select(
        "obj_sizes,fabric_config,category"
    ).eq("id", garment_id).limit(1).execute()
    if not g.data:
        return None
    obj_sizes = g.data[0].get("obj_sizes") or {}
    garment_obj = obj_sizes.get(size)
    if not garment_obj:
        return None

    return {
        "input": {
            "body_obj_url": _resolve_storage_url(body_obj),
            "garment_obj_url": _resolve_storage_url(garment_obj),
            "smpl_params_url": _resolve_storage_url(pf.get("smpl_params") or "") or None,
            "fabric_config": g.data[0].get("fabric_config") or {},
            # v46: the handler anchors PARTIAL garments anatomically by
            # category — tops at the shoulder, bottoms at the hip crest.
            # Without it a t-shirt's hem is matched to the avatar's feet.
            # Full-body garments ignore this and keep feet-matching.
            "category": g.data[0].get("category"),
            "simulation_mode": "swift",
            "garment_id": garment_id,
            "size": size,
            "user_id": user_id,
            "drape_job_id": str(job["id"]),
            "garment_version_hash": job["garment_version_hash"],
            "body_hash": job["body_hash"],
        }
    }


def _mark_failed(job_id: str, msg: str, retryable: bool) -> None:
    """Either kick a job back to queued (if attempts < max) or terminal-fail."""
    try:
        r = supabase_service.client.table("drape_jobs").select(
            "attempts,max_attempts"
        ).eq("id", job_id).limit(1).execute()
        if not r.data:
            return
        attempts = r.data[0].get("attempts") or 0
        max_a = r.data[0].get("max_attempts") or 3
        if retryable and attempts < max_a:
            supabase_service.client.table("drape_jobs").update({
                "status": "queued",
                "error_message": msg[:500],
            }).eq("id", job_id).execute()
        else:
            supabase_service.client.table("drape_jobs").update({
                "status": "failed",
                "error_message": msg[:500],
            }).eq("id", job_id).execute()
    except Exception as e:
        print(f"[drape_dispatcher] _mark_failed bookkeeping error: {e}")


async def _dispatch_one(client: httpx.AsyncClient, job: dict) -> None:
    job_id = str(job["id"])
    payload = _build_runpod_payload(job)
    if payload is None:
        _mark_failed(job_id, "Missing body or garment OBJ at dispatch time", retryable=False)
        return

    webhook = _webhook_url()
    if webhook:
        payload["webhook"] = webhook

    run_url = f"https://api.runpod.ai/v2/{settings.runpod_draping_endpoint_id}/run"
    headers = {"Authorization": f"Bearer {settings.runpod_api_key}"}

    try:
        resp = await client.post(run_url, json=payload, headers=headers, timeout=30.0)
        resp.raise_for_status()
        body = resp.json()
    except Exception as e:
        _mark_failed(job_id, f"RunPod /run failed: {e}", retryable=True)
        return

    runpod_job_id = body.get("id")
    if not runpod_job_id:
        _mark_failed(job_id, f"RunPod /run returned no id: {body}", retryable=True)
        return

    supabase_service.client.table("drape_jobs").update({
        "status": "running",
        "runpod_job_id": runpod_job_id,
    }).eq("id", job_id).execute()


def _claim_jobs(limit_n: int) -> list[dict]:
    try:
        r = supabase_service.client.rpc(
            "claim_drape_jobs", {"limit_n": limit_n}
        ).execute()
        return r.data or []
    except Exception as e:
        print(f"[drape_dispatcher] claim_drape_jobs RPC failed: {e}")
        return []


async def _tick() -> None:
    if not settings.runpod_api_key or not settings.runpod_draping_endpoint_id:
        return
    if not _webhook_url():
        # Without a webhook target we cannot complete jobs. Don't dispatch.
        return

    jobs = _claim_jobs(DISPATCH_BATCH)
    if not jobs:
        return

    print(f"[drape_dispatcher] claimed {len(jobs)} jobs")
    async with httpx.AsyncClient() as client:
        await asyncio.gather(*[_dispatch_one(client, j) for j in jobs])


async def dispatcher_loop(stop_event: asyncio.Event) -> None:
    """Long-running coroutine. Owned by the FastAPI lifespan."""
    print(f"[drape_dispatcher] started (tick={TICK_SECONDS}s, batch={DISPATCH_BATCH})")
    try:
        while not stop_event.is_set():
            try:
                await _tick()
            except Exception as e:
                print(f"[drape_dispatcher] tick error: {e}")
                import traceback
                traceback.print_exc()
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=TICK_SECONDS)
            except asyncio.TimeoutError:
                continue
    finally:
        print("[drape_dispatcher] stopped")
