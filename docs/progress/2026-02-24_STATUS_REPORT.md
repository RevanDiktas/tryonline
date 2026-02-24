# Status Report — Monday 24 Feb 2026

## Summary

Spent the day fixing Shopify app install flow, backend deployment, and RunPod avatar pipeline. Multiple issues surfaced and were resolved. By end of day: Shopify OAuth flow works, backend and frontend deploy from `feature/analytics`, RunPod image reverted to last known working version and rebuilding.

---

## What was done

### 1. Shopify app install — "Redirecting to install..." fix
- **Problem**: App showed "Redirecting to install..." forever in the Shopify iframe.
- **Fix**: Added a **"Complete install"** button that appears immediately (no 2s delay). Button links to backend OAuth with `target="_top"` so it works inside the iframe.

### 2. Frontend OAuth URL pointed at wrong server (404)
- **Problem**: "Complete install" button linked to `tryonline.vercel.app/api/shopify/auth` — the frontend. Shopify OAuth routes live on the **backend** (Railway). Got **404 Not Found**.
- **Root cause**: `apiBase` was set to `''` in the browser, so all Shopify API calls went to the frontend origin instead of `NEXT_PUBLIC_API_URL` (backend).
- **Fix**: All Shopify calls (session check, complete-install, auth link) now use `process.env.NEXT_PUBLIC_API_URL` directly (the Railway backend URL). Added clear error message if the env var is missing.

### 3. Railway deploying wrong branch (404 on all Shopify routes)
- **Problem**: Railway was deploying from `feature/analytics`, which didn't have the Shopify router code. All Shopify routes returned **404** even though the backend was running.
- **Root cause**: Shopify OAuth work was done on `main`. Railway was connected to `feature/analytics` which was many commits behind.
- **Fix**: Merged `main` into `feature/analytics` and pushed. All Shopify routes now present on `feature/analytics`. Confirmed with `/routes` endpoint (shows `shopify_ok: true`).

### 4. OAuth cookie error (`oauth_error=same_site_cookies`)
- **Problem**: After OAuth redirect, Shopify showed "De app kon niet worden geladen" (app could not be loaded) with `oauth_error=same_site_cookies`.
- **Root cause**: The OAuth state cookie was set with `SameSite=Lax`, which browsers don't send on cross-site redirects from Shopify back to our backend.
- **Fix**: Changed cookie to `SameSite=None; Secure=True`. The callback already accepted missing state cookies (HMAC-only verification) as a fallback.

### 5. Garments storage bucket on brand signup
- **Problem**: No organized storage for garment files (GLBs per brand/product).
- **Fix**: Added `ensure_garments_bucket()` in `SupabaseService` — creates a shared `garments` bucket (public) on first brand signup. Path convention: `garments/{brand_id}/{product_id}/{filename}`. Added helpers: `garment_storage_path()`, `get_garment_public_url()`.

### 6. RunPod avatar pipeline broken — container won't start
- **Problem**: Avatar creation failed. RunPod logs showed `error creating container: container create: exit status 1` in a loop. No worker could start.
- **Investigation**: Between the last working commit (`db6f6ac`, Feb 3) and current (`40320ae`), only `handler.py` changed (added shutil symlink logic). The Dockerfile, requirements, and pipeline code were identical.
- **Fix**: Reverted `handler.py` on `main` to the exact working version (`db6f6ac`). Pushed to `main` so RunPod rebuilds the image from known-good code. Build completed; worker initializing at end of day.

### 7. Deploy branch alignment
- **Problem**: Kept pushing to `main` but Railway and Vercel deploy from `feature/analytics`. RunPod deploys from `main`.
- **Fix**: 
  - **Railway** (backend): `feature/analytics`
  - **Vercel** (frontend): `feature/analytics` (deploy hook created)
  - **RunPod** (avatar GPU): `main`
  - Created `docs/DEPLOY_BRANCH.md` documenting this.

---

## What went wrong (lessons)

1. **Branch mismatch** was the #1 time waster. Code was on `main`, Railway deployed `feature/analytics`. Should have checked the deploy branch first.
2. **Frontend using relative API paths** for Shopify OAuth — worked locally (Next.js rewrites) but not in production (Shopify iframe blocks cross-origin redirects differently).
3. **Cookie SameSite=Lax** doesn't survive cross-site OAuth redirects. Should always use `SameSite=None; Secure` for OAuth state cookies.
4. **RunPod container creation failures** appear to be infrastructure-related (exit status 1 on container create, not on code execution). Reverting to known-good code was the right call.

---

## Current state

| Service | Branch | Status |
|---------|--------|--------|
| **Backend (Railway)** | `feature/analytics` | Running, Shopify routes work |
| **Frontend (Vercel)** | `feature/analytics` | Deploy triggered via hook |
| **RunPod (avatar GPU)** | `main` | Image rebuilt, worker initializing |
| **Supabase** | — | brands table empty (no successful install yet), garments bucket not yet created (created on first brand signup) |
| **Shopify app** | tryon-9 (active) | Installed on dev store, "Complete install" button works, OAuth flow reaches backend |

---

## Still to do tonight / next session

1. **Confirm RunPod worker starts** — check Workers tab, run a test avatar creation.
2. **Complete Shopify install flow** — uninstall app, reinstall, click "Complete install", verify brand row in Supabase + garments bucket in Storage.
3. **Add garments for dev store** — upload GLBs to `garments/{brand_id}/{product_id}/`, insert `garments` rows.
4. **Test widget on product page** — confirm Try On button loads and try-on works.
5. **Deep links and App Store** — add onboarding steps in the embedded app (from COMPLETE_STEPS_WALKTHROUGH.md).

---

## Files changed today

### Backend
- `backend/app/api/routes/shopify.py` — SameSite=None cookie, ping endpoint
- `backend/app/main.py` — `/routes` debug endpoint
- `backend/app/config.py` — `garments_bucket` config
- `backend/app/services/supabase.py` — `ensure_garments_bucket()`, `garment_storage_path()`, `get_garment_public_url()`, called from `upsert_brand_for_shop()`
- `backend/app/api/routes/avatar.py` — treat RunPod `output.error` as failure
- `backend/railway.toml` — Railway build config

### Frontend
- `frontend/app/app/page.tsx` — use `NEXT_PUBLIC_API_URL` for all Shopify calls, show "Complete install" button, error when env var missing

### Avatar pipeline
- `avatar-creation/pipelines/handler.py` — reverted to db6f6ac (working version)

### Docs
- `docs/DEPLOY_BRANCH.md`
- `docs/FRESH_ONBOARDING_STEPS.md`
- `docs/GARMENTS_STORAGE_LAYOUT.md`
- `docs/RAILWAY_404_SHOPIFY_AUTH.md`
- `docs/ONBOARDING_AND_GARMENTS_FLOW.md`
- `docs/SHOP_DOMAIN_AND_SESSIONS_EXPLAINED.md`
