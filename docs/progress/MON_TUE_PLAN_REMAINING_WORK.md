# Remaining work — structured overview & Mon–Tue plan

**Goal:** Everything done **this week** — preferably by **Tuesday**; OK to wrap small stuff **Wednesday evening**. **Launching with a brand.**  
**Approach:** Quickest path + highest quality.  
**Domain (planned):** **tryon.global** (best/cheapest option for now).

---

## 1. What still needs to be done (full list)

### Must-do before App Store

| # | Item | What it is | Why it matters |
|---|------|------------|----------------|
| **3** | ~~Avatar photo guide~~ | ✅ **Done.** In-app onboarding: Avoid/Do, pose image, upload order; desktop no-scroll, mobile tidy. | — |
| **4** | ~~**Custom domain**~~ | ✅ **Done.** **tryon.global** live (Vercel, DNS, CORS, Supabase, Shopify app URL + redirects). | — |

### App Store publishing (after 3 & 4)

| # | Item | What it is | Why it matters |
|---|------|------------|----------------|
| 5 | **Privacy policy URL** | Hosted privacy policy page; link in app listing and in app | Required for App Store submission. |
| 6 | **App listing** | App name, short/long description, screenshots (per Shopify requirements), support/contact | Required for discovery and review. |
| 7 | **App icon** | 1200×1200 px icon; no "Shopify"/"Example" in imagery | Required for listing. |
| 8 | **Compliance webhooks** | Subscribe to required Shopify compliance webhooks (per current Partner dashboard) | Required for App Store. |
| 9 | **Emergency contact** | Set in Partner dashboard | Required for App Store. |
| 10 | **Review checklist & automated checks** | Run Shopify’s automated checks; fix any failures before submit | Reduces rejections and back-and-forth. |
| 11 | **Error handling & edge cases** | Expired Shopify tokens, graceful error pages, network timeouts | Better review outcome and UX. |
| 12 | **Test on second store** | Install and test on another dev store (different theme if possible) | Confirms no single-store quirks; review often tests on multiple themes. |

### Optional / later (not blocking “everything done by Tuesday”)

- Brand garment management (upload from dashboard)
- Brand onboarding polish (“Getting Started” steps)
- Multi-seat, billing, email digest, etc.

---

## 2. Priority order (recommended)

**Phase A — Done ✅**  
Steps 3 and 4 complete.

1. ~~**Step 3 — Avatar photo guide**~~ ✅ Done (in-app onboarding photo step).
2. ~~**Step 4 — Custom domain (tryon.global)**~~ ✅ Done. Vercel + DNS + CORS + Supabase + Shopify app URLs. Unblocks App Store and privacy policy URL.

**Phase B — App Store publishing (Tuesday)**  
Once 3 & 4 are done, do these in this order:

3. **Privacy policy** — Write or adapt a one-pager; host on your domain (e.g. `yourapp.com/privacy`).  
4. **App icon** — 1200×1200; create or finalize.  
5. **App listing** — Name, description, screenshots (use real UI from your app).  
6. **Compliance + emergency contact** — In Partner dashboard: webhooks + contact.  
7. **Automated checks** — Run checks; fix any failures.  
8. **Error handling pass** — Quick review: token expiry, errors, timeouts.  
9. **Test on second store** — Install on another dev store; smoke test.  
10. **Submit for review** — Submit; then respond to any reviewer feedback.

---

## 3. Mon–Tue plan (quickest + high quality)

### Step 3 — Done ✅

Avatar photo guide is **implemented in-app** (onboarding photo step: Avoid/Do, pose image, upload order; desktop 2-col no-scroll, mobile tidy). No separate doc required for launch.

### Step 4 — Custom domain (tryon.global) — Done ✅

tryon.global is live: Vercel, DNS, backend CORS, Supabase redirects, Shopify app URL and redirect_urls. Widget and dashboards work on the new domain.

---

### Tuesday (full day)

**Order to be refined tomorrow evening after Mon is done.** For now:

| Block | Tasks | Notes |
|-------|--------|--------|
| **Privacy** | Host privacy policy on tryon.global (e.g. `/privacy`). | Required for listing; can use template + adapt. |
| **Icon** | 1200×1200; create/finalize; upload in Partner dashboard. | Can prep file(s) Monday if helpful. |
| **Listing** | Name, short + long description, screenshots (real app UI). | Double-check everything before going live. |
| **Checks** | Compliance webhooks, emergency contact, automated checks. | Fix any failures before submit. |
| **Optional** | Error handling pass, test on second store, then submit. | Wrap small stuff Wednesday evening if needed. |

**Tuesday end state:** Privacy, icon, listing done; everything double-checked; listed / submitted. **Must be done this week — launching with a brand.**

---

## 4. Where things live (reference)

| What | Where |
|------|--------|
| Latest status (steps 1–4, App Store) | `docs/progress/2026-03-02_STATUS_REPORT.md` |
| Launch order & domain | `docs/SHOPIFY_APP_STORE_WIDGET_PLAN.md` (Part A, Part C) |
| App Store requirements | `docs/SHOPIFY_APP_STORE_WIDGET_PLAN.md` (Part D, §2.3); [Shopify App Store requirements](https://shopify.dev/docs/apps/launch/shopify-app-store/app-store-requirements) |
| Deploy extension | `cd shopify_app && npm run deploy` (or `bash deploy.sh`) |

---

## 5. If time is tight

**Must be done this week — launching with a brand.** Tuesday target; OK to wrap Wednesday evening.

**Minimum by EOD Tuesday:** Step 3 + 4 (Mon); privacy live on tryon.global; icon + listing filled; compliance + contact set; checks run and critical issues fixed; listed / submitted.

**Can wrap Wednesday evening if needed:** Final double-check, icon prep, second-store test, or small follow-ups after submit.

---

*Created: Sunday. Monday evening: step 3 + step 4 (both done). Tuesday: privacy, icon, listing, double-check, list. Done this week (Tuesday ideal; Wednesday evening OK). Launching with a brand. Update this record when Mon is done to structure Tuesday.*
