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
        thumbnail_url: Optional[str] = None
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
        response = self.client.storage.from_(settings.photos_bucket).create_signed_url(
            photo_path, 
            expires_in
        )
        return response.get("signedURL", "")
    
    async def upload_avatar(self, user_id: str, file_data: bytes, filename: str) -> str:
        """Upload avatar GLB to storage"""
        file_path = f"{user_id}/{filename}"
        
        self.client.storage.from_(settings.avatars_bucket).upload(
            file_path,
            file_data,
            {"content-type": "model/gltf-binary"}
        )
        
        # Get public URL
        public_url = self.client.storage.from_(settings.avatars_bucket).get_public_url(file_path)
        return public_url
    
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
