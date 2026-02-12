# Status Update — January 26, 2026

**Date:** January 26, 2026  
**Open this in ~2 days** when you're back to pick up work.  
**Single source of truth:** `docs/IMPLEMENTATION_PLAN_WHEN_BACK.md`

---

## What We Did (Planning Lock)

- **Implementation plan** is complete and in `IMPLEMENTATION_PLAN_WHEN_BACK.md`. It covers:
  - **Brand onboarding:** Lead form when someone picks “I’m a Brand” → `/brands/lead` → we contact them (no account).
  - **Tracking:** “Click” API (`POST /api/events/track`), per-event spec, scripts, storage (`analytics_events` → `analytics_daily`), algos (daily + WTD/MTD/QTD/YTD).
  - **We use vs Brand gets:** We use everything (avatar failures, errors, full funnel); brand dashboard shows only try-ons, size selected, add-to-cart, **purchases through our widget**, revenue, conversion, sizing, region. No returns at MVP.
  - **Dashboard:** Time filters (Today / WTD / MTD / QTD / YTD), KPIs, funnel, sizing, products, region, export. Displays algo output.
  - **Shopify:** Button + embed use our API; webhooks for `orders/paid` → `purchase` only. Attribution via `session_id` in cart.
  - **Phases 1–4:** Brand leads → event wiring + events + daily + algos → dashboard → Shopify button + webhooks.

- **Tracked actions (5.4):** Research-based list. Must-have: `widget_opened`, `tryon_started`, `size_recommended`, `size_selected`, `add_to_cart`, `purchase`, `avatar_started`, `avatar_created` + region. High-value: `widget_closed`, `tryon_ended`, `size_viewed`, `checkout_started`, etc.

- **Gaps added to plan (Section 10):** Four items to fix before/during build:
  1. **Privacy / consent** — Photo/avatar consent, retention/deletion, privacy policy for widget.
  2. **Rate limiting on `POST /api/events/track`** — Prevent abuse and metric inflation.
  3. **Timezone** — Decide UTC vs brand TZ for “Today” and WTD/MTD/QTD/YTD.
  4. **Who accesses our internal dashboard** — Auth, internal-only, etc.

---

## What’s Already Working (Unchanged)

- Avatar creation pipeline (RunPod, Supabase, measurements).
- Try-on viewer, size selector, fit recommendations, add-to-cart callback.
- User flow: signup → onboarding → dashboard.
- Backend API, frontend, `POST /api/events/track` exists but is **not wired** from the UI yet.

---

## When You’re Back

1. **Read** `IMPLEMENTATION_PLAN_WHEN_BACK.md` (full plan).
2. **Start with Phase 1:** Brand lead flow (table, API, `/brands/lead` page, signup routing).
3. **Then Phase 2:** Event wiring + events + daily grain. Use tracked actions in 5.4 and extend 4.2.
4. **Then Phase 3:** Dashboard (algo output, we-use vs brand-gets).
5. **Then Phase 4:** Shopify button + webhooks + attribution.
6. **Address Section 10** (privacy, rate limit, timezone, dashboard access) as you build.

---

## Summary in Plain Language (What Still Needs to Be Built)

**For a 5th grader:**

1. **Brand signup form**  
   When someone says “I’m a brand,” they fill out a form (name, email, etc.) so we can call them. We don’t build a full brand account yet—just save their info.

2. **Counting what people do**  
   We need to count things like: “They opened Try On,” “They picked size M,” “They clicked Add to Cart,” “They bought something.” Right now we don’t save that. We’ll add code so every important click sends a message to our server and we store it.

3. **Adding up the numbers**  
   We store each action by day. Then we add them up for “this week,” “this month,” etc. A separate program does that math so the dashboard can show charts.

4. **The dashboard**  
   A page with charts and numbers: how many try-ons, how many bought, which sizes people chose, which products won. **We** see extra stuff (like “avatar broke”); **brands** only see what matters to them (try-ons, sizes, sales). You can pick “today,” “this week,” “this month,” etc.

5. **Shopify connection**  
   The “Try On” button on a store needs to talk to our system. When someone buys, Shopify tells us, and we remember it was from our try-on. We’re not doing returns yet—just “what they bought.”

6. **Housekeeping**  
   We also need to: ask permission before using photos, limit how many “count” messages one person can send, decide what “today” means (our timezone vs the store’s), and lock the dashboard so only we can see our internal view.

**In one sentence:** We still need to build the brand form, start counting and storing what people do in the try-on, add up those numbers by day/week/month, show them in a dashboard (different for us vs brands), and connect the Shopify button and purchase data—plus a few rules for privacy, safety, and who can see what.

---

*Last updated: January 26, 2026.*
