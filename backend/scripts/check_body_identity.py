"""
Offline check for the avatar-based body hash (app/services/body_clustering.py).

  - a dashboard measurement edit keeps the hash -> enqueue does nothing, drapes stay found
  - a regenerated avatar changes the hash -> every garment x size is re-queued (stale
    jobs reset, not skipped, despite idx_drape_jobs_unique not covering body_hash)
  - lookups serve legacy-hash rows during the transition, and prefer new-hash rows
  - scripts/migrate_body_hash.py relabels legacy rows, resolves collisions (newest wins),
    leaves drapes of an older avatar alone, repoints jobs

Runs the real modules against an in-memory FAKE Supabase client. No network, no prod.

    cd backend && python3 scripts/check_body_identity.py
"""
import os
import sys
import uuid

os.environ["SUPABASE_URL"] = "http://supabase.invalid"
os.environ["SUPABASE_SERVICE_KEY"] = "fake-service-key"
os.environ["SUPABASE_JWT_SECRET"] = "local-test-secret"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.supabase import supabase_service  # noqa: E402

UNIQUE = {  # table -> unique key columns (mirrors the real indexes)
    "drape_jobs": ("user_id", "garment_id", "size", "garment_version_hash"),
    "draped_meshes": ("garment_id", "size", "body_hash"),
}


class _Result:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, db, table):
        self.db, self.table, self.filters = db, table, []
        self.op, self.payload, self.limit_n, self.offset = "select", None, None, 0

    def select(self, *_a, **_k):
        return self

    def eq(self, c, v):
        self.filters.append(("eq", c, v))
        return self

    def in_(self, c, vs):
        self.filters.append(("in", c, list(vs)))
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, n, *_a, **_k):
        self.limit_n = n
        return self

    def range(self, a, b, *_x):
        self.offset, self.limit_n = a, b - a + 1
        return self

    def insert(self, row):
        self.op, self.payload = "insert", row
        return self

    def update(self, row):
        self.op, self.payload = "update", row
        return self

    def delete(self):
        self.op = "delete"
        return self

    def _match(self, row):
        for op, c, v in self.filters:
            if op == "eq" and row.get(c) != v:
                return False
            if op == "in" and row.get(c) not in v:
                return False
        return True

    def execute(self):
        rows = self.db.tables.setdefault(self.table, [])
        if self.op == "insert":
            new = {"id": str(uuid.uuid4()), **self.payload}
            key = UNIQUE.get(self.table)
            if key and any(all(r.get(k) == new.get(k) for k in key) for r in rows):
                raise Exception("duplicate key value violates unique constraint (23505)")
            rows.append(new)
            return _Result([new])
        hit = [r for r in rows if self._match(r)]
        if self.op == "update":
            for r in hit:
                r.update(self.payload)
            return _Result([dict(r) for r in hit])
        if self.op == "delete":
            self.db.tables[self.table] = [r for r in rows if r not in hit]
            return _Result(hit)
        hit = hit[self.offset:]
        if self.limit_n is not None:
            hit = hit[:self.limit_n]
        return _Result([dict(r) for r in hit])


class FakeClient:
    def __init__(self):
        self.tables = {}

    def table(self, name):
        return FakeQuery(self, name)


fake = FakeClient()
supabase_service.client = fake

from app.api.routes import draping, products  # noqa: E402
from app.services import body_clustering as bc  # noqa: E402
from app.services import drape_queue  # noqa: E402

draping.supabase.client = fake  # draping.py holds its own SupabaseService() instance

failures = 0


def check(name, cond, detail=""):
    global failures
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        failures += 1


UID = "9ede4581-7aea-4916-b680-d1346c8322ad"
PATH = "https://x/storage/v1/object/public/avatars/9ede4581/body_apose.obj"
passport = {
    "user_id": UID, "status": "completed", "height": 195, "chest": 104, "waist": 88, "hips": 100,
    "gender": "male", "processing_completed_at": "2026-09-30T17:51:25.123456+00:00",
    "pipeline_files": {"apose_mesh": PATH, "tpose_mesh": PATH.replace("apose", "tpose")},
    "updated_at": "2026-09-30T17:52:01+00:00",
}

# --------------------------------------------------------------------------- 1. the hash

h0 = bc.compute_body_hash(UID, passport)
edited = {**passport, "chest": 110, "waist": 95, "height": 196, "updated_at": "2026-10-03T09:00:00+00:00"}
check("measurement edit -> same body hash", bc.compute_body_hash(UID, edited) == h0)
check("measurement edit DOES change the legacy hash (the old bug)",
      bc.compute_legacy_body_hash(UID, edited) != bc.compute_legacy_body_hash(UID, passport))
regen = {**passport, "processing_completed_at": "2026-10-03T10:00:00+00:00"}
check("regenerated avatar -> new body hash", bc.compute_body_hash(UID, regen) != h0)
repointed = {**passport, "pipeline_files": {"apose_mesh": PATH.replace(".obj", "_feet0.obj")}}
check("body mesh repointed -> new body hash", bc.compute_body_hash(UID, repointed) != h0)
check("other user, same avatar fields -> different hash", bc.compute_body_hash("other", passport) != h0)
check("timestamp formatting (Z vs +00:00) doesn't change the hash",
      bc.compute_body_hash(UID, {**passport, "processing_completed_at": "2026-09-30T17:51:25.123456Z"}) == h0)
check("no body mesh -> None", bc.compute_body_hash(UID, {**passport, "pipeline_files": {}}) is None)
check("apose preferred over tpose for the body file", bc.body_mesh_path(passport) == PATH)

# --------------------------------------------------------------------------- 2. enqueue

SIZES = ["xs", "s", "m", "l", "xl", "xxl"]
fake.tables = {
    "fit_passports": [dict(passport)],
    "garments": [{"id": f"g{i}", "brand_id": "b1", "is_active": True, "content_hash": f"v{i}",
                  "obj_sizes": {s: f"garments/g{i}/{s}.obj" for s in SIZES}} for i in range(7)],
    "drape_jobs": [], "draped_meshes": [],
}


def complete_all_jobs(body_hash):
    for j in fake.tables["drape_jobs"]:
        if j["status"] == "queued":
            mesh = {"id": str(uuid.uuid4()), "garment_id": j["garment_id"], "size": j["size"],
                    "body_hash": j["body_hash"], "garment_version_hash": j["garment_version_hash"],
                    "draped_glb_url": f"https://x/draped/{j['garment_id']}/{j['size']}/{j['body_hash']}.glb",
                    "created_at": "2026-09-30T18:00:00+00:00"}
            fake.tables["draped_meshes"] = [m for m in fake.tables["draped_meshes"] if not (
                m["garment_id"] == mesh["garment_id"] and m["size"] == mesh["size"] and m["body_hash"] == body_hash)]
            fake.tables["draped_meshes"].append(mesh)
            j.update(status="completed", draped_mesh_id=mesh["id"], completed_at="2026-09-30T18:00:00+00:00")


c = drape_queue.enqueue_full_drape(UID, priority=10)
check("new avatar -> 42 jobs enqueued", c["enqueued"] == 42 and len(fake.tables["drape_jobs"]) == 42, str(c))
check("jobs carry the avatar hash", all(j["body_hash"] == h0 for j in fake.tables["drape_jobs"]))
complete_all_jobs(h0)

fake.tables["fit_passports"][0].update(chest=110, waist=95, height=196, updated_at="2026-10-03T09:00:00+00:00")
c = drape_queue.enqueue_full_drape(UID, priority=10)
check("measurement edit -> 0 jobs, all 42 still cached",
      c["enqueued"] == 0 and c["skipped_already_cached"] == 42, str(c))
check("measurement edit -> drapes still found by tryon-config lookup",
      len(products._get_draped_urls("g0", products._body_lookup_hashes(UID), SIZES)) == 6)

fake.tables["fit_passports"][0]["processing_completed_at"] = "2026-10-03T10:00:00+00:00"
h1 = bc.compute_body_hash(UID, fake.tables["fit_passports"][0])
c = drape_queue.enqueue_full_drape(UID, priority=10)
jobs = fake.tables["drape_jobs"]
check("regenerated avatar -> 42 jobs re-queued (stale jobs reset, not skipped)",
      c["enqueued"] == 42 and c.get("reset_stale") == 42 and len(jobs) == 42, str(c))
check("re-queued jobs carry the NEW hash and are queued",
      all(j["body_hash"] == h1 and j["status"] == "queued" and j["attempts"] == 0 for j in jobs))
c = drape_queue.enqueue_full_drape(UID, priority=10)
check("enqueue again while in flight -> 0 new, 42 already queued",
      c["enqueued"] == 0 and c["skipped_already_queued"] == 42, str(c))
jobs[0]["status"] = "failed"
c = drape_queue.enqueue_full_drape(UID, priority=10)
check("same-hash failed job is not retried by enqueue (no retry storm)",
      jobs[0]["status"] == "failed" and c["enqueued"] == 0, str(c))
c = drape_queue.enqueue_for_garment("g1", user_ids=[UID])
check("enqueue_for_garment uses the same rules (6 sizes already queued)",
      c["enqueued"] == 0 and c["skipped_already_queued"] == 6, str(c))

# Transition: deployed, not yet migrated. Rows + jobs still on the legacy hash.
fake.tables["fit_passports"] = [dict(passport)]
legacy0 = bc.compute_legacy_body_hash(UID, passport)
for j in fake.tables["drape_jobs"]:
    j.update(body_hash=legacy0, status="completed", completed_at="2026-09-30T18:00:00+00:00")
fake.tables["draped_meshes"] = [
    {"id": f"t{j['id']}", "garment_id": j["garment_id"], "size": j["size"], "body_hash": legacy0,
     "garment_version_hash": j["garment_version_hash"], "draped_glb_url": "https://x/t.glb"}
    for j in fake.tables["drape_jobs"]]
c = drape_queue.enqueue_full_drape(UID, priority=10)
check("transition: legacy-hash drapes of the CURRENT avatar count as cached (no mass re-drape)",
      c["enqueued"] == 0 and c["skipped_already_cached"] == 42, str(c))
for j in fake.tables["drape_jobs"]:
    j["completed_at"] = "2026-09-01T00:00:00+00:00"  # draped before this avatar existed
c = drape_queue.enqueue_full_drape(UID, priority=10)
check("transition: legacy-hash drapes of an OLDER avatar are re-queued",
      c["enqueued"] == 42 and c.get("reset_stale") == 42, str(c))

# --------------------------------------------------------------------------- 3. lookups

fake.tables["fit_passports"] = [dict(passport)]
legacy = bc.compute_legacy_body_hash(UID, passport)
fake.tables["draped_meshes"] = [
    {"id": "m1", "garment_id": "g9", "size": "M", "body_hash": legacy, "draped_glb_url": "https://x/legacy_m.glb"},
    {"id": "m2", "garment_id": "g9", "size": "L", "body_hash": legacy, "draped_glb_url": "https://x/legacy_l.glb"},
    {"id": "m3", "garment_id": "g9", "size": "L", "body_hash": h0, "draped_glb_url": "https://x/new_l.glb"},
]
urls = products._get_draped_urls("g9", products._body_lookup_hashes(UID), ["m", "l"])
check("tryon-config serves a legacy-hash drape during the transition", urls.get("m") == "https://x/legacy_m.glb", str(urls))
check("tryon-config prefers the new-hash drape when both exist", urls.get("l") == "https://x/new_l.glb", str(urls))
ident = draping._body_identity(UID)
check("draping lookup serves legacy row", draping._cached_drape_url("g9", "M", ident.lookup_hashes) == "https://x/legacy_m.glb")
check("draping lookup prefers new row", draping._cached_drape_url("g9", "L", ident.lookup_hashes) == "https://x/new_l.glb")
check("draping lookup: nothing cached -> None", draping._cached_drape_url("g9", "S", ident.lookup_hashes) is None)

# --------------------------------------------------------------------------- 4. migration

old_meas_hash = "beb465b1f94707a0"  # left on a job by an earlier measurement edit
fake.tables = {
    "fit_passports": [dict(passport)],
    "draped_meshes": [
        # (g1, m) under legacy and under an older measurement hash: newest wins
        {"id": "a", "draped_glb_url": "https://x/a.glb", "garment_id": "g1", "size": "m", "body_hash": legacy, "created_at": "2026-09-30T18:00:00+00:00"},
        {"id": "b", "draped_glb_url": "https://x/b.glb", "garment_id": "g1", "size": "m", "body_hash": old_meas_hash, "created_at": "2026-09-30T19:00:00+00:00"},
        # (g1, l) only legacy: relabel
        {"id": "c", "draped_glb_url": "https://x/c.glb", "garment_id": "g1", "size": "l", "body_hash": legacy, "created_at": "2026-09-30T18:00:00+00:00"},
        # (g2, m) draped BEFORE the current avatar existed: leave alone
        {"id": "d", "draped_glb_url": "https://x/d.glb", "garment_id": "g2", "size": "m", "body_hash": old_meas_hash, "created_at": "2026-09-01T00:00:00+00:00"},
        # someone else's row
        {"id": "z", "draped_glb_url": "https://x/z.glb", "garment_id": "g1", "size": "m", "body_hash": "ffffffffffffffff", "created_at": "2026-09-30T18:00:00+00:00"},
    ],
    "drape_jobs": [
        {"id": "j1", "user_id": UID, "garment_id": "g1", "size": "m", "body_hash": legacy, "draped_mesh_id": "a",
         "completed_at": "2026-09-30T18:00:00+00:00", "status": "completed"},
        {"id": "j2", "user_id": UID, "garment_id": "g1", "size": "l", "body_hash": legacy, "draped_mesh_id": "c",
         "completed_at": "2026-09-30T18:00:00+00:00", "status": "completed"},
        {"id": "j3", "user_id": UID, "garment_id": "g2", "size": "m", "body_hash": old_meas_hash, "draped_mesh_id": "d",
         "completed_at": "2026-09-01T00:00:00+00:00", "status": "completed"},
    ],
}
sys.path.insert(0, os.path.dirname(__file__))
import migrate_body_hash  # noqa: E402

sys.argv = ["migrate_body_hash.py"]
before = {t: [dict(r) for r in rows] for t, rows in fake.tables.items()}
migrate_body_hash.main()
check("migration dry run changes nothing",
      {t: [dict(r) for r in rows] for t, rows in fake.tables.items()} == before)
sys.argv = ["migrate_body_hash.py", "--apply"]
migrate_body_hash.main()
by_id = {m["id"]: m for m in fake.tables["draped_meshes"]}
check("collision: newest (b) kept and relabelled, older (a) deleted",
      "a" not in by_id and by_id.get("b", {}).get("body_hash") == h0, str(sorted(by_id)))
check("legacy-only row relabelled to the new hash", by_id.get("c", {}).get("body_hash") == h0)
check("row draped before the current avatar left untouched", by_id.get("d", {}).get("body_hash") == old_meas_hash)
check("another user's row untouched", by_id.get("z", {}).get("body_hash") == "ffffffffffffffff")
jobs = {j["id"]: j for j in fake.tables["drape_jobs"]}
check("all the user's jobs carry the new hash", all(j["body_hash"] == h0 for j in jobs.values()))
check("job pointing at the deleted row repointed to the kept row", jobs["j1"]["draped_mesh_id"] == "b")
urls = products._get_draped_urls("g1", products._body_lookup_hashes(UID), ["m", "l"])
check("after migration both sizes resolve via the new hash", set(urls) == {"m", "l"}, str(urls))
sys.argv = ["migrate_body_hash.py", "--apply"]
snap = {t: [dict(r) for r in rows] for t, rows in fake.tables.items()}
migrate_body_hash.main()
check("migration is idempotent (second --apply changes nothing)",
      {t: [dict(r) for r in rows] for t, rows in fake.tables.items()} == snap)

print(f"\n{'ALL CHECKS PASSED' if not failures else f'{failures} CHECK(S) FAILED'}")
sys.exit(1 if failures else 0)
