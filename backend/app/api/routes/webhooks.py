"""
Shopify webhooks — orders/paid for purchase attribution; GDPR compliance webhooks.
"""
import base64
import hmac
import hashlib
import json
from fastapi import APIRouter, Request, HTTPException, Response
from typing import Any

from app.services.supabase import supabase_service
from app.config import get_settings

router = APIRouter()
settings = get_settings()

# Attribute name from cart (theme must use this key)
TRYON_SESSION_ATTR = "tryon_session_id"

# Compliance webhook topics (Shopify mandatory for App Store)
COMPLIANCE_TOPICS = {"customers/data_request", "customers/redact", "shop/redact"}
# Same URI may receive app/uninstalled if configured in shopify.app.toml
ALLOWED_WEBHOOK_TOPICS = COMPLIANCE_TOPICS | {"app/uninstalled"}


def _verify_shopify_hmac(body: bytes, hmac_header: str | None) -> bool:
    """Verify Shopify webhook HMAC using the shared dependency."""
    from app.api.deps import verify_shopify_webhook
    return verify_shopify_webhook(body, hmac_header)


def _get_session_id_from_order(order: dict[str, Any]) -> str | None:
    """Extract tryon_session_id from order note_attributes or line_item properties."""
    # Cart attributes → order.note_attributes
    attrs = order.get("note_attributes") or []
    for a in attrs:
        if isinstance(a, dict) and a.get("name") == TRYON_SESSION_ATTR:
            v = a.get("value")
            return str(v) if v else None
    # Fallback: line item properties (if theme put it there)
    for item in order.get("line_items") or []:
        props = item.get("properties") or []
        for p in props:
            if isinstance(p, dict) and p.get("name") == TRYON_SESSION_ATTR:
                v = p.get("value")
                return str(v) if v else None
    return None


def _get_line_items_with_tryon(order: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract line items with tryon attribution. Returns [{ session_id, size, quantity, price }, ...]"""
    TRYON_SIZE_ATTR = "_tryon_size"
    order_session = _get_session_id_from_order(order)
    items: list[dict[str, Any]] = []
    for li in order.get("line_items") or []:
        sid: str | None = None
        size: str | None = None
        for p in li.get("properties") or []:
            if isinstance(p, dict):
                n = p.get("name") or ""
                v = p.get("value")
                if n == TRYON_SESSION_ATTR and v:
                    sid = str(v)
                elif n == TRYON_SIZE_ATTR and v:
                    size = str(v).strip() or None
        if not sid and order_session and size:
            sid = order_session
        if sid:
            qty = int(li.get("quantity", 1) or 1)
            price = float(li.get("price", 0) or 0) * qty
            items.append({"session_id": sid, "size": size or (str(li.get("variant_title") or "").strip()) or None, "quantity": qty, "price": price})
    return items


@router.post("/shopify/orders-paid")
async def shopify_orders_paid(request: Request):
    """
    Handle Shopify orders/paid webhook.
    Extracts session_id from cart attributes, writes purchase event.
    Idempotent by order_id.
    """
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256")
    if not _verify_shopify_hmac(body, hmac_header):
        raise HTTPException(status_code=401, detail="Invalid HMAC")

    try:
        order = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    order_id = str(order.get("id") or "")
    if not order_id:
        raise HTTPException(status_code=400, detail="Missing order id")

    session_id = _get_session_id_from_order(order)
    shop_domain = (
        request.headers.get("X-Shopify-Shop-Domain")
        or order.get("shop_domain")
        or (order.get("shop", {}).get("myshopify_domain") if isinstance(order.get("shop"), dict) else None)
    )

    total_price = float(order.get("total_price", 0) or 0)
    currency = str(order.get("currency", "USD") or "USD")

    tryon_items = _get_line_items_with_tryon(order)
    event_data: dict[str, Any] = {
        "order_id": order_id,
        "amount": total_price,
        "currency": currency,
    }
    if tryon_items:
        event_data["items"] = tryon_items

    event_id = await supabase_service.track_purchase(
        order_id=order_id,
        session_id=session_id,
        shop_domain=shop_domain,
        amount=total_price,
        currency=currency,
        event_data=event_data,
    )

    if event_id is None and session_id:
        # Idempotent: already exists
        return Response(status_code=200, content="OK")
    if event_id is None:
        return Response(status_code=200, content="OK")  # No session_id, skip
    return Response(status_code=200, content="OK")


# --- Mandatory compliance webhooks (GDPR/CCPA; required for App Store) ---
# Shopify sends all three topics to the same URI; identify by X-Shopify-Topic header.


@router.post("/shopify/compliance")
async def shopify_compliance_webhook(request: Request):
    """
    Single endpoint for mandatory compliance webhooks: customers/data_request,
    customers/redact, shop/redact. Verify HMAC, acknowledge with 200. Actual
    data deletion/export can be implemented or queued here.
    """
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256")
    if not _verify_shopify_hmac(body, hmac_header):
        raise HTTPException(status_code=401, detail="Invalid HMAC")

    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    topic = (request.headers.get("X-Shopify-Topic") or "").strip()
    if topic not in ALLOWED_WEBHOOK_TOPICS:
        raise HTTPException(status_code=400, detail="Unknown compliance topic")

    # Acknowledge receipt immediately (Shopify requires 200 within 5s).
    # Optional: enqueue or run data_request/redact logic here.
    if topic == "customers/data_request":
        # Payload: shop_id, shop_domain, orders_requested, customer, data_request.id
        pass
    elif topic == "customers/redact":
        # Payload: shop_id, shop_domain, customer, orders_to_redact
        pass
    elif topic == "shop/redact":
        # Payload: shop_id, shop_domain
        pass

    return Response(status_code=200, content="OK", media_type="text/plain")
