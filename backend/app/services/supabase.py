"""
Supabase service for database and storage operations
"""
from supabase import create_client, Client
from functools import lru_cache
from typing import Optional, Dict, Any
from datetime import datetime

from app.config import get_settings


settings = get_settings()


@lru_cache()
def get_supabase_client() -> Client:
    """Get cached Supabase client with service role key"""
    return create_client(
        settings.supabase_url,
        settings.supabase_service_key
    )


class SupabaseService:
    """Service for Supabase operations"""
    
    def __init__(self):
        self.client = get_supabase_client()
    
    # ==========================================
    # FIT PASSPORT OPERATIONS
    # ==========================================
    
    async def get_fit_passport(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get fit passport by user ID"""
        response = self.client.table("fit_passports").select("*").eq("user_id", user_id).single().execute()
        return response.data if response.data else None
    
    async def update_fit_passport_status(
        self, 
        user_id: str, 
        status: str, 
        progress_message: str = ""
    ) -> bool:
        """Update processing status"""
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if status == "processing":
            update_data["processing_started_at"] = datetime.utcnow().isoformat()
        elif status in ["completed", "failed"]:
            update_data["processing_completed_at"] = datetime.utcnow().isoformat()
        
        response = self.client.table("fit_passports").update(update_data).eq("user_id", user_id).execute()
        return len(response.data) > 0
    
    async def update_fit_passport_with_results(
        self,
        user_id: str,
        avatar_url: str,
        measurements: Dict[str, int],
        thumbnail_url: Optional[str] = None,
        pipeline_files: Optional[Dict[str, str]] = None
    ) -> bool:
        """Update fit passport with avatar and measurements"""
        update_data = {
            "avatar_url": avatar_url,
            "avatar_thumbnail_url": thumbnail_url,
            "status": "completed",
            "processing_completed_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            # Measurements
            "chest": measurements.get("chest"),
            "waist": measurements.get("waist"),
            "hips": measurements.get("hips"),
            "inseam": measurements.get("inseam"),
            "shoulder_width": measurements.get("shoulder_width"),
            "arm_length": measurements.get("arm_length"),
            "neck": measurements.get("neck"),
            "thigh": measurements.get("thigh"),
            "torso_length": measurements.get("torso_length"),
        }
        
        # Store all pipeline file URLs in JSONB field (if column exists)
        if pipeline_files:
            # Try to update pipeline_files column if it exists
            # If column doesn't exist, files are still in storage and can be accessed via URLs
            update_data["pipeline_files"] = pipeline_files
        
        response = self.client.table("fit_passports").update(update_data).eq("user_id", user_id).execute()
        return len(response.data) > 0
    
    async def update_measurements(
        self,
        user_id: str,
        measurements: Dict[str, int]
    ) -> bool:
        """Update only measurements (user-corrected)"""
        update_data = {
            "updated_at": datetime.utcnow().isoformat(),
            **measurements
        }
        
        response = self.client.table("fit_passports").update(update_data).eq("user_id", user_id).execute()
        return len(response.data) > 0
    
    # ==========================================
    # USER PHOTO OPERATIONS
    # ==========================================
    
    async def get_user_photo(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get latest user photo"""
        response = (
            self.client.table("user_photos")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None
    
    # ==========================================
    # STORAGE OPERATIONS
    # ==========================================
    
    def get_photo_signed_url(self, photo_path: str, expires_in: int = 3600) -> str:
        """Get signed URL for private photo"""
        try:
            response = self.client.storage.from_(settings.photos_bucket).create_signed_url(
                photo_path, 
                expires_in
            )
            if isinstance(response, dict):
                return response.get("signedURL", "")
            elif hasattr(response, "signedURL"):
                return response.signedURL
            return ""
        except Exception as e:
            print(f"[Supabase] Error creating signed URL for {photo_path}: {e}")
            return ""
    
    async def upload_avatar(self, user_id: str, file_data: bytes, filename: str) -> str:
        """
        Upload avatar file to storage.
        
        Files are organized by user_id in folders:
        - Storage path: avatars/{user_id}/{filename}
        - This ensures each user's files are isolated in their own folder
        - Example: avatars/694af2e0-4b22-4cdf-801f-24dc8a731d8f/avatar_textured.glb
        """
        file_path = f"{user_id}/{filename}"
        print(f"[Supabase] Uploading to: avatars/{file_path} (user_id: {user_id})")
        
        # Determine content type based on extension
        content_type = "application/octet-stream"
        if filename.endswith(".glb"):
            content_type = "model/gltf-binary"
        elif filename.endswith(".obj"):
            content_type = "model/obj"
        elif filename.endswith(".png"):
            content_type = "image/png"
        elif filename.endswith(".json"):
            content_type = "application/json"
        elif filename.endswith(".npz"):
            content_type = "application/octet-stream"
        
        self.client.storage.from_(settings.avatars_bucket).upload(
            file_path,
            file_data,
            {"content-type": content_type}
        )
        
        # Get public URL
        public_url = self.client.storage.from_(settings.avatars_bucket).get_public_url(file_path)
        return public_url
    
    async def upload_pipeline_files(
        self, 
        user_id: str, 
        files_bytes: dict,
        file_key_to_filename: dict = None
    ) -> dict:
        """
        Upload all pipeline output files to Supabase storage.
        
        Args:
            user_id: User ID for folder organization
            files_bytes: Dict of {file_key: bytes_data}
            file_key_to_filename: Optional mapping of file_key to filename
        
        Returns:
            Dict of {file_key: public_url}
        """
        if file_key_to_filename is None:
            # Default filename mapping
            file_key_to_filename = {
                "avatar_glb": "avatar_textured.glb",
                "skin_texture": "skin_texture.png",
                "original_mesh": "body_original.obj",
                "smpl_params": "smpl_params.npz",
                "tpose_mesh": "body_tpose.obj",
                "apose_mesh": "body_apose.obj",
                "measurements": "measurements.json",
                "face_crop": "face_crop.png",
                "avatar_texture": "avatar_texture.png",
                "skin_detection_mask": "skin_detection_mask.png",
            }
        
        uploaded_urls = {}
        
        for file_key, file_data in files_bytes.items():
            filename = file_key_to_filename.get(file_key, f"{file_key}.bin")
            try:
                url = await self.upload_avatar(user_id, file_data, filename)
                uploaded_urls[file_key] = url
                print(f"Uploaded {file_key} -> {filename} ({len(file_data) / 1024:.1f} KB)")
            except Exception as e:
                print(f"Failed to upload {file_key}: {e}")
                # Continue with other files
        
        return uploaded_urls
    
    # ==========================================
    # ANALYTICS OPERATIONS
    # ==========================================
    
    async def track_event(
        self,
        user_id: str,
        event_type: str,
        brand_id: Optional[str] = None,
        garment_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Track analytics event"""
        event_data = {
            "user_id": user_id,
            "event_type": event_type,
            "brand_id": brand_id,
            "garment_id": garment_id,
            "session_id": session_id,
            "metadata": metadata or {},
        }
        
        response = self.client.table("analytics_events").insert(event_data).execute()
        return response.data[0]["id"] if response.data else None


# Singleton instance
supabase_service = SupabaseService()
