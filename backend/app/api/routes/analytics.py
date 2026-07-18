"""
Category A & B analytics API — ROI, Attribution, Fit Accuracy.

Uses direct Supabase table queries with Python aggregation.
Results are cached for 60 seconds via TTLCache to avoid repeated full scans.
"""
import hashlib
import json
import logging
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from cachetools import TTLCache
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.supabase import supabase_service

logger = logging.getLogger(__name__)
router = APIRouter()

_cache: TTLCache = TTLCache(maxsize=256, ttl=60)


def _cache_key(prefix: str, **kwargs: Any) -> str:
    raw = json.dumps({"_": prefix, **kwargs}, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()

# Ordinal map for letter sizes (Category B — size up/down, MASE)
SIZE_ORDINAL_LETTER = {
    "xs": 0, "xxs": 0, "extra small": 0,
    "s": 1, "small": 1,
    "m": 2, "medium": 2,
    "l": 3, "large": 3,
    "xl": 4, "xxl": 4, "extra large": 4,
}


def _size_to_ordinal(s: str | None) -> int | None:
    """Map size to ordinal for comparison. Letter sizes (XS–XXL) and numeric (30, 32, 34)."""
    if not s:
        return None
    k = str(s).strip().lower()
    if k in SIZE_ORDINAL_LETTER:
        return SIZE_ORDINAL_LETTER[k]
    try:
        return int(k)
    except ValueError:
        return None


# Attribution window: purchases/ATC count only if within this many days of tryon
ATTRIBUTION_WINDOW_DAYS = 30


@router.get("/debug")
async def analytics_debug(
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
):
    """
    Debug endpoint: returns raw event count and sample to verify backend<>Supabase connection.
    Only available when DEBUG=true.
    """
    from app.config import get_settings
    if not get_settings().debug:
        raise HTTPException(status_code=404, detail="Not found")
    if not start:
        end_d = datetime.now(timezone.utc).date()
        start_d = end_d - timedelta(days=30)
    else:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
        end_d = datetime.strptime(end or start, "%Y-%m-%d").date() if end else start_d

    start_ts = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
    end_extended = end_d + timedelta(days=ATTRIBUTION_WINDOW_DAYS)
    end_ts_extended = datetime.combine(end_extended, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()

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
        by_type = defaultdict(int)
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
    widget_opens: int = 0
    open_to_tryon_rate: Optional[float] = None
    cart_abandonment_rate: Optional[float] = None
    avg_time_to_purchase_hours: Optional[float] = None
    same_session_purchase_rate: Optional[float] = None
    returns: int = 0
    return_rate: Optional[float] = None
    revenue_lost_to_returns: float = 0.0
    bracket_orders: int = 0
    bracket_rate: Optional[float] = None


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
    if not start:
        end_d = datetime.now(timezone.utc).date()
        start_d = end_d - timedelta(days=30)
    else:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
        end_d = datetime.strptime(end or start, "%Y-%m-%d").date() if end else start_d

    start_ts = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
    end_ts = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()
    # Extend window for conversions: purchases can occur up to 30d after tryon
    end_extended = end_d + timedelta(days=ATTRIBUTION_WINDOW_DAYS)
    end_ts_extended = datetime.combine(end_extended, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()

    q = (
        supabase_service.client.table("analytics_events")
        .select("event_type,session_id,event_data,created_at")
        .gte("created_at", start_ts)
        .lte("created_at", end_ts_extended)
    )
    if shop:
        q = q.eq("shop_domain", shop)
    if brand_id:
        q = q.eq("brand_id", brand_id)

    r = q.execute()
    events = r.data or []

    # Cohort: sessions where tryon_started in [start, end]; first_tryon_ts per session
    session_first_tryon: dict[str, str] = {}
    for e in events:
        if e.get("event_type") != "tryon_started":
            continue
        sid = e.get("session_id")
        created = e.get("created_at")
        if not sid or not created:
            continue
        if start_ts <= created <= end_ts:
            if sid not in session_first_tryon or created < session_first_tryon[sid]:
                session_first_tryon[sid] = created

    cohort_sessions = set(session_first_tryon.keys())
    tryons = len(cohort_sessions)

    # Conversions: ATC and purchase within attribution window
    cutoff_ts: dict[str, str] = {}
    for sid, first in session_first_tryon.items():
        try:
            dt = datetime.fromisoformat(first.replace("Z", "+00:00"))
            cut = dt + timedelta(days=ATTRIBUTION_WINDOW_DAYS)
            cutoff_ts[sid] = cut.isoformat()
        except (ValueError, TypeError):
            cutoff_ts[sid] = ""

    atc_sessions: set[str] = set()
    order_ids: set[str] = set()
    revenue = 0.0
    purchase_count = 0

    for e in events:
        sid = e.get("session_id")
        if sid not in cohort_sessions:
            continue
        created = e.get("created_at") or ""
        cutoff = cutoff_ts.get(sid, "")
        if cutoff and created > cutoff:
            continue

        if e.get("event_type") == "add_to_cart":
            atc_sessions.add(sid)
        elif e.get("event_type") == "purchase":
            purchase_count += 1
            ed = e.get("event_data") or {}
            revenue += float(ed.get("amount", 0) or 0)
            oid = ed.get("order_id")
            if oid:
                order_ids.add(str(oid))

    atcs = len(atc_sessions)
    purchases = purchase_count

    sessions = len({e["session_id"] for e in events if e.get("session_id") and e.get("session_id") in cohort_sessions})
    atc_rate = atcs / tryons if tryons else None
    purchase_rate = purchases / tryons if tryons else None
    rev_per_tryon = revenue / tryons if tryons else None
    aov_tryon = revenue / len(order_ids) if order_ids else (revenue / purchase_count if purchase_count else None)

    # --- Enhanced metrics: widget_opens, cart_abandonment, time-to-purchase, returns, brackets ---
    widget_opens = sum(1 for e in events if e.get("event_type") == "widget_opened")
    open_to_tryon_rate = (tryons / widget_opens) if widget_opens else None
    cart_abandonment_rate = (1 - (purchases / atcs)) if atcs > 0 else None

    # Time to purchase: delta between first tryon_started and purchase per session
    session_tryon_ts: dict[str, datetime] = {}
    for e in events:
        if e.get("event_type") == "tryon_started" and e.get("session_id") in cohort_sessions:
            sid = e["session_id"]
            try:
                dt = datetime.fromisoformat(e["created_at"].replace("Z", "+00:00"))
                if sid not in session_tryon_ts or dt < session_tryon_ts[sid]:
                    session_tryon_ts[sid] = dt
            except (ValueError, TypeError, KeyError):
                pass

    purchase_deltas_hours: list[float] = []
    same_session_purchases = 0
    total_purchases_for_ssp = 0
    return_count = 0
    revenue_lost_to_returns = 0.0
    bracket_orders = 0

    for e in events:
        sid = e.get("session_id")
        etype = e.get("event_type")
        ed = e.get("event_data") or {}

        if etype == "purchase" and sid in session_tryon_ts:
            total_purchases_for_ssp += 1
            try:
                purchase_dt = datetime.fromisoformat(e["created_at"].replace("Z", "+00:00"))
                delta_hours = (purchase_dt - session_tryon_ts[sid]).total_seconds() / 3600
                purchase_deltas_hours.append(delta_hours)
                if delta_hours <= 1.0:
                    same_session_purchases += 1
            except (ValueError, TypeError, KeyError):
                pass
            if ed.get("is_bracketed"):
                bracket_orders += 1

        if etype == "return" and sid in cohort_sessions:
            return_count += 1
            revenue_lost_to_returns += float(ed.get("amount_refunded", 0) or 0)

    avg_time_to_purchase_hours = (
        round(sum(purchase_deltas_hours) / len(purchase_deltas_hours), 2)
        if purchase_deltas_hours else None
    )
    same_session_purchase_rate = (
        round(same_session_purchases / total_purchases_for_ssp, 4)
        if total_purchases_for_ssp else None
    )
    return_rate = round(return_count / purchases, 4) if purchases else None
    bracket_rate = round(bracket_orders / purchases, 4) if purchases else None

    result = MetricsResponse(
        tryons_started=tryons,
        add_to_carts=atcs,
        purchases=purchases,
        tryon_atc_rate=round(atc_rate, 4) if atc_rate is not None else None,
        tryon_purchase_rate=round(purchase_rate, 4) if purchase_rate is not None else None,
        revenue_attributed=round(revenue, 2),
        revenue_per_tryon=round(rev_per_tryon, 2) if rev_per_tryon is not None else None,
        aov_tryon=round(aov_tryon, 2) if aov_tryon is not None else None,
        unique_sessions=sessions,
        widget_opens=widget_opens,
        open_to_tryon_rate=round(open_to_tryon_rate, 4) if open_to_tryon_rate is not None else None,
        cart_abandonment_rate=round(cart_abandonment_rate, 4) if cart_abandonment_rate is not None else None,
        avg_time_to_purchase_hours=avg_time_to_purchase_hours,
        same_session_purchase_rate=same_session_purchase_rate,
        returns=return_count,
        return_rate=return_rate,
        revenue_lost_to_returns=round(revenue_lost_to_returns, 2),
        bracket_orders=bracket_orders,
        bracket_rate=bracket_rate,
    )
    _cache[key] = result
    return result


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
    if not start:
        end_d = datetime.now(timezone.utc).date()
        start_d = end_d - timedelta(days=30)
    else:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
        end_d = datetime.strptime(end or start, "%Y-%m-%d").date() if end else start_d

    start_ts = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
    end_ts = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()
    end_extended = end_d + timedelta(days=ATTRIBUTION_WINDOW_DAYS)
    end_ts_extended = datetime.combine(end_extended, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()

    q = (
        supabase_service.client.table("analytics_events")
        .select("event_type,session_id,event_data,created_at,product_id")
        .gte("created_at", start_ts)
        .lte("created_at", end_ts_extended)
    )
    if shop:
        q = q.eq("shop_domain", shop)
    if brand_id:
        q = q.eq("brand_id", brand_id)
    if product_id:
        q = q.eq("product_id", product_id)

    r = q.execute()
    events = r.data or []

    # Cohort: (session_id, product_id) -> first tryon ts. Product from tryon_started.
    session_product_first_tryon: dict[tuple[str, str], str] = {}
    for e in events:
        if e.get("event_type") != "tryon_started":
            continue
        sid = e.get("session_id")
        pid = (e.get("product_id") or "").strip()
        created = e.get("created_at")
        if not sid or not pid or not created or not (start_ts <= created <= end_ts):
            continue
        key = (sid, pid)
        if key not in session_product_first_tryon or created < session_product_first_tryon[key]:
            session_product_first_tryon[key] = created

    # Build cutoff per (session, product)
    cutoff_ts: dict[tuple[str, str], str] = {}
    for (sid, pid), first in session_product_first_tryon.items():
        try:
            dt = datetime.fromisoformat(first.replace("Z", "+00:00"))
            cutoff_ts[(sid, pid)] = (dt + timedelta(days=ATTRIBUTION_WINDOW_DAYS)).isoformat()
        except (ValueError, TypeError):
            cutoff_ts[(sid, pid)] = ""

    # Per product: tryons, atc_sessions, purchase_sessions, revenue, order_ids
    prod_tryons: dict[str, set[str]] = defaultdict(set)
    prod_atc: dict[str, set[str]] = defaultdict(set)
    prod_revenue: dict[str, float] = defaultdict(float)
    prod_orders: dict[str, set[str]] = defaultdict(set)
    prod_purchase_count: dict[str, int] = defaultdict(int)

    for e in events:
        sid = e.get("session_id")
        pid_raw = (e.get("product_id") or "").strip()
        created = e.get("created_at") or ""
        etype = e.get("event_type")

        if etype == "tryon_started" and sid and pid_raw and (sid, pid_raw) in session_product_first_tryon:
            prod_tryons[pid_raw].add(sid)

        if etype == "add_to_cart" and sid and pid_raw:
            if (sid, pid_raw) not in session_product_first_tryon:
                continue
            cutoff = cutoff_ts.get((sid, pid_raw), "")
            if cutoff and created > cutoff:
                continue
            prod_atc[pid_raw].add(sid)

        if etype == "purchase" and sid:
            # Attribute full order to primary product (first tryon for this session)
            session_products = [p for (s, p) in session_product_first_tryon if s == sid]
            if not session_products:
                continue
            primary = session_products[0]
            cutoff = cutoff_ts.get((sid, primary), "")
            if cutoff and created > cutoff:
                continue
            ed = e.get("event_data") or {}
            amt = float(ed.get("amount", 0) or 0)
            prod_revenue[primary] += amt
            prod_purchase_count[primary] += 1
            oid = ed.get("order_id")
            if oid:
                prod_orders[primary].add(str(oid))

    # Build per-product metrics
    all_products = set(prod_tryons.keys()) | set(prod_atc.keys()) | set(prod_revenue.keys())
    products_out = []
    for pid in sorted(all_products):
        tryons = len(prod_tryons.get(pid, set()))
        atcs = len(prod_atc.get(pid, set()))
        rev = prod_revenue.get(pid, 0.0)
        orders = prod_orders.get(pid, set())
        purch_cnt = prod_purchase_count.get(pid, 0)
        aov = rev / len(orders) if orders else (rev / purch_cnt if purch_cnt else None)
        purchases = purch_cnt
        atc_rate = atcs / tryons if tryons else None
        purch_rate = purchases / tryons if tryons else None
        rev_per_tryon = rev / tryons if tryons else None
        products_out.append(ProductMetrics(
            product_id=pid,
            tryons_started=tryons,
            add_to_carts=atcs,
            purchases=purch_cnt,
            revenue_attributed=round(rev, 2),
            tryon_atc_rate=round(atc_rate, 4) if atc_rate is not None else None,
            tryon_purchase_rate=round(purch_rate, 4) if purch_rate is not None else None,
            revenue_per_tryon=round(rev_per_tryon, 2) if rev_per_tryon is not None else None,
            aov_tryon=round(aov, 2) if aov is not None else None,
        ))

    products_out.sort(key=lambda x: (-x.revenue_attributed, -x.tryons_started))

    result = MetricsByProductResponse(
        products=products_out,
        attribution_window_days=ATTRIBUTION_WINDOW_DAYS,
    )
    _cache[key] = result
    return result


# --- Category B: Fit Accuracy ---

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
    if not start:
        end_d = datetime.now(timezone.utc).date()
        start_d = end_d - timedelta(days=30)
    else:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
        end_d = datetime.strptime(end or start, "%Y-%m-%d").date() if end else start_d

    start_ts = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
    end_ts = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()

    q = (
        supabase_service.client.table("analytics_events")
        .select("event_type,session_id,event_data")
        .gte("created_at", start_ts)
        .lte("created_at", end_ts)
    )
    if shop:
        q = q.eq("shop_domain", shop)
    if brand_id:
        q = q.eq("brand_id", brand_id)
    r = q.execute()
    events = r.data or []

    dist_rec: dict[str, int] = {}
    dist_sel: dict[str, int] = {}
    dist_pur: dict[str, int] = {}
    session_to_rec: dict[str, str] = {}
    session_to_sel: dict[str, str] = {}
    session_to_pur: dict[str, str] = {}

    for e in events:
        sid = e.get("session_id")
        ed = e.get("event_data") or {}
        etype = e.get("event_type")
        raw = ed.get("size")
        size_raw = str(raw).strip() if raw is not None and raw != "" else ""

        if etype == "size_recommended" and size_raw and sid:
            size_key = size_raw.upper() if len(size_raw) <= 3 else size_raw
            dist_rec[size_key] = dist_rec.get(size_key, 0) + 1
            session_to_rec[sid] = size_raw

        elif etype == "size_selected" and size_raw and sid:
            size_key = size_raw.upper() if len(size_raw) <= 3 else size_raw
            dist_sel[size_key] = dist_sel.get(size_key, 0) + 1
            session_to_sel[sid] = size_raw

        elif etype == "add_to_cart" and size_raw and sid:
            size_key = size_raw.upper() if len(size_raw) <= 3 else size_raw
            dist_sel[size_key] = dist_sel.get(size_key, 0) + 1
            if sid not in session_to_sel:
                session_to_sel[sid] = size_raw

        elif etype == "purchase":
            items = ed.get("items") or []
            for it in items:
                sid_item = it.get("session_id")
                raw_sz = it.get("size")
                sz = str(raw_sz).strip() if raw_sz is not None and raw_sz != "" else ""
                if sid_item and sz:
                    size_key = sz.upper() if len(sz) <= 3 else sz
                    dist_pur[size_key] = dist_pur.get(size_key, 0) + 1
                    session_to_pur[sid_item] = sz

    sessions_with_rec = len(session_to_rec)
    sessions_with_both = set(session_to_rec.keys()) & set(session_to_pur.keys())
    sessions_with_purchase_and_size = len(sessions_with_both)

    acceptance_rate = None
    size_up_rate = None
    size_down_rate = None
    mase = None

    if sessions_with_both:
        matches = sum(
            1 for sid in sessions_with_both
            if _normalize_size(session_to_rec.get(sid)) == _normalize_size(session_to_pur.get(sid))
        )
        acceptance_rate = round(matches / len(sessions_with_both), 4) if sessions_with_both else None
        # MASE = mean |ordinal_purchased - ordinal_recommended| (purchased vs recommended)
        err_sum = 0.0
        err_n = 0
        for sid in sessions_with_both:
            o_rec = _size_to_ordinal(session_to_rec.get(sid))
            o_pur = _size_to_ordinal(session_to_pur.get(sid))
            if o_rec is not None and o_pur is not None:
                err_sum += abs(o_pur - o_rec)
                err_n += 1
        mase = round(err_sum / err_n, 4) if err_n else None

    sessions_with_sel_and_rec = set(session_to_rec.keys()) & set(session_to_sel.keys())
    if sessions_with_sel_and_rec:
        up = 0
        down = 0
        for sid in sessions_with_sel_and_rec:
            o_rec = _size_to_ordinal(session_to_rec.get(sid))
            o_sel = _size_to_ordinal(session_to_sel.get(sid))
            if o_rec is not None and o_sel is not None:
                diff = o_sel - o_rec
                if diff > 0:
                    up += 1
                elif diff < 0:
                    down += 1
        total = len(sessions_with_sel_and_rec)
        size_up_rate = round(up / total, 4) if total else None
        size_down_rate = round(down / total, 4) if total else None

    result = FitMetricsResponse(
        size_distribution_recommended=dist_rec,
        size_distribution_selected=dist_sel,
        size_distribution_purchased=dist_pur,
        acceptance_rate=acceptance_rate,
        size_up_rate=size_up_rate,
        size_down_rate=size_down_rate,
        mase=mase,
        sessions_with_recommendation=sessions_with_rec,
        sessions_with_purchase_and_size=sessions_with_purchase_and_size,
    )
    _cache[key] = result
    return result


# Aliases for acceptance comparison (e.g. "Large" vs "L")
SIZE_ALIASES = {"large": "l", "medium": "m", "small": "s", "extra small": "xs", "extra large": "xl"}


# --- Category C: Trend & Demand Forecasting ---

class VelocityResponse(BaseModel):
    tryon_velocity_7d: int
    tryon_velocity_30d: int
    purchase_velocity_7d: int
    purchase_velocity_30d: int
    tryon_sessions_7d: int
    purchase_sessions_7d: int
    velocity_ratio_7d: Optional[float] = None  # purchase / tryon (lag indicator)
    velocity_ratio_30d: Optional[float] = None


class AtRiskProduct(BaseModel):
    product_id: str
    tryons: int
    purchases: int
    conversion: Optional[float] = None
    ratio: Optional[float] = None
    severity: str  # "critical" | "warning" | "watch"


class AtRiskProductsResponse(BaseModel):
    products: list[AtRiskProduct]
    min_tryons: int
    conversion_threshold: float


class ExplorationTrendPoint(BaseModel):
    week_start: str  # YYYY-MM-DD (Monday)
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
    stress_score: float  # views / max(purchases, 1)


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
    by_country: dict[str, dict[str, float]]  # country -> { size -> pct }
    raw_counts: dict[str, dict[str, int]]  # country -> { size -> count }
    top_size_by_country: dict[str, str] = {}
    by_city: dict[str, dict[str, CitySizeData]] = {}  # country -> { city -> CitySizeData }


@router.get("/velocity", response_model=VelocityResponse)
async def get_velocity(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
):
    key = _cache_key("velocity", start=start, end=end, shop=shop)
    if key in _cache:
        return _cache[key]
    if not start:
        end_d = datetime.now(timezone.utc).date()
        start_d = end_d - timedelta(days=30)
    else:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
        end_d = datetime.strptime(end or start, "%Y-%m-%d").date() if end else start_d

    start_ts = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
    end_ts = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()

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

    # Rolling window: 7d = last 7 days of range, 30d = full range
    end_dt = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc)
    cutoff_7d = (end_dt - timedelta(days=7)).isoformat()

    tryons_7d = sum(1 for e in events if e.get("event_type") == "tryon_started" and (e.get("created_at") or "") >= cutoff_7d)
    tryons_30d = sum(1 for e in events if e.get("event_type") == "tryon_started")
    purchases_7d = sum(1 for e in events if e.get("event_type") == "purchase" and (e.get("created_at") or "") >= cutoff_7d)
    purchases_30d = sum(1 for e in events if e.get("event_type") == "purchase")

    tryon_sessions_7d = len({e["session_id"] for e in events if e.get("event_type") == "tryon_started" and e.get("session_id") and (e.get("created_at") or "") >= cutoff_7d})
    purchase_sessions_7d = len({e["session_id"] for e in events if e.get("event_type") == "purchase" and e.get("session_id") and (e.get("created_at") or "") >= cutoff_7d})

    velocity_ratio_7d = round(purchases_7d / tryons_7d, 4) if tryons_7d else None
    velocity_ratio_30d = round(purchases_30d / tryons_30d, 4) if tryons_30d else None

    result = VelocityResponse(
        tryon_velocity_7d=tryons_7d,
        tryon_velocity_30d=tryons_30d,
        purchase_velocity_7d=purchases_7d,
        purchase_velocity_30d=purchases_30d,
        tryon_sessions_7d=tryon_sessions_7d,
        purchase_sessions_7d=purchase_sessions_7d,
        velocity_ratio_7d=velocity_ratio_7d,
        velocity_ratio_30d=velocity_ratio_30d,
    )
    _cache[key] = result
    return result


@router.get("/at-risk-products", response_model=AtRiskProductsResponse)
async def get_at_risk_products(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    min_tryons: int = Query(5, description="Minimum tryons to consider"),
    conversion_threshold: float = Query(0.05, description="Conversion below this flags as at-risk"),
):
    key = _cache_key("at_risk", start=start, end=end, shop=shop, min_tryons=min_tryons, threshold=conversion_threshold)
    if key in _cache:
        return _cache[key]
    if not start:
        end_d = datetime.now(timezone.utc).date()
        start_d = end_d - timedelta(days=30)
    else:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
        end_d = datetime.strptime(end or start, "%Y-%m-%d").date() if end else start_d

    start_ts = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
    end_ts = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()

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

    # Pass 1: session_id -> product_id from tryon_started; count tryons per product
    session_to_product: dict[str, str] = {}
    by_product: dict[str, dict[str, int]] = {}
    for e in events:
        if e.get("event_type") != "tryon_started":
            continue
        sid = e.get("session_id")
        pid = (e.get("product_id") or "").strip() or "_unknown"
        if sid and pid != "_unknown":
            session_to_product[str(sid)] = pid
        if pid not in by_product:
            by_product[pid] = {"tryons": 0, "purchases": 0}
        by_product[pid]["tryons"] += 1

    # Pass 2: attribute purchases to products via session
    for e in events:
        if e.get("event_type") != "purchase":
            continue
        sid = e.get("session_id")
        items = (e.get("event_data") or {}).get("items") or []
        seen_products: set[str] = set()
        for it in items:
            sid_item = it.get("session_id")
            prod = session_to_product.get(str(sid_item or "")) if sid_item else None
            if not prod and sid:
                prod = session_to_product.get(str(sid))
            if prod:
                seen_products.add(prod)
        if not seen_products and sid:
            prod = session_to_product.get(str(sid))
            if prod:
                seen_products.add(prod)
        for p in seen_products:
            if p not in by_product:
                by_product[p] = {"tryons": 0, "purchases": 0}
            by_product[p]["purchases"] += 1

    at_risk: list[AtRiskProduct] = []
    for pid, data in by_product.items():
        tryons = data["tryons"]
        purchases = data["purchases"]
        if pid == "_unknown" or tryons < min_tryons:
            continue
        conversion = (purchases / tryons) if tryons else 0.0
        ratio = (tryons / purchases) if purchases else float("inf") if tryons else 0.0

        if purchases == 0:
            severity = "critical"
        elif conversion < conversion_threshold:
            severity = "warning"
        elif conversion < 0.10:
            severity = "watch"
        else:
            continue

        at_risk.append(AtRiskProduct(
            product_id=pid,
            tryons=tryons,
            purchases=purchases,
            conversion=round(conversion, 4) if purchases else None,
            ratio=round(ratio, 2) if purchases and ratio != float("inf") else None,
            severity=severity,
        ))

    at_risk.sort(key=lambda x: (-x.tryons, x.purchases))

    result = AtRiskProductsResponse(
        products=at_risk,
        min_tryons=min_tryons,
        conversion_threshold=conversion_threshold,
    )
    _cache[key] = result
    return result


@router.get("/exploration-trend", response_model=ExplorationTrendResponse)
async def get_exploration_trend(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
):
    key = _cache_key("exploration_trend", start=start, end=end, shop=shop)
    if key in _cache:
        return _cache[key]
    if not start:
        end_d = datetime.now(timezone.utc).date()
        start_d = end_d - timedelta(days=90)
    else:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
        end_d = datetime.strptime(end or start, "%Y-%m-%d").date() if end else start_d

    start_ts = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
    end_ts = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()

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

    # size_viewed + size_selected = size exploration
    exploration_events = [
        e for e in events
        if e.get("event_type") in ("size_viewed", "size_selected") and e.get("session_id")
    ]

    # Group by ISO week (Monday start)
    week_to_sessions: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for e in exploration_events:
        created = e.get("created_at")
        if not created:
            continue
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            # Monday = start of week
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


@router.get("/size-stress", response_model=SizeStressResponse)
async def get_size_stress(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    min_views: int = Query(10, description="Minimum views to consider"),
    views_to_purchases_ratio: float = Query(5.0, description="Flag if views >= ratio * purchases"),
):
    key = _cache_key("size_stress", start=start, end=end, shop=shop, min_views=min_views, ratio=views_to_purchases_ratio)
    if key in _cache:
        return _cache[key]
    if not start:
        end_d = datetime.now(timezone.utc).date()
        start_d = end_d - timedelta(days=30)
    else:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
        end_d = datetime.strptime(end or start, "%Y-%m-%d").date() if end else start_d

    start_ts = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
    end_ts = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()

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

    # Build session -> product_id from tryon_started; aggregate views and purchases per (product_id, size)
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
            p = pid or (session_to_product.get(sid or "", ""))
            if p and sz:
                size_key = sz.upper() if len(sz) <= 3 else sz
                key_views_clean[(p, size_key)] += 1
        elif etype == "purchase":
            for it in (ed.get("items") or []):
                raw_sz = it.get("size")
                sz = str(raw_sz).strip() if raw_sz is not None and raw_sz != "" else None
                sid_item = it.get("session_id")
                p = pid or (session_to_product.get(sid_item or "", "")) if sid_item else pid
                if p and sz:
                    size_key = sz.upper() if len(sz) <= 3 else sz
                    key_purchases_clean[(p, size_key)] += 1

    all_keys = set(key_views_clean.keys()) | set(key_purchases_clean.keys())
    items = []
    for (pid, size) in all_keys:
        views = key_views_clean.get((pid, size), 0)
        purchases = key_purchases_clean.get((pid, size), 0)
        if views < min_views:
            continue
        stress = views / max(purchases, 1)
        if stress < views_to_purchases_ratio:
            continue
        conv = round(purchases / views, 4) if views else None
        items.append(SizeStressItem(
            product_id=pid,
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
    if not start:
        end_d = datetime.now(timezone.utc).date()
        start_d = end_d - timedelta(days=30)
    else:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
        end_d = datetime.strptime(end or start, "%Y-%m-%d").date() if end else start_d

    start_ts = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
    end_ts = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()

    q = (
        supabase_service.client.table("analytics_events")
        .select("event_type,event_data,country,city")
        .gte("created_at", start_ts)
        .lte("created_at", end_ts)
    )
    if shop:
        q = q.eq("shop_domain", shop)
    if brand_id:
        q = q.eq("brand_id", brand_id)
    r = q.execute()
    events = r.data or []

    country_size: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    # country -> city -> size -> count
    city_size: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

    for e in events:
        country = (e.get("country") or "Unknown").strip() or "Unknown"
        raw_city = (e.get("city") or "").strip()
        city = raw_city.title() if raw_city else ""
        ed = e.get("event_data") or {}
        etype = e.get("event_type")

        if etype in ("size_recommended", "size_selected", "size_viewed"):
            raw = ed.get("size")
            sz = str(raw).strip() if raw is not None and raw != "" else None
            if sz:
                size_key = sz.upper() if len(sz) <= 3 else sz
                country_size[country][size_key] += 1
                if city:
                    city_size[country][city][size_key] += 1
        elif etype == "purchase":
            for it in (ed.get("items") or []):
                raw_sz = it.get("size")
                sz = str(raw_sz).strip() if raw_sz is not None and raw_sz != "" else None
                if sz:
                    size_key = sz.upper() if len(sz) <= 3 else sz
                    country_size[country][size_key] += 1
                    if city:
                        city_size[country][city][size_key] += 1

    by_country: dict[str, dict[str, float]] = {}
    raw_counts: dict[str, dict[str, int]] = {}
    top_size_by_country: dict[str, str] = {}
    for country, size_counts in country_size.items():
        total = sum(size_counts.values())
        raw_counts[country] = dict(size_counts)
        by_country[country] = {
            sz: round(cnt / total, 4) if total else 0.0
            for sz, cnt in size_counts.items()
        }
        if size_counts:
            top = max(size_counts.items(), key=lambda x: x[1])
            top_size_by_country[country] = top[0]

    by_city: dict[str, dict[str, CitySizeData]] = {}
    for country, cities in city_size.items():
        by_city[country] = {}
        for city_name, sc in cities.items():
            total = sum(sc.values())
            by_city[country][city_name] = CitySizeData(
                sizes={sz: round(cnt / total, 4) if total else 0.0 for sz, cnt in sc.items()},
                raw_counts=dict(sc),
                total=total,
                top_size=max(sc.items(), key=lambda x: x[1])[0] if sc else "",
            )

    result = RegionalSizeResponse(
        by_country=by_country,
        raw_counts=raw_counts,
        top_size_by_country=top_size_by_country,
        by_city=by_city,
    )
    _cache[key] = result
    return result


def _normalize_size(s: str | None) -> str:
    """Canonical form for size comparison."""
    if not s:
        return ""
    k = str(s).strip().lower()
    return SIZE_ALIASES.get(k, k)


# ---------------------------------------------------------------------------
# Phase 1+: Dwell-Time Aggregation
# ---------------------------------------------------------------------------

class DwellMetricsResponse(BaseModel):
    total_sessions: int
    avg_dwell_seconds: Optional[float] = None
    median_dwell_seconds: Optional[float] = None
    p90_dwell_seconds: Optional[float] = None
    dwell_to_conversion: Optional[float] = None


@router.get("/dwell-metrics", response_model=DwellMetricsResponse)
async def get_dwell_metrics(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    brand_id: Optional[str] = Query(None, description="Filter by brand_id"),
):
    key = _cache_key("dwell_metrics", start=start, end=end, shop=shop, brand_id=brand_id)
    if key in _cache:
        return _cache[key]

    if not start:
        end_d = datetime.now(timezone.utc).date()
        start_d = end_d - timedelta(days=30)
    else:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
        end_d = datetime.strptime(end or start, "%Y-%m-%d").date() if end else start_d

    start_ts = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
    end_ts = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()

    q = (
        supabase_service.client.table("analytics_events")
        .select("event_type,session_id,event_data,created_at")
        .gte("created_at", start_ts)
        .lte("created_at", end_ts)
    )
    if shop:
        q = q.eq("shop_domain", shop)
    if brand_id:
        q = q.eq("brand_id", brand_id)
    r = q.execute()
    events = r.data or []

    session_dwell: dict[str, float] = {}
    conversion_sessions: set[str] = set()

    for e in events:
        sid = e.get("session_id")
        etype = e.get("event_type")
        ed = e.get("event_data") or {}

        if etype == "tryon_ended" and sid:
            dwell = ed.get("dwell_seconds")
            if dwell is not None:
                try:
                    session_dwell[sid] = float(dwell)
                except (ValueError, TypeError):
                    pass

        if etype in ("add_to_cart", "purchase") and sid:
            conversion_sessions.add(sid)

    total_sessions = len(session_dwell)
    if not total_sessions:
        result = DwellMetricsResponse(total_sessions=0)
        _cache[key] = result
        return result

    dwell_values = sorted(session_dwell.values())
    avg_dwell = round(sum(dwell_values) / len(dwell_values), 2)
    median_dwell = round(statistics.median(dwell_values), 2)

    p90_idx = int(len(dwell_values) * 0.9)
    p90_dwell = round(dwell_values[min(p90_idx, len(dwell_values) - 1)], 2)

    above_median = {sid for sid, d in session_dwell.items() if d > median_dwell}
    above_median_converted = above_median & conversion_sessions
    dwell_to_conversion = (
        round(len(above_median_converted) / len(above_median) * 100, 2)
        if above_median else None
    )

    result = DwellMetricsResponse(
        total_sessions=total_sessions,
        avg_dwell_seconds=avg_dwell,
        median_dwell_seconds=median_dwell,
        p90_dwell_seconds=p90_dwell,
        dwell_to_conversion=dwell_to_conversion,
    )
    _cache[key] = result
    return result


# ---------------------------------------------------------------------------
# Phase 2: Device / Platform Breakdown
# ---------------------------------------------------------------------------

class DeviceMetrics(BaseModel):
    device_type: str
    tryons: int
    add_to_carts: int
    purchases: int
    conversion_rate: Optional[float] = None


class DeviceMetricsResponse(BaseModel):
    devices: list[DeviceMetrics]
    total_events: int


def _classify_device(user_agent: str | None) -> str:
    if not user_agent:
        return "unknown"
    ua = user_agent.lower()
    if "ipad" in ua or "tablet" in ua:
        return "tablet"
    if "mobile" in ua or "android" in ua or "iphone" in ua:
        return "mobile"
    return "desktop"


@router.get("/device-metrics", response_model=DeviceMetricsResponse)
async def get_device_metrics(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    brand_id: Optional[str] = Query(None, description="Filter by brand_id"),
):
    key = _cache_key("device_metrics", start=start, end=end, shop=shop, brand_id=brand_id)
    if key in _cache:
        return _cache[key]

    if not start:
        end_d = datetime.now(timezone.utc).date()
        start_d = end_d - timedelta(days=30)
    else:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
        end_d = datetime.strptime(end or start, "%Y-%m-%d").date() if end else start_d

    start_ts = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
    end_ts = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()

    q = (
        supabase_service.client.table("analytics_events")
        .select("event_type,session_id,user_agent")
        .gte("created_at", start_ts)
        .lte("created_at", end_ts)
    )
    if shop:
        q = q.eq("shop_domain", shop)
    if brand_id:
        q = q.eq("brand_id", brand_id)
    r = q.execute()
    events = r.data or []

    device_tryons: dict[str, set[str]] = defaultdict(set)
    device_atc: dict[str, set[str]] = defaultdict(set)
    device_purchases: dict[str, int] = defaultdict(int)

    for e in events:
        device = _classify_device(e.get("user_agent"))
        sid = e.get("session_id") or ""
        etype = e.get("event_type")

        if etype == "tryon_started" and sid:
            device_tryons[device].add(sid)
        elif etype == "add_to_cart" and sid:
            device_atc[device].add(sid)
        elif etype == "purchase":
            device_purchases[device] += 1

    all_devices = set(device_tryons) | set(device_atc) | set(device_purchases)
    devices_out: list[DeviceMetrics] = []
    for device in sorted(all_devices):
        t = len(device_tryons.get(device, set()))
        a = len(device_atc.get(device, set()))
        p = device_purchases.get(device, 0)
        conv = round(p / t, 4) if t else None
        devices_out.append(DeviceMetrics(
            device_type=device, tryons=t, add_to_carts=a,
            purchases=p, conversion_rate=conv,
        ))

    result = DeviceMetricsResponse(devices=devices_out, total_events=len(events))
    _cache[key] = result
    return result


# ---------------------------------------------------------------------------
# Phase 3: Per-Product Fit Confidence
# ---------------------------------------------------------------------------

class ProductFitConfidence(BaseModel):
    product_id: str
    total_recommendations: int
    acceptance_count: int
    size_up_count: int
    size_down_count: int
    fit_confidence_score: float
    most_common_deviation: Optional[str] = None


class FitConfidenceResponse(BaseModel):
    products: list[ProductFitConfidence]


@router.get("/fit-confidence-by-product", response_model=FitConfidenceResponse)
async def get_fit_confidence_by_product(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    brand_id: Optional[str] = Query(None, description="Filter by brand_id"),
):
    key = _cache_key("fit_confidence", start=start, end=end, shop=shop, brand_id=brand_id)
    if key in _cache:
        return _cache[key]

    if not start:
        end_d = datetime.now(timezone.utc).date()
        start_d = end_d - timedelta(days=30)
    else:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
        end_d = datetime.strptime(end or start, "%Y-%m-%d").date() if end else start_d

    start_ts = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
    end_ts = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()

    q = (
        supabase_service.client.table("analytics_events")
        .select("event_type,session_id,product_id,event_data")
        .gte("created_at", start_ts)
        .lte("created_at", end_ts)
    )
    if shop:
        q = q.eq("shop_domain", shop)
    if brand_id:
        q = q.eq("brand_id", brand_id)
    r = q.execute()
    events = r.data or []

    # session -> product -> recommended size
    session_product_rec: dict[str, dict[str, str]] = defaultdict(dict)
    # session -> product -> selected/purchased size
    session_product_sel: dict[str, dict[str, str]] = defaultdict(dict)

    for e in events:
        sid = e.get("session_id")
        pid = (e.get("product_id") or "").strip()
        ed = e.get("event_data") or {}
        etype = e.get("event_type")
        raw_size = ed.get("size")
        sz = str(raw_size).strip() if raw_size is not None and raw_size != "" else ""

        if not sid or not pid:
            continue

        if etype == "size_recommended" and sz:
            session_product_rec[sid][pid] = sz
        elif etype in ("size_selected", "add_to_cart") and sz:
            if pid not in session_product_sel[sid]:
                session_product_sel[sid][pid] = sz

    # Aggregate per product
    prod_stats: dict[str, dict[str, int]] = defaultdict(lambda: {
        "total": 0, "accept": 0, "up": 0, "down": 0,
    })

    for sid, products in session_product_rec.items():
        for pid, rec_size in products.items():
            sel_size = session_product_sel.get(sid, {}).get(pid)
            if not sel_size:
                continue
            stats = prod_stats[pid]
            stats["total"] += 1
            o_rec = _size_to_ordinal(rec_size)
            o_sel = _size_to_ordinal(sel_size)
            if _normalize_size(rec_size) == _normalize_size(sel_size):
                stats["accept"] += 1
            elif o_rec is not None and o_sel is not None:
                if o_sel > o_rec:
                    stats["up"] += 1
                elif o_sel < o_rec:
                    stats["down"] += 1

    products_out: list[ProductFitConfidence] = []
    for pid, s in prod_stats.items():
        total = s["total"]
        if not total:
            continue
        score = round((s["accept"] / total) * 100, 2)
        if s["up"] >= s["down"] and s["up"] > 0:
            deviation = "size_up"
        elif s["down"] > 0:
            deviation = "size_down"
        else:
            deviation = "none"
        products_out.append(ProductFitConfidence(
            product_id=pid,
            total_recommendations=total,
            acceptance_count=s["accept"],
            size_up_count=s["up"],
            size_down_count=s["down"],
            fit_confidence_score=score,
            most_common_deviation=deviation,
        ))

    products_out.sort(key=lambda x: (-x.fit_confidence_score, -x.total_recommendations))
    result = FitConfidenceResponse(products=products_out)
    _cache[key] = result
    return result


# ---------------------------------------------------------------------------
# Phase 3: Repeat / High-Intent Visitors
# ---------------------------------------------------------------------------

class RepeatVisitorMetrics(BaseModel):
    unique_users: int
    returning_users: int
    returning_user_rate: Optional[float] = None
    repeat_product_tryons: int
    high_intent_users: int
    high_intent_conversion_rate: Optional[float] = None


class RepeatVisitorsResponse(BaseModel):
    metrics: RepeatVisitorMetrics
    top_repeated_products: list[dict]


@router.get("/repeat-visitors", response_model=RepeatVisitorsResponse)
async def get_repeat_visitors(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    brand_id: Optional[str] = Query(None, description="Filter by brand_id"),
):
    key = _cache_key("repeat_visitors", start=start, end=end, shop=shop, brand_id=brand_id)
    if key in _cache:
        return _cache[key]

    if not start:
        end_d = datetime.now(timezone.utc).date()
        start_d = end_d - timedelta(days=30)
    else:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
        end_d = datetime.strptime(end or start, "%Y-%m-%d").date() if end else start_d

    start_ts = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
    end_ts = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()

    q = (
        supabase_service.client.table("analytics_events")
        .select("event_type,session_id,user_id,product_id")
        .gte("created_at", start_ts)
        .lte("created_at", end_ts)
    )
    if shop:
        q = q.eq("shop_domain", shop)
    if brand_id:
        q = q.eq("brand_id", brand_id)
    r = q.execute()
    events = r.data or []

    # user -> set of sessions
    user_sessions: dict[str, set[str]] = defaultdict(set)
    # (user, product) -> set of sessions where tryon_started
    user_product_sessions: dict[tuple[str, str], set[str]] = defaultdict(set)
    # users who purchased
    purchase_users: set[str] = set()

    for e in events:
        uid = e.get("user_id")
        sid = e.get("session_id")
        pid = (e.get("product_id") or "").strip()
        etype = e.get("event_type")

        if not uid:
            continue

        if sid:
            user_sessions[uid].add(sid)

        if etype == "tryon_started" and pid and sid:
            user_product_sessions[(uid, pid)].add(sid)

        if etype == "purchase":
            purchase_users.add(uid)

    unique_users = len(user_sessions)
    returning_users = sum(1 for sessions in user_sessions.values() if len(sessions) >= 2)
    returning_user_rate = round(returning_users / unique_users, 4) if unique_users else None

    # High intent: users who tried same product in 2+ distinct sessions
    high_intent_user_ids: set[str] = set()
    repeat_product_tryons = 0
    product_repeat_counts: dict[str, int] = defaultdict(int)

    for (uid, pid), sessions in user_product_sessions.items():
        if len(sessions) >= 2:
            high_intent_user_ids.add(uid)
            repeat_product_tryons += len(sessions)
            product_repeat_counts[pid] += len(sessions)

    high_intent_converted = high_intent_user_ids & purchase_users
    high_intent_conversion_rate = (
        round(len(high_intent_converted) / len(high_intent_user_ids), 4)
        if high_intent_user_ids else None
    )

    top_products = sorted(product_repeat_counts.items(), key=lambda x: -x[1])[:10]
    top_repeated_products = [
        {
            "product_id": pid,
            "repeat_count": cnt,
            "converted": any(
                uid in purchase_users
                for (uid, p), _ in user_product_sessions.items()
                if p == pid and len(user_product_sessions[(uid, p)]) >= 2
            ),
        }
        for pid, cnt in top_products
    ]

    result = RepeatVisitorsResponse(
        metrics=RepeatVisitorMetrics(
            unique_users=unique_users,
            returning_users=returning_users,
            returning_user_rate=returning_user_rate,
            repeat_product_tryons=repeat_product_tryons,
            high_intent_users=len(high_intent_user_ids),
            high_intent_conversion_rate=high_intent_conversion_rate,
        ),
        top_repeated_products=top_repeated_products,
    )
    _cache[key] = result
    return result


# ---------------------------------------------------------------------------
# Phase 3: Body-Shape-to-Size Correlation
# ---------------------------------------------------------------------------

class BodyShapeInsight(BaseModel):
    product_id: str
    measurement_group: str
    recommended_size: str
    actual_purchased_size: str
    deviation: str
    shopper_count: int


class BodyShapeInsightsResponse(BaseModel):
    insights: list[BodyShapeInsight]
    total_data_points: int


def _bucket_measurement(value: float) -> str:
    """Bucket a body measurement (cm) into 10-cm ranges."""
    lower = int(value // 10) * 10
    return f"{lower}_{lower + 10}"


@router.get("/body-shape-insights", response_model=BodyShapeInsightsResponse)
async def get_body_shape_insights(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    brand_id: Optional[str] = Query(None, description="Filter by brand_id"),
):
    key = _cache_key("body_shape_insights", start=start, end=end, shop=shop, brand_id=brand_id)
    if key in _cache:
        return _cache[key]

    if not start:
        end_d = datetime.now(timezone.utc).date()
        start_d = end_d - timedelta(days=30)
    else:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
        end_d = datetime.strptime(end or start, "%Y-%m-%d").date() if end else start_d

    start_ts = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
    end_ts = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()

    q = (
        supabase_service.client.table("analytics_events")
        .select("event_type,session_id,user_id,product_id,event_data")
        .gte("created_at", start_ts)
        .lte("created_at", end_ts)
    )
    if shop:
        q = q.eq("shop_domain", shop)
    if brand_id:
        q = q.eq("brand_id", brand_id)
    r = q.execute()
    events = r.data or []

    # Collect user_ids that have size_recommended events
    user_product_rec: dict[str, dict[str, str]] = defaultdict(dict)
    user_product_purchased: dict[str, dict[str, str]] = defaultdict(dict)
    relevant_user_ids: set[str] = set()

    for e in events:
        uid = e.get("user_id")
        pid = (e.get("product_id") or "").strip()
        ed = e.get("event_data") or {}
        etype = e.get("event_type")

        if not uid:
            continue

        if etype == "size_recommended" and pid:
            raw = ed.get("size")
            sz = str(raw).strip() if raw is not None and raw != "" else ""
            if sz:
                user_product_rec[uid][pid] = sz
                relevant_user_ids.add(uid)

        if etype == "purchase" and pid:
            for it in (ed.get("items") or []):
                raw_sz = it.get("size")
                sz = str(raw_sz).strip() if raw_sz is not None and raw_sz != "" else ""
                p = it.get("product_id") or pid
                if sz:
                    user_product_purchased[uid][p] = sz

    if not relevant_user_ids:
        result = BodyShapeInsightsResponse(insights=[], total_data_points=0)
        _cache[key] = result
        return result

    # Look up fit_passports for these users
    fp_q = (
        supabase_service.client.table("fit_passports")
        .select("user_id,chest,waist,hips")
        .in_("user_id", list(relevant_user_ids))
    )
    fp_r = fp_q.execute()
    passports = {fp["user_id"]: fp for fp in (fp_r.data or []) if fp.get("user_id")}

    # (product, measurement_group, rec_size, purchased_size) -> count
    insight_counts: dict[tuple[str, str, str, str], int] = defaultdict(int)
    total_data_points = 0

    for uid in relevant_user_ids:
        fp = passports.get(uid)
        if not fp:
            continue
        chest = fp.get("chest")
        if chest is None:
            continue
        try:
            measurement_group = f"chest_{_bucket_measurement(float(chest))}"
        except (ValueError, TypeError):
            continue

        for pid, rec_size in user_product_rec.get(uid, {}).items():
            purchased_size = user_product_purchased.get(uid, {}).get(pid)
            if not purchased_size:
                continue
            insight_counts[(pid, measurement_group, rec_size, purchased_size)] += 1
            total_data_points += 1

    insights: list[BodyShapeInsight] = []
    for (pid, mg, rec, purchased), count in insight_counts.items():
        o_rec = _size_to_ordinal(rec)
        o_pur = _size_to_ordinal(purchased)
        if o_rec is not None and o_pur is not None:
            if o_pur > o_rec:
                deviation = "size_up"
            elif o_pur < o_rec:
                deviation = "size_down"
            else:
                deviation = "none"
        elif _normalize_size(rec) == _normalize_size(purchased):
            deviation = "none"
        else:
            deviation = "unknown"

        insights.append(BodyShapeInsight(
            product_id=pid,
            measurement_group=mg,
            recommended_size=rec,
            actual_purchased_size=purchased,
            deviation=deviation,
            shopper_count=count,
        ))

    insights.sort(key=lambda x: (-x.shopper_count, x.product_id))
    result = BodyShapeInsightsResponse(insights=insights, total_data_points=total_data_points)
    _cache[key] = result
    return result


# ---------------------------------------------------------------------------
# Phase 2: Return Analysis
# ---------------------------------------------------------------------------

class ReturnMetricsResponse(BaseModel):
    total_purchases: int
    total_returns: int
    return_rate: Optional[float] = None
    revenue_lost: float
    top_returned_products: list[dict]
    # Per-SKU sales + returns (every SKU with a sale or a return), sorted by units sold.
    sku_breakdown: list[dict] = []
    avg_days_to_return: Optional[float] = None


@router.get("/return-metrics", response_model=ReturnMetricsResponse)
async def get_return_metrics(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    brand_id: Optional[str] = Query(None, description="Filter by brand_id"),
):
    key = _cache_key("return_metrics", start=start, end=end, shop=shop, brand_id=brand_id)
    if key in _cache:
        return _cache[key]

    if not start:
        end_d = datetime.now(timezone.utc).date()
        start_d = end_d - timedelta(days=30)
    else:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
        end_d = datetime.strptime(end or start, "%Y-%m-%d").date() if end else start_d

    start_ts = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
    end_ts = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()

    q = (
        supabase_service.client.table("analytics_events")
        .select("event_type,session_id,product_id,event_data,created_at")
        .gte("created_at", start_ts)
        .lte("created_at", end_ts)
    )
    if shop:
        q = q.eq("shop_domain", shop)
    if brand_id:
        q = q.eq("brand_id", brand_id)
    r = q.execute()
    events = r.data or []

    # order_id -> {product_id, purchase_ts, amount}
    purchases_by_order: dict[str, dict] = {}
    # order_id -> return_ts
    returns_by_order: dict[str, str] = {}
    # sku key -> {purchases, returns, sku, variant_id, product_id, title} — counts are in units
    sku_counts: dict[str, dict[str, Any]] = {}
    revenue_lost = 0.0
    total_purchases = 0
    total_returns = 0

    def _sku_meta(li: dict[str, Any]) -> tuple[str, dict[str, str]]:
        """Group key + display meta for a line item. Shopify variant == one SKU;
        prefer the merchant SKU code, fall back to variant_id, then product_id."""
        sku = str(li.get("sku") or "").strip()
        variant_id = str(li.get("variant_id") or "").strip()
        product_id = str(li.get("product_id") or "").strip()
        key = sku or variant_id or product_id
        meta = {
            "sku": sku,
            "variant_id": variant_id,
            "product_id": product_id,
            "title": str(li.get("title") or li.get("name") or "").strip(),
        }
        return key, meta

    def _bump_sku(li: dict[str, Any], field: str) -> None:
        key, meta = _sku_meta(li)
        if not key:
            return
        qty = int(li.get("quantity", 1) or 1)
        row = sku_counts.get(key)
        if row is None:
            row = {"purchases": 0, "returns": 0, **meta}
            sku_counts[key] = row
        row[field] += qty
        # Backfill display fields if a later event carries richer info
        for k in ("sku", "variant_id", "product_id", "title"):
            if not row.get(k) and meta.get(k):
                row[k] = meta[k]

    for e in events:
        ed = e.get("event_data") or {}
        etype = e.get("event_type")
        pid = (e.get("product_id") or "").strip()

        if etype == "purchase":
            total_purchases += 1
            oid = ed.get("order_id")
            if oid:
                purchases_by_order[str(oid)] = {
                    "product_id": pid,
                    "created_at": e.get("created_at"),
                    "amount": float(ed.get("amount", 0) or 0),
                }
            # Per-SKU sold units from the raw order line items (webhook stores these
            # in event_data; the top-level product_id column is not set for orders/paid).
            line_items = ed.get("line_items") or []
            if line_items:
                for li in line_items:
                    _bump_sku(li, "purchases")
            elif pid:  # legacy events with no line_items payload
                _bump_sku({"product_id": pid}, "purchases")

        elif etype == "return":
            total_returns += 1
            oid = ed.get("order_id")
            if oid:
                returns_by_order[str(oid)] = e.get("created_at", "")
            revenue_lost += float(ed.get("amount_refunded", 0) or 0)
            # Per-SKU returned units from refund line items (event_data.items).
            ret_items = ed.get("items") or []
            if ret_items:
                for it in ret_items:
                    _bump_sku(it, "returns")
            else:  # legacy events with no per-item payload
                ret_pid = pid or str(ed.get("product_id", "") or "")
                if ret_pid:
                    _bump_sku({"product_id": ret_pid}, "returns")

    return_rate = round(total_returns / total_purchases, 4) if total_purchases else None

    # Compute avg days to return
    days_to_return: list[float] = []
    for oid, return_ts in returns_by_order.items():
        purchase = purchases_by_order.get(oid)
        if not purchase or not return_ts or not purchase.get("created_at"):
            continue
        try:
            p_dt = datetime.fromisoformat(purchase["created_at"].replace("Z", "+00:00"))
            r_dt = datetime.fromisoformat(return_ts.replace("Z", "+00:00"))
            days_to_return.append((r_dt - p_dt).total_seconds() / 86400)
        except (ValueError, TypeError):
            pass

    avg_days = round(sum(days_to_return) / len(days_to_return), 2) if days_to_return else None

    def _sku_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "sku": row["sku"],
            "variant_id": row["variant_id"],
            "product_id": row["product_id"],
            "title": row["title"],
            "return_count": row["returns"],
            "purchase_count": row["purchases"],
            "return_rate": round(row["returns"] / row["purchases"], 4) if row["purchases"] else None,
        }

    # "Most returned" widget: per-SKU, only SKUs that actually came back.
    top_returned = sorted(
        [_sku_row(row) for row in sku_counts.values() if row["returns"] > 0],
        key=lambda x: -x["return_count"],
    )[:10]

    # Full per-SKU sales + returns table (paid and/or returned), best sellers first.
    sku_breakdown = sorted(
        [_sku_row(row) for row in sku_counts.values() if row["purchases"] > 0 or row["returns"] > 0],
        key=lambda x: (-x["purchase_count"], -x["return_count"]),
    )[:100]

    result = ReturnMetricsResponse(
        total_purchases=total_purchases,
        total_returns=total_returns,
        return_rate=return_rate,
        revenue_lost=round(revenue_lost, 2),
        top_returned_products=top_returned,
        sku_breakdown=sku_breakdown,
        avg_days_to_return=avg_days,
    )
    _cache[key] = result
    return result


# ---------------------------------------------------------------------------
# Phase 4: A/B Cohort Comparison (TryOn users vs baseline)
# ---------------------------------------------------------------------------

class CohortComparisonResponse(BaseModel):
    tryon_users_count: int
    tryon_purchases: int
    tryon_returns: int
    tryon_aov: Optional[float] = None
    tryon_return_rate: Optional[float] = None
    tryon_conversion_rate: Optional[float] = None
    tryon_bracket_rate: Optional[float] = None
    baseline_note: str = "Compare these TryOn metrics against your Shopify store averages"


@router.get("/cohort-comparison", response_model=CohortComparisonResponse)
async def get_cohort_comparison(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    brand_id: Optional[str] = Query(None, description="Filter by brand_id"),
):
    key = _cache_key("cohort_comparison", start=start, end=end, shop=shop, brand_id=brand_id)
    if key in _cache:
        return _cache[key]

    if not start:
        end_d = datetime.now(timezone.utc).date()
        start_d = end_d - timedelta(days=30)
    else:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
        end_d = datetime.strptime(end or start, "%Y-%m-%d").date() if end else start_d

    start_ts = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
    end_ts = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()

    q = (
        supabase_service.client.table("analytics_events")
        .select("event_type,session_id,user_id,event_data,created_at")
        .gte("created_at", start_ts)
        .lte("created_at", end_ts)
    )
    if shop:
        q = q.eq("shop_domain", shop)
    if brand_id:
        q = q.eq("brand_id", brand_id)
    r = q.execute()
    events = r.data or []

    tryon_users: set[str] = set()
    tryon_sessions: set[str] = set()

    for e in events:
        if e.get("event_type") == "tryon_started":
            uid = e.get("user_id")
            sid = e.get("session_id")
            if uid:
                tryon_users.add(uid)
            if sid:
                tryon_sessions.add(sid)

    purchases = 0
    returns = 0
    revenue = 0.0
    order_ids: set[str] = set()
    bracket_orders = 0

    for e in events:
        sid = e.get("session_id")
        uid = e.get("user_id")
        ed = e.get("event_data") or {}
        etype = e.get("event_type")

        is_tryon_user = (uid and uid in tryon_users) or (sid and sid in tryon_sessions)
        if not is_tryon_user:
            continue

        if etype == "purchase":
            purchases += 1
            revenue += float(ed.get("amount", 0) or 0)
            oid = ed.get("order_id")
            if oid:
                order_ids.add(str(oid))
            if ed.get("is_bracketed"):
                bracket_orders += 1

        elif etype == "return":
            returns += 1

    tryon_users_count = len(tryon_users) or len(tryon_sessions)
    tryon_aov = round(revenue / len(order_ids), 2) if order_ids else (
        round(revenue / purchases, 2) if purchases else None
    )
    tryon_return_rate = round(returns / purchases, 4) if purchases else None
    tryon_conversion_rate = round(purchases / tryon_users_count, 4) if tryon_users_count else None
    tryon_bracket_rate = round(bracket_orders / purchases, 4) if purchases else None

    result = CohortComparisonResponse(
        tryon_users_count=tryon_users_count,
        tryon_purchases=purchases,
        tryon_returns=returns,
        tryon_aov=tryon_aov,
        tryon_return_rate=tryon_return_rate,
        tryon_conversion_rate=tryon_conversion_rate,
        tryon_bracket_rate=tryon_bracket_rate,
    )
    _cache[key] = result
    return result


# ---------------------------------------------------------------------------
# Phase 4: Predictive Return-Risk Scoring
# ---------------------------------------------------------------------------

class OrderReturnRisk(BaseModel):
    order_id: str
    session_id: Optional[str] = None
    risk_score: float
    risk_factors: list[str]
    product_id: Optional[str] = None


class ReturnRiskResponse(BaseModel):
    high_risk_orders: list[OrderReturnRisk]
    avg_risk_score: Optional[float] = None
    total_scored: int


@router.get("/return-risk", response_model=ReturnRiskResponse)
async def get_return_risk(
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    brand_id: Optional[str] = Query(None, description="Filter by brand_id"),
):
    key = _cache_key("return_risk", shop=shop, brand_id=brand_id)
    if key in _cache:
        return _cache[key]

    end_d = datetime.now(timezone.utc).date()
    start_d = end_d - timedelta(days=30)
    start_ts = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
    end_ts = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()

    q = (
        supabase_service.client.table("analytics_events")
        .select("event_type,session_id,user_id,product_id,event_data,created_at")
        .gte("created_at", start_ts)
        .lte("created_at", end_ts)
    )
    if shop:
        q = q.eq("shop_domain", shop)
    if brand_id:
        q = q.eq("brand_id", brand_id)
    r = q.execute()
    events = r.data or []

    # Pre-compute helper structures
    session_rec_size: dict[str, str] = {}
    session_sel_size: dict[str, str] = {}
    session_dwell: dict[str, float] = {}
    session_product: dict[str, str] = {}
    user_sessions: dict[str, set[str]] = defaultdict(set)

    # Historical return counts per product
    product_purchases: dict[str, int] = defaultdict(int)
    product_returns: dict[str, int] = defaultdict(int)

    purchase_events: list[dict] = []

    for e in events:
        sid = e.get("session_id")
        uid = e.get("user_id")
        pid = (e.get("product_id") or "").strip()
        ed = e.get("event_data") or {}
        etype = e.get("event_type")

        if uid and sid:
            user_sessions[uid].add(sid)

        if etype == "tryon_started" and sid and pid:
            session_product[sid] = pid

        if etype == "size_recommended" and sid:
            raw = ed.get("size")
            if raw:
                session_rec_size[sid] = str(raw).strip()

        if etype in ("size_selected", "add_to_cart") and sid:
            raw = ed.get("size")
            if raw and sid not in session_sel_size:
                session_sel_size[sid] = str(raw).strip()

        if etype == "tryon_ended" and sid:
            dwell = ed.get("dwell_seconds")
            if dwell is not None:
                try:
                    session_dwell[sid] = float(dwell)
                except (ValueError, TypeError):
                    pass

        if etype == "purchase":
            purchase_events.append(e)
            if pid:
                product_purchases[pid] += 1

        if etype == "return":
            ret_pid = pid or ed.get("product_id", "")
            if ret_pid:
                product_returns[ret_pid] += 1

    product_return_rates: dict[str, float] = {}
    for pid, pcount in product_purchases.items():
        product_return_rates[pid] = product_returns.get(pid, 0) / pcount if pcount else 0.0

    scored_orders: list[OrderReturnRisk] = []
    all_scores: list[float] = []

    for e in purchase_events:
        sid = e.get("session_id")
        uid = e.get("user_id")
        ed = e.get("event_data") or {}
        oid = ed.get("order_id")
        if not oid:
            continue

        score = 0.0
        factors: list[str] = []
        pid = (e.get("product_id") or "").strip() or session_product.get(sid or "", "")

        if ed.get("is_bracketed"):
            score += 40
            factors.append("bracketed_order")

        if sid and sid in session_rec_size and sid in session_sel_size:
            if _normalize_size(session_rec_size[sid]) != _normalize_size(session_sel_size[sid]):
                score += 25
                factors.append("size_mismatch")

        if sid and session_dwell.get(sid, 999) < 30:
            score += 15
            factors.append("rushed_decision")

        if uid and len(user_sessions.get(uid, set())) <= 1:
            score += 10
            factors.append("first_time_user")

        if pid and product_return_rates.get(pid, 0) > 0.15:
            score += 10
            factors.append("high_return_product")

        all_scores.append(score)
        if score > 50:
            scored_orders.append(OrderReturnRisk(
                order_id=str(oid),
                session_id=sid,
                risk_score=score,
                risk_factors=factors,
                product_id=pid or None,
            ))

    scored_orders.sort(key=lambda x: -x.risk_score)
    avg_risk = round(sum(all_scores) / len(all_scores), 2) if all_scores else None

    result = ReturnRiskResponse(
        high_risk_orders=scored_orders,
        avg_risk_score=avg_risk,
        total_scored=len(all_scores),
    )
    _cache[key] = result
    return result


# ---------------------------------------------------------------------------
# Time-Series Trends (weekly key metrics)
# ---------------------------------------------------------------------------

class TimeSeriesPoint(BaseModel):
    week_start: str  # YYYY-MM-DD (Monday)
    widget_opens: int = 0
    tryons: int = 0
    add_to_carts: int = 0
    purchases: int = 0
    returns: int = 0
    revenue: float = 0.0
    conversion_rate: Optional[float] = None
    atc_rate: Optional[float] = None
    return_rate: Optional[float] = None


class TimeSeriesResponse(BaseModel):
    weeks: list[TimeSeriesPoint]


@router.get("/time-series", response_model=TimeSeriesResponse)
async def get_time_series(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    brand_id: Optional[str] = Query(None, description="Filter by brand_id"),
):
    key = _cache_key("time_series", start=start, end=end, shop=shop, brand_id=brand_id)
    if key in _cache:
        return _cache[key]

    if not start:
        end_d = datetime.now(timezone.utc).date()
        start_d = end_d - timedelta(days=90)
    else:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
        end_d = datetime.strptime(end or start, "%Y-%m-%d").date() if end else start_d

    start_ts = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
    end_ts = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()

    q = (
        supabase_service.client.table("analytics_events")
        .select("event_type,session_id,event_data,created_at")
        .gte("created_at", start_ts)
        .lte("created_at", end_ts)
    )
    if shop:
        q = q.eq("shop_domain", shop)
    if brand_id:
        q = q.eq("brand_id", brand_id)
    r = q.execute()
    events = r.data or []

    week_data: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "widget_opens": 0, "tryon_sessions": set(), "atc_sessions": set(),
        "purchases": 0, "returns": 0, "revenue": 0.0,
    })

    for e in events:
        created = e.get("created_at")
        if not created:
            continue
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            week_start = (dt.date() - timedelta(days=dt.weekday())).isoformat()
        except (ValueError, TypeError):
            continue

        etype = e.get("event_type")
        sid = e.get("session_id") or ""
        ed = e.get("event_data") or {}
        w = week_data[week_start]

        if etype == "widget_opened":
            w["widget_opens"] += 1
        elif etype == "tryon_started" and sid:
            w["tryon_sessions"].add(sid)
        elif etype == "add_to_cart" and sid:
            w["atc_sessions"].add(sid)
        elif etype == "purchase":
            w["purchases"] += 1
            w["revenue"] += float(ed.get("amount", 0) or 0)
        elif etype == "return":
            w["returns"] += 1

    weeks_out: list[TimeSeriesPoint] = []
    for week_start in sorted(week_data.keys()):
        w = week_data[week_start]
        tryons = len(w["tryon_sessions"])
        atcs = len(w["atc_sessions"])
        purchases = w["purchases"]
        returns = w["returns"]
        weeks_out.append(TimeSeriesPoint(
            week_start=week_start,
            widget_opens=w["widget_opens"],
            tryons=tryons,
            add_to_carts=atcs,
            purchases=purchases,
            returns=returns,
            revenue=round(w["revenue"], 2),
            conversion_rate=round(purchases / tryons * 100, 2) if tryons else None,
            atc_rate=round(atcs / tryons * 100, 2) if tryons else None,
            return_rate=round(returns / purchases * 100, 2) if purchases else None,
        ))

    result = TimeSeriesResponse(weeks=weeks_out)
    _cache[key] = result
    return result


# ---------------------------------------------------------------------------
# Fit-to-Purchase Correlation
# ---------------------------------------------------------------------------

class FitPurchaseCorrelationBucket(BaseModel):
    deviation: str  # "accepted", "size_up_1", "size_down_1", "size_up_2+", "size_down_2+"
    sessions: int
    purchases: int
    returns: int
    purchase_rate: Optional[float] = None
    return_rate: Optional[float] = None


class FitPurchaseCorrelationResponse(BaseModel):
    buckets: list[FitPurchaseCorrelationBucket]
    total_sessions_with_recommendation: int
    overall_acceptance_rate: Optional[float] = None


@router.get("/fit-purchase-correlation", response_model=FitPurchaseCorrelationResponse)
async def get_fit_purchase_correlation(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    brand_id: Optional[str] = Query(None, description="Filter by brand_id"),
):
    """
    Shows the relationship between fit recommendation accuracy and purchase/return outcomes.
    Groups sessions by size deviation (accepted, sized up, sized down) and shows
    purchase rate and return rate for each group.
    """
    key = _cache_key("fit_purchase_correlation", start=start, end=end, shop=shop, brand_id=brand_id)
    if key in _cache:
        return _cache[key]

    if not start:
        end_d = datetime.now(timezone.utc).date()
        start_d = end_d - timedelta(days=90)
    else:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
        end_d = datetime.strptime(end or start, "%Y-%m-%d").date() if end else start_d

    start_ts = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
    end_ts = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()

    q = (
        supabase_service.client.table("analytics_events")
        .select("event_type,session_id,product_id,event_data,created_at")
        .gte("created_at", start_ts)
        .lte("created_at", end_ts)
    )
    if shop:
        q = q.eq("shop_domain", shop)
    if brand_id:
        q = q.eq("brand_id", brand_id)
    r = q.execute()
    events = r.data or []

    session_rec: dict[str, str] = {}
    session_sel: dict[str, str] = {}
    session_purchased: set[str] = set()
    session_returned: set[str] = set()

    for e in events:
        sid = e.get("session_id")
        ed = e.get("event_data") or {}
        etype = e.get("event_type")
        raw = ed.get("size")
        sz = str(raw).strip() if raw is not None and raw != "" else ""

        if not sid:
            continue

        if etype == "size_recommended" and sz:
            session_rec[sid] = sz
        elif etype in ("size_selected", "add_to_cart") and sz:
            if sid not in session_sel:
                session_sel[sid] = sz
        elif etype == "purchase":
            session_purchased.add(sid)
        elif etype == "return":
            session_returned.add(sid)

    sessions_with_both = set(session_rec.keys()) & set(session_sel.keys())
    total_with_rec = len(session_rec)

    bucket_counts: dict[str, dict[str, int]] = defaultdict(lambda: {
        "sessions": 0, "purchases": 0, "returns": 0,
    })

    accepted_count = 0
    for sid in sessions_with_both:
        rec = session_rec[sid]
        sel = session_sel[sid]
        o_rec = _size_to_ordinal(rec)
        o_sel = _size_to_ordinal(sel)

        if _normalize_size(rec) == _normalize_size(sel):
            bucket_name = "accepted"
            accepted_count += 1
        elif o_rec is not None and o_sel is not None:
            diff = o_sel - o_rec
            if diff == 1:
                bucket_name = "size_up_1"
            elif diff >= 2:
                bucket_name = "size_up_2+"
            elif diff == -1:
                bucket_name = "size_down_1"
            else:
                bucket_name = "size_down_2+"
        else:
            bucket_name = "other"

        bucket_counts[bucket_name]["sessions"] += 1
        if sid in session_purchased:
            bucket_counts[bucket_name]["purchases"] += 1
        if sid in session_returned:
            bucket_counts[bucket_name]["returns"] += 1

    display_order = ["accepted", "size_up_1", "size_down_1", "size_up_2+", "size_down_2+", "other"]
    buckets_out: list[FitPurchaseCorrelationBucket] = []
    for name in display_order:
        if name not in bucket_counts:
            continue
        b = bucket_counts[name]
        sessions = b["sessions"]
        purchases = b["purchases"]
        returns = b["returns"]
        buckets_out.append(FitPurchaseCorrelationBucket(
            deviation=name,
            sessions=sessions,
            purchases=purchases,
            returns=returns,
            purchase_rate=round(purchases / sessions * 100, 2) if sessions else None,
            return_rate=round(returns / purchases * 100, 2) if purchases else None,
        ))

    overall_acceptance = (
        round(accepted_count / len(sessions_with_both) * 100, 2)
        if sessions_with_both else None
    )

    result = FitPurchaseCorrelationResponse(
        buckets=buckets_out,
        total_sessions_with_recommendation=total_with_rec,
        overall_acceptance_rate=overall_acceptance,
    )
    _cache[key] = result
    return result
