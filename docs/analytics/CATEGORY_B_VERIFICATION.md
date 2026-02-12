# Category B — Fit Accuracy: Verification Checklist

Use this to ensure B works robustly before moving to Category C.

---

## Step 1: Data Flow — Widget → Events

| Check | How |
|-------|-----|
| `size_recommended` in events | Use widget, open try-on. Supabase `analytics_events` → filter `event_type='size_recommended'` → `event_data` has `{"size":"..."}` |
| `size_selected` in events | Click a size button. Check `event_type='size_selected'`, `event_data->>'size'` |
| `add_to_cart` with size | Click Add to Cart. Check `event_type='add_to_cart'`, `event_data->>'size'` |
| Session consistency | Same `session_id` across widget_opened → tryon_started → size_recommended → size_selected → add_to_cart |

**Test:** Dashboard → "Open widget with my account" → TRY ON → pick size S → ADD TO CART. Verify all 4 events have the same `session_id` and correct `size`.

---

## Step 2: Webhook — Order → Purchase Event

| Check | How |
|-------|-----|
| Size in line item properties | Cart snippet must add `_tryon_size` (done in `shopify-tryon-cart-snippet.js`) |
| Webhook extracts size | Run test script (see Step 4) |
| Purchase event has `items` | Supabase → `analytics_events` → `event_type='purchase'` → `event_data` has `"items": [{ "session_id", "size" }]` |

---

## Step 3: Fit Metrics API

| Check | How |
|-------|-----|
| Size distributions | `GET /api/analytics/fit-metrics` → `size_distribution_recommended`, `_selected`, `_purchased` |
| Acceptance rate | Sessions where `size_recommended == size_purchased` (needs purchase data) |
| MASE | Mean \|ordinal_purchased - ordinal_recommended\| (needs purchase data) |
| Size up/down | From selected vs recommended (works without purchases) |

---

## Step 4: Webhook Test Script

```bash
cd backend

# Get a session_id from Supabase (analytics_events, any row with session_id)
# Then run:
python scripts/test_webhook_purchase.py --session-id YOUR_SESSION_ID --size M
```

This sends a simulated order to the webhook. Verify:
1. Supabase has new `purchase` event
2. `event_data.items` has `[{ "session_id": "...", "size": "M" }]`
3. Dashboard Fit Accuracy shows acceptance rate / MASE (if session had size_recommended)

---

## Step 5: End-to-End Flow

1. **Create session with recommendation:** Open widget → TRY ON → note `session_id` from network tab or Supabase
2. **Simulate purchase:** `python scripts/test_webhook_purchase.py -s <session_id> --size M`
3. **Verify:** Dashboard Fit Accuracy — Acceptance rate, MASE, Purchased distribution should update

---

## Robustness Notes

- **Size normalization:** XS/xs, S/s, M/m, L/l, XL/xl, Large→L, Small→S, etc. all match
- **Numeric sizes:** 30, 32, 34 map to ordinals for MASE
- **Missing size:** Events without size are skipped; rates stay valid
- **Multi-item orders:** Each line item with `tryon_session_id` + `_tryon_size` gets one `items` entry
