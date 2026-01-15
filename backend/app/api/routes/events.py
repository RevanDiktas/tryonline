"""
Analytics event tracking endpoints
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.models.events import AnalyticsEvent, AnalyticsEventResponse
from app.services.supabase import supabase_service

router = APIRouter()


@router.post("/track", response_model=AnalyticsEventResponse)
async def track_event(event: AnalyticsEvent):
    """
    Track an analytics event
    
    Used to track user actions for analytics:
    - Avatar creation
    - Try-on sessions
    - Size changes
    - Add to cart
    - Purchases
    """
    event_id = await supabase_service.track_event(
        user_id=event.user_id,
        event_type=event.event_type.value,
        brand_id=event.brand_id,
        garment_id=event.garment_id,
        session_id=event.session_id,
        metadata=event.metadata
    )
    
    if not event_id:
        raise HTTPException(
            status_code=500,
            detail="Failed to track event"
        )
    
    return AnalyticsEventResponse(
        success=True,
        event_id=event_id,
        message="Event tracked successfully"
    )


@router.post("/tryon-session")
async def create_tryon_session(
    user_id: str,
    brand_id: str,
    garment_id: str
):
    """
    Create a new try-on session
    
    Called when user opens the try-on widget
    """
    # TODO: Implement tryon_sessions table operations
    session_id = f"session-{datetime.utcnow().timestamp()}"
    
    return {
        "session_id": session_id,
        "user_id": user_id,
        "brand_id": brand_id,
        "garment_id": garment_id,
        "started_at": datetime.utcnow().isoformat()
    }
