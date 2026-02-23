"""
Product / garment tryon config — model URLs, size chart
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.supabase import supabase_service

router = APIRouter()

class TryonConfigResponse(BaseModel):
    product_id: str
    model_urls: dict[str, str]
    size_chart: dict[str, dict[str, int]]
    model_type: str = "combined"  # "combined" (avatar+garment in one) | "garment_only"


@router.get("/{product_id}/tryon-config", response_model=TryonConfigResponse)
async def get_tryon_config(
    product_id: str,
    base_url: Optional[str] = Query(None, description="Base URL for relative paths"),
):
    """
    Get tryon config for a product: model URLs per size, size chart.
    Resolves relative storage paths to full Supabase URLs.
    """
    from app.config import get_settings
    settings = get_settings()
    storage_base = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/public"

    try:
        r = supabase_service.client.table("garments").select("sizes,size_chart").eq(
            "shopify_product_id", product_id
        ).limit(1).execute()

        if not r.data or len(r.data) == 0:
            raise HTTPException(status_code=404, detail="Garment not found")

        row = r.data[0]
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
