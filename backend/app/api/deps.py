"""
Shared authentication and verification dependencies for FastAPI routes.
"""
import base64
import hashlib
import hmac
import logging

import jwt
from fastapi import Depends, HTTPException, Request
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


def _webhook_hmac_secrets() -> list[str]:
    """Secrets Shopify may use to sign webhooks (primary app, optional pilot app, per-shop dedicated apps, optional explicit webhook secret)."""
    from app.config import get_shop_apps
    settings = get_settings()
    seen: set[str] = set()
    out: list[str] = []
    candidates = [
        settings.shopify_webhook_secret,
        settings.shopify_client_secret,
        settings.shopify_client_secret_pilot,
    ]
    candidates.extend((app.get("client_secret") or "") for app in get_shop_apps().values())
    for s in candidates:
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
