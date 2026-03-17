# Status Report — March 13, 2026

**Date:** Friday, March 13, 2026  
**Summary:** App Store listing is almost complete. Frontend app landing now matches tryon.global (light theme, brand-only when from Shopify). **Still to do: record Loom video, then we’ll call it a day.**

---

## What we did today

### App Store listing (Shopify Partners)

- **Pricing:** Added one public **free** plan (internal handle `free`), redirect URL `/`. Plan can be changed or paid tiers added later.
- **App discovery content:** Filled App card subtitle and App store search terms (virtual try-on, size recommendation, fit guide, etc.).
- **Install requirements:** Set “My app requires” → **Shopify Online Store** (theme app extensions).
- **App testing information:**
  - Test account: Tryon credentials provided so reviewers can log in.
  - **Testing instructions:** Step-by-step notes added (install app, open from admin, log in with test account, test storefront Try On flow, check Analytics).
  - **Screencast URL:** Not yet filled — **only remaining item.**

### Frontend: App landing (/app)

- **Shopify vs website:** When opened from Shopify (`?shop=...`), only “Launch Your Brand” is shown; on tryon.global/app without shop param, both “Create Your Fit Passport” and “Launch Your Brand” are shown.
- **Look and feel:** Page matches tryon.global (white background, same layout, lucide icons). Forced light theme on /app so the embedded view in Shopify Admin looks the same as the main site.
- **Pushed to:** `feature/analytics` (commits: app landing brand-only, match tryon.global layout, force light theme).

---

## Current status

| Item | Status |
|------|--------|
| Basic app information | Done |
| App store listing content | Done |
| Pricing details | Done (free plan) |
| App discovery content | Done |
| Install requirements | Done (Online Store) |
| Tracking / Contact | Done (per earlier steps) |
| App testing: Test account | Done |
| App testing: Testing instructions | Done |
| App landing (Shopify = brand only, same look as tryon.global) | Done |
| **App testing: Screencast URL (Loom video)** | **Pending** |

---

## Next: Loom video, then call it a day

1. **Record screencast with Loom (3–8 min)**  
   - Screen + camera (optional). Show: onboarding, merchant flow (app in admin), customer flow (storefront → Try On → size → add to cart), main features.  
   - No loud background noise.

2. **Paste the Loom (or YouTube) URL** into the “Screencast URL” field in App testing information.

3. **Submit for review** when ready (or leave for next session).

After the video is done and the URL is in, we’ll call it a day.

---

## Quick reference

- **App listing:** Shopify Partners → App → Distribution → Manage listing  
- **Screencast:** Loom (or YouTube unlisted), 3–8 min, main features + merchant + customer flow  
- **Testing instructions:** Already in place (439/2800 chars)

---

# Update — March 15, 2026

**Summary:** “Submit for review” was disabled because **Controles ingesloten apps** (embedded app checks) were pending. We added App Bridge from Shopify’s CDN and session-token usage, pushed to `feature/analytics`, created a new dev store, and installed Tryon on it. App loads correctly in the admin. Next: wait for Shopify’s automated check (~2 h), then submit.

## What we did (March 15)

### Embedded app checks (why submit was disabled)

- Shopify requires: (1) **App Bridge script from Shopify’s CDN**, (2) **Session tokens for user verification**, (3) **Use the app in a dev store** so they can run the check (runs automatically about every 2 hours).

### Code changes

- **`ShopifyAppBridge` component** (`frontend/components/ShopifyAppBridge.tsx`): When the app is opened with `?shop=...myshopify.com`, it injects `<meta name="shopify-api-key">` and `<script src="https://cdn.shopify.com/shopifycloud/app-bridge.js">`, and calls the session-token API after load.
- **Root layout:** Renders `ShopifyAppBridge` inside `Suspense` so it runs on all pages when embedded.
- **Pushed to:** `feature/analytics` (commit: “Add App Bridge from Shopify CDN and session token for embedded app checks”).

### Dev store and install

- **New dev store:** Created “Tryon” (tryon-9626.myshopify.com) via **Dev store toevoegen** in the dev dashboard.
- **Install:** Used the install link from Partners (Overview → test/install on dev store), selected the new store, completed OAuth.
- **Result:** Tryon opens in the admin; homepage shows “Virtual Try-On For Everyone” and “Go to Brand Dashboard” — working as expected.

## Current status

| Item | Status |
|------|--------|
| App Bridge from Shopify CDN | Done (injected when `?shop=` present) |
| Session token usage | Done (called when script loads) |
| New dev store | Created (tryon-9626) |
| Tryon installed on dev store | Done |
| **Controles ingesloten apps** | Pending (auto-check ~every 2 h) |
| **Submit for review** | Unlocked after embedded checks pass |

## Next (tomorrow or when check passes)

1. **Use the app once** in the new dev store if not already (e.g. open Brand Dashboard, sign in/onboard).
2. **Wait** for the next run of “Controles ingesloten apps” (up to ~2 hours).
3. In Partners → **Distributie** → **App Store-recensie**, confirm the two embedded-app items are green.
4. Click **Ter controle indienen** and submit for review.
5. **Screencast:** Add Loom (or YouTube) URL to App testing when ready.

---

# Update — March 17, 2026: Why submit was blocked + fix

## Blocker: “Controles ingesloten apps” not passing

Shopify’s automated check looks for:

1. **App Bridge script from Shopify’s CDN** in the **initial HTML** (first response), not only injected by JavaScript after load.
2. **Session tokens** used for user verification (e.g. `getSessionToken()` or `authenticatedFetch`).

Our implementation only injected the script in React `useEffect`, so the checker often didn’t see it.

## Code fix (March 17)

- **Root layout** (`frontend/app/layout.tsx`): Added `<meta name="shopify-api-key">` and `<script src="https://cdn.shopify.com/shopifycloud/app-bridge.js">` in the document `<head>` so they are in the **initial HTML** for every page. No async so the script is present when Shopify’s check runs.
- **ShopifyAppBridge** component: Still runs when `?shop=` is present; if the script is already in the document (from layout), it calls `tryUseSessionToken()` after a short delay so session-token usage is visible.

After deploying this, use the app in the dev store again and wait for the next ~2 h check cycle.

---

# Plan: Get Tryon into the Shopify App Store

## Phase 1: Unblock “Submit for review” (embedded app checks)

1. **Deploy** the March 17 fix (App Bridge in initial HTML) to production (e.g. push to `feature/analytics`, ensure Vercel builds tryon.global from that branch).
2. **Open the app in the dev store**: Partners → Apps → Tryon → Overview → install/test link → open on store tryon-9626 (or your dev store). Land on the app homepage inside the admin.
3. **Use the app**: e.g. click “Go to Brand Dashboard”, sign in or onboard, open the brand dashboard. This generates session data for the check.
4. **Wait** for the next automatic run of “Controles ingesloten apps” (about every 2 hours).
5. **Check**: Partners → Distributie → App Store-recensie. When the two embedded-app items (App Bridge from CDN, session tokens) are green, **Ter controle indienen** becomes active.

## Phase 2: Before you click “Submit for review”

- **Protected customer data**: You already have “Aanvraag toegang tot beschermde klantgegevens voltooid” (request completed). If it’s still “Concept”, open **Toegangsverzoeken voor API** → **Beheren** for that section and submit/finalize if needed.
- **Other API access**: Only request what Tryon actually uses (e.g. read_orders). Ignore “Subscription APIs”, “Payment mandate scopes”, “Post-purchase”, “Product reviews”, “Chat in checkout”, etc. unless you use them.
- **Screencast**: Record a 3–8 min Loom (or YouTube unlisted) showing install → open app → brand onboarding/dashboard → storefront try-on if applicable. Add the URL in App testing information.
- **Testing instructions / test account**: Already in place; keep them up to date.

## Phase 3: Submit and after

1. Click **Ter controle indienen** (Submit for review).
2. Wait for Shopify’s email (review times vary).
3. **Core Web Vitals** (LCP &lt; 2.5s, CLS &lt; 0.1) are measured in the admin panel; if you get feedback on performance, optimize the embedded app load.
4. **Built for Shopify** is optional; you can apply later.
