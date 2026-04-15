"""
Analytics event models — Category A schema aligned
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    # Avatar events
    avatar_created = "avatar_created"
    avatar_viewed = "avatar_viewed"
    avatar_started = "avatar_started"
    avatar_failed = "avatar_failed"

    # Widget events
    widget_opened = "widget_opened"
    widget_closed = "widget_closed"

    # Try-on events
    tryon_started = "tryon_started"
    tryon_ended = "tryon_ended"
    tryon_size_changed = "tryon_size_changed"

    # Size events (Category B)
    size_recommended = "size_recommended"
    size_viewed = "size_viewed"
    size_selected = "size_selected"

    # Shopping events
    add_to_cart = "add_to_cart"
    checkout_started = "checkout_started"
    purchase = "purchase"

    # Wishlist events
    wishlist_add = "wishlist_add"
    wishlist_remove = "wishlist_remove"

    # Post-purchase events
    return_item = "return"
    fit_feedback = "fit_feedback"


class AnalyticsEvent(BaseModel):
    """Analytics event — matches analytics_events table"""
    event_type: EventType
    user_id: Optional[str] = None  # Nullable for anonymous
    session_id: Optional[str] = None
    brand_id: Optional[str] = None
    shop_domain: Optional[str] = None
    product_id: Optional[str] = None  # Maps from garment_id in frontend
    variant_id: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    preferred_fit: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None  # → event_data JSONB
    timestamp: Optional[datetime] = None


class AnalyticsEventResponse(BaseModel):
    """Response after tracking event"""
    success: bool
    event_id: Optional[str] = None
    message: str = "Event tracked"


# --- Try-on session ---

class CreateTryonSessionRequest(BaseModel):
    """Request to create a try-on session"""
    user_id: Optional[str] = None
    shop_domain: Optional[str] = None
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    variant_id: Optional[str] = None
    brand_id: Optional[str] = None


class CreateTryonSessionResponse(BaseModel):
    """Response with session id for attribution"""
    session_id: str
    session_token: str
