"""
Avatar creation and retrieval endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form, Depends, Request
from typing import Dict, Any
from datetime import datetime
import uuid

from slowapi import Limiter
from app.api.rate_limit import client_key

from app.models.avatar import (
    AvatarCreateRequest,
    AvatarCreateResponse,
    AvatarStatusResponse,
    AvatarResponse,
    Measurements,
    ProcessingStatus,
    pipeline_gender,
)
from app.api.deps import UserAccess, get_current_user_id
from app.services.supabase import supabase_service
from app.services.runpod import runpod_service
from app.config import get_settings

settings = get_settings()

router = APIRouter()
limiter = Limiter(key_func=client_key)


@router.post("/upload-photo")
@limiter.limit("10/minute")
async def upload_photo(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
):
    """
    Upload a user photo to Supabase Storage using the service role key
    (bypasses RLS). Returns the storage path and public URL.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")

    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg"
    filename = f"photo_{uuid.uuid4().hex[:8]}.{ext}"
    storage_path = f"{user_id}/{filename}"

    bucket = supabase_service.client.storage.from_(settings.photos_bucket)
    try:
        bucket.upload(
            storage_path,
            contents,
            {"content-type": file.content_type or "image/jpeg", "x-upsert": "true"},
        )
    except Exception as e:
        print(f"[Avatar] Photo upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {e}")

    public_url = bucket.get_public_url(storage_path)
    return {"path": storage_path, "url": public_url}

# In-memory job storage (use Redis in production)
jobs: Dict[str, Dict[str, Any]] = {}


@router.post("/create", response_model=AvatarCreateResponse)
@limiter.limit("5/minute")
async def create_avatar(
    request: Request,
    body: AvatarCreateRequest,
    background_tasks: BackgroundTasks,
    auth_user_id: str = Depends(get_current_user_id),
):
    """
    Start avatar creation process
    
    1. Validates the request (user_id from JWT must match body)
    2. Updates fit_passport status to 'processing'
    3. Queues the job to RunPod (or mock)
    4. Returns job_id for status polling
    """
    if body.user_id != auth_user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Generate job ID
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    
    # The passport is created here if the client has not made one (the widget onboards
    # without ever visiting tryon.global), and always holds what this avatar is built from.
    try:
        saved = await supabase_service.ensure_fit_passport(
            user_id=body.user_id,
            height=body.height,
            weight=body.weight,
            gender=body.gender.value,
        )
    except Exception as e:
        print(f"[Avatar] Could not write fit passport for {body.user_id}: {e}")
        saved = False
    if not saved:
        # fit_passports.user_id references users.id: no profile row, no passport.
        raise HTTPException(
            status_code=409,
            detail="Your account is not fully set up yet. Finish signing up, then try again.",
        )
    
    # Store job info
    jobs[job_id] = {
        "user_id": body.user_id,
        "status": ProcessingStatus.queued,
        "progress": 0,
        "message": "Preparing your avatar...",
        "started_at": datetime.utcnow(),
        "runpod_job_id": None,
        "avatar_url": None,
        "measurements": None,
        "error": None,
    }
    
    # Start background processing
    background_tasks.add_task(
        process_avatar_job,
        job_id=job_id,
        request=body
    )
    
    return AvatarCreateResponse(
        job_id=job_id,
        user_id=body.user_id,
        status=ProcessingStatus.queued,
        message="Avatar creation started",
        estimated_time_seconds=120
    )


def drape_scope_for_shop(shop_domain: str | None) -> list[str] | None:
    """Which brands a new avatar is pre-draped for.

    A shopper who onboards from a store's widget needs that store's garments now, not
    every garment on the platform: return that store's brand. No shop (onboarding on
    tryon.global), or a shop we cannot match to a brand, returns None = every store, which
    is what happened before and is the safe side: nobody ends up with no drapes.
    """
    shop = (shop_domain or "").strip()
    if not shop:
        return None
    try:
        brand_id = supabase_service._resolve_brand_id(shop)
    except Exception as e:
        print(f"[Avatar] Brand lookup failed for shop {shop!r}: {e}")
        return None
    if not brand_id:
        print(f"[Avatar] No brand for shop {shop!r}; pre-draping for every store")
        return None
    return [brand_id]


POLL_SECONDS = 2
MAX_BUILD_SECONDS = 600


def advance(job: dict, floor: int, cap: int, message: str) -> None:
    """Move the progress bar forward one step. It never goes backwards."""
    job["progress"] = max(job["progress"], min(max(job["progress"] + 1, floor), cap))
    job["message"] = message


async def process_avatar_job(job_id: str, request: AvatarCreateRequest):
    """
    Background task to process avatar creation
    
    This is where the magic happens:
    1. Submit to RunPod GPU
    2. Poll for completion
    3. Upload GLB to Supabase storage
    4. Update database with results
    """
    try:
        print(f"[Avatar] 🚀 Starting avatar job: {job_id}")
        print(f"[Avatar]   User ID: {request.user_id}")
        print(f"[Avatar]   Height: {request.height} cm")
        print(f"[Avatar]   Gender: {request.gender.value} (pipeline: {pipeline_gender(request.gender)})")
        print(f"[Avatar]   Photo URL: {request.photo_url[:100]}...")
        
        jobs[job_id]["status"] = ProcessingStatus.processing
        advance(jobs[job_id], 5, 5, "Starting...")
        
        # photos bucket is PRIVATE — public URLs return 400.
        # We MUST create a signed URL for RunPod to download the photo.
        photo_url = request.photo_url
        print(f"[Avatar] Original photo URL: {photo_url[:120]}...")
        
        # Extract storage path from any Supabase photos URL
        photo_path = None
        for marker in ["/storage/v1/object/public/photos/", "/storage/v1/object/sign/photos/"]:
            if marker in photo_url:
                path_start = photo_url.find(marker) + len(marker)
                photo_path = photo_url[path_start:]
                if "?" in photo_path:
                    photo_path = photo_path.split("?")[0]
                break
        
        if photo_path:
            try:
                signed_url = supabase_service.get_photo_signed_url(photo_path, expires_in=3600)
                if signed_url:
                    photo_url = signed_url
                    print(f"[Avatar] ✓ Signed URL created (path: {photo_path})")
                else:
                    print(f"[Avatar] ❌ Signed URL empty! photo_path={photo_path}")
            except Exception as e:
                print(f"[Avatar] ❌ Signed URL error: {e}")
        else:
            print(f"[Avatar] ⚠️  URL does not match Supabase photos pattern, using as-is")
        
        print(f"[Avatar] Final photo URL for RunPod: {photo_url[:120]}...")
        
        print(f"[Avatar] 📤 Submitting job to RunPod...")
        
        # Check if using mock service
        from app.services.runpod import MockRunPodService
        service_class_name = type(runpod_service).__name__
        print(f"[Avatar] RunPod service type: {service_class_name}")
        
        if service_class_name == "MockRunPodService":
            print(f"[Avatar] ⚠️  WARNING: Using MOCK RunPod service - jobs will NOT be submitted to RunPod!")
            print(f"[Avatar] ⚠️  Set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID environment variables in .env file")
            print(f"[Avatar] ⚠️  Current values: API_KEY={'SET' if hasattr(settings, 'runpod_api_key') and settings.runpod_api_key else 'NOT SET'}")
            print(f"[Avatar] ⚠️  Current values: ENDPOINT_ID={'SET' if hasattr(settings, 'runpod_endpoint_id') and settings.runpod_endpoint_id else 'NOT SET'}")
        else:
            print(f"[Avatar] ✓ Using real RunPod service")
        
        # Submit to RunPod
        runpod_job_id = await runpod_service.submit_avatar_job(
            photo_url=photo_url,  # Use signed URL
            height=request.height,
            weight=request.weight,
            gender=pipeline_gender(request.gender),
            user_id=request.user_id
        )
        
        print(f"[Avatar] RunPod submission response: {runpod_job_id}")
        
        if not runpod_job_id:
            error_msg = "Failed to submit job to RunPod - check RunPod API key and endpoint ID configuration"
            print(f"[Avatar] ❌ {error_msg}")
            raise Exception(error_msg)
        
        print(f"[Avatar] ✅ Job submitted to RunPod: {runpod_job_id}")
        
        jobs[job_id]["runpod_job_id"] = runpod_job_id
        advance(jobs[job_id], 10, 10, "Starting...")
        
        import asyncio
        import time
        submitted = time.monotonic()
        max_attempts = MAX_BUILD_SECONDS // POLL_SECONDS
        
        for attempt in range(max_attempts):
            await asyncio.sleep(POLL_SECONDS)
            
            print(f"[Avatar] Poll #{attempt+1}/{max_attempts} for RunPod job {runpod_job_id}")
            status_result = await runpod_service.get_job_status(runpod_job_id)
            runpod_status = status_result.get("status", "")
            
            if runpod_status == "IN_QUEUE":
                busy = time.monotonic() - submitted > 60
                advance(jobs[job_id], 10, 30, "Our servers are busy right now. Hang tight..." if busy else "Starting...")
            elif runpod_status == "IN_PROGRESS":
                advance(jobs[job_id], 30, 90, "Getting your measurements...")
            elif runpod_status == "COMPLETED":
                gpu_done = time.monotonic()
                output = status_result.get("output", {})
                # RunPod marks job COMPLETED even when handler returns {"error": "..."}
                if output.get("error"):
                    error_msg = output.get("error", "Unknown pipeline error")
                    print(f"[Avatar] ❌ RunPod job returned error: {error_msg}")
                    raise Exception(f"Avatar pipeline failed: {error_msg}")
                measurements = output.get("measurements", {})
                
                print(f"[Avatar] ✓ RunPod job completed successfully")
                print(f"[Avatar]   Measurements received: {len(measurements)} values")
                print(f"[Avatar]   Files in output: {list(output.get('files_bytes', {}).keys())}")
                
                # Ensure measurements is a dict and has required fields
                if not isinstance(measurements, dict):
                    print(f"[Avatar] ⚠ WARNING: Measurements is not a dict: {type(measurements)}")
                    measurements = {}
                
                # CRITICAL: Convert all float measurements to integers (database expects INTEGER)
                # Pipeline returns floats like 57.6, 58.7 but Supabase columns are INTEGER
                measurements_int = {}
                for key, value in measurements.items():
                    if value is not None:
                        try:
                            measurements_int[key] = int(round(float(value)))
                        except (ValueError, TypeError):
                            print(f"[Avatar] ⚠ WARNING: Could not convert '{key}': {value}")
                
                # Ensure height is always present (as integer)
                if "height" not in measurements_int:
                    measurements_int["height"] = int(round(float(request.height)))
                else:
                    measurements_int["height"] = int(round(float(measurements_int["height"])))
                
                measurements = measurements_int
                print(f"[Avatar] Converted {len(measurements)} measurements to integers")
                
                # Upload all pipeline files to Supabase storage
                advance(jobs[job_id], 95, 95, "Almost done...")
                
                files_bytes = output.get("files_bytes", {})
                
                # Upload all files
                file_urls = {}
                upload_errors = []
                
                if files_bytes:
                    print(f"[Avatar] Uploading {len(files_bytes)} files to Supabase...")
                    try:
                        file_urls = await supabase_service.upload_pipeline_files(
                            user_id=request.user_id,
                            files_bytes=files_bytes
                        )
                        
                        # Verify uploads
                        print(f"[Avatar] Upload verification:")
                        print(f"  Files to upload: {len(files_bytes)}")
                        print(f"  Files uploaded: {len(file_urls)}")
                        
                        for file_key in files_bytes.keys():
                            if file_key in file_urls:
                                print(f"    ✓ {file_key}: {file_urls[file_key][:80]}...")
                            else:
                                print(f"    ✗ {file_key}: Upload failed")
                                upload_errors.append(file_key)
                    except Exception as upload_error:
                        print(f"[Avatar] ✗ Upload error: {upload_error}")
                        import traceback
                        traceback.print_exc()
                        # Continue anyway - try to save what we can
                else:
                    print(f"[Avatar] ⚠ WARNING: No files_bytes in output")
                    print(f"[Avatar]   Output keys: {list(output.keys())}")
                    # Fallback: try old format (single GLB)
                    glb_bytes = output.get("avatar_glb_bytes")
                    if glb_bytes:
                        try:
                            avatar_url = await supabase_service.upload_avatar(
                                user_id=request.user_id,
                                file_data=glb_bytes,
                                filename="avatar_textured.glb"
                            )
                            file_urls["avatar_glb"] = avatar_url
                            print(f"[Avatar] Uploaded single GLB: {avatar_url[:80]}...")
                        except Exception as e:
                            print(f"[Avatar] ✗ Failed to upload GLB: {e}")
                
                # Get main avatar URL (prioritize GLB)
                # CRITICAL: Only use URLs from file_urls (Supabase URLs), NEVER use fallback paths
                avatar_url = file_urls.get("avatar_glb") or file_urls.get("apose_mesh")
                
                # Validate that we have a valid Supabase URL (must start with http/https)
                if not avatar_url:
                    error_msg = f"[Avatar] ❌ CRITICAL ERROR: No avatar URL found in file_urls. Upload may have failed."
                    print(error_msg)
                    print(f"[Avatar]   file_urls keys: {list(file_urls.keys())}")
                    print(f"[Avatar]   files_bytes keys: {list(files_bytes.keys()) if files_bytes else 'None'}")
                    raise Exception("Avatar upload failed - no avatar URL available. Check upload logs above.")
                
                # Ensure it's a valid URL (not a local path)
                if not avatar_url.startswith(('http://', 'https://')):
                    error_msg = f"[Avatar] ❌ CRITICAL ERROR: Invalid avatar URL format: {avatar_url}"
                    print(error_msg)
                    print(f"[Avatar]   URL must be a Supabase storage URL (starts with http/https)")
                    raise Exception(f"Invalid avatar URL format. Got: {avatar_url}")
                
                print(f"[Avatar] ✓ Valid avatar URL found: {avatar_url[:80]}...")
                
                # Update database with all file URLs stored in JSONB
                print(f"[Avatar] Updating database with results...")
                try:
                    db_update_success = await supabase_service.update_fit_passport_with_results(
                        user_id=request.user_id,
                        avatar_url=avatar_url,  # This is now guaranteed to be a valid Supabase URL
                        measurements=measurements,
                        pipeline_files=file_urls  # Store all URLs in JSONB field
                    )
                    
                    # Verify database update and user linkage
                    if db_update_success:
                        print(f"[Avatar] ✓ Database updated successfully")
                        # Verify by reading back
                        fit_passport = await supabase_service.get_fit_passport(request.user_id)
                        if fit_passport:
                            print(f"[Avatar] ✓ Verification: Avatar URL in DB: {fit_passport.get('avatar_url', 'NOT SET')[:80]}...")
                            print(f"[Avatar] ✓ Verification: Status: {fit_passport.get('status')}")
                            print(f"[Avatar] ✓ Verification: Measurements count: {len([k for k in ['chest', 'waist', 'hips', 'inseam'] if fit_passport.get(k)])}")
                            
                            # Verify user linkage: Check that avatar_url contains user_id
                            db_avatar_url = fit_passport.get('avatar_url', '')
                            if request.user_id in db_avatar_url:
                                print(f"[Avatar] ✓ USER LINKAGE VERIFIED: Avatar URL contains user_id '{request.user_id}'")
                                print(f"[Avatar]   Storage path structure: avatars/{request.user_id}/avatar_textured.glb")
                            else:
                                print(f"[Avatar] ⚠ WARNING: Avatar URL does not contain user_id")
                                print(f"[Avatar]   User ID: {request.user_id}")
                                print(f"[Avatar]   Avatar URL: {db_avatar_url[:100]}...")
                            
                            # Verify pipeline_files linkage
                            pipeline_files = fit_passport.get('pipeline_files', {})
                            if pipeline_files:
                                print(f"[Avatar] ✓ Pipeline files stored: {len(pipeline_files)} files")
                                # Check that all file URLs contain user_id
                                files_with_user_id = sum(1 for url in pipeline_files.values() if request.user_id in str(url))
                                print(f"[Avatar]   Files linked to user: {files_with_user_id}/{len(pipeline_files)}")
                                if files_with_user_id == len(pipeline_files):
                                    print(f"[Avatar] ✓ All pipeline files correctly linked to user_id")
                                else:
                                    print(f"[Avatar] ⚠ Some files may not be linked correctly")
                        else:
                            print(f"[Avatar] ✗ Verification failed: Could not read back fit_passport")
                    else:
                        print(f"[Avatar] ✗ Database update failed")
                        raise Exception("Failed to update database")
                except Exception as db_error:
                    print(f"[Avatar] ✗ Database update error: {db_error}")
                    import traceback
                    traceback.print_exc()
                    raise
                
                jobs[job_id]["status"] = ProcessingStatus.completed
                jobs[job_id]["progress"] = 100
                jobs[job_id]["message"] = "Done"
                # Where the time went, in seconds: waiting for a GPU worker, the worker running
                # (model loading included), the pipeline itself, and saving the files here.
                rp = status_result.get("timing") or {}
                secs = lambda ms: round(ms / 1000, 1) if isinstance(ms, (int, float)) else None
                jobs[job_id]["timing"] = {
                    "queue": secs(rp.get("queue_ms")),
                    "gpu": secs(rp.get("gpu_ms")),
                    "pipeline": output.get("processing_time"),
                    "save": round(time.monotonic() - gpu_done, 1),
                    "total": round(time.monotonic() - submitted, 1),
                }
                print(f"[Avatar] TIMING {job_id}: {jobs[job_id]['timing']}")
                try:
                    await supabase_service.track_event(
                        "avatar_build_timing",
                        user_id=request.user_id,
                        shop_domain=request.shop_domain,
                        event_data=jobs[job_id]["timing"],
                    )
                except Exception as timing_err:
                    print(f"[Avatar] Could not record build timing (non-fatal): {timing_err}")
                jobs[job_id]["avatar_url"] = avatar_url
                jobs[job_id]["measurements"] = measurements
                jobs[job_id]["completed_at"] = datetime.utcnow()

                print(f"[Avatar] ✓ Job {job_id} marked as completed")
                print(f"[Avatar]   Avatar URL: {avatar_url[:80]}...")
                print(f"[Avatar]   Measurements: {len(measurements)} values")

                # Pre-drape fan-out: enqueue this avatar against every active
                # garment x size. Runs synchronously here (just a batch of
                # Postgres inserts), the actual sims are picked up by the
                # dispatcher loop. Failures here must NOT fail the avatar job.
                try:
                    from app.services.drape_queue import enqueue_full_drape
                    brand_ids = drape_scope_for_shop(request.shop_domain)
                    drape_counts = enqueue_full_drape(request.user_id, priority=10, brand_ids=brand_ids)
                    scope = f"shop {request.shop_domain}" if brand_ids is not None else "all stores"
                    print(f"[Avatar] Pre-drape enqueue ({scope}): {drape_counts}")
                except Exception as drape_err:
                    print(f"[Avatar] Pre-drape enqueue failed (non-fatal): {drape_err}")

                return
                
            elif runpod_status in ["FAILED", "CANCELLED"]:
                raise Exception(status_result.get("error", "GPU processing failed"))
        
        # Timeout
        raise Exception("Avatar creation timed out")
        
    except Exception as e:
        import traceback
        print(f"[Avatar] ❌ PROCESS FAILED: {e}")
        traceback.print_exc()
        jobs[job_id]["status"] = ProcessingStatus.failed
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["message"] = "Avatar creation failed"
        
        try:
            await supabase_service.update_fit_passport_status(
                user_id=request.user_id,
                status="failed"
            )
        except Exception:
            pass


@router.get("/status/{job_id}", response_model=AvatarStatusResponse)
async def get_avatar_status(job_id: str):
    """
    Get status of avatar creation job
    
    Poll this endpoint to track progress
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    return AvatarStatusResponse(
        job_id=job_id,
        user_id=job["user_id"],
        status=job["status"],
        progress=job["progress"],
        message=job["message"],
        avatar_url=job.get("avatar_url"),
        measurements=job.get("measurements"),
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
        error=job.get("error"),
    )


@router.get("/debug/test-upload")
async def debug_test_upload():
    """Diagnostic: test if Supabase storage upload works. Only available in debug mode."""
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Not found")
    results = {}
    try:
        from app.config import get_settings
        s = get_settings()
        results["avatars_bucket"] = s.avatars_bucket
        results["supabase_url"] = s.supabase_url
        
        bucket = supabase_service.client.storage.from_(s.avatars_bucket)
        test_data = b'{"test": true}'
        test_path = "_debug/upload_test.json"
        
        # Try upload
        try:
            bucket.upload(test_path, test_data, {"content-type": "application/json", "x-upsert": "true"})
            results["upload_upsert"] = "OK"
        except Exception as e1:
            results["upload_upsert"] = str(e1)
            try:
                bucket.remove([test_path])
                bucket.upload(test_path, test_data, {"content-type": "application/json"})
                results["upload_remove_retry"] = "OK"
            except Exception as e2:
                results["upload_remove_retry"] = str(e2)
                try:
                    bucket.update(test_path, test_data, {"content-type": "application/json"})
                    results["upload_update"] = "OK"
                except Exception as e3:
                    results["upload_update"] = str(e3)
        
        url = bucket.get_public_url(test_path)
        results["public_url"] = url
        results["status"] = "success" if any(v == "OK" for v in results.values()) else "all_failed"
        
        # List buckets
        try:
            buckets = supabase_service.client.storage.list_buckets()
            results["buckets"] = [b.name for b in buckets]
        except Exception as eb:
            results["buckets_error"] = str(eb)
        
    except Exception as e:
        import traceback
        results["error"] = str(e)
        results["traceback"] = traceback.format_exc()
    
    return results


@router.get("/{user_id}", response_model=AvatarResponse)
async def get_avatar(user_id: str, _access: None = Depends(UserAccess("avatar"))):
    """
    Get user's avatar and measurements.
    ALWAYS returns avatar_textured.glb URL — canonical path from Supabase storage.
    Never returns OBJ; widget must load GLB for correct scale (mm) + texture.
    """
    try:
        fit_passport = await supabase_service.get_fit_passport(user_id)
    except Exception:
        fit_passport = None
    
    if not fit_passport:
        raise HTTPException(status_code=404, detail="Avatar not found")
    
    # Canonical GLB URL — avatars/{user_id}/avatar_textured.glb in storage
    # Bypasses DB confusion; RunPod pipeline always outputs this file
    from app.config import get_settings
    _s = get_settings()
    base = _s.supabase_url.rstrip("/")
    bucket = getattr(_s, "avatars_bucket", "avatars")
    avatar_url = f"{base}/storage/v1/object/public/{bucket}/{user_id}/avatar_textured.glb"
    
    return AvatarResponse(
        user_id=user_id,
        avatar_url=avatar_url,
        avatar_thumbnail_url=fit_passport.get("avatar_thumbnail_url"),
        measurements=Measurements(
            height=fit_passport.get("height", 0),
            chest=fit_passport.get("chest"),
            waist=fit_passport.get("waist"),
            hips=fit_passport.get("hips"),
            inseam=fit_passport.get("inseam"),
            shoulder_width=fit_passport.get("shoulder_width"),
            arm_length=fit_passport.get("arm_length"),
            neck=fit_passport.get("neck"),
            thigh=fit_passport.get("thigh"),
            torso_length=fit_passport.get("torso_length"),
        ),
        gender=fit_passport.get("gender", "other"),
        status=fit_passport.get("status", "pending"),
        created_at=fit_passport.get("created_at"),
        updated_at=fit_passport.get("updated_at"),
    )
