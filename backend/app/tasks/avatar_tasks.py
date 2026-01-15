"""
Avatar creation background tasks
"""
from app.tasks.celery_app import celery_app
from app.services.supabase import supabase_service
from app.services.runpod import runpod_service
import asyncio


@celery_app.task(bind=True, max_retries=3)
def create_avatar_task(
    self,
    user_id: str,
    photo_url: str,
    height: int,
    weight: int | None,
    gender: str
):
    """
    Celery task for avatar creation
    
    This runs in a worker process, handling:
    1. Submit to RunPod GPU
    2. Poll for completion
    3. Update database with results
    """
    try:
        # Run async code in sync context
        loop = asyncio.get_event_loop()
        
        # Update status
        loop.run_until_complete(
            supabase_service.update_fit_passport_status(
                user_id=user_id,
                status="processing"
            )
        )
        
        # Submit to RunPod
        runpod_job_id = loop.run_until_complete(
            runpod_service.submit_avatar_job(
                photo_url=photo_url,
                height=height,
                weight=weight,
                gender=gender,
                user_id=user_id
            )
        )
        
        if not runpod_job_id:
            raise Exception("Failed to submit job to GPU")
        
        # Poll for completion
        max_attempts = 60
        for attempt in range(max_attempts):
            asyncio.get_event_loop().run_until_complete(asyncio.sleep(5))
            
            status_result = loop.run_until_complete(
                runpod_service.get_job_status(runpod_job_id)
            )
            
            if status_result.get("status") == "COMPLETED":
                output = status_result.get("output", {})
                
                # Update database with results
                loop.run_until_complete(
                    supabase_service.update_fit_passport_with_results(
                        user_id=user_id,
                        avatar_url=output.get("avatar_url"),
                        measurements=output.get("measurements", {})
                    )
                )
                
                return {
                    "success": True,
                    "avatar_url": output.get("avatar_url"),
                    "measurements": output.get("measurements")
                }
            
            elif status_result.get("status") in ["FAILED", "CANCELLED"]:
                raise Exception(status_result.get("error", "GPU processing failed"))
        
        raise Exception("Avatar creation timed out")
        
    except Exception as e:
        # Update status to failed
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            supabase_service.update_fit_passport_status(
                user_id=user_id,
                status="failed"
            )
        )
        
        # Retry if we haven't exceeded max retries
        raise self.retry(exc=e, countdown=30)
