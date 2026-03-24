"""
Avatar creation and retrieval endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any
from datetime import datetime
import uuid

from app.models.avatar import (
    AvatarCreateRequest,
    AvatarCreateResponse,
    AvatarStatusResponse,
    AvatarResponse,
    Measurements,
    ProcessingStatus,
)
from app.services.supabase import supabase_service
from app.services.runpod import runpod_service
from app.config import get_settings

settings = get_settings()

router = APIRouter()

# In-memory job storage (use Redis in production)
jobs: Dict[str, Dict[str, Any]] = {}


@router.post("/create", response_model=AvatarCreateResponse)
async def create_avatar(
    request: AvatarCreateRequest,
    background_tasks: BackgroundTasks
):
    """
    Start avatar creation process
    
    1. Validates the request
    2. Updates fit_passport status to 'processing'
    3. Queues the job to RunPod (or mock)
    4. Returns job_id for status polling
    """
    
    # Generate job ID
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    
    # Update fit_passport status
    await supabase_service.update_fit_passport_status(
        user_id=request.user_id,
        status="processing",
        progress_message="Starting avatar creation..."
    )
    
    # Store job info
    jobs[job_id] = {
        "user_id": request.user_id,
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
        request=request
    )
    
    return AvatarCreateResponse(
        job_id=job_id,
        user_id=request.user_id,
        status=ProcessingStatus.queued,
        message="Avatar creation started",
        estimated_time_seconds=120
    )


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
        print(f"[Avatar]   Gender: {request.gender.value}")
        print(f"[Avatar]   Photo URL: {request.photo_url[:100]}...")
        
        jobs[job_id]["status"] = ProcessingStatus.processing
        jobs[job_id]["progress"] = 10
        jobs[job_id]["message"] = "Preparing photo for GPU..."
        
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
        
        jobs[job_id]["message"] = "Submitting job to RunPod..."
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
            gender=request.gender.value,
            user_id=request.user_id
        )
        
        print(f"[Avatar] RunPod submission response: {runpod_job_id}")
        
        if not runpod_job_id:
            error_msg = "Failed to submit job to RunPod - check RunPod API key and endpoint ID configuration"
            print(f"[Avatar] ❌ {error_msg}")
            raise Exception(error_msg)
        
        print(f"[Avatar] ✅ Job submitted to RunPod: {runpod_job_id}")
        
        jobs[job_id]["runpod_job_id"] = runpod_job_id
        jobs[job_id]["progress"] = 20
        jobs[job_id]["message"] = "Processing on GPU..."
        
        import asyncio
        max_attempts = 60  # 5 minutes with 5 second intervals
        
        for attempt in range(max_attempts):
            await asyncio.sleep(5)
            
            print(f"[Avatar] Poll #{attempt+1}/{max_attempts} for RunPod job {runpod_job_id}")
            status_result = await runpod_service.get_job_status(runpod_job_id)
            runpod_status = status_result.get("status", "")
            
            if runpod_status == "IN_QUEUE":
                if attempt < 12:
                    jobs[job_id]["progress"] = min(10 + attempt * 2, 30)
                    jobs[job_id]["message"] = "Preparing your avatar..."
                else:
                    jobs[job_id]["progress"] = 30
                    jobs[job_id]["message"] = "Our servers are busy right now. Hang tight..."
            elif runpod_status == "IN_PROGRESS":
                jobs[job_id]["progress"] = min(50 + attempt, 90)
                jobs[job_id]["message"] = "Creating your avatar and extracting measurements..."
            elif runpod_status == "COMPLETED":
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
                jobs[job_id]["progress"] = 95
                jobs[job_id]["message"] = "Saving your avatar files..."
                
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
                jobs[job_id]["message"] = "Avatar created successfully!"
                jobs[job_id]["avatar_url"] = avatar_url
                jobs[job_id]["measurements"] = measurements
                jobs[job_id]["completed_at"] = datetime.utcnow()
                
                print(f"[Avatar] ✓ Job {job_id} marked as completed")
                print(f"[Avatar]   Avatar URL: {avatar_url[:80]}...")
                print(f"[Avatar]   Measurements: {len(measurements)} values")
                
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
    """Diagnostic: test if Supabase storage upload works."""
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
async def get_avatar(user_id: str):
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
