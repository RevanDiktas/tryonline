"""
Offline check for widget onboarding, part 2 (backend):

  1. Widget tokens: issued for one shopper, refuse forgery, expiry and other shoppers.
  2. Sign-in hand-off (/api/auth/widget-state): a completion must be proven with the
     page's bearer token to yield a widget token; nobody can complete as someone else.
  3. Bare user_id routes (/api/avatar/{id}, /api/draping/check, wishlist): open but logged
     while WIDGET_AUTH_REQUIRED is off, closed when it is on.
  4. /api/avatar/create: creates the fit passport itself, sends "other" to the pipeline
     as "neutral", and scopes the pre-drape fan-out to the store it was started from.

In-process TestClient, FAKE Supabase client, throwaway secrets. No server, no network,
no production data, no RunPod.

    cd backend && python3 scripts/check_widget_onboarding.py
"""
import asyncio
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

from app.api.routes import auth as auth_routes  # noqa: E402
from app.api.routes import avatar as avatar_routes  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.models.avatar import AvatarCreateRequest, pipeline_gender  # noqa: E402
from app.services import widget_token  # noqa: E402
from app.services.supabase import supabase_service  # noqa: E402

ALICE = "aaaaaaaa-0000-0000-0000-000000000001"
BOB = "bbbbbbbb-0000-0000-0000-000000000002"
NO_PROFILE = "cccccccc-0000-0000-0000-000000000003"
SHOP = "la-fam-ams.myshopify.com"

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
        self.op, self.payload, self.limit_n, self.is_single = "select", None, None, False

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

    def in_(self, col, vals):
        self.filters.append((col, set(vals)))
        return self

    def limit(self, n, *_a, **_k):
        self.limit_n = n
        return self

    def order(self, *_a, **_k):
        return self

    def single(self):
        self.is_single = True
        return self

    def _match(self, row):
        for col, val in self.filters:
            v = row.get(col)
            if (v not in val) if isinstance(val, set) else (v != val):
                return False
        return True

    def execute(self):
        rows = self.db.tables.setdefault(self.table, [])
        if self.op == "insert":
            if self.table == "fit_passports":
                if not any(u["id"] == self.payload["user_id"] for u in self.db.tables["users"]):
                    raise RuntimeError('insert violates foreign key constraint "fit_passports_user_id_fkey"')
                if any(r["user_id"] == self.payload["user_id"] for r in rows):
                    raise RuntimeError("duplicate key value violates unique constraint (23505)")
            row = {"id": f"row-{len(rows) + 1}", **self.payload}
            rows.append(row)
            return _Result([dict(row)])
        hits = [r for r in rows if self._match(r)]
        if self.op == "update":
            for r in hits:
                r.update(self.payload)
            return _Result([dict(r) for r in hits])
        if self.is_single:
            if len(hits) != 1:
                raise RuntimeError("PGRST116")
            return _Result(dict(hits[0]))
        return _Result([dict(r) for r in hits[: self.limit_n or len(hits)]])


class FakeAuth:
    def get_user(self, _token):
        raise RuntimeError("fake auth: token rejected")


class FakeClient:
    def __init__(self):
        self.auth = FakeAuth()
        self.tables = {
            "users": [{"id": ALICE}, {"id": BOB}],
            "fit_passports": [{"id": "fp-bob", "user_id": BOB, "height": 180, "gender": "male",
                               "status": "completed", "created_at": "2026-09-01T00:00:00+00:00",
                               "updated_at": "2026-09-01T00:00:00+00:00"}],
            "brands": [{"id": "brand-lafam", "shopify_domain": SHOP},
                       {"id": "brand-ramin", "shopify_domain": "ph2360-eq.myshopify.com"}],
            "saved_items": [],
            "garments": [], "draped_meshes": [], "drape_jobs": [],
        }

    def table(self, name):
        return FakeQuery(self, name)


fake = FakeClient()
supabase_service.client = fake
client = TestClient(app)


def bearer(user_id, exp_s=3600, secret=TEST_SECRET):
    tok = jwt.encode({"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + exp_s},
                     secret, algorithm="HS256")
    return {"Authorization": f"Bearer {tok}"}


def require_auth(on: bool):
    get_settings().widget_auth_required = on


# --------------------------------------------------------------------------- 1. tokens

tok = widget_token.issue(ALICE)
check("token verifies for the shopper it was issued to", widget_token.verify(tok) == ALICE)
v, body, sig = tok.split(".")
check("tampered payload is refused",
      widget_token.verify(f"{v}.{widget_token._b64(b'{\"uid\":\"' + BOB.encode() + b'\",\"iat\":1,\"exp\":9999999999}')}.{sig}") is None)
check("tampered signature is refused", widget_token.verify(f"{v}.{body}.{sig[:-2]}xx") is None)
check("expired token is refused", widget_token.verify(widget_token.issue(ALICE, ttl_seconds=60, now=time.time() - 120)) is None)
check("garbage / empty / wrong version are refused",
      all(widget_token.verify(t) is None for t in ("", None, "abc", "v2.a.b", "v1..", f"v9.{body}.{sig}")))
check("the token is not signed with the raw service key",
      widget_token._secret() != os.environ["SUPABASE_SERVICE_KEY"].encode())
check("token lifetime is 30 days", abs(
    __import__("json").loads(widget_token._unb64(body))["exp"] - time.time() - 30 * 86400) < 5)

# --------------------------------------------------------------------------- 2. hand-off


def complete(state, user_id, headers=None):
    return client.post(f"/api/auth/widget-state/{state}/complete",
                       json={"user_id": user_id, "display_name": "A"}, headers=headers or {})


def poll(state):
    return client.get(f"/api/auth/widget-state/{state}").json()


require_auth(False)
check("poll before completion -> no user", poll("state-0001") == {"user_id": None})

r = complete("state-0001", ALICE, bearer(ALICE))
got = poll("state-0001")
check("proven completion -> user_id + a widget token for that user",
      r.status_code == 200 and got.get("user_id") == ALICE and widget_token.verify(got.get("widget_token")) == ALICE,
      str(got))
check("a state is read once", poll("state-0001") == {"user_id": None})

r = complete("state-0002", BOB, bearer(ALICE))
check("signed in as Alice, completing as Bob -> 403, nothing stored",
      r.status_code == 403 and poll("state-0002") == {"user_id": None}, f"{r.status_code}")

r = complete("state-0003", ALICE, {"Authorization": "Bearer not.a.token"})
check("invalid bearer token -> 401 (not treated as anonymous)", r.status_code == 401, str(r.status_code))

r = complete("state-0004", ALICE)
got = poll("state-0004")
check("rollout (flag off): unproven completion still signs the widget in, WITHOUT a widget token",
      r.status_code == 200 and got.get("user_id") == ALICE and "widget_token" not in got, str(got))

complete("state-0005", ALICE, bearer(ALICE))
complete("state-0005", ALICE)  # a stale tab re-completing without a token
check("an unproven re-completion does not strip the token from a proven one",
      widget_token.verify(poll("state-0005").get("widget_token")) == ALICE)

r = complete("x" * 200, ALICE, bearer(ALICE))
check("oversized state token -> 400", r.status_code == 400, str(r.status_code))

require_auth(True)
r = complete("state-0006", ALICE)
check("flag on: unproven completion -> 401, nothing stored",
      r.status_code == 401 and poll("state-0006") == {"user_id": None}, str(r.status_code))
r = complete("state-0007", ALICE, bearer(ALICE))
check("flag on: proven completion still works", r.status_code == 200 and poll("state-0007").get("user_id") == ALICE)

# --------------------------------------------------------------------------- 3. bare user_id

alice_tok = {"X-Widget-Token": widget_token.issue(ALICE)}
bob_tok = {"X-Widget-Token": widget_token.issue(BOB)}

require_auth(False)
check("flag off: /api/avatar/{id} with no proof -> 200 (live widget keeps working)",
      client.get(f"/api/avatar/{BOB}").status_code == 200)
check("flag off: Alice's widget token on Bob's avatar -> 403 (proof for someone else always fails)",
      client.get(f"/api/avatar/{BOB}", headers=alice_tok).status_code == 403)
check("flag off: a tryon.global page naming another user (/embed?user_id=) keeps working",
      client.get(f"/api/avatar/{BOB}", headers=bearer(ALICE)).status_code == 200)

require_auth(True)
check("flag on: /api/avatar/{id} with no proof -> 401", client.get(f"/api/avatar/{BOB}").status_code == 401)
check("flag on: own widget token -> 200", client.get(f"/api/avatar/{BOB}", headers=bob_tok).status_code == 200)
check("flag on: own session -> 200", client.get(f"/api/avatar/{BOB}", headers=bearer(BOB)).status_code == 200)
check("flag on: forged widget token -> 401",
      client.get(f"/api/avatar/{BOB}", headers={"X-Widget-Token": bob_tok["X-Widget-Token"][:-3] + "abc"}).status_code == 401)
check("flag on: someone else's widget token -> 403",
      client.get(f"/api/avatar/{BOB}", headers=alice_tok).status_code == 403)
check("flag on: someone else's session -> 403",
      client.get(f"/api/avatar/{BOB}", headers=bearer(ALICE)).status_code == 403)

q = {"garment_id": "g1", "size": "m", "user_id": BOB}
check("flag on: /api/draping/check no proof -> 401, own token -> 200",
      client.get("/api/draping/check", params=q).status_code == 401
      and client.get("/api/draping/check", params=q, headers=bob_tok).status_code == 200)
w = {"shop": SHOP, "user_id": BOB}
check("flag on: wishlist status no proof -> 401, own token -> 200, other's token -> 403",
      (client.get("/api/wishlist/tee/status", params=w).status_code,
       client.get("/api/wishlist/tee/status", params=w, headers=bob_tok).status_code,
       client.get("/api/wishlist/tee/status", params=w, headers=alice_tok).status_code) == (401, 200, 403))
r = client.post("/api/wishlist", json={"product_id": "tee", "shop_domain": SHOP, "user_id": BOB}, headers=alice_tok)
check("flag on: cannot save to Bob's wishlist with Alice's token -> 403, nothing written",
      r.status_code == 403 and not fake.tables["saved_items"], str(r.status_code))

# One onboarding, two surfaces: the size-only card reads the passport, the try-on reads
# passport + avatar.
r = client.get(f"/api/measurements/passport/{BOB}", headers=bob_tok)
fp_body = r.json() if r.status_code == 200 else {}
check("passport route: status, gender, height and the measured values, for the shopper's own token",
      r.status_code == 200 and fp_body.get("status") == "completed" and fp_body.get("gender") == "male" and fp_body.get("height") == 180
      and isinstance(fp_body.get("measurements"), dict), str(fp_body))
check("passport route returns no avatar: a size-only surface fetches no 3D file",
      not any("avatar" in k or "glb" in str(v).lower() for k, v in fp_body.items()), str(list(fp_body)))
check("avatar route still returns passport + avatar for the try-on",
      "avatar_url" in client.get(f"/api/avatar/{BOB}", headers=bob_tok).json())
check("flag on: passport route no proof -> 401, someone else's token -> 403, own session -> 200",
      (client.get(f"/api/measurements/passport/{BOB}").status_code,
       client.get(f"/api/measurements/passport/{BOB}", headers=alice_tok).status_code,
       client.get(f"/api/measurements/passport/{BOB}", headers=bearer(BOB)).status_code) == (401, 403, 200))
check("passport route: a shopper who never started -> 404",
      client.get(f"/api/measurements/passport/{NO_PROFILE}", headers=bearer(NO_PROFILE)).status_code == 404)
require_auth(False)

# --------------------------------------------------------------------------- 4. create

check("pipeline gender: male/female pass through, other and unknown -> neutral",
      (pipeline_gender("male"), pipeline_gender("female"), pipeline_gender("other"), pipeline_gender("x"))
      == ("male", "female", "neutral", "neutral"))

submitted = []


async def fake_submit(photo_url, height, weight, gender, user_id):
    submitted.append({"gender": gender, "user_id": user_id, "height": height})
    return None  # "RunPod refused": the job fails fast, after we have seen what was sent


avatar_routes.runpod_service.submit_avatar_job = fake_submit
payload = {"user_id": ALICE, "photo_url": "https://example.invalid/p.jpg", "height": 172, "weight": 64,
           "gender": "other", "shop_domain": SHOP}

r = client.post("/api/avatar/create", json=payload, headers=bearer(ALICE))
fp = [p for p in fake.tables["fit_passports"] if p["user_id"] == ALICE]
check("/create with no passport -> 200 and the passport now exists",
      r.status_code == 200 and len(fp) == 1, f"{r.status_code} {r.text[:200]}")
check("the passport holds what the avatar is built from, gender as the shopper chose it",
      bool(fp) and (fp[0]["height"], fp[0]["weight"], fp[0]["gender"]) == (172, 64, "other"), str(fp))
check("the pipeline was sent gender 'neutral', not 'other'",
      submitted and submitted[-1]["gender"] == "neutral" and submitted[-1]["user_id"] == ALICE, str(submitted))

r = client.post("/api/avatar/create", json={**payload, "gender": "female", "height": 170}, headers=bearer(ALICE))
fp = [p for p in fake.tables["fit_passports"] if p["user_id"] == ALICE]
check("/create again -> still one passport, updated in place",
      r.status_code == 200 and len(fp) == 1 and (fp[0]["height"], fp[0]["gender"]) == (170, "female"), str(fp))
check("female goes to the pipeline as female", submitted[-1]["gender"] == "female")

r = client.post("/api/avatar/create", json={**payload, "user_id": NO_PROFILE}, headers=bearer(NO_PROFILE))
check("/create for an account with no profile row -> 409 with a message, no job started",
      r.status_code == 409 and len(submitted) == 2, f"{r.status_code} {r.text[:120]}")

r = client.post("/api/avatar/create", json={**payload, "user_id": BOB}, headers=bearer(ALICE))
check("/create for someone else -> 403", r.status_code == 403, str(r.status_code))

check("drape scope: a known shop -> that store's brand only",
      avatar_routes.drape_scope_for_shop(SHOP) == ["brand-lafam"], str(avatar_routes.drape_scope_for_shop(SHOP)))
check("drape scope: no shop (tryon.global onboarding) -> every store",
      avatar_routes.drape_scope_for_shop(None) is None and avatar_routes.drape_scope_for_shop("  ") is None)
check("drape scope: unknown shop -> every store (never zero drapes)",
      avatar_routes.drape_scope_for_shop("nobody.myshopify.com") is None)

# The fan-out itself: with the scope, only that brand's garments are queued.
from app.services import drape_queue  # noqa: E402

fake.tables["garments"] = [
    {"id": "g-lafam", "brand_id": "brand-lafam", "is_active": True, "obj_sizes": {"m": "a.obj", "l": "b.obj"}, "content_hash": "h1"},
    {"id": "g-ramin", "brand_id": "brand-ramin", "is_active": True, "obj_sizes": {"m": "c.obj"}, "content_hash": "h2"},
]
drape_queue.compute_body_hash = lambda uid, passport: f"body-{uid[:4]}"
drape_queue.compute_legacy_body_hash = lambda uid, passport: None
counts = drape_queue.enqueue_full_drape(BOB, priority=10, brand_ids=avatar_routes.drape_scope_for_shop(SHOP))
queued = {(j["garment_id"], j["size"]) for j in fake.tables["drape_jobs"]}
check("scoped fan-out queues the store's 2 garment-sizes and none of the other store's",
      counts["enqueued"] == 2 and queued == {("g-lafam", "m"), ("g-lafam", "l")}, f"{counts} {queued}")
fake.tables["drape_jobs"].clear()
counts = drape_queue.enqueue_full_drape(BOB, priority=10, brand_ids=avatar_routes.drape_scope_for_shop(None))
check("unscoped fan-out still queues every store (3 garment-sizes)", counts["enqueued"] == 3, str(counts))

# What process_avatar_job does for a store sign-up: this store first, then every other store behind it.
fake.tables["drape_jobs"].clear()
drape_queue.enqueue_full_drape(BOB, priority=10, brand_ids=avatar_routes.drape_scope_for_shop(SHOP))
rest = drape_queue.enqueue_full_drape(BOB, priority=avatar_routes.OTHER_STORES_DRAPE_PRIORITY)
by_key = {(j["garment_id"], j["size"]): j["priority"] for j in fake.tables["drape_jobs"]}
check("store sign-up: this store's garments at priority 10, the other store's queued behind them, no duplicates",
      by_key == {("g-lafam", "m"): 10, ("g-lafam", "l"): 10, ("g-ramin", "m"): avatar_routes.OTHER_STORES_DRAPE_PRIORITY}
      and len(fake.tables["drape_jobs"]) == 3 and rest["enqueued"] == 1, f"{by_key} {rest}")

req = AvatarCreateRequest(**{k: v for k, v in payload.items() if k != "shop_domain"})
check("shop_domain is optional: older clients that do not send it still validate", req.shop_domain is None)

print(f"\n{'ALL CHECKS PASSED' if not failures else f'{failures} CHECK(S) FAILED'}")
sys.exit(1 if failures else 0)
