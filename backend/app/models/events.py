"""
Analytics event models
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    # Avatar events
    avatar_created = "avatar_created"
    avatar_viewed = "avatar_viewed"
    
    # Try-on events
    tryon_started = "tryon_started"
    tryon_size_changed = "tryon_size_changed"
    tryon_completed = "tryon_completed"
    
    # Shopping events
    add_to_cart = "add_to_cart"
    purchase = "purchase"
    
    # Widget events
    widget_opened = "widget_opened"
    widget_closed = "widget_closed"


class AnalyticsEvent(BaseModel):
    """Analytics event to track"""
    user_id: str
    event_type: EventType
    brand_id: Optional[str] = None
    garment_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None


class AnalyticsEventResponse(BaseModel):
    """Response after tracking event"""
    success: bool
    event_id: Optional[str] = None
    message: str = "Event tracked"
