"""
Supabase service for database and storage operations
"""
import traceback

from supabase import create_client, Client
from functools import lru_cache
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

from app.config import get_settings


settings = get_settings()


def _canonical_shopify_domain(shop_domain: str) -> str:
    """Normalize Shopify admin hostname to slug.myshopify.com (lowercase)."""
    s = (shop_domain or "").strip().lower()
    if not s:
        return s
    if s.endswith(".myshopify.com"):
        return s
    if "." in s:
        return s
    return f"{s}.myshopify.com"


def _shopify_domain_lookup_keys(shop_domain: str) -> list[str]:
    """Possible brands.shopify_domain values for the same shop (short slug vs full host)."""
    s = (shop_domain or "").strip().lower()
    if not s:
        return []
    canonical = _canonical_shopify_domain(s)
    short = canonical[: -len(".myshopify.com")] if canonical.endswith(".myshopify.com") else ""
    ordered = [canonical, s, short] if short else [canonical, s]
    out: list[str] = []
    seen: set[str] = set()
    for k in ordered:
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _normalize_brand_shopify_domain_for_storage(shop_domain: str) -> str:
    """Store canonical myshopify host when the value is a bare slug or *.myshopify.com."""
    raw = (shop_domain or "").strip()
    if not raw:
        return raw
    sl = raw.lower()
    if sl.endswith(".myshopify.com") or "." not in sl:
        return _canonical_shopify_domain(raw)
    return raw


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
        try:
            response = self.client.table("fit_passports").select("*").eq("user_id", user_id).single().execute()
            return response.data if response.data else None
        except Exception:
            # .single() throws PGRST116 when 0 rows found
            response = self.client.table("fit_passports").select("*").eq("user_id", user_id).execute()
            return response.data[0] if response.data else None
    
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
        
        if pipeline_files:
            update_data["pipeline_files"] = pipeline_files
        
        try:
            response = self.client.table("fit_passports").update(update_data).eq("user_id", user_id).execute()
            return len(response.data) > 0
        except Exception as e:
            if "pipeline_files" in str(e) and pipeline_files:
                print(f"[Supabase] pipeline_files column missing, retrying without it")
                update_data.pop("pipeline_files", None)
                response = self.client.table("fit_passports").update(update_data).eq("user_id", user_id).execute()
                return len(response.data) > 0
            raise
    
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
        """Get signed URL for private photo (photos bucket is NOT public)."""
        try:
            response = self.client.storage.from_(settings.photos_bucket).create_signed_url(
                photo_path, 
                expires_in
            )
            url = ""
            if isinstance(response, dict):
                url = response.get("signedURL") or response.get("signedUrl") or ""
            elif hasattr(response, "signedURL"):
                url = response.signedURL or ""
            elif hasattr(response, "signedUrl"):
                url = response.signedUrl or ""
            if not url:
                print(f"[Supabase] Signed URL response has no URL: {response}")
            return url
        except Exception as e:
            print(f"[Supabase] Error creating signed URL for {photo_path}: {e}")
            return ""
    
    def ensure_avatars_bucket(self) -> bool:
        """Create the avatars storage bucket if it doesn't exist."""
        try:
            self.client.storage.create_bucket(
                settings.avatars_bucket,
                options={"public": True}
            )
            print(f"[Supabase] Created bucket: {settings.avatars_bucket}")
            return True
        except Exception as e:
            msg = str(e).lower()
            if "already exists" in msg or "duplicate" in msg or "409" in msg:
                return True
            print(f"[Supabase] ensure_avatars_bucket error: {e}")
            return False
    
    async def upload_avatar(self, user_id: str, file_data: bytes, filename: str) -> str:
        """
        Upload avatar file to storage (upsert — overwrites if already exists).
        
        Storage path: avatars/{user_id}/{filename}
        """
        file_path = f"{user_id}/{filename}"
        
        content_types = {
            ".glb": "model/gltf-binary",
            ".obj": "model/obj",
            ".png": "image/png",
            ".json": "application/json",
        }
        ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
        content_type = content_types.get(ext, "application/octet-stream")
        
        bucket = self.client.storage.from_(settings.avatars_bucket)
        
        # Strategy: try upload with upsert header, fall back to remove+upload, fall back to update
        try:
            bucket.upload(
                file_path, file_data,
                {"content-type": content_type, "x-upsert": "true"}
            )
        except Exception as first_err:
            print(f"[Supabase] Upload attempt 1 failed for {file_path}: {first_err}")
            try:
                bucket.remove([file_path])
                bucket.upload(file_path, file_data, {"content-type": content_type})
            except Exception as second_err:
                print(f"[Supabase] Upload attempt 2 (remove+upload) failed: {second_err}")
                try:
                    bucket.update(file_path, file_data, {"content-type": content_type})
                except Exception as third_err:
                    print(f"[Supabase] Upload attempt 3 (update) failed: {third_err}")
                    raise
        
        return bucket.get_public_url(file_path)
    
    async def upload_pipeline_files(
        self, 
        user_id: str, 
        files_bytes: dict,
        file_key_to_filename: dict = None
    ) -> dict:
        """
        Upload all pipeline output files to Supabase storage.
        Returns: Dict of {file_key: public_url}
        """
        self.ensure_avatars_bucket()
        
        if file_key_to_filename is None:
            file_key_to_filename = {
                "avatar_glb": "avatar_textured.glb",
                "avatar_glb_alt": "avatar_textured.glb",
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
        
        SKIP_KEYS = {"skin_detection_mask"}
        
        uploaded_urls = {}
        
        for file_key, file_data in files_bytes.items():
            if file_key in SKIP_KEYS:
                print(f"[Supabase] Skipping {file_key} ({len(file_data)/1024:.0f} KB, debug-only)")
                continue
            if file_key == "avatar_glb_alt" and "avatar_glb" in files_bytes:
                continue
            filename = file_key_to_filename.get(file_key, f"{file_key}.bin")
            try:
                url = await self.upload_avatar(user_id, file_data, filename)
                uploaded_urls[file_key] = url
                print(f"[Supabase] Uploaded {file_key} -> {filename} ({len(file_data) / 1024:.1f} KB)")
            except Exception as e:
                print(f"[Supabase] FAILED to upload {file_key} -> {filename}: {e}")
                import traceback
                traceback.print_exc()
        
        return uploaded_urls

    def ensure_garments_bucket(self) -> bool:
        """
        Ensure the shared garments bucket exists (for structure garments/{brand_id}/{product_id}/...).
        Idempotent: safe to call on every brand signup. Creates bucket only if missing.
        """
        try:
            self.client.storage.create_bucket(
                settings.garments_bucket,
                options={"public": True}
            )
            print(f"[Supabase] Created bucket: {settings.garments_bucket}")
            return True
        except Exception as e:
            msg = str(e).lower()
            if "already exists" in msg or "duplicate" in msg or "409" in msg:
                return True
            print(f"[Supabase] ensure_garments_bucket: {e}")
            return False

    @staticmethod
    def garment_storage_path(brand_id: str, product_id: str, filename: str) -> str:
        """
        Path inside the garments bucket: brand_id/product_id/filename.
        Use for uploads and for storing in garments.sizes (relative path).
        """
        return f"{brand_id}/{product_id}/{filename}".replace("//", "/")

    def get_garment_public_url(self, brand_id: str, product_id: str, filename: str) -> str:
        """Public URL for a file in garments bucket at brand_id/product_id/filename."""
        path = self.garment_storage_path(brand_id, product_id, filename)
        return self.client.storage.from_(settings.garments_bucket).get_public_url(path)
    
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
            for key in _shopify_domain_lookup_keys(shop_domain):
                r = self.client.table("brands").select("id").eq("shopify_domain", key).limit(1).execute()
                if r.data and len(r.data) > 0:
                    return str(r.data[0]["id"])
        except Exception:
            pass
        return None

    def upsert_brand_for_shop(self, shop_domain: str, shopify_access_token: str) -> Optional[str]:
        """Create or update brand by shopify_domain; set shopify_access_token. Returns brand id or None."""
        if not shop_domain or not shop_domain.strip() or not shopify_access_token:
            return None
        shop = _canonical_shopify_domain(shop_domain)
        if not shop:
            return None
        try:
            brand_id = None
            existing_domain: Optional[str] = None
            for key in _shopify_domain_lookup_keys(shop_domain):
                r = self.client.table("brands").select("id", "shopify_domain").eq("shopify_domain", key).limit(1).execute()
                if r.data and len(r.data) > 0:
                    brand_id = str(r.data[0]["id"])
                    existing_domain = (r.data[0].get("shopify_domain") or "").strip()
                    break
            if brand_id:
                upd: Dict[str, Any] = {
                    "shopify_access_token": shopify_access_token,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                if existing_domain and existing_domain.lower() != shop:
                    upd["shopify_domain"] = shop
                self.client.table("brands").update(upd).eq("id", brand_id).execute()
                return brand_id
            # Ensure garments bucket exists (garments/{brand_id}/{product_id}/...)
            self.ensure_garments_bucket()
            # Insert new brand (name/email required by schema)
            ins = self.client.table("brands").insert({
                "name": shop,
                "email": f"{shop.replace('.', '-')}@tryon-placeholder.local",
                "shopify_domain": shop,
                "shopify_access_token": shopify_access_token,
                "status": "active",
            }).execute()
            if ins.data and len(ins.data) > 0:
                new_brand_id = str(ins.data[0]["id"])
                self._create_brand_folder(new_brand_id)
                return new_brand_id
            print(f"[Supabase] upsert_brand_for_shop: insert OK but no row returned shop={shop!r}")
        except Exception as e:
            print(
                f"[Supabase] upsert_brand_for_shop error shop={shop_domain.strip()!r}: {e}\n{traceback.format_exc()}"
            )
        return None

    def get_brand_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Return the brand record owned by this user, or None."""
        if not user_id:
            return None
        try:
            r = self.client.table("brands").select("*").eq("user_id", user_id).limit(1).execute()
            if r.data and len(r.data) > 0:
                return r.data[0]
        except Exception as e:
            print(f"[Supabase] get_brand_by_user_id error: {e}")
        return None

    def get_brand_by_shopify_domain(self, shopify_domain: str) -> Optional[Dict[str, Any]]:
        """Return the brand record matching this shopify_domain, or None."""
        if not shopify_domain or not shopify_domain.strip():
            return None
        try:
            for key in _shopify_domain_lookup_keys(shopify_domain):
                r = self.client.table("brands").select("*").eq("shopify_domain", key).limit(1).execute()
                if r.data and len(r.data) > 0:
                    return r.data[0]
        except Exception as e:
            print(f"[Supabase] get_brand_by_shopify_domain error: {e}")
        return None

    def link_user_to_brand(self, brand_id: str, user_id: str, name: str, email: str) -> Optional[str]:
        """Update an existing brand (created by OAuth) with the user_id, real name, and email."""
        try:
            self.client.table("brands").update({
                "user_id": user_id,
                "name": name,
                "email": email,
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("id", brand_id).execute()
            self.ensure_garments_bucket()
            self._create_brand_folder(brand_id)
            print(f"[Supabase] Linked user {user_id} to brand {brand_id}")
            return brand_id
        except Exception as e:
            print(f"[Supabase] link_user_to_brand error: {e}")
            return None

    def _create_brand_folder(self, brand_id: str) -> bool:
        """Create a folder for this brand inside the garments bucket by uploading a placeholder."""
        try:
            bucket = self.client.storage.from_(settings.garments_bucket)
            placeholder_path = f"{brand_id}/.folder"
            bucket.upload(
                placeholder_path,
                b"",
                {"content-type": "application/octet-stream", "x-upsert": "true"},
            )
            print(f"[Supabase] Created garments folder: {settings.garments_bucket}/{brand_id}/")
            return True
        except Exception as e:
            msg = str(e).lower()
            if "already exists" in msg or "duplicate" in msg:
                return True
            print(f"[Supabase] _create_brand_folder error: {e}")
            return False

    def create_brand_for_user(
        self,
        user_id: str,
        name: str,
        email: str,
        shopify_domain: Optional[str] = None,
    ) -> Optional[str]:
        """Create a brand record linked to a user. Returns brand_id or None."""
        self.ensure_garments_bucket()
        row: Dict[str, Any] = {
            "user_id": user_id,
            "name": name,
            "email": email,
            "status": "active",
        }
        if shopify_domain and shopify_domain.strip():
            row["shopify_domain"] = _normalize_brand_shopify_domain_for_storage(shopify_domain)
        try:
            ins = self.client.table("brands").insert(row).execute()
            if ins.data and len(ins.data) > 0:
                brand_id = str(ins.data[0]["id"])
                self._create_brand_folder(brand_id)
                return brand_id
        except Exception as e:
            print(f"[Supabase] create_brand_for_user error: {e}")
        return None

    def clear_shopify_tokens_matching_shop_domain(self, shop_domain: str) -> None:
        """GDPR shop redact: clear token on any brands row whose shopify_domain matches this shop (slug or full host)."""
        keys = _shopify_domain_lookup_keys(shop_domain)
        if not keys:
            return
        try:
            self.client.table("brands").update({
                "shopify_access_token": None,
                "is_active": False,
            }).in_("shopify_domain", keys).execute()
        except Exception as e:
            print(f"[Supabase] clear_shopify_tokens_matching_shop_domain error: {e}")

    def has_shopify_session(self, shop_domain: str) -> bool:
        """Return True if we have a non-empty shopify_access_token for this shop."""
        if not shop_domain or not shop_domain.strip():
            return False
        try:
            for key in _shopify_domain_lookup_keys(shop_domain):
                r = (
                    self.client.table("brands")
                    .select("shopify_access_token")
                    .eq("shopify_domain", key)
                    .limit(1)
                    .execute()
                )
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
        event_id = str(response.data[0]["id"]) if response.data else None

        # Update tryon_sessions row with lifecycle data
        if session_id and event_type in (
            "size_recommended", "size_selected", "size_viewed",
            "add_to_cart", "purchase",
        ):
            self._update_tryon_session(session_id, event_type, event_data)

        return event_id

    def _update_tryon_session(
        self,
        session_id: str,
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Progressively populate tryon_sessions with size/action/purchase data."""
        ed = event_data or {}
        update: Dict[str, Any] = {}
        try:
            if event_type == "size_recommended":
                update["size_recommended"] = ed.get("size")
            elif event_type == "size_selected":
                update["size_selected"] = ed.get("size")
            elif event_type == "size_viewed":
                cur = self.client.table("tryon_sessions").select("sizes_viewed").eq("id", session_id).limit(1).execute()
                existing = []
                if cur.data and cur.data[0].get("sizes_viewed"):
                    existing = cur.data[0]["sizes_viewed"]
                    if isinstance(existing, str):
                        existing = [existing]
                new_size = ed.get("size")
                if new_size and new_size not in existing:
                    existing.append(new_size)
                update["sizes_viewed"] = existing
            elif event_type == "add_to_cart":
                update["action"] = "add_to_cart"
                if ed.get("size"):
                    update["size_selected"] = ed["size"]
            elif event_type == "purchase":
                update["action"] = "purchased"
                update["purchase_order_id"] = ed.get("order_id")
                update["purchase_amount"] = ed.get("amount")

            if update:
                self.client.table("tryon_sessions").update(update).eq("id", session_id).execute()
        except Exception:
            pass

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
        Enriches with brand_id (from shop_domain) and user_id (from tryon_sessions).
        Returns event_id or None if duplicate (already processed).
        """
        payload = event_data or {}
        payload["order_id"] = order_id
        payload["amount"] = amount
        payload["currency"] = currency

        brand_id = self._resolve_brand_id(shop_domain) if shop_domain else None

        user_id: Optional[str] = None
        if session_id:
            try:
                r = self.client.table("tryon_sessions").select("user_id").eq("id", session_id).single().execute()
                if r.data and r.data.get("user_id"):
                    user_id = str(r.data["user_id"])
            except Exception:
                pass

        row = {
            "event_type": "purchase",
            "user_id": user_id,
            "session_id": session_id,
            "brand_id": brand_id,
            "shop_domain": shop_domain,
            "event_data": payload,
        }
        row = {k: v for k, v in row.items() if v is not None}

        try:
            response = self.client.table("analytics_events").insert(row).execute()
            event_id = str(response.data[0]["id"]) if response.data else None
        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                return None  # Idempotent: already processed
            raise

        # Populate saved_items (closet) from order line_items
        if user_id and event_id:
            self._save_purchased_items_to_closet(
                user_id=user_id,
                shop_domain=shop_domain,
                order_data=payload,
                brand_name=None,
            )

        return event_id

    def _save_purchased_items_to_closet(
        self,
        user_id: str,
        shop_domain: Optional[str],
        order_data: Dict[str, Any],
        brand_name: Optional[str] = None,
    ) -> None:
        """Insert purchased line items into saved_items with list_type='closet'.
        Promotes any matching wishlist item to closet via upsert."""
        line_items = order_data.get("items") or []
        currency = str(order_data.get("currency", "USD") or "USD")

        # Resolve brand name from shop_domain if not provided
        if not brand_name and shop_domain:
            try:
                brand = self.get_brand_by_shopify_domain(shop_domain)
                if brand:
                    brand_name = brand.get("name")
            except Exception:
                pass

        # Also try to get line items from the raw Shopify order (nested in event_data)
        raw_line_items = order_data.get("line_items") or []

        items_to_save: list[Dict[str, Any]] = []

        for li in raw_line_items:
            product_id = str(li.get("product_id") or "").strip()
            if not product_id:
                continue
            row = {
                "user_id": user_id,
                "list_type": "closet",
                "product_id": product_id,
                "shop_domain": shop_domain or "",
                "variant_id": str(li.get("variant_id") or "").strip() or None,
                "product_name": (li.get("title") or li.get("name") or "").strip() or None,
                "product_price": float(li.get("price", 0) or 0),
                "currency": currency,
                "brand_name": brand_name,
            }
            items_to_save.append(row)

        if not items_to_save:
            return

        for item in items_to_save:
            try:
                # Remove wishlist entry if it exists (promote to closet)
                self.client.table("saved_items").delete().eq(
                    "user_id", user_id
                ).eq(
                    "product_id", item["product_id"]
                ).eq(
                    "shop_domain", item["shop_domain"]
                ).eq(
                    "list_type", "wishlist"
                ).execute()

                self.client.table("saved_items").upsert(
                    item,
                    on_conflict="user_id,product_id,shop_domain,list_type",
                ).execute()
            except Exception as e:
                print(f"[Supabase] _save_purchased_items_to_closet error for product {item.get('product_id')}: {e}")


# Singleton instance
supabase_service = SupabaseService()
