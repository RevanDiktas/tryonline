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
   POST /api/auth/widget-state/{token}/complete.
4. The next poll from the widget picks up the user_id, and the widget reloads.
"""

import logging
import secrets
from time import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

_widget_states: dict[str, dict] = {}
_STATE_TTL = 300  # 5 minutes


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
    """Poll endpoint: returns user_id when the popup has completed OAuth."""
    _cleanup()
    state = _widget_states.get(token)
    if state and state.get("user_id"):
        uid = state["user_id"]
        name = state.get("display_name", "")
        del _widget_states[token]
        return {"user_id": uid, "display_name": name}
    return {"user_id": None}


@router.post("/widget-state/{token}/complete")
async def complete_widget_state(token: str, body: WidgetStateComplete):
    """Called by the auth callback page after successful OAuth."""
    _cleanup()
    _widget_states[token] = {
        "user_id": body.user_id,
        "display_name": body.display_name,
        "ts": time(),
    }
    logger.info("Widget state completed for token=%s user=%s", token[:8], body.user_id[:8])
    return {"ok": True}
