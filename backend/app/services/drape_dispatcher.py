"""
Drape dispatcher
================

Background loop that wakes every TICK_SECONDS (or at once when the widget asks for a
drape), atomically claims queued jobs (via the `claim_drape_jobs` RPC, lowest priority
number first), and POSTs each to RunPod's async endpoint with a webhook back to our
callback route.

RunPod only gets as many jobs as it can run (MAX_IN_FLIGHT, the endpoint's worker
count). Everything else waits in drape_jobs, where priority decides what goes next.
Measured 2026-10-05: handing RunPod every job at once left 39 in its first-come queue,
so the garment a shopper was looking at waited ~23 min for a 30-75 s drape.

The actual upload-and-cache step happens in the webhook handler, not here. This
module's only job is "queued -> dispatched (running on RunPod)".

Configuration via env:
  - RUNPOD_DRAPING_ENDPOINT_ID  (required; otherwise dispatcher logs and skips)
  - BACKEND_PUBLIC_URL          (required; used to build webhook URL)
  - DRAPE_DISPATCHER_INTERVAL   (seconds, default 30)
  - DRAPE_DISPATCH_BATCH        (max jobs claimed per tick, default 4)
  - DRAPE_MAX_IN_FLIGHT         (jobs RunPod may hold, queued + running; default 2,
                                 the drape endpoint's max workers)
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.config import get_settings
from app.services.supabase import supabase_service

settings = get_settings()


TICK_SECONDS = int(os.getenv("DRAPE_DISPATCHER_INTERVAL", "30"))
DISPATCH_BATCH = int(os.getenv("DRAPE_DISPATCH_BATCH", "4"))
MAX_IN_FLIGHT = int(os.getenv("DRAPE_MAX_IN_FLIGHT", "2"))
# Without RunPod's own count, a job dispatched longer ago than this no longer holds a slot
# (a lost webhook must not stall the queue). A drape runs in 30-75 s plus a cold start.
IN_FLIGHT_WINDOW_SECONDS = 15 * 60

_wake: Optional[asyncio.Event] = None


def wake_dispatcher() -> None:
    """Run a tick now instead of at the next interval (a shopper is waiting)."""
    if _wake is not None:
        _wake.set()


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
    from app.services.body_clustering import body_mesh_path
    pf = fp.data[0].get("pipeline_files") or {}
    body_obj = body_mesh_path(fp.data[0])  # same file the body hash identifies
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
            # Without a service key the handler base64-inlines the OBJ, GLB and
            # every texture into its HTTP response. RunPod rejects any output
            # over ~20MB with a 400 on job-done but still reports the job
            # COMPLETED, so the callback sees `output: {}` and retries until
            # the job burns its attempts. Measured on the La Fam jeans: ~22MB,
            # 220s of good simulation discarded three times over. With the key
            # the handler uploads to draped-artifacts and returns short URLs.
            "supabase_service_key": settings.supabase_service_key,
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


async def _runpod_backlog(client: httpx.AsyncClient) -> Optional[int]:
    """Jobs RunPod holds for the drape endpoint (queued + running), from its health
    route. Counts every source, including jobs whose webhook never came back."""
    url = f"https://api.runpod.ai/v2/{settings.runpod_draping_endpoint_id}/health"
    try:
        resp = await client.get(url, headers={"Authorization": f"Bearer {settings.runpod_api_key}"}, timeout=10.0)
        resp.raise_for_status()
        jobs = resp.json().get("jobs") or {}
        return int(jobs.get("inQueue") or 0) + int(jobs.get("inProgress") or 0)
    except Exception as e:
        print(f"[drape_dispatcher] RunPod health failed, counting from drape_jobs: {e}")
        return None


def _db_in_flight() -> int:
    """Fallback count: our jobs handed to RunPod recently and not finished."""
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=IN_FLIGHT_WINDOW_SECONDS)).isoformat()
    try:
        r = supabase_service.client.table("drape_jobs").select("id").in_(
            "status", ["dispatched", "running"]
        ).gte("dispatched_at", cutoff).execute()
        return len(r.data or [])
    except Exception as e:
        print(f"[drape_dispatcher] in-flight count failed: {e}")
        return MAX_IN_FLIGHT   # unknown: dispatch nothing this tick


def _free_slots(backlog: int) -> int:
    return max(0, min(DISPATCH_BATCH, MAX_IN_FLIGHT - backlog))


async def _tick() -> None:
    if not settings.runpod_api_key or not settings.runpod_draping_endpoint_id:
        return
    if not _webhook_url():
        # Without a webhook target we cannot complete jobs. Don't dispatch.
        return

    async with httpx.AsyncClient() as client:
        backlog = await _runpod_backlog(client)
        if backlog is None:
            backlog = _db_in_flight()
        free = _free_slots(backlog)
        if free == 0:
            return

        jobs = _claim_jobs(free)
        if not jobs:
            return

        print(f"[drape_dispatcher] claimed {len(jobs)} jobs (RunPod held {backlog})")
        await asyncio.gather(*[_dispatch_one(client, j) for j in jobs])


async def dispatcher_loop(stop_event: asyncio.Event) -> None:
    """Long-running coroutine. Owned by the FastAPI lifespan."""
    global _wake
    _wake = asyncio.Event()
    print(f"[drape_dispatcher] started (tick={TICK_SECONDS}s, batch={DISPATCH_BATCH}, max_in_flight={MAX_IN_FLIGHT})")
    try:
        while not stop_event.is_set():
            _wake.clear()
            try:
                await _tick()
            except Exception as e:
                print(f"[drape_dispatcher] tick error: {e}")
                import traceback
                traceback.print_exc()
            # Sleep until the interval passes, a shopper asks for a drape, or shutdown.
            waiters = [asyncio.ensure_future(stop_event.wait()), asyncio.ensure_future(_wake.wait())]
            try:
                await asyncio.wait(waiters, timeout=TICK_SECONDS, return_when=asyncio.FIRST_COMPLETED)
            finally:
                for w in waiters:
                    w.cancel()
    finally:
        _wake = None
        print("[drape_dispatcher] stopped")
