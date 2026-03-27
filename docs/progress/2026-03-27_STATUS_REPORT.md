# Status Report — 2026-03-27

## Completed today

### Shopify widget OAuth — FIXED (properly this time)

The Google/Apple sign-in from the Shopify product page widget has been broken for weeks due to layered browser security restrictions. Today we did deep research and found the real root causes, then built the correct solution.

**Root causes identified:**
1. **Google blocks iframes** — Google's OAuth page sets `X-Frame-Options: DENY`, so it refuses to load inside any iframe (including our widget on Shopify's PDP).
2. **Google's COOP kills window.opener** — When a popup navigates through `accounts.google.com`, Google's `Cross-Origin-Opener-Policy: same-origin` header nullifies `window.opener`. So `window.opener.postMessage()` fails in the callback.
3. **BroadcastChannel is partitioned** — Chrome partitions BroadcastChannel by top-level site. The iframe (top-level: `myshopify.com`) and the popup (top-level: `tryon.global`) live in different partitions and cannot communicate.

**Solution: backend-mediated state exchange**
- Widget generates a unique state token (UUID) and opens a popup via `window.open()` (small 500x650 window, stays on the PDP)
- Widget polls `GET /api/auth/widget-state/{token}` every 2 seconds
- Popup loads `widget-signin`, auto-triggers Google OAuth (in top-level window, no iframe restrictions)
- After OAuth completes, the callback page POSTs `{ user_id, display_name }` to `POST /api/auth/widget-state/{token}/complete`
- Popup shows "Signed in! You can close this window." and auto-closes
- Widget's next poll picks up the `user_id` and reloads with it

**Tested and confirmed working:** Google sign-in from the Shopify product page → popup opens → Google consent screen → auth completes → popup closes → avatar + measurements load on PDP. User never leaves the product page.

### Analytics performance — TTLCache (completed earlier this week)

- Reverted failed Postgres RPC approach (PostgREST schema cache wouldn't discover new functions despite `NOTIFY pgrst, 'reload schema'`)
- Restored proven Python-based direct table queries for all 9 analytics endpoints
- Added `TTLCache(maxsize=256, ttl=60)` to all 9 endpoints for 60-second caching
- Analytics dashboards load fast and reliably

### Auth reliability improvements (completed earlier this week)

- **Frontend**: `getAccessToken()` proactively refreshes Supabase session if token expires within 120 seconds
- **Frontend**: `fetchApi()` has 401 retry mechanism (refreshes token and retries once)
- **Backend**: `get_current_user_id` has Supabase Auth API fallback — first tries local JWT verification, falls back to Supabase REST API if JWT secret is misconfigured
- **Brand dashboard**: "Getting Started" bar only shows when data is loaded and is dismissible

---

## Files changed today

| File | Branch | Change |
|------|--------|--------|
| `backend/app/api/routes/auth.py` | `feature/analytics` | NEW: Widget state exchange endpoints (in-memory TTL store) |
| `backend/app/main.py` | `feature/analytics` | Register auth router at `/api/auth` |
| `frontend/public/test-viewer.html` | `feature/analytics` | Popup + polling for Google/Apple OAuth; all sign-in paths use popup when in iframe |
| `frontend/app/widget-signin/page.tsx` | `feature/analytics` | Reads `widget_state`, passes through OAuth, completes state via backend |
| `frontend/app/auth/callback/page.tsx` | `feature/analytics` | POSTs user_id to backend widget-state endpoint after OAuth, auto-closes popup |
| `frontend/lib/supabase-auth.ts` | `feature/analytics` | `signInWithSocial` accepts and passes `widgetState` through redirect URL |

---

## Security measures in place

These were implemented during the codebase audit and remain intact:

| Measure | Status |
|---------|--------|
| JWT authentication on all user-scoped backend routes | DONE |
| Supabase Auth API fallback for JWT verification | DONE |
| Shopify webhook HMAC verification (all 3 compliance endpoints) | DONE |
| Debug/diagnostic endpoints gated behind `DEBUG=true` env var | DONE |
| API rate limiting via `slowapi` (120 req/min default) | DONE |

---

## Codebase audit — items NOT YET done (future backlog)

These were identified during the comprehensive codebase optimization audit but deferred. Organized by priority.

### Performance optimization

| Item | Description | Priority |
|------|-------------|----------|
| **Database indexes** | Add indexes on frequently-queried columns (`user_id`, `shop_domain`, `created_at`, `event_type`) in `tryon_sessions`, `tryon_events`, `fit_passports` tables. Currently relies on Supabase defaults. | High |
| **Postgres RPC functions** | Move heavy aggregation to server-side SQL functions (tried but PostgREST cache failed; revisit with direct `supabase.rpc()` calls or raw SQL). Currently mitigated by TTLCache. | Medium |
| **Frontend bundle splitting** | Large components (Three.js globe, charts) should be dynamically imported with `React.lazy` + `Suspense` to reduce initial bundle size. | Medium |
| **Image optimization** | Serve avatar/garment GLB thumbnails via CDN with proper cache headers. Consider pre-generating 2D preview thumbnails. | Medium |
| **AbortController for fetch** | Add request cancellation to all frontend API calls (component unmounts, page navigation) to prevent memory leaks and stale updates. | Low |
| **Connection pooling** | Use `httpx.AsyncClient` session pooling in the backend instead of creating new connections per request. | Low |

### Frontend / UX improvements

| Item | Description | Priority |
|------|-------------|----------|
| **React.memo / useMemo** | Memoize expensive components (analytics charts, globe) to prevent unnecessary re-renders on parent state changes. | Medium |
| **Error boundaries** | Add React error boundaries around major sections (dashboard, globe, avatar viewer) so a crash in one section doesn't take down the whole page. | Medium |
| **Skeleton loaders** | Replace "Loading..." text with skeleton UI patterns for dashboard cards, charts, and garment lists. | Low |
| **Offline/slow network handling** | Show appropriate messages when the user has no internet or very slow connection. | Low |
| **Globe: light theme polish** | Verify globe colors/contrast on light theme (developed mostly on dark). | Low |

### Backend / infrastructure

| Item | Description | Priority |
|------|-------------|----------|
| **Structured logging** | Replace `print()` and ad-hoc `logger` calls with consistent structured JSON logging (timestamp, request_id, user_id, action). Makes Railway logs searchable. | Medium |
| **Error monitoring (Sentry)** | Add Sentry to both frontend and backend for automatic error tracking, alerting, and stack traces. | Medium |
| **Input validation hardening** | Add stricter Pydantic validation on all request bodies (length limits, regex patterns, allowed values). Currently some endpoints accept any string. | Medium |
| **Background job queue** | Replace in-memory avatar job tracking with a proper queue (Redis/Celery). Current in-memory dict loses jobs on backend restart. | Medium |
| **Supabase Storage RLS** | Add proper INSERT policies for authenticated users on `photos` and `avatars` buckets (currently bypassed via service role key on backend). | Low |
| **API versioning** | Add `/v1/` prefix to all API routes for future backward compatibility. | Low |

### Avatar pipeline

| Item | Description | Priority |
|------|-------------|----------|
| **PERSONA model integration** | Research and benchmark PERSONA (ICCV 2025) against current pipeline for more realistic avatars. Priority #1 on the R&D roadmap. | High (R&D) |
| **Fit heatmap generation** | Implement tension/strain visualization for garments on avatars. Priority #2 on R&D roadmap. | High (R&D) |
| **Garment construction automation** | Automate 2D-to-3D garment pipeline using TailorNet, CLO3D API, or newer research (SPnet, GarmageNet). Priority #3 on R&D roadmap. | Medium (R&D) |

---

## Remaining operational tasks

1. **Test Apple sign-in from widget** — same popup flow as Google, should work.
2. **Merge `feature/analytics` → `main`** — branch has significant changes accumulated.
3. **Shopify App Store review** — awaiting response from Shopify review team.
4. **Apple secret rotation** — JWT expires ~August 2026.
5. **Re-run avatar creation for Hatice** — avatar texture was blank/white; needs re-creation.
6. **Globe: real city data** — once more events with city field populated, verify city-level analytics show real data.
