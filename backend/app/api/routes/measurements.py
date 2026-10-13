"""
Measurement endpoints — JWT-protected.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Any, Dict, Optional

from app.api.deps import UserAccess, get_current_user_id, get_optional_user_id
from app.services.supabase import supabase_service

router = APIRouter()
logger = logging.getLogger(__name__)

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


# ---------------------------------------------------------------------------
# The size quiz, saved to an account ("quiz fit passport")
#
# The "Find my size" card estimates a size from seven answers. Saved here, the same answers
# give the shopper an estimated size in every store without asking again. It is an estimate:
# the photo fit passport above is the measurement, and a completed one always wins.
# ---------------------------------------------------------------------------

# Same limits as frontend/public/size-estimator.js INPUT_LIMITS.
QUIZ_LIMITS = {"height": (120, 230), "weight": (30, 250), "age": (14, 100)}
QUIZ_SHAPE_KEYS = ("chest", "belly", "hips")
QUIZ_AGE_BANDS = ("15-24", "25-34", "35-44", "45-54", "55-64", "65+")
QUIZ_ESTIMATE_KEYS = ("chest", "waist", "hips")
QUIZ_ESTIMATE_RANGE = (40, 220)   # cm; anything outside is not a body


def _number(v: Any) -> Optional[float]:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v) if v == v and abs(v) != float("inf") else None


def clean_quiz_profile(raw: Any) -> Dict[str, Any]:
    """Keep only what the quiz asks, in range. Raises ValueError naming the first bad answer.
    Unknown keys are dropped, so nothing else can be parked in this row."""
    if not isinstance(raw, dict):
        raise ValueError("profile")
    gender = raw.get("gender")
    if gender not in ("female", "male"):
        raise ValueError("gender")
    out: Dict[str, Any] = {"gender": gender}
    for key in ("height", "weight"):
        n = _number(raw.get(key))
        lo, hi = QUIZ_LIMITS[key]
        if n is None or not lo <= n <= hi:
            raise ValueError(key)
        out[key] = round(n)
    age = _number(raw.get("age"))
    if age is not None:
        lo, hi = QUIZ_LIMITS["age"]
        if not lo <= age <= hi:
            raise ValueError("age")
        out["age"] = round(age)
    if raw.get("ageBand") is not None:
        if raw["ageBand"] not in QUIZ_AGE_BANDS:
            raise ValueError("ageBand")
        out["ageBand"] = raw["ageBand"]
    shape = raw.get("shape") or {}
    if not isinstance(shape, dict):
        raise ValueError("shape")
    out["shape"] = {}
    for key in QUIZ_SHAPE_KEYS:
        if shape.get(key) is None:
            continue
        if isinstance(shape[key], bool) or shape[key] not in (-1, 0, 1):
            raise ValueError("shape")
        out["shape"][key] = int(shape[key])
    if raw.get("units") is not None:
        if raw["units"] not in ("metric", "imperial"):
            raise ValueError("units")
        out["units"] = raw["units"]
    if raw.get("fit") is not None:
        if raw["fit"] not in ("slim", "regular", "loose"):
            raise ValueError("fit")
        out["fit"] = raw["fit"]
    return out


def clean_quiz_estimate(raw: Any) -> Optional[Dict[str, float]]:
    """The body the answers imply, for reporting. Optional; bad values are dropped, not refused."""
    if not isinstance(raw, dict):
        return None
    lo, hi = QUIZ_ESTIMATE_RANGE
    out = {}
    for key in QUIZ_ESTIMATE_KEYS:
        n = _number(raw.get(key))
        if n is not None and lo <= n <= hi:
            out[key] = round(n, 1)
    return out or None


def quiz_profile_writer(
    user_id: str,
    request: Request,
    bearer_user_id: Optional[str] = Depends(get_optional_user_id),
) -> str:
    """Writing always needs proof, whatever WIDGET_AUTH_REQUIRED says: the shopper's own
    session, or a widget token issued for them. A bare user_id is never enough to write."""
    from app.services import widget_token as wt

    if bearer_user_id is not None:
        if bearer_user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        return user_id
    token_user = wt.verify(request.headers.get("x-widget-token"))
    if token_user is None:
        raise HTTPException(status_code=401, detail="Authorization required")
    if token_user != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return user_id


class QuizProfileSave(BaseModel):
    profile: Dict[str, Any]
    estimate: Optional[Dict[str, Any]] = None
    shop_domain: Optional[str] = None


def _quiz_profile_out(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": row.get("user_id"),
        "profile": row.get("profile"),
        "estimate": row.get("estimate"),
        "updated_at": row.get("updated_at"),
    }


@router.put("/quiz-profile/{user_id}")
async def save_quiz_profile(body: QuizProfileSave, user_id: str = Depends(quiz_profile_writer)):
    """Save (or replace) the shopper's quiz answers on their account."""
    try:
        profile = clean_quiz_profile(body.profile)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid answer: {e}")
    now = datetime.now(timezone.utc).isoformat()
    fields = {"profile": profile, "estimate": clean_quiz_estimate(body.estimate), "updated_at": now}
    shop = (body.shop_domain or "").strip().lower()[:255] or None
    table = supabase_service.client.table("quiz_profiles")
    try:
        existing = table.select("user_id").eq("user_id", user_id).limit(1).execute()
        if existing.data:
            r = supabase_service.client.table("quiz_profiles").update(fields).eq("user_id", user_id).execute()
        else:
            # shop_domain = where the shopper first saved it; later saves keep it.
            r = supabase_service.client.table("quiz_profiles").insert(
                {"user_id": user_id, "shop_domain": shop, "created_at": now, **fields}
            ).execute()
    except Exception as e:
        msg = str(e).lower()
        if "foreign key" in msg or "23503" in msg:
            # No public.users row: the account was never finished.
            raise HTTPException(status_code=409, detail="Account profile missing")
        if "duplicate" in msg or "23505" in msg or "unique" in msg:
            r = supabase_service.client.table("quiz_profiles").update(fields).eq("user_id", user_id).execute()
        else:
            logger.error("quiz profile save failed for %s: %s", user_id[:8], e)
            raise HTTPException(status_code=503, detail="Could not save")
    if not (r.data or []):
        raise HTTPException(status_code=503, detail="Could not save")
    return _quiz_profile_out({"user_id": user_id, **fields})


@router.get("/quiz-profile/{user_id}")
async def get_quiz_profile(user_id: str, _access: None = Depends(UserAccess("quiz profile"))):
    """The shopper's saved quiz answers. 404 = none saved."""
    try:
        r = supabase_service.client.table("quiz_profiles").select("*").eq("user_id", user_id).limit(1).execute()
    except Exception as e:
        logger.error("quiz profile read failed for %s: %s", user_id[:8], e)
        raise HTTPException(status_code=503, detail="Could not load")
    if not r.data:
        raise HTTPException(status_code=404, detail="No quiz profile")
    return _quiz_profile_out(r.data[0])


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
