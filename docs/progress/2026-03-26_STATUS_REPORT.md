# Status Report — 2026-03-26

## Completed today

### Brand dashboard — chart tooltip responsiveness
- Disabled all Recharts animation (`isAnimationActive={false}`) on every Tooltip, Bar, Area, and Line component.
- Tooltips now appear instantly on hover with zero lag.

### Brand dashboard — globe visualization overhaul
Complete rewrite of the `RegionalSizeGlobe` component across 7 iterative commits:

**Visual quality**
- Earth dot density doubled: 80k -> 160k Fibonacci-distributed points.
- Smoother dot sprite: 128px canvas with gaussian-like radial gradient falloff.
- Brighter land colors for dark theme (cyan `#22d3ee` / `#67e8f9` instead of muted teal).
- Globe sphere darkened (`#020617`) for maximum contrast.
- Refined ocean detection heuristic to eliminate ocean noise while preserving deserts, snow, and ice coverage.
- Higher resolution earth grid (1024x512 vs 720x360).

**Country borders**
- Fixed TopoJSON parser (was reading `geometry.coordinates` instead of `geometry.arcs` per the TopoJSON spec — borders were silently failing to render).
- Borders fetched from CDN (`world-atlas@2/countries-110m.json`), rendered as line segments on globe surface.
- Always faintly visible (0.15 base opacity), sharpen on zoom. Bright cyan color (`#a5f3fc`) for dark theme.

**Country coverage**
- Expanded country coordinates from 37 to 120+ countries across all continents (full Africa, Caribbean, Central Asia, more Southeast Asia, all smaller European states).

**Click-to-zoom interaction**
- Clicking a country data dot zooms the camera smoothly to that region (ease-out cubic animation, ~0.5s).
- Country dot disappears when selected, replaced by gold city-level dots.
- City dots: smaller scale (0.013), pulsing ring animation, hoverable with tooltip showing city name + size breakdown.
- Click anywhere on the globe surface (or "Back to globe" button) to zoom back out.
- Auto-rotation pauses while a country is selected.

**City-level data**
- Backend: extended `/api/analytics/regional-size` to return `by_city` field (country -> city -> size distribution). City names normalized with `.title()` to prevent duplicates.
- Frontend: 130+ major city coordinates pre-mapped (Amsterdam, Zaandam, Rotterdam, Paris, London, Milan, New York, Tokyo, etc.).
- Fallback: if backend has no city data yet, generates city markers from known coordinates for countries with analytics data.

### Earlier today (before dashboard work)

**RunPod payload fix** — avatar results now delivered
- Excluded `skin_detection_mask` (18.6 MB debug image) from return payload. Payload dropped from 20.51 MB to ~1.9 MB.
- Pushed to `main`, Docker image rebuilt and deployed on RunPod.

**Polling timeout increases**
- Frontend: 4 min -> 10 min | Backend: 5 min -> 10 min | avatar_tasks: 5 min -> 10 min.

**SSL fix** — `www.tryon.global` 308 redirect to `tryon.global`.

**Shopify App Store review** — sent follow-up email to `app-review@shopify.com`.

---

## Files changed today

| File | Branch | Change |
|------|--------|--------|
| `frontend/components/analytics/RegionalSizeGlobe.tsx` | `feature/analytics` | Full rewrite: 160k dots, borders, click-to-zoom, city dots, smoother rendering |
| `frontend/components/analytics/Charts.tsx` | `feature/analytics` | `isAnimationActive={false}` on all chart elements for instant tooltips |
| `frontend/app/brand/page.tsx` | `feature/analytics` | Pass `by_city` prop to globe component |
| `backend/app/api/routes/analytics.py` | `feature/analytics` | Add `by_city` to regional-size response, normalize city names |
| `avatar-creation/pipelines/handler.py` | `main` | Excluded `skin_detection_mask` from return payload |
| `backend/app/api/routes/avatar.py` | `feature/analytics` | Backend polling timeout 5 min -> 10 min |
| `backend/app/tasks/avatar_tasks.py` | `feature/analytics` | Task polling timeout 5 min -> 10 min |
| `frontend/lib/api.ts` | `feature/analytics` | Frontend polling timeout 4 min -> 10 min |

---

## Remaining tasks

1. **Add timer to mobile fit passport creation** — shoppers creating their fit passport on phone need a visible countdown/elapsed timer so they know the process is still running and how long it's been. Currently there's no time indicator, which causes uncertainty especially on slower connections or when RunPod is queued.
2. **Test avatar creation with new Docker image** — have colleague retry onboarding to confirm results now arrive in Supabase/dashboard.
3. **Test Apple sign-in from widget** — provider is configured, same flow as Google.
4. **Test OAuth complete-profile flow** — fresh Google/Apple account to verify birthday/phone collection.
5. **Shopify App Store review** — awaiting response from Shopify review team.
6. **Apple secret rotation** — JWT expires ~August 2026.
7. **Globe: light theme polish** — verify colors/contrast on light theme (tested mostly on dark today).
8. **Globe: real city data** — once more events accumulate with city field populated, verify city-level analytics show real data instead of fallback markers.
