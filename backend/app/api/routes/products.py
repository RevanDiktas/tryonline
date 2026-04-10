"""
Product / garment tryon config — model URLs, size chart
"""
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.supabase import supabase_service

router = APIRouter()

# Theme Liquid passes product.handle (e.g. rs-zip-up). Brands may store it in either column.
_GARMENT_SELECT_FULL = "sizes,size_chart,shopify_product_id,shopify_product_handle"
_GARMENT_SELECT_FALLBACK = "sizes,size_chart,shopify_product_id"
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
    # Scoped: scan brand's garments (small); matches handle OR id, any casing.
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
    # Exact column match (unscoped or second chance) — fresh builder each iteration
    for field in ("shopify_product_id", "shopify_product_handle"):
        try:
            q = supabase_service.client.table("garments").select("sizes,size_chart")
            if brand_id:
                q = q.eq("brand_id", brand_id)
            r = q.eq(field, product_id).limit(1).execute()
            if r.data:
                return r.data[0]
        except Exception:
            continue
    return None

class TryonConfigResponse(BaseModel):
    product_id: str
    model_urls: dict[str, str]
    size_chart: dict[str, dict[str, int]]
    model_type: str = "combined"  # "combined" (avatar+garment in one) | "garment_only"


@router.get("/{product_id}/tryon-config", response_model=TryonConfigResponse)
async def get_tryon_config(
    product_id: str,
    shop: Optional[str] = Query(
        None,
        description="Shopify shop domain (e.g. raminstudios.myshopify.com) — required to pick the correct brand when handles collide",
    ),
    base_url: Optional[str] = Query(None, description="Base URL for relative paths"),
):
    """
    Get tryon config for a product: model URLs per size, size chart.
    Resolves relative storage paths to full Supabase URLs.
    When ``shop`` is provided, the garment row is scoped to that shop's brand so the
    same product handle on another store cannot steal the wrong GLBs.
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
        sizes = row.get("sizes") or {}
        size_chart = row.get("size_chart") or {}

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

        return TryonConfigResponse(
            product_id=product_id,
            model_urls=model_urls,
            size_chart=size_chart_out or {"m": {"chest": 100, "waist": 84, "hips": 98}},
            model_type=str(row.get("model_type") or "garment_only"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
