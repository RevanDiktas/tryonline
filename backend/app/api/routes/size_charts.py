"""
Category size charts for a brand — one chart per category or per Shopify product type,
used by the size finder for every product that has no 3D garment chart of its own.

Brand (JWT):
- GET    /api/size-charts            -- list the brand's category charts
- POST   /api/size-charts            -- create
- PUT    /api/size-charts/{id}       -- update
- DELETE /api/size-charts/{id}       -- delete

Public (storefront widget, MCP):
- GET /api/size-charts/resolve?shop=&product_id=&product_type=&title=
    -> {size_chart, category, fit_type, source: garment|product_type|category|none}
"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import get_current_user_id
from app.api.routes.garments import VALID_CATEGORIES, VALID_FIT_TYPES, _get_user_brand_id
from app.api.routes.products import _find_garment_row, _norm_pid
from app.services.supabase import SupabaseService

router = APIRouter()
supabase = SupabaseService()

# Same keyword lists as frontend/public/size-estimator.js inferCategory, so the server
# and the widget agree on the fallback category.
_CATEGORY_WORDS: dict[str, list[str]] = {
    "bottoms": ["pant", "trouser", "jean", "denim", "short", "skirt", "legging", "jogger", "chino", "broek", "rok", "hose", "pantalon", "jupe"],
    "outerwear": ["jacket", "coat", "parka", "blazer", "puffer", "bomber", "trench", "gilet", "vest", "jas", "mantel", "manteau", "veste", "windbreaker", "anorak"],
    "dresses": ["dress", "gown", "jurk", "kleid", "robe", "jumpsuit", "playsuit"],
    "accessories": ["hat", "cap", "beanie", "scarf", "belt", "bag", "sock", "glove", "pet", "muts", "sjaal", "riem", "tas", "sok"],
    "tops": ["shirt", "tee", "top", "hoodie", "sweater", "sweat", "jumper", "knit", "cardigan", "polo", "blouse", "crew", "longsleeve", "trui", "pullover"],
}


def infer_category(product_type: Optional[str], title: Optional[str]) -> str:
    text = f"{product_type or ''} {title or ''}".lower()
    for cat in ("bottoms", "outerwear", "dresses", "accessories", "tops"):
        if any(w in text for w in _CATEGORY_WORDS[cat]):
            return cat
    return "tops"


def _norm_chart(chart: Any) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    if not isinstance(chart, dict):
        return out
    for size, meas in chart.items():
        if not isinstance(meas, dict):
            continue
        row: dict[str, float] = {}
        for k, v in meas.items():
            try:
                row[str(k).strip().lower()] = float(v)
            except (TypeError, ValueError):
                continue
        if row:
            out[str(size).strip().lower()] = row
    return out


def _norm_types(types: Any) -> list[str]:
    if not isinstance(types, list):
        return []
    seen: list[str] = []
    for t in types:
        s = str(t or "").strip().lower()
        if s and s not in seen:
            seen.append(s)
    return seen


class ChartCreate(BaseModel):
    name: str
    category: str
    product_types: list[str] = []
    fit_type: str = "regular"
    size_chart: dict = {}


class ChartUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    product_types: Optional[list[str]] = None
    fit_type: Optional[str] = None
    size_chart: Optional[dict] = None
    is_active: Optional[bool] = None


def _validate(category: Optional[str], fit_type: Optional[str]) -> None:
    if category is not None and category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"category must be one of {VALID_CATEGORIES}")
    if fit_type is not None and fit_type not in VALID_FIT_TYPES:
        raise HTTPException(status_code=400, detail=f"fit_type must be one of {VALID_FIT_TYPES}")


def _own(chart_id: str, brand_id: str) -> dict:
    r = supabase.client.table("brand_size_charts").select("*").eq("id", chart_id).limit(1).execute()
    if not r.data:
        raise HTTPException(status_code=404, detail="Size chart not found")
    row = r.data[0]
    if str(row.get("brand_id")) != brand_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return row


# ───────────────────────── brand CRUD ─────────────────────────

@router.get("")
async def list_charts(user_id: str = Depends(get_current_user_id)):
    brand_id = _get_user_brand_id(user_id)
    try:
        r = (supabase.client.table("brand_size_charts").select("*")
             .eq("brand_id", brand_id).order("created_at").execute())
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Size charts not available yet: {e}")
    return r.data or []


@router.post("")
async def create_chart(body: ChartCreate, user_id: str = Depends(get_current_user_id)):
    brand_id = _get_user_brand_id(user_id)
    _validate(body.category, body.fit_type)
    row = {
        "brand_id": brand_id,
        "name": body.name.strip() or body.category,
        "category": body.category,
        "product_types": _norm_types(body.product_types),
        "fit_type": body.fit_type,
        "size_chart": _norm_chart(body.size_chart),
    }
    r = supabase.client.table("brand_size_charts").insert(row).execute()
    if not r.data:
        raise HTTPException(status_code=500, detail="Could not create size chart")
    return r.data[0]


@router.put("/{chart_id}")
async def update_chart(chart_id: str, body: ChartUpdate, user_id: str = Depends(get_current_user_id)):
    brand_id = _get_user_brand_id(user_id)
    _own(chart_id, brand_id)
    _validate(body.category, body.fit_type)
    patch: dict[str, Any] = {"updated_at": "now()"}
    if body.name is not None:
        patch["name"] = body.name.strip()
    if body.category is not None:
        patch["category"] = body.category
    if body.product_types is not None:
        patch["product_types"] = _norm_types(body.product_types)
    if body.fit_type is not None:
        patch["fit_type"] = body.fit_type
    if body.size_chart is not None:
        patch["size_chart"] = _norm_chart(body.size_chart)
    if body.is_active is not None:
        patch["is_active"] = body.is_active
    r = supabase.client.table("brand_size_charts").update(patch).eq("id", chart_id).execute()
    if not r.data:
        raise HTTPException(status_code=500, detail="Could not update size chart")
    return r.data[0]


@router.delete("/{chart_id}")
async def delete_chart(chart_id: str, user_id: str = Depends(get_current_user_id)):
    brand_id = _get_user_brand_id(user_id)
    _own(chart_id, brand_id)
    supabase.client.table("brand_size_charts").delete().eq("id", chart_id).execute()
    return {"ok": True}


# ───────────────────────── public resolve ─────────────────────────

class ResolveResponse(BaseModel):
    size_chart: dict[str, dict[str, float]] = {}
    category: str = "tops"
    fit_type: str = "regular"
    source: str = "none"          # garment | product_type | category | none
    chart_name: Optional[str] = None


@router.get("/resolve", response_model=ResolveResponse)
async def resolve_chart(
    shop: str = Query(..., description="Shopify shop domain"),
    product_id: Optional[str] = Query(None, description="Product handle or id"),
    product_type: Optional[str] = Query(None),
    title: Optional[str] = Query(None),
):
    """Which size chart applies to this product. Garment chart first, then the brand's
    chart for the Shopify product type, then the brand's chart for the category."""
    brand = supabase.get_brand_by_shopify_domain(shop)
    inferred = infer_category(product_type, title)
    if not brand:
        return ResolveResponse(category=inferred)
    brand_id = str(brand["id"])

    # 1. The product's own garment (3D) chart.
    if product_id:
        g = _find_garment_row(product_id, brand_id)
        if g:
            chart = _norm_chart(g.get("size_chart"))
            if chart:
                return ResolveResponse(
                    size_chart=chart,
                    category=g.get("category") or inferred,
                    fit_type=g.get("fit_type") or "regular",
                    source="garment",
                    chart_name=g.get("name"),
                )

    try:
        r = (supabase.client.table("brand_size_charts").select("*")
             .eq("brand_id", brand_id).eq("is_active", True).execute())
        rows = [x for x in (r.data or []) if _norm_chart(x.get("size_chart"))]
    except Exception as e:  # table not migrated yet: behave as before (no chart)
        print(f"[size_charts] resolve: {e}")
        rows = []

    # 2. Exact Shopify product type.
    pt = _norm_pid(product_type)
    if pt:
        for x in rows:
            if pt in _norm_types(x.get("product_types")):
                return ResolveResponse(size_chart=_norm_chart(x["size_chart"]), category=x["category"],
                                       fit_type=x.get("fit_type") or "regular", source="product_type",
                                       chart_name=x.get("name"))

    # 3. Category default: the chart for this category with no product types, else any for it.
    cands = [x for x in rows if x.get("category") == inferred]
    cands.sort(key=lambda x: (len(_norm_types(x.get("product_types"))), str(x.get("created_at"))))
    if cands:
        x = cands[0]
        return ResolveResponse(size_chart=_norm_chart(x["size_chart"]), category=x["category"],
                               fit_type=x.get("fit_type") or "regular", source="category",
                               chart_name=x.get("name"))

    return ResolveResponse(category=inferred)
