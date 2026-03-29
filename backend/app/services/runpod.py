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

    def _heatmap_base_url(self) -> Optional[str]:
        eid = (settings.runpod_heatmap_endpoint_id or "").strip()
        if not eid:
            return None
        return f"https://api.runpod.ai/v2/{eid}"

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
        
        url = f"{self.base_url}/run"
        print(f"[RunPod] Submitting job to: {url}")
        print(f"[RunPod] Payload: {payload}")
        print(f"[RunPod] Headers: Authorization={'SET' if self.api_key else 'NOT SET'}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                print(f"[RunPod] Response status: {response.status_code}")
                print(f"[RunPod] Response body: {response.text[:500]}")
                
                if response.status_code == 200:
                    data = response.json()
                    job_id = data.get("id")
                    if job_id:
                        print(f"[RunPod] ✅ Job submitted successfully: {job_id}")
                        return job_id
                    else:
                        print(f"[RunPod] ⚠️  Response missing 'id' field: {data}")
                        return None
                else:
                    print(f"[RunPod] ❌ Submit error: {response.status_code}")
                    print(f"[RunPod] Response: {response.text}")
                    return None
        except Exception as e:
            print(f"[RunPod] ❌ Exception submitting job: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status of a RunPod job
        Returns: {status, output, error}
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/status/{job_id}",
                    headers=self._get_headers(),
                    timeout=120.0  # large timeout — RunPod returns ~12MB of base64 files
                )
                
                if response.status_code != 200:
                    print(f"[RunPod] Status check failed: HTTP {response.status_code}")
                    return {"status": "ERROR", "error": f"HTTP {response.status_code}"}
                
                data = response.json()
                status = data.get("status", "UNKNOWN")
                output = data.get("output") or {}
                error = data.get("error")
                
                print(f"[RunPod] Job {job_id} status: {status}")
                if error:
                    print(f"[RunPod] Job {job_id} error: {error}")
                
                if status != "COMPLETED" or not output:
                    return {"status": status, "output": output, "error": error}
                
                # Pipeline error (handler returned {"error": "..."})
                if output.get("error"):
                    return {"status": "COMPLETED", "output": output, "error": output["error"]}
                
                # Decode base64 files into bytes
                processed_output = {
                    "measurements": output.get("measurements", {}),
                    "processing_time": output.get("processing_time_seconds"),
                    "files_bytes": {},
                    "file_sizes": output.get("file_sizes", {}),
                }
                
                files_base64 = output.get("files_base64", {})
                if not files_base64 and output.get("avatar_glb_base64"):
                    files_base64 = {"avatar_glb": output["avatar_glb_base64"]}
                
                print(f"[RunPod] Decoding {len(files_base64)} files from base64...")
                for file_key, file_b64 in files_base64.items():
                    try:
                        processed_output["files_bytes"][file_key] = base64.b64decode(file_b64)
                    except Exception as e:
                        print(f"[RunPod] Failed to decode {file_key}: {e}")
                
                print(f"[RunPod] Decoded {len(processed_output['files_bytes'])} files, measurements: {len(processed_output['measurements'])} values")
                
                return {"status": "COMPLETED", "output": processed_output, "error": None}
        except Exception as e:
            print(f"[RunPod] get_job_status exception: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "IN_PROGRESS", "output": None, "error": None}
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/cancel/{job_id}",
                headers=self._get_headers(),
                timeout=30.0
            )
            return response.status_code == 200

    async def submit_heatmap_job(self, input_payload: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Submit a job to the heatmap / Warp serverless endpoint (RUNPOD_HEATMAP_ENDPOINT_ID).
        Same API key as avatar; payload is passed as {"input": ...}.
        """
        base = self._heatmap_base_url()
        if not base:
            print("[RunPod heatmap] RUNPOD_HEATMAP_ENDPOINT_ID not set")
            return None
        if not self.api_key:
            print("[RunPod heatmap] RUNPOD_API_KEY not set")
            return None
        # Default input when omitted; explicit {} left as-is (e.g. tests).
        if input_payload is None:
            input_payload = {"action": "smoke"}
        payload = {"input": input_payload}
        url = f"{base}/run"
        print(f"[RunPod heatmap] POST {url}")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0,
                )
                print(f"[RunPod heatmap] submit status: {response.status_code}")
                if response.status_code != 200:
                    print(f"[RunPod heatmap] body: {response.text[:800]}")
                    return None
                data = response.json()
                job_id = data.get("id")
                if not job_id:
                    print(f"[RunPod heatmap] missing id in response: {data}")
                    return None
                print(f"[RunPod heatmap] job id: {job_id}")
                return job_id
        except Exception as e:
            print(f"[RunPod heatmap] submit exception: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def get_heatmap_job_status(self, job_id: str) -> Dict[str, Any]:
        """Poll heatmap endpoint job status (raw output; no avatar base64 decoding)."""
        base = self._heatmap_base_url()
        if not base:
            return {"status": "ERROR", "error": "RUNPOD_HEATMAP_ENDPOINT_ID not set", "output": None}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{base}/status/{job_id}",
                    headers=self._get_headers(),
                    timeout=120.0,
                )
                if response.status_code != 200:
                    return {
                        "status": "ERROR",
                        "error": f"HTTP {response.status_code}: {response.text[:500]}",
                        "output": None,
                    }
                data = response.json()
                return {
                    "status": data.get("status", "UNKNOWN"),
                    "output": data.get("output"),
                    "error": data.get("error"),
                }
        except Exception as e:
            print(f"[RunPod heatmap] status exception: {e}")
            return {"status": "ERROR", "error": str(e), "output": None}


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
    api_key = settings.runpod_api_key
    endpoint_id = settings.runpod_endpoint_id
    
    print(f"[RunPod Service] Initializing...")
    print(f"[RunPod Service] API Key: {'SET' if api_key else 'NOT SET (using mock)'}")
    print(f"[RunPod Service] Endpoint ID: {endpoint_id if endpoint_id else 'NOT SET (using mock)'}")
    
    if api_key and endpoint_id:
        service = RunPodService()
        print(f"[RunPod Service] ✅ Using real RunPod service")
        print(f"[RunPod Service] Base URL: {service.base_url}")
        return service
    else:
        print("[RunPod Service] ⚠️  RunPod not configured - using MOCK service")
        print("[RunPod Service] ⚠️  Jobs will NOT be submitted to RunPod!")
        print("[RunPod Service] ⚠️  Set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID environment variables")
        return MockRunPodService()


runpod_service = get_runpod_service()
