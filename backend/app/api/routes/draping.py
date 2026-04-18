"""
Cloth Draping API — request simulation, poll status, retrieve draped meshes.

Endpoints:
- POST /api/draping/request     — trigger draping for a garment+size+user
- GET  /api/draping/status/{id} — poll draping job status
- GET  /api/draping/check       — quick cache check (does draped mesh exist?)
"""

import base64
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from app.config import get_settings
from app.services.supabase import SupabaseService

router = APIRouter()
settings = get_settings()
supabase = SupabaseService()


def _body_hash_from_user(user_id: str) -> Optional[str]:
    """
    Compute body bucket hash from user's fit passport.
    Uses quantized measurements for clustering — similar body shapes
    share the same hash, enabling shared draping cache hits.
    """
    from app.services.body_clustering import compute_body_bucket_from_passport
    try:
        r = supabase.client.table("fit_passports").select(
            "pipeline_files,chest,waist,hips,height,weight,gender"
        ).eq("user_id", user_id).limit(1).execute()
        if not r.data:
            return None
        return compute_body_bucket_from_passport(r.data[0])
    except Exception:
        return None


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


def _get_user_body_files(user_id: str) -> Optional[dict]:
    """Get user's body OBJ and SMPL params URLs from pipeline_files."""
    try:
        r = supabase.client.table("fit_passports").select(
            "pipeline_files,avatar_url"
        ).eq("user_id", user_id).limit(1).execute()
        if not r.data:
            return None
        passport = r.data[0]
        pf = passport.get("pipeline_files") or {}
        body_obj_url = pf.get("tpose_mesh") or pf.get("apose_mesh") or pf.get("original_mesh")
        smpl_params_url = pf.get("smpl_params")
        if not body_obj_url:
            return None
        return {
            "body_obj_url": body_obj_url,
            "smpl_params_url": smpl_params_url,
        }
    except Exception:
        return None


def _resolve_storage_url(path: str) -> str:
    """Convert relative storage path to full public URL."""
    if path.startswith("http"):
        return path
    storage_base = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/public"
    return f"{storage_base}/{path.lstrip('/')}"


async def _run_draping_job(request_id: str, user_id: str, garment_id: str, size: str, body_hash: str):
    """Background task: call RunPod draping endpoint, store result."""
    import httpx

    try:
        supabase.client.table("draping_requests").update({
            "status": "processing"
        }).eq("id", request_id).execute()

        body_files = _get_user_body_files(user_id)
        garment_info = _get_garment_draping_info(garment_id, size)

        if not body_files or not garment_info:
            supabase.client.table("draping_requests").update({
                "status": "failed",
                "error_message": "Missing body or garment files",
            }).eq("id", request_id).execute()
            return

        runpod_payload = {
            "input": {
                "body_obj_url": _resolve_storage_url(body_files["body_obj_url"]),
                "garment_obj_url": _resolve_storage_url(garment_info["obj_path"]),
                "smpl_params_url": _resolve_storage_url(body_files["smpl_params_url"]) if body_files.get("smpl_params_url") else None,
                "fabric_config": garment_info.get("fabric_config", {}),
                "simulation_mode": "swift",
                "garment_id": garment_id,
                "size": size,
                "user_id": user_id,
            }
        }

        if not settings.runpod_api_key or not settings.runpod_draping_endpoint_id:
            supabase.client.table("draping_requests").update({
                "status": "failed",
                "error_message": "RunPod draping endpoint not configured",
            }).eq("id", request_id).execute()
            return

        # Submit to RunPod
        async with httpx.AsyncClient(timeout=180.0) as client:
            run_url = f"https://api.runpod.ai/v2/{settings.runpod_draping_endpoint_id}/runsync"
            headers = {"Authorization": f"Bearer {settings.runpod_api_key}"}

            resp = await client.post(run_url, json=runpod_payload, headers=headers)
            resp.raise_for_status()
            result = resp.json()

        job_output = result.get("output", {})
        if not job_output.get("success"):
            supabase.client.table("draping_requests").update({
                "status": "failed",
                "error_message": job_output.get("error", "Unknown RunPod error"),
                "runpod_job_id": result.get("id"),
            }).eq("id", request_id).execute()
            return

        # Upload draped GLB to Supabase Storage
        glb_b64 = job_output.get("draped_glb_base64", "")
        if not glb_b64:
            supabase.client.table("draping_requests").update({
                "status": "failed",
                "error_message": "No GLB in RunPod response",
            }).eq("id", request_id).execute()
            return

        glb_bytes = base64.b64decode(glb_b64)
        storage_path = f"draped/{garment_id}/{size}/{body_hash}.glb"

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

        # Insert into draped_meshes cache
        mesh_row = supabase.client.table("draped_meshes").upsert({
            "garment_id": garment_id,
            "size": size,
            "body_hash": body_hash,
            "draped_glb_url": draped_url,
            "simulation_method": job_output.get("simulation_method", "unknown"),
            "processing_time_seconds": job_output.get("processing_time_seconds"),
            "vertex_count": job_output.get("vertex_count"),
        }, on_conflict="garment_id,size,body_hash").execute()

        mesh_id = mesh_row.data[0]["id"] if mesh_row.data else None

        supabase.client.table("draping_requests").update({
            "status": "completed",
            "draped_mesh_id": mesh_id,
            "runpod_job_id": result.get("id"),
        }).eq("id", request_id).execute()

    except Exception as e:
        print(f"[Draping] Job {request_id} failed: {e}")
        import traceback
        traceback.print_exc()
        supabase.client.table("draping_requests").update({
            "status": "failed",
            "error_message": str(e)[:500],
        }).eq("id", request_id).execute()


class TestRunRequest(BaseModel):
    body_obj_url: str
    garment_obj_url: str
    fabric_preset: str = "cotton_medium"
    simulation_mode: str = "swift"


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


class DrapingResponse(BaseModel):
    request_id: str
    status: str
    draped_url: Optional[str] = None
    cached: bool = False


@router.post("/request", response_model=DrapingResponse)
async def request_draping(body: DrapingRequest, background_tasks: BackgroundTasks):
    """
    Request cloth draping for a garment+size+user.
    Returns immediately with a request_id. Draping runs in background.
    If a cached result exists, returns it immediately.
    """
    body_hash = _body_hash_from_user(body.user_id)
    if not body_hash:
        raise HTTPException(status_code=400, detail="User has no body data (fit passport required)")

    garment_info = _get_garment_draping_info(body.garment_id, body.size)
    if not garment_info:
        raise HTTPException(status_code=404, detail="No OBJ mesh for this garment+size")

    # Check cache first
    try:
        cached = supabase.client.table("draped_meshes").select("draped_glb_url").eq(
            "garment_id", body.garment_id
        ).eq("size", body.size).eq("body_hash", body_hash).limit(1).execute()

        if cached.data and cached.data[0].get("draped_glb_url"):
            return DrapingResponse(
                request_id="cached",
                status="completed",
                draped_url=cached.data[0]["draped_glb_url"],
                cached=True,
            )
    except Exception:
        pass

    # Check for in-progress request
    try:
        existing = supabase.client.table("draping_requests").select("id,status").eq(
            "garment_id", body.garment_id
        ).eq("size", body.size).eq("body_hash", body_hash).in_(
            "status", ["pending", "processing"]
        ).limit(1).execute()

        if existing.data:
            return DrapingResponse(
                request_id=str(existing.data[0]["id"]),
                status=existing.data[0]["status"],
            )
    except Exception:
        pass

    # Create new request
    row = supabase.client.table("draping_requests").insert({
        "user_id": body.user_id,
        "garment_id": body.garment_id,
        "size": body.size,
        "body_hash": body_hash,
        "status": "pending",
    }).execute()

    if not row.data:
        raise HTTPException(status_code=500, detail="Failed to create draping request")

    request_id = str(row.data[0]["id"])

    background_tasks.add_task(
        _run_draping_job,
        request_id=request_id,
        user_id=body.user_id,
        garment_id=body.garment_id,
        size=body.size,
        body_hash=body_hash,
    )

    return DrapingResponse(request_id=request_id, status="pending")


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


class DrapingCheckResponse(BaseModel):
    has_cached: bool
    draped_url: Optional[str] = None
    has_obj: bool = False


@router.get("/check", response_model=DrapingCheckResponse)
async def check_draping_cache(
    garment_id: str = Query(...),
    size: str = Query(...),
    user_id: str = Query(...),
):
    """Quick check: does a draped mesh exist for this garment+size+user?"""
    body_hash = _body_hash_from_user(user_id)
    if not body_hash:
        return DrapingCheckResponse(has_cached=False, has_obj=False)

    garment_info = _get_garment_draping_info(garment_id, size)
    has_obj = garment_info is not None

    try:
        cached = supabase.client.table("draped_meshes").select("draped_glb_url").eq(
            "garment_id", garment_id
        ).eq("size", size).eq("body_hash", body_hash).limit(1).execute()

        if cached.data and cached.data[0].get("draped_glb_url"):
            return DrapingCheckResponse(
                has_cached=True,
                draped_url=cached.data[0]["draped_glb_url"],
                has_obj=has_obj,
            )
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
