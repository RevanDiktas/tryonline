"""
Measurement endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.supabase import supabase_service

router = APIRouter()


class MeasurementsUpdate(BaseModel):
    """Request to update measurements"""
    user_id: str
    chest: Optional[int] = None
    waist: Optional[int] = None
    hips: Optional[int] = None
    inseam: Optional[int] = None
    shoulder_width: Optional[int] = None
    arm_length: Optional[int] = None
    neck: Optional[int] = None
    thigh: Optional[int] = None
    torso_length: Optional[int] = None


class MeasurementsResponse(BaseModel):
    """Response after updating measurements"""
    success: bool
    message: str


@router.post("/update", response_model=MeasurementsResponse)
async def update_measurements(request: MeasurementsUpdate):
    """
    Update user's measurements
    
    Used when user corrects auto-generated measurements
    """
    # Build update dict with only provided values
    measurements = {}
    
    if request.chest is not None:
        measurements["chest"] = request.chest
    if request.waist is not None:
        measurements["waist"] = request.waist
    if request.hips is not None:
        measurements["hips"] = request.hips
    if request.inseam is not None:
        measurements["inseam"] = request.inseam
    if request.shoulder_width is not None:
        measurements["shoulder_width"] = request.shoulder_width
    if request.arm_length is not None:
        measurements["arm_length"] = request.arm_length
    if request.neck is not None:
        measurements["neck"] = request.neck
    if request.thigh is not None:
        measurements["thigh"] = request.thigh
    if request.torso_length is not None:
        measurements["torso_length"] = request.torso_length
    
    if not measurements:
        raise HTTPException(
            status_code=400, 
            detail="No measurements provided"
        )
    
    success = await supabase_service.update_measurements(
        user_id=request.user_id,
        measurements=measurements
    )
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to update measurements"
        )
    
    return MeasurementsResponse(
        success=True,
        message="Measurements updated successfully"
    )


@router.get("/{user_id}")
async def get_measurements(user_id: str):
    """
    Get user's current measurements
    """
    fit_passport = await supabase_service.get_fit_passport(user_id)
    
    if not fit_passport:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user_id": user_id,
        "height": fit_passport.get("height"),
        "weight": fit_passport.get("weight"),
        "chest": fit_passport.get("chest"),
        "waist": fit_passport.get("waist"),
        "hips": fit_passport.get("hips"),
        "inseam": fit_passport.get("inseam"),
        "shoulder_width": fit_passport.get("shoulder_width"),
        "arm_length": fit_passport.get("arm_length"),
        "neck": fit_passport.get("neck"),
        "thigh": fit_passport.get("thigh"),
        "torso_length": fit_passport.get("torso_length"),
    }
