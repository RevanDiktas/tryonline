# What’s Next — Structured Plan (Post–Addresses)

**Context:** Shipping addresses are done (schema, backend API, dashboard UI, data in Supabase). Below is a clear order of what to implement next and how.

---

## Option A — Checkout profile API (use address at brand checkout)

**What we implement**

- **Backend:** A merchant- or app-facing endpoint that returns the **default shipping address** for a user, with **consent** (e.g. user identified by session token or signed request from the widget).
- **Use case:** When the user clicks “Checkout” on a TryOn brand:
  - Either a **Shopify Checkout UI Extension** (or similar) calls our API with the user’s identity → we return default address → brand pre-fills checkout.
  - Or a **TryOn bridge page** (“Confirm your info”) shows the user their default address, they click “Continue to checkout” → we pass address (e.g. in URL params or cart attributes) to the brand’s checkout.
- **No change** to the address UI you already have; we only **expose** the default address in a controlled way.

**Implementation steps**

1. **Backend**
   - Add `GET /api/checkout-profile` (or `GET /api/me/default-address`).
   - **Auth/consent:** Either:
     - Require a **signed token** (e.g. JWT or HMAC) that encodes `user_id` + `shop_domain` + expiry, issued when the user clicks “Checkout” from the widget; or
     - Require **session token** from the TryOn widget that we map to `user_id` (if we already have that).
   - Response: default address only (label, name, line1, line2, city, state, postal_code, country). No `user_id` or other PII beyond what’s needed for shipping.
2. **Frontend (optional for MVP)**
   - If we do a bridge page: add a route (e.g. `/checkout/confirm`) that shows default address, “Continue to [Brand] checkout” button, and redirects to brand with address in query/attributes if the brand supports it.
3. **Docs**
   - Short spec for brands: how to call the API (auth, query params), response shape, and example.

**Out of scope for this step**

- Payment, wishlist, order history (per your earlier priorities).

---

## Option B — Step 2 of MORE DATA (analytics schema + wiring)

**What we implement**

- **Schema/events:** Ensure every analytics event that can have **country** and **city** gets them (from user profile or IP fallback). Ensure **brand_id** is set where applicable.
- **Backend:** Enrich `track_event` (or equivalent) with:
  - `country`, `city` from `users` or `user_addresses` when `user_id` is present; else from IP (e.g. GeoIP) if you want.
  - `brand_id` when we have a mapping (e.g. shop_domain → brand_id).
- **Frontend:** Ensure the embed/widget (and onboarding if relevant) **always** call the track endpoint for the key funnel events; no missing events.

**Implementation steps**

1. **DB**
   - Confirm `analytics_events` (or current events table) has columns `country`, `city`, `brand_id` (add if missing via migration).
2. **Backend**
   - In the event-tracking handler:
     - If `user_id` present: load `country`/`city` from `users` or from default `user_addresses`; fallback to existing payload.
     - Resolve `brand_id` from `shop_domain` (e.g. lookup table or config).
   - Write only what’s needed for analytics; no new public API.
3. **Frontend**
   - Audit embed/widget/onboarding: list every place that should fire an event (opened, started, size_viewed, add_to_cart, checkout_started, etc.) and ensure they all call the backend track API with the required context (session_id, user_id if logged in, shop_domain, product_id).
4. **Docs**
   - Update QUANT_DATA_STRATEGY or DATA_FLOW with “Step 2 done: events have country, city, brand_id where applicable.”

**Out of scope for this step**

- Step 3 (derived calculations, daily aggregation, Parquet). That’s a separate chunk of work.

---

## Option C — Recommended size visualization (brand dashboard)

**What we implement**

- **Brand dashboard:** Improve how **recommended size** and **regional size** are shown:
  - Fit Accuracy / Regional Size charts: show recommended vs selected vs purchased more clearly.
  - Surface **average/typical size per region** (e.g. “Most common recommended size in NL: M”) so brands can see regional demand at a glance.

**Implementation steps**

1. **Backend**
   - Add or reuse an analytics endpoint that returns:
     - Per region (country or country+city): counts or distribution of recommended size, selected size, purchased size; optional “top size” or “average” per region.
2. **Frontend**
   - In the brand dashboard (e.g. Fit Accuracy / Regional tab):
     - Use the new (or existing) API to show regional breakdown and “typical size per region.”
     - Adjust charts (e.g. tooltips, labels, or a small summary card) so recommended vs selected vs purchased is obvious.

**Out of scope for this step**

- Changing how we *compute* recommended size; only how we *visualize* it.

---

## Option D — Address UX polish (optional)

**What we implement**

- **Country:** Dropdown or typeahead (e.g. ISO countries) instead of free text.
- **Validation:** Optional client- or server-side checks (e.g. required fields, postal code format per country).
- **Copy:** Small tweaks (e.g. “Use at checkout” already in place; add “Default” if you want).

**Implementation steps**

1. **Frontend**
   - Add a country list (e.g. static JSON or a small API) and use it in the address form (dropdown or combobox).
   - Optionally validate before submit (e.g. non-empty required fields, basic postal code pattern).
2. **Backend**
   - Optional: light server-side validation on POST/PATCH (e.g. required fields, max lengths).

---

## Suggested order

| Priority | Option | Why |
|----------|--------|-----|
| **1** | **A — Checkout profile API** | Closes the loop: addresses are not only stored but **usable** at brand checkout. Enables bridge page or Shopify extension next. |
| **2** | **B — Step 2 MORE DATA** | Makes analytics and quant strategy correct (country, city, brand_id on events). Needed for reliable dashboards and future modeling. |
| **3** | **C — Recommended size viz** | Improves brand dashboard value without changing the rest of the stack. |
| **4** | **D — Address UX polish** | Nice-to-have; can be done anytime. |

---

## What we’ll implement next (recommendation)

- **Next:** **Option A — Checkout profile API**
  - One new backend route that returns default address with consent.
  - Optional: minimal “Confirm your info” bridge page that shows default address and a “Continue to checkout” action.
- **After that:** **Option B — Step 2 MORE DATA** (schema + enrichment + event wiring).

If you confirm you want to start with **Option A**, the next step is to implement the backend endpoint and (if you want) the bridge page as above.
