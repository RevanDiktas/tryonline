"""
Wishlist / Closet CRUD — JWT-protected endpoints for managing saved items.
- GET    /api/wishlist                      — list saved items (optionally filtered by list_type)
- POST   /api/wishlist                      — add item to wishlist
- DELETE /api/wishlist/{item_id}            — remove item
- GET    /api/wishlist/{product_id}/status  — check if product is wishlisted
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import get_current_user_id
from app.services.supabase import supabase_service

router = APIRouter()


class WishlistAddPayload(BaseModel):
    product_id: str
    shop_domain: str
    variant_id: Optional[str] = None
    product_name: Optional[str] = None
    product_image_url: Optional[str] = None
    product_price: Optional[float] = None
    currency: Optional[str] = "USD"
    brand_name: Optional[str] = None


@router.get("")
async def list_saved_items(
    list_type: Optional[str] = Query(None, description="Filter: 'wishlist' or 'closet'"),
    user_id: str = Depends(get_current_user_id),
):
    """List the authenticated user's saved items, optionally filtered by list_type."""
    try:
        q = (
            supabase_service.client.table("saved_items")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
        )
        if list_type in ("wishlist", "closet"):
            q = q.eq("list_type", list_type)
        r = q.execute()
        return {"ok": True, "items": r.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def add_to_wishlist(
    body: WishlistAddPayload,
    user_id: str = Depends(get_current_user_id),
):
    """Add a product to the user's wishlist (idempotent via unique constraint)."""
    row = {
        "user_id": user_id,
        "list_type": "wishlist",
        "product_id": body.product_id.strip(),
        "shop_domain": body.shop_domain.strip(),
    }
    if body.variant_id:
        row["variant_id"] = body.variant_id.strip()
    if body.product_name:
        row["product_name"] = body.product_name.strip()
    if body.product_image_url:
        row["product_image_url"] = body.product_image_url.strip()
    if body.product_price is not None:
        row["product_price"] = body.product_price
    if body.currency:
        row["currency"] = body.currency.strip()
    if body.brand_name:
        row["brand_name"] = body.brand_name.strip()

    try:
        r = (
            supabase_service.client.table("saved_items")
            .upsert(row, on_conflict="user_id,product_id,shop_domain,list_type")
            .execute()
        )
        item = r.data[0] if r.data else row
        return {"ok": True, "item": item}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{item_id}")
async def remove_saved_item(
    item_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Remove a saved item (ownership verified via user_id match)."""
    try:
        r = (
            supabase_service.client.table("saved_items")
            .select("id, user_id")
            .eq("id", item_id)
            .limit(1)
            .execute()
        )
        if not r.data:
            raise HTTPException(status_code=404, detail="Item not found")
        if str(r.data[0].get("user_id")) != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        supabase_service.client.table("saved_items").delete().eq("id", item_id).execute()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{product_id}/status")
async def get_wishlist_status(
    product_id: str,
    shop: str = Query(..., description="Shop domain"),
    user_id: str = Depends(get_current_user_id),
):
    """Check whether a product is in the user's wishlist."""
    try:
        r = (
            supabase_service.client.table("saved_items")
            .select("id, list_type")
            .eq("user_id", user_id)
            .eq("product_id", product_id.strip())
            .eq("shop_domain", shop.strip())
            .execute()
        )
        wishlisted = any(row.get("list_type") == "wishlist" for row in (r.data or []))
        owned = any(row.get("list_type") == "closet" for row in (r.data or []))
        return {"ok": True, "wishlisted": wishlisted, "owned": owned}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
