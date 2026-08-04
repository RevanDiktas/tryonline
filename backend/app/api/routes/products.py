"""
Product / garment tryon config — model URLs, size chart, draped mesh integration
"""
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.supabase import supabase_service

router = APIRouter()

_GARMENT_BASE_COLS = "id,name,sizes,size_chart,category,fit_type,obj_sizes,shopify_product_id"
# Columns that only exist on newer schemas. Probed once each, then memoised, so
# the read path keeps working against a DB where a migration hasn't run yet.
_OPTIONAL_GARMENT_COLS = ("shopify_product_handle", "companion_garment_id")
_HAS_COLUMN: dict[str, bool] = {}


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


def _has_garment_column(column: str) -> bool:
    """Does `garments` have this column? Probed once, then memoised — a missing
    column must degrade the response, never 500 the whole PDP."""
    if column in _HAS_COLUMN:
        return _HAS_COLUMN[column]
    try:
        supabase_service.client.table("garments").select(column).limit(1).execute()
        _HAS_COLUMN[column] = True
    except Exception:
        _HAS_COLUMN[column] = False
    return _HAS_COLUMN[column]


def _garment_select_columns() -> str:
    """Base columns plus whichever optional ones this schema actually has."""
    cols = [_GARMENT_BASE_COLS]
    cols.extend(c for c in _OPTIONAL_GARMENT_COLS if _has_garment_column(c))
    return ",".join(cols)


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


def _build_garment_meshes(
    row: dict[str, Any],
    storage_base: str,
    body_hash: Optional[str],
) -> tuple[dict[str, str], dict[str, dict[str, float]], bool, Optional[dict[str, str]]]:
    """Resolve one garment row into (model_urls, size_chart, has_obj, draped_urls).

    Shared by the primary garment and its companion so both sides of an outfit
    go through identical URL resolution and cache lookup — the companion is not
    a second, subtly different code path.
    """
    model_urls: dict[str, str] = {}
    for k, v in (row.get("sizes") or {}).items():
        url = str(v) if v else ""
        if url and not url.startswith("http"):
            url = f"{storage_base}/{url.lstrip('/')}"
        model_urls[str(k).lower()] = url

    size_chart_out: dict[str, dict[str, float]] = {}
    for k, v in (row.get("size_chart") or {}).items():
        if isinstance(v, dict):
            # Keep measurements as floats — merchant charts use decimals (e.g. 33.5 cm).
            # int() truncated half-cm values, throwing the size match off.
            clean: dict[str, float] = {}
            for kk, vv in v.items():
                if vv is None:
                    continue
                try:
                    clean[str(kk).lower()] = float(vv)
                except (TypeError, ValueError):
                    continue
            size_chart_out[str(k).lower()] = clean

    obj_sizes = row.get("obj_sizes") or {}
    has_obj = bool(obj_sizes and any(obj_sizes.values()))

    draped_urls: Optional[dict[str, str]] = None
    garment_id = str(row.get("id") or "")
    if body_hash and garment_id and has_obj:
        draped_urls = _get_draped_urls(garment_id, body_hash, list(model_urls.keys())) or None

    return model_urls, size_chart_out, has_obj, draped_urls


class CompanionConfig(BaseModel):
    """The other half of the outfit. Same shape as the primary garment so the
    viewer can render it through the same path — it just never owns the size
    selector."""
    garment_id: str
    name: Optional[str] = None
    product_handle: Optional[str] = None
    category: str = "bottoms"
    fit_type: str = "regular"
    model_urls: dict[str, str]
    size_chart: dict[str, dict[str, float]] = {}
    draped_urls: Optional[dict[str, str]] = None


class TryonConfigResponse(BaseModel):
    product_id: str
    model_urls: dict[str, str]
    size_chart: dict[str, dict[str, float]]  # cm, decimals allowed (e.g. 33.5)
    model_type: str = "combined"
    category: str = "tops"
    fit_type: str = "regular"
    draped_urls: Optional[dict[str, str]] = None
    has_obj: bool = False
    garment_id: Optional[str] = None
    draping_available: bool = False
    companion: Optional[CompanionConfig] = None


def _resolve_companion(
    row: dict[str, Any],
    storage_base: str,
    body_hash: Optional[str],
) -> Optional[CompanionConfig]:
    """Load the paired garment so the avatar is never half-dressed.

    Fails soft on purpose: a missing, deleted or mesh-less companion returns
    None and the PDP renders the primary alone. A broken pairing must never
    take down the product page it is attached to.
    """
    companion_id = row.get("companion_garment_id")
    if not companion_id:
        return None
    try:
        r = (
            supabase_service.client.table("garments")
            .select(_garment_select_columns())
            .eq("id", str(companion_id))
            .limit(1)
            .execute()
        )
        if not r.data:
            print(f"[products] companion {companion_id} not found for garment {row.get('id')}")
            return None
        crow = r.data[0]
        model_urls, size_chart, _has_obj, draped_urls = _build_garment_meshes(
            crow, storage_base, body_hash
        )
        if not model_urls:
            print(f"[products] companion {companion_id} has no model URLs — skipping")
            return None
        return CompanionConfig(
            garment_id=str(crow.get("id") or ""),
            name=crow.get("name"),
            product_handle=(crow.get("shopify_product_handle")
                            or crow.get("shopify_product_id")),
            category=str(crow.get("category") or "bottoms"),
            fit_type=str(crow.get("fit_type") or "regular"),
            model_urls=model_urls,
            size_chart=size_chart,
            draped_urls=draped_urls,
        )
    except Exception as e:
        print(f"[products] companion resolve failed for {companion_id}: {e}")
        return None


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

        # One passport lookup, shared by both halves of the outfit.
        body_hash = _body_hash_from_user(user_id) if user_id else None

        model_urls, size_chart_out, has_obj, draped_urls = _build_garment_meshes(
            row, storage_base, body_hash
        )

        if not model_urls:
            raise HTTPException(status_code=404, detail="No model URLs for this garment")

        companion = _resolve_companion(row, storage_base, body_hash)

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
            companion=companion,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
