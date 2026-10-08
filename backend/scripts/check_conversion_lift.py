"""Checks for the conversion comparison: the store beacon, the visitor tag on paid orders,
and the arithmetic. In-process, FAKE Supabase. No network.

    python3 scripts/check_conversion_lift.py
"""
import asyncio
import json
import os
import sys

os.environ.setdefault("SUPABASE_URL", "http://supabase.invalid")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test")
os.environ.setdefault("SUPABASE_ANON_KEY", "test")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.routes import analytics, events, webhooks  # noqa: E402
from app.services.supabase import supabase_service  # noqa: E402

failures = 0


def check(name, cond, detail=""):
    global failures
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        failures += 1


# ---- arithmetic ----
w, o, lift, ok = analytics.conversion_lift_numbers(visitors=1000, widget_visitors=200, widget_orders=30, other_orders=40)
check("rates: 30/200 and 40/800", abs(w - 0.15) < 1e-9 and abs(o - 0.05) < 1e-9, (w, o))
check("lift: 15% vs 5% is +200%", abs(lift - 2.0) < 1e-9, lift)
check("enough data on both sides is comparable", ok is True)
w, o, lift, ok = analytics.conversion_lift_numbers(1000, 200, 3, 40)
check("few widget orders: a rate, but not comparable", w is not None and ok is False)
w, o, lift, ok = analytics.conversion_lift_numbers(50, 0, 0, 5)
check("nobody used the widget: no widget rate, no lift", w is None and lift is None and ok is False, (w, lift))
w, o, lift, ok = analytics.conversion_lift_numbers(10, 25, 2, 1)
check("more users than visits recorded: no negative group", o is None and lift is None, (o, lift))
w, o, lift, ok = analytics.conversion_lift_numbers(400, 150, 25, 0)
check("no other orders: no lift (no dividing by zero)", lift is None and o == 0.0, (o, lift))

# ---- the visitor tag on a paid order ----
order = {"note_attributes": [{"name": "_tryon_visitor_id", "value": "v_abc12345"}, {"name": "gift", "value": "yes"}]}
check("order: visitor tag is read from the cart attributes", webhooks._get_visitor_id_from_order(order) == "v_abc12345")
check("order: no tag, no visitor", webhooks._get_visitor_id_from_order({"note_attributes": [{"name": "gift", "value": "x"}]}) is None)
check("order: missing attributes are fine", webhooks._get_visitor_id_from_order({}) is None)

# ---- the beacon ----
rows = []


class FakeQuery:
    def __init__(self):
        self.f = {}

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        self.f[col] = val
        return self

    def gte(self, *a):
        return self

    def limit(self, *a):
        return self

    def execute(self):
        hit = [r for r in rows if r["event_type"] == self.f.get("event_type") and r["shop_domain"] == self.f.get("shop_domain")
               and r["event_data"]["visitor_id"] == self.f.get("event_data->>visitor_id")]
        return type("R", (), {"data": hit})()


class FakeClient:
    def table(self, name):
        return FakeQuery()


async def fake_track_event(event_type, **kw):
    rows.append({"event_type": event_type, "shop_domain": kw.get("shop_domain"), "product_id": kw.get("product_id"),
                 "event_data": kw.get("event_data"), "ip_address": kw.get("ip_address")})
    return "id"

supabase_service.client = FakeClient()
supabase_service.track_event = fake_track_event
supabase_service.get_brand_by_shopify_domain = lambda shop: {"id": "b1"} if shop == "known.myshopify.com" else None

app = FastAPI()
app.state.limiter = events.limiter
app.include_router(events.router, prefix="/api/events")
client = TestClient(app)


def beacon(payload, content_type="text/plain;charset=UTF-8"):
    return client.post("/api/events/store-beacon", content=json.dumps(payload) if not isinstance(payload, str) else payload,
                       headers={"Content-Type": content_type})

r = beacon({"t": "visit", "shop": "known.myshopify.com", "vid": "v_abc12345", "product_id": "123"})
check("beacon: text/plain body is accepted (no CORS preflight needed)", r.status_code == 204 and len(rows) == 1, (r.status_code, rows))
check("beacon: stored as store_visit with the visitor id, no IP", rows and rows[0]["event_type"] == "store_visit"
      and rows[0]["event_data"] == {"visitor_id": "v_abc12345"} and rows[0]["ip_address"] is None, rows)
beacon({"t": "visit", "shop": "known.myshopify.com", "vid": "v_abc12345"})
check("beacon: the same visitor on the same day counts once", len(rows) == 1, len(rows))
beacon({"t": "used", "shop": "known.myshopify.com", "vid": "v_abc12345"})
check("beacon: 'used' is its own row", len(rows) == 2 and rows[1]["event_type"] == "store_widget_used", rows)
n = len(rows)
beacon({"t": "visit", "shop": "stranger.myshopify.com", "vid": "v_abc12345"})
check("beacon: unknown store is dropped", len(rows) == n)
beacon({"t": "visit", "shop": "known.myshopify.com", "vid": "x"})
beacon({"t": "visit", "shop": "known.myshopify.com", "vid": "bad id with spaces!"})
check("beacon: malformed visitor ids are dropped", len(rows) == n)
beacon({"t": "purchase", "shop": "known.myshopify.com", "vid": "v_abc12345"})
check("beacon: cannot write any other event type", len(rows) == n)
r = beacon("not json")
check("beacon: garbage still answers 204 and stores nothing", r.status_code == 204 and len(rows) == n)
r = beacon({"t": "visit", "shop": "known.myshopify.com", "vid": "v_" + "a" * 3000})
check("beacon: oversized body is dropped", r.status_code == 204 and len(rows) == n)

print(f"\n{'ALL CHECKS PASSED' if not failures else f'{failures} CHECK(S) FAILED'}")
sys.exit(1 if failures else 0)
