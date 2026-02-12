# Preferred Fit Flow — Analysis

## Confirmed

- **fit_passports** — Updates correctly when you change Slim/Regular/Loose on the dashboard ✓
- **Size recommendation algo** — Uses preferred_fit correctly (e.g. Loose → size L) ✓

## Flow: Where does `analytics_events.preferred_fit` come from?

```
Dashboard (Loose) → fit_passports.preferred_fit = 'loose'
                            ↓
User opens widget ("Open widget with my account")
                            ↓
Link: /test-viewer.html?user_id=xxx&preferred_fit=loose&...
                            ↓
Widget tracks events → POST /api/events/track { user_id, preferred_fit, ... }
                            ↓
Backend track_event():
  1. If user_id present → fetch fit_passports.preferred_fit (source of truth)
  2. Use DB value; fall back to payload only if DB returns None
  3. Insert into analytics_events
```

## Current backend logic (after fix)

```python
if user_id:
    db_preferred_fit = await self._get_preferred_fit(user_id)
    preferred_fit = db_preferred_fit if db_preferred_fit is not None else preferred_fit
```

So analytics **always** uses `fit_passports` when `user_id` is present, ignoring the payload.

## Why analytics_events might still show "regular"

1. **Old events** — Events recorded before you changed to Loose still have "regular". Filter by `created_at` to see only new events.

2. **Widget opened without user_id** — If the widget was opened via a URL without `user_id` (e.g. bookmark, direct URL), no user_id is sent. We don’t fetch from fit_passports. We use the payload, which may be missing or default to something else.

3. **Backend not restarted** — Restart uvicorn after code changes so the new logic is loaded.

4. **Timing** — If you change to Loose and immediately click "Open widget" before the save finishes, fit_passports might still have "regular" when the first events are tracked.

## How to verify

1. Set preferred fit to **Loose** on the dashboard.
2. Wait 2–3 seconds for the save to complete.
3. Click **"Open widget with my account"** (new tab).
4. Complete the try-on flow (open, select size, add to cart).
5. In Supabase → `analytics_events`, filter by today and your `user_id`, and confirm the latest rows have `preferred_fit = 'loose'`.

## Debug (optional)

In `backend/app/services/supabase.py`, uncomment the print in `track_event`:

```python
# print(f"[Analytics] user_id={user_id[:8]}.. payload_preferred_fit={preferred_fit} db_preferred_fit={db_preferred_fit} → using={preferred_fit}")
```

Then run a test and check the backend logs for `payload_preferred_fit`, `db_preferred_fit`, and the final `using` value.
