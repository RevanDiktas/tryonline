"""
Every drape sent to RunPod carries an execution timeout, and a job still running after
DRAPE_STUCK_AFTER_S is cancelled on RunPod and failed here. (2026-11-13: three drapes ran
18-44 hours and held both workers.)    cd backend && python3 scripts/check_drape_timeout.py
"""
import asyncio, os, sys
from datetime import datetime, timedelta, timezone
os.environ.update(SUPABASE_URL="http://supabase.invalid", SUPABASE_SERVICE_KEY="fake", SUPABASE_JWT_SECRET="x" * 40,
                  RUNPOD_API_KEY="k", RUNPOD_DRAPING_ENDPOINT_ID="ep1", BACKEND_PUBLIC_URL="https://api.test")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import httpx
from app.services import drape_dispatcher as D
from app.services.supabase import supabase_service

failures = 0
def check(name, cond, detail=""):
    global failures
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))
    failures += 0 if cond else 1

now = datetime.now(timezone.utc)
class R:
    def __init__(s, d): s.data = d
class Q:
    def __init__(s, db, t): s.db, s.t, s.f, s.op, s.p = db, t, [], "select", None
    def select(s, *a, **k): return s
    def update(s, p): s.op, s.p = "update", p; return s
    def eq(s, c, v): s.f.append(("eq", c, v)); return s
    def lt(s, c, v): s.f.append(("lt", c, v)); return s
    def gte(s, c, v): s.f.append(("gte", c, v)); return s
    def in_(s, c, v): s.f.append(("in", c, list(v))); return s
    def limit(s, n): return s
    def execute(s):
        rows = s.db[s.t]
        hits = [r for r in rows if all(
            (op == "eq" and str(r.get(c)) == str(v)) or (op == "lt" and str(r.get(c)) < str(v)) or
            (op == "gte" and str(r.get(c)) >= str(v)) or (op == "in" and r.get(c) in v) for op, c, v in s.f)]
        if s.op == "update":
            for r in hits: r.update(s.p)
        return R([dict(r) for r in hits])
class Client:
    def __init__(s, db): s.db = db
    def table(s, n): return Q(s.db, n)

db = {"drape_jobs": [
    {"id": "j-stuck", "status": "running", "runpod_job_id": "rp-1", "dispatched_at": (now - timedelta(hours=44)).isoformat(), "garment_id": "g", "size": "xl"},
    {"id": "j-fresh", "status": "running", "runpod_job_id": "rp-2", "dispatched_at": (now - timedelta(minutes=5)).isoformat(), "garment_id": "g", "size": "m"},
    {"id": "j-done", "status": "completed", "runpod_job_id": "rp-3", "dispatched_at": (now - timedelta(days=3)).isoformat(), "garment_id": "g", "size": "s"},
]}
supabase_service.client = Client(db)
D.settings.runpod_api_key = "k"; D.settings.runpod_draping_endpoint_id = "ep1"

posts = []
def handler(req):
    posts.append((req.method, str(req.url), req.content))
    return httpx.Response(200, json={"id": "rp-new"})
client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

n = asyncio.run(D._reap_stuck(client))
by = {r["id"]: r for r in db["drape_jobs"]}
check("one stuck job found", n == 1)
check("stuck job cancelled on RunPod", any(u.endswith("/v2/ep1/cancel/rp-1") for _, u, _ in posts), str(posts))
check("stuck job failed here, with a reason", by["j-stuck"]["status"] == "failed" and "30 min" in by["j-stuck"]["error_message"])
check("a 5-minute-old job is left alone", by["j-fresh"]["status"] == "running")
check("finished jobs untouched", by["j-done"]["status"] == "completed")

# the /run payload carries RunPod's execution timeout
D._build_runpod_payload = lambda job: {"input": {"x": 1}}
db["drape_jobs"].append({"id": "j-new", "status": "dispatched", "attempts": 0, "max_attempts": 3})
posts.clear()
asyncio.run(D._dispatch_one(client, {"id": "j-new"}))
import json
sent = json.loads(posts[-1][2])
check("/run payload has policy.executionTimeout = 900 s", sent.get("policy", {}).get("executionTimeout") == 900_000, str(sent.get("policy")))
check("webhook still set", sent.get("webhook") == "https://api.test/api/draping/runpod-callback")
print(f"\n{failures} failed" if failures else "\nall passed"); sys.exit(1 if failures else 0)
