"""
Brand registration and management routes — JWT-protected.
POST /api/brand/register  -- create brand record linked to an authenticated user
GET  /api/brand/me        -- get current user's brand record
"""
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends

from app.api.deps import get_current_user_id
from app.services.supabase import SupabaseService

router = APIRouter()
supabase = SupabaseService()


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
