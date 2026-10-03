"""
Offline check: brand dashboard analytics are scoped to the caller's own Shopify store.

Runs the FastAPI app in-process (TestClient) against a FAKE Supabase client, so it needs
no server, makes no network calls and never touches production. Tokens are minted with a
throwaway HS256 secret that only exists inside this process.

    cd backend && python3 scripts/check_analytics_scoping.py

Exits non-zero on the first failed check.
"""
import os
import sys
import time
from datetime import datetime, timedelta, timezone

# Must be set before app.config is imported (get_settings is cached).
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
from app.services.supabase import supabase_service  # noqa: E402

USER_A = "aaaaaaaa-0000-0000-0000-000000000001"   # owns shop A
USER_B = "bbbbbbbb-0000-0000-0000-000000000002"   # owns shop B
USER_SHOPPER = "cccccccc-0000-0000-0000-000000000003"  # no brand row
USER_NO_STORE = "dddddddd-0000-0000-0000-000000000004"  # brand without shopify_domain
SHOP_A = "la-fam-ams.myshopify.com"
SHOP_B = "ph2360-eq.myshopify.com"

TODAY = datetime.now(timezone.utc).date()
NOW_ISO = datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# --------------------------------------------------------------------------- fake supabase

class _Result:
    def __init__(self, data):
        self.data = data


MAX_ROWS = 1000  # like Supabase's PostgREST max-rows: every response is silently capped


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
        self.db.log.append((self.table, list(self.filters)))
        rows = self.db.tables.get(self.table, [])
        out = []
        for row in rows:
            ok = True
            for op, col, val in self.filters:
                v = row.get(col)
                if op == "eq" and v != val:
                    ok = False
                elif op == "in" and v not in val:
                    ok = False
                elif op == "gte" and (v or "") < val:
                    ok = False
                elif op == "lte" and (v or "") > val:
                    ok = False
            if ok:
                out.append(dict(row))
        for col in reversed(self.orders):
            out.sort(key=lambda row: str(row.get(col) or ""))
        n = min(self.limit_n or MAX_ROWS, MAX_ROWS)
        return _Result(out[self.offset:self.offset + n])


class FakeAuth:
    def get_user(self, _token):
        raise RuntimeError("fake auth: token rejected")


class FakeClient:
    def __init__(self):
        self.auth = FakeAuth()
        self.log = []
        self.tables = {
            "brands": [
                {"id": "brand-a", "user_id": USER_A, "shopify_domain": SHOP_A},
                {"id": "brand-b", "user_id": USER_B, "shopify_domain": SHOP_B},
                {"id": "brand-x", "user_id": USER_NO_STORE, "shopify_domain": None},
            ],
            "analytics_events": [
                *[{"id": f"ea{i}", "event_type": "widget_opened", "session_id": f"a{i}",
                   "shop_domain": SHOP_A, "created_at": NOW_ISO, "event_data": {}} for i in range(3)],
                *[{"id": f"eb{i}", "event_type": "widget_opened", "session_id": f"b{i}",
                   "shop_domain": SHOP_B, "created_at": NOW_ISO, "event_data": {}} for i in range(7)],
            ],
            "fit_passports": [],
        }

    def table(self, name):
        return FakeQuery(self, name)


fake = FakeClient()
supabase_service.client = fake


def token(user_id, secret=TEST_SECRET, exp_s=600):
    return jwt.encode(
        {"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + exp_s},
        secret,
        algorithm="HS256",
    )


def reset():
    analytics._cache.clear()
    deps._brand_scope_cache.clear()
    rate_limit._storage.reset()
    fake.log.clear()


client = TestClient(app)
ROUTES = [
    "/api/analytics/metrics", "/api/analytics/fit-metrics", "/api/analytics/velocity",
    "/api/analytics/at-risk-products", "/api/analytics/exploration-trend",
    "/api/analytics/size-stress", "/api/analytics/regional-size",
    "/api/analytics/metrics-by-product", "/api/analytics/dwell-metrics",
    "/api/analytics/device-metrics", "/api/analytics/fit-confidence-by-product",
    "/api/analytics/repeat-visitors", "/api/analytics/body-shape-insights",
    "/api/analytics/return-metrics", "/api/analytics/cohort-comparison",
    "/api/analytics/return-risk", "/api/analytics/time-series",
    "/api/analytics/fit-purchase-correlation",
]
RANGE = {"start": (TODAY - timedelta(days=29)).isoformat(), "end": TODAY.isoformat()}

failures = 0


def check(name, cond, detail=""):
    global failures
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        failures += 1


def get(path, user=None, raw_token=None, **params):
    headers = {}
    if raw_token is not None:
        headers["Authorization"] = f"Bearer {raw_token}"
    elif user is not None:
        headers["Authorization"] = f"Bearer {token(user)}"
    return client.get(path, params=params, headers=headers)


# --------------------------------------------------------------------------- checks

reset()
r = get("/api/analytics/metrics", **RANGE)
check("no token -> 401", r.status_code == 401, r.text)

r = get("/api/analytics/metrics", raw_token="garbage.token.value", **RANGE)
check("garbage token -> 401", r.status_code == 401, r.text)

r = get("/api/analytics/metrics", raw_token=token(USER_A, secret="some-other-secret"), **RANGE)
check("token signed with wrong secret -> 401", r.status_code == 401, r.text)

r = get("/api/analytics/metrics", raw_token=token(USER_A, exp_s=-60), **RANGE)
check("expired token -> 401", r.status_code == 401, r.text)

r = get("/api/analytics/metrics", user=USER_A, shop=SHOP_B, **RANGE)
check("brand A token + shop=B -> 403", r.status_code == 403, r.text)

r = get("/api/analytics/metrics", user=USER_SHOPPER, **RANGE)
check("user with no brand -> 403", r.status_code == 403, r.text)

r = get("/api/analytics/metrics", user=USER_NO_STORE, **RANGE)
check("brand without shopify_domain -> 403", r.status_code == 403, r.text)

reset()
r = get("/api/analytics/metrics", user=USER_A, **RANGE)
check("brand A, no shop -> 200", r.status_code == 200, r.text)
check("brand A, no shop -> only A's events (3 opens, not 10)",
      r.status_code == 200 and r.json().get("widget_opens") == 3, r.text)

reset()
r = get("/api/analytics/metrics", user=USER_A, shop="", **RANGE)
check("brand A, shop='' -> A's data", r.status_code == 200 and r.json().get("widget_opens") == 3, r.text)

for variant in ("https://LA-FAM-AMS.myshopify.com/", "la-fam-ams", " La-Fam-Ams.MyShopify.com "):
    reset()
    r = get("/api/analytics/metrics", user=USER_A, shop=variant, **RANGE)
    check(f"brand A, shop={variant!r} normalises -> 200", r.status_code == 200, r.text)

r = get("/api/analytics/metrics", user=USER_A, start="2026-13-01", end=TODAY.isoformat())
check("bad date -> 400", r.status_code == 400, r.text)
r = get("/api/analytics/metrics", user=USER_A, start="yesterday")
check("non-ISO date -> 400", r.status_code == 400, r.text)
r = get("/api/analytics/metrics", user=USER_A, start=TODAY.isoformat(),
        end=(TODAY - timedelta(days=1)).isoformat())
check("start > end -> 400", r.status_code == 400, r.text)
r = get("/api/analytics/metrics", user=USER_A, start=(TODAY - timedelta(days=366)).isoformat(),
        end=TODAY.isoformat())
check("span 367 days -> 400", r.status_code == 400, r.text)
reset()
r = get("/api/analytics/metrics", user=USER_A, start=(TODAY - timedelta(days=365)).isoformat(),
        end=TODAY.isoformat())
check("span 366 days -> 200", r.status_code == 200, r.text)

# Every dashboard route: 401 without a token; with A's token 200, and every analytics_events
# query it ran carried shop_domain == A.
reset()
for path in ROUTES:
    r = get(path, **RANGE)
    check(f"{path} no token -> 401", r.status_code == 401, r.text)
reset()
for path in ROUTES:
    fake.log.clear()
    r = get(path, user=USER_A, **RANGE)
    ev_queries = [f for t, f in fake.log if t == "analytics_events"]
    scoped = bool(ev_queries) and all(("eq", "shop_domain", SHOP_A) in f for f in ev_queries)
    check(f"{path} -> 200, every events query scoped to A", r.status_code == 200 and scoped,
          f"status={r.status_code} queries={ev_queries}")
    r = get(path, user=USER_A, shop=SHOP_B, **RANGE)
    check(f"{path} shop=B -> 403", r.status_code == 403, r.text)

# Brand lookup is cached: one dashboard load (18 calls) = one brands query.
reset()
for path in ROUTES:
    get(path, user=USER_A, **RANGE)
brand_queries = sum(1 for t, _ in fake.log if t == "brands")
check("18 calls -> 1 brands lookup (60s cache)", brand_queries == 1, f"brands queries={brand_queries}")

# /debug: auth first, then 404 while DEBUG is off.
r = get("/api/analytics/debug")
check("/debug no token -> 401", r.status_code == 401, r.text)
r = get("/api/analytics/debug", user=USER_A)
check("/debug with token, DEBUG off -> 404", r.status_code == 404, r.text)

print(f"\n{'ALL CHECKS PASSED' if not failures else f'{failures} CHECK(S) FAILED'}")
sys.exit(1 if failures else 0)
