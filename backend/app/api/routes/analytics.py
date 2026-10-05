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
from typing import Any, Callable, NamedTuple, Optional

from cachetools import TTLCache
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import get_brand_shop
from app.api.rate_limit import analytics_rate_limit
from app.services.analytics_cohort import (
    ATTRIBUTION_WINDOW_DAYS,
    COHORT_COLUMNS,
    Cohort,
    build_cohort,
    chosen_sizes,
    parse_ts,
)
from app.services.supabase import supabase_service

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(analytics_rate_limit)])

_cache: TTLCache = TTLCache(maxsize=256, ttl=60)


def _cache_key(prefix: str, **kwargs: Any) -> str:
    raw = json.dumps({"_": prefix, **kwargs}, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()

# PostgREST caps every response at the project's max-rows (1000 on Supabase), silently.
PAGE_SIZE = 1000
# Safety valve so one request can't pull an unbounded table into memory.
MAX_FETCH_ROWS = 250_000
IN_CHUNK = 100


def fetch_all(make_query: Callable[[], Any], page_size: int = PAGE_SIZE) -> list[dict]:
    """Run a select to completion, page by page, in a stable (created_at, id) order.
    `make_query` must return a FRESH builder each call: postgrest-py's .range() appends
    params, so one builder can't be re-ranged. Stops on an empty page rather than a short
    one, so a server max-rows lower than page_size can't truncate the result."""
    rows: list[dict] = []
    offset = 0
    while True:
        batch = (
            make_query()
            .order("created_at")
            .order("id")
            .range(offset, offset + page_size - 1)
            .execute()
        ).data or []
        if not batch:
            return rows
        rows.extend(batch)
        offset += len(batch)
        if len(rows) >= MAX_FETCH_ROWS:
            logger.warning("fetch_all hit MAX_FETCH_ROWS=%d; result truncated", MAX_FETCH_ROWS)
            return rows


def fetch_events(columns: str, shop: str, start_ts: str, end_ts: str, **eq: Any) -> list[dict]:
    """All analytics_events rows for ONE shop in [start_ts, end_ts]. The shop filter is built
    in here so no caller can query without it; extra **eq filters only narrow further."""
    def make():
        q = (
            supabase_service.client.table("analytics_events")
            .select(columns)
            .eq("shop_domain", shop)
            .gte("created_at", start_ts)
            .lte("created_at", end_ts)
        )
        for col, val in eq.items():
            q = q.eq(col, val)
        return q
    return fetch_all(make)


# Longest window a dashboard query may span (inclusive days). 1y + a leap day.
MAX_RANGE_DAYS = 366


class DateRange(NamedTuple):
    start_d: Any  # date
    end_d: Any    # date
    start_ts: str  # start_d 00:00:00 UTC, ISO
    end_ts: str    # end_d 23:59:59.999999 UTC, ISO (end date is inclusive)


def _parse_day(value: str, name: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"Invalid {name} date; use YYYY-MM-DD")


def parse_range(start: Optional[str], end: Optional[str], default_days: int) -> DateRange:
    """Shared ?start=&end= handling for every analytics route.
    No start -> [end (or today UTC) - default_days, end]. Start without end -> that single day.
    400 on a bad format, start > end, or a span over MAX_RANGE_DAYS."""
    if start:
        start_d = _parse_day(start, "start")
        end_d = _parse_day(end, "end") if end else start_d
    else:
        end_d = _parse_day(end, "end") if end else datetime.now(timezone.utc).date()
        start_d = end_d - timedelta(days=default_days)
    if start_d > end_d:
        raise HTTPException(status_code=400, detail="start must be on or before end")
    if (end_d - start_d).days + 1 > MAX_RANGE_DAYS:
        raise HTTPException(status_code=400, detail=f"Date range too long (max {MAX_RANGE_DAYS} days)")
    start_ts = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
    end_ts = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()
    return DateRange(start_d, end_d, start_ts, end_ts)


# --- Time buckets for trend charts -------------------------------------------------------

GRANULARITY_PATTERN = "^(day|week|month)$"


def default_granularity(start_d, end_d) -> str:
    """day up to 31 days, week up to 186 days (~6 months), month beyond."""
    days = (end_d - start_d).days + 1
    if days <= 31:
        return "day"
    if days <= 186:
        return "week"
    return "month"


def _period_start(d, granularity: str):
    if granularity == "week":
        return d - timedelta(days=d.weekday())  # Monday
    if granularity == "month":
        return d.replace(day=1)
    return d


def _next_period(period_start, granularity: str):
    if granularity == "week":
        return period_start + timedelta(days=7)
    if granularity == "month":
        return (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return period_start + timedelta(days=1)


def bucket_ranges(start_d, end_d, granularity: str) -> list[tuple[Any, Any]]:
    """Every bucket covering [start_d, end_d], each clipped to the range: (first_day, last_day).
    A range starting mid-week/month gets a partial first bucket labelled start_d."""
    out = []
    p = _period_start(start_d, granularity)
    while p <= end_d:
        nxt = _next_period(p, granularity)
        out.append((max(p, start_d), min(nxt - timedelta(days=1), end_d)))
        p = nxt
    return out


def bucket_key(created_at: str, granularity: str, start_d) -> Optional[str]:
    """Clipped bucket start (YYYY-MM-DD, UTC) for an event timestamp, or None if unparseable."""
    try:
        d = datetime.fromisoformat(created_at.replace("Z", "+00:00")).astimezone(timezone.utc).date()
    except (ValueError, TypeError, AttributeError):
        return None
    return max(_period_start(d, granularity), start_d).isoformat()


# Ordinal map for letter sizes (Category B — size up/down, MASE)
# Each size is its own step: XS and XXS (or XL and XXL) sharing a rank hid real size-ups.
SIZE_ORDINAL_LETTER = {
    "xxs": 0, "2xs": 0,
    "xs": 1, "extra small": 1,
    "s": 2, "small": 2,
    "m": 3, "medium": 3,
    "l": 4, "large": 4,
    "xl": 5, "extra large": 5,
    "xxl": 6, "2xl": 6,
    "xxxl": 7, "3xl": 7,
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


# Attribution window and every ROI definition live in analytics_cohort (one definition
# per metric). Routes below only shape a Cohort into a response.
_events_cache: TTLCache = TTLCache(maxsize=64, ttl=60)


def clear_caches() -> None:
    """Drop cached responses and cached event scans (tests, and after a data fix)."""
    _cache.clear()
    _events_cache.clear()


def _r(value: Optional[float], digits: int = 4) -> Optional[float]:
    return round(value, digits) if value is not None else None


def _day_bounds(start_d, end_d) -> tuple[datetime, datetime]:
    start = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=timezone.utc)
    end = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc)
    return start, end


def load_cohort_events(shop: str, start_d, end_d) -> list[dict]:
    """Everything a cohort for [start_d, end_d] needs, for ONE shop: all events from start
    to end + the attribution window (purchases that follow a late try-on), plus refunds
    after that up to now (a return can come weeks after the order). Cached for 60s so the
    ~8 routes one dashboard load builds from the same range share a single scan."""
    key = _cache_key("cohort_events", shop=shop, start=start_d, end=end_d)
    cached = _events_cache.get(key)
    if cached is not None:
        return cached
    start, end = _day_bounds(start_d, end_d)
    end_ext = end + timedelta(days=ATTRIBUTION_WINDOW_DAYS)
    events = fetch_events(COHORT_COLUMNS, shop, start.isoformat(), end_ext.isoformat())
    now = datetime.now(timezone.utc)
    if end_ext < now:
        late_from = (end_ext + timedelta(microseconds=1)).isoformat()
        events = events + fetch_events(COHORT_COLUMNS, shop, late_from, now.isoformat(), event_type="return")
    _events_cache[key] = events
    return events


def load_cohort(shop: str, start_d, end_d) -> tuple[Cohort, list[dict]]:
    """The try-on cohort for [start_d, end_d] (inclusive UTC days) and the events it was
    built from."""
    events = load_cohort_events(shop, start_d, end_d)
    start, end = _day_bounds(start_d, end_d)
    return build_cohort(events, start, end, ATTRIBUTION_WINDOW_DAYS), events


@router.get("/debug")
async def analytics_debug(
    shop: str = Depends(get_brand_shop),
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
    start_d, end_d, start_ts, end_ts = parse_range(start, end, 30)
    end_extended = end_d + timedelta(days=ATTRIBUTION_WINDOW_DAYS)
    end_ts_extended = datetime.combine(end_extended, datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()

    try:
        events = fetch_events("event_type,session_id,shop_domain,created_at", shop, start_ts, end_ts_extended)
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
    # Definitions: app/services/analytics_cohort.py. Counts are distinct sessions / orders.
    tryons_started: int
    add_to_carts: int
    purchases: int
    purchase_sessions: int = 0
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
    attribution_window_days: int = ATTRIBUTION_WINDOW_DAYS


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: str = Depends(get_brand_shop),
):
    key = _cache_key("metrics", start=start, end=end, shop=shop)
    if key in _cache:
        return _cache[key]
    start_d, end_d, _, _ = parse_range(start, end, 30)
    c, _events = load_cohort(shop, start_d, end_d)

    # Time from a session's first try-on to each of its orders.
    deltas_hours = [
        (o.created - c.anchors[o.session_id]).total_seconds() / 3600
        for o in c.orders.values()
    ]
    avg_time_to_purchase_hours = round(sum(deltas_hours) / len(deltas_hours), 2) if deltas_hours else None
    same_session_purchase_rate = (
        round(sum(1 for d in deltas_hours if d <= 1.0) / len(deltas_hours), 4) if deltas_hours else None
    )

    result = MetricsResponse(
        tryons_started=c.tryons,
        add_to_carts=c.add_to_carts,
        purchases=c.purchases,
        purchase_sessions=len(c.purchase_sessions),
        tryon_atc_rate=_r(c.atc_rate),
        tryon_purchase_rate=_r(c.purchase_rate),
        revenue_attributed=round(c.revenue, 2),
        revenue_per_tryon=_r(c.revenue_per_tryon, 2),
        aov_tryon=_r(c.aov, 2),
        unique_sessions=len(c.active_sessions),
        widget_opens=c.widget_opens,
        open_to_tryon_rate=_r(c.open_to_tryon_rate),
        cart_abandonment_rate=_r(c.cart_abandonment_rate),
        avg_time_to_purchase_hours=avg_time_to_purchase_hours,
        same_session_purchase_rate=same_session_purchase_rate,
        returns=c.returned,
        return_rate=_r(c.return_rate),
        revenue_lost_to_returns=round(c.revenue_lost, 2),
        bracket_orders=c.bracket_orders,
        bracket_rate=_r(c.bracket_rate),
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


def product_breakdown(c: Cohort) -> dict[str, dict[str, Any]]:
    """Per tried-on product: try-on sessions, add-to-cart sessions, credited orders,
    converting sessions and revenue. An order is credited to ONE product (see
    Cohort.order_product), so product rows sum to the cohort's orders and revenue."""
    out: dict[str, dict[str, Any]] = {}

    def row(pid: str) -> dict[str, Any]:
        return out.setdefault(pid, {
            "tryon_sessions": set(), "atc_sessions": set(), "orders": set(),
            "purchase_sessions": set(), "returned": set(), "revenue": 0.0,
        })

    for sid, tried in c.session_products.items():
        for pid in tried:
            row(pid)["tryon_sessions"].add(sid)
    for sid, pid in c.atc_products:
        if pid in c.session_products.get(sid, []):
            row(pid)["atc_sessions"].add(sid)
    for o in c.orders.values():
        pid = c.order_product(o)
        if not pid:
            continue
        r = row(pid)
        r["orders"].add(o.order_id)
        r["purchase_sessions"].add(o.session_id)
        r["revenue"] += o.amount
        if o.order_id in c.returns:
            r["returned"].add(o.order_id)
    return out


@router.get("/metrics-by-product", response_model=MetricsByProductResponse)
async def get_metrics_by_product(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: str = Depends(get_brand_shop),
    product_id: Optional[str] = Query(None, description="Filter to single product_id"),
):
    key = _cache_key("metrics_by_product", start=start, end=end, shop=shop, product_id=product_id)
    if key in _cache:
        return _cache[key]
    start_d, end_d, _, _ = parse_range(start, end, 30)
    c, _events = load_cohort(shop, start_d, end_d)

    products_out = []
    for pid, r in product_breakdown(c).items():
        if product_id and pid != product_id:
            continue
        tryons = len(r["tryon_sessions"])
        atcs = len(r["atc_sessions"])
        orders = len(r["orders"])
        rev = r["revenue"]
        products_out.append(ProductMetrics(
            product_id=pid,
            tryons_started=tryons,
            add_to_carts=atcs,
            purchases=orders,
            revenue_attributed=round(rev, 2),
            tryon_atc_rate=round(atcs / tryons, 4) if tryons else None,
            tryon_purchase_rate=round(len(r["purchase_sessions"]) / tryons, 4) if tryons else None,
            revenue_per_tryon=round(rev / tryons, 2) if tryons else None,
            aov_tryon=round(rev / orders, 2) if orders else None,
        ))

    products_out.sort(key=lambda x: (-x.revenue_attributed, -x.tryons_started, x.product_id))

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
    shop: str = Depends(get_brand_shop),
):
    key = _cache_key("fit_metrics", start=start, end=end, shop=shop)
    if key in _cache:
        return _cache[key]
    start_d, end_d, start_ts, end_ts = parse_range(start, end, 30)

    events = fetch_events("event_type,session_id,event_data,created_at", shop, start_ts, end_ts)

    # One recommended and one chosen size per session (see chosen_sizes): the
    # distributions count sessions, not clicks.
    session_to_rec, session_to_sel = chosen_sizes(events)
    session_to_pur: dict[str, str] = {}
    dist_rec: dict[str, int] = {}
    dist_sel: dict[str, int] = {}
    dist_pur: dict[str, int] = {}

    def _size_key(sz: str) -> str:
        return sz.upper() if len(sz) <= 3 else sz

    for sz in session_to_rec.values():
        dist_rec[_size_key(sz)] = dist_rec.get(_size_key(sz), 0) + 1
    for sz in session_to_sel.values():
        dist_sel[_size_key(sz)] = dist_sel.get(_size_key(sz), 0) + 1

    seen_orders: set[str] = set()
    for e in events:
        if e.get("event_type") != "purchase":
            continue
        ed = e.get("event_data") or {}
        oid = str(ed.get("order_id") or "")
        if oid:
            if oid in seen_orders:
                continue
            seen_orders.add(oid)
        for it in ed.get("items") or []:
            sid_item = it.get("session_id")
            raw_sz = it.get("size")
            sz = str(raw_sz).strip() if raw_sz is not None and raw_sz != "" else ""
            if sid_item and sz:
                dist_pur[_size_key(sz)] = dist_pur.get(_size_key(sz), 0) + 1
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
    # Trailing windows ending at `end`: 7d = [end-6, end], 30d = [end-29, end].
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
    week_start: str  # bucket start YYYY-MM-DD (kept for the frontend; may be day/week/month)
    bucket_end: Optional[str] = None  # last day in the bucket, clipped to the range
    avg_sizes_per_session: float
    sessions_count: int
    total_size_events: int


class ExplorationTrendResponse(BaseModel):
    data: list[ExplorationTrendPoint]
    granularity: str = "week"


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
    shop: str = Depends(get_brand_shop),
):
    # start is validated but otherwise unused: both windows trail `end`, whatever range the
    # dashboard has selected, so the "7d"/"30d" cards mean what they say.
    _, end_d, _, _ = parse_range(start, end, 30)
    key = _cache_key("velocity", end=end_d.isoformat(), shop=shop)
    if key in _cache:
        return _cache[key]

    # Same definitions as /metrics, over trailing windows: [end-29, end] = 30 days
    # inclusive, [end-6, end] = 7 days inclusive. Both cohorts come from one scan.
    start_30 = end_d - timedelta(days=29)
    events = load_cohort_events(shop, start_30, end_d)
    c30 = build_cohort(events, *_day_bounds(start_30, end_d), ATTRIBUTION_WINDOW_DAYS)
    c7 = build_cohort(events, *_day_bounds(end_d - timedelta(days=6), end_d), ATTRIBUTION_WINDOW_DAYS)

    result = VelocityResponse(
        tryon_velocity_7d=c7.tryons,
        tryon_velocity_30d=c30.tryons,
        purchase_velocity_7d=c7.purchases,
        purchase_velocity_30d=c30.purchases,
        tryon_sessions_7d=c7.tryons,
        purchase_sessions_7d=len(c7.purchase_sessions),
        velocity_ratio_7d=round(c7.purchases / c7.tryons, 4) if c7.tryons else None,
        velocity_ratio_30d=round(c30.purchases / c30.tryons, 4) if c30.tryons else None,
    )
    _cache[key] = result
    return result


@router.get("/at-risk-products", response_model=AtRiskProductsResponse)
async def get_at_risk_products(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: str = Depends(get_brand_shop),
    min_tryons: int = Query(5, description="Minimum tryons to consider"),
    conversion_threshold: float = Query(0.05, description="Conversion below this flags as at-risk"),
):
    key = _cache_key("at_risk", start=start, end=end, shop=shop, min_tryons=min_tryons, threshold=conversion_threshold)
    if key in _cache:
        return _cache[key]
    start_d, end_d, _, _ = parse_range(start, end, 30)
    c, _events = load_cohort(shop, start_d, end_d)

    at_risk: list[AtRiskProduct] = []
    for pid, r in product_breakdown(c).items():
        tryons = len(r["tryon_sessions"])
        purchases = len(r["orders"])
        if tryons < min_tryons:
            continue
        # Conversion is sessions over sessions, like every other purchase rate.
        conversion = len(r["purchase_sessions"]) / tryons

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
            ratio=round(tryons / purchases, 2) if purchases else None,
            severity=severity,
        ))

    at_risk.sort(key=lambda x: (-x.tryons, x.purchases, x.product_id))

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
    shop: str = Depends(get_brand_shop),
    granularity: Optional[str] = Query(None, pattern=GRANULARITY_PATTERN, description="day|week|month; default by span"),
):
    start_d, end_d, start_ts, end_ts = parse_range(start, end, 90)
    gran = granularity or default_granularity(start_d, end_d)
    key = _cache_key("exploration_trend", start=start_d, end=end_d, shop=shop, granularity=gran)
    if key in _cache:
        return _cache[key]

    events = fetch_events("event_type,session_id,created_at", shop, start_ts, end_ts)

    # size_viewed + size_selected = size exploration
    exploration_events = [
        e for e in events
        if e.get("event_type") in ("size_viewed", "size_selected") and e.get("session_id")
    ]

    # bucket start -> session -> size events; every bucket present so the chart has no gaps
    buckets = bucket_ranges(start_d, end_d, gran)
    bucket_sessions: dict[str, dict[str, int]] = {b0.isoformat(): defaultdict(int) for b0, _ in buckets}
    for e in exploration_events:
        bk = bucket_key(e.get("created_at") or "", gran, start_d)
        if bk in bucket_sessions:
            bucket_sessions[bk][e.get("session_id") or ""] += 1

    data = []
    for b0, b1 in buckets:
        session_counts = bucket_sessions[b0.isoformat()]
        total_events = sum(session_counts.values())
        sessions_count = len(session_counts)
        avg_sizes = round(total_events / sessions_count, 2) if sessions_count else 0.0
        data.append(ExplorationTrendPoint(
            week_start=b0.isoformat(),
            bucket_end=b1.isoformat(),
            avg_sizes_per_session=avg_sizes,
            sessions_count=sessions_count,
            total_size_events=total_events,
        ))

    result = ExplorationTrendResponse(data=data, granularity=gran)
    _cache[key] = result
    return result


@router.get("/size-stress", response_model=SizeStressResponse)
async def get_size_stress(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: str = Depends(get_brand_shop),
    min_views: int = Query(10, description="Minimum views to consider"),
    views_to_purchases_ratio: float = Query(5.0, description="Flag if views >= ratio * purchases"),
):
    key = _cache_key("size_stress", start=start, end=end, shop=shop, min_views=min_views, ratio=views_to_purchases_ratio)
    if key in _cache:
        return _cache[key]
    start_d, end_d, start_ts, end_ts = parse_range(start, end, 30)

    events = fetch_events("event_type,product_id,session_id,event_data", shop, start_ts, end_ts)

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
    shop: str = Depends(get_brand_shop),
):
    key = _cache_key("regional_size", start=start, end=end, shop=shop)
    if key in _cache:
        return _cache[key]
    start_d, end_d, start_ts, end_ts = parse_range(start, end, 30)

    events = fetch_events("event_type,event_data,country,city", shop, start_ts, end_ts)

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

class DwellBucket(BaseModel):
    label: str
    sessions: int


# (label, upper bound in seconds, exclusive); the last bucket is open-ended.
DWELL_BUCKETS = [("0 to 10s", 10), ("10 to 20s", 20), ("20 to 30s", 30), ("30 to 60s", 60), ("Over 60s", None)]


class DwellMetricsResponse(BaseModel):
    total_sessions: int
    avg_dwell_seconds: Optional[float] = None
    median_dwell_seconds: Optional[float] = None
    p90_dwell_seconds: Optional[float] = None
    dwell_to_conversion: Optional[float] = None
    histogram: list[DwellBucket] = []


@router.get("/dwell-metrics", response_model=DwellMetricsResponse)
async def get_dwell_metrics(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: str = Depends(get_brand_shop),
):
    key = _cache_key("dwell_metrics", start=start, end=end, shop=shop)
    if key in _cache:
        return _cache[key]

    start_d, end_d, start_ts, end_ts = parse_range(start, end, 30)

    events = fetch_events("event_type,session_id,event_data,created_at", shop, start_ts, end_ts)

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

    histogram = []
    lower = 0.0
    for label, upper in DWELL_BUCKETS:
        n = sum(1 for d in dwell_values if d >= lower and (upper is None or d < upper))
        histogram.append(DwellBucket(label=label, sessions=n))
        lower = upper if upper is not None else lower

    result = DwellMetricsResponse(
        histogram=histogram,
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
    shop: str = Depends(get_brand_shop),
):
    key = _cache_key("device_metrics", start=start, end=end, shop=shop)
    if key in _cache:
        return _cache[key]

    start_d, end_d, _, _ = parse_range(start, end, 30)
    c, events = load_cohort(shop, start_d, end_d)

    # A session has one device: the one it tried on with. Its add-to-cart and its orders
    # are counted under that device, so store orders that never touched the widget no
    # longer show up here as "unknown".
    def device_of(sid: Optional[str]) -> str:
        return _classify_device(c.session_user_agent.get(sid or ""))

    device_tryons: dict[str, set[str]] = defaultdict(set)
    device_atc: dict[str, set[str]] = defaultdict(set)
    device_orders: dict[str, int] = defaultdict(int)
    device_buyers: dict[str, set[str]] = defaultdict(set)

    for sid in c.anchors:
        device_tryons[device_of(sid)].add(sid)
    for sid in c.atc:
        device_atc[device_of(sid)].add(sid)
    for o in c.orders.values():
        device_orders[device_of(o.session_id)] += 1
        device_buyers[device_of(o.session_id)].add(o.session_id)

    devices_out: list[DeviceMetrics] = []
    for device in sorted(device_tryons):
        t = len(device_tryons[device])
        devices_out.append(DeviceMetrics(
            device_type=device,
            tryons=t,
            add_to_carts=len(device_atc.get(device, set())),
            purchases=device_orders.get(device, 0),
            conversion_rate=round(len(device_buyers.get(device, set())) / t, 4) if t else None,
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
    shop: str = Depends(get_brand_shop),
):
    key = _cache_key("fit_confidence", start=start, end=end, shop=shop)
    if key in _cache:
        return _cache[key]

    start_d, end_d, start_ts, end_ts = parse_range(start, end, 30)

    events = fetch_events("event_type,session_id,product_id,event_data,created_at", shop, start_ts, end_ts)

    # (session, product) -> recommended / chosen size, one of each (see chosen_sizes).
    rec_by_pair, sel_by_pair = chosen_sizes(events, by_product=True)
    session_product_rec: dict[str, dict[str, str]] = defaultdict(dict)
    session_product_sel: dict[str, dict[str, str]] = defaultdict(dict)
    for (sid, pid), sz in rec_by_pair.items():
        session_product_rec[sid][pid] = sz
    for (sid, pid), sz in sel_by_pair.items():
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
    shop: str = Depends(get_brand_shop),
):
    key = _cache_key("repeat_visitors", start=start, end=end, shop=shop)
    if key in _cache:
        return _cache[key]

    start_d, end_d, start_ts, end_ts = parse_range(start, end, 30)

    events = fetch_events("event_type,session_id,user_id,product_id", shop, start_ts, end_ts)

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
    shop: str = Depends(get_brand_shop),
):
    key = _cache_key("body_shape_insights", start=start, end=end, shop=shop)
    if key in _cache:
        return _cache[key]

    start_d, end_d, start_ts, end_ts = parse_range(start, end, 30)

    events = fetch_events("event_type,session_id,user_id,product_id,event_data", shop, start_ts, end_ts)

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
    # Chunked: .in_() goes in the URL, and hundreds of UUIDs overflow the request line.
    passports: dict[str, dict] = {}
    user_ids = sorted(relevant_user_ids)
    for i in range(0, len(user_ids), IN_CHUNK):
        fp_r = (
            supabase_service.client.table("fit_passports")
            .select("user_id,chest,waist,hips")
            .in_("user_id", user_ids[i:i + IN_CHUNK])
            .execute()
        )
        for fp in fp_r.data or []:
            if fp.get("user_id"):
                passports[fp["user_id"]] = fp

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
    # Store-wide: every order paid in the range, widget or not. The try-on cohort's own
    # return rate is on /metrics and /cohort-comparison.
    scope: str = "all_store_orders"
    total_purchases: int   # distinct orders paid in the range
    total_returns: int     # of those, orders with at least one refund (whenever it came)
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
    shop: str = Depends(get_brand_shop),
):
    key = _cache_key("return_metrics", start=start, end=end, shop=shop)
    if key in _cache:
        return _cache[key]

    start_d, end_d, _, _ = parse_range(start, end, 30)
    events = load_cohort_events(shop, start_d, end_d)
    start_dt, end_dt = _day_bounds(start_d, end_d)

    # sku key -> {purchases, returns, sku, variant_id, product_id, title} — counts are in units
    sku_counts: dict[str, dict[str, Any]] = {}

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

    # Orders paid in the range, once each.
    orders: dict[str, datetime] = {}
    for e in events:
        if e.get("event_type") != "purchase":
            continue
        t = parse_ts(e.get("created_at"))
        if t is None or not (start_dt <= t <= end_dt):
            continue
        ed = e.get("event_data") or {}
        oid = str(ed.get("order_id") or f"event:{e.get('id')}")
        if oid in orders:
            continue
        orders[oid] = t
        pid = (e.get("product_id") or "").strip()
        # Per-SKU sold units from the raw order line items (webhook stores these
        # in event_data; the top-level product_id column is the try-on handle).
        line_items = ed.get("line_items") or []
        if line_items:
            for li in line_items:
                _bump_sku(li, "purchases")
        elif pid:  # legacy events with no line_items payload
            _bump_sku({"product_id": pid}, "purchases")

    # Refunds on those orders, once each; several refunds on an order are one return.
    first_refund: dict[str, datetime] = {}
    seen_refunds: set[str] = set()
    revenue_lost = 0.0
    for e in events:
        if e.get("event_type") != "return":
            continue
        ed = e.get("event_data") or {}
        oid = str(ed.get("order_id") or "")
        if oid not in orders:
            continue
        refund_key = str(ed.get("refund_id") or f"event:{e.get('id')}")
        if refund_key in seen_refunds:
            continue
        seen_refunds.add(refund_key)
        t = parse_ts(e.get("created_at"))
        if t is not None and (oid not in first_refund or t < first_refund[oid]):
            first_refund[oid] = t
        first_refund.setdefault(oid, orders[oid])
        revenue_lost += float(ed.get("amount_refunded", 0) or 0)
        # Per-SKU returned units from refund line items (event_data.items).
        ret_items = ed.get("items") or []
        if ret_items:
            for it in ret_items:
                _bump_sku(it, "returns")
        else:  # legacy events with no per-item payload
            ret_pid = (e.get("product_id") or "").strip() or str(ed.get("product_id", "") or "")
            if ret_pid:
                _bump_sku({"product_id": ret_pid}, "returns")

    total_purchases = len(orders)
    total_returns = len(first_refund)
    return_rate = round(total_returns / total_purchases, 4) if total_purchases else None

    days_to_return = [
        (first_refund[oid] - orders[oid]).total_seconds() / 86400 for oid in first_refund
    ]
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
# Phase 4: Cohort Comparison (try-on orders vs the rest of the store)
# ---------------------------------------------------------------------------

# Below this many orders on either side, a difference between the two groups is noise.
# The numbers are still returned; `comparable` tells the dashboard not to headline a lift.
MIN_ORDERS_FOR_COMPARISON = 20


class CohortComparisonResponse(BaseModel):
    # Try-on cohort: sessions that tried on in the range, and the orders they led to.
    tryon_sessions: int = 0
    tryon_users_count: int             # distinct signed-in shoppers among those sessions
    tryon_purchases: int               # distinct orders
    tryon_returns: int                 # of those, orders refunded
    tryon_revenue: float = 0.0
    tryon_aov: Optional[float] = None
    tryon_return_rate: Optional[float] = None
    tryon_conversion_rate: Optional[float] = None  # converting sessions / try-on sessions
    tryon_bracket_rate: Optional[float] = None
    # Baseline: store orders paid in the range that never touched the widget.
    baseline_orders: int = 0
    baseline_returns: int = 0
    baseline_revenue: float = 0.0
    baseline_aov: Optional[float] = None
    baseline_return_rate: Optional[float] = None
    baseline_bracket_rate: Optional[float] = None
    attribution_window_days: int = ATTRIBUTION_WINDOW_DAYS
    min_orders_for_comparison: int = MIN_ORDERS_FOR_COMPARISON
    comparable: bool = False
    baseline_note: str = (
        "Baseline is every store order in the range that did not come through the widget. "
        "It has no conversion rate: store visits are not tracked."
    )


@router.get("/cohort-comparison", response_model=CohortComparisonResponse)
async def get_cohort_comparison(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: str = Depends(get_brand_shop),
):
    key = _cache_key("cohort_comparison", start=start, end=end, shop=shop)
    if key in _cache:
        return _cache[key]

    start_d, end_d, _, _ = parse_range(start, end, 30)
    c, _events = load_cohort(shop, start_d, end_d)

    result = CohortComparisonResponse(
        tryon_sessions=c.tryons,
        tryon_users_count=len(c.users),
        tryon_purchases=c.purchases,
        tryon_returns=c.returned,
        tryon_revenue=round(c.revenue, 2),
        tryon_aov=_r(c.aov, 2),
        tryon_return_rate=_r(c.return_rate),
        tryon_conversion_rate=_r(c.purchase_rate),
        tryon_bracket_rate=_r(c.bracket_rate),
        baseline_orders=len(c.baseline_orders),
        baseline_returns=len(c.baseline_returns),
        baseline_revenue=round(c.baseline_revenue, 2),
        baseline_aov=_r(c.baseline_aov, 2),
        baseline_return_rate=_r(c.baseline_return_rate),
        baseline_bracket_rate=_r(c.baseline_bracket_rate),
        comparable=(
            c.purchases >= MIN_ORDERS_FOR_COMPARISON
            and len(c.baseline_orders) >= MIN_ORDERS_FOR_COMPARISON
        ),
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
    shop: str = Depends(get_brand_shop),
):
    key = _cache_key("return_risk", shop=shop)
    if key in _cache:
        return _cache[key]

    start_d, end_d, _, _ = parse_range(None, None, 30)
    c, events = load_cohort(shop, start_d, end_d)

    # Only try-on orders are scored: every signal below except bracketing comes from the
    # try-on session, so a store order without one has nothing to score.
    session_rec_size, session_sel_size = chosen_sizes(events)
    session_dwell: dict[str, float] = {}
    user_sessions: dict[str, set[str]] = defaultdict(set)

    for e in events:
        sid = e.get("session_id")
        uid = e.get("user_id")
        if not sid or sid not in c.anchors:
            continue
        if uid:
            user_sessions[uid].add(sid)
        if e.get("event_type") == "tryon_ended":
            dwell = (e.get("event_data") or {}).get("dwell_seconds")
            if dwell is not None:
                try:
                    session_dwell[sid] = float(dwell)
                except (ValueError, TypeError):
                    pass

    # Historical return rate per tried-on product, from this cohort's own orders.
    product_return_rates: dict[str, float] = {}
    for pid, r in product_breakdown(c).items():
        if r["orders"]:
            product_return_rates[pid] = len(r["returned"]) / len(r["orders"])

    scored_orders: list[OrderReturnRisk] = []
    all_scores: list[float] = []

    for o in c.orders.values():
        sid = o.session_id
        uid = o.user_id or c.session_user.get(sid or "")
        score = 0.0
        factors: list[str] = []
        pid = c.order_product(o) or ""

        if o.is_bracketed:
            score += 40
            factors.append("bracketed_order")

        if sid in session_rec_size and sid in session_sel_size:
            if _normalize_size(session_rec_size[sid]) != _normalize_size(session_sel_size[sid]):
                score += 25
                factors.append("size_mismatch")

        if session_dwell.get(sid, 999) < 30:
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
                order_id=o.order_id,
                session_id=sid,
                risk_score=score,
                risk_factors=factors,
                product_id=pid or None,
            ))

    scored_orders.sort(key=lambda x: (-x.risk_score, x.order_id))
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
    week_start: str  # bucket start YYYY-MM-DD (kept for the frontend; may be day/week/month)
    bucket_end: Optional[str] = None  # last day in the bucket, clipped to the range
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
    weeks: list[TimeSeriesPoint]  # one point per bucket in [start, end], zero-filled
    granularity: str = "week"


@router.get("/time-series", response_model=TimeSeriesResponse)
async def get_time_series(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    shop: str = Depends(get_brand_shop),
    granularity: Optional[str] = Query(None, pattern=GRANULARITY_PATTERN, description="day|week|month; default by span"),
):
    start_d, end_d, _, _ = parse_range(start, end, 90)
    gran = granularity or default_granularity(start_d, end_d)
    key = _cache_key("time_series", start=start_d, end=end_d, shop=shop, granularity=gran)
    if key in _cache:
        return _cache[key]

    c, _events = load_cohort(shop, start_d, end_d)

    # Zero-filled: one entry per bucket in [start, end], clipped to the range.
    buckets = bucket_ranges(start_d, end_d, gran)
    week_data: dict[str, dict[str, Any]] = {
        b0.isoformat(): {
            "opens": 0, "tryons": 0, "atc": 0, "orders": 0, "buyers": set(),
            "returned": 0, "revenue": 0.0,
        }
        for b0, _ in buckets
    }

    def bucket_of(t: datetime) -> Optional[dict[str, Any]]:
        d = t.astimezone(timezone.utc).date()
        return week_data.get(max(_period_start(d, gran), start_d).isoformat())

    # A session lives in the bucket of its first try-on, and so does everything it went on
    # to do. That makes each bucket's rates sessions-over-sessions for the same sessions,
    # and makes the buckets add up to the /metrics totals for the same range.
    for sid, t in c.opens.items():
        w = bucket_of(t)
        if w is not None:
            w["opens"] += 1
    for sid, anchor in c.anchors.items():
        w = bucket_of(anchor)
        if w is None:
            continue
        w["tryons"] += 1
        if sid in c.atc:
            w["atc"] += 1
    for o in c.orders.values():
        w = bucket_of(c.anchors[o.session_id])
        if w is None:
            continue
        w["orders"] += 1
        w["buyers"].add(o.session_id)
        w["revenue"] += o.amount
        if o.order_id in c.returns:
            w["returned"] += 1

    weeks_out: list[TimeSeriesPoint] = []
    for b0, b1 in buckets:
        week_start = b0.isoformat()
        w = week_data[week_start]
        tryons = w["tryons"]
        orders = w["orders"]
        weeks_out.append(TimeSeriesPoint(
            week_start=week_start,
            bucket_end=b1.isoformat(),
            widget_opens=w["opens"],
            tryons=tryons,
            add_to_carts=w["atc"],
            purchases=orders,
            returns=w["returned"],
            revenue=round(w["revenue"], 2),
            conversion_rate=round(len(w["buyers"]) / tryons * 100, 2) if tryons else None,
            atc_rate=round(w["atc"] / tryons * 100, 2) if tryons else None,
            return_rate=round(w["returned"] / orders * 100, 2) if orders else None,
        ))

    result = TimeSeriesResponse(weeks=weeks_out, granularity=gran)
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
    shop: str = Depends(get_brand_shop),
):
    """
    Shows the relationship between fit recommendation accuracy and purchase/return outcomes.
    Groups sessions by size deviation (accepted, sized up, sized down) and shows
    purchase rate and return rate for each group.
    """
    key = _cache_key("fit_purchase_correlation", start=start, end=end, shop=shop)
    if key in _cache:
        return _cache[key]

    start_d, end_d, start_ts, end_ts = parse_range(start, end, 90)

    events = fetch_events("event_type,session_id,product_id,event_data,created_at", shop, start_ts, end_ts)

    session_rec, session_sel = chosen_sizes(events)
    session_purchased: set[str] = set()
    session_returned: set[str] = set()

    for e in events:
        sid = e.get("session_id")
        if not sid:
            continue
        if e.get("event_type") == "purchase":
            session_purchased.add(sid)
        elif e.get("event_type") == "return":
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
