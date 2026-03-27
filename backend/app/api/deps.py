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


def verify_shopify_webhook(body: bytes, hmac_header: str | None) -> bool:
    """
    Verify Shopify webhook HMAC-SHA256 signature.
    In debug mode, allows requests when the secret is not configured.
    In production, rejects all requests without a valid secret + signature.
    """
    settings = get_settings()
    secret = settings.shopify_webhook_secret or ""
    if not secret:
        if settings.debug:
            return True
        return False
    if not hmac_header:
        return False
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    computed = base64.b64encode(digest).decode("ascii")
    return hmac.compare_digest(computed, hmac_header)
