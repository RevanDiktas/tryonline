"""
Widget authentication state exchange.

When the TryOn widget runs inside a Shopify iframe, it cannot do OAuth via
redirect (Google blocks iframes) or rely on window.opener.postMessage
(Google's COOP header nullifies window.opener after navigating through their
OAuth page).  BroadcastChannel is also unusable because Chrome partitions it
by top-level site, so the iframe (top-level: myshopify.com) and the popup
(top-level: tryon.global) live in different partitions.

Solution: backend-mediated state exchange.

1. Widget generates a random state token and opens a popup for OAuth.
2. Widget polls  GET /api/auth/widget-state/{token}  until a result appears.
3. After OAuth, the callback page POSTs the authenticated user_id to
   POST /api/auth/widget-state/{token}/complete, with its Supabase bearer token.
4. The next poll from the widget picks up the user_id and a widget token
   (app/services/widget_token.py), and the widget reloads.

The completing page must prove who it is: with a bearer token, the user_id in the body
has to be the token's user. A widget token is only ever issued for a completion that
was proven this way, so nobody can mint one for someone else's user_id. Completions
without a bearer token are still accepted while WIDGET_AUTH_REQUIRED is off (pages
deployed before this change), but they never yield a widget token.
"""

import logging
from time import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_optional_user_id
from app.config import get_settings
from app.services import widget_token

logger = logging.getLogger(__name__)

router = APIRouter()

_widget_states: dict[str, dict] = {}
_STATE_TTL = 3600  # 1 hour: a link_state is completed at sign-up, then read after onboarding
_MAX_TOKEN_LEN = 128


def _cleanup() -> None:
    now = time()
    stale = [k for k, v in _widget_states.items() if now - v["ts"] > _STATE_TTL]
    for k in stale:
        del _widget_states[k]


class WidgetStateComplete(BaseModel):
    user_id: str
    display_name: str = ""


@router.get("/widget-state/{token}")
async def get_widget_state(token: str):
    """Poll endpoint: returns user_id when the popup has completed OAuth. One read: the
    state is consumed. `widget_token` is present when the completion was authenticated."""
    _cleanup()
    state = _widget_states.get(token)
    if state and state.get("user_id"):
        uid = state["user_id"]
        name = state.get("display_name", "")
        del _widget_states[token]
        out = {"user_id": uid, "display_name": name}
        if state.get("verified"):
            out["widget_token"] = widget_token.issue(uid)
        return out
    return {"user_id": None}


@router.post("/widget-state/{token}/complete")
async def complete_widget_state(
    token: str,
    body: WidgetStateComplete,
    bearer_user_id: str | None = Depends(get_optional_user_id),
):
    """Called by the auth callback page after successful OAuth."""
    if not token or len(token) > _MAX_TOKEN_LEN:
        raise HTTPException(status_code=400, detail="Invalid state token")
    if bearer_user_id is not None and bearer_user_id != body.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if bearer_user_id is None:
        if get_settings().widget_auth_required:
            raise HTTPException(status_code=401, detail="Authorization required")
        logger.warning(
            "Widget state completed without proof (token=%s user=%s); WIDGET_AUTH_REQUIRED is off",
            token[:8], body.user_id[:8],
        )
    _cleanup()
    existing = _widget_states.get(token)
    # A proven completion is never downgraded by a later unproven one for the same state
    # (goBackToStore re-completes it; a stale tab may do so without a token).
    if existing and existing.get("verified") and bearer_user_id is None and existing.get("user_id") == body.user_id:
        existing["ts"] = time()
        return {"ok": True}
    _widget_states[token] = {
        "user_id": body.user_id,
        "display_name": body.display_name,
        "verified": bearer_user_id is not None,
        "ts": time(),
    }
    logger.info("Widget state completed for token=%s user=%s", token[:8], body.user_id[:8])
    return {"ok": True}
