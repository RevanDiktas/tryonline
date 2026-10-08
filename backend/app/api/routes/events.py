"""
Analytics event tracking endpoints — Category A
"""
import json
import re
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response
from slowapi import Limiter
from app.api.rate_limit import client_key

from app.models.events import (
    AnalyticsEvent,
    AnalyticsEventResponse,
    CreateTryonSessionRequest,
    CreateTryonSessionResponse,
)
from app.services.supabase import supabase_service

router = APIRouter()
limiter = Limiter(key_func=client_key)


def _get_client_info(request: Request) -> tuple[str | None, str | None]:
    """Extract user_agent and ip from request"""
    user_agent = request.headers.get("user-agent")
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else request.client.host if request.client else None
    return user_agent, ip


@router.post("/track", response_model=AnalyticsEventResponse)
@limiter.limit("60/minute")
async def track_event(request: Request, event: AnalyticsEvent):
    """
    Track an analytics event (Category A).
    Events: widget_opened, tryon_started, size_recommended, size_selected, add_to_cart, purchase, etc.
    """
    user_agent, ip_address = _get_client_info(request)
    event_id = await supabase_service.track_event(
        event_type=event.event_type.value,
        user_id=event.user_id,
        session_id=event.session_id,
        brand_id=event.brand_id,
        shop_domain=event.shop_domain,
        product_id=event.product_id,
        variant_id=event.variant_id,
        country=event.country,
        city=event.city,
        preferred_fit=event.preferred_fit,
        event_data=event.metadata,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    if not event_id:
        raise HTTPException(status_code=500, detail="Failed to track event")
    return AnalyticsEventResponse(success=True, event_id=event_id, message="Event tracked successfully")


@router.post("/tryon-session", response_model=CreateTryonSessionResponse)
async def create_tryon_session(body: CreateTryonSessionRequest):
    """
    Create a try-on session when widget opens. Returns session_id for attribution.
    Frontend uses session_id in all subsequent track_event calls and in cart attributes.
    """
    result = await supabase_service.create_tryon_session(
        user_id=body.user_id,
        shop_domain=body.shop_domain,
        product_id=body.product_id,
        product_name=body.product_name,
        variant_id=body.variant_id,
        brand_id=body.brand_id,
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create try-on session")
    return CreateTryonSessionResponse(session_id=result["session_id"], session_token=result["session_token"])


# ---------------------------------------------------------------------------
# Store traffic, for the conversion comparison.
#
# The store block (assets/tryon-size.js) sends one "visit" per visitor per day when a
# product page with our button loads, and one "used" per visitor per day when the widget
# shows that shopper a size. With paid orders (orders/paid webhook) that gives a conversion
# rate for shoppers who used the widget and for those who did not.
#
# It arrives from the store's own domain via navigator.sendBeacon as text/plain, so the
# browser needs no CORS preflight. The visitor id is a random id kept in the store's
# localStorage: no account, no cookie, nothing personal.
# ---------------------------------------------------------------------------
STORE_BEACON_TYPES = {"visit": "store_visit", "used": "store_widget_used"}
_VISITOR_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


@router.post("/store-beacon")
@limiter.limit("30/minute")
async def store_beacon(request: Request):
    """Always answers 204: a beacon's response is never read, and a store page must not
    see errors from us."""
    done = Response(status_code=204)
    try:
        raw = await request.body()
        if not raw or len(raw) > 2048:
            return done
        data = json.loads(raw)
        event_type = STORE_BEACON_TYPES.get(str(data.get("t") or ""))
        shop = str(data.get("shop") or "").strip().lower()
        vid = str(data.get("vid") or "")
        if not event_type or not shop or not _VISITOR_ID_RE.match(vid):
            return done
        # Only stores we know: this is an open endpoint.
        if not supabase_service.get_brand_by_shopify_domain(shop):
            return done
        # One row per visitor per day and type, whatever the page sends.
        day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        seen = (
            supabase_service.client.table("analytics_events").select("id")
            .eq("event_type", event_type).eq("shop_domain", shop)
            .eq("event_data->>visitor_id", vid).gte("created_at", day_start.isoformat())
            .limit(1).execute()
        )
        if seen.data:
            return done
        product_id = str(data.get("product_id") or "")[:64] or None
        user_agent, _ip = _get_client_info(request)
        await supabase_service.track_event(
            event_type=event_type,
            shop_domain=shop,
            product_id=product_id,
            event_data={"visitor_id": vid},
            user_agent=user_agent,
        )
    except Exception as e:
        print(f"[store-beacon] dropped: {e}")
    return done
