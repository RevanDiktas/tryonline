"""
User addresses (Shopper Passport -- shipping addresses).
All routes require a valid Supabase JWT; user_id is extracted from the token.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.api.deps import get_current_user_id
from app.services.supabase import supabase_service

router = APIRouter()


class AddressCreate(BaseModel):
    label: str
    name: str
    line1: str
    city: str
    postal_code: str
    country: str
    line2: Optional[str] = None
    state: Optional[str] = None
    is_default: bool = False


class AddressUpdate(BaseModel):
    label: Optional[str] = None
    name: Optional[str] = None
    line1: Optional[str] = None
    line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    is_default: Optional[bool] = None


@router.get("")
async def list_addresses(user_id: str = Depends(get_current_user_id)):
    """List all addresses for the authenticated user."""
    addresses = await supabase_service.get_addresses(user_id)
    return {"addresses": addresses}


@router.post("")
async def create_address(body: AddressCreate, user_id: str = Depends(get_current_user_id)):
    """Create a new address for the authenticated user."""
    addr = await supabase_service.create_address(
        user_id=user_id,
        label=body.label.strip(),
        name=body.name.strip(),
        line1=body.line1.strip(),
        city=body.city.strip(),
        postal_code=body.postal_code.strip(),
        country=body.country.strip(),
        line2=body.line2.strip() if body.line2 else None,
        state=body.state.strip() if body.state else None,
        is_default=body.is_default,
    )
    if not addr:
        raise HTTPException(status_code=500, detail="Failed to create address")
    return {"address": addr}


@router.patch("/{address_id}")
async def update_address(address_id: str, body: AddressUpdate, user_id: str = Depends(get_current_user_id)):
    """Update an address. Ownership verified via JWT user_id."""
    ok = await supabase_service.update_address(
        address_id=address_id,
        user_id=user_id,
        label=body.label.strip() if body.label else None,
        name=body.name.strip() if body.name else None,
        line1=body.line1.strip() if body.line1 else None,
        line2=body.line2.strip() if body.line2 else None,
        city=body.city.strip() if body.city else None,
        state=body.state.strip() if body.state else None,
        postal_code=body.postal_code.strip() if body.postal_code else None,
        country=body.country.strip() if body.country else None,
        is_default=body.is_default,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Address not found or access denied")
    addresses = await supabase_service.get_addresses(user_id)
    updated = next((a for a in addresses if str(a["id"]) == address_id), None)
    return {"address": updated or {"id": address_id}}


@router.delete("/{address_id}")
async def delete_address(address_id: str, user_id: str = Depends(get_current_user_id)):
    """Delete an address. Ownership verified via JWT user_id."""
    ok = await supabase_service.delete_address(address_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Address not found or access denied")
    return {"success": True}
