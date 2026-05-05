"""
Product / garment tryon config — model URLs, size chart, draped mesh integration
"""
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.supabase import supabase_service

router = APIRouter()

_GARMENT_SELECT_FULL = "id,sizes,size_chart,category,fit_type,obj_sizes,shopify_product_id,shopify_product_handle"
_GARMENT_SELECT_FALLBACK = "id,sizes,size_chart,category,fit_type,obj_sizes,shopify_product_id"
_HAS_SHOPIFY_PRODUCT_HANDLE: Optional[bool] = None


def _norm_pid(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _row_matches_product_id(row: dict[str, Any], product_id: str) -> bool:
    want = _norm_pid(product_id)
    if not want:
        return False
    for key in ("shopify_product_id", "shopify_product_handle"):
        if _norm_pid(row.get(key)) == want:
            return True
    return False


def _garment_select_columns() -> str:
    """Prefer handle column when present; older DBs may not have shopify_product_handle."""
    global _HAS_SHOPIFY_PRODUCT_HANDLE
    if _HAS_SHOPIFY_PRODUCT_HANDLE is True:
        return _GARMENT_SELECT_FULL
    if _HAS_SHOPIFY_PRODUCT_HANDLE is False:
        return _GARMENT_SELECT_FALLBACK
    try:
        supabase_service.client.table("garments").select("shopify_product_handle").limit(1).execute()
        _HAS_SHOPIFY_PRODUCT_HANDLE = True
    except Exception:
        _HAS_SHOPIFY_PRODUCT_HANDLE = False
    return _GARMENT_SELECT_FULL if _HAS_SHOPIFY_PRODUCT_HANDLE else _GARMENT_SELECT_FALLBACK


def _find_garment_row(product_id: str, brand_id: Optional[str]) -> Optional[dict[str, Any]]:
    cols = _garment_select_columns()
    if brand_id:
        try:
            r = (
                supabase_service.client.table("garments")
                .select(cols)
                .eq("brand_id", brand_id)
                .execute()
            )
            for row in r.data or []:
                if _row_matches_product_id(row, product_id):
                    return row
        except Exception:
            pass
    for field in ("shopify_product_id", "shopify_product_handle"):
        try:
            q = supabase_service.client.table("garments").select(cols)
            if brand_id:
                q = q.eq("brand_id", brand_id)
            r = q.eq(field, product_id).limit(1).execute()
            if r.data:
                return r.data[0]
        except Exception:
            continue
    return None


def _body_hash_from_user(user_id: str) -> Optional[str]:
    """Compute per-user body hash from fit passport for draping cache lookup."""
    from app.services.body_clustering import compute_body_hash
    try:
        r = supabase_service.client.table("fit_passports").select(
            "chest,waist,hips,height,weight,gender,inseam,shoulder_width,arm_length,neck,thigh,torso_length"
        ).eq("user_id", user_id).limit(1).execute()
        if not r.data:
            return None
        return compute_body_hash(user_id, r.data[0])
    except Exception:
        return None


def _get_draped_urls(garment_id: str, body_hash: str, sizes: list[str]) -> dict[str, str]:
    """Check draped_meshes cache for all sizes of this garment+body."""
    draped = {}
    try:
        r = supabase_service.client.table("draped_meshes").select(
            "size,draped_glb_url"
        ).eq("garment_id", garment_id).eq("body_hash", body_hash).execute()
        for row in r.data or []:
            s = row.get("size", "").lower()
            url = row.get("draped_glb_url", "")
            if s and url:
                draped[s] = url
    except Exception:
        pass
    return draped


class TryonConfigResponse(BaseModel):
    product_id: str
    model_urls: dict[str, str]
    size_chart: dict[str, dict[str, int]]
    model_type: str = "combined"
    category: str = "tops"
    fit_type: str = "regular"
    draped_urls: Optional[dict[str, str]] = None
    has_obj: bool = False
    garment_id: Optional[str] = None
    draping_available: bool = False


@router.get("/{product_id}/tryon-config", response_model=TryonConfigResponse)
async def get_tryon_config(
    product_id: str,
    shop: Optional[str] = Query(None, description="Shopify shop domain"),
    user_id: Optional[str] = Query(None, description="User ID for draped mesh lookup"),
    base_url: Optional[str] = Query(None, description="Base URL for relative paths"),
):
    """
    Get tryon config for a product: model URLs per size, size chart.
    When user_id is provided, also checks for cached draped meshes.
    """
    from app.config import get_settings
    settings = get_settings()
    storage_base = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/public"

    try:
        brand = supabase_service.get_brand_by_shopify_domain(shop) if shop and shop.strip() else None
        brand_id = str(brand["id"]) if brand and brand.get("id") else None

        row = _find_garment_row(product_id, brand_id)
        if not row:
            raise HTTPException(status_code=404, detail="Garment not found")

        garment_id = str(row.get("id") or "")
        sizes = row.get("sizes") or {}
        size_chart = row.get("size_chart") or {}
        obj_sizes = row.get("obj_sizes") or {}

        model_urls = {}
        for k, v in sizes.items():
            key = str(k).lower()
            url = str(v) if v else ""
            if url and not url.startswith("http"):
                url = f"{storage_base}/{url.lstrip('/')}"
            model_urls[key] = url

        if not model_urls:
            raise HTTPException(status_code=404, detail="No model URLs for this garment")

        size_chart_out = {}
        for k, v in (size_chart or {}).items():
            if isinstance(v, dict):
                size_chart_out[str(k).lower()] = {kk: int(vv) for kk, vv in v.items() if vv is not None}

        has_obj = bool(obj_sizes and any(obj_sizes.values()))
        draped_urls: Optional[dict[str, str]] = None

        if user_id and garment_id and has_obj:
            body_hash = _body_hash_from_user(user_id)
            if body_hash:
                draped_urls = _get_draped_urls(garment_id, body_hash, list(model_urls.keys()))
                if not draped_urls:
                    draped_urls = None

        return TryonConfigResponse(
            product_id=product_id,
            model_urls=model_urls,
            size_chart=size_chart_out or {"m": {"chest": 100, "waist": 84, "hips": 98}},
            model_type=str(row.get("model_type") or "garment_only"),
            category=str(row.get("category") or "tops"),
            fit_type=str(row.get("fit_type") or "regular"),
            draped_urls=draped_urls,
            has_obj=has_obj,
            garment_id=garment_id,
            draping_available=has_obj,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
