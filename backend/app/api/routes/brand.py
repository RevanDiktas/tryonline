"""
Brand registration and management routes — JWT-protected.
POST /api/brand/leads     -- public: a brand asks to start (tryon.global/start); no auth
POST /api/brand/register  -- create brand record linked to an authenticated user
GET  /api/brand/me        -- get current user's brand record
"""
import re
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends, Request
from slowapi import Limiter

from app.api.deps import get_current_user_id
from app.api.rate_limit import client_key
from app.services.supabase import SupabaseService

router = APIRouter()
supabase = SupabaseService()
limiter = Limiter(key_func=client_key)


class BrandRegisterBody(BaseModel):
    brand_name: str
    email: str
    phone: Optional[str] = None
    country: Optional[str] = None
    shopify_domain: Optional[str] = None


@router.post("/register")
async def register_brand(body: BrandRegisterBody, user_id: str = Depends(get_current_user_id)):
    """
    Create a brand record linked to the authenticated user.
    If a brand already exists for this shopify_domain (created by OAuth install),
    we link it to this user instead of creating a duplicate.
    """
    try:
        existing = supabase.get_brand_by_user_id(user_id)
        if existing:
            supabase.ensure_garments_bucket()
            supabase._create_brand_folder(existing["id"])
            return {"ok": True, "brand_id": existing["id"], "existing": True}

        if body.shopify_domain:
            oauth_brand = supabase.get_brand_by_shopify_domain(body.shopify_domain)
            if oauth_brand and not oauth_brand.get("user_id"):
                brand_id = supabase.link_user_to_brand(
                    brand_id=str(oauth_brand["id"]),
                    user_id=user_id,
                    name=body.brand_name,
                    email=body.email,
                )
                if brand_id:
                    return {"ok": True, "brand_id": brand_id, "existing": True}

        brand_id = supabase.create_brand_for_user(
            user_id=user_id,
            name=body.brand_name,
            email=body.email,
            shopify_domain=body.shopify_domain,
        )
        if not brand_id:
            raise HTTPException(status_code=500, detail="Failed to create brand record")
        return {"ok": True, "brand_id": brand_id, "existing": False}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[brand/register] error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/me")
async def get_my_brand(user_id: str = Depends(get_current_user_id)):
    """Get the brand record for the authenticated user."""
    try:
        brand = supabase.get_brand_by_user_id(user_id)
        if not brand:
            raise HTTPException(status_code=404, detail="No brand found for this user")
        return {"ok": True, "brand": brand}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[brand/me] error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ---- leads: brands that ask to start from tryon.global/start (public, rate-limited) ----

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_LEAD_PLANS = {"free", "size_pro", "try_on", "scale", "enterprise"}


class BrandLeadBody(BaseModel):
    brand_name: str = Field(min_length=1, max_length=120)
    contact_name: Optional[str] = Field(default=None, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    shop_domain: Optional[str] = Field(default=None, max_length=255)
    plan: Optional[str] = Field(default=None, max_length=32)
    notes: Optional[str] = Field(default=None, max_length=2000)
    source: Optional[str] = Field(default=None, max_length=64)


def _normalise_shop(value: Optional[str]) -> Optional[str]:
    """'https://www.Brand.com/' or 'brand.myshopify.com' -> a bare lowercase host, or None."""
    if not value:
        return None
    host = re.sub(r"^https?://", "", value.strip().lower()).split("/")[0]
    return host or None


@router.post("/leads")
@limiter.limit("5/minute")
async def create_brand_lead(request: Request, body: BrandLeadBody):
    """
    Record a brand that wants to start. Until the public Shopify app is listed, the team
    replies with a private install link; brand_leads.status tracks the follow-up.
    """
    email = body.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    row = {
        "brand_name": body.brand_name.strip(),
        "contact_name": (body.contact_name or "").strip() or None,
        "email": email,
        "shop_domain": _normalise_shop(body.shop_domain),
        "plan": body.plan if body.plan in _LEAD_PLANS else None,
        "notes": (body.notes or "").strip() or None,
        "source": (body.source or "website")[:64],
    }
    try:
        supabase.client.table("brand_leads").insert(row).execute()
    except Exception as e:
        print(f"[brand] lead insert failed for {email}: {e}")
        raise HTTPException(status_code=500, detail="Could not save your request. Email revan@tryon.global instead.")
    print(f"[brand] new lead: {row['brand_name']} <{email}> shop={row['shop_domain']} plan={row['plan']}")
    return {"ok": True}
