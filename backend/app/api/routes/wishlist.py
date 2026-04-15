"""
Wishlist / Closet CRUD — endpoints for managing saved items.

Auth strategy:
  - Dashboard (tryon.global, first-party): JWT via Authorization header
  - Widget iframe (third-party on Shopify PDP): user_id in body/query param
    (third-party storage partitioning blocks localStorage access to the JWT)
  Both paths verify the user exists before accepting writes.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.api.deps import get_current_user_id
from app.services.supabase import supabase_service

logger = logging.getLogger(__name__)
router = APIRouter()
_optional_bearer = HTTPBearer(auto_error=False)


def _resolve_user_id(
    credentials: HTTPAuthorizationCredentials | None,
    fallback_user_id: str | None,
) -> str:
    """Resolve user_id from JWT token (preferred) or fallback user_id param.
    Validates that the user exists in the DB for the fallback path."""
    # Try JWT first
    if credentials and credentials.credentials:
        try:
            return get_current_user_id(credentials)
        except HTTPException:
            pass

    # Fallback: explicit user_id (widget iframe path)
    if fallback_user_id and fallback_user_id.strip():
        uid = fallback_user_id.strip()
        try:
            r = supabase_service.client.table("users").select("id").eq("id", uid).limit(1).execute()
            if r.data and len(r.data) > 0:
                return uid
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Invalid user_id")

    raise HTTPException(status_code=401, detail="Authorization required")


class WishlistAddPayload(BaseModel):
    product_id: str
    shop_domain: str
    user_id: Optional[str] = None
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
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
):
    """Add a product to the user's wishlist.
    Accepts JWT auth OR user_id in body (for widget iframe)."""
    user_id = _resolve_user_id(credentials, body.user_id)

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
    """Remove a saved item (ownership verified via JWT user_id match)."""
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
    uid: Optional[str] = Query(None, alias="user_id", description="User ID (widget fallback)"),
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
):
    """Check whether a product is in the user's wishlist.
    Accepts JWT auth OR user_id query param (for widget iframe)."""
    user_id = _resolve_user_id(credentials, uid)

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
