"""
Measurement endpoints — JWT-protected.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.api.deps import UserAccess, get_current_user_id
from app.services.supabase import supabase_service

router = APIRouter()

# The body measurements a fit passport holds (cm).
PASSPORT_MEASUREMENTS = (
    "chest", "waist", "hips", "inseam", "shoulder_width", "arm_length", "neck", "thigh", "torso_length",
)


@router.get("/passport/{user_id}")
async def get_fit_passport(user_id: str, _access: None = Depends(UserAccess("fit passport"))):
    """The shopper's fit passport and nothing else: what a size-only surface needs.

    One onboarding always produces both a fit passport and an avatar. What a surface
    fetches depends on what it shows:
      - size only (the "Find my size" card)  -> this route
      - try-on (the 3D viewer)               -> GET /api/avatar/{user_id}: passport + avatar

    `status` is the passport's: pending / processing / completed / failed. Measurements
    are only real once it is `completed`; before that the row holds what the shopper
    typed (height, weight) and no measured value. 404 = the shopper has not started.
    """
    fp = await supabase_service.get_fit_passport(user_id)
    if not fp:
        raise HTTPException(status_code=404, detail="No fit passport")
    measurements = {k: fp.get(k) for k in PASSPORT_MEASUREMENTS if fp.get(k) is not None}
    return {
        "user_id": user_id,
        "status": fp.get("status") or "pending",
        "gender": fp.get("gender"),
        "height": fp.get("height"),
        "weight": fp.get("weight"),
        "preferred_fit": fp.get("preferred_fit"),
        "measurements": measurements,
        "measured_at": fp.get("processing_completed_at"),
    }


class MeasurementsUpdate(BaseModel):
    """Request to update measurements"""
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
async def update_measurements(request: MeasurementsUpdate, user_id: str = Depends(get_current_user_id)):
    """Update the authenticated user's measurements."""
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
        user_id=user_id,
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


@router.get("/me")
async def get_my_measurements(user_id: str = Depends(get_current_user_id)):
    """Get the authenticated user's measurements."""
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
        "preferred_fit": fit_passport.get("preferred_fit"),
    }


@router.get("/{user_id}")
async def get_measurements(user_id: str, auth_user_id: str = Depends(get_current_user_id)):
    """Get measurements by user_id. Verifies caller owns the data."""
    if user_id != auth_user_id:
        raise HTTPException(status_code=403, detail="Access denied")

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
        "preferred_fit": fit_passport.get("preferred_fit"),
    }
