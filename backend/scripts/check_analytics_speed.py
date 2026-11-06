"""
One dashboard load fires ~20 analytics calls for the same range. They must share ONE scan of
the events table (not one each), and run side by side (not one after another). Fake Supabase
with 10,500 events and 50 ms per 1,000-row page, like a 3-month La Fam range.
    cd backend && python3 scripts/check_analytics_speed.py
"""
import os, sys, time, threading
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
TEST_SECRET = "local-test-secret-not-a-real-key-0123456789"
os.environ.update(SUPABASE_URL="http://supabase.invalid", SUPABASE_SERVICE_KEY="fake", SUPABASE_JWT_SECRET=TEST_SECRET, DEBUG="false")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import jwt
from fastapi.testclient import TestClient
from app.main import app
from app.api import deps, rate_limit
from app.api.routes import analytics
from app.services.supabase import supabase_service

SHOP, USER = "la-fam-ams.myshopify.com", "11111111-0000-0000-0000-000000000001"
PAGE_MS = 50
failures = 0
def check(name, cond, detail=""):
    global failures
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))
    failures += 0 if cond else 1

class R:
    def __init__(s, d, c=None): s.data, s.count = d, c
class Q:
    def __init__(s, db, t): s.db, s.t, s.f, s.off, s.lim, s.cnt = db, t, [], 0, None, None
    def select(s, *a, count=None, **k): s.cnt = count; return s
    def eq(s, c, v): s.f.append(("eq", c, v)); return s
    def gte(s, c, v): s.f.append(("gte", c, v)); return s
    def lte(s, c, v): s.f.append(("lte", c, v)); return s
    def in_(s, c, v): s.f.append(("in", c, list(v))); return s
    @property
    def not_(s): return s
    def limit(s, n, *a, **k): s.lim = n; return s
    def order(s, *a, **k): return s
    def range(s, a, b, *x): s.off, s.lim = a, b - a + 1; return s
    def execute(s):
        rows = s.db.tables.get(s.t, [])
        out = []
        for r in rows:
            ok = True
            for op, c, v in s.f:
                x = r.get(c)
                if op == "eq" and x != v: ok = False
                elif op == "gte" and (x is None or x < v): ok = False
                elif op == "lte" and (x is None or x > v): ok = False
                elif op == "in" and x in v: ok = False   # only used as not_.in_
            if ok: out.append(r)
        if s.t == "analytics_events" and s.cnt is None:
            with s.db.lock: s.db.pages += 1
            time.sleep(PAGE_MS / 1000)
        page = out[s.off:s.off + (s.lim or len(out))]
        return R([dict(r) for r in page], len(out))
class Auth:
    def get_user(s, t): raise RuntimeError("rejected")
class Fake:
    def __init__(s):
        s.auth, s.lock, s.pages = Auth(), threading.Lock(), 0
        s.tables = {"brands": [{"id": "b1", "user_id": USER, "shopify_domain": SHOP}], "analytics_events": [], "fit_passports": []}
    def table(s, n): return Q(s, n)

fake = Fake(); supabase_service.client = fake
END = datetime.now(timezone.utc).date() - timedelta(days=1)
rows = []
for i in range(10500):
    d = END - timedelta(days=i % 90)
    ts = datetime.combine(d, datetime.min.time()).replace(hour=i % 24, tzinfo=timezone.utc)
    et = ["widget_opened", "tryon_started", "size_finder_result", "purchase"][i % 4]
    rows.append({"id": f"e{i:06d}", "event_type": et, "shop_domain": SHOP, "session_id": f"s{i // 3}", "user_id": None,
                 "product_id": f"p{i % 20}", "user_agent": "x", "country": "NL", "city": "Amsterdam",
                 "created_at": ts.isoformat(), "event_data": {"amount": 80, "order_id": str(i)} if et == "purchase" else {}})
fake.tables["analytics_events"] = rows
analytics.clear_caches(); deps._brand_scope_cache.clear(); rate_limit._storage.reset()

client = TestClient(app)
H = {"Authorization": "Bearer " + jwt.encode({"sub": USER, "aud": "authenticated", "exp": int(time.time()) + 3600}, TEST_SECRET, algorithm="HS256")}
start = (END - timedelta(days=89)).isoformat(); end = END.isoformat()
P = {"start": start, "end": end, "shop": SHOP}
routes = ["metrics", "fit-metrics", "velocity", "at-risk-products", "exploration-trend", "size-stress", "regional-size",
          "metrics-by-product", "dwell-metrics", "device-metrics", "fit-confidence-by-product", "repeat-visitors",
          "body-shape-insights", "return-metrics", "cohort-comparison", "time-series", "fit-purchase-correlation",
          "size-finder", "conversion-lift"]
t0 = time.monotonic()
with ThreadPoolExecutor(max_workers=20) as ex:
    res = list(ex.map(lambda r: client.get(f"/api/analytics/{r}", params=P, headers=H), routes))
wall = time.monotonic() - t0
bad = [(r, x.status_code, x.text[:80]) for r, x in zip(routes, res) if x.status_code != 200]
check("all routes answer 200", not bad, str(bad))
# One scan of the cohort window (11 pages) that the plain window is cut from, plus the small
# late-returns scan. Before this: 210 pages (one scan per route).
check(f"one shared scan per load, not one per route (pages={fake.pages})", fake.pages <= 24, str(fake.pages))
budget = 24 * PAGE_MS / 1000 + 1.5
check(f"dashboard load in {wall:.2f}s (< {budget:.1f}s)", wall < budget)

# Second load for the same range: served from the scan cache, no pages at all.
fake.pages = 0; t0 = time.monotonic()
with ThreadPoolExecutor(max_workers=20) as ex:
    list(ex.map(lambda r: client.get(f"/api/analytics/{r}", params=P, headers=H), routes))
check(f"repeat load reads no pages ({fake.pages}) and takes {time.monotonic()-t0:.2f}s", fake.pages == 0)

# "Last month" works too.
m = client.get("/api/analytics/metrics", params={"start": (END - timedelta(days=30)).isoformat(), "end": end, "shop": SHOP}, headers=H)
check("last-month range answers", m.status_code == 200 and m.json().get("widget_opens", 0) > 0, m.text[:120])
print(f"\n{failures} failed" if failures else "\nall passed"); sys.exit(1 if failures else 0)
