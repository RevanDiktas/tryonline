"""
Offline check for the dashboard date ranges (1D / 1W / 1M / 3M / 6M / 1Y):
  - >1000-row results are paged to completion (no silent PostgREST truncation)
  - /time-series and /exploration-trend: default granularity, zero-filled buckets, clipping
  - /velocity: 7d / 30d are trailing windows ending at `end`, whatever the selected range
  - /api/analytics rate limit: per client, 300/minute

Same harness as check_analytics_scoping.py: in-process TestClient, FAKE Supabase client,
throwaway HS256 secret. No server, no network, no production data.

    cd backend && python3 scripts/check_analytics_ranges.py
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
from app.services.supabase import supabase_service  # noqa: E402

USER_A = "aaaaaaaa-0000-0000-0000-000000000001"
SHOP_A = "la-fam-ams.myshopify.com"
END = date(2026, 10, 3)  # a Saturday, so week buckets are partial at both ends


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
        self.db.log.append((self.table, list(self.filters), self.offset))
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
        n = min(self.limit_n or self.db.max_rows, self.db.max_rows)
        return _Result(out[self.offset:self.offset + n])


class FakeAuth:
    def get_user(self, _token):
        raise RuntimeError("fake auth: token rejected")


class FakeClient:
    def __init__(self):
        self.auth = FakeAuth()
        self.log = []
        self.max_rows = 1000  # Supabase default PostgREST max-rows
        self.tables = {
            "brands": [{"id": "brand-a", "user_id": USER_A, "shopify_domain": SHOP_A}],
            "analytics_events": [],
            "fit_passports": [],
        }

    def table(self, name):
        return FakeQuery(self, name)


fake = FakeClient()
supabase_service.client = fake
client = TestClient(app)
failures = 0
_seq = 0


def ev(event_type, day, hour=12, **extra):
    global _seq
    _seq += 1
    ts = datetime.combine(day, datetime.min.time()).replace(hour=hour, tzinfo=timezone.utc)
    return {"id": f"e{_seq:07d}", "event_type": event_type, "shop_domain": SHOP_A,
            "session_id": extra.pop("session_id", f"s{_seq}"), "created_at": ts.isoformat(),
            "event_data": extra.pop("event_data", {}), **extra}


def set_events(rows):
    fake.tables["analytics_events"] = rows
    analytics.clear_caches()
    deps._brand_scope_cache.clear()
    rate_limit._storage.reset()
    fake.log.clear()


def check(name, cond, detail=""):
    global failures
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        failures += 1


HEADERS = {"Authorization": "Bearer " + jwt.encode(
    {"sub": USER_A, "aud": "authenticated", "exp": int(time.time()) + 3600}, TEST_SECRET, algorithm="HS256")}


def get(path, **params):
    return client.get(path, params=params, headers=HEADERS)


def span(days):
    return {"start": (END - timedelta(days=days - 1)).isoformat(), "end": END.isoformat()}


# --------------------------------------------------------------------------- 1. pagination

rows = [ev("widget_opened", END - timedelta(days=i % 300), hour=i % 24) for i in range(2500)]
set_events(rows)
r = get("/api/analytics/metrics", **span(366))
check("/metrics counts all 2500 events across pages (not 1000)",
      r.status_code == 200 and r.json()["widget_opens"] == 2500, r.text[:200])  # 2500 sessions
pages = [off for t, _, off in fake.log if t == "analytics_events"]
check("paged at offsets 0,1000,2000,2500 (empty page ends it)", pages == [0, 1000, 2000, 2500], str(pages))

fake.max_rows = 400  # a server cap below PAGE_SIZE must still not truncate
set_events(rows)
got = analytics.fetch_events("id", SHOP_A, "2000-01-01T00:00:00+00:00", "2100-01-01T00:00:00+00:00")
check("server max-rows 400 < page size: still all 2500 rows", len(got) == 2500, str(len(got)))
check("no duplicates or gaps across pages", len({g["id"] for g in got}) == 2500)
fake.max_rows = 1000

# --------------------------------------------------------------------------- 2. buckets


def expected_buckets(start_d, end_d, gran):
    starts = []
    d = start_d
    while d <= end_d:
        if gran == "day":
            k = d
        elif gran == "week":
            k = max(d - timedelta(days=d.weekday()), start_d)
        else:
            k = max(d.replace(day=1), start_d)
        if not starts or starts[-1] != k:
            starts.append(k)
        d += timedelta(days=1)
    return [k.isoformat() for k in starts]


for days, want_gran in ((1, "day"), (7, "day"), (31, "day"), (92, "week"), (183, "week"), (366, "month")):
    rng = span(days)
    start_d = date.fromisoformat(rng["start"])
    # one try-on on the first day, one on the last day, nothing in between
    set_events([ev("tryon_started", start_d), ev("tryon_started", END, hour=23)])
    for path, list_key in (("/api/analytics/time-series", "weeks"),
                           ("/api/analytics/exploration-trend", "data")):
        r = get(path, **rng)
        ok = r.status_code == 200
        body = r.json() if ok else {}
        pts = body.get(list_key, [])
        want = expected_buckets(start_d, END, want_gran)
        label = f"{path.rsplit('/', 1)[1]} {days}d"
        check(f"{label}: granularity={want_gran}", body.get("granularity") == want_gran, str(body.get("granularity")))
        check(f"{label}: {len(want)} zero-filled buckets", [p["week_start"] for p in pts] == want,
              f"got {len(pts)}: {[p['week_start'] for p in pts][:4]}...")
        if pts:
            check(f"{label}: first bucket clipped to start", pts[0]["week_start"] == rng["start"])
            check(f"{label}: last bucket ends at end", pts[-1]["bucket_end"] == rng["end"])
            contiguous = all(
                date.fromisoformat(a["bucket_end"]) + timedelta(days=1) == date.fromisoformat(b["week_start"])
                for a, b in zip(pts, pts[1:]))
            check(f"{label}: buckets contiguous, no gaps/overlap", contiguous)
        if path.endswith("time-series") and pts:
            tryons = [p["tryons"] for p in pts]
            first_last_ok = (tryons[0] == 2) if len(pts) == 1 else (tryons[0] == 1 and tryons[-1] == 1)
            check(f"{label}: events land in first/last bucket, rest zero",
                  first_last_ok and sum(tryons) == 2, str(tryons[:5]))

set_events([])
r = get("/api/analytics/time-series", granularity="day", **span(366))
check("explicit granularity=day over 366d -> 366 buckets",
      r.status_code == 200 and len(r.json()["weeks"]) == 366 and r.json()["granularity"] == "day")
r = get("/api/analytics/time-series", granularity="hour", **span(7))
check("invalid granularity -> 422", r.status_code == 422, str(r.status_code))

# --------------------------------------------------------------------------- 3. velocity

# A purchase counts only for the try-on session that led to it (same definitions as
# /metrics): s-a and s-c each buy once; the store order with no session is not a try-on
# purchase; s-d's order comes 31 days after its try-on, outside the attribution window.
set_events([
    ev("tryon_started", END, session_id="s-a"),                                   # in 7d
    ev("tryon_started", END - timedelta(days=6), session_id="s-b"),               # in 7d
    ev("tryon_started", END - timedelta(days=7), session_id="s-c"),               # in 30d only
    ev("tryon_started", END - timedelta(days=29), session_id="s-d"),              # in 30d only
    ev("tryon_started", END - timedelta(days=30), session_id="s-e"),              # outside both
    ev("purchase", END, hour=13, session_id="s-a", event_data={"order_id": "o1", "amount": 50}),
    ev("purchase", END - timedelta(days=5), session_id="s-c", event_data={"order_id": "o2", "amount": 60}),
    ev("purchase", END - timedelta(days=2), session_id=None, event_data={"order_id": "o3", "amount": 70}),
    ev("purchase", END + timedelta(days=2), session_id="s-d", event_data={"order_id": "o4", "amount": 80}),
    ev("purchase", END - timedelta(days=3), session_id="s-e", event_data={"order_id": "o5", "amount": 90}),
])
for days in (1, 7, 31, 366):
    r = get("/api/analytics/velocity", **span(days))
    b = r.json() if r.status_code == 200 else {}
    check(f"velocity with {days}d range: tryons 7d=2 30d=4, try-on purchases 7d=1 30d=2",
          (b.get("tryon_velocity_7d"), b.get("tryon_velocity_30d"),
           b.get("purchase_velocity_7d"), b.get("purchase_velocity_30d")) == (2, 4, 1, 2), str(b))
    analytics.clear_caches()

# --------------------------------------------------------------------------- 4. rate limit

set_events([])
codes = [get("/api/analytics/return-risk").status_code for _ in range(18 * 16)]
check("16 dashboard loads (288 calls) in a minute -> no 429", 429 not in codes)
codes = [get("/api/analytics/return-risk").status_code for _ in range(13)]  # calls 289..301
check("call 300 allowed, call 301 -> 429", codes[-2] == 200 and codes[-1] == 429, str(codes[-3:]))
r = client.get("/api/analytics/return-risk", headers={**HEADERS, "X-Forwarded-For": "203.0.113.9, 10.0.0.1"})
check("another client (X-Forwarded-For first hop) has its own bucket", r.status_code == 200, str(r.status_code))
check("client_key uses the first X-Forwarded-For hop",
      rate_limit.client_key(type("R", (), {"headers": {"x-forwarded-for": " 198.51.100.7 , 10.0.0.1"},
                                          "client": None})()) == "198.51.100.7")

print(f"\n{'ALL CHECKS PASSED' if not failures else f'{failures} CHECK(S) FAILED'}")
sys.exit(1 if failures else 0)
