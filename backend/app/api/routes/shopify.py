"""
Shopify OAuth and embedded app session.
- GET /api/shopify/auth?shop=... → redirect to Shopify authorize
- GET /api/shopify/auth/callback → exchange code, upsert brand, redirect to frontend /app
- GET /api/shopify/session?shop=... → 200 if we have a token for shop, 401 otherwise
"""
import hashlib
import hmac as hmacc
import secrets
import re
from urllib.parse import urlencode, parse_qsl

from pydantic import BaseModel
from fastapi import APIRouter, Query, Request, Response, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse

from app.config import get_settings
from app.services.supabase import SupabaseService

router = APIRouter()
settings = get_settings()
supabase = SupabaseService()

# Shop hostname: xxx.myshopify.com
SHOP_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-]*\.myshopify\.com$")
SHOPIFY_AUTH_SCOPE = "read_orders"  # Match shopify.app.toml
STATE_COOKIE = "shopify_oauth_state"


def _pilot_shop_domains() -> set[str]:
    raw = (settings.shopify_pilot_shops or "").strip()
    return {s.strip().lower() for s in raw.split(",") if s.strip()}


def _oauth_creds_for_shop(shop: str) -> tuple[str, str] | None:
    """
    Return (client_id, client_secret) for OAuth authorize, token exchange, and callback HMAC.
    Pilot-listed shops use SHOPIFY_CLIENT_ID_PILOT / SECRET when set; others use primary.
    """
    shop = shop.strip().lower()
    if shop in _pilot_shop_domains():
        cid = (settings.shopify_client_id_pilot or "").strip()
        csec = (settings.shopify_client_secret_pilot or "").strip()
        if cid and csec:
            return cid, csec
        return None
    cid = (settings.shopify_client_id or "").strip()
    csec = (settings.shopify_client_secret or "").strip()
    if cid and csec:
        return cid, csec
    return None


def _verify_hmac(params: dict, secret: str, received_hmac: str) -> bool:
    """Verify Shopify HMAC: params (without hmac) sorted, joined, HMAC-SHA256 with secret."""
    if not secret or not received_hmac:
        return False
    filtered = {k: v for k, v in params.items() if k != "hmac"}
    message = "&".join(f"{k}={v}" for k, v in sorted(filtered.items()))
    expected = hmacc.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return hmacc.compare_digest(expected, received_hmac)


@router.get("")
async def shopify_router_ping():
    """Confirm Shopify router is mounted (GET /api/shopify)."""
    return {"status": "ok", "message": "Shopify OAuth routes are available. Use GET /api/shopify/auth?shop=xxx.myshopify.com to start install."}


@router.get("/auth")
async def shopify_auth(
    request: Request,
    response: Response,
    shop: str = Query(..., description="Shop myshopify domain"),
):
    """Redirect to Shopify OAuth authorize. Call this when embedded app has no session."""
    shop = shop.strip().lower()
    if not SHOP_PATTERN.match(shop):
        return {"error": "Invalid shop hostname"}
    creds = _oauth_creds_for_shop(shop)
    if not creds:
        return {"error": "Shopify OAuth not configured for this shop"}
    client_id, _client_secret = creds
    state = secrets.token_urlsafe(32)
    base = (settings.backend_public_url or str(request.base_url)).rstrip("/")
    redirect_uri = f"{base}/api/shopify/auth/callback"
    params = {
        "client_id": client_id,
        "scope": SHOPIFY_AUTH_SCOPE,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    auth_url = f"https://{shop}/admin/oauth/authorize?{urlencode(params)}"
    resp = RedirectResponse(url=auth_url, status_code=302)
    # SameSite=None; Secure so the cookie is sent when Shopify redirects back (cross-site)
    resp.set_cookie(
        STATE_COOKIE,
        state,
        max_age=600,
        httponly=True,
        samesite="none",
        secure=True,
    )
    return resp


@router.get("/auth/callback")
async def shopify_auth_callback(
    request: Request,
    response: Response,
    code: str = Query(None),
    shop: str = Query(None),
    hmac: str = Query(None),
    state: str = Query(None),
):
    """Exchange code for access token, upsert brand, redirect to frontend /app."""
    print(f"[Shopify callback] hit: shop={shop!r} code={'yes' if code else 'no'} state_cookie={'yes' if request.cookies.get(STATE_COOKIE) else 'no'}")
    if not code or not shop or not hmac or not state:
        return RedirectResponse(
            url=f"{settings.frontend_app_url.rstrip('/')}/app?error=missing_params",
            status_code=302,
        )
    shop = shop.strip().lower()
    if not SHOP_PATTERN.match(shop):
        return RedirectResponse(
            url=f"{settings.frontend_app_url.rstrip('/')}/app?error=invalid_shop",
            status_code=302,
        )
    # State cookie is set when WE redirect to OAuth (embedded app flow). When the user
    # uses the custom INSTALL LINK, they never hit /auth, so we never set the cookie.
    # In that case we rely on HMAC (proves Shopify sent the request). If cookie is
    # present, verify it; if missing (install link flow), skip state check.
    state_cookie = request.cookies.get(STATE_COOKIE)
    if state_cookie and not secrets.compare_digest(state_cookie, state):
        return RedirectResponse(
            url=f"{settings.frontend_app_url.rstrip('/')}/app?error=invalid_state",
            status_code=302,
        )
    # Build param map for HMAC (all query params)
    q = dict(parse_qsl(str(request.url.query)))
    creds = _oauth_creds_for_shop(shop)
    if not creds:
        return RedirectResponse(
            url=f"{settings.frontend_app_url.rstrip('/')}/app?error=oauth_not_configured",
            status_code=302,
        )
    _cid, client_secret = creds
    if not _verify_hmac(q, client_secret, hmac):
        return RedirectResponse(
            url=f"{settings.frontend_app_url.rstrip('/')}/app?error=hmac_failed",
            status_code=302,
        )
    import httpx
    token_url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        "client_id": creds[0],
        "client_secret": client_secret,
        "code": code,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(token_url, data=payload)
    except Exception as e:
        print(f"[Shopify callback] token exchange network error: {e}")
        return RedirectResponse(
            url=f"{settings.frontend_app_url.rstrip('/')}/app?error=token_exchange",
            status_code=302,
        )
    if r.status_code != 200:
        print(f"[Shopify callback] token exchange HTTP {r.status_code}: {r.text[:800]}")
        return RedirectResponse(
            url=f"{settings.frontend_app_url.rstrip('/')}/app?error=token_exchange",
            status_code=302,
        )
    data = r.json()
    access_token = data.get("access_token")
    if not access_token:
        return RedirectResponse(
            url=f"{settings.frontend_app_url.rstrip('/')}/app?error=no_token",
            status_code=302,
        )
    brand_id = supabase.upsert_brand_for_shop(shop, access_token)
    if not brand_id:
        print(f"[Shopify callback] db_failed: shop={shop!r}")
        return RedirectResponse(
            url=f"{settings.frontend_app_url.rstrip('/')}/app?error=db_failed",
            status_code=302,
        )
    print(f"[Shopify callback] brand created: shop={shop!r} brand_id={brand_id}")
    app_url = f"{settings.frontend_app_url.rstrip('/')}/app?shop={shop}"
    resp = RedirectResponse(url=app_url, status_code=302)
    resp.delete_cookie(STATE_COOKIE, samesite="none", secure=True)
    return resp


class CompleteInstallBody(BaseModel):
    code: str
    shop: str
    hmac: str
    state: str


@router.post("/complete-install")
async def shopify_complete_install(body: CompleteInstallBody):
    """
    Fallback when redirect to callback is blocked: frontend lands on /app?code=... and calls this
    with the OAuth params. We exchange code and create brand, return { ok: true } or { error }.
    """
    import httpx
    shop = body.shop.strip().lower()
    if not SHOP_PATTERN.match(shop):
        return JSONResponse(content={"ok": False, "error": "invalid_shop"}, status_code=400)
    creds = _oauth_creds_for_shop(shop)
    if not creds:
        return JSONResponse(content={"ok": False, "error": "oauth_not_configured"}, status_code=400)
    client_id, client_secret = creds
    params = {"code": body.code, "shop": body.shop, "hmac": body.hmac, "state": body.state}
    if not _verify_hmac(params, client_secret, body.hmac):
        return JSONResponse(content={"ok": False, "error": "hmac_failed"}, status_code=400)
    token_url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": body.code,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(token_url, data=payload)
    except Exception as e:
        print(f"[Shopify complete-install] network error: {e}")
        return JSONResponse(content={"ok": False, "error": "token_exchange"}, status_code=400)
    if r.status_code != 200:
        print(f"[Shopify complete-install] token exchange failed: {r.status_code} {r.text[:800]}")
        return JSONResponse(content={"ok": False, "error": "token_exchange"}, status_code=400)
    data = r.json()
    access_token = data.get("access_token")
    if not access_token:
        return JSONResponse(content={"ok": False, "error": "no_token"}, status_code=400)
    brand_id = supabase.upsert_brand_for_shop(shop, access_token)
    if not brand_id:
        print(f"[Shopify complete-install] db_failed: shop={shop!r}")
        return JSONResponse(content={"ok": False, "error": "db_failed"}, status_code=500)
    print(f"[Shopify complete-install] brand created: shop={shop!r} brand_id={brand_id}")
    return {"ok": True, "shop": shop}


@router.get("/session")
async def shopify_session(shop: str = Query(..., description="Shop myshopify domain")):
    """Return 200 if we have a stored session (access token) for this shop, 401 otherwise."""
    if not shop or not shop.strip():
        return JSONResponse(content={"ok": False, "reason": "missing_shop"}, status_code=401)
    try:
        if supabase.has_shopify_session(shop.strip()):
            return {"ok": True}
    except Exception as e:
        print(f"[shopify/session] error checking session: {e}")
        return JSONResponse(content={"ok": False, "reason": "internal_error"}, status_code=500)
    return JSONResponse(content={"ok": False, "reason": "no_session"}, status_code=401)


# ============================================
# GDPR Mandatory Webhooks
# Shopify requires these for App Store submission.
# ============================================

@router.post("/webhooks/customers/data_request")
async def gdpr_customers_data_request(request: Request):
    """Shopify sends this when a customer requests their data. We log it for manual processing."""
    from app.api.deps import verify_shopify_webhook
    import json
    body_bytes = await request.body()
    if not verify_shopify_webhook(body_bytes, request.headers.get("X-Shopify-Hmac-Sha256")):
        raise HTTPException(status_code=401, detail="Invalid HMAC")
    body = json.loads(body_bytes)
    shop = body.get("shop_domain", "unknown")
    customer_email = body.get("customer", {}).get("email", "unknown")
    print(f"[GDPR] Data request: shop={shop} customer={customer_email}")
    return {"ok": True}


@router.post("/webhooks/customers/redact")
async def gdpr_customers_redact(request: Request):
    """Shopify sends this when a customer requests deletion. Delete their analytics events."""
    from app.api.deps import verify_shopify_webhook
    import json
    body_bytes = await request.body()
    if not verify_shopify_webhook(body_bytes, request.headers.get("X-Shopify-Hmac-Sha256")):
        raise HTTPException(status_code=401, detail="Invalid HMAC")
    body = json.loads(body_bytes)
    shop = body.get("shop_domain", "unknown")
    customer = body.get("customer", {})
    customer_email = customer.get("email", "")
    print(f"[GDPR] Customer redact: shop={shop} customer={customer_email}")
    try:
        if customer_email:
            supabase.client.table("analytics_events").delete().eq(
                "shop_domain", shop
            ).eq("metadata->>customer_email", customer_email).execute()
    except Exception as e:
        print(f"[GDPR] Redact error: {e}")
    return {"ok": True}


@router.post("/webhooks/shop/redact")
async def gdpr_shop_redact(request: Request):
    """Shopify sends this 48h after app uninstall. Delete all shop data."""
    from app.api.deps import verify_shopify_webhook
    import json
    body_bytes = await request.body()
    if not verify_shopify_webhook(body_bytes, request.headers.get("X-Shopify-Hmac-Sha256")):
        raise HTTPException(status_code=401, detail="Invalid HMAC")
    body = json.loads(body_bytes)
    shop = body.get("shop_domain", "unknown")
    print(f"[GDPR] Shop redact: shop={shop}")
    try:
        supabase.client.table("analytics_events").delete().eq("shop_domain", shop).execute()
        supabase.client.table("brands").update({
            "shopify_access_token": None,
            "is_active": False,
        }).eq("shopify_domain", shop).execute()
    except Exception as e:
        print(f"[GDPR] Shop redact error: {e}")
    return {"ok": True}
