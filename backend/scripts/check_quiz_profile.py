"""
Offline check for the size quiz saved to an account (quiz_profiles):

  1. Writing needs proof (own session or own widget token), whatever WIDGET_AUTH_REQUIRED says.
  2. Only the quiz's own answers are stored, in range; anything else is refused or dropped.
  3. Save then read gives the same answers back; a second save replaces the first.
  4. Reading follows the same rules as the fit passport route.
  5. It never touches fit_passports (the measured passport stays the measured passport).

In-process TestClient, FAKE Supabase client, throwaway secrets. No network, no production data.

    cd backend && python3 scripts/check_quiz_profile.py
"""
import os
import sys
import time

TEST_SECRET = "local-test-secret-not-a-real-key-0123456789"
os.environ["SUPABASE_URL"] = "http://supabase.invalid"
os.environ["SUPABASE_SERVICE_KEY"] = "fake-service-key"
os.environ["SUPABASE_JWT_SECRET"] = TEST_SECRET
os.environ["DEBUG"] = "false"
os.environ.pop("WIDGET_AUTH_REQUIRED", None)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import jwt  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.routes.measurements import clean_quiz_estimate, clean_quiz_profile  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.models.events import EventType  # noqa: E402
from app.services import widget_token  # noqa: E402
from app.services.supabase import supabase_service  # noqa: E402

ALICE = "aaaaaaaa-0000-0000-0000-000000000001"
BOB = "bbbbbbbb-0000-0000-0000-000000000002"
GHOST = "cccccccc-0000-0000-0000-000000000003"   # signed in, no public.users row

failures = 0


def check(name, cond, detail=""):
    global failures
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        failures += 1


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
        self.filters.append((col, val))
        return self

    def limit(self, n, *_a, **_k):
        self.limit_n = n
        return self

    def single(self):
        return self

    def execute(self):
        self.db.touched.add(self.table)
        rows = self.db.tables.setdefault(self.table, [])
        if self.op == "insert":
            if not any(u["id"] == self.payload["user_id"] for u in self.db.tables["users"]):
                raise RuntimeError('insert violates foreign key constraint (23503)')
            if any(r["user_id"] == self.payload["user_id"] for r in rows):
                raise RuntimeError("duplicate key value violates unique constraint (23505)")
            rows.append(dict(self.payload))
            return _Result([dict(self.payload)])
        hits = [r for r in rows if all(r.get(c) == v for c, v in self.filters)]
        if self.op == "update":
            for r in hits:
                r.update(self.payload)
        return _Result([dict(r) for r in hits[: self.limit_n or len(hits)]])


class FakeAuth:
    def get_user(self, _token):
        raise RuntimeError("fake auth: token rejected")


class FakeClient:
    def __init__(self):
        self.auth = FakeAuth()
        self.touched = set()
        self.tables = {"users": [{"id": ALICE}, {"id": BOB}], "quiz_profiles": [], "fit_passports": []}

    def table(self, name):
        return FakeQuery(self, name)


fake = FakeClient()
supabase_service.client = fake
client = TestClient(app)


def bearer(user_id):
    tok = jwt.encode({"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + 3600}, TEST_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {tok}"}


def wtok(user_id):
    return {"X-Widget-Token": widget_token.issue(user_id)}


def require_auth(on):
    get_settings().widget_auth_required = on


def put(user_id, profile, headers=None, **extra):
    return client.put(f"/api/measurements/quiz-profile/{user_id}", json={"profile": profile, **extra}, headers=headers or {})


def get(user_id, headers=None):
    return client.get(f"/api/measurements/quiz-profile/{user_id}", headers=headers or {})


GOOD = {"gender": "male", "height": 190, "weight": 92, "age": 30, "ageBand": "25-34",
        "shape": {"chest": 1, "belly": 0}, "units": "metric", "fit": "regular"}

# --------------------------------------------------------------------------- 1. proof to write
require_auth(False)
check("flag off: no proof -> 401 (a bare user id never writes)", put(ALICE, GOOD).status_code == 401)
check("someone else's session -> 403", put(ALICE, GOOD, bearer(BOB)).status_code == 403)
check("someone else's widget token -> 403", put(ALICE, GOOD, wtok(BOB)).status_code == 403)
check("forged widget token -> 401", put(ALICE, GOOD, {"X-Widget-Token": wtok(ALICE)["X-Widget-Token"][:-3] + "abc"}).status_code == 401)
check("invalid bearer -> 401", put(ALICE, GOOD, {"Authorization": "Bearer not.a.token"}).status_code == 401)
check("nothing was stored by any refused write", fake.tables["quiz_profiles"] == [])

# --------------------------------------------------------------------------- 2. what is stored
r = put(ALICE, {**GOOD, "email": "x@y.z", "notes": "<script>", "shape": {"chest": 1, "belly": 0, "extra": 1}},
        bearer(ALICE), estimate={"chest": 108.4, "waist": 95.21, "hips": 9999, "junk": 1}, shop_domain="La-Fam-AMS.myshopify.com")
row = fake.tables["quiz_profiles"][0] if fake.tables["quiz_profiles"] else {}
check("own session saves", r.status_code == 200, r.text)
check("unknown keys are dropped", set(row.get("profile", {})) == set(GOOD) and set(row["profile"]["shape"]) == {"chest", "belly"}, str(row.get("profile")))
check("estimate keeps only believable chest/waist/hips", row.get("estimate") == {"chest": 108.4, "waist": 95.2}, str(row.get("estimate")))
check("the store it was first saved in is kept, lower case", row.get("shop_domain") == "la-fam-ams.myshopify.com")

BAD = [
    ("gender other", {**GOOD, "gender": "other"}), ("no gender", {k: v for k, v in GOOD.items() if k != "gender"}),
    ("height 90", {**GOOD, "height": 90}), ("height text", {**GOOD, "height": "190"}), ("height true", {**GOOD, "height": True}),
    ("weight 400", {**GOOD, "weight": 400}), ("age 5", {**GOOD, "age": 5}), ("age band", {**GOOD, "ageBand": "0-99"}),
    ("shape 2", {**GOOD, "shape": {"chest": 2}}), ("shape list", {**GOOD, "shape": [1]}),
    ("units", {**GOOD, "units": "stone"}), ("fit", {**GOOD, "fit": "baggy"}),
]
for name, p in BAD:
    check(f"refused: {name}", put(ALICE, p, bearer(ALICE)).status_code == 422)
check("refused writes left the saved answers alone", fake.tables["quiz_profiles"][0]["profile"]["height"] == 190)
check("age and build are optional", clean_quiz_profile({"gender": "female", "height": 165.4, "weight": 60}) ==
      {"gender": "female", "height": 165, "weight": 60, "shape": {}})
check("estimate: nothing usable -> None", clean_quiz_estimate({"chest": "big"}) is None and clean_quiz_estimate(None) is None)

# --------------------------------------------------------------------------- 3. save, read, replace
got = get(ALICE, bearer(ALICE))
check("read gives the saved answers back", got.status_code == 200 and got.json()["profile"] == row["profile"], got.text)
r = put(ALICE, {**GOOD, "weight": 88, "fit": "loose"}, wtok(ALICE), shop_domain="other.myshopify.com")
check("own widget token saves too", r.status_code == 200, r.text)
check("a second save replaces the first, one row per shopper",
      len(fake.tables["quiz_profiles"]) == 1 and fake.tables["quiz_profiles"][0]["profile"]["weight"] == 88
      and fake.tables["quiz_profiles"][0]["profile"]["fit"] == "loose")
check("the first store stays on the row", fake.tables["quiz_profiles"][0]["shop_domain"] == "la-fam-ams.myshopify.com")
check("no account profile row -> 409, nothing stored",
      put(GHOST, GOOD, bearer(GHOST)).status_code == 409 and len(fake.tables["quiz_profiles"]) == 1)

# --------------------------------------------------------------------------- 4. reading
check("none saved -> 404", get(BOB, bearer(BOB)).status_code == 404)
check("someone else's widget token -> 403", get(ALICE, wtok(BOB)).status_code == 403)
require_auth(True)
check("flag on: no proof -> 401", get(ALICE).status_code == 401)
check("flag on: someone else's session -> 403", get(ALICE, bearer(BOB)).status_code == 403)
check("flag on: own widget token -> 200", get(ALICE, wtok(ALICE)).status_code == 200)
check("flag on: writes still need proof", put(ALICE, GOOD).status_code == 401)
require_auth(False)

# --------------------------------------------------------------------------- 5. separate from the measured passport
check("fit_passports was never read or written", "fit_passports" not in fake.touched, str(fake.touched))
check("events exist for saved and loaded",
      EventType("size_finder_profile_saved") and EventType("size_finder_profile_loaded"))

print(f"\n{failures} failed" if failures else "\nall passed")
sys.exit(1 if failures else 0)
