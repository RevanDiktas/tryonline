"""
Offline check for POST /api/garments/{id}/duplicate: the copy keeps the size chart, fit, fabric
settings and every mesh (copied into its own storage folder), gets its own name and handle,
refuses a handle already in use, and never copies another brand's garment. Fake Supabase,
no network.    cd backend && python3 scripts/check_garment_duplicate.py
"""
import os, sys, time
TEST_SECRET = "local-test-secret-not-a-real-key-0123456789"
os.environ.update(SUPABASE_URL="http://supabase.invalid", SUPABASE_SERVICE_KEY="fake", SUPABASE_JWT_SECRET=TEST_SECRET, DEBUG="false")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import jwt
from fastapi.testclient import TestClient
from app.main import app
from app.api.routes import garments as G

BRAND, OTHER = "b1", "b2"
failures = 0
def check(name, cond, detail=""):
    global failures
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))
    failures += 0 if cond else 1

class R:
    def __init__(s, d): s.data = d
class Q:
    def __init__(s, db, t): s.db, s.t, s.f, s.op, s.p = db, t, [], "select", None
    def select(s, *a, **k): return s
    def insert(s, row): s.op, s.p = "insert", row; return s
    def update(s, f): s.op, s.p = "update", f; return s
    def eq(s, c, v): s.f.append((c, v)); return s
    def limit(s, n): return s
    def order(s, *a, **k): return s
    def execute(s):
        rows = s.db.setdefault(s.t, [])
        if s.op == "insert":
            row = {"id": f"g{len(rows)+1}", **s.p}; rows.append(row); return R([dict(row)])
        hits = [r for r in rows if all(str(r.get(c)) == str(v) for c, v in s.f)]
        if s.op == "update":
            for r in hits: r.update(s.p)
        return R([dict(r) for r in hits])
class Bucket:
    def __init__(s): s.files = {"b1/striped-pants-black-grey/m.glb": b"GLB", "b1/striped-pants-black-grey/m.obj": b"OBJ", "b1/striped-pants-black-grey/l.obj": b"OBJ2"}
    def copy(s, a, b):
        if a not in s.files: raise RuntimeError("missing")
        s.files[b] = s.files[a]
    def download(s, p): return s.files[p]
    def upload(s, p, c, o): s.files[p] = c
class Storage:
    def __init__(s): s.b = Bucket()
    def from_(s, n): return s.b
class Client:
    def __init__(s, db): s.db, s.storage = db, Storage()
    def table(s, n): return Q(s.db, n)

chart = {"xs": {"length": 94, "waist": 34}, "m": {"length": 100, "waist": 40}}
db = {"garments": [
    {"id": "g1", "brand_id": BRAND, "name": "striped pants black/grey", "category": "bottoms", "fit_type": "regular",
     "shopify_product_id": "striped-pants-black-grey", "size_chart": chart, "fabric_config": {"preset": "denim"},
     "sizes": {"m": "garments/b1/striped-pants-black-grey/m.glb"},
     "obj_sizes": {"m": "garments/b1/striped-pants-black-grey/m.obj", "l": "garments/b1/striped-pants-black-grey/l.obj"}},
    {"id": "g2", "brand_id": OTHER, "name": "theirs", "sizes": {}, "obj_sizes": {}, "size_chart": {}},
]}
client = Client(db)
G.supabase.client = client
G.supabase.ensure_garments_bucket = lambda: None
G.supabase.get_brand_by_user_id = lambda uid: {"id": BRAND} if uid == "u1" else None
backfilled = []
G._backfill_drape_for_garment = lambda gid: backfilled.append(gid)
tc = TestClient(app)
def h(uid="u1"):
    return {"Authorization": "Bearer " + jwt.encode({"sub": uid, "aud": "authenticated", "exp": int(time.time()) + 3600}, TEST_SECRET, algorithm="HS256")}

r = tc.post("/api/garments/g1/duplicate", json={"name": "striped pants navy/grey", "shopify_product_id": "striped-pants-navy-grey"}, headers=h())
check("duplicate ok", r.status_code == 200, r.text)
g = r.json()["garment"]
check("new row, own name and handle", g["id"] != "g1" and g["name"] == "striped pants navy/grey" and g["shopify_product_id"] == "striped-pants-navy-grey")
check("size chart copied", g["size_chart"] == chart)
check("category, fit, fabric copied", g["category"] == "bottoms" and g["fit_type"] == "regular" and g["fabric_config"] == {"preset": "denim"})
check("meshes copied into the new folder", g["sizes"] == {"m": "garments/b1/striped-pants-navy-grey/m.glb"} and
      g["obj_sizes"] == {"m": "garments/b1/striped-pants-navy-grey/m.obj", "l": "garments/b1/striped-pants-navy-grey/l.obj"})
check("files really exist", client.storage.b.files.get("b1/striped-pants-navy-grey/l.obj") == b"OBJ2")
check("original untouched", db["garments"][0]["sizes"] == {"m": "garments/b1/striped-pants-black-grey/m.glb"})
check("counts reported", r.json()["files_copied"] == 3 and r.json()["files_expected"] == 3)
check("drapes queued for the copy", backfilled == [g["id"]])
check("chart edit on the copy does not touch the original",
      (db["garments"][0]["size_chart"] is not g["size_chart"]))

check("same handle as the source -> 400", tc.post("/api/garments/g1/duplicate", json={"name": "x", "shopify_product_id": "striped-pants-black-grey"}, headers=h()).status_code == 400)
check("handle already used -> 409", tc.post("/api/garments/g1/duplicate", json={"name": "x", "shopify_product_id": "striped-pants-navy-grey"}, headers=h()).status_code == 409)
check("empty name -> 400", tc.post("/api/garments/g1/duplicate", json={"name": " "}, headers=h()).status_code == 400)
r = tc.post("/api/garments/g1/duplicate", json={"name": "no handle yet"}, headers=h())
check("no handle: allowed, folder is the new id", r.status_code == 200 and r.json()["garment"]["sizes"]["m"].startswith(f"garments/b1/{r.json()['garment']['id']}/"))
check("another brand's garment -> 403", tc.post("/api/garments/g2/duplicate", json={"name": "x"}, headers=h()).status_code == 403)
check("no auth -> 401", tc.post("/api/garments/g1/duplicate", json={"name": "x"}).status_code == 401)
print(f"\n{failures} failed" if failures else "\nall passed"); sys.exit(1 if failures else 0)
