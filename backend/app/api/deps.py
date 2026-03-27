"""
Shared authentication and verification dependencies for FastAPI routes.
"""
import base64
import hashlib
import hmac

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

_bearer = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """
    Verify the Supabase access token and return the authenticated user_id.
    Raises 401 if token is missing/invalid, 503 if JWT secret is not configured.
    """
    settings = get_settings()
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=503,
            detail="Authentication not configured (missing SUPABASE_JWT_SECRET)",
        )
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail="Authorization required",
        )
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.supabase_jwt_secret,
            audience="authenticated",
            algorithms=["HS256"],
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


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
