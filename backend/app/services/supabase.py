"""
Supabase service for database and storage operations
"""
from supabase import create_client, Client
from functools import lru_cache
from typing import Optional, Dict, Any, Tuple
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
        measurements: Dict[str, Any],  # Accept both int and float
        thumbnail_url: Optional[str] = None,
        pipeline_files: Optional[Dict[str, str]] = None
    ) -> bool:
        """Update fit passport with avatar and measurements
        
        CRITICAL: All measurements MUST be integers (database columns are INTEGER type)
        """
        def to_int(value):
            """Convert value to integer, return None if invalid"""
            if value is None:
                return None
            try:
                return int(round(float(value)))
            except (ValueError, TypeError):
                return None
        
        update_data = {
            "avatar_url": avatar_url,
            "avatar_thumbnail_url": thumbnail_url,
            "status": "completed",
            "processing_completed_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            # Measurements - convert all to integers
            "chest": to_int(measurements.get("chest")),
            "waist": to_int(measurements.get("waist")),
            "hips": to_int(measurements.get("hips")),
            "inseam": to_int(measurements.get("inseam")),
            "shoulder_width": to_int(measurements.get("shoulder_width")),
            "arm_length": to_int(measurements.get("arm_length")),
            "neck": to_int(measurements.get("neck")),
            "thigh": to_int(measurements.get("thigh")),
            "torso_length": to_int(measurements.get("torso_length")),
        }
        
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
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
        measurements: Dict[str, Any]  # Accept both int and float
    ) -> bool:
        """Update only measurements (user-corrected)
        
        CRITICAL: All measurements MUST be integers (database columns are INTEGER type)
        """
        def to_int(value):
            """Convert value to integer, return None if invalid"""
            if value is None:
                return None
            try:
                return int(round(float(value)))
            except (ValueError, TypeError):
                return None
        
        update_data = {"updated_at": datetime.utcnow().isoformat()}
        
        # Convert all measurements to integers
        for key, value in measurements.items():
            int_value = to_int(value)
            if int_value is not None:
                update_data[key] = int_value
        
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
    # USER ADDRESSES (Shopper Passport)
    # ==========================================
    
    async def get_addresses(self, user_id: str) -> list:
        """List all addresses for a user, default first."""
        response = (
            self.client.table("user_addresses")
            .select("*")
            .eq("user_id", user_id)
            .order("is_default", desc=True)
            .order("created_at", desc=False)
            .execute()
        )
        return list(response.data) if response.data else []

    async def get_default_address(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the default shipping address for a user, or the first address if none is default."""
        addresses = await self.get_addresses(user_id)
        if not addresses:
            return None
        default = next((a for a in addresses if a.get("is_default")), addresses[0])
        return default
    
    async def create_address(
        self,
        user_id: str,
        label: str,
        name: str,
        line1: str,
        city: str,
        postal_code: str,
        country: str,
        line2: Optional[str] = None,
        state: Optional[str] = None,
        is_default: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Create address. If is_default=True, unsets other defaults for this user."""
        if is_default:
            self.client.table("user_addresses").update({"is_default": False}).eq("user_id", user_id).execute()
        row = {
            "user_id": user_id,
            "label": label,
            "name": name,
            "line1": line1,
            "line2": line2 or None,
            "city": city,
            "state": state or None,
            "postal_code": postal_code,
            "country": country,
            "is_default": is_default,
        }
        response = self.client.table("user_addresses").insert(row).execute()
        return response.data[0] if response.data else None
    
    async def update_address(
        self,
        address_id: str,
        user_id: str,
        label: Optional[str] = None,
        name: Optional[str] = None,
        line1: Optional[str] = None,
        line2: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        postal_code: Optional[str] = None,
        country: Optional[str] = None,
        is_default: Optional[bool] = None,
    ) -> bool:
        """Update address. Verifies user_id owns the address. If is_default=True, unsets others."""
        # Verify ownership
        check = self.client.table("user_addresses").select("id").eq("id", address_id).eq("user_id", user_id).execute()
        if not check.data:
            return False
        update_data = {}
        if label is not None:
            update_data["label"] = label
        if name is not None:
            update_data["name"] = name
        if line1 is not None:
            update_data["line1"] = line1
        if line2 is not None:
            update_data["line2"] = line2
        if city is not None:
            update_data["city"] = city
        if state is not None:
            update_data["state"] = state
        if postal_code is not None:
            update_data["postal_code"] = postal_code
        if country is not None:
            update_data["country"] = country
        if is_default is not None:
            update_data["is_default"] = is_default
            if is_default:
                self.client.table("user_addresses").update({"is_default": False}).eq("user_id", user_id).execute()
        if not update_data:
            return True
        response = self.client.table("user_addresses").update(update_data).eq("id", address_id).eq("user_id", user_id).execute()
        return len(response.data) > 0
    
    async def delete_address(self, address_id: str, user_id: str) -> bool:
        """Delete address. Verifies user_id owns the address."""
        response = self.client.table("user_addresses").delete().eq("id", address_id).eq("user_id", user_id).execute()
        return len(response.data) > 0
    
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
    # ANALYTICS OPERATIONS (Category A schema)
    # ==========================================

    async def create_tryon_session(
        self,
        user_id: Optional[str] = None,
        shop_domain: Optional[str] = None,
        product_id: Optional[str] = None,
        product_name: Optional[str] = None,
        variant_id: Optional[str] = None,
        brand_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create try-on session, return session_id for attribution"""
        import uuid
        session_token = str(uuid.uuid4())
        row = {
            "session_token": session_token,
            "user_id": user_id,
            "shop_domain": shop_domain,
            "product_id": product_id,
            "product_name": product_name,
            "variant_id": variant_id,
            "action": "opened",
        }
        response = self.client.table("tryon_sessions").insert(row).execute()
        if response.data and len(response.data) > 0:
            session_id = response.data[0]["id"]
            return {"session_id": str(session_id), "session_token": session_token}
        return None

    async def _get_preferred_fit(self, user_id: str) -> Optional[str]:
        """Fetch preferred_fit from fit_passports when user_id present. Used for enrichment."""
        try:
            r = self.client.table("fit_passports").select("preferred_fit").eq("user_id", user_id).single().execute()
            if r.data and r.data.get("preferred_fit"):
                return str(r.data["preferred_fit"])
        except Exception:
            pass
        return None

    async def _get_user_region(self, user_id: str) -> Tuple[Optional[str], Optional[str]]:
        """Get country and city for a user: from users table, else from default user_addresses. Returns (country, city)."""
        try:
            r = self.client.table("users").select("country, city").eq("id", user_id).single().execute()
            if r.data:
                uc, ucity = r.data.get("country"), r.data.get("city")
                if uc or ucity:
                    return (uc, ucity)
        except Exception:
            pass
        try:
            addr = await self.get_default_address(user_id)
            if addr:
                return (addr.get("country"), addr.get("city"))
        except Exception:
            pass
        return (None, None)

    def _resolve_brand_id(self, shop_domain: str) -> Optional[str]:
        """Resolve brand_id from brands.shopify_domain. Returns brand id (str) or None."""
        if not shop_domain or not shop_domain.strip():
            return None
        try:
            r = self.client.table("brands").select("id").eq("shopify_domain", shop_domain.strip()).limit(1).execute()
            if r.data and len(r.data) > 0:
                return str(r.data[0]["id"])
        except Exception:
            pass
        return None

    def upsert_brand_for_shop(self, shop_domain: str, shopify_access_token: str) -> Optional[str]:
        """Create or update brand by shopify_domain; set shopify_access_token. Returns brand id or None."""
        if not shop_domain or not shop_domain.strip() or not shopify_access_token:
            return None
        shop = shop_domain.strip()
        try:
            r = self.client.table("brands").select("id").eq("shopify_domain", shop).limit(1).execute()
            if r.data and len(r.data) > 0:
                brand_id = str(r.data[0]["id"])
                self.client.table("brands").update({
                    "shopify_access_token": shopify_access_token,
                    "updated_at": datetime.utcnow().isoformat(),
                }).eq("id", brand_id).execute()
                return brand_id
            # Insert new brand (name/email required by schema)
            ins = self.client.table("brands").insert({
                "name": shop,
                "email": f"{shop.replace('.', '-')}@tryon-placeholder.local",
                "shopify_domain": shop,
                "shopify_access_token": shopify_access_token,
                "status": "active",
            }).execute()
            if ins.data and len(ins.data) > 0:
                return str(ins.data[0]["id"])
        except Exception:
            pass
        return None

    def has_shopify_session(self, shop_domain: str) -> bool:
        """Return True if we have a non-empty shopify_access_token for this shop."""
        if not shop_domain or not shop_domain.strip():
            return False
        try:
            r = self.client.table("brands").select("shopify_access_token").eq("shopify_domain", shop_domain.strip()).limit(1).execute()
            if r.data and len(r.data) > 0 and r.data[0].get("shopify_access_token"):
                return True
        except Exception:
            pass
        return False

    async def track_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        brand_id: Optional[str] = None,
        shop_domain: Optional[str] = None,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
        country: Optional[str] = None,
        city: Optional[str] = None,
        preferred_fit: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[str]:
        """Track analytics event — aligned to analytics_events schema. Enriches preferred_fit, country/city (user profile), brand_id (shop_domain)."""
        # Enrich preferred_fit from fit_passports when user_id present
        if user_id:
            db_preferred_fit = await self._get_preferred_fit(user_id)
            preferred_fit = db_preferred_fit if db_preferred_fit is not None else preferred_fit
        # Enrich country/city from user profile (users or default address) when user_id present and not already set
        if user_id and (country is None or city is None):
            region_country, region_city = await self._get_user_region(user_id)
            if country is None and region_country:
                country = region_country
            if city is None and region_city:
                city = region_city
        # Resolve brand_id from shop_domain when not already set
        if shop_domain and brand_id is None:
            resolved_brand_id = self._resolve_brand_id(shop_domain)
            if resolved_brand_id:
                brand_id = resolved_brand_id
        row = {
            "event_type": event_type,
            "user_id": user_id,
            "session_id": session_id,
            "brand_id": brand_id,
            "shop_domain": shop_domain,
            "product_id": product_id,
            "variant_id": variant_id,
            "country": country,
            "city": city,
            "preferred_fit": preferred_fit,
            "event_data": event_data or {},
            "user_agent": user_agent,
            "ip_address": ip_address,
        }
        # Drop None values so DB uses defaults
        row = {k: v for k, v in row.items() if v is not None}
        response = self.client.table("analytics_events").insert(row).execute()
        return str(response.data[0]["id"]) if response.data else None

    async def track_purchase(
        self,
        order_id: str,
        session_id: Optional[str] = None,
        shop_domain: Optional[str] = None,
        amount: float = 0,
        currency: str = "USD",
        event_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Insert purchase event. Idempotent by order_id.
        Returns event_id or None if duplicate (already processed).
        """
        payload = event_data or {}
        payload["order_id"] = order_id
        payload["amount"] = amount
        payload["currency"] = currency

        row = {
            "event_type": "purchase",
            "session_id": session_id,
            "shop_domain": shop_domain,
            "event_data": payload,
        }
        row = {k: v for k, v in row.items() if v is not None}

        try:
            response = self.client.table("analytics_events").insert(row).execute()
            return str(response.data[0]["id"]) if response.data else None
        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                return None  # Idempotent: already processed
            raise


# Singleton instance
supabase_service = SupabaseService()
