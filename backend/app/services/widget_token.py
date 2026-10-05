"""
Widget tokens: proof that the store-page widget was signed in as a given shopper.

The widget runs in an iframe on the brand's store and cannot hold the shopper's
tryon.global session, so until now it identified the shopper to the API with a bare
user_id. Anyone who learned a user_id could read that shopper's avatar and
measurements. A widget token closes that: the backend issues it once, when a signed-in
tryon.global page completes the widget's sign-in hand-off, and the widget presents it
with every request that names a user_id.

Format:  v1.<base64url(json {"uid", "iat", "exp"})>.<base64url(HMAC-SHA256)>

It is signed, not encrypted: it carries nothing but the user id and two timestamps. It
grants only what the widget needs (read the shopper's own avatar and drapes, save to
their wishlist); it is not a Supabase session and cannot sign in to tryon.global.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Optional

from app.config import get_settings

_VERSION = "v1"


def _secret() -> bytes:
    """WIDGET_TOKEN_SECRET if set; otherwise a key derived from the service key, so the
    feature works without new configuration and the service key itself never signs
    anything that leaves the server."""
    s = get_settings()
    explicit = (s.widget_token_secret or "").strip()
    if explicit:
        return explicit.encode()
    return hmac.new(s.supabase_service_key.encode(), b"tryon-widget-token-v1", hashlib.sha256).digest()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(body: str) -> str:
    return _b64(hmac.new(_secret(), f"{_VERSION}.{body}".encode(), hashlib.sha256).digest())


def issue(user_id: str, ttl_seconds: Optional[int] = None, now: Optional[float] = None) -> str:
    issued = int(now if now is not None else time.time())
    ttl = ttl_seconds if ttl_seconds is not None else get_settings().widget_token_ttl_days * 86400
    body = _b64(json.dumps({"uid": user_id, "iat": issued, "exp": issued + ttl}, separators=(",", ":")).encode())
    return f"{_VERSION}.{body}.{_sign(body)}"


def verify(token: Optional[str], now: Optional[float] = None) -> Optional[str]:
    """The user id a token was issued for, or None if it is malformed, forged or expired."""
    if not token or not isinstance(token, str):
        return None
    parts = token.strip().split(".")
    if len(parts) != 3 or parts[0] != _VERSION:
        return None
    _, body, sig = parts
    if not hmac.compare_digest(_sign(body), sig):
        return None
    try:
        payload = json.loads(_unb64(body))
        uid, exp = payload["uid"], int(payload["exp"])
    except (ValueError, KeyError, TypeError):
        return None
    if not isinstance(uid, str) or not uid:
        return None
    if (now if now is not None else time.time()) >= exp:
        return None
    return uid
