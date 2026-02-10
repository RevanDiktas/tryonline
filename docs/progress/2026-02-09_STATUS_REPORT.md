# Status Report — February 9, 2026

**Date:** Monday, February 9, 2026  
**Open this tomorrow evening** when you continue. Our main priority is to **ship**.

---

## Top priority: ship

**The one thing that matters:** Execute the launch plan. When it’s done, we’re shipped.

**Single source of truth:** `docs/SHOPIFY_APP_STORE_WIDGET_PLAN.md`

That doc has everything: launch order (domain → Supabase → backend → frontend → RunPod → widget/CORS → Shopify pilot), what runs where, every code change we need (Part B), step-by-step server-by-server (Part C), time estimate (~18–24 hours to pilot), and the Shopify App Store widget details (Part D). **“App Store” in that doc = Shopify App Store only** (not Apple).

We’re not building new features. We’re **tying loose ends** and getting the product live so a brand can use the Try On widget on their store.

**Every step (in order):**
1. Domain
2. Code changes (Part B: CORS, PORT, env.example, test-viewer apiUrl)
3. Backend deploy (Railway or Render)
4. Frontend deploy (Vercel)
5. RunPod verify (endpoint + API key in backend env)
6. Widget URL + CORS test
7. Shopify app pilot (Partner app, theme extension, install on dev store, test)

When 1–7 are done = pilot launched. Shopify App Store listing = after pilot.

---

## What we need to do (in order)

1. **Domain** — You’re getting the domain tomorrow. No “Shopify” or “Example” in the name. Once we have it, we use it for frontend (and optionally backend) and document it.
2. **Code changes (Part B in the plan)** — Backend: CORS from env, PORT from env, `SHOPIFY_WEBHOOK_SECRET` in env.example. Frontend: `test-viewer.html` apiUrl default for production so the widget works without passing `api_url`. Small, focused changes.
3. **Backend deploy** — Railway or Render. Env vars, deploy, `/health` works. Optional: custom domain for API.
4. **Frontend deploy** — Vercel. Env vars, deploy, attach domain. Test `/` and `/test-viewer.html`.
5. **RunPod** — Already running. Confirm endpoint + API key in backend env.
6. **Widget URL + CORS** — Test production widget URL; confirm CORS allows frontend origin.
7. **Shopify app (pilot)** — Create Partner app (custom/private), add theme app extension (button + cart script), wire widget URL, install on dev store, test Try On → add to cart.

Pilot launch = steps 1–7 done. **Shopify App Store listing** comes later, after the pilot is going well.

---

## What we already have

- RunPod avatar pipeline running  
- Frontend and backend code in place; Supabase linked with APIs and webhooks  
- Widget (test-viewer, cart snippet), analytics, events, brand dashboard, user dashboard  
- Launch plan with order, code checklist, time estimate, and App Store (Shopify) section  

Loose ends: domain, the small Part B code changes, deploy backend + frontend, then Shopify app (extension + install). That’s it.

---

## Tomorrow evening (when you continue)

1. **Domain** — If you have it: document it (e.g. in the plan or here). No “Shopify”/“Example”.
2. **Start at the top of the plan** — Part B code changes first (backend CORS + PORT, frontend test-viewer apiUrl), then Part C Step 2 (Supabase verify), Step 3 (backend deploy), Step 4 (frontend deploy). One step at a time.
3. **Key file** — Keep `docs/SHOPIFY_APP_STORE_WIDGET_PLAN.md` open. It’s the checklist. When that plan is done, we’re shipped.

---

## Key file

| What | Where |
|------|--------|
| **Launch plan (priority #1)** | `docs/SHOPIFY_APP_STORE_WIDGET_PLAN.md` |

---

## Summary

**Today:** We made the launch plan the main priority. Everything we need to ship is in that doc: order, code changes, infra, time (~18–24 hrs to pilot). Domain tomorrow; then we execute. No new scope — tie loose ends and go live.

**Tomorrow:** Get domain, start executing the plan (Part B → deploy backend → deploy frontend → RunPod verify → widget/CORS → Shopify pilot). When the plan is done, it’s shipped.

Let’s go.

---

*Last updated: February 9, 2026.*
