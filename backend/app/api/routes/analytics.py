"""
Category A & B analytics API — ROI, Attribution, Fit Accuracy
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.supabase import supabase_service

router = APIRouter()

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
    Debug endpoint: returns raw event count and sample to verify backend↔Supabase connection.
    Use ?shop=demo.myshopify.com to match brand dashboard filter.
    """
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


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    brand_id: Optional[str] = Query(None, description="Filter by brand_id"),
):
    """
    Category A metrics for the given date range.
    Uses attribution window: cohort = tryon_started in range; conversions = ATC/purchase
    within ATTRIBUTION_WINDOW_DAYS of first tryon.
    """
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

    return MetricsResponse(
        tryons_started=tryons,
        add_to_carts=atcs,
        purchases=purchases,
        tryon_atc_rate=round(atc_rate, 4) if atc_rate is not None else None,
        tryon_purchase_rate=round(purchase_rate, 4) if purchase_rate is not None else None,
        revenue_attributed=round(revenue, 2),
        revenue_per_tryon=round(rev_per_tryon, 2) if rev_per_tryon is not None else None,
        aov_tryon=round(aov_tryon, 2) if aov_tryon is not None else None,
        unique_sessions=sessions,
    )


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
    """
    Category A: ROI metrics per product. Same attribution window as /metrics.
    """
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

    return MetricsByProductResponse(
        products=products_out,
        attribution_window_days=ATTRIBUTION_WINDOW_DAYS,
    )


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
    """
    Category B: Fit accuracy and size demand metrics.
    """
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

    return FitMetricsResponse(
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


class RegionalSizeResponse(BaseModel):
    by_country: dict[str, dict[str, float]]  # country -> { size -> pct }
    raw_counts: dict[str, dict[str, int]]  # country -> { size -> count }
    top_size_by_country: dict[str, str] = {}  # country -> most common size (for "typical size per region")


@router.get("/velocity", response_model=VelocityResponse)
async def get_velocity(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
):
    """
    Category C: TryOn and Purchase velocity (rolling window counts).
    """
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

    return VelocityResponse(
        tryon_velocity_7d=tryons_7d,
        tryon_velocity_30d=tryons_30d,
        purchase_velocity_7d=purchases_7d,
        purchase_velocity_30d=purchases_30d,
        tryon_sessions_7d=tryon_sessions_7d,
        purchase_sessions_7d=purchase_sessions_7d,
        velocity_ratio_7d=velocity_ratio_7d,
        velocity_ratio_30d=velocity_ratio_30d,
    )


@router.get("/at-risk-products", response_model=AtRiskProductsResponse)
async def get_at_risk_products(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    min_tryons: int = Query(5, description="Minimum tryons to consider"),
    conversion_threshold: float = Query(0.05, description="Conversion below this flags as at-risk"),
):
    """
    Category C: High try-on / low purchase SKUs.
    Products where tryons >= min_tryons AND (purchases=0 OR conversion < threshold).
    """
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

    return AtRiskProductsResponse(
        products=at_risk,
        min_tryons=min_tryons,
        conversion_threshold=conversion_threshold,
    )


@router.get("/exploration-trend", response_model=ExplorationTrendResponse)
async def get_exploration_trend(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
):
    """
    Category C: Rising size exploration — avg sizes viewed/selected per session by week.
    """
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

    return ExplorationTrendResponse(data=data)


@router.get("/size-stress", response_model=SizeStressResponse)
async def get_size_stress(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    min_views: int = Query(10, description="Minimum views to consider"),
    views_to_purchases_ratio: float = Query(5.0, description="Flag if views >= ratio * purchases"),
):
    """
    Category C: Sizes with interest but low conversion (product × size).
    """
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

    return SizeStressResponse(
        items=items,
        min_views=min_views,
        views_to_purchases_ratio_threshold=views_to_purchases_ratio,
    )


@router.get("/regional-size", response_model=RegionalSizeResponse)
async def get_regional_size_distribution(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(None, description="Filter by shop_domain"),
    brand_id: Optional[str] = Query(None, description="Filter by brand_id"),
):
    """
    Category C: Size distribution by country (regional divergence).
    Returns by_country (pct), raw_counts, and top_size_by_country (typical size per region).
    """
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
        .select("event_type,event_data,country")
        .gte("created_at", start_ts)
        .lte("created_at", end_ts)
    )
    if shop:
        q = q.eq("shop_domain", shop)
    if brand_id:
        q = q.eq("brand_id", brand_id)
    r = q.execute()
    events = r.data or []

    # country -> size -> count (from size_recommended, size_selected, purchase)
    country_size: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for e in events:
        country = (e.get("country") or "Unknown").strip() or "Unknown"
        ed = e.get("event_data") or {}
        etype = e.get("event_type")

        if etype in ("size_recommended", "size_selected", "size_viewed"):
            raw = ed.get("size")
            sz = str(raw).strip() if raw is not None and raw != "" else None
            if sz:
                size_key = sz.upper() if len(sz) <= 3 else sz
                country_size[country][size_key] += 1
        elif etype == "purchase":
            for it in (ed.get("items") or []):
                raw_sz = it.get("size")
                sz = str(raw_sz).strip() if raw_sz is not None and raw_sz != "" else None
                if sz:
                    size_key = sz.upper() if len(sz) <= 3 else sz
                    country_size[country][size_key] += 1

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
            top_size = max(size_counts.items(), key=lambda x: x[1])
            top_size_by_country[country] = top_size[0]

    return RegionalSizeResponse(by_country=by_country, raw_counts=raw_counts, top_size_by_country=top_size_by_country)


def _normalize_size(s: str | None) -> str:
    """Canonical form for size comparison."""
    if not s:
        return ""
    k = str(s).strip().lower()
    return SIZE_ALIASES.get(k, k)
