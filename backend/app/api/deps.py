"""
Shared authentication and verification dependencies for FastAPI routes.
"""
import base64
import hashlib
import hmac
import logging

from dataclasses import dataclass

import jwt
from cachetools import TTLCache
from fastapi import Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """
    Verify the Supabase access token and return the authenticated user_id.
    Strategy: fast local JWT check first, then Supabase Auth API fallback
    so auth works even if the JWT secret is misconfigured.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authorization required")

    token = credentials.credentials
    settings = get_settings()

    # --- Fast path: local HS256 verification ---
    if settings.supabase_jwt_secret:
        try:
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                audience="authenticated",
                algorithms=["HS256"],
            )
            user_id = payload.get("sub")
            if user_id:
                return user_id
        except jwt.ExpiredSignatureError:
            logger.debug("Local JWT: token expired, trying Supabase Auth API")
        except jwt.PyJWTError as exc:
            logger.warning("Local JWT verification failed (%s), trying Supabase Auth API", exc)
    else:
        logger.warning("SUPABASE_JWT_SECRET not set — using Supabase Auth API for verification")

    # --- Fallback: verify via Supabase Auth REST API ---
    try:
        from app.services.supabase import supabase_service
        resp = supabase_service.client.auth.get_user(token)
        if resp and resp.user and resp.user.id:
            logger.info("Token verified via Supabase Auth API (user=%s)", resp.user.id)
            return str(resp.user.id)
    except Exception as exc:
        logger.warning("Supabase Auth API verification also failed: %s", exc)

    raise HTTPException(status_code=401, detail="Invalid or expired token")



# ---------------------------------------------------------------------------
# Brand scoping: which Shopify store(s) the signed-in caller may read.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BrandScope:
    shop: str       # canonical "<slug>.myshopify.com"
    brand_id: str


# user_id -> tuple of (canonical shop, brand_id). A dashboard load fires ~18 analytics
# calls, so cache briefly instead of hitting `brands` 18 times. Failed lookups are not cached.
_brand_scope_cache: TTLCache = TTLCache(maxsize=1024, ttl=60)


def normalize_shop_domain(raw: str | None) -> str:
    """Lowercase, strip scheme/path/trailing slash, and expand a bare slug to slug.myshopify.com.
    Matches how brands.shopify_domain and analytics_events.shop_domain are stored."""
    from app.services.supabase import _canonical_shopify_domain

    s = (raw or "").strip().lower()
    for prefix in ("https://", "http://"):
        if s.startswith(prefix):
            s = s[len(prefix):]
    s = s.split("/", 1)[0].strip()
    return _canonical_shopify_domain(s) if s else ""


def _brand_scopes_for_user(user_id: str) -> tuple[tuple[str, str], ...]:
    cached = _brand_scope_cache.get(user_id)
    if cached is not None:
        return cached
    from app.services.supabase import supabase_service

    try:
        r = (
            supabase_service.client.table("brands")
            .select("id,shopify_domain")
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as exc:
        logger.error("Brand lookup failed for user=%s: %s", user_id[:8], exc)
        raise HTTPException(status_code=503, detail="Could not load your brand. Try again.")
    rows = r.data or []
    if not rows:
        raise HTTPException(status_code=403, detail="No brand account for this user")
    scopes = tuple(
        (normalize_shop_domain(row.get("shopify_domain")), str(row["id"]))
        for row in rows
        if normalize_shop_domain(row.get("shopify_domain"))
    )
    _brand_scope_cache[user_id] = scopes
    return scopes


def get_brand_scope(
    user_id: str = Depends(get_current_user_id),
    shop: str | None = Query(None, description="Shopify domain; must be one of the caller's stores"),
) -> BrandScope:
    """
    Resolve the store the caller may read. 401 (no/invalid token) comes from get_current_user_id.
    - `shop` given and not one of the caller's stores -> 403
    - `shop` missing/empty -> the caller's only store (400 if they own several)
    - caller's brand has no shopify_domain -> 403
    """
    scopes = _brand_scopes_for_user(user_id)
    if not scopes:
        raise HTTPException(status_code=403, detail="No Shopify store linked")
    requested = normalize_shop_domain(shop)
    if requested:
        for domain, brand_id in scopes:
            if domain == requested:
                return BrandScope(shop=domain, brand_id=brand_id)
        raise HTTPException(status_code=403, detail="Not your store")
    if len(scopes) > 1:
        raise HTTPException(status_code=400, detail="Several stores linked; pass ?shop=")
    domain, brand_id = scopes[0]
    return BrandScope(shop=domain, brand_id=brand_id)


def get_brand_shop(scope: BrandScope = Depends(get_brand_scope)) -> str:
    """Canonical shop_domain the caller may read (see get_brand_scope)."""
    return scope.shop

def _webhook_hmac_secrets() -> list[str]:
    """Secrets Shopify may use to sign webhooks (primary app, optional pilot app, optional la fam app, optional explicit webhook secret)."""
    settings = get_settings()
    seen: set[str] = set()
    out: list[str] = []
    for s in (
        settings.shopify_webhook_secret,
        settings.shopify_client_secret,
        settings.shopify_client_secret_pilot,
        settings.shopify_client_secret_lafam,
    ):
        t = (s or "").strip()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def verify_shopify_webhook(body: bytes, hmac_header: str | None) -> bool:
    """
    Verify Shopify webhook HMAC-SHA256 signature.
    Tries each configured secret (webhook override, primary client secret, pilot client secret)
    so both the public app and a custom-distribution pilot can post to the same URLs.
    In debug mode, allows requests when no secret is configured.
    In production, rejects all requests without a valid secret + signature.
    """
    settings = get_settings()
    secrets_list = _webhook_hmac_secrets()
    if not secrets_list:
        if settings.debug:
            return True
        return False
    if not hmac_header:
        return False
    for secret in secrets_list:
        digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
        computed = base64.b64encode(digest).decode("ascii")
        if hmac.compare_digest(computed, hmac_header):
            return True
    return False
