"""
One definition per metric for the brand dashboard.

Every ROI number on the dashboard is derived from a `Cohort` built here, so a card, a
trend chart and a table can never disagree about what a "try-on" or a "purchase" is.

Definitions (all counts are DISTINCT, never raw event counts):

  try-on            a widget session with at least one `tryon_started` in [start, end].
                    The session's anchor is its first try-on in the range.
  widget open       a widget session with at least one `widget_opened` in [start, end].
  add to cart       a try-on session with an `add_to_cart` at or after its anchor and
                    within the attribution window.
  purchase          a distinct Shopify order (order_id) whose try-on session is in the
                    cohort, paid at or after the anchor and within the attribution
                    window. A store order with no try-on session is never a purchase
                    here; it belongs to the baseline.
  converting session a try-on session with at least one purchase.
  return            a purchase (order) with at least one refund, whenever the refund
                    came. Several refunds on one order are one return.
  baseline order    a distinct store order paid in [start, end] that did not come
                    through the widget at all (no try-on session on it).

Rates divide like by like: sessions by sessions, orders by orders.

    add-to-cart rate   = add-to-cart sessions / try-on sessions
    purchase rate      = converting sessions  / try-on sessions
    return rate        = returned orders      / orders
    bracket rate       = bracketed orders     / orders
    AOV                = revenue              / orders

Pure functions over event dicts: no database access, so they can be checked offline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

# A purchase counts for a try-on only if it is paid within this many days of it.
ATTRIBUTION_WINDOW_DAYS = 30

# Columns a cohort needs from analytics_events.
COHORT_COLUMNS = "id,event_type,session_id,user_id,product_id,user_agent,event_data,created_at"


def parse_ts(value: Any) -> Optional[datetime]:
    """Event timestamp as an aware UTC datetime, or None if unparseable. Timestamps are
    compared as datetimes, never as strings: PostgREST trims trailing zeros off the
    fraction, so ISO strings of different lengths do not sort chronologically."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value or not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _amount(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class Order:
    order_id: str
    session_id: Optional[str]
    user_id: Optional[str]
    product_id: str
    created: datetime
    amount: float
    is_bracketed: bool
    event: dict


@dataclass
class Refunds:
    """All refunds seen for one order, collapsed to one return."""
    order_id: str
    first: datetime
    amount: float = 0.0
    refund_ids: set = field(default_factory=set)
    events: list = field(default_factory=list)


@dataclass
class Cohort:
    start: datetime
    end: datetime
    window_days: int
    # try-on session -> first try-on in [start, end]
    anchors: dict[str, datetime] = field(default_factory=dict)
    # try-on session -> products tried in the range, in order of first try-on
    session_products: dict[str, list[str]] = field(default_factory=dict)
    session_user: dict[str, str] = field(default_factory=dict)
    session_user_agent: dict[str, str] = field(default_factory=dict)
    # widget session -> first widget_opened in [start, end]
    opens: dict[str, datetime] = field(default_factory=dict)
    # every widget session with any widget event in [start, end]
    active_sessions: set = field(default_factory=set)
    # try-on session -> first qualifying add_to_cart
    atc: dict[str, datetime] = field(default_factory=dict)
    # (session, product) pairs that were added to cart
    atc_products: set = field(default_factory=set)
    orders: dict[str, Order] = field(default_factory=dict)
    returns: dict[str, Refunds] = field(default_factory=dict)
    baseline_orders: dict[str, Order] = field(default_factory=dict)
    baseline_returns: dict[str, Refunds] = field(default_factory=dict)

    # ----- counts ---------------------------------------------------------------
    @property
    def tryons(self) -> int:
        return len(self.anchors)

    @property
    def widget_opens(self) -> int:
        return len(self.opens)

    @property
    def add_to_carts(self) -> int:
        return len(self.atc)

    @property
    def purchases(self) -> int:
        return len(self.orders)

    @property
    def purchase_sessions(self) -> set:
        return {o.session_id for o in self.orders.values() if o.session_id}

    @property
    def revenue(self) -> float:
        return sum(o.amount for o in self.orders.values())

    @property
    def returned(self) -> int:
        return len(self.returns)

    @property
    def revenue_lost(self) -> float:
        return sum(r.amount for r in self.returns.values())

    @property
    def bracket_orders(self) -> int:
        return sum(1 for o in self.orders.values() if o.is_bracketed)

    @property
    def users(self) -> set:
        return {self.session_user[s] for s in self.anchors if s in self.session_user}

    # ----- rates (None when the denominator is zero) -----------------------------
    @property
    def open_to_tryon_rate(self) -> Optional[float]:
        if not self.opens:
            return None
        return len(set(self.opens) & set(self.anchors)) / len(self.opens)

    @property
    def atc_rate(self) -> Optional[float]:
        return self.add_to_carts / self.tryons if self.tryons else None

    @property
    def purchase_rate(self) -> Optional[float]:
        return len(self.purchase_sessions) / self.tryons if self.tryons else None

    @property
    def cart_abandonment_rate(self) -> Optional[float]:
        if not self.atc:
            return None
        return 1 - len(set(self.atc) & self.purchase_sessions) / len(self.atc)

    @property
    def aov(self) -> Optional[float]:
        return self.revenue / self.purchases if self.purchases else None

    @property
    def revenue_per_tryon(self) -> Optional[float]:
        return self.revenue / self.tryons if self.tryons else None

    @property
    def return_rate(self) -> Optional[float]:
        return self.returned / self.purchases if self.purchases else None

    @property
    def bracket_rate(self) -> Optional[float]:
        return self.bracket_orders / self.purchases if self.purchases else None

    # ----- baseline ---------------------------------------------------------------
    @property
    def baseline_revenue(self) -> float:
        return sum(o.amount for o in self.baseline_orders.values())

    @property
    def baseline_aov(self) -> Optional[float]:
        n = len(self.baseline_orders)
        return self.baseline_revenue / n if n else None

    @property
    def baseline_return_rate(self) -> Optional[float]:
        n = len(self.baseline_orders)
        return len(self.baseline_returns) / n if n else None

    @property
    def baseline_bracket_rate(self) -> Optional[float]:
        n = len(self.baseline_orders)
        return sum(1 for o in self.baseline_orders.values() if o.is_bracketed) / n if n else None

    def order_product(self, order: Order) -> Optional[str]:
        """The tried-on product an order is credited to: the product stamped on the
        purchase when this session tried it, else the last product the session tried."""
        tried = self.session_products.get(order.session_id or "", [])
        if not tried:
            return None
        return order.product_id if order.product_id in tried else tried[-1]


def _order_key(e: dict) -> str:
    oid = (e.get("event_data") or {}).get("order_id")
    return str(oid) if oid else f"event:{e.get('id')}"


def build_cohort(
    events: Iterable[dict],
    start: datetime,
    end: datetime,
    window_days: int = ATTRIBUTION_WINDOW_DAYS,
) -> Cohort:
    """Build the try-on cohort for [start, end] from one shop's events.

    `events` should cover [start, end + window_days] so purchases that follow a late
    try-on are seen, plus every `return` since `start` so late refunds are seen. Events
    outside what a definition needs are ignored, so passing extra rows is harmless.
    """
    events = list(events)
    c = Cohort(start=start, end=end, window_days=window_days)
    window = timedelta(days=window_days)

    # Pass 1: who tried on, and who opened the widget, inside the range.
    tryon_rows: list[tuple[datetime, str, str]] = []
    for e in events:
        etype = e.get("event_type")
        sid = e.get("session_id")
        if not sid or etype in ("purchase", "return"):
            continue
        t = parse_ts(e.get("created_at"))
        if t is None or not (start <= t <= end):
            continue
        c.active_sessions.add(sid)
        if e.get("user_id") and sid not in c.session_user:
            c.session_user[sid] = str(e["user_id"])
        if e.get("user_agent") and sid not in c.session_user_agent:
            c.session_user_agent[sid] = e["user_agent"]
        if etype == "widget_opened":
            if sid not in c.opens or t < c.opens[sid]:
                c.opens[sid] = t
        elif etype == "tryon_started":
            if sid not in c.anchors or t < c.anchors[sid]:
                c.anchors[sid] = t
            tryon_rows.append((t, sid, (e.get("product_id") or "").strip()))

    for _t, sid, pid in sorted(tryon_rows, key=lambda r: r[0]):
        tried = c.session_products.setdefault(sid, [])
        if pid and pid not in tried:
            tried.append(pid)

    def attributed(sid: Optional[str], t: Optional[datetime]) -> bool:
        anchor = c.anchors.get(sid or "")
        return anchor is not None and t is not None and anchor <= t <= anchor + window

    # Pass 2: what those sessions went on to do.
    refund_events: list[dict] = []
    for e in events:
        etype = e.get("event_type")
        sid = e.get("session_id")
        t = parse_ts(e.get("created_at"))
        if etype == "add_to_cart":
            if attributed(sid, t):
                if sid not in c.atc or t < c.atc[sid]:
                    c.atc[sid] = t
                pid = (e.get("product_id") or "").strip()
                if pid:
                    c.atc_products.add((sid, pid))
        elif etype == "purchase":
            if t is None:
                continue
            ed = e.get("event_data") or {}
            key = _order_key(e)
            order = Order(
                order_id=key,
                session_id=sid,
                user_id=str(e["user_id"]) if e.get("user_id") else None,
                product_id=(e.get("product_id") or "").strip(),
                created=t,
                amount=_amount(ed.get("amount")),
                is_bracketed=bool(ed.get("is_bracketed")),
                event=e,
            )
            if attributed(sid, t):
                c.orders.setdefault(key, order)
            elif not sid and start <= t <= end:
                c.baseline_orders.setdefault(key, order)
        elif etype == "return":
            refund_events.append(e)

    # Pass 3: refunds, joined to their order and counted once per order.
    seen_refunds: set[str] = set()
    for e in refund_events:
        ed = e.get("event_data") or {}
        oid = str(ed.get("order_id") or "")
        if oid in c.orders:
            bucket = c.returns
        elif oid in c.baseline_orders:
            bucket = c.baseline_returns
        else:
            continue
        refund_key = str(ed.get("refund_id") or f"event:{e.get('id')}")
        if refund_key in seen_refunds:
            continue
        seen_refunds.add(refund_key)
        t = parse_ts(e.get("created_at")) or end
        r = bucket.get(oid)
        if r is None:
            r = bucket[oid] = Refunds(order_id=oid, first=t)
        r.first = min(r.first, t)
        r.amount += _amount(ed.get("amount_refunded"))
        r.refund_ids.add(refund_key)
        r.events.append(e)

    return c


def _clean_size(raw: Any) -> str:
    return str(raw).strip() if raw is not None and raw != "" else ""


def chosen_sizes(events: Iterable[dict], by_product: bool = False) -> tuple[dict, dict]:
    """(recommended, chosen) size per widget session, one of each per session.

      recommended  the latest `size_recommended` in the session.
      chosen       the size the shopper added to cart; if they never did, the last size
                   they selected. Clicking through five sizes is one choice, not five.

    Keys are session ids, or (session id, product id) pairs when `by_product` is set.
    """
    recommended: dict = {}
    selected: dict = {}
    carted: dict = {}
    rows = sorted(
        (e for e in events if e.get("session_id")),
        key=lambda e: parse_ts(e.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc),
    )
    for e in rows:
        size = _clean_size((e.get("event_data") or {}).get("size"))
        if not size:
            continue
        sid = e["session_id"]
        if by_product:
            pid = (e.get("product_id") or "").strip()
            if not pid:
                continue
            key: Any = (sid, pid)
        else:
            key = sid
        etype = e.get("event_type")
        if etype == "size_recommended":
            recommended[key] = size
        elif etype == "size_selected":
            selected[key] = size
        elif etype == "add_to_cart":
            carted[key] = size
    return recommended, {**selected, **carted}
