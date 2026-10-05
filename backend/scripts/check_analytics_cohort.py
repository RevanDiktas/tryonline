"""
Offline check for the dashboard's metric definitions (app/services/analytics_cohort.py):
one definition per metric, distinct sessions and orders, try-on cohort only, 30-day window.

  1. build_cohort on a hand-written store: every count and rate is checked by hand.
  2. The routes agree with each other: /metrics totals == sum of /time-series buckets ==
     sum of /metrics-by-product rows == /cohort-comparison == /device-metrics.
  3. Store orders that never touched the widget stay out of every try-on number and land
     in the baseline.

Same harness as check_analytics_ranges.py: in-process TestClient, FAKE Supabase client,
throwaway HS256 secret. No server, no network, no production data.

    cd backend && python3 scripts/check_analytics_cohort.py
"""
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone

TEST_SECRET = "local-test-secret-not-a-real-key-0123456789"
os.environ["SUPABASE_URL"] = "http://supabase.invalid"
os.environ["SUPABASE_SERVICE_KEY"] = "fake-service-key"
os.environ["SUPABASE_JWT_SECRET"] = TEST_SECRET
os.environ["DEBUG"] = "false"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import jwt  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api import deps, rate_limit  # noqa: E402
from app.api.routes import analytics  # noqa: E402
from app.main import app  # noqa: E402
from app.services.analytics_cohort import build_cohort, chosen_sizes, parse_ts  # noqa: E402
from app.services.supabase import supabase_service  # noqa: E402

USER_A = "aaaaaaaa-0000-0000-0000-000000000001"
SHOP = "la-fam-ams.myshopify.com"
OTHER_SHOP = "someone-else.myshopify.com"
START, END = date(2026, 9, 1), date(2026, 9, 30)
IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X)"
MAC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

failures = 0
_seq = 0


def check(name, cond, detail=""):
    global failures
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        failures += 1


def ev(event_type, day, hour=12, minute=0, session_id=None, shop=SHOP, **extra):
    global _seq
    _seq += 1
    ts = datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute, tzinfo=timezone.utc)
    return {"id": _seq, "event_type": event_type, "shop_domain": shop, "session_id": session_id,
            "created_at": ts.isoformat(), "event_data": extra.pop("event_data", {}), **extra}


def order(oid, amount, day, hour=12, session_id=None, **extra):
    data = {"order_id": oid, "amount": amount, "currency": "EUR", **extra.pop("event_data", {})}
    return ev("purchase", day, hour=hour, session_id=session_id, event_data=data, **extra)


def refund(rid, oid, amount, day, session_id=None):
    return ev("return", day, session_id=session_id,
              event_data={"refund_id": rid, "order_id": oid, "amount_refunded": amount})


D = lambda n: date(2026, 9, n)  # noqa: E731

# --------------------------------------------------------------------------- the store
#
# Try-on sessions (all in September):
#   s1  iPhone  opens, tries "tee" twice (two tryon_started = ONE try-on), adds to cart
#               twice (ONE add-to-cart), buys order o1 (€100) 20 min later, bracketed.
#               o1 is refunded twice (r1 €40, r2 €60) = ONE return, €100 lost.
#   s2  Mac     opens, tries "tee" then "cap", adds "cap" to cart, never buys.
#   s3  iPhone  opens, tries "cap", buys o2 (€50) on day 29 after the try-on, and o3 (€30)
#               on day 31 after it: o3 is outside the 30-day window.
#   s4  Mac     opens, never tries on.
#   s5  Mac     tried on in AUGUST (before the range), buys o4 in September: not this cohort.
# Store orders with no session: o5 (€80, refunded r3), o6 (€120), o7 (€70, bracketed),
#   and o8 paid in October (outside the range, not baseline).
# Shopify retries: o1's purchase event arrives twice, and refund r1 arrives twice.
# Another shop's events must never leak in (the fake applies the shop filter).

EVENTS = [
    ev("widget_opened", D(3), 10, 0, "s1", user_id="u1", user_agent=IPHONE),
    ev("tryon_started", D(3), 10, 1, "s1", user_id="u1", user_agent=IPHONE, product_id="tee"),
    ev("size_recommended", D(3), 10, 1, "s1", product_id="tee", event_data={"size": "m"}),
    ev("size_selected", D(3), 10, 2, "s1", product_id="tee", event_data={"size": "s"}),
    ev("size_selected", D(3), 10, 3, "s1", product_id="tee", event_data={"size": "xl"}),
    ev("size_selected", D(3), 10, 4, "s1", product_id="tee", event_data={"size": "l"}),
    ev("tryon_started", D(3), 10, 5, "s1", user_id="u1", user_agent=IPHONE, product_id="tee"),
    ev("add_to_cart", D(3), 10, 6, "s1", product_id="tee", event_data={"size": "l"}),
    ev("add_to_cart", D(3), 10, 7, "s1", product_id="tee", event_data={"size": "l"}),
    ev("tryon_ended", D(3), 10, 8, "s1", event_data={"dwell_seconds": 25}),
    order("o1", 100, D(3), 10, "s1", product_id="tee", user_id="u1",
          event_data={"is_bracketed": True}, minute=21),
    order("o1", 100, D(3), 10, "s1", product_id="tee", user_id="u1",
          event_data={"is_bracketed": True}, minute=22),
    refund("r1", "o1", 40, D(10), "s1"),
    refund("r1", "o1", 40, D(10), "s1"),
    refund("r2", "o1", 60, D(12), "s1"),

    ev("widget_opened", D(5), 9, 0, "s2", user_id="u2", user_agent=MAC),
    ev("tryon_started", D(5), 9, 1, "s2", user_id="u2", user_agent=MAC, product_id="tee"),
    ev("tryon_started", D(5), 9, 3, "s2", user_id="u2", user_agent=MAC, product_id="cap"),
    ev("size_recommended", D(5), 9, 3, "s2", product_id="cap", event_data={"size": "l"}),
    ev("add_to_cart", D(5), 9, 4, "s2", product_id="cap", event_data={"size": "l"}),
    ev("tryon_ended", D(5), 9, 9, "s2", event_data={"dwell_seconds": 480}),

    ev("widget_opened", D(20), 8, 0, "s3", user_agent=IPHONE),
    ev("tryon_started", D(20), 8, 1, "s3", user_agent=IPHONE, product_id="cap"),
    order("o2", 50, date(2026, 10, 19), 8, "s3", product_id="cap"),   # day 29
    order("o3", 30, date(2026, 10, 21), 8, "s3", product_id="cap"),   # day 31: too late

    ev("widget_opened", D(21), 8, 0, "s4", user_agent=MAC),

    ev("tryon_started", date(2026, 8, 25), 8, 0, "s5", user_agent=MAC, product_id="tee"),
    order("o4", 999, D(2), 8, "s5", product_id="tee"),

    order("o5", 80, D(8)),
    refund("r3", "o5", 80, D(15)),
    order("o6", 120, D(9)),
    order("o7", 70, D(28), event_data={"is_bracketed": True}),
    order("o8", 60, date(2026, 10, 2)),

    ev("tryon_started", D(4), 8, 0, "x1", shop=OTHER_SHOP, product_id="tee"),
    order("x-o1", 5000, D(4), 9, "x1", shop=OTHER_SHOP),
]

# --------------------------------------------------------------------------- 1. build_cohort

start_dt = datetime.combine(START, datetime.min.time()).replace(tzinfo=timezone.utc)
end_dt = datetime.combine(END, datetime.max.time()).replace(tzinfo=timezone.utc)
own = [e for e in EVENTS if e["shop_domain"] == SHOP]
c = build_cohort(own, start_dt, end_dt)

check("try-ons = 3 distinct sessions (s1 tried twice, s5 tried in August)",
      c.tryons == 3 and set(c.anchors) == {"s1", "s2", "s3"}, str(sorted(c.anchors)))
check("widget opens = 4 distinct sessions", c.widget_opens == 4, str(c.widget_opens))
check("open -> try-on rate = 3/4", c.open_to_tryon_rate == 0.75, str(c.open_to_tryon_rate))
check("add to cart = 2 sessions (s1 clicked twice)", c.add_to_carts == 2, str(c.add_to_carts))
check("purchases = 2 orders: o1 once despite the retry, o2 on day 29; o3 (day 31), o4 and "
      "the store orders are out", set(c.orders) == {"o1", "o2"}, str(sorted(c.orders)))
check("revenue = 150", c.revenue == 150, str(c.revenue))
check("converting sessions = 2, purchase rate = 2/3",
      c.purchase_sessions == {"s1", "s3"} and abs(c.purchase_rate - 2 / 3) < 1e-9)
check("add-to-cart rate = 2/3", abs(c.atc_rate - 2 / 3) < 1e-9, str(c.atc_rate))
check("cart abandonment = 1/2 (s2 carted, never bought)", c.cart_abandonment_rate == 0.5,
      str(c.cart_abandonment_rate))
check("AOV = 75, revenue per try-on = 50", c.aov == 75 and c.revenue_per_tryon == 50)
check("returns = 1 order (two refunds, one delivered twice), 100 lost",
      c.returned == 1 and c.revenue_lost == 100 and c.returns["o1"].refund_ids == {"r1", "r2"},
      f"{c.returned} {c.revenue_lost}")
check("return rate = 1/2, bracket rate = 1/2", c.return_rate == 0.5 and c.bracket_rate == 0.5)
check("baseline = 3 store orders in range (o5 o6 o7), not o8 (October) or o4 (has a session)",
      set(c.baseline_orders) == {"o5", "o6", "o7"}, str(sorted(c.baseline_orders)))
check("baseline: revenue 270, AOV 90, return rate 1/3, bracket rate 1/3",
      c.baseline_revenue == 270 and c.baseline_aov == 90
      and abs(c.baseline_return_rate - 1 / 3) < 1e-9 and abs(c.baseline_bracket_rate - 1 / 3) < 1e-9)
check("signed-in shoppers in the cohort = 2", c.users == {"u1", "u2"}, str(c.users))
check("s2 tried tee then cap, in that order", c.session_products["s2"] == ["tee", "cap"])

rec, chosen = chosen_sizes(own)
check("chosen size: s1 clicked S, XL, L then carted L -> one choice, L",
      chosen.get("s1") == "l" and rec.get("s1") == "m", f"{rec} {chosen}")
check("parse_ts orders a trimmed fraction correctly (string compare would not)",
      parse_ts("2026-09-03T10:00:00.5+00:00") < parse_ts("2026-09-03T10:00:00.75+00:00")
      and parse_ts("2026-09-03T10:00:00+00:00") < parse_ts("2026-09-03T10:00:00.1+00:00"))

# window edges
edge = [
    ev("tryon_started", D(1), 0, 0, "e1", product_id="tee"),
    order("in", 10, date(2026, 10, 1), 0, "e1"),                # exactly 30 days later
    order("out", 10, date(2026, 10, 1), 1, "e1"),               # 30 days + 1 hour
    order("before", 10, date(2026, 8, 31), 23, "e1"),           # before the try-on
]
ce = build_cohort(edge, start_dt, end_dt)
check("attribution window: exactly 30 days counts, 30 days + 1h and before-the-try-on do not",
      set(ce.orders) == {"in"}, str(sorted(ce.orders)))

# --------------------------------------------------------------------------- fake supabase


class _Result:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, db, table):
        self.db, self.table, self.filters = db, table, []
        self.orders, self.offset, self.limit_n = [], 0, None

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self.filters.append(("eq", col, val))
        return self

    def gte(self, col, val):
        self.filters.append(("gte", col, val))
        return self

    def lte(self, col, val):
        self.filters.append(("lte", col, val))
        return self

    def in_(self, col, vals):
        self.filters.append(("in", col, list(vals)))
        return self

    def limit(self, n, *_a, **_k):
        self.limit_n = n
        return self

    def order(self, col, desc=False, **_k):
        self.orders.append(col)
        return self

    def range(self, start, end, *_a):
        self.offset, self.limit_n = start, end - start + 1
        return self

    def execute(self):
        out = []
        for row in self.db.tables.get(self.table, []):
            ok = True
            for op, col, val in self.filters:
                v = row.get(col)
                if (op == "eq" and v != val) or (op == "in" and v not in val) \
                        or (op == "gte" and (v or "") < val) or (op == "lte" and (v or "") > val):
                    ok = False
                    break
            if ok:
                out.append(dict(row))
        for col in reversed(self.orders):
            out.sort(key=lambda row: str(row.get(col) or ""))
        n = min(self.limit_n or 1000, 1000)
        return _Result(out[self.offset:self.offset + n])


class FakeAuth:
    def get_user(self, _token):
        raise RuntimeError("fake auth: token rejected")


class FakeClient:
    def __init__(self):
        self.auth = FakeAuth()
        self.tables = {
            "brands": [{"id": "brand-a", "user_id": USER_A, "shopify_domain": SHOP}],
            "analytics_events": [{**e, "id": f"e{e['id']:07d}"} for e in EVENTS],
            "fit_passports": [],
        }

    def table(self, name):
        return FakeQuery(self, name)


supabase_service.client = FakeClient()
client = TestClient(app)
HEADERS = {"Authorization": "Bearer " + jwt.encode(
    {"sub": USER_A, "aud": "authenticated", "exp": int(time.time()) + 3600}, TEST_SECRET, algorithm="HS256")}
RANGE = {"start": START.isoformat(), "end": END.isoformat()}


def get(path, **params):
    analytics.clear_caches()
    deps._brand_scope_cache.clear()
    rate_limit._storage.reset()
    r = client.get(f"/api/analytics/{path}", params={**RANGE, **params}, headers=HEADERS)
    assert r.status_code == 200, (path, r.status_code, r.text[:300])
    return r.json()


# --------------------------------------------------------------------------- 2. routes agree

m = get("metrics")
check("/metrics: 4 opens, 3 try-ons, 2 add-to-carts, 2 purchases, 2 converting sessions",
      (m["widget_opens"], m["tryons_started"], m["add_to_carts"], m["purchases"], m["purchase_sessions"])
      == (4, 3, 2, 2, 2), str(m))
check("/metrics: revenue 150, AOV 75, purchase rate 0.6667, ATC rate 0.6667",
      (m["revenue_attributed"], m["aov_tryon"], m["tryon_purchase_rate"], m["tryon_atc_rate"])
      == (150.0, 75.0, 0.6667, 0.6667), str(m))
check("/metrics: 1 return, return rate 0.5, 100 lost, 1 bracket order",
      (m["returns"], m["return_rate"], m["revenue_lost_to_returns"], m["bracket_orders"], m["bracket_rate"])
      == (1, 0.5, 100.0, 1, 0.5), str(m))
check("/metrics: no rate above 100%",
      all((m[k] or 0) <= 1 for k in ("tryon_atc_rate", "tryon_purchase_rate", "open_to_tryon_rate",
                                     "cart_abandonment_rate", "return_rate", "bracket_rate")))
check("/metrics: avg time to purchase = (0.33h + 29 days) / 2", m["avg_time_to_purchase_hours"] == 348.16,
      str(m["avg_time_to_purchase_hours"]))
check("/metrics: same-session purchases = 1 of 2", m["same_session_purchase_rate"] == 0.5)

for gran in ("day", "week", "month"):
    ts = get("time-series", granularity=gran)["weeks"]
    tot = {k: sum(p[k] for p in ts) for k in ("widget_opens", "tryons", "add_to_carts", "purchases", "returns")}
    rev = round(sum(p["revenue"] for p in ts), 2)
    check(f"/time-series ({gran}) buckets add up to the /metrics totals",
          (tot["widget_opens"], tot["tryons"], tot["add_to_carts"], tot["purchases"], tot["returns"], rev)
          == (m["widget_opens"], m["tryons_started"], m["add_to_carts"], m["purchases"], m["returns"],
              m["revenue_attributed"]), f"{tot} rev={rev}")
    check(f"/time-series ({gran}): no bucket converts above 100%",
          all((p["conversion_rate"] or 0) <= 100 and (p["atc_rate"] or 0) <= 100 for p in ts))

bp = get("metrics-by-product")["products"]
rows = {p["product_id"]: p for p in bp}
check("/metrics-by-product: tee = 2 try-on sessions, 1 ATC, 1 order €100",
      (rows["tee"]["tryons_started"], rows["tee"]["add_to_carts"], rows["tee"]["purchases"],
       rows["tee"]["revenue_attributed"]) == (2, 1, 1, 100.0), str(rows.get("tee")))
check("/metrics-by-product: cap = 2 try-on sessions, 1 ATC, 1 order €50",
      (rows["cap"]["tryons_started"], rows["cap"]["add_to_carts"], rows["cap"]["purchases"],
       rows["cap"]["revenue_attributed"]) == (2, 1, 1, 50.0), str(rows.get("cap")))
check("/metrics-by-product rows add up to /metrics orders and revenue",
      sum(p["purchases"] for p in bp) == m["purchases"]
      and round(sum(p["revenue_attributed"] for p in bp), 2) == m["revenue_attributed"])
one = get("metrics-by-product", product_id="cap")["products"]
check("/metrics-by-product?product_id=cap -> the same cap row", one == [rows["cap"]], str(one))

dv = {d["device_type"]: d for d in get("device-metrics")["devices"]}
check("/device-metrics: mobile 2 try-ons / 2 orders, desktop 1 try-on / 0 orders, no 'unknown'",
      set(dv) == {"mobile", "desktop"}
      and (dv["mobile"]["tryons"], dv["mobile"]["purchases"], dv["mobile"]["conversion_rate"]) == (2, 2, 1.0)
      and (dv["desktop"]["tryons"], dv["desktop"]["purchases"], dv["desktop"]["add_to_carts"]) == (1, 0, 1),
      str(dv))
check("/device-metrics adds up to /metrics",
      sum(d["tryons"] for d in dv.values()) == m["tryons_started"]
      and sum(d["purchases"] for d in dv.values()) == m["purchases"])

cc = get("cohort-comparison")
check("/cohort-comparison try-on side == /metrics",
      (cc["tryon_sessions"], cc["tryon_purchases"], cc["tryon_returns"], cc["tryon_revenue"], cc["tryon_aov"],
       cc["tryon_conversion_rate"], cc["tryon_return_rate"], cc["tryon_bracket_rate"])
      == (m["tryons_started"], m["purchases"], m["returns"], m["revenue_attributed"], m["aov_tryon"],
          m["tryon_purchase_rate"], m["return_rate"], m["bracket_rate"]), str(cc))
check("/cohort-comparison baseline: 3 orders, €270, AOV 90, 1 return (0.3333), bracket 0.3333",
      (cc["baseline_orders"], cc["baseline_revenue"], cc["baseline_aov"], cc["baseline_returns"],
       cc["baseline_return_rate"], cc["baseline_bracket_rate"]) == (3, 270.0, 90.0, 1, 0.3333, 0.3333), str(cc))
check("/cohort-comparison: 2 try-on orders is too few to call a lift (comparable=false)",
      cc["comparable"] is False and cc["min_orders_for_comparison"] == 20)

ar = get("at-risk-products", min_tryons=2, conversion_threshold=0.9)["products"]
check("/at-risk-products: sessions over sessions (tee 1/2, cap 1/2)",
      {p["product_id"]: (p["tryons"], p["purchases"], p["conversion"]) for p in ar}
      == {"tee": (2, 1, 0.5), "cap": (2, 1, 0.5)}, str(ar))

# --------------------------------------------------------------------------- 3. store-wide

rm = get("return-metrics")
check("/return-metrics is store-wide: 5 orders paid in range (o1 once, o4 o5 o6 o7), 2 returned",
      (rm["scope"], rm["total_purchases"], rm["total_returns"], rm["return_rate"], rm["revenue_lost"])
      == ("all_store_orders", 5, 2, 0.4, 180.0), str({k: rm[k] for k in rm if k != "sku_breakdown"}))
check("/return-metrics: avg days to return = (7 + 7) / 2",
      rm["avg_days_to_return"] is not None and abs(rm["avg_days_to_return"] - 7.0) < 0.2,
      str(rm["avg_days_to_return"]))

fm = get("fit-metrics")
check("/fit-metrics: 'selected' counts one choice per session, not every click",
      fm["size_distribution_selected"] == {"L": 2} and fm["size_distribution_recommended"] == {"M": 1, "L": 1},
      f"{fm['size_distribution_selected']} {fm['size_distribution_recommended']}")
check("/fit-metrics: s1 sized up (M -> L), s2 accepted: size-up rate 1/2", fm["size_up_rate"] == 0.5,
      str(fm["size_up_rate"]))

dw = get("dwell-metrics")
check("/dwell-metrics histogram: 25s -> '20 to 30s', 480s -> 'Over 60s', sums to the session count",
      {b["label"]: b["sessions"] for b in dw["histogram"]}
      == {"0 to 10s": 0, "10 to 20s": 0, "20 to 30s": 1, "30 to 60s": 0, "Over 60s": 1}
      and sum(b["sessions"] for b in dw["histogram"]) == dw["total_sessions"], str(dw))

check("XL and XXL are different sizes (a size-up from XL to XXL is seen)",
      analytics._size_to_ordinal("xxl") > analytics._size_to_ordinal("xl") > analytics._size_to_ordinal("l")
      and analytics._size_to_ordinal("xs") > analytics._size_to_ordinal("xxs"))

print(f"\n{'ALL CHECKS PASSED' if not failures else f'{failures} CHECK(S) FAILED'}")
sys.exit(1 if failures else 0)
