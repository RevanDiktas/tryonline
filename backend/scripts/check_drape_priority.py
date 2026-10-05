"""
Offline check for drape scheduling (2026-10-05):

  1. The dispatcher hands RunPod only as many jobs as it can run (DRAPE_MAX_IN_FLIGHT),
     counting what RunPod already holds; without RunPod's count, recent jobs in drape_jobs.
  2. Claims go lowest priority number first, so the garment on screen beats the fan-out.
  3. /api/draping/request moves the shopper's existing drape job to the front (or adds one)
     instead of starting its own RunPod call, and wakes the dispatcher.
  4. /api/draping/status/job:<id> reports the job and returns the cached drape when done.
  5. wake_dispatcher() runs a tick at once instead of at the next interval.
  6. A new avatar's fan-out puts the product page the shopper onboarded from first.

Measured before the change: 39 jobs in RunPod's first-come queue, ~23 min wait for a
30-75 s drape. In-process TestClient, FAKE Supabase and RunPod. No network.

    cd backend && python3 scripts/check_drape_priority.py
"""
import asyncio
import os
import sys

os.environ["SUPABASE_URL"] = "http://supabase.invalid"
os.environ["SUPABASE_SERVICE_KEY"] = "fake-service-key"
os.environ["RUNPOD_API_KEY"] = "fake-runpod-key"
os.environ["RUNPOD_DRAPING_ENDPOINT_ID"] = "fake-drape-endpoint"
os.environ["BACKEND_PUBLIC_URL"] = "http://backend.invalid"
os.environ["DRAPE_MAX_IN_FLIGHT"] = "2"
os.environ["DRAPE_DISPATCH_BATCH"] = "4"
os.environ["DEBUG"] = "false"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient  # noqa: E402

from app.api.routes import draping as draping_routes  # noqa: E402
from app.main import app  # noqa: E402
from app.services import drape_dispatcher as dd  # noqa: E402
from app.services import drape_queue as dq  # noqa: E402
from app.services.body_clustering import compute_body_hash  # noqa: E402
from app.services.supabase import supabase_service  # noqa: E402

SHOPPER = "aaaaaaaa-0000-0000-0000-000000000001"
OTHER = "bbbbbbbb-0000-0000-0000-000000000002"
ZIP = "garment-zip"
TEE = "garment-tee"
VERSION = "v1"

failures = 0


def check(name, cond, detail=""):
    global failures
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        failures += 1


# --------------------------------------------------------------------------- fake supabase

class _Result:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, db, table):
        self.db, self.table, self.filters = db, table, []
        self.op, self.payload, self.limit_n = "select", None, None

    def select(self, *_a, **_k):
        return self

    def insert(self, row):
        self.op, self.payload = "insert", row
        return self

    def update(self, fields):
        self.op, self.payload = "update", fields
        return self

    def eq(self, col, val):
        self.filters.append(("eq", col, val))
        return self

    def in_(self, col, vals):
        self.filters.append(("in", col, set(vals)))
        return self

    def gte(self, col, val):
        self.filters.append(("gte", col, val))
        return self

    def limit(self, n, *_a, **_k):
        self.limit_n = n
        return self

    def order(self, *_a, **_k):
        return self

    def _match(self, row):
        for op, col, val in self.filters:
            v = row.get(col)
            if op == "eq" and v != val:
                return False
            if op == "in" and v not in val:
                return False
            if op == "gte" and (v is None or str(v) < str(val)):
                return False
        return True

    def execute(self):
        rows = self.db.tables.setdefault(self.table, [])
        if self.op == "insert":
            row = {"id": f"{self.table}-{len(rows) + 1}", "created_at": f"t{len(rows) + 100:04d}",
                   "attempts": 0, **self.payload}
            rows.append(row)
            return _Result([dict(row)])
        hits = [r for r in rows if self._match(r)]
        if self.op == "update":
            for r in hits:
                r.update(self.payload)
            return _Result([dict(r) for r in hits])
        return _Result([dict(r) for r in hits[: self.limit_n or len(hits)]])


class FakeRpc:
    def __init__(self, db, name, params):
        self.db, self.name, self.params = db, name, params

    def execute(self):
        assert self.name == "claim_drape_jobs"
        queued = [r for r in self.db.tables["drape_jobs"] if r["status"] == "queued"]
        queued.sort(key=lambda r: (r["priority"], r["created_at"]))
        out = []
        for r in queued[: self.params["limit_n"]]:
            r.update({"status": "dispatched", "dispatched_at": "2999-01-01T00:00:00+00:00",
                      "attempts": r.get("attempts", 0) + 1})
            out.append(dict(r))
        return _Result(out)


class FakeClient:
    def __init__(self):
        self.tables = {}
        self.reset()

    def reset(self):
        def passport(uid, mesh):
            return {"user_id": uid, "status": "completed", "pipeline_files": {"apose_mesh": mesh},
                    "processing_completed_at": "2026-10-05T18:17:00+00:00", "height": 195, "gender": "male"}
        self.tables = {
            "fit_passports": [passport(SHOPPER, f"avatars/{SHOPPER}/body_apose.obj"),
                              passport(OTHER, f"avatars/{OTHER}/body_apose.obj")],
            "garments": [{"id": g, "brand_id": "brand-ramin", "is_active": True, "content_hash": VERSION,
                          "fabric_config": {}, "category": "tops", "shopify_product_handle": handle,
                          "obj_sizes": {s: f"garments/{g}/{s}.obj" for s in ("s", "m", "l")}}
                         for g, handle in ((ZIP, "rs-zip-up"), (TEE, "rs-tee"))],
            "brands": [{"id": "brand-ramin", "shopify_domain": "ph2360-eq.myshopify.com"}],
            "drape_jobs": [], "draped_meshes": [],
        }

    def table(self, name):
        return FakeQuery(self, name)

    def rpc(self, name, params):
        return FakeRpc(self, name, params)


fake = FakeClient()
supabase_service.client = fake
draping_routes.supabase.client = fake
client = TestClient(app)


def body_hash(uid):
    return compute_body_hash(uid, next(p for p in fake.tables["fit_passports"] if p["user_id"] == uid))


def add_job(uid, garment, size, status="queued", priority=10, created="t0001", **extra):
    row = {"id": f"job-{uid[:1]}-{garment}-{size}", "user_id": uid, "garment_id": garment, "size": size,
           "body_hash": body_hash(uid), "garment_version_hash": VERSION, "priority": priority,
           "status": status, "created_at": created, "attempts": 0, **extra}
    fake.tables["drape_jobs"].append(row)
    return row


def job_id_garment(job_id):
    return next(r["garment_id"] for r in fake.tables["drape_jobs"] if r["id"] == job_id)


def job(job_id):
    return next(r for r in fake.tables["drape_jobs"] if r["id"] == job_id)


# Fake RunPod: the health count and the /run call.
runpod = {"backlog": 0, "health_ok": True, "sent": []}


async def fake_backlog(_client):
    return runpod["backlog"] if runpod["health_ok"] else None


async def fake_dispatch_one(_client, j):
    runpod["sent"].append(j["id"])
    fake.table("drape_jobs").update({"status": "running", "runpod_job_id": f"rp-{j['id']}"}).eq("id", j["id"]).execute()


REAL_WAKE = dd.wake_dispatcher
dd._runpod_backlog = fake_backlog
dd._dispatch_one = fake_dispatch_one


def tick():
    runpod["sent"] = []
    asyncio.run(dd._tick())
    return list(runpod["sent"])


# --------------------------------------------------------------------------- 1. in-flight cap

check("free slots: RunPod empty -> 2", dd._free_slots(0) == 2)
check("free slots: RunPod holds 1 -> 1", dd._free_slots(1) == 1)
check("free slots: RunPod holds 39 -> 0", dd._free_slots(39) == 0)

fake.reset()
for i, (g, s) in enumerate([(TEE, "s"), (TEE, "m"), (TEE, "l"), (ZIP, "s"), (ZIP, "m"), (ZIP, "l")]):
    add_job(OTHER, g, s, created=f"t{i:04d}")
runpod["backlog"] = 39
check("RunPod full (39 waiting): nothing dispatched", tick() == [])
runpod["backlog"] = 1
check("RunPod holds 1: exactly 1 dispatched", len(tick()) == 1)
runpod["backlog"] = 0
sent = tick()
check("RunPod empty: 2 dispatched (not the batch of 4)", len(sent) == 2, sent)
check("fan-out order kept when priorities are equal", sent == ["job-b-garment-tee-m", "job-b-garment-tee-l"], sent)

# Health route down: count our own recent in-flight jobs instead.
runpod["health_ok"] = False
fake.reset()
add_job(OTHER, TEE, "s", status="running", dispatched_at="2999-01-01T00:00:00+00:00")
add_job(OTHER, TEE, "m", status="running", dispatched_at="2999-01-01T00:00:00+00:00")
add_job(OTHER, TEE, "l", created="t0005")
check("no RunPod count, 2 recent in flight: nothing dispatched", tick() == [])
for r in fake.tables["drape_jobs"]:
    if r["status"] == "running":
        r["dispatched_at"] = "2000-01-01T00:00:00+00:00"   # webhook lost long ago
check("no RunPod count, in-flight jobs are stale: queue moves again", tick() == ["job-b-garment-tee-l"])
runpod["health_ok"] = True

# --------------------------------------------------------------------------- 2-3. the garment on screen jumps the queue

fake.reset()
runpod["backlog"] = 0
for i, (g, s) in enumerate([(TEE, "s"), (TEE, "m"), (TEE, "l")]):
    add_job(OTHER, g, s, created=f"t{i:04d}")                      # someone else's fan-out, first in line
for i, (g, s) in enumerate([(ZIP, "s"), (ZIP, "m"), (ZIP, "l")]):
    add_job(SHOPPER, g, s, created=f"t{10 + i:04d}")               # this shopper's fan-out, behind it

woken = []
dd.wake_dispatcher = lambda: woken.append(1)

r = client.post("/api/draping/request", json={"garment_id": ZIP, "size": "l", "user_id": SHOPPER, "on_screen": True})
d = r.json()
check("/request answers 200", r.status_code == 200, r.text)
check("/request returns the existing job to poll", d.get("request_id") == "job:job-a-garment-zip-l" and d.get("status") == "pending", d)
check("/request moved the on-screen size to priority 0", job("job-a-garment-zip-l")["priority"] == dq.PRIORITY_ON_SCREEN)
check("/request woke the dispatcher", len(woken) == 1)
check("/request made no job of its own", len(fake.tables["drape_jobs"]) == 6)

client.post("/api/draping/request", json={"garment_id": ZIP, "size": "m", "user_id": SHOPPER})
check("another size of the open garment goes right behind it (priority 1)", job("job-a-garment-zip-m")["priority"] == dq.PRIORITY_IN_VIEWER)

sent = tick()
check("next dispatch: the on-screen size first, then the open garment", sent == ["job-a-garment-zip-l", "job-a-garment-zip-m"], sent)

# A job already handed to RunPod is left alone.
before = dict(job("job-a-garment-zip-l"))
client.post("/api/draping/request", json={"garment_id": ZIP, "size": "l", "user_id": SHOPPER, "on_screen": True})
check("a job already running keeps its state", job("job-a-garment-zip-l")["status"] == before["status"] == "running")

# No fan-out job yet (an avatar older than the garment): one is added at the front.
fake.reset()
add_job(OTHER, TEE, "s", created="t0001")
r = client.post("/api/draping/request", json={"garment_id": ZIP, "size": "s", "user_id": SHOPPER, "on_screen": True})
new = [j for j in fake.tables["drape_jobs"] if j["user_id"] == SHOPPER]
check("missing job: one is added", len(new) == 1 and new[0]["status"] == "queued", new)
check("missing job: added at priority 0", new and new[0]["priority"] == dq.PRIORITY_ON_SCREEN)
check("missing job: dispatched before the older fan-out", tick()[:1] == [new[0]["id"]] if new else False)

# A job that used up its attempts is reported, not retried in a loop.
fake.reset()
add_job(SHOPPER, ZIP, "s", status="failed", error_message="sim exploded")
d = client.post("/api/draping/request", json={"garment_id": ZIP, "size": "s", "user_id": SHOPPER, "on_screen": True}).json()
check("failed job: /request says failed", d.get("status") == "failed", d)
check("failed job: not put back in the queue", job("job-a-garment-zip-s")["status"] == "failed")

# Cached drape: answered at once, no job touched.
fake.reset()
fake.tables["draped_meshes"].append({"garment_id": ZIP, "size": "m", "body_hash": body_hash(SHOPPER),
                                     "garment_version_hash": VERSION, "draped_glb_url": "https://cdn.invalid/zip-m.glb"})
d = client.post("/api/draping/request", json={"garment_id": ZIP, "size": "m", "user_id": SHOPPER, "on_screen": True}).json()
check("cached drape: returned straight away", d.get("cached") is True and d.get("draped_url") == "https://cdn.invalid/zip-m.glb", d)
check("cached drape: no job added", fake.tables["drape_jobs"] == [])

# --------------------------------------------------------------------------- 4. status of a job

fake.reset()
add_job(SHOPPER, ZIP, "m")
s = client.get("/api/draping/status/job:job-a-garment-zip-m").json()
check("status: queued job is processing", s.get("status") == "processing", s)
job("job-a-garment-zip-m")["status"] = "running"
check("status: running job is processing", client.get("/api/draping/status/job:job-a-garment-zip-m").json().get("status") == "processing")
job("job-a-garment-zip-m")["status"] = "completed"
fake.tables["draped_meshes"].append({"garment_id": ZIP, "size": "m", "body_hash": body_hash(SHOPPER),
                                     "garment_version_hash": VERSION, "draped_glb_url": "https://cdn.invalid/zip-m.glb"})
s = client.get("/api/draping/status/job:job-a-garment-zip-m").json()
check("status: completed job returns the drape", s.get("status") == "completed" and s.get("draped_url") == "https://cdn.invalid/zip-m.glb", s)
fake.tables["draped_meshes"].clear()
s = client.get("/api/draping/status/job:job-a-garment-zip-m").json()
check("status: completed without a mesh is failed, not a hang", s.get("status") == "failed", s)
job("job-a-garment-zip-m").update({"status": "failed", "error_message": "sim exploded"})
s = client.get("/api/draping/status/job:job-a-garment-zip-m").json()
check("status: failed job reports its error", s.get("status") == "failed" and s.get("error") == "sim exploded", s)
check("status: unknown job is 404", client.get("/api/draping/status/job:nope").status_code == 404)

# --------------------------------------------------------------------------- 5. wake-up


async def wake_test():
    dd.TICK_SECONDS = 3600
    ticks = []

    async def counting_tick():
        ticks.append(1)
    dd._tick = counting_tick
    stop = asyncio.Event()
    task = asyncio.create_task(dd.dispatcher_loop(stop))
    await asyncio.sleep(0.05)
    first = len(ticks)
    REAL_WAKE()
    await asyncio.sleep(0.05)
    second = len(ticks)
    stop.set()
    await asyncio.wait_for(task, 1)
    return first, second


real_tick = dd._tick
first, second = asyncio.run(wake_test())
dd._tick = real_tick
check("loop ticks once at start", first == 1, first)
check("wake_dispatcher runs another tick at once (interval is an hour)", second == 2, second)

# --------------------------------------------------------------------------- 6. product first

fake.reset()
dd.wake_dispatcher = lambda: woken.append(1)
woken.clear()
dq.enqueue_full_drape(SHOPPER, priority=10, brand_ids=["brand-ramin"])       # what /create does on completion
check("fan-out queued every garment x size", len(fake.tables["drape_jobs"]) == 6, len(fake.tables["drape_jobs"]))
moved = dq.drape_product_first(SHOPPER, "ph2360-eq.myshopify.com", "rs-zip-up")
check("product first: all its sizes moved up", sorted(moved) == ["l", "m", "s"], moved)
zip_p = sorted(j["priority"] for j in fake.tables["drape_jobs"] if j["garment_id"] == ZIP)
tee_p = sorted(j["priority"] for j in fake.tables["drape_jobs"] if j["garment_id"] == TEE)
check("product first: its jobs at priority 0, the rest stay at 10", zip_p == [0, 0, 0] and tee_p == [10, 10, 10], (zip_p, tee_p))
check("product first: dispatcher woken", len(woken) == 1)
runpod["backlog"] = 0
sent = tick()
check("product first: dispatched before the store's other garments",
      len(sent) == 2 and all(job_id_garment(j) == ZIP for j in sent), sent)
check("product first: unknown product changes nothing", dq.drape_product_first(SHOPPER, "ph2360-eq.myshopify.com", "no-such-product") == [])
check("product first: no shop or product changes nothing", dq.drape_product_first(SHOPPER, None, "rs-zip-up") == [] and dq.drape_product_first(SHOPPER, "ph2360-eq.myshopify.com", None) == [])

print()
print("ALL CHECKS PASSED" if failures == 0 else f"{failures} CHECK(S) FAILED")
sys.exit(1 if failures else 0)
