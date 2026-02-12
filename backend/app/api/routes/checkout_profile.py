"""
Checkout profile API — returns the user's default shipping address for prefill at brand checkout.
Caller must send the user's Supabase access token (Bearer) so we can verify identity and return only their default address.
"""
import jwt
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.services.supabase import supabase_service

router = APIRouter()
security = HTTPBearer(auto_error=False)


def _verify_supabase_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    """Verify Bearer token as Supabase JWT; return user_id (sub). Raises HTTPException on failure."""
    settings = get_settings()
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=503,
            detail="Checkout profile API is not configured (missing SUPABASE_JWT_SECRET)",
        )
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required: Bearer <Supabase access token>",
        )
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.supabase_jwt_secret,
            audience="authenticated",
            algorithms=["HS256"],
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="Invalid token: wrong audience")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("")
async def get_checkout_profile(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    """
    Return the authenticated user's default shipping address for checkout prefill.

    **Auth:** Send the user's Supabase access token in the Authorization header:
    `Authorization: Bearer <access_token>`.

    **Use case:** Your app (e.g. TryOn bridge page) gets the token from the user's
    session, calls this API, and uses the returned address to prefill the brand's
    checkout or show a "Confirm your address" step.

    **Response:** Shipping address only (no user id or internal ids). 404 if the user
    has no saved addresses.
    """
    user_id = _verify_supabase_token(credentials)
    address = await supabase_service.get_default_address(user_id)
    if not address:
        raise HTTPException(
            status_code=404,
            detail="No shipping address found. Add one in your TryOn dashboard.",
        )
    return {
        "address": {
            "label": address.get("label"),
            "name": address.get("name"),
            "line1": address.get("line1"),
            "line2": address.get("line2"),
            "city": address.get("city"),
            "state": address.get("state"),
            "postal_code": address.get("postal_code"),
            "country": address.get("country"),
        }
    }
