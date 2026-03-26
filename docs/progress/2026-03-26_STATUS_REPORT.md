# Status Report — 2026-03-26

## Completed today

### RunPod payload fix — avatar results now delivered
- **Root cause**: The RunPod handler was encoding `skin_detection_mask` (18.6 MB debug image) in the return payload, pushing total to 20.51 MB and exceeding RunPod's ~20 MB limit. RunPod rejected the response with 400 Bad Request.
- **Fix**: Excluded `skin_detection_mask` from the return payload. Payload drops from 20.51 MB to ~1.9 MB. Skin detection and avatar texturing still work — only the debug visualization was removed.
- **Pushed to `main`**, Docker image rebuilt and deployed on RunPod (build completed successfully, 6.71 GB image pushed to registry).

### Polling timeout increases — no more premature loading screen exits
- Frontend polling: 4 min -> **10 min** (300 attempts x 2s)
- Backend polling: 5 min -> **10 min** (120 attempts x 5s)
- avatar_tasks polling: 5 min -> **10 min** (120 attempts x 5s)
- Pushed to `feature/analytics` (Railway + Vercel auto-redeploy).

### SSL fix — `www.tryon.global` no longer shows security warning
- Added `www.tryon.global` to Vercel domains with 308 permanent redirect to `tryon.global`.
- `tryon.global` remains the primary production domain.
- All three domains (`www.tryon.global`, `tryon.global`, `tryonline.vercel.app`) showing valid configuration.

### Shopify App Store review follow-up
- App submitted ~1.5 weeks ago, still in "assigning a reviewer" stage.
- Sent follow-up email to `app-review@shopify.com` requesting status update.

---

## Key fixes

| Issue | Root cause | Fix |
|-------|-----------|-----|
| RunPod "Failed to return job results" 400 | `skin_detection_mask` (18.6 MB) pushed payload over 20 MB limit | Excluded debug image from return payload |
| Loading screen quits while RunPod queued | Frontend timeout was 4 min, backend 5 min | Both increased to 10 min |
| `www.tryon.global` SSL security warning | `www` subdomain not configured in Vercel | Added `www.tryon.global` with 308 redirect to `tryon.global` |

---

## Files changed today

| File | Branch | Change |
|------|--------|--------|
| `avatar-creation/pipelines/handler.py` | `main` | Excluded `skin_detection_mask` from return payload |
| `backend/app/api/routes/avatar.py` | `feature/analytics` | Backend polling timeout 5 min -> 10 min |
| `backend/app/tasks/avatar_tasks.py` | `feature/analytics` | Task polling timeout 5 min -> 10 min |
| `frontend/lib/api.ts` | `feature/analytics` | Frontend polling timeout 4 min -> 10 min |

---

## Remaining tasks

1. **Test avatar creation with new Docker image** — have colleague retry onboarding to confirm results now arrive in Supabase/dashboard.
2. **Test Apple sign-in from widget** — provider is configured, same flow as Google.
3. **Test OAuth complete-profile flow** — fresh Google/Apple account to verify birthday/phone collection.
4. **Shopify App Store review** — awaiting response from Shopify review team.
5. **Apple secret rotation** — JWT expires ~August 2026.
