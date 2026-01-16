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
        "message": "Job queued",
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
        jobs[job_id]["status"] = ProcessingStatus.processing
        jobs[job_id]["progress"] = 10
        jobs[job_id]["message"] = "Preparing photo for GPU..."
        
        # Convert photo URL to signed URL (required for private buckets)
        # Extract path from public URL: https://xxx.supabase.co/storage/v1/object/public/photos/user_id/file.jpg
        # -> user_id/file.jpg (path within bucket, not including bucket name)
        photo_url = request.photo_url
        if "/storage/v1/object/public/photos/" in photo_url:
            # Extract the path after /photos/ (this is the path within the bucket)
            path_start = photo_url.find("/photos/") + len("/photos/")
            photo_path = photo_url[path_start:]
            
            # Remove query parameters if any
            if "?" in photo_path:
                photo_path = photo_path.split("?")[0]
            
            # Create signed URL (valid for 1 hour)
            try:
                signed_url = supabase_service.get_photo_signed_url(photo_path, expires_in=3600)
                if signed_url:
                    photo_url = signed_url
                    print(f"[Avatar] Using signed URL for photo (path: {photo_path})")
                else:
                    print(f"[Avatar] Warning: Failed to create signed URL, using original: {photo_url}")
            except Exception as e:
                print(f"[Avatar] Error creating signed URL: {e}, using original URL")
                # Continue with original URL - might work if bucket is public
        
        jobs[job_id]["message"] = "Uploading to GPU..."
        
        # Submit to RunPod
        runpod_job_id = await runpod_service.submit_avatar_job(
            photo_url=photo_url,  # Use signed URL
            height=request.height,
            weight=request.weight,
            gender=request.gender.value,
            user_id=request.user_id
        )
        
        if not runpod_job_id:
            raise Exception("Failed to submit job to GPU")
        
        jobs[job_id]["runpod_job_id"] = runpod_job_id
        jobs[job_id]["progress"] = 20
        jobs[job_id]["message"] = "Processing on GPU..."
        
        # Poll for completion (in real scenario, use webhooks or celery)
        import asyncio
        max_attempts = 60  # 5 minutes with 5 second intervals
        
        for attempt in range(max_attempts):
            await asyncio.sleep(5)
            
            status_result = await runpod_service.get_job_status(runpod_job_id)
            runpod_status = status_result.get("status", "")
            
            # Update progress based on RunPod status
            if runpod_status == "IN_QUEUE":
                jobs[job_id]["progress"] = 25
                jobs[job_id]["message"] = "Waiting in GPU queue..."
            elif runpod_status == "IN_PROGRESS":
                jobs[job_id]["progress"] = min(50 + attempt, 90)
                jobs[job_id]["message"] = "Creating your 3D avatar..."
            elif runpod_status == "COMPLETED":
                # Success!
                output = status_result.get("output", {})
                measurements = output.get("measurements", {})
                
                # Upload all pipeline files to Supabase storage
                jobs[job_id]["progress"] = 95
                jobs[job_id]["message"] = "Saving your avatar files..."
                
                files_bytes = output.get("files_bytes", {})
                
                # Upload all files
                file_urls = {}
                if files_bytes:
                    file_urls = await supabase_service.upload_pipeline_files(
                        user_id=request.user_id,
                        files_bytes=files_bytes
                    )
                else:
                    # Fallback: try old format (single GLB)
                    glb_bytes = output.get("avatar_glb_bytes")
                    if glb_bytes:
                        avatar_url = await supabase_service.upload_avatar(
                            user_id=request.user_id,
                            file_data=glb_bytes,
                            filename="avatar_textured.glb"
                        )
                        file_urls["avatar_glb"] = avatar_url
                
                # Get main avatar URL (prioritize GLB)
                avatar_url = file_urls.get("avatar_glb") or file_urls.get("apose_mesh") or "/models/avatar_with_tshirt_m.glb"
                
                # Update database with all file URLs stored in JSONB
                # First update basic fields
                await supabase_service.update_fit_passport_with_results(
                    user_id=request.user_id,
                    avatar_url=avatar_url,
                    measurements=measurements,
                    pipeline_files=file_urls  # Store all URLs in JSONB field
                )
                
                jobs[job_id]["status"] = ProcessingStatus.completed
                jobs[job_id]["progress"] = 100
                jobs[job_id]["message"] = "Avatar created successfully!"
                jobs[job_id]["avatar_url"] = avatar_url
                jobs[job_id]["measurements"] = measurements
                jobs[job_id]["completed_at"] = datetime.utcnow()
                
                return
                
            elif runpod_status in ["FAILED", "CANCELLED"]:
                raise Exception(status_result.get("error", "GPU processing failed"))
        
        # Timeout
        raise Exception("Avatar creation timed out")
        
    except Exception as e:
        print(f"Avatar processing error: {e}")
        jobs[job_id]["status"] = ProcessingStatus.failed
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["message"] = "Avatar creation failed"
        
        await supabase_service.update_fit_passport_status(
            user_id=request.user_id,
            status="failed"
        )


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


@router.get("/{user_id}", response_model=AvatarResponse)
async def get_avatar(user_id: str):
    """
    Get user's avatar and measurements
    """
    fit_passport = await supabase_service.get_fit_passport(user_id)
    
    if not fit_passport:
        raise HTTPException(status_code=404, detail="Avatar not found")
    
    return AvatarResponse(
        user_id=user_id,
        avatar_url=fit_passport.get("avatar_url"),
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
