"""
Analytics event tracking endpoints — Category A
"""
from fastapi import APIRouter, HTTPException, Request

from app.models.events import (
    AnalyticsEvent,
    AnalyticsEventResponse,
    CreateTryonSessionRequest,
    CreateTryonSessionResponse,
)
from app.services.supabase import supabase_service

router = APIRouter()


def _get_client_info(request: Request) -> tuple[str | None, str | None]:
    """Extract user_agent and ip from request"""
    user_agent = request.headers.get("user-agent")
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else request.client.host if request.client else None
    return user_agent, ip


@router.post("/track", response_model=AnalyticsEventResponse)
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
