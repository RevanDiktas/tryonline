# Next priorities — App on Shopify market + brand onboarding

**Context:** Try-on widget works on the PDP (pilot store). Adding more products will happen on the real store. Next focus: **get the app on the Shopify App Store** and **make brand onboarding work** so brands that install (from the store or install link) get a guided setup. Then refine.

---

## 1. Brand onboarding (so install = guided setup)

**Goal:** When a brand installs Tryon and opens the app in Shopify admin, they see **our** onboarding (not the public site) and get the widget in one click.

| Step | What |
|------|------|
| **1.1** | **Embedded app** — New route (e.g. `/app` or `/shopify-admin`) in the existing Next.js app that loads inside Shopify admin (embedded). Use Shopify App Bridge + session token to get `shop`. |
| **1.2** | **Onboarding UI** — Welcome → “Add Try On button” (deep link to theme editor to add the Try On block) → “Enable cart” (deep link to activate TryOn cart embed) → Done + link to “We’ll set up your products” or brand dashboard. |
| **1.3** | **Deep links** — Use Shopify block deep link and app embed activate URL (see `docs/BRAND_APP_ONBOARDING_PLAN.md` §5 Phase 1). Need `client_id` from Partners (Tryon app). |
| **1.4** | **App URL in Partners** — Set App URL to the embedded app (e.g. `https://tryonline.vercel.app/app`). OAuth redirect to same. So opening Tryon in Apps shows onboarding. |
| **1.5** | **Install → brand** — On app install (OAuth callback or webhook), backend creates/updates `brands` with `shopify_domain` = shop. |

**Outcome:** Any brand that installs (via link or later via App Store) opens the app → sees onboarding → one click adds block + enables embed → store linked in DB.

**Full spec:** `docs/BRAND_APP_ONBOARDING_PLAN.md` (Phase 1).

---

## 2. App on the Shopify App Store (market)

**Goal:** Tryon is discoverable so merchants can find and install it; onboarding (step 1) is what they see after install.

| Step | What |
|------|------|
| **2.1** | **Listing** — Icon 1200×1200, description, screenshots, support/emergency contact. No “Shopify” or “Example” in app URLs or API contact (App Store rule). |
| **2.2** | **Compliance** — Compliance webhooks subscribed; emergency contact set. |
| **2.3** | **Automated checks** — Run Shopify’s checks; fix any failures. |
| **2.4** | **Submit** — Submit for review. Review typically 1–2 weeks. |

**Outcome:** App is on the Shopify App Store; new brands discover and install → go through onboarding (step 1).

**Full spec:** `docs/SHOPIFY_APP_STORE_WIDGET_PLAN.md` (Part A.5, Step 8, listing requirements).

---

## 3. After that — refine

- Add more products with try-on **on the real store** (Supabase `garments` + `shopify_product_id` per product).
- Orders/paid webhook + `SHOPIFY_WEBHOOK_SECRET` if not already done.
- Optional: custom domain, analytics daily cron, UX polish.

---

## Order

1. **First:** Brand onboarding (embedded app + install → brand + deep links). Without this, even after listing, installs would have no guided setup.
2. **Then:** App Store listing and submit. Then the app is on the market and installs flow through onboarding.
3. **Then:** Refine (more products on real store, webhook, polish).

---

## References

| Doc | Content |
|-----|--------|
| `docs/BRAND_APP_ONBOARDING_PLAN.md` | Full onboarding plan, Phase 1–4, technical details |
| `docs/SHOPIFY_APP_STORE_WIDGET_PLAN.md` | App Store requirements, listing, compliance, submit |
