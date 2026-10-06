"""
Product / garment tryon config — model URLs, size chart, draped mesh integration
"""
import time
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.supabase import supabase_service

router = APIRouter()

_GARMENT_BASE_COLS = "id,name,sizes,size_chart,category,fit_type,obj_sizes,shopify_product_id"
# Columns that only exist on newer schemas. Probed once each, then memoised, so
# the read path keeps working against a DB where a migration hasn't run yet.
_OPTIONAL_GARMENT_COLS = ("shopify_product_handle", "companion_garment_id")
_HAS_COLUMN: dict[str, bool] = {}

# shop -> (monotonic expiry, handles). In-process only; each worker warms its own.
_TRYON_HANDLES_TTL_S = 60.0
_TRYON_HANDLES_CACHE: dict[str, tuple[float, list[str]]] = {}


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


def _body_lookup_hashes(user_id: str) -> Optional[list[str]]:
    """Draped-mesh read keys for this user's current avatar, preferred first: the
    avatar-based hash, then the legacy measurement hash while rows are migrated.
    Measurement edits don't change the preferred one (see body_clustering)."""
    from app.services.body_clustering import body_identity_for_user
    ident = body_identity_for_user(user_id)
    return ident.lookup_hashes if ident and ident.body_hash else None


def _get_draped_urls(garment_id: str, body_hashes: list[str], sizes: list[str]) -> dict[str, str]:
    """Check draped_meshes cache for all sizes of this garment+body. Per size, the row
    under the most preferred body hash wins."""
    from app.services.body_clustering import pick_by_hash_preference
    draped = {}
    try:
        r = supabase_service.client.table("draped_meshes").select(
            "size,body_hash,draped_glb_url"
        ).eq("garment_id", garment_id).in_("body_hash", body_hashes).execute()
        rows = [
            {**row, "size": (row.get("size") or "").lower()}
            for row in (r.data or []) if row.get("size") and row.get("draped_glb_url")
        ]
        for s, row in pick_by_hash_preference(rows, body_hashes).items():
            draped[s] = row["draped_glb_url"]
    except Exception:
        pass
    return draped


def _build_garment_meshes(
    row: dict[str, Any],
    storage_base: str,
    body_hashes: Optional[list[str]],
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
    if body_hashes and garment_id and has_obj:
        draped_urls = _get_draped_urls(garment_id, body_hashes, list(model_urls.keys())) or None

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
    body_hashes: Optional[list[str]],
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
            crow, storage_base, body_hashes
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


def _has_model_url(row: dict[str, Any]) -> bool:
    """Would tryon-config hand the viewer something to load? Same source as
    _build_garment_meshes' model_urls (garments.sizes), minus the draping lookups."""
    sizes = row.get("sizes")
    if not isinstance(sizes, dict):
        return False
    return any(str(v).strip() for v in sizes.values() if v)


def _tryon_handles_for_brand(brand_id: str) -> list[str]:
    """Every product id/handle in this brand that resolves to a 3D garment."""
    cols = "sizes,shopify_product_id"
    if _has_garment_column("shopify_product_handle"):
        cols += ",shopify_product_handle"
    r = (
        supabase_service.client.table("garments")
        .select(cols)
        .eq("brand_id", brand_id)
        .execute()
    )
    handles: list[str] = []
    seen: set[str] = set()
    for row in r.data or []:
        if not _has_model_url(row):
            continue
        for key in ("shopify_product_handle", "shopify_product_id"):
            h = _norm_pid(row.get(key))
            if h and h not in seen:
                seen.add(h)
                handles.append(h)
    return handles


class TryonHandlesResponse(BaseModel):
    shop: str = ""
    handles: list[str] = []


@router.get("/tryon-handles", response_model=TryonHandlesResponse)
async def get_tryon_handles(
    response: Response,
    shop: Optional[str] = Query(None, description="Shopify shop domain"),
):
    """
    Which products in this shop have a 3D garment, so the PDP block can pick
    "Try On" vs "Find my size" on page load without a per-product tryon-config
    round trip. Unknown or missing shop is an empty list, never an error.
    """
    # Storefront origins (e.g. www.lafamamsterdam.com) aren't in CORS_ORIGINS. This is a
    # credential-less public GET, so open it here rather than widening global CORS.
    response.headers["Access-Control-Allow-Origin"] = "*"
    shop_key = _norm_pid(shop)
    if not shop_key:
        response.headers["Cache-Control"] = "public, max-age=60"
        return TryonHandlesResponse(shop="", handles=[])

    now = time.monotonic()
    hit = _TRYON_HANDLES_CACHE.get(shop_key)
    if hit and hit[0] > now:
        response.headers["Cache-Control"] = "public, max-age=60"
        return TryonHandlesResponse(shop=shop_key, handles=hit[1])

    try:
        brand = supabase_service.get_brand_by_shopify_domain(shop_key)
        brand_id = str(brand["id"]) if brand and brand.get("id") else None
        handles = _tryon_handles_for_brand(brand_id) if brand_id else []
    except Exception as e:
        # A failure is an error, not an empty list: the block would cache [] and show
        # "Find my size" on 3D products. On an error it retries, then keeps Try On.
        print(f"[products] tryon-handles failed for {shop_key}: {e}")
        return JSONResponse(
            status_code=503,
            content={"detail": "Try-on product list unavailable"},
            headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "no-store"},
        )

    _TRYON_HANDLES_CACHE[shop_key] = (now + _TRYON_HANDLES_TTL_S, handles)
    response.headers["Cache-Control"] = "public, max-age=60"
    return TryonHandlesResponse(shop=shop_key, handles=handles)


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
        body_hashes = _body_lookup_hashes(user_id) if user_id else None

        model_urls, size_chart_out, has_obj, draped_urls = _build_garment_meshes(
            row, storage_base, body_hashes
        )

        if not model_urls:
            raise HTTPException(status_code=404, detail="No model URLs for this garment")

        companion = _resolve_companion(row, storage_base, body_hashes)

        return TryonConfigResponse(
            product_id=product_id,
            model_urls=model_urls,
            # No chart is no chart: a stand-in made every chart-based fit score wrong.
            size_chart=size_chart_out or {},
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
