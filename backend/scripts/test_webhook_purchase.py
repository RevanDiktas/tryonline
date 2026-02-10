#!/usr/bin/env python3
"""
Test the Shopify orders/paid webhook with a simulated order.
Use this to verify Category B: purchase events with size flow correctly.

Usage:
  python scripts/test_webhook_purchase.py [--session-id UUID] [--size M] [--base-url URL]

Get a session_id from Supabase: analytics_events or tryon_sessions (use one that has size_recommended).
"""
import argparse
import json
import os
import sys

# Add parent so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description="Test Shopify orders/paid webhook")
    ap.add_argument("--session-id", "-s", help="TryOn session_id (from tryon_sessions or analytics_events)")
    ap.add_argument("--size", default="M", help="Size purchased (default: M)")
    ap.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    ap.add_argument("--order-id", default=None, help="Order ID (default: test-ORDER_TIMESTAMP)")
    args = ap.parse_args()

    import time
    order_id = args.order_id or f"test-{int(time.time())}"
    session_id = args.session_id or "00000000-0000-0000-0000-000000000000"
    size = args.size
    base_url = args.base_url.rstrip("/")

    if session_id == "00000000-0000-0000-0000-000000000000":
        print("WARNING: Using placeholder session_id. For proper B verification, use a real session_id")
        print("  from Supabase analytics_events (any row with session_id) or tryon_sessions.")
        print("  Example: python scripts/test_webhook_purchase.py -s <your-session-id>")
        print()

    # Shopify orders/paid webhook payload (minimal)
    order = {
        "id": order_id,
        "total_price": "49.00",
        "currency": "USD",
        "line_items": [
            {
                "id": 123456789,
                "variant_id": 987654321,
                "quantity": 1,
                "price": "49.00",
                "variant_title": f"{size} / Default",
                "properties": [
                    {"name": "tryon_session_id", "value": session_id},
                    {"name": "_tryon_size", "value": size},
                ],
            }
        ],
    }

    url = f"{base_url}/api/webhooks/shopify/orders-paid"
    print(f"POST {url}")
    print(f"  order_id={order_id} session_id={session_id} size={size}")
    print()

    try:
        r = httpx.post(
            url,
            json=order,
            headers={"Content-Type": "application/json", "X-Shopify-Shop-Domain": "demo.myshopify.com"},
            timeout=10,
        )
        print(f"Status: {r.status_code}")
        if r.status_code != 200:
            print(f"Body: {r.text}")
            sys.exit(1)
        print("OK — webhook accepted.")
        print()
        print("Next: Check Supabase analytics_events for event_type='purchase'.")
        print("  event_data should have: order_id, amount, items: [{ session_id, size }]")
        print("  Then refresh the dashboard Fit Accuracy section.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
