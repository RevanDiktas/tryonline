# Status Report — March 2, 2026 (updated March 3)

## Mobile widget fix — COMPLETE ✅

- **Status:** All mobile Try On widget work is done and verified.
- **Final tweak (Feb 23):** Avatar vertical offset on mobile set to **y = 0** (no offset); orbit target aligned to 0. Layout and framing look correct on device.
- **Included:** Avatar visible and sized (1.6× scale on mobile), measurements in one horizontal row, full widget fits viewport without scroll, widget opens in PDP iframe (no new tab), Add to Cart works, session persistence (sessionStorage) so login is remembered in same session, compact mobile layout (header, size buttons, add-to-cart). No further mobile widget changes planned.

---

## Done (steps 1 & 2) ✅

- **Step 1 — “Avatar not ready” / 401 in widget:** Fixed. Auth/session in embedded context (e.g. sessionStorage, URL params) now works so shoppers with an avatar can use Try On on the storefront.
- **Step 2 — Mobile layout for dashboards:** Fixed. Brand and shopper dashboards are polished and usable on mobile.

---

## Accomplishments today (March 3)

### Mobile sign-in: always show form
- **Issue:** On phone, tapping "Sign in" from the widget sent users to the sign-in page but they were auto-redirected (stale session) and never saw the form → "Avatar not ready" or broken flow.
- **Fix:** When opening sign-in from the widget on mobile, add `show_form=1` to the URL. Widget sign-in page skips "already logged in" redirect when `show_form=1` and always shows the email/password form. Desktop unchanged.
- **Files:** `frontend/public/test-viewer.html` (buildWidgetSignInUrl), `frontend/app/widget-signin/page.tsx` (showForm check in useEffect).

### Mobile widget: shrink and fit full avatar
- **Issue:** On phone the 3D avatar was too large; head and lower legs were cropped.
- **Fix:** Mobile only (viewport ≤768px): camera FOV 38° (was 28°), camera distance 5.8 (was 4.5); avatar section and canvas-container `max-height: 42vh`, `min-height: 300px`. Avatar scale 1.6× on mobile; vertical offset set to **y = 0** (no offset) for correct framing. Full avatar fits; zoom/rotate/pan unchanged.
- **File:** `frontend/public/test-viewer.html` (initScene + mobile media query). **✅ Verified on device — mobile widget fix complete.**

### Try On “Add to Cart” and cart UI refresh (no full page reload)
- **Goal:** After adding to cart from the Try On widget, the Shopify cart (drawer, icon, count) should update without a full page refresh.
- **Findings:**
  - `POST /cart/add.js` with `sections` and `sections_url` **does** return section HTML (e.g. `main-cart-items`, `cart-drawer`, `cart-icon-bubble`). Confirmed via `[TryOn] Add response had sections: main-cart-items, cart-drawer, cart-icon-bubble`.
  - Section HTML was not applied because **response wrapper IDs did not match the page DOM**. Themes (e.g. Dawn) use dynamic section IDs like `shopify-section-template--14199693705272__main-cart-items`, while the add response sometimes uses static IDs like `shopify-section-main-cart-items`, so `getElementById` failed and no replacement happened.

### Changes made in `shopify_app/extensions/tryon-widget/assets/tryon-cart.js`
1. **Section ID matching**
   - If `getElementById(newEl.id)` finds nothing, fallback to `querySelector('[id^="shopify-section-"][id*="' + keySlug + '"]')` so we find the real section wrapper (e.g. `template--123__main-cart-items`) on the page.
   - Before replacing, set `newEl.id = existing.id` so the theme’s dynamic section ID is preserved and theme JS still targets the right node.

2. **Full node replace**
   - Primary path is `existing.parentNode.replaceChild(newEl, existing)` so the entire section (including custom elements) is swapped; innerHTML fallback kept for robustness.

3. **Bundled sections in add request**
   - Use `getCartSectionIds()` (discovery from DOM + Dawn `data-id` fallback) for the `sections` parameter in `POST /cart/add.js`.
   - Send `sections_url: window.location.pathname` so section HTML is rendered in the current page context.
   - Use locale-aware cart URL when `window.Shopify.routes.root` is available.

4. **Dawn-style refresh**
   - `refreshCartDrawerDawn()`: fetch `?section_id=cart-drawer` and replace `cart-drawer-items`, `.cart-drawer__footer`, `.drawer__contents`, `.cart-drawer__form`; fetch `?section_id=cart-icon-bubble` and replace that section’s innerHTML so the cart icon/count updates.

5. **Timing**
   - Delay opening the cart drawer by 150 ms after section replacement so the new markup is in the DOM before the drawer is shown.

6. **Diagnostics**
   - Log `[TryOn] Replaced N section(s) from add response` so we can confirm sections are being replaced (e.g. 3 when all three sections are returned).

7. **Locale-aware cart.js**
   - Use `window.Shopify.routes.root + 'cart.js'` for the cart count refresh when available.

### March 3 — Cart instant update fixed (Dawn)
- **Issue:** Cart drawer and icon did not update without a full page refresh after adding from the Try On widget, even though `POST /cart/add.js` succeeded and returned section HTML.
- **Root cause:** We were doing our own section HTML replacement. The theme (Dawn) expects its **cart** element to run its own update via `renderContents(response)` — the same path the native “Add to cart” uses.
- **Fix in `tryon-cart.js`:**
  1. **Request sections from the theme:** If `cart-drawer` or `cart-notification` has `getSectionsToRender()`, use that for the `sections` param in `POST /cart/add.js` (same as the native form).
  2. **Use theme’s update after add:** After a successful add, if the theme cart has `renderContents`, call `themeCart.renderContents(addResponse)` so the drawer and icon update exactly like the native button.
  3. **Fallback:** If no theme cart or no `renderContents` (non-Dawn theme), keep existing logic: `renderSections`, `refreshCartDrawerDawn`, count update, open drawer.
- **Result:** Cart drawer opens immediately with the new item(s); icon/count update without refresh. Confirmed on store with two Try On adds (L and M) showing in drawer with correct subtotal.

### Other
- Deploy command for Shopify extension (avoids `._*` on external volumes):  
  `cd /Volumes/Expansion/mvp_pipeline/shopify_app && npm run deploy` (or `bash deploy.sh`).

---

## What was done this session

| # | Task | Status |
|---|------|--------|
| 1 | Use discovered section IDs + `sections_url` in cart/add.js POST | Done |
| 2 | Improve section discovery (main-cart, Dawn data-id, fallback list) | Done |
| 3 | Match section by key when exact id fails (querySelector fallback) | Done |
| 4 | Preserve existing section id when replacing (newEl.id = existing.id) | Done |
| 5 | Prefer full replaceChild for section swap; innerHTML fallback | Done |
| 6 | Dawn-style refresh (section_id=cart-drawer + targeted replace) | Done |
| 7 | Delay drawer open by 150 ms after section update | Done |
| 8 | Diagnostic log: “Replaced N section(s) from add response” | Done |
| 9 | Locale-aware cart.js URL | Done |
| 10 | **(Mar 3)** Use theme `cart.renderContents(response)` for instant cart update (Dawn) | Done |
| — | **“Avatar not ready” + 401** (if still seen) | Mitigated on mobile; revisit if needed |
| 11 | **(Mar 3)** Mobile sign-in: always show form (`show_form=1`) so users can sign in on phone | Done |
| 12 | **(Mar 3)** Mobile widget: shrink + fit full avatar (camera FOV/distance, max-height 42vh); avatar y offset = 0 on mobile | Done — **mobile fix complete** ✅ |

---

## Done — Step 3 (Avatar photo guide) ✅

- **In-app onboarding photo guide:** Complete. On the photo upload step we show: Avoid this, Do this, Photo guide (pose image on #FFFFFF), then Click to upload photo, then Back/Create Avatar. Order teaches guidelines before upload. Desktop: 2-column layout (Avoid+Do left, Photo guide+Upload right) so no scrolling; mobile: single column, tidy text in boxes. Pose image (A-pose, neutral background, tight clothing) and copy are in place. Optional: add a standalone doc (e.g. `docs/AVATAR_PHOTO_GUIDE.md`) later if needed.

---

## Done — Step 4 (Custom domain tryon.global) ✅

- **tryon.global** is live: Vercel (tryonline project), DNS (GoDaddy → Vercel), backend CORS (Railway), Supabase redirect URLs + Site URL, Shopify extension `widget_base` and `shopify.app.toml` (application_url + redirect_urls) all point to tryon.global. Widget and dashboards work on the new domain.

---

## Remaining — For launch / App Store (what’s left to do)

**Steps 3 & 4 are done** (Avatar photo guide + Domain). What’s left is **App Store publishing** so the app can be listed/submitted.

### Before App Store submission (in order)

| # | Item | What to do |
|---|------|------------|
| 1 | **Privacy policy URL** | Host a privacy policy page at tryon.global (e.g. `/privacy`). Required for listing. |
| 2 | **App icon** | Create/finalize 1200×1200 px icon; upload in Partner dashboard. No “Shopify”/“Example” in imagery. |
| 3 | **App listing** | App name, short + long description, screenshots (real app UI). Support/contact info. |
| 4 | **Compliance webhooks** | Subscribe to required compliance webhooks in Partner dashboard. |
| 5 | **Emergency contact** | Set in Partner dashboard (required for App Store). |
| 6 | **Automated checks** | Run Shopify’s automated checks on the App Store review page; fix any failures. |
| 7 | **Error handling pass** | Quick review: token expiry, graceful errors, timeouts. |
| 8 | **Test on second store** | Install on another dev store (different theme if possible); smoke test. |
| 9 | **Submit for review** | Submit; respond to any reviewer feedback. |

**Goal:** Listed and ready (or submitted) so you’re launching with a brand. OK to wrap small items (e.g. second-store test, final double-check) later if needed.

---

## Current state

- **Branch:** `feature/analytics`
- **Try On extension:** Deployed via `shopify_app` (tryon-widget); cart logic in `tryon-cart.js`.
- **Widget:** `frontend/public/test-viewer.html`; init and avatar flow depend on successful auth (e.g. `/auth/me`). User name in header and avatar y on mobile fixed.
- **Cart:** Instant update after Try On add is fixed (Mar 3: theme `renderContents` on Dawn).
- **Domain:** **tryon.global** live (Vercel, DNS, CORS, Supabase, Shopify app URL + redirects).
- **Steps 1–4:** Done (widget/dashboards, avatar photo guide, tryon.global). **Remaining:** App Store prep (privacy, icon, listing, compliance, checks, submit).

---

## Key files touched

- `shopify_app/extensions/tryon-widget/assets/tryon-cart.js` — section matching, replace logic, Dawn refresh, delay, logging, locale-aware URLs.
- `frontend/public/test-viewer.html` — mobile sign-in URL `show_form=1`, mobile camera (FOV 38, distance 5.8), avatar section max-height 42vh, avatar scale 1.6× and **y offset = 0** on mobile (final framing).
- `frontend/app/widget-signin/page.tsx` — when `show_form=1`, skip auto-redirect and always show sign-in form (mobile flow).
- `frontend/app/onboarding/page.tsx` — Avatar photo guide: Avoid/Do, pose image (#FFFFFF), upload order; desktop 2-col no-scroll, mobile tidy.
