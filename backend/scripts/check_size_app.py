"""
Offline check for the TryOn Size Shopify app (app/api/routes/size_app.py) and the garment leak fix:

  1. /session refuses anything but a session token signed by THIS app for a real shop
     (missing, wrong secret, wrong audience, expired, iss/dest naming different shops).
  2. A first load exchanges the session token for an offline token and stores it; a stored
     token that Shopify rejects is replaced by a fresh exchange.
  3. The plan answer and the setup links come back for the verified shop only.
  4. /webhooks refuses unsigned requests and requests signed by another app's secret.
  5. app/uninstalled clears the token; app_subscriptions/update follows the status.
  6. customers/redact deletes that customer's events in that shop only.
  7. shop/redact deletes the shop's events, unless the shop is also a Tryon brand (then only
     the TryOn Size row goes).
  8. tryon-config for a shop with no brand is a 404, never another brand's garment.

In-process TestClient, FAKE Supabase client, throwaway secrets. No network, no production data.

    cd backend && python3 scripts/check_size_app.py
"""
import base64
import hashlib
import hmac
import json
import os
import sys
import time

CID, SECRET = "size-client-id-test", "size-secret-test-0123456789abcdef"
os.environ["SUPABASE_URL"] = "http://supabase.invalid"
os.environ["SUPABASE_SERVICE_KEY"] = "fake-service-key"
os.environ["SHOPIFY_CLIENT_ID_SIZE"] = CID
os.environ["SHOPIFY_CLIENT_SECRET_SIZE"] = SECRET
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import jwt  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.routes import size_app  # noqa: E402
from app.main import app  # noqa: E402
from app.services.supabase import supabase_service  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        FAILS.append(name)


class _Result:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, db, table):
        self.db, self.table, self.filters, self.op, self.payload, self.n = db, table, [], "select", None, None

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self.filters.append((col, val))
        return self

    def in_(self, col, vals):
        self.filters.append((col, tuple(vals)))
        return self

    def limit(self, n, *_a, **_k):
        self.n = n
        return self

    def upsert(self, row, on_conflict=None):
        self.op, self.payload = "upsert", row
        return self

    def update(self, fields):
        self.op, self.payload = "update", fields
        return self

    def delete(self):
        self.op = "delete"
        return self

    def _match(self, row):
        for col, val in self.filters:
            if "->>" in col:
                base, key = col.split("->>")
                have = (row.get(base) or {}).get(key)
            else:
                have = row.get(col)
            if isinstance(val, tuple):
                if have not in val:
                    return False
            elif have != val:
                return False
        return True

    def execute(self):
        rows = self.db.setdefault(self.table, [])
        self.db.setdefault("_log", []).append((self.op, self.table, list(self.filters)))
        if self.op == "upsert":
            for r in rows:
                if r.get("shop_domain") == self.payload["shop_domain"]:
                    r.update(self.payload)
                    return _Result([r])
            rows.append(dict(self.payload))
            return _Result([self.payload])
        hits = [r for r in rows if self._match(r)]
        if self.op == "delete":
            self.db[self.table] = [r for r in rows if not self._match(r)]
            return _Result(hits)
        if self.op == "update":
            for r in hits:
                r.update(self.payload)
            return _Result(hits)
        return _Result(hits[: self.n] if self.n else hits)


class FakeClient:
    def __init__(self):
        self.db = {}

    def table(self, name):
        return FakeQuery(self.db, name)


fake = FakeClient()
supabase_service._client = fake
type(supabase_service).client = property(lambda self: fake)  # every module shares this instance

# Shopify stand-ins: record what was called, never touch the network.
calls = {"exchange": 0, "sync": 0}
reject_tokens = set()


async def fake_exchange(shop, session_token):
    calls["exchange"] += 1
    return f"offline-{shop}-{calls['exchange']}", ""


async def fake_sync(shop, token):
    calls["sync"] += 1
    if token in reject_tokens:
        raise PermissionError("rejected")
    size_app._save(shop, active=True, plan_name="TryOn Size", plan_status="ACTIVE")
    return True, "TryOn Size", "ACTIVE"


size_app._token_exchange = fake_exchange
size_app.sync_plan = fake_sync
size_app._stats = lambda shop, days=30: (size_app.SizeAppStats(sessions=3), True)

client = TestClient(app)
SHOP = "demo-store.myshopify.com"


def session_token(secret=SECRET, aud=CID, shop=SHOP, iss_shop=None, exp_in=60):
    now = int(time.time())
    return jwt.encode({
        "iss": f"https://{iss_shop or shop}/admin", "dest": f"https://{shop}", "aud": aud,
        "sub": "42", "exp": now + exp_in, "nbf": now - 5, "iat": now - 5, "jti": "x", "sid": "y",
    }, secret, algorithm="HS256")


def post_session(token=None):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post("/api/size-app/session", headers=h)


# 1. Refusals
check("no token -> 401", post_session().status_code == 401)
check("other app's secret -> 401", post_session(session_token(secret="other-secret-xxxxxxxxxxxxxxxx")).status_code == 401)
check("wrong audience -> 401", post_session(session_token(aud="ec47b40d60204a8d7cf80aa50e313d19")).status_code == 401)
check("expired -> 401", post_session(session_token(exp_in=-120)).status_code == 401)
check("iss and dest name different shops -> 401",
      post_session(session_token(iss_shop="evil.myshopify.com")).status_code == 401)
check("dest not a myshopify host -> 401", post_session(session_token(shop="evil.com")).status_code == 401)
check("no exchange happened for any refused token", calls["exchange"] == 0)

# 2 + 3. First load, then a rejected stored token
r = post_session(session_token())
body = r.json() if r.status_code == 200 else {}
check("valid token -> 200", r.status_code == 200, r.text[:200])
check("first load exchanged a token", calls["exchange"] == 1)
row = next((x for x in fake.db.get("size_app_installs", []) if x["shop_domain"] == SHOP), {})
check("offline token stored for the verified shop", row.get("access_token") == f"offline-{SHOP}-1")
check("plan answer returned", body.get("active") is True and body.get("plan_name") == "TryOn Size")
check("pricing link is this store's plan page",
      body.get("pricing_url") == "https://admin.shopify.com/store/demo-store/charges/tryon-size/pricing_plans")
check("theme editor link adds this app's block",
      f"addAppBlockId={CID}/find-my-size" in (body.get("theme_editor_url") or "")
      and (body.get("theme_editor_url") or "").startswith(f"https://{SHOP}/admin/themes/current/editor"))

r = post_session(session_token())
check("second load reuses the stored token", r.status_code == 200 and calls["exchange"] == 1)
reject_tokens.add(f"offline-{SHOP}-1")
r = post_session(session_token())
row = next((x for x in fake.db["size_app_installs"] if x["shop_domain"] == SHOP), {})
check("rejected stored token -> fresh exchange", r.status_code == 200 and calls["exchange"] == 2
      and row.get("access_token") == f"offline-{SHOP}-2")


# 4. Webhook signatures
def webhook(topic, payload, secret=SECRET, sign=True, shop=SHOP):
    raw = json.dumps(payload).encode()
    h = {"X-Shopify-Topic": topic, "X-Shopify-Shop-Domain": shop, "Content-Type": "application/json"}
    if sign:
        h["X-Shopify-Hmac-Sha256"] = base64.b64encode(hmac.new(secret.encode(), raw, hashlib.sha256).digest()).decode()
    return client.post("/api/size-app/webhooks", content=raw, headers=h)


check("unsigned webhook -> 401", webhook("app/uninstalled", {}, sign=False).status_code == 401)
check("webhook signed by another app -> 401", webhook("app/uninstalled", {}, secret="la-fam-secret").status_code == 401)
check("unknown topic -> 400", webhook("orders/paid", {}).status_code == 400)

# 5. Uninstall and subscription updates
r = webhook("app/uninstalled", {"myshopify_domain": SHOP})
row = next((x for x in fake.db["size_app_installs"] if x["shop_domain"] == SHOP), {})
check("app/uninstalled -> token cleared, inactive, row kept",
      r.status_code == 200 and row.get("access_token") is None and row.get("active") is False and row.get("uninstalled_at"))
r = webhook("app_subscriptions/update", {"app_subscription": {"name": "TryOn Size", "status": "ACTIVE"}})
row = next((x for x in fake.db["size_app_installs"] if x["shop_domain"] == SHOP), {})
check("subscription ACTIVE -> active", r.status_code == 200 and row.get("active") is True)
webhook("app_subscriptions/update", {"app_subscription": {"name": "TryOn Size", "status": "CANCELLED"}})
row = next((x for x in fake.db["size_app_installs"] if x["shop_domain"] == SHOP), {})
check("subscription CANCELLED -> inactive", row.get("active") is False and row.get("plan_status") == "CANCELLED")

# 6. customers/redact
fake.db["analytics_events"] = [
    {"id": 1, "shop_domain": SHOP, "event_data": {"customer_id": "777"}},
    {"id": 2, "shop_domain": SHOP, "event_data": {"customer_email": "a@b.c"}},
    {"id": 3, "shop_domain": SHOP, "event_data": {"customer_id": "888"}},
    {"id": 4, "shop_domain": "la-fam-ams.myshopify.com", "event_data": {"customer_id": "777"}},
]
r = webhook("customers/redact", {"shop_domain": SHOP, "customer": {"id": 777, "email": "a@b.c"}})
left = sorted(e["id"] for e in fake.db["analytics_events"])
check("customers/redact deletes that customer in that shop only", r.status_code == 200 and left == [3, 4], str(left))
check("customers/data_request -> 200", webhook("customers/data_request", {"shop_domain": SHOP, "data_request": {"id": 1}}).status_code == 200)

# 7. shop/redact, with and without a Tryon brand on the same shop
fake.db["brands"] = [{"id": "b-lafam", "shopify_domain": "la-fam-ams.myshopify.com"}]
fake.db["size_app_installs"].append({"shop_domain": "la-fam-ams.myshopify.com", "active": False})
fake.db["tryon_sessions"] = [{"id": "s1", "shop_domain": SHOP}, {"id": "s2", "shop_domain": "la-fam-ams.myshopify.com"}]
r = webhook("shop/redact", {"shop_domain": "la-fam-ams.myshopify.com"}, shop="la-fam-ams.myshopify.com")
check("shop/redact on a Tryon brand keeps its events and sessions",
      r.status_code == 200 and any(e["id"] == 4 for e in fake.db["analytics_events"])
      and any(s["id"] == "s2" for s in fake.db["tryon_sessions"]))
check("shop/redact on a Tryon brand removes its TryOn Size row",
      not any(x["shop_domain"] == "la-fam-ams.myshopify.com" for x in fake.db["size_app_installs"]))
r = webhook("shop/redact", {"shop_domain": SHOP})
check("shop/redact on a size-only shop deletes its events, sessions and row",
      r.status_code == 200 and not any(e["shop_domain"] == SHOP for e in fake.db["analytics_events"])
      and not any(s["shop_domain"] == SHOP for s in fake.db["tryon_sessions"])
      and not any(x["shop_domain"] == SHOP for x in fake.db["size_app_installs"]))

# 8. Garment leak
fake.db["garments"] = [{"id": "g1", "brand_id": "b-lafam", "shopify_product_handle": "tshirt", "shopify_product_id": "1"}]
fake.db["_log"] = []
r = client.get("/api/products/tshirt/tryon-config", params={"shop": "new-size-shop.myshopify.com"})
garment_reads = [x for x in fake.db["_log"] if x[1] == "garments"]
check("tryon-config for a shop with no brand -> 404", r.status_code == 404, str(r.status_code))
check("... without reading any garment", garment_reads == [], str(garment_reads))

print()
print(f"{len(FAILS)} failed" if FAILS else "all passed")
sys.exit(1 if FAILS else 0)
