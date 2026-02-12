# Status Update — February 5, 2026

**Date:** February 5, 2026  
**Open this when you're back** for today's summary + tomorrow's plan.

---

## What We Did Today

### 1. Brand Dashboard — Black & White Lab Aesthetic
- Switched from slate/blue undertones to **pure black/white** palette
- Background: `bg-black` (dark), `bg-white` (light)
- Panels: `bg-white/[0.03]` / `bg-black/[0.03]` — no borders
- Consistent grayscale for charts, tables, labels
- High-end lab / quant-style look (Optiver-inspired)

### 2. Day / Night Mode (Theme Toggle)
- **ThemeProvider** (`frontend/contexts/ThemeContext.tsx`) — stores `light` | `dark`, persists to `localStorage`
- **Brand dashboard** (`/brand`): sun/moon toggle in header; all components theme-aware
- **User dashboard** (`/dashboard`): same toggle; panels, text, buttons adapt
- Both dashboards support full light and dark themes

### 3. GLB Viewer Background — Theme-Aware
- **User dashboard avatar canvas** (Three.js): `scene.background` switches with theme
  - Dark: `0x0a0a0a` | Light: `0xf9fafb`
- Reads `localStorage.getItem('tryon-theme')` on init; syncs via `useEffect` when theme changes
- File: `frontend/app/dashboard/page.tsx` — `sceneRef`, theme effect

### 4. Avatar GLB Viewer — Brighter Lighting
- Avatar was appearing dark/muted in the viewer; adjusted lighting so it appears bright and true to original color
- **Lighting changes:** Ambient 0.7→1.4, front 0.9→1.5, back 0.4→1.0; added fill light (0.8)
- **Renderer:** `outputColorSpace = SRGBColorSpace`, `toneMappingExposure = 1.3`
- File: `frontend/app/dashboard/page.tsx` — Three.js scene lighting

### 5. Chart Upgrades
- **Tooltips:** Borderless, soft shadow; dark = `rgba(10,10,10,0.95)`; light = `rgba(255,255,255,0.96)`
- **Grid lines:** Subtler (opacity 0.06 dark)
- **Bars:** Larger radius (6px), `maxBarSize` 32
- **Axis labels:** Refined typography (fontWeight 500, opacity)
- File: `frontend/components/analytics/Charts.tsx`

### 6. Panel & Layout Polish
- **Removed all borders** from panels, metric cards, tables (no more "amateuristic" outlines)
- **Rounded corners:** `rounded-2xl` for panels, `rounded-xl` for cards
- **Typography:** Tighter tracking (`0.22em`), larger metric values (`text-xl`), `tracking-tight` on headings
- **Transitions:** 300ms ease-out on panels, metric cells
- **Fade-in:** `dashboard-fade-in` animation on main content
- **Uniform chart heights:** `CHART_HEIGHT = 200` — all graph panels use same min-height

### 7. Edit Button & White Widgets
- Edit button on user dashboard matches "Open widget" style: `bg-white text-black` (dark) / `bg-slate-900 text-white` (light)
- Consistent primary action styling across dashboards

### 8. User Dashboard Polish
- Borders removed from all cards
- Light mode: `shadow-sm` for depth
- Theme-aware typography, buttons, inputs
- `dashboard-fade-in` on main content

---

## What's Ready

| Area | Status |
|------|--------|
| Brand dashboard (ROI, Fit, Trend tabs) | ✓ Polished, theme-aware |
| User dashboard (avatar, measurements, fit passport) | ✓ Polished, theme-aware |
| Avatar GLB viewer lighting | ✓ Bright, true to original color |
| Day/night theme toggle | ✓ Both dashboards, persisted |
| GLB viewer background | ✓ Adapts to theme |
| Charts (funnel, velocity, size dist, exploration, regional) | ✓ Refined tooltips, bars, grid |
| Category A & B analytics | ✓ Implemented (previous sessions) |

---

## What We Still Need to Do

### 1. Step 2 & 3 of MORE DATA (Before / Alongside UI)

Per `docs/QUANT_DATA_STRATEGY.md` Section 7:

| Step | Description | Status |
|------|-------------|--------|
| **Step 2: Variables per category** | Ensure all raw datapoints are captured and schema-aligned | ⏳ Pending |
| **Step 3: Calculations** | Derived variable formulas, daily aggregation job, Parquet export | ⏳ Pending |

**Step 2 details:**
- Schema alignment: `brand_id`, `country`, `city` on every event
- Wire `trackEvent` in frontend (embed, onboarding, widget) — backend enriches with region
- Resolve product_id vs garment_id mapping

**Step 3 details:**
- Define derived variable calculations (see QUANT_DATA_STRATEGY Sections 3.1–3.3)
- Implement daily aggregation job → `analytics_daily`
- Parquet export for quant workloads (optional but recommended)

*Note: We built the UI before completing Step 2 & 3. The dashboard works with current event data, but full quant/data strategy alignment is still pending.*

### 2. Checkout Profile — Address & Billing (Planned for Tomorrow)

**Concept:** Users store **shipping address**, **billing info**, and other checkout details once in their TryOn dashboard. This profile is reused across all TryOn-integrated brands. At checkout, the user only **confirms** pre-filled info instead of typing it every time.

**Scope:**
- New schema: `user_addresses`, `user_billing` (or combined `user_checkout_profile`)
- Dashboard UI: "Shipping & Billing" section in user dashboard
- API: CRUD for addresses, billing
- Merchant integration: API for brands to fetch user profile (with consent) at checkout; "Confirm your info" flow

**Why:** Faster checkout, fewer errors, higher conversion, happier users.

### 3. Recommended Size Visualization — Improve General Size per Region

**Concept:** Make the visualization of **recommended size** data stronger so we can understand **average size per region** more accurately. Better regional size insights → more accurate buying/ allocation decisions.

**Scope:**
- Improve how recommended-size data is visualised (e.g. in Fit Accuracy / Regional Size charts)
- Ensure regional breakdown shows recommended vs selected vs purchased clearly
- Surface average/typical size per region so we can quantify regional demand

---

## Plan for Tomorrow (Feb 6)

1. **Checkout Profile — Phase 1**
   - Design schema (addresses, billing)
   - Create migration
   - Add API routes (get/update profile)
   - Add "Shipping & Billing" section to user dashboard UI

2. **Step 2 of MORE DATA**
   - Add `country`, `city` to analytics_events (from user profile or IP)
   - Ensure `brand_id` on events where applicable
   - Wire trackEvent in embed/widget if not already

3. **Step 3 of MORE DATA** (if time)
   - Prioritise derived calculations for dashboard
   - Daily aggregation job (if not present)

4. **Recommended size visualization**
   - Improve general size viz for recommended size
   - Surface average size per region more clearly

---

## Key File Locations

| Area | Path |
|------|------|
| Theme context | `frontend/contexts/ThemeContext.tsx` |
| Brand dashboard | `frontend/app/brand/page.tsx` |
| User dashboard | `frontend/app/dashboard/page.tsx` |
| Charts | `frontend/components/analytics/Charts.tsx` |
| Quant data strategy | `docs/QUANT_DATA_STRATEGY.md` |
| Data inventory | `docs/DATA_INVENTORY_FOR_QUANT.md` |
| Category C roadmap | `docs/analytics/IMPLEMENTATION_ROADMAP_CATEGORY_C.md` |

---

## Summary

**Today:** Dashboard UI upgraded — black/white lab aesthetic, day/night mode, theme-aware GLB viewer, brighter avatar lighting, softer charts, no borders, polished typography and transitions.

**Still to do:** Step 2 & 3 of MORE DATA (variables + calculations), Checkout Profile (addresses, billing, confirm at checkout).

**Tomorrow:** Checkout Profile Phase 1 + Step 2 MORE DATA.

---

*Last updated: February 5, 2026.*
