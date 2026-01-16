"""
RunPod service for GPU processing
"""
import httpx
import base64
from typing import Optional, Dict, Any
from app.config import get_settings

settings = get_settings()


class RunPodService:
    """Service for RunPod serverless GPU operations"""
    
    def __init__(self):
        self.api_key = settings.runpod_api_key
        self.endpoint_id = settings.runpod_endpoint_id
        self.base_url = f"https://api.runpod.ai/v2/{self.endpoint_id}"
        
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def submit_avatar_job(
        self,
        photo_url: str,
        height: int,
        weight: Optional[int],
        gender: str,
        user_id: str
    ) -> Optional[str]:
        """
        Submit avatar creation job to RunPod
        Returns job_id if successful
        """
        payload = {
            "input": {
                "photo_url": photo_url,
                "height": height,
                "weight": weight,
                "gender": gender,
                "user_id": user_id,
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/run",
                json=payload,
                headers=self._get_headers(),
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("id")
            else:
                print(f"RunPod submit error: {response.status_code} - {response.text}")
                return None
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status of a RunPod job
        Returns: {status, output, error}
        
        Output contains:
        - avatar_glb_base64: Base64-encoded GLB file
        - measurements: Standardized measurements dict
        - processing_time_seconds: Time taken
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/status/{job_id}",
                headers=self._get_headers(),
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "UNKNOWN")
                output = data.get("output", {})
                error = data.get("error")
                
                # Debug logging
                print(f"[RunPod] Job {job_id} status: {status}")
                if error:
                    print(f"[RunPod] Job {job_id} error: {error}")
                
                # Transform output to expected format
                processed_output = None
                if output:
                    processed_output = {
                        "measurements": output.get("measurements", {}),
                        "processing_time": output.get("processing_time_seconds"),
                        # All files as decoded bytes dict
                        "files_bytes": {},
                        "file_sizes": output.get("file_sizes", {}),
                    }
                    
                    # Decode all base64 files
                    files_base64 = output.get("files_base64", {})
                    if not files_base64:
                        # Fallback to old format (single GLB)
                        if output.get("avatar_glb_base64"):
                            files_base64 = {"avatar_glb": output["avatar_glb_base64"]}
                    
                    for file_key, file_base64 in files_base64.items():
                        try:
                            processed_output["files_bytes"][file_key] = base64.b64decode(
                                file_base64
                            )
                        except Exception as e:
                            print(f"Failed to decode {file_key} base64: {e}")
                
                return {
                    "status": data.get("status", "UNKNOWN"),
                    "output": processed_output,
                    "error": data.get("error"),
                }
            else:
                return {
                    "status": "ERROR",
                    "error": f"Failed to get status: {response.status_code}"
                }
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/cancel/{job_id}",
                headers=self._get_headers(),
                timeout=30.0
            )
            return response.status_code == 200


# Mock service for development without RunPod
class MockRunPodService:
    """Mock RunPod service for local development"""
    
    async def submit_avatar_job(
        self,
        photo_url: str,
        height: int,
        weight: Optional[int],
        gender: str,
        user_id: str
    ) -> str:
        """Mock job submission - returns fake job ID"""
        import uuid
        return f"mock-{uuid.uuid4().hex[:8]}"
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Mock job status - always returns completed with fake data"""
        return {
            "status": "COMPLETED",
            "output": {
                "avatar_url": "/models/avatar_with_tshirt_m.glb",
                "measurements": {
                    "chest": 102,
                    "waist": 83,
                    "hips": 96,
                    "inseam": 86,
                    "shoulder_width": 46,
                    "arm_length": 61,
                    "neck": 40,
                    "thigh": 61,
                    "torso_length": 58,
                }
            },
            "error": None
        }
    
    async def cancel_job(self, job_id: str) -> bool:
        return True


# Use mock service if RunPod not configured
def get_runpod_service():
    if settings.runpod_api_key and settings.runpod_endpoint_id:
        return RunPodService()
    else:
        print("⚠️  RunPod not configured, using mock service")
        return MockRunPodService()


runpod_service = get_runpod_service()
