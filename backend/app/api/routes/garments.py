"""
Garment CRUD + GLB file upload for brand dashboard.
- GET    /api/garments?brand_id=...       — list garments for a brand
- POST   /api/garments                    — create garment row
- PUT    /api/garments/{garment_id}       — update garment row
- DELETE /api/garments/{garment_id}       — delete garment row
- POST   /api/garments/{garment_id}/upload — upload GLB file for a size
"""
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel

from app.config import get_settings
from app.services.supabase import SupabaseService

router = APIRouter()
settings = get_settings()
supabase = SupabaseService()

VALID_CATEGORIES = ["tops", "bottoms", "outerwear", "dresses", "accessories"]
VALID_FIT_TYPES = ["slim", "regular", "oversized"]
VALID_SIZES = ["xs", "s", "m", "l", "xl", "xxl"]


class GarmentCreate(BaseModel):
    brand_id: str
    name: str
    category: Optional[str] = None
    shopify_product_id: Optional[str] = None
    fit_type: str = "regular"
    size_chart: Optional[dict] = None


class GarmentUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    shopify_product_id: Optional[str] = None
    fit_type: Optional[str] = None
    size_chart: Optional[dict] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_garments(brand_id: str = Query(...)):
    """List all garments for a brand."""
    try:
        r = supabase.client.table("garments").select("*").eq(
            "brand_id", brand_id
        ).order("created_at", desc=True).execute()
        return {"ok": True, "garments": r.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_garment(body: GarmentCreate):
    """Create a new garment row (no GLB files yet — upload separately)."""
    if body.category and body.category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {VALID_CATEGORIES}")
    if body.fit_type and body.fit_type not in VALID_FIT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid fit_type. Must be one of: {VALID_FIT_TYPES}")

    row = {
        "brand_id": body.brand_id,
        "name": body.name,
        "category": body.category,
        "shopify_product_id": body.shopify_product_id or None,
        "fit_type": body.fit_type,
        "size_chart": body.size_chart or {},
        "sizes": {},
        "is_active": True,
    }
    try:
        ins = supabase.client.table("garments").insert(row).execute()
        if ins.data and len(ins.data) > 0:
            return {"ok": True, "garment": ins.data[0]}
        raise HTTPException(status_code=500, detail="Insert returned no data")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{garment_id}")
async def update_garment(garment_id: str, body: GarmentUpdate):
    """Update garment metadata (name, category, Shopify product ID, etc.)."""
    updates = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.category is not None:
        if body.category not in VALID_CATEGORIES:
            raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {VALID_CATEGORIES}")
        updates["category"] = body.category
    if body.shopify_product_id is not None:
        updates["shopify_product_id"] = body.shopify_product_id
    if body.fit_type is not None:
        if body.fit_type not in VALID_FIT_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid fit_type. Must be one of: {VALID_FIT_TYPES}")
        updates["fit_type"] = body.fit_type
    if body.size_chart is not None:
        updates["size_chart"] = body.size_chart
    if body.is_active is not None:
        updates["is_active"] = body.is_active

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        r = supabase.client.table("garments").update(updates).eq("id", garment_id).execute()
        if r.data and len(r.data) > 0:
            return {"ok": True, "garment": r.data[0]}
        raise HTTPException(status_code=404, detail="Garment not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{garment_id}")
async def delete_garment(garment_id: str):
    """Delete a garment and its storage files."""
    try:
        r = supabase.client.table("garments").select("brand_id, sizes").eq("id", garment_id).limit(1).execute()
        if not r.data:
            raise HTTPException(status_code=404, detail="Garment not found")

        garment = r.data[0]
        brand_id = garment.get("brand_id")
        sizes = garment.get("sizes") or {}

        # Delete storage files
        if brand_id and sizes:
            paths_to_delete = []
            for path in sizes.values():
                if path and isinstance(path, str) and not path.startswith("http"):
                    paths_to_delete.append(path)
            if paths_to_delete:
                try:
                    supabase.client.storage.from_(settings.garments_bucket).remove(paths_to_delete)
                except Exception:
                    pass

        supabase.client.table("garments").delete().eq("id", garment_id).execute()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{garment_id}/upload")
async def upload_garment_glb(
    garment_id: str,
    size: str = Form(..., description="Size key: xs, s, m, l, xl"),
    file: UploadFile = File(..., description="GLB file"),
):
    """Upload a GLB file for a specific size of a garment."""
    size_key = size.strip().lower()
    if size_key not in VALID_SIZES:
        raise HTTPException(status_code=400, detail=f"Invalid size. Must be one of: {VALID_SIZES}")

    if not file.filename or not file.filename.lower().endswith(".glb"):
        raise HTTPException(status_code=400, detail="Only .glb files are accepted")

    try:
        r = supabase.client.table("garments").select("brand_id, shopify_product_id, sizes").eq(
            "id", garment_id
        ).limit(1).execute()
        if not r.data:
            raise HTTPException(status_code=404, detail="Garment not found")

        garment = r.data[0]
        brand_id = garment["brand_id"]
        product_id = garment.get("shopify_product_id") or garment_id
        current_sizes = garment.get("sizes") or {}

        filename = f"{size_key}.glb"
        storage_path = f"{brand_id}/{product_id}/{filename}"

        content = await file.read()
        bucket = supabase.client.storage.from_(settings.garments_bucket)

        # Delete existing file if present
        old_path = current_sizes.get(size_key)
        if old_path and isinstance(old_path, str) and not old_path.startswith("http"):
            try:
                bucket.remove([old_path])
            except Exception:
                pass

        bucket.upload(
            storage_path,
            content,
            {"content-type": "model/gltf-binary", "x-upsert": "true"},
        )

        full_url = bucket.get_public_url(storage_path)

        # Store the relative path in the sizes JSONB (backend resolves to full URL)
        current_sizes[size_key] = f"garments/{storage_path}"
        supabase.client.table("garments").update({"sizes": current_sizes}).eq("id", garment_id).execute()

        return {"ok": True, "size": size_key, "url": full_url, "path": storage_path}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
