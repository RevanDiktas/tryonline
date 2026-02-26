# Status Report — February 26, 2026

## Accomplishments Today

### Login Bug Fixed (Critical)
- Identified root cause: `createBrowserClient` stores sessions in **cookies**, which are blocked by browsers inside the Shopify admin iframe (third-party context)
- Switched Supabase client from cookie-based (`createBrowserClient`) to localStorage-based (`createClient`), which works in iframes
- Added three-tier fallback in `login()`: getSession → direct DB query → auth metadata, so login never silently fails
- Brand login now works correctly inside the Shopify admin iframe

### Shopify App Flow Polished
- **Logout** now redirects to the homepage (`/`) instead of the login page
- **Homepage in Shopify mode** shows brand-focused content:
  - Subtitle: "Add virtual try-on to your store. Reduce returns by up to 40%."
  - Two CTAs: "Sign In" + "Create Brand Account" (no shopper signup)
- **Homepage on main website** remains unchanged: both shopper and brand CTAs
- Removed the auto-redirect from homepage to `/signup` in Shopify mode — homepage now displays properly
- TRYON logo on login/signup pages correctly navigates to the homepage

### End-to-End Shopify Flow Verified
The full flow now works inside the Shopify admin:
1. Install app from distribution link → OAuth connects store
2. Redirect to homepage → brand signs in or creates account
3. Brand dashboard loads inside Shopify admin with analytics
4. Logout returns to the brand-focused homepage
5. Login again works without issues (session persists via localStorage)

---

## Completed from Previous Report's TODO List

| # | Task | Status |
|---|------|--------|
| 1 | Test full Shopify install flow end-to-end | Done |
| 2 | Verify Railway deployment | Done |
| 3 | Fix the Supabase 406 error (users table upsert) | Done (INSERT + UPDATE fallback) |
| — | Fix login inside Shopify iframe | Done (localStorage switch) |
| — | Fix logout redirect + homepage for Shopify | Done |

---

## What Still Needs To Be Done

### Immediate (Next Session)
1. **Brand garment management** — allow brands to upload, view, and categorize garments in their `garments/{brand_id}/` folder from the brand dashboard
2. **Shopify widget integration** — test the TryOn button on a product page in the dev store, ensure shopper login + virtual try-on works end-to-end
3. **Session persistence on page reload** — localStorage works for in-session navigation, but verify sessions survive full page reloads in the Shopify iframe

### Short-term (Before App Store Submission)
4. **Shopify App Store listing** — prepare app name, description, screenshots, privacy policy, and submit for review
5. **Brand onboarding polish** — add a "Getting Started" guide or onboarding steps on the brand dashboard for new brands (e.g., "Upload your first garment", "Install the widget on your store")
6. **Error handling & edge cases** — handle expired Shopify access tokens, graceful error pages, network timeout handling

### Nice-to-have (Post-Launch)
7. **Multi-seat brand accounts** — allow multiple users per brand (contact person vs admin)
8. **Brand billing/pricing** — Stripe integration for brand subscriptions
9. **Shopper ↔ Brand analytics linking** — when a shopper uses TryOn on a brand's product page, link the session to the brand for conversion analytics
10. **Email notifications** — welcome email after brand signup, weekly analytics digest

---

## Architecture Overview

```
┌─────────────────────────┐     ┌──────────────────────────────┐
│  tryonline.vercel.app   │     │ tryon-shopify-theta.vercel   │
│  (APP_MODE=website)     │     │ (APP_MODE=shopify)           │
│  Shoppers + Brands      │     │ Brands only                  │
│  localStorage sessions  │     │ localStorage sessions        │
└────────────┬────────────┘     └──────────────┬───────────────┘
             │                                  │
             └──────────┬───────────────────────┘
                        ▼
         ┌──────────────────────────┐
         │  Railway Backend (API)   │
         │  heroic-celebration...   │
         │  FastAPI + Supabase      │
         └──────────────┬───────────┘
                        ▼
              ┌──────────────────┐
              │    Supabase      │
              │  Auth / DB /     │
              │  Storage         │
              └──────────────────┘
```

**Branch:** `feature/analytics` (production for all services)
**Shopify App Version:** tryon-10 (active)

---

## Key Files Modified Today
- `frontend/lib/supabase-auth.ts` — switched to `createClient`, added login fallback
- `frontend/app/page.tsx` — Shopify-mode homepage (brand-only CTAs, no auto-redirect)
- `frontend/app/brand/page.tsx` — logout redirects to `/` instead of `/login`
