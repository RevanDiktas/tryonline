"""
Brand registration and management routes.
POST /api/brand/register  — create brand record linked to an authenticated user
GET  /api/brand/me         — get current user's brand record
"""
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.services.supabase import SupabaseService

router = APIRouter()
supabase = SupabaseService()


class BrandRegisterBody(BaseModel):
    user_id: str
    brand_name: str
    email: str
    phone: Optional[str] = None
    country: Optional[str] = None
    shopify_domain: Optional[str] = None


@router.post("/register")
async def register_brand(body: BrandRegisterBody):
    """
    Create a brand record linked to the authenticated user.
    Called after Supabase auth signup when user_type='brand'.
    If a brand already exists for this shopify_domain (created by OAuth install),
    we link it to this user instead of creating a duplicate.
    """
    existing = supabase.get_brand_by_user_id(body.user_id)
    if existing:
        supabase.ensure_garments_bucket()
        supabase._create_brand_folder(existing["id"])
        return {"ok": True, "brand_id": existing["id"], "existing": True}

    # Check if a brand was already created by Shopify OAuth (has shopify_domain but no user_id)
    if body.shopify_domain:
        oauth_brand = supabase.get_brand_by_shopify_domain(body.shopify_domain)
        if oauth_brand and not oauth_brand.get("user_id"):
            brand_id = supabase.link_user_to_brand(
                brand_id=str(oauth_brand["id"]),
                user_id=body.user_id,
                name=body.brand_name,
                email=body.email,
            )
            if brand_id:
                return {"ok": True, "brand_id": brand_id, "existing": True}

    brand_id = supabase.create_brand_for_user(
        user_id=body.user_id,
        name=body.brand_name,
        email=body.email,
        shopify_domain=body.shopify_domain,
    )
    if not brand_id:
        raise HTTPException(status_code=500, detail="Failed to create brand record")
    return {"ok": True, "brand_id": brand_id, "existing": False}


@router.get("/me")
async def get_my_brand(user_id: str):
    """Get the brand record for the given user_id."""
    brand = supabase.get_brand_by_user_id(user_id)
    if not brand:
        raise HTTPException(status_code=404, detail="No brand found for this user")
    return {"ok": True, "brand": brand}
