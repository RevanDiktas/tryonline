"""
Garment CRUD + GLB file upload for brand dashboard — JWT-protected.
- GET    /api/garments                    -- list garments for the authenticated brand
- POST   /api/garments                    -- create garment row
- PUT    /api/garments/{garment_id}       -- update garment row
- DELETE /api/garments/{garment_id}       -- delete garment row
- POST   /api/garments/{garment_id}/upload -- upload GLB file for a size
"""
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel

from app.config import get_settings
from app.api.deps import get_current_user_id
from app.services.supabase import SupabaseService

router = APIRouter()
settings = get_settings()
supabase = SupabaseService()

VALID_CATEGORIES = ["tops", "bottoms", "outerwear", "dresses", "accessories"]
VALID_FIT_TYPES = ["slim", "regular", "oversized"]
# Letter sizes (XXS-XXXL) plus numeric/EU systems (Women 32-46, Men 44-58). A garment uses
# one system; keys are stored as-is in the sizes / size_chart JSONB.
VALID_SIZES = [
    "xxs", "xs", "s", "m", "l", "xl", "xxl", "xxxl",
    "32", "34", "36", "38", "40", "42", "44", "46",
    "48", "50", "52", "54", "56", "58",
]


def _storage_product_folder(garment: dict) -> str:
    """Folder name under garments/{brand_id}/ — same as theme product.handle when using handles."""
    pid = (garment.get("shopify_product_id") or "").strip()
    ph = (garment.get("shopify_product_handle") or "").strip()
    return pid or ph or str(garment.get("id"))


def _get_user_brand_id(user_id: str) -> str:
    """Resolve the brand_id for an authenticated user. Raises 403 if no brand."""
    brand = supabase.get_brand_by_user_id(user_id)
    if not brand:
        raise HTTPException(status_code=403, detail="No brand found for this user")
    return str(brand["id"])


def _verify_garment_ownership(garment_id: str, brand_id: str) -> dict:
    """Load a garment and verify it belongs to the given brand. Raises 404/403."""
    r = supabase.client.table("garments").select("*").eq("id", garment_id).limit(1).execute()
    if not r.data:
        raise HTTPException(status_code=404, detail="Garment not found")
    garment = r.data[0]
    if str(garment.get("brand_id")) != brand_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return garment


class GarmentCreate(BaseModel):
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
    fabric_config: Optional[dict] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_garments(user_id: str = Depends(get_current_user_id)):
    """List all garments for the authenticated user's brand."""
    brand_id = _get_user_brand_id(user_id)
    try:
        r = supabase.client.table("garments").select("*").eq(
            "brand_id", brand_id
        ).order("created_at", desc=True).execute()
        return {"ok": True, "garments": r.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_garment(body: GarmentCreate, user_id: str = Depends(get_current_user_id)):
    """Create a new garment for the authenticated user's brand."""
    brand_id = _get_user_brand_id(user_id)

    if body.category and body.category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {VALID_CATEGORIES}")
    if body.fit_type and body.fit_type not in VALID_FIT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid fit_type. Must be one of: {VALID_FIT_TYPES}")

    spid = (body.shopify_product_id or "").strip() or None
    row = {
        "brand_id": brand_id,
        "name": body.name,
        "category": body.category,
        "shopify_product_id": spid,
        "fit_type": body.fit_type,
        "size_chart": body.size_chart or {},
        "sizes": {},
        "is_active": True,
    }
    if spid:
        row["shopify_product_handle"] = spid
    try:
        ins = supabase.client.table("garments").insert(row).execute()
        if not ins.data or len(ins.data) == 0:
            raise HTTPException(status_code=500, detail="Insert returned no data")

        garment = ins.data[0]
        garment_id = str(garment["id"])
        product_folder = _storage_product_folder(garment) or garment_id

        supabase.ensure_garments_bucket()
        try:
            bucket = supabase.client.storage.from_(settings.garments_bucket)
            placeholder_path = f"{brand_id}/{product_folder}/.folder"
            bucket.upload(
                placeholder_path,
                b"",
                {"content-type": "application/octet-stream", "x-upsert": "true"},
            )
        except Exception as e:
            print(f"[Garments] Folder creation note: {e}")

        return {"ok": True, "garment": garment}
    except HTTPException:
        raise
    except Exception as e:
        err = str(e)
        if spid and "shopify_product_handle" in err.lower():
            row.pop("shopify_product_handle", None)
            try:
                ins = supabase.client.table("garments").insert(row).execute()
                if not ins.data or len(ins.data) == 0:
                    raise HTTPException(status_code=500, detail="Insert returned no data")
                garment = ins.data[0]
                garment_id = str(garment["id"])
                product_folder = _storage_product_folder(garment) or garment_id
                supabase.ensure_garments_bucket()
                try:
                    bucket = supabase.client.storage.from_(settings.garments_bucket)
                    placeholder_path = f"{brand_id}/{product_folder}/.folder"
                    bucket.upload(
                        placeholder_path,
                        b"",
                        {"content-type": "application/octet-stream", "x-upsert": "true"},
                    )
                except Exception as e2:
                    print(f"[Garments] Folder creation note: {e2}")
                return {"ok": True, "garment": garment}
            except Exception as e2:
                raise HTTPException(status_code=500, detail=str(e2))
        raise HTTPException(status_code=500, detail=err)


@router.put("/{garment_id}")
async def update_garment(garment_id: str, body: GarmentUpdate, user_id: str = Depends(get_current_user_id)):
    """Update garment metadata. Verifies brand ownership."""
    brand_id = _get_user_brand_id(user_id)
    _verify_garment_ownership(garment_id, brand_id)

    updates = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.category is not None:
        if body.category not in VALID_CATEGORIES:
            raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {VALID_CATEGORIES}")
        updates["category"] = body.category
    if body.shopify_product_id is not None:
        v = (body.shopify_product_id or "").strip() or None
        updates["shopify_product_id"] = v
        updates["shopify_product_handle"] = v
    if body.fit_type is not None:
        if body.fit_type not in VALID_FIT_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid fit_type. Must be one of: {VALID_FIT_TYPES}")
        updates["fit_type"] = body.fit_type
    if body.size_chart is not None:
        updates["size_chart"] = body.size_chart
    if body.fabric_config is not None:
        updates["fabric_config"] = body.fabric_config
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
        err = str(e)
        if "shopify_product_handle" in err.lower() and "shopify_product_handle" in updates:
            updates.pop("shopify_product_handle", None)
            if not updates:
                raise HTTPException(status_code=400, detail="No fields to update")
            try:
                r = supabase.client.table("garments").update(updates).eq("id", garment_id).execute()
                if r.data and len(r.data) > 0:
                    return {"ok": True, "garment": r.data[0]}
            except Exception as e2:
                raise HTTPException(status_code=500, detail=str(e2))
            raise HTTPException(status_code=404, detail="Garment not found")
        raise HTTPException(status_code=500, detail=err)


@router.delete("/{garment_id}")
async def delete_garment(garment_id: str, user_id: str = Depends(get_current_user_id)):
    """Delete a garment. Verifies brand ownership."""
    brand_id = _get_user_brand_id(user_id)
    garment = _verify_garment_ownership(garment_id, brand_id)

    sizes = garment.get("sizes") or {}
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


@router.post("/{garment_id}/sync")
async def sync_garment_sizes(garment_id: str, user_id: str = Depends(get_current_user_id)):
    """Scan storage for existing GLB files and update the sizes column."""
    brand_id = _get_user_brand_id(user_id)
    garment = _verify_garment_ownership(garment_id, brand_id)

    product_id = _storage_product_folder(garment) or garment_id
    folder_path = f"{brand_id}/{product_id}"
    bucket = supabase.client.storage.from_(settings.garments_bucket)

    try:
        files = bucket.list(folder_path)
    except Exception:
        files = []

    sizes = {}
    for f in files:
        name = f.get("name", "") if isinstance(f, dict) else str(f)
        name_lower = name.lower()
        for sz in VALID_SIZES:
            if name_lower == f"{sz}.glb":
                sizes[sz] = f"garments/{folder_path}/{name}"
                break

    supabase.client.table("garments").update({"sizes": sizes}).eq("id", garment_id).execute()
    return {"ok": True, "sizes": sizes, "folder": folder_path}


@router.post("/{garment_id}/upload")
async def upload_garment_glb(
    garment_id: str,
    size: str = Form(..., description="Size key: xs, s, m, l, xl"),
    file: UploadFile = File(..., description="GLB file"),
    user_id: str = Depends(get_current_user_id),
):
    """Upload a GLB file for a specific size. Verifies brand ownership."""
    brand_id = _get_user_brand_id(user_id)
    garment = _verify_garment_ownership(garment_id, brand_id)

    size_key = size.strip().lower()
    if size_key not in VALID_SIZES:
        raise HTTPException(status_code=400, detail=f"Invalid size. Must be one of: {VALID_SIZES}")

    if not file.filename or not file.filename.lower().endswith(".glb"):
        raise HTTPException(status_code=400, detail="Only .glb files are accepted")

    product_id = _storage_product_folder(garment) or garment_id
    current_sizes = garment.get("sizes") or {}

    filename = f"{size_key}.glb"
    storage_path = f"{brand_id}/{product_id}/{filename}"

    content = await file.read()
    bucket = supabase.client.storage.from_(settings.garments_bucket)

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

    current_sizes[size_key] = f"garments/{storage_path}"
    supabase.client.table("garments").update({"sizes": current_sizes}).eq("id", garment_id).execute()

    return {"ok": True, "size": size_key, "url": full_url, "path": storage_path}


@router.post("/{garment_id}/upload-obj")
async def upload_garment_obj(
    garment_id: str,
    size: str = Form(..., description="Size key: xs, s, m, l, xl"),
    file: UploadFile = File(..., description="OBJ mesh file (triangulated)"),
    user_id: str = Depends(get_current_user_id),
):
    """Upload an OBJ mesh for cloth draping simulation. Stored alongside GLB files."""
    brand_id = _get_user_brand_id(user_id)
    garment = _verify_garment_ownership(garment_id, brand_id)

    size_key = size.strip().lower()
    if size_key not in VALID_SIZES:
        raise HTTPException(status_code=400, detail=f"Invalid size. Must be one of: {VALID_SIZES}")

    if not file.filename or not file.filename.lower().endswith(".obj"):
        raise HTTPException(status_code=400, detail="Only .obj files are accepted")

    product_id = _storage_product_folder(garment) or garment_id
    current_obj_sizes = garment.get("obj_sizes") or {}

    filename = f"{size_key}.obj"
    storage_path = f"{brand_id}/{product_id}/{filename}"

    content = await file.read()
    bucket = supabase.client.storage.from_(settings.garments_bucket)

    old_path = current_obj_sizes.get(size_key)
    if old_path and isinstance(old_path, str) and not old_path.startswith("http"):
        try:
            bucket.remove([old_path])
        except Exception:
            pass

    bucket.upload(
        storage_path,
        content,
        {"content-type": "model/obj", "x-upsert": "true"},
    )

    full_url = bucket.get_public_url(storage_path)

    current_obj_sizes[size_key] = f"garments/{storage_path}"
    supabase.client.table("garments").update({"obj_sizes": current_obj_sizes}).eq("id", garment_id).execute()

    return {"ok": True, "size": size_key, "url": full_url, "path": storage_path}


@router.put("/{garment_id}/fabric")
async def update_fabric_config(
    garment_id: str,
    fabric_config: dict,
    user_id: str = Depends(get_current_user_id),
):
    """Update fabric material properties for cloth simulation."""
    brand_id = _get_user_brand_id(user_id)
    _verify_garment_ownership(garment_id, brand_id)

    valid_keys = {"stretch_compliance", "bend_compliance", "thickness", "density", "friction", "damping", "preset"}
    filtered = {k: v for k, v in fabric_config.items() if k in valid_keys}

    supabase.client.table("garments").update({"fabric_config": filtered}).eq("id", garment_id).execute()
    return {"ok": True, "fabric_config": filtered}
