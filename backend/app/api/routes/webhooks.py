"""
Shopify webhooks — orders/paid for purchase attribution, refunds/create for return
tracking, bracketing detection; GDPR compliance webhooks.
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


def _detect_bracketing(order: dict[str, Any]) -> tuple[bool, int]:
    """Detect if an order contains bracketed items (same product, multiple sizes).
    Returns (is_bracketed, bracket_item_count)."""
    from collections import Counter
    product_ids = Counter()
    for li in order.get("line_items") or []:
        pid = li.get("product_id")
        if pid:
            product_ids[pid] += 1
    bracket_count = sum(c for c in product_ids.values() if c > 1)
    return (bracket_count > 0, bracket_count)


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
    is_bracketed, bracket_count = _detect_bracketing(order)
    event_data: dict[str, Any] = {
        "order_id": order_id,
        "amount": total_price,
        "currency": currency,
        "is_bracketed": is_bracketed,
        "bracket_items": bracket_count,
    }
    if tryon_items:
        event_data["items"] = tryon_items

    # Include raw line_items for closet population (product_id, title, price, variant_id)
    raw_line_items = order.get("line_items") or []
    if raw_line_items:
        event_data["line_items"] = [
            {
                "product_id": str(li.get("product_id") or ""),
                "variant_id": str(li.get("variant_id") or ""),
                "title": li.get("title") or li.get("name") or "",
                "price": str(li.get("price", "0")),
                "quantity": li.get("quantity", 1),
            }
            for li in raw_line_items
        ]

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
    elif topic == "app/uninstalled":
        # Null the access token so has_shopify_session() returns false. Brand row is
        # retained; shop/redact handles data deletion 48h later if no reinstall.
        shop_domain = (
            request.headers.get("X-Shopify-Shop-Domain")
            or payload.get("myshopify_domain")
            or payload.get("domain")
        )
        if shop_domain:
            try:
                supabase_service.clear_shopify_tokens_matching_shop_domain(shop_domain)
                print(f"[Shopify uninstall] cleared token shop={shop_domain!r}")
            except Exception as e:
                print(f"[Shopify uninstall] clear token error shop={shop_domain!r}: {e}")

    return Response(status_code=200, content="OK", media_type="text/plain")


@router.post("/shopify/refunds-created")
async def shopify_refunds_created(request: Request):
    """
    Handle Shopify refunds/create webhook.
    Tracks return events for return-rate analytics and revenue-lost calculations.
    Idempotent by refund_id.
    """
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256")
    if not _verify_shopify_hmac(body, hmac_header):
        raise HTTPException(status_code=401, detail="Invalid HMAC")

    try:
        refund = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    refund_id = str(refund.get("id") or "")
    order_id = str(refund.get("order_id") or "")
    if not refund_id:
        raise HTTPException(status_code=400, detail="Missing refund id")

    shop_domain = (
        request.headers.get("X-Shopify-Shop-Domain")
        or refund.get("shop_domain")
    )

    refund_line_items = refund.get("refund_line_items") or []
    total_refunded = 0.0
    returned_products: list[dict[str, Any]] = []
    for rli in refund_line_items:
        qty = int(rli.get("quantity", 0) or 0)
        subtotal = float(rli.get("subtotal", 0) or 0)
        total_refunded += subtotal
        li = rli.get("line_item") or {}
        returned_products.append({
            "product_id": str(li.get("product_id") or ""),
            "variant_id": str(li.get("variant_id") or ""),
            "title": li.get("title") or li.get("name") or "",
            "quantity": qty,
            "subtotal": subtotal,
        })

    reason = refund.get("note") or ""
    for tr in refund.get("transactions") or []:
        if tr.get("kind") == "refund":
            total_refunded = max(total_refunded, float(tr.get("amount", 0) or 0))

    session_id: str | None = None
    try:
        r = supabase_service.client.table("analytics_events") \
            .select("session_id") \
            .eq("event_type", "purchase") \
            .execute()
        for row in r.data or []:
            ed = row.get("event_data") or {}
            if str(ed.get("order_id", "")) == order_id:
                session_id = row.get("session_id")
                break
    except Exception:
        pass

    event_data: dict[str, Any] = {
        "refund_id": refund_id,
        "order_id": order_id,
        "amount_refunded": total_refunded,
        "reason": reason,
        "items": returned_products,
    }

    event_id = await supabase_service.track_event(
        event_type="return",
        session_id=session_id,
        shop_domain=shop_domain,
        event_data=event_data,
    )

    return Response(status_code=200, content="OK")
