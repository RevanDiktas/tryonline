# Frontend update 2026-05-11 (Mon)

## Headline

Five commits shipped to `feature/analytics` covering the marketing hero, the shopper dashboard avatar, and three icon assets (favicon, dark-mode moon, Apple SSO pictogram). Validated visually by Revan: logo, moon, and Apple pictogram all confirmed clean.

## Commits pushed

| SHA       | Scope                | Summary |
|-----------|----------------------|---------|
| `b201d5f` | Hero (GLB swap)      | Hero avatar + garment swapped to local `avatar_textured.glb` + bow-sweats `v45.12.1` outputs in `public/redesign/`, avatar locked to auto-rotate (no drag). |
| `5851bf1` | Hero (render fix)    | Replaced `AlignedScene` with `DrapedScene`, added unit auto-detect (mm vs m), moved lighting to ACES + warehouse HDR. |
| `de0e0cf` | Headline + dashboard | Headline shortened to `Tryon before you buy.`; shopper dashboard avatar now full viewport with auto-framing camera + `ResizeObserver`. |
| `5fe5700` | Dashboard spacing    | Page padding, column gap, and avatar column ratio tightened so cards stop drifting apart. |
| `4f6be6e` | Icons + favicon      | Mask-based crescent moon in both `SharedNav` and `DashboardShell`, Lucide apple SVG on the SSO button, TryOn favicon installed as `app/icon.png`. |

## Detail

### 1. Hero GLB swap and render fix

The homepage hero was loading the avatar and small-logo M garment from public Supabase URLs through `AlignedScene` (the same component the live PDP widget uses). On the bow-sweats M output `AlignedScene` independently normalized avatar and garment to 1.8m height, which inflated the sweater to roughly 2.6x its real size and caused the garment to swallow the avatar's face and hands.

Fix landed in two parts.

First commit (`b201d5f`) replaced the Supabase URLs with locally-shipped GLBs under `frontend/public/redesign/` so the homepage no longer blocks on storage, locked drag/pan/zoom off (`interactive={false}` at both desktop and mobile call sites; `autoRotate` stays on), and added `frontend/public/redesign/*.glb` to the `.gitignore` allowlist alongside the existing `frontend/public/models/*.glb` rule.

Second commit (`5851bf1`) replaced `AlignedScene` with a local `DrapedScene` that:

- Loads both GLBs at `scale=1, position=0,0,0` so the drape pipeline's shared world coords are preserved.
- Detects per-mesh unit from the y-extent. The avatar GLB exports in millimeters (y ~1800), the drape pipeline exports in meters (y ~1.83). Without that conversion the meter-scale garment got crushed to 1mm tall and disappeared.
- Applies one uniform scale on the wrapping group to fit `TARGET_HEIGHT=1.8m`, then translates so the bbox bottom lands on `FLOOR_Y=-0.9` where the `ContactShadows` plane lives.

Lighting moved to standard glTF showcase setup: `ACESFilmicToneMapping`, `toneMappingExposure=1.25`, `Environment preset="warehouse"` with `environmentIntensity=1.1`. The RAMIN print on the chest is textured grey (~rgb 99) under `alphaMode=MASK`; the previous city HDR was too dim for the grey to read on the black hoodie, the new warehouse HDR + bumped exposure surfaces it.

### 2. Shopper dashboard avatar (`de0e0cf`, `5fe5700`)

The shopper dashboard at `/dashboard` was cropping the avatar above the head and below the knees. Two underlying causes:

1. Layout: grid was `1fr / 1.2fr` with the avatar in a `4/5` aspect ratio card and `minHeight: 240`. The avatar column was the narrower one, the aspect locked the card to portrait regardless of viewport, and the canvas never got vertical room.
2. Rendering: avatar was scaled by `1.8 / max(size.x, size.y, size.z)`. For an A-pose where arm span exceeds height, `maxDim` is the arm dimension; the model came out shorter than 1.8m but the camera was still positioned for a 1.8m subject so head and feet drifted out of frame. `setSize` ran exactly once on init, so any container resize put the canvas out of sync with the camera aspect.

`de0e0cf` flipped the grid to `1.6fr / 1fr` (avatar dominant), swapped the aspect ratio for `height: calc(100vh - 220px), minHeight: 560` on desktop / `70vh, minHeight: 420` on mobile, normalized on `size.y` instead of `maxDim`, and replaced the hard-coded camera with a `frameCamera()` that recomputes distance from canvas aspect on every resize. A `ResizeObserver` keeps the renderer + camera in sync as the column flexes.

`5fe5700` was the follow-up tighten: page padding 20/24/28 → 14/24/22, heading-to-grid gap 16 → 10, avatar/measurements column gap 20 → 14, avatar column ratio relaxed to `1.05fr / 1fr` since the A-pose was never going to fill the wider column anyway and the measurements card deserved more horizontal room.

### 3. Icon cleanup and favicon (`4f6be6e`)

Three deferred bits that had been driving the page to look amateur:

- **Moon icon (dark mode toggle)**. Two separate copies in the codebase. `DashboardShell.tsx` (used on `/dashboard`) and `SharedNav.tsx` (used on homepage, pricing, demo, lobby, brand/cohorts, and the Broadcast nav) each had a hand-rolled crescent with the path `M11 8.5A4.5 4.5 0 016.5 4 4 4 0 109 11.5 4.5 4.5 0 0111 8.5z`. The two-arc geometry rendered as a wedge with a visible notch where the inner arc met the outer at small sizes. First fix only touched `DashboardShell`, which is why the homepage moon still looked broken on the next test. Final fix: both files now use a mask-based crescent (one filled circle minus an offset circle) with file-scoped mask IDs so they don't collide. Result is a true half-moon with no arc-meeting wedge.

- **Apple SSO pictogram**. The SSO button used a hand-rolled path on `viewBox="-2 0 26 24"`. The leaf sat right against the top viewBox edge so any subpixel rounding clipped it. Swapped to the Lucide apple icon on a standard `viewBox="0 0 24 24"` with the leaf comfortably inside the box.

- **Favicon**. `/Volumes/Expansion/web.png` (the TryOn black-square pictogram, 1201x1201) installed as `frontend/app/icon.png`. Next.js App Router convention auto-injects `<link rel="icon" href="/icon.png" sizes="1201x1201">` into the HTML head; replaces Vercel's globe in browser tabs. Required adding `!frontend/app/icon.png` and `!frontend/app/apple-icon.png` to the gitignore allowlist next to the existing `frontend/public/**/*.png` rules. Hard refresh (Cmd+Shift+R) needed to clear the cached globe.

## Key files

| Area                  | File |
|-----------------------|------|
| Hero scene            | `frontend/components/redesign/AvatarHero.tsx` |
| Hero call sites       | `frontend/components/redesign/Broadcast.tsx` (l.244, l.914) |
| Hero GLBs             | `frontend/public/redesign/avatar_textured.glb`, `frontend/public/redesign/bow-sweats_m.glb` |
| Shopper dashboard     | `frontend/app/dashboard/page.tsx` (Three.js useEffect + grid block) |
| Dark mode toggle (homepage et al) | `frontend/components/redesign/SharedNav.tsx` |
| Dark mode toggle (dashboard)      | `frontend/components/redesign/DashboardShell.tsx` |
| Apple SSO icon        | `frontend/components/redesign/AuthForms.tsx` (`AppleA`) |
| Favicon               | `frontend/app/icon.png` |
| GLB + icon allowlist  | `.gitignore` |

## Validated

- Homepage hero (desktop) renders bow-sweats M on `avatar_textured.glb` with the grey RAMIN print readable, auto-rotates, no drag.
- `/dashboard` avatar fits head to feet in a 100vh-bound card; spacing reads tight, not airy.
- TryOn favicon visible in browser tab (after hard refresh).
- Crescent moon button is a clean half-moon shape, no wedge.
- Apple SSO button on `/signup` and `/login` shows the full apple with leaf intact.

## Next

Remaining shopper-dashboard polish and the Fortnite-lobby vision at `/dashboard/lobby` are still open. No frontend work blocking on backend or RunPod cycles.
