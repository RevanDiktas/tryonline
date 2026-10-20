"""
"TryOn Size": the public Shopify app that is only the Find my size button.

One login: the embedded admin page (frontend /size-app) sends Shopify's session token. We
verify it here (HS256 with the app secret, aud = client id) and swap it for an offline Admin
API token (token exchange). No TryOn account or password inside Shopify, and the shop comes
from the verified token, never from a typed domain.

Billing is Shopify Managed Pricing: Shopify hosts the plan page and owns the subscription. We
read the active subscription and mirror "has a plan" into an app-data metafield
(tryon_size.active) that the theme block reads, so a shop without a plan shows no button and
the storefront makes no extra request to find that out.

Routes (mounted at /api/size-app):
- POST /session     Authorization: Bearer <session token>  -> install state, plan, setup links, 30-day stats
- POST /webhooks    app/uninstalled, app_subscriptions/update and the three compliance topics
"""
import base64
import hashlib
import hmac
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
import jwt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.config import get_settings
from app.services.supabase import supabase_service

router = APIRouter()

API_VERSION = "2026-01"
BLOCK_HANDLE = "find-my-size"  # extensions/size-widget/blocks/find-my-size.liquid
METAFIELD_NAMESPACE = "tryon_size"
METAFIELD_KEY = "active"
SHOP_RE = re.compile(r"^[a-z0-9][a-z0-9\-]*\.myshopify\.com$")
TABLE = "size_app_installs"


class SizeAppStats(BaseModel):
    days: int = 30
    sessions: int = 0
    sizes_given: int = 0
    added_to_cart: int = 0
    orders: int = 0
    revenue: float = 0.0
    top_sizes: dict[str, int] = {}


class SizeAppSessionResponse(BaseModel):
    shop: str
    active: bool
    plan_name: Optional[str] = None
    plan_status: Optional[str] = None
    pricing_url: str
    theme_editor_url: str
    seen_on_store: bool
    stats: SizeAppStats


def _creds() -> tuple[str, str]:
    s = get_settings()
    cid = (s.shopify_client_id_size or "").strip()
    sec = (s.shopify_client_secret_size or "").strip()
    if not cid or not sec:
        raise HTTPException(status_code=503, detail="TryOn Size app credentials are not configured")
    return cid, sec


def verify_session_token(token: str) -> str:
    """Return the shop (*.myshopify.com) a Shopify session token was issued for, or 401.
    Checks signature, audience, expiry and that iss and dest name the same shop."""
    cid, sec = _creds()
    try:
        claims = jwt.decode(
            token, sec, algorithms=["HS256"], audience=cid, leeway=10,
            options={"require": ["exp", "nbf", "iss", "dest", "aud"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid session token: {exc}")
    dest = str(claims.get("dest") or "")
    iss = str(claims.get("iss") or "")
    shop = dest.removeprefix("https://").strip("/").lower()
    if not SHOP_RE.match(shop) or not iss.startswith(f"https://{shop}/"):
        raise HTTPException(status_code=401, detail="Session token names no valid shop")
    return shop


async def _token_exchange(shop: str, session_token: str) -> tuple[str, str]:
    """Swap a session token for an offline access token. Returns (access_token, scope)."""
    cid, sec = _creds()
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"https://{shop}/admin/oauth/access_token",
            json={
                "client_id": cid,
                "client_secret": sec,
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "subject_token": session_token,
                "subject_token_type": "urn:ietf:params:oauth:token-type:id_token",
                "requested_token_type": "urn:shopify:params:oauth:token-type:offline-access-token",
            },
        )
    if r.status_code != 200:
        print(f"[size-app] token exchange failed shop={shop} status={r.status_code} body={r.text[:300]}")
        raise HTTPException(status_code=401, detail="Shopify token exchange failed")
    data = r.json()
    return data["access_token"], data.get("scope") or ""


async def _admin_graphql(shop: str, token: str, query: str, variables: Optional[dict] = None) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"https://{shop}/admin/api/{API_VERSION}/graphql.json",
            headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"},
            json={"query": query, "variables": variables or {}},
        )
    if r.status_code == 401:
        raise PermissionError("access token rejected")
    r.raise_for_status()
    body = r.json()
    if body.get("errors"):
        raise RuntimeError(f"GraphQL errors: {body['errors']}")
    return body.get("data") or {}


PLAN_QUERY = """
query {
  currentAppInstallation {
    id
    activeSubscriptions { name status }
  }
}
"""

SET_ACTIVE_MUTATION = """
mutation SetActive($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    userErrors { field message }
  }
}
"""


async def sync_plan(shop: str, token: str) -> tuple[bool, Optional[str], Optional[str]]:
    """Read the shop's subscription from Shopify, write tryon_size.active for the block, and
    store it. Returns (active, plan_name, plan_status). ACTIVE covers the free trial."""
    data = await _admin_graphql(shop, token, PLAN_QUERY)
    inst = data.get("currentAppInstallation") or {}
    subs = inst.get("activeSubscriptions") or []
    live = next((s for s in subs if s.get("status") == "ACTIVE"), None)
    current = live or (subs[0] if subs else None)
    active = live is not None
    res = await _admin_graphql(shop, token, SET_ACTIVE_MUTATION, {"metafields": [{
        "ownerId": inst["id"],
        "namespace": METAFIELD_NAMESPACE,
        "key": METAFIELD_KEY,
        "type": "boolean",
        "value": "true" if active else "false",
    }]})
    errors = (res.get("metafieldsSet") or {}).get("userErrors") or []
    if errors:
        raise RuntimeError(f"metafieldsSet: {errors}")
    plan_name = current.get("name") if current else None
    plan_status = current.get("status") if current else None
    _save(shop, active=active, plan_name=plan_name, plan_status=plan_status)
    return active, plan_name, plan_status


def _row(shop: str) -> Optional[dict]:
    r = supabase_service.client.table(TABLE).select("*").eq("shop_domain", shop).limit(1).execute()
    return r.data[0] if r.data else None


def _save(shop: str, **fields: Any) -> None:
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    supabase_service.client.table(TABLE).upsert({"shop_domain": shop, **fields}, on_conflict="shop_domain").execute()


def _links(shop: str) -> tuple[str, str]:
    cid, _ = _creds()
    store = shop.removesuffix(".myshopify.com")
    handle = (get_settings().shopify_app_handle_size or "tryon-size").strip()
    pricing = f"https://admin.shopify.com/store/{store}/charges/{handle}/pricing_plans"
    editor = (
        f"https://{shop}/admin/themes/current/editor?template=product"
        f"&addAppBlockId={cid}/{BLOCK_HANDLE}&target=mainSection"
    )
    return pricing, editor


def _stats(shop: str, days: int = 30) -> tuple[SizeAppStats, bool]:
    """Last `days` of the size card on this shop, from the same summary the brand dashboard
    uses. Second value: whether the card has been seen live on the store at all."""
    from app.api.routes.analytics import (
        ATTRIBUTION_WINDOW_DAYS, _day_bounds, load_cohort_events, size_finder_summary,
    )
    end_d = datetime.now(timezone.utc).date()
    start_d = end_d - timedelta(days=days - 1)
    events = load_cohort_events(shop, start_d, end_d)
    start, end = _day_bounds(start_d, end_d)
    s = size_finder_summary(events, start, end, ATTRIBUTION_WINDOW_DAYS)
    shown = sum(s.recommended_distribution.values())
    top = dict(sorted(s.recommended_distribution.items(), key=lambda kv: -kv[1])[:5])
    stats = SizeAppStats(
        days=days, sessions=s.sessions, sizes_given=shown,
        added_to_cart=sum(s.atc_by_basis.values()), orders=sum(s.purchases_by_basis.values()),
        revenue=round(s.revenue, 2), top_sizes=top,
    )
    return stats, bool(events)


@router.post("/session", response_model=SizeAppSessionResponse)
async def size_app_session(request: Request):
    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing session token")
    session_token = auth[7:].strip()
    shop = verify_session_token(session_token)

    row = _row(shop)
    token = (row or {}).get("access_token")
    try:
        if not token:
            raise PermissionError("no token yet")
        active, plan_name, plan_status = await sync_plan(shop, token)
    except PermissionError:
        # First load after install, a reinstall, or a revoked token: exchange a fresh one.
        token, scope = await _token_exchange(shop, session_token)
        _save(shop, access_token=token, scope=scope, uninstalled_at=None,
              **({} if row else {"installed_at": datetime.now(timezone.utc).isoformat()}))
        active, plan_name, plan_status = await sync_plan(shop, token)

    pricing, editor = _links(shop)
    try:
        stats, seen = _stats(shop)
    except Exception as e:
        print(f"[size-app] stats failed shop={shop}: {e}")
        stats, seen = SizeAppStats(), False
    return SizeAppSessionResponse(
        shop=shop, active=active, plan_name=plan_name, plan_status=plan_status,
        pricing_url=pricing, theme_editor_url=editor, seen_on_store=seen, stats=stats,
    )


def _verify_webhook(body: bytes, header: Optional[str]) -> bool:
    _, sec = _creds()
    if not header:
        return False
    digest = base64.b64encode(hmac.new(sec.encode(), body, hashlib.sha256).digest()).decode()
    return hmac.compare_digest(digest, header)


@router.post("/webhooks")
async def size_app_webhooks(request: Request):
    """Every TryOn Size webhook, told apart by X-Shopify-Topic. Signed with this app's secret
    only, so a webhook from the other apps can never act on these rows (or the reverse)."""
    body = await request.body()
    if not _verify_webhook(body, request.headers.get("X-Shopify-Hmac-Sha256")):
        raise HTTPException(status_code=401, detail="Invalid HMAC")
    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    topic = (request.headers.get("X-Shopify-Topic") or "").strip()
    shop = (request.headers.get("X-Shopify-Shop-Domain") or payload.get("shop_domain") or "").strip().lower()
    if not SHOP_RE.match(shop):
        raise HTTPException(status_code=400, detail="No shop on webhook")

    if topic == "app/uninstalled":
        # Keep the row (a reinstall within 48h finds it); shop/redact removes it.
        _save(shop, access_token=None, active=False, plan_status="CANCELLED",
              uninstalled_at=datetime.now(timezone.utc).isoformat())
    elif topic == "app_subscriptions/update":
        sub = payload.get("app_subscription") or {}
        status = str(sub.get("status") or "").upper()
        _save(shop, plan_name=sub.get("name"), plan_status=status, active=status == "ACTIVE")
        row = _row(shop)
        if row and row.get("access_token"):
            try:
                await sync_plan(shop, row["access_token"])
            except Exception as e:
                # The row is already right; the metafield follows on the next admin load.
                print(f"[size-app] metafield sync after subscription update failed shop={shop}: {e}")
    elif topic == "customers/data_request":
        # TryOn Size subscribes to no order or customer topics and reads no customer data from
        # Shopify, so there is nothing keyed by a Shopify customer to export.
        print(f"[size-app] customers/data_request shop={shop} request={(payload.get('data_request') or {}).get('id')}")
    elif topic == "customers/redact":
        customer = payload.get("customer") or {}
        for field, value in (("customer_id", str(customer.get("id") or "")),
                             ("customer_email", customer.get("email") or "")):
            if value:
                supabase_service.client.table("analytics_events").delete().eq(
                    "shop_domain", shop).eq(f"event_data->>{field}", value).execute()
    elif topic == "shop/redact":
        # 48h after uninstall. If the shop is also a Tryon brand (another of our apps), its
        # events belong to that install too: delete only this app's row.
        supabase_service.client.table(TABLE).delete().eq("shop_domain", shop).execute()
        if not supabase_service.get_brand_by_shopify_domain(shop):
            supabase_service.client.table("analytics_events").delete().eq("shop_domain", shop).execute()
            supabase_service.client.table("tryon_sessions").delete().eq("shop_domain", shop).execute()
    else:
        raise HTTPException(status_code=400, detail=f"Unhandled topic {topic!r}")
    return {"ok": True}
