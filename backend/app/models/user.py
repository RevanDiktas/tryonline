"""
User-related Pydantic models
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserProfile(BaseModel):
    """User profile data"""
    id: str
    email: EmailStr
    name: str
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    user_type: str = "shopper"
    created_at: datetime
