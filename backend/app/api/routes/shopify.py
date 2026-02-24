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

from fastapi import APIRouter, Query, Request, Response
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


def _verify_hmac(params: dict, secret: str, received_hmac: str) -> bool:
    """Verify Shopify HMAC: params (without hmac) sorted, joined, HMAC-SHA256 with secret."""
    if not secret or not received_hmac:
        return False
    filtered = {k: v for k, v in params.items() if k != "hmac"}
    message = "&".join(f"{k}={v}" for k, v in sorted(filtered.items()))
    expected = hmacc.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return hmacc.compare_digest(expected, received_hmac)


@router.get("/auth")
async def shopify_auth(
    request: Request,
    response: Response,
    shop: str = Query(..., description="Shop myshopify domain"),
):
    """Redirect to Shopify OAuth authorize. Call this when embedded app has no session."""
    if not settings.shopify_client_id or not settings.shopify_client_secret:
        return {"error": "Shopify OAuth not configured"}
    shop = shop.strip().lower()
    if not SHOP_PATTERN.match(shop):
        return {"error": "Invalid shop hostname"}
    state = secrets.token_urlsafe(32)
    base = (settings.backend_public_url or str(request.base_url)).rstrip("/")
    redirect_uri = f"{base}/api/shopify/auth/callback"
    params = {
        "client_id": settings.shopify_client_id,
        "scope": SHOPIFY_AUTH_SCOPE,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    auth_url = f"https://{shop}/admin/oauth/authorize?{urlencode(params)}"
    resp = RedirectResponse(url=auth_url, status_code=302)
    resp.set_cookie(
        STATE_COOKIE,
        state,
        max_age=600,
        httponly=True,
        samesite="lax",
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
    if not _verify_hmac(q, settings.shopify_client_secret, hmac):
        return RedirectResponse(
            url=f"{settings.frontend_app_url.rstrip('/')}/app?error=hmac_failed",
            status_code=302,
        )
    # Exchange code for access_token (form-urlencoded per Shopify docs)
    import httpx
    token_url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        "client_id": settings.shopify_client_id,
        "client_secret": settings.shopify_client_secret,
        "code": code,
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(token_url, data=payload)
    if r.status_code != 200:
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
    resp.delete_cookie(STATE_COOKIE)
    return resp


@router.get("/session")
async def shopify_session(shop: str = Query(..., description="Shop myshopify domain")):
    """Return 200 if we have a stored session (access token) for this shop, 401 otherwise."""
    if not shop or not shop.strip():
        return JSONResponse(content={"ok": False, "reason": "missing_shop"}, status_code=401)
    if supabase.has_shopify_session(shop.strip()):
        return {"ok": True}
    return JSONResponse(content={"ok": False, "reason": "no_session"}, status_code=401)
