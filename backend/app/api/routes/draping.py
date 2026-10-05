"""
Cloth Draping API — request simulation, poll status, retrieve draped meshes.

Endpoints:
- POST /api/draping/request           — trigger draping for a garment+size+user
- GET  /api/draping/status/{id}       — poll draping job status
- GET  /api/draping/check             — quick cache check (does draped mesh exist?)
- POST /api/draping/runpod-callback   — RunPod webhook -> writes draped_meshes
- POST /api/draping/backfill          — admin fan-out for existing avatars
- GET  /api/draping/admin/queue       — admin queue counters
"""

import base64
import os
from typing import Optional, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from pydantic import BaseModel

from app.api.deps import UserAccess

from app.config import get_settings
from app.services.supabase import SupabaseService

router = APIRouter()
settings = get_settings()
supabase = SupabaseService()


CALLBACK_TOKEN = os.getenv("DRAPE_CALLBACK_TOKEN", "")


def _body_identity(user_id: str):
    """Per-user, per-avatar body identity (see body_clustering): `.body_hash` is the
    write key, `.lookup_hashes` the read keys (new first, legacy measurement hash as a
    fallback while rows are migrated). Measurement edits don't change it."""
    from app.services.body_clustering import body_identity_for_user
    ident = body_identity_for_user(user_id)
    return ident if ident and ident.body_hash else None


def _cached_drape_url(garment_id: str, size: str, lookup_hashes: list) -> Optional[str]:
    """draped_glb_url for this garment+size under the preferred available body hash."""
    from app.services.body_clustering import pick_by_hash_preference
    r = supabase.client.table("draped_meshes").select("size,body_hash,draped_glb_url").eq(
        "garment_id", garment_id
    ).eq("size", size).in_("body_hash", lookup_hashes).execute()
    rows = [row for row in (r.data or []) if row.get("draped_glb_url")]
    best = pick_by_hash_preference(rows, lookup_hashes).get(size)
    return best["draped_glb_url"] if best else None


def _get_garment_draping_info(garment_id: str, size: str) -> Optional[dict]:
    """Fetch garment's OBJ path and fabric config for the given size."""
    try:
        r = supabase.client.table("garments").select(
            "obj_sizes,fabric_config,sizes"
        ).eq("id", garment_id).limit(1).execute()
        if not r.data:
            return None
        garment = r.data[0]
        obj_sizes = garment.get("obj_sizes") or {}
        obj_path = obj_sizes.get(size)
        if not obj_path:
            return None
        return {
            "obj_path": obj_path,
            "fabric_config": garment.get("fabric_config") or {},
            "glb_path": (garment.get("sizes") or {}).get(size),
        }
    except Exception:
        return None


class TestRunRequest(BaseModel):
    body_obj_url: str
    garment_obj_url: str
    fabric_preset: str = "cotton_medium"
    simulation_mode: str = "swift"
    # v46: anchors partial garments anatomically (tops -> shoulder,
    # bottoms -> hip). Omit for full-body garments; they feet-match.
    category: Optional[str] = None


@router.post("/test-run")
async def test_drape_run(body: TestRunRequest):
    """
    Direct draping test — no auth, no DB, no garment IDs.
    Sends raw OBJ URLs to RunPod and returns the result.
    For internal testing only.
    """
    import httpx

    if not settings.runpod_api_key or not settings.runpod_draping_endpoint_id:
        raise HTTPException(
            status_code=503,
            detail="RUNPOD_DRAPING_ENDPOINT_ID not configured on this backend"
        )

    runpod_payload = {
        "input": {
            "body_obj_url": body.body_obj_url,
            "garment_obj_url": body.garment_obj_url,
            "fabric_config": {"preset": body.fabric_preset},
            "simulation_mode": body.simulation_mode,
            "category": body.category,
            "garment_id": "test",
            "size": "test",
            "user_id": "test",
        }
    }

    run_url = f"https://api.runpod.ai/v2/{settings.runpod_draping_endpoint_id}/runsync"
    headers = {"Authorization": f"Bearer {settings.runpod_api_key}"}

    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(run_url, json=runpod_payload, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"RunPod error: {resp.text[:500]}")
        result = resp.json()

    output = result.get("output", {})
    if not output.get("success"):
        raise HTTPException(status_code=500, detail=output.get("error", "Unknown error"))

    # If we have GLB bytes, upload to temp storage so the viewer can load it
    glb_url = None
    if output.get("draped_glb_base64"):
        try:
            import uuid as _uuid
            glb_bytes = base64.b64decode(output["draped_glb_base64"])
            storage_path = f"draped/_test/{_uuid.uuid4().hex}.glb"
            supabase.ensure_garments_bucket()
            bucket = supabase.client.storage.from_(settings.garments_bucket)
            try:
                bucket.upload(storage_path, glb_bytes, {"content-type": "model/gltf-binary", "x-upsert": "true"})
            except Exception:
                bucket.update(storage_path, glb_bytes, {"content-type": "model/gltf-binary"})
            glb_url = bucket.get_public_url(storage_path)
        except Exception as e:
            print(f"[Draping test-run] Failed to upload GLB: {e}")

    return {
        "success": True,
        "simulation_method": output.get("simulation_method"),
        "vertex_count": output.get("vertex_count"),
        "processing_time_seconds": output.get("processing_time_seconds"),
        "draped_glb_url": glb_url,
        "draped_glb_base64": output.get("draped_glb_base64") if not glb_url else None,
    }


class DrapingRequest(BaseModel):
    garment_id: str
    size: str
    user_id: str
    # The size the try-on is showing right now: drapes first. Other sizes of the open
    # garment come right after it.
    on_screen: bool = False


class DrapingResponse(BaseModel):
    request_id: str
    status: str
    draped_url: Optional[str] = None
    cached: bool = False


@router.post("/request", response_model=DrapingResponse)
async def request_draping(body: DrapingRequest, background_tasks: BackgroundTasks):
    """
    The try-on has this garment+size open: return the cached drape, or put this shopper's
    drape job at the front of the queue and return an id to poll (`job:<drape_job id>`).

    Same drape_jobs row as the fan-out after onboarding, run by the same dispatcher, so the
    garment is never draped twice and the result lands in draped_meshes either way.
    """
    ident = _body_identity(body.user_id)
    if not ident:
        raise HTTPException(status_code=400, detail="User has no body data (fit passport required)")

    garment_info = _get_garment_draping_info(body.garment_id, body.size)
    if not garment_info:
        raise HTTPException(status_code=404, detail="No OBJ mesh for this garment+size")

    # Check cache first (new hash, then legacy while rows are migrated)
    try:
        url = _cached_drape_url(body.garment_id, body.size, ident.lookup_hashes)
        if url:
            return DrapingResponse(
                request_id="cached",
                status="completed",
                draped_url=url,
                cached=True,
            )
    except Exception:
        pass

    from app.services.drape_dispatcher import wake_dispatcher
    from app.services.drape_queue import PRIORITY_IN_VIEWER, PRIORITY_ON_SCREEN, prioritize_drape

    priority = PRIORITY_ON_SCREEN if body.on_screen else PRIORITY_IN_VIEWER
    job = prioritize_drape(body.user_id, body.garment_id, body.size, priority)
    if not job:
        raise HTTPException(status_code=404, detail="Nothing to drape for this garment+size")
    if job.get("status") == "failed":
        return DrapingResponse(request_id=f"job:{job['id']}", status="failed")
    wake_dispatcher()
    # This garment was not ready for this shopper, so others may be missing too: queue the
    # rest behind it, after the response is sent.
    from app.services.drape_queue import fill_drape_gaps
    background_tasks.add_task(fill_drape_gaps, body.user_id)
    return DrapingResponse(request_id=f"job:{job['id']}", status="pending")


class DrapingStatusResponse(BaseModel):
    request_id: str
    status: str
    draped_url: Optional[str] = None
    error: Optional[str] = None
    simulation_method: Optional[str] = None


@router.get("/status/{request_id}", response_model=DrapingStatusResponse)
async def get_draping_status(request_id: str):
    """Poll draping job status. Returns draped_url when complete."""
    if request_id == "cached":
        return DrapingStatusResponse(request_id="cached", status="completed")
    if request_id.startswith("job:"):
        return _drape_job_status(request_id)

    try:
        r = supabase.client.table("draping_requests").select(
            "id,status,error_message,draped_mesh_id"
        ).eq("id", request_id).limit(1).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not r.data:
        raise HTTPException(status_code=404, detail="Draping request not found")

    req = r.data[0]
    draped_url = None
    sim_method = None

    if req.get("draped_mesh_id"):
        try:
            mesh = supabase.client.table("draped_meshes").select(
                "draped_glb_url,simulation_method"
            ).eq("id", req["draped_mesh_id"]).limit(1).execute()
            if mesh.data:
                draped_url = mesh.data[0].get("draped_glb_url")
                sim_method = mesh.data[0].get("simulation_method")
        except Exception:
            pass

    return DrapingStatusResponse(
        request_id=str(req["id"]),
        status=req["status"],
        draped_url=draped_url,
        error=req.get("error_message"),
        simulation_method=sim_method,
    )


def _drape_job_status(request_id: str) -> DrapingStatusResponse:
    """Status of a drape job started or moved up by /request: the drape itself is read from
    the draped_meshes cache, which the RunPod callback fills."""
    job_id = request_id[len("job:"):]
    try:
        r = supabase.client.table("drape_jobs").select(
            "id,user_id,garment_id,size,status,error_message"
        ).eq("id", job_id).limit(1).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not r.data:
        raise HTTPException(status_code=404, detail="Draping request not found")
    job = r.data[0]
    status = job.get("status")
    if status == "completed":
        ident = _body_identity(job["user_id"])
        url = _cached_drape_url(job["garment_id"], job["size"], ident.lookup_hashes) if ident else None
        if url:
            return DrapingStatusResponse(request_id=request_id, status="completed", draped_url=url)
        return DrapingStatusResponse(request_id=request_id, status="failed", error="Drape finished but no mesh was saved")
    if status in ("failed", "cancelled"):
        return DrapingStatusResponse(request_id=request_id, status="failed", error=job.get("error_message"))
    return DrapingStatusResponse(request_id=request_id, status="processing")


class DrapingCheckResponse(BaseModel):
    has_cached: bool
    draped_url: Optional[str] = None
    has_obj: bool = False


@router.get("/check", response_model=DrapingCheckResponse)
async def check_draping_cache(
    garment_id: str = Query(...),
    size: str = Query(...),
    user_id: str = Query(...),
    _access: None = Depends(UserAccess("drape check")),
):
    """Quick check: does a draped mesh exist for this garment+size+user?"""
    ident = _body_identity(user_id)
    if not ident:
        return DrapingCheckResponse(has_cached=False, has_obj=False)

    garment_info = _get_garment_draping_info(garment_id, size)
    has_obj = garment_info is not None

    try:
        url = _cached_drape_url(garment_id, size, ident.lookup_hashes)
        if url:
            return DrapingCheckResponse(has_cached=True, draped_url=url, has_obj=has_obj)
    except Exception:
        pass

    return DrapingCheckResponse(has_cached=False, has_obj=has_obj)


class PrecomputeRequest(BaseModel):
    garment_id: str
    sizes: list[str]
    n_buckets: int = 50


class PrecomputeResponse(BaseModel):
    total_jobs: int
    already_cached: int
    new_jobs_queued: int


@router.post("/precompute", response_model=PrecomputeResponse)
async def precompute_draping(body: PrecomputeRequest, background_tasks: BackgroundTasks):
    """
    Pre-compute draped meshes for representative body shapes.
    Generates ~n_buckets body shape buckets and queues draping for each
    garment+size+bucket combo that isn't already cached.
    """
    from app.services.body_clustering import generate_representative_bodies

    bodies = generate_representative_bodies(body.n_buckets)
    total = 0
    cached = 0
    queued = 0

    for size in body.sizes:
        garment_info = _get_garment_draping_info(body.garment_id, size)
        if not garment_info:
            continue

        for b in bodies:
            total += 1
            bucket = b["bucket"]

            try:
                existing = supabase.client.table("draped_meshes").select("id").eq(
                    "garment_id", body.garment_id
                ).eq("size", size).eq("body_hash", bucket).limit(1).execute()
                if existing.data:
                    cached += 1
                    continue
            except Exception:
                pass

            queued += 1

    return PrecomputeResponse(
        total_jobs=total,
        already_cached=cached,
        new_jobs_queued=queued,
    )


@router.get("/stats")
async def draping_stats():
    """Get draping cache statistics."""
    try:
        total_cached = supabase.client.table("draped_meshes").select(
            "id", count="exact"
        ).execute()
        total_requests = supabase.client.table("draping_requests").select(
            "id", count="exact"
        ).execute()
        pending = supabase.client.table("draping_requests").select(
            "id", count="exact"
        ).in_("status", ["pending", "processing"]).execute()
        failed = supabase.client.table("draping_requests").select(
            "id", count="exact"
        ).eq("status", "failed").execute()

        return {
            "cached_meshes": total_cached.count or 0,
            "total_requests": total_requests.count or 0,
            "pending_requests": pending.count or 0,
            "failed_requests": failed.count or 0,
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Pre-drape: RunPod webhook callback
# ---------------------------------------------------------------------------


def _check_callback_token(token: Optional[str]) -> None:
    if CALLBACK_TOKEN and token != CALLBACK_TOKEN:
        raise HTTPException(status_code=401, detail="Bad callback token")


def _persist_drape_result(job: dict, output: dict) -> None:
    """Upload GLB, upsert draped_meshes, mark drape_jobs completed.
    Idempotent: re-running with the same job/output is a no-op (storage upsert,
    DB upsert)."""
    # The handler returns the GLB one of two ways. Given a Supabase service key
    # it uploads to the draped-artifacts bucket and sends back a URL; otherwise
    # it base64-inlines the bytes. The inline form is capped by RunPod at ~20MB
    # and silently dropped above that, so the URL is the path that scales.
    glb_b64 = output.get("draped_glb_base64") or ""
    glb_url = output.get("draped_glb_url") or ""
    if glb_b64:
        glb_bytes = base64.b64decode(glb_b64)
    elif glb_url:
        with httpx.Client(timeout=300.0, follow_redirects=True) as client:
            r = client.get(glb_url)
            r.raise_for_status()
            glb_bytes = r.content
    else:
        raise ValueError("No draped_glb_base64 or draped_glb_url in RunPod output")
    garment_id = job["garment_id"]
    size = job["size"]
    body_hash = job["body_hash"]
    version = job["garment_version_hash"]
    storage_path = f"draped/{garment_id}/{version}/{size}/{body_hash}.glb"

    supabase.ensure_garments_bucket()
    bucket = supabase.client.storage.from_(settings.garments_bucket)
    try:
        bucket.upload(
            storage_path, glb_bytes,
            {"content-type": "model/gltf-binary", "x-upsert": "true"},
        )
    except Exception:
        bucket.update(storage_path, glb_bytes, {"content-type": "model/gltf-binary"})

    draped_url = bucket.get_public_url(storage_path)

    mesh_row = supabase.client.table("draped_meshes").upsert({
        "garment_id": garment_id,
        "size": size,
        "body_hash": body_hash,
        "garment_version_hash": version,
        "draped_glb_url": draped_url,
        "simulation_method": output.get("simulation_method", "unknown"),
        "processing_time_seconds": output.get("processing_time_seconds"),
        "vertex_count": output.get("vertex_count"),
    }, on_conflict="garment_id,size,body_hash").execute()

    mesh_id = mesh_row.data[0]["id"] if mesh_row.data else None

    supabase.client.table("drape_jobs").update({
        "status": "completed",
        "draped_mesh_id": mesh_id,
        "completed_at": "now()",
        "error_message": None,
    }).eq("id", job["id"]).execute()


def _mark_job_failed_or_retry(job: dict, msg: str) -> None:
    """Either kick back to queued or terminal-fail, based on attempts."""
    attempts = job.get("attempts") or 0
    max_a = job.get("max_attempts") or 3
    if attempts < max_a:
        supabase.client.table("drape_jobs").update({
            "status": "queued",
            "runpod_job_id": None,
            "error_message": msg[:500],
        }).eq("id", job["id"]).execute()
    else:
        supabase.client.table("drape_jobs").update({
            "status": "failed",
            "error_message": msg[:500],
        }).eq("id", job["id"]).execute()


@router.post("/runpod-callback")
async def runpod_callback(request: Request, token: Optional[str] = Query(None)):
    """
    Webhook target for RunPod async jobs. Idempotent on runpod_job_id: if the
    same callback fires twice (RunPod retries up to 2x), the second call lands
    on a 'completed' or 'failed' job and is a no-op.
    """
    _check_callback_token(token)

    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Bad JSON: {e}")

    runpod_job_id = body.get("id") or ""
    rp_status = (body.get("status") or "").upper()
    output: dict[str, Any] = body.get("output") or {}
    rp_error = body.get("error")

    if not runpod_job_id:
        return {"ok": False, "reason": "missing job id"}

    job_q = supabase.client.table("drape_jobs").select(
        "*"
    ).eq("runpod_job_id", runpod_job_id).limit(1).execute()
    if not job_q.data:
        # Could be a stale callback for a job we already pruned. Don't 500.
        print(f"[draping] callback for unknown runpod_job_id={runpod_job_id}")
        return {"ok": True, "reason": "unknown job"}

    job = job_q.data[0]
    if job.get("status") in ("completed", "failed", "cancelled"):
        return {"ok": True, "reason": "already terminal"}

    if rp_status == "COMPLETED" and output.get("success"):
        try:
            _persist_drape_result(job, output)
            return {"ok": True}
        except Exception as e:
            print(f"[draping] persist failed for job {job['id']}: {e}")
            import traceback; traceback.print_exc()
            _mark_job_failed_or_retry(job, f"persist error: {e}")
            return {"ok": False, "reason": "persist error"}

    msg = rp_error or output.get("error") or f"RunPod status={rp_status}"
    _mark_job_failed_or_retry(job, str(msg))
    return {"ok": True, "reason": "marked failed/retry"}


# ---------------------------------------------------------------------------
# Pre-drape: admin / backfill
# ---------------------------------------------------------------------------


def _check_admin(authorization: Optional[str]) -> None:
    """Cheap admin gate: header-based shared secret. Replace with proper
    Supabase RLS-via-JWT once we have an admin role wired."""
    expected = os.getenv("DRAPE_ADMIN_TOKEN", "")
    if not expected:
        return  # dev: no token configured -> open
    if not authorization or authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Admin token required")


class BackfillRequest(BaseModel):
    brand_id: Optional[str] = None
    user_ids: Optional[list[str]] = None
    priority: int = 200
    dry_run: bool = False


class BackfillResponse(BaseModel):
    users_processed: int
    enqueued: int
    skipped_no_obj: int
    skipped_already_cached: int
    skipped_already_queued: int
    skipped_no_passport: int
    dry_run: bool


@router.post("/backfill", response_model=BackfillResponse)
async def backfill_existing_avatars(
    body: BackfillRequest,
    request: Request,
):
    """
    Walk all completed fit_passports (optionally filtered) and enqueue drape
    jobs against every active garment x size for the given brand (or all
    brands if brand_id omitted).

    Idempotent: re-runs are safe. Existing cached rows and queued jobs are
    skipped.
    """
    _check_admin(request.headers.get("authorization"))

    from app.services.drape_queue import enqueue_full_drape

    brand_ids = [body.brand_id] if body.brand_id else None

    if body.user_ids:
        user_ids = body.user_ids
    else:
        users_q = supabase.client.table("fit_passports").select(
            "user_id"
        ).eq("status", "completed").order("updated_at", desc=True).execute()
        user_ids = [u["user_id"] for u in (users_q.data or []) if u.get("user_id")]

    totals = dict(enqueued=0, skipped_no_obj=0, skipped_already_cached=0,
                  skipped_already_queued=0, skipped_no_passport=0)

    if body.dry_run:
        return BackfillResponse(
            users_processed=len(user_ids),
            **totals,
            dry_run=True,
        )

    for uid in user_ids:
        counts = enqueue_full_drape(uid, priority=body.priority, brand_ids=brand_ids)
        for k in totals:
            totals[k] += counts.get(k, 0)

    return BackfillResponse(
        users_processed=len(user_ids),
        **totals,
        dry_run=False,
    )


@router.get("/admin/queue")
async def admin_queue_status(request: Request):
    """Counters for the admin page: queue depth by status + cache sizes."""
    _check_admin(request.headers.get("authorization"))

    counts: dict[str, int] = {
        "queued": 0, "dispatched": 0, "running": 0,
        "completed": 0, "failed": 0, "cancelled": 0, "skipped_cache_hit": 0,
    }
    try:
        r = supabase.client.rpc("drape_job_status_counts").execute()
        for row in r.data or []:
            counts[row["status"]] = int(row["count"])
    except Exception as e:
        print(f"[draping] admin/queue rpc failed: {e}")

    try:
        cached = supabase.client.table("draped_meshes").select(
            "id", count="exact"
        ).execute()
        cache_size = cached.count or 0
    except Exception:
        cache_size = 0

    try:
        avatars = supabase.client.table("fit_passports").select(
            "user_id", count="exact"
        ).eq("status", "completed").execute()
        avatar_count = avatars.count or 0
    except Exception:
        avatar_count = 0

    try:
        garments_q = supabase.client.table("garments").select(
            "id", count="exact"
        ).eq("is_active", True).execute()
        garment_count = garments_q.count or 0
    except Exception:
        garment_count = 0

    return {
        "jobs": counts,
        "cached_meshes": cache_size,
        "completed_avatars": avatar_count,
        "active_garments": garment_count,
    }


class DrainRequest(BaseModel):
    confirm: bool = False


@router.post("/admin/drain")
async def admin_drain_queue(body: DrainRequest, request: Request):
    """Cancels all queued drape jobs. Running/dispatched jobs continue."""
    _check_admin(request.headers.get("authorization"))
    if not body.confirm:
        raise HTTPException(status_code=400, detail="confirm: true required")
    r = supabase.client.table("drape_jobs").update({
        "status": "cancelled"
    }).eq("status", "queued").execute()
    return {"cancelled": len(r.data or [])}
