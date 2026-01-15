"""
Avatar-related Pydantic models
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"


class ProcessingStatus(str, Enum):
    pending = "pending"
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class AvatarCreateRequest(BaseModel):
    """Request to create a new avatar"""
    user_id: str = Field(..., description="User's UUID")
    photo_url: str = Field(..., description="URL to uploaded photo in Supabase Storage")
    height: int = Field(..., ge=100, le=250, description="Height in cm")
    weight: Optional[int] = Field(None, ge=30, le=300, description="Weight in kg")
    gender: Gender = Field(..., description="Body type")


class AvatarCreateResponse(BaseModel):
    """Response after creating avatar job"""
    job_id: str = Field(..., description="Unique job identifier")
    user_id: str
    status: ProcessingStatus = ProcessingStatus.queued
    message: str = "Avatar creation started"
    estimated_time_seconds: int = 120


class AvatarStatusResponse(BaseModel):
    """Response for avatar processing status"""
    job_id: str
    user_id: str
    status: ProcessingStatus
    progress: int = Field(0, ge=0, le=100, description="Processing progress percentage")
    message: str = ""
    avatar_url: Optional[str] = None
    measurements: Optional[dict] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class Measurements(BaseModel):
    """Body measurements in cm"""
    height: int
    chest: Optional[int] = None
    waist: Optional[int] = None
    hips: Optional[int] = None
    inseam: Optional[int] = None
    shoulder_width: Optional[int] = None
    arm_length: Optional[int] = None
    neck: Optional[int] = None
    thigh: Optional[int] = None
    torso_length: Optional[int] = None


class AvatarResponse(BaseModel):
    """Full avatar data response"""
    user_id: str
    avatar_url: Optional[str] = None
    avatar_thumbnail_url: Optional[str] = None
    measurements: Measurements
    gender: Gender
    status: ProcessingStatus
    created_at: datetime
    updated_at: datetime
