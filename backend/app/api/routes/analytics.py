"""
Category A & B & C analytics API — ROI, Attribution, Fit Accuracy, Trend & Demand.

Heavy aggregation is delegated to Postgres RPC functions (analytics_*).
All responses are cached for 60 seconds via TTLCache.
Exploration-trend and size-stress remain Python-side (complex JSONB logic).
"""
import hashlib
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from cachetools import TTLCache
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.supabase import supabase_service

logger = logging.getLogger(__name__)
router = APIRouter()

ATTRIBUTION_WINDOW_DAYS = 30

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
_cache: TTLCache = TTLCache(maxsize=256, ttl=60)


def _cache_key(prefix: str, **kwargs: Any) -> str:
    raw = json.dumps({"_": prefix, **kwargs}, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date_range(
    start: str | None, end: str | None, default_days: int = 30
) -> tuple[str, str]:
    """Return (start_iso, end_iso) timestamps for Postgres timestamptz params."""
    if not start:
        end_d = datetime.now(timezone.utc).date()
        start_d = end_d - timedelta(days=default_days)
    else:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
        end_d = (
            datetime.strptime(end, "%Y-%m-%d").date() if end else start_d
        )
    start_ts = (
        datetime.combine(start_d, datetime.min.time())
        .replace(tzinfo=timezone.utc)
        .isoformat()
    )
    end_ts = (
        datetime.combine(end_d, datetime.max.time())
        .replace(tzinfo=timezone.utc)
        .isoformat()
    )
    return start_ts, end_ts


def _call_rpc(fn_name: str, params: dict) -> Any:
    """Call a Supabase Postgres function and return the parsed result."""
    try:
        response = supabase_service.client.rpc(fn_name, params).execute()
        return response.data
    except Exception as exc:
        msg = str(exc).lower()
        if "does not exist" in msg or "could not find" in msg:
            raise HTTPException(
                status_code=503,
                detail=(
                    f"RPC function '{fn_name}' not found. "
                    "Run docs/migrations/analytics_rpc_functions.sql in the Supabase SQL Editor first."
                ),
            )
        raise


# ---------------------------------------------------------------------------
# Debug (unchanged — lightweight, no RPC needed)
# ---------------------------------------------------------------------------

@router.get("/debug")
async def analytics_debug(
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
):
    from app.config import get_settings

    if not get_settings().debug:
        raise HTTPException(status_code=404, detail="Not found")

    start_ts, _ = _parse_date_range(start, end)
    _, end_ts_raw = _parse_date_range(start, end)
    end_d = datetime.fromisoformat(end_ts_raw).date() if end else datetime.now(timezone.utc).date()
    end_extended = end_d + timedelta(days=ATTRIBUTION_WINDOW_DAYS)
    end_ts_extended = (
        datetime.combine(end_extended, datetime.max.time())
        .replace(tzinfo=timezone.utc)
        .isoformat()
    )

    q = (
        supabase_service.client.table("analytics_events")
        .select("event_type,session_id,shop_domain,created_at")
        .gte("created_at", start_ts)
        .lte("created_at", end_ts_extended)
    )
    if shop:
        q = q.eq("shop_domain", shop)

    try:
        r = q.execute()
        events = r.data or []
        by_type: dict[str, int] = defaultdict(int)
        for e in events:
            by_type[e.get("event_type", "?")] += 1
        sample = events[0] if events else None
        return {
            "ok": True,
            "raw_event_count": len(events),
            "event_types": dict(by_type),
            "date_range": {"start": start_ts, "end_extended": end_ts_extended},
            "shop_filter": shop,
            "sample_event": sample,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Pydantic response models (identical to previous — no frontend changes)
# ---------------------------------------------------------------------------

class MetricsResponse(BaseModel):
    tryons_started: int
    add_to_carts: int
    purchases: int
    tryon_atc_rate: Optional[float] = None
    tryon_purchase_rate: Optional[float] = None
    revenue_attributed: float
    revenue_per_tryon: Optional[float] = None
    aov_tryon: Optional[float] = None
    unique_sessions: int


class ProductMetrics(BaseModel):
    product_id: str
    tryons_started: int
    add_to_carts: int
    purchases: int
    revenue_attributed: float
    tryon_atc_rate: Optional[float] = None
    tryon_purchase_rate: Optional[float] = None
    revenue_per_tryon: Optional[float] = None
    aov_tryon: Optional[float] = None


class MetricsByProductResponse(BaseModel):
    products: list[ProductMetrics]
    attribution_window_days: int = ATTRIBUTION_WINDOW_DAYS


class FitMetricsResponse(BaseModel):
    size_distribution_recommended: dict[str, int]
    size_distribution_selected: dict[str, int]
    size_distribution_purchased: dict[str, int]
    acceptance_rate: Optional[float] = None
    size_up_rate: Optional[float] = None
    size_down_rate: Optional[float] = None
    mase: Optional[float] = None
    sessions_with_recommendation: int
    sessions_with_purchase_and_size: int


class VelocityResponse(BaseModel):
    tryon_velocity_7d: int
    tryon_velocity_30d: int
    purchase_velocity_7d: int
    purchase_velocity_30d: int
    tryon_sessions_7d: int
    purchase_sessions_7d: int
    velocity_ratio_7d: Optional[float] = None
    velocity_ratio_30d: Optional[float] = None


class AtRiskProduct(BaseModel):
    product_id: str
    tryons: int
    purchases: int
    conversion: Optional[float] = None
    ratio: Optional[float] = None
    severity: str


class AtRiskProductsResponse(BaseModel):
    products: list[AtRiskProduct]
    min_tryons: int
    conversion_threshold: float


class ExplorationTrendPoint(BaseModel):
    week_start: str
    avg_sizes_per_session: float
    sessions_count: int
    total_size_events: int


class ExplorationTrendResponse(BaseModel):
    data: list[ExplorationTrendPoint]


class SizeStressItem(BaseModel):
    product_id: str
    size: str
    views: int
    purchases: int
    conversion: Optional[float] = None
    stress_score: float


class SizeStressResponse(BaseModel):
    items: list[SizeStressItem]
    min_views: int
    views_to_purchases_ratio_threshold: float


class RegionalSizePoint(BaseModel):
    country: str
    size: str
    count: int
    pct: float


class CitySizeData(BaseModel):
    sizes: dict[str, float] = {}
    raw_counts: dict[str, int] = {}
    total: int = 0
    top_size: str = ""


class RegionalSizeResponse(BaseModel):
    by_country: dict[str, dict[str, float]]
    raw_counts: dict[str, dict[str, int]]
    top_size_by_country: dict[str, str] = {}
    by_city: dict[str, dict[str, CitySizeData]] = {}


# ---------------------------------------------------------------------------
# 1. /metrics  (RPC: analytics_metrics)
# ---------------------------------------------------------------------------

@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    brand_id: Optional[str] = Query(None, description="Filter by brand_id"),
):
    key = _cache_key("metrics", start=start, end=end, shop=shop, brand_id=brand_id)
    if key in _cache:
        return _cache[key]

    start_ts, end_ts = _parse_date_range(start, end)
    data = _call_rpc("analytics_metrics", {
        "p_start": start_ts,
        "p_end": end_ts,
        "p_shop": shop,
        "p_brand_id": brand_id,
    })

    if not data or not isinstance(data, dict):
        data = {}

    result = MetricsResponse(
        tryons_started=data.get("tryons_started", 0),
        add_to_carts=data.get("add_to_carts", 0),
        purchases=data.get("purchases", 0),
        tryon_atc_rate=data.get("tryon_atc_rate"),
        tryon_purchase_rate=data.get("tryon_purchase_rate"),
        revenue_attributed=data.get("revenue_attributed", 0.0),
        revenue_per_tryon=data.get("revenue_per_tryon"),
        aov_tryon=data.get("aov_tryon"),
        unique_sessions=data.get("unique_sessions", 0),
    )
    _cache[key] = result
    return result


# ---------------------------------------------------------------------------
# 2. /metrics-by-product  (RPC: analytics_metrics_by_product)
# ---------------------------------------------------------------------------

@router.get("/metrics-by-product", response_model=MetricsByProductResponse)
async def get_metrics_by_product(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    brand_id: Optional[str] = Query(None, description="Filter by brand_id"),
    product_id: Optional[str] = Query(None, description="Filter to single product_id"),
):
    key = _cache_key("metrics_by_product", start=start, end=end, shop=shop, brand_id=brand_id, product_id=product_id)
    if key in _cache:
        return _cache[key]

    start_ts, end_ts = _parse_date_range(start, end)
    rows = _call_rpc("analytics_metrics_by_product", {
        "p_start": start_ts,
        "p_end": end_ts,
        "p_shop": shop,
        "p_brand_id": brand_id,
        "p_product_id": product_id,
    })

    if not rows or not isinstance(rows, list):
        rows = []

    products = [
        ProductMetrics(
            product_id=r.get("product_id", ""),
            tryons_started=r.get("tryons_started", 0),
            add_to_carts=r.get("add_to_carts", 0),
            purchases=r.get("purchases", 0),
            revenue_attributed=r.get("revenue_attributed", 0.0),
            tryon_atc_rate=r.get("tryon_atc_rate"),
            tryon_purchase_rate=r.get("tryon_purchase_rate"),
            revenue_per_tryon=r.get("revenue_per_tryon"),
            aov_tryon=r.get("aov_tryon"),
        )
        for r in rows
    ]

    result = MetricsByProductResponse(
        products=products,
        attribution_window_days=ATTRIBUTION_WINDOW_DAYS,
    )
    _cache[key] = result
    return result


# ---------------------------------------------------------------------------
# 3. /fit-metrics  (RPC: analytics_fit_metrics)
# ---------------------------------------------------------------------------

@router.get("/fit-metrics", response_model=FitMetricsResponse)
async def get_fit_metrics(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    brand_id: Optional[str] = Query(None, description="Filter by brand_id"),
):
    key = _cache_key("fit_metrics", start=start, end=end, shop=shop, brand_id=brand_id)
    if key in _cache:
        return _cache[key]

    start_ts, end_ts = _parse_date_range(start, end)
    data = _call_rpc("analytics_fit_metrics", {
        "p_start": start_ts,
        "p_end": end_ts,
        "p_shop": shop,
        "p_brand_id": brand_id,
    })

    if not data or not isinstance(data, dict):
        data = {}

    def _int_dict(d: Any) -> dict[str, int]:
        if not isinstance(d, dict):
            return {}
        return {str(k): int(v) for k, v in d.items()}

    result = FitMetricsResponse(
        size_distribution_recommended=_int_dict(data.get("size_distribution_recommended")),
        size_distribution_selected=_int_dict(data.get("size_distribution_selected")),
        size_distribution_purchased=_int_dict(data.get("size_distribution_purchased")),
        acceptance_rate=data.get("acceptance_rate"),
        size_up_rate=data.get("size_up_rate"),
        size_down_rate=data.get("size_down_rate"),
        mase=data.get("mase"),
        sessions_with_recommendation=data.get("sessions_with_recommendation", 0),
        sessions_with_purchase_and_size=data.get("sessions_with_purchase_and_size", 0),
    )
    _cache[key] = result
    return result


# ---------------------------------------------------------------------------
# 4. /velocity  (RPC: analytics_velocity)
# ---------------------------------------------------------------------------

@router.get("/velocity", response_model=VelocityResponse)
async def get_velocity(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
):
    key = _cache_key("velocity", start=start, end=end, shop=shop)
    if key in _cache:
        return _cache[key]

    start_ts, end_ts = _parse_date_range(start, end)
    data = _call_rpc("analytics_velocity", {
        "p_start": start_ts,
        "p_end": end_ts,
        "p_shop": shop,
    })

    if not data or not isinstance(data, dict):
        data = {}

    result = VelocityResponse(
        tryon_velocity_7d=data.get("tryon_velocity_7d", 0),
        tryon_velocity_30d=data.get("tryon_velocity_30d", 0),
        purchase_velocity_7d=data.get("purchase_velocity_7d", 0),
        purchase_velocity_30d=data.get("purchase_velocity_30d", 0),
        tryon_sessions_7d=data.get("tryon_sessions_7d", 0),
        purchase_sessions_7d=data.get("purchase_sessions_7d", 0),
        velocity_ratio_7d=data.get("velocity_ratio_7d"),
        velocity_ratio_30d=data.get("velocity_ratio_30d"),
    )
    _cache[key] = result
    return result


# ---------------------------------------------------------------------------
# 5. /at-risk-products  (RPC: analytics_at_risk)
# ---------------------------------------------------------------------------

@router.get("/at-risk-products", response_model=AtRiskProductsResponse)
async def get_at_risk_products(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    min_tryons: int = Query(5, description="Minimum tryons to consider"),
    conversion_threshold: float = Query(0.05, description="Conversion below this flags as at-risk"),
):
    key = _cache_key("at_risk", start=start, end=end, shop=shop, min_tryons=min_tryons, ct=conversion_threshold)
    if key in _cache:
        return _cache[key]

    start_ts, end_ts = _parse_date_range(start, end)
    rows = _call_rpc("analytics_at_risk", {
        "p_start": start_ts,
        "p_end": end_ts,
        "p_shop": shop,
        "p_min_tryons": min_tryons,
        "p_conversion_threshold": conversion_threshold,
    })

    if not rows or not isinstance(rows, list):
        rows = []

    products = []
    for r in rows:
        tryons = r.get("tryons", 0)
        purchases = r.get("purchases", 0)
        ratio_val = round(tryons / purchases, 2) if purchases else None
        products.append(AtRiskProduct(
            product_id=r.get("product_id", ""),
            tryons=tryons,
            purchases=purchases,
            conversion=r.get("conversion"),
            ratio=ratio_val,
            severity=r.get("severity", "watch"),
        ))

    result = AtRiskProductsResponse(
        products=products,
        min_tryons=min_tryons,
        conversion_threshold=conversion_threshold,
    )
    _cache[key] = result
    return result


# ---------------------------------------------------------------------------
# 6. /exploration-trend  (Python + cache — complex JSONB week-bucketing)
# ---------------------------------------------------------------------------

@router.get("/exploration-trend", response_model=ExplorationTrendResponse)
async def get_exploration_trend(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
):
    key = _cache_key("exploration_trend", start=start, end=end, shop=shop)
    if key in _cache:
        return _cache[key]

    start_ts, end_ts = _parse_date_range(start, end, default_days=90)

    q = (
        supabase_service.client.table("analytics_events")
        .select("event_type,session_id,created_at")
        .gte("created_at", start_ts)
        .lte("created_at", end_ts)
    )
    if shop:
        q = q.eq("shop_domain", shop)
    r = q.execute()
    events = r.data or []

    exploration_events = [
        e for e in events
        if e.get("event_type") in ("size_viewed", "size_selected") and e.get("session_id")
    ]

    week_to_sessions: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for e in exploration_events:
        created = e.get("created_at")
        if not created:
            continue
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            week_start = dt.date() - timedelta(days=dt.weekday())
            week_key = week_start.isoformat()
            sid = e.get("session_id") or ""
            week_to_sessions[week_key][sid] += 1
        except (ValueError, TypeError):
            continue

    data = []
    for week_start in sorted(week_to_sessions.keys()):
        session_counts = week_to_sessions[week_start]
        total_events = sum(session_counts.values())
        sessions_count = len(session_counts)
        avg_sizes = round(total_events / sessions_count, 2) if sessions_count else 0.0
        data.append(ExplorationTrendPoint(
            week_start=week_start,
            avg_sizes_per_session=avg_sizes,
            sessions_count=sessions_count,
            total_size_events=total_events,
        ))

    result = ExplorationTrendResponse(data=data)
    _cache[key] = result
    return result


# ---------------------------------------------------------------------------
# 7. /size-stress  (Python + cache — complex JSONB cross-reference)
# ---------------------------------------------------------------------------

@router.get("/size-stress", response_model=SizeStressResponse)
async def get_size_stress(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    min_views: int = Query(10, description="Minimum views to consider"),
    views_to_purchases_ratio: float = Query(5.0, description="Flag if views >= ratio * purchases"),
):
    key = _cache_key("size_stress", start=start, end=end, shop=shop, mv=min_views, vpr=views_to_purchases_ratio)
    if key in _cache:
        return _cache[key]

    start_ts, end_ts = _parse_date_range(start, end)

    q = (
        supabase_service.client.table("analytics_events")
        .select("event_type,product_id,session_id,event_data")
        .gte("created_at", start_ts)
        .lte("created_at", end_ts)
    )
    if shop:
        q = q.eq("shop_domain", shop)
    r = q.execute()
    events = r.data or []

    key_views_clean: dict[tuple[str, str], int] = defaultdict(int)
    key_purchases_clean: dict[tuple[str, str], int] = defaultdict(int)
    session_to_product: dict[str, str] = {}

    for e in events:
        if e.get("event_type") == "tryon_started":
            sid = e.get("session_id")
            pid = (e.get("product_id") or "").strip()
            if sid and pid:
                session_to_product[sid] = pid

    for e in events:
        pid = (e.get("product_id") or "").strip()
        ed = e.get("event_data") or {}
        etype = e.get("event_type")
        sid = e.get("session_id")

        if etype in ("size_viewed", "size_selected", "size_recommended"):
            raw = ed.get("size")
            sz = str(raw).strip() if raw is not None and raw != "" else None
            p = pid or session_to_product.get(sid or "", "")
            if p and sz:
                size_key = sz.upper() if len(sz) <= 3 else sz
                key_views_clean[(p, size_key)] += 1
        elif etype == "purchase":
            for it in (ed.get("items") or []):
                raw_sz = it.get("size")
                sz = str(raw_sz).strip() if raw_sz is not None and raw_sz != "" else None
                sid_item = it.get("session_id")
                p = pid or (session_to_product.get(sid_item or "", "") if sid_item else "")
                if p and sz:
                    size_key = sz.upper() if len(sz) <= 3 else sz
                    key_purchases_clean[(p, size_key)] += 1

    all_keys = set(key_views_clean.keys()) | set(key_purchases_clean.keys())
    items = []
    for (p_id, size) in all_keys:
        views = key_views_clean.get((p_id, size), 0)
        purchases = key_purchases_clean.get((p_id, size), 0)
        if views < min_views:
            continue
        stress = views / max(purchases, 1)
        if stress < views_to_purchases_ratio:
            continue
        conv = round(purchases / views, 4) if views else None
        items.append(SizeStressItem(
            product_id=p_id,
            size=size,
            views=views,
            purchases=purchases,
            conversion=conv,
            stress_score=round(stress, 2),
        ))

    items.sort(key=lambda x: (-x.stress_score, -x.views))

    result = SizeStressResponse(
        items=items,
        min_views=min_views,
        views_to_purchases_ratio_threshold=views_to_purchases_ratio,
    )
    _cache[key] = result
    return result


# ---------------------------------------------------------------------------
# 8. /regional-size  (RPC: analytics_regional_size)
# ---------------------------------------------------------------------------

@router.get("/regional-size", response_model=RegionalSizeResponse)
async def get_regional_size_distribution(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    brand_id: Optional[str] = Query(None, description="Filter by brand_id"),
):
    key = _cache_key("regional_size", start=start, end=end, shop=shop, brand_id=brand_id)
    if key in _cache:
        return _cache[key]

    start_ts, end_ts = _parse_date_range(start, end)
    data = _call_rpc("analytics_regional_size", {
        "p_start": start_ts,
        "p_end": end_ts,
        "p_shop": shop,
        "p_brand_id": brand_id,
    })

    if not data or not isinstance(data, dict):
        data = {}

    raw_counts = data.get("raw_counts") or {}
    by_country = data.get("by_country") or {}
    top_size_by_country = data.get("top_size_by_country") or {}

    by_city_raw = data.get("by_city") or {}
    by_city: dict[str, dict[str, CitySizeData]] = {}
    for country, cities in by_city_raw.items():
        if not isinstance(cities, dict):
            continue
        by_city[country] = {}
        for city_name, city_data in cities.items():
            if not isinstance(city_data, dict):
                continue
            by_city[country][city_name] = CitySizeData(
                sizes=city_data.get("sizes") or {},
                raw_counts=city_data.get("raw_counts") or {},
                total=city_data.get("total", 0),
                top_size=city_data.get("top_size", ""),
            )

    result = RegionalSizeResponse(
        by_country=by_country,
        raw_counts=raw_counts,
        top_size_by_country=top_size_by_country,
        by_city=by_city,
    )
    _cache[key] = result
    return result
