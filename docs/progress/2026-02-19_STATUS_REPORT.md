# Status Report — February 19, 2026

**Summary:** All three servers are running (Vercel, Railway, RunPod). Next: verify CORS, then Widget URL + CORS test, then Shopify app pilot.

---

## Current state — servers

| Component | Status | URL / note |
|-----------|--------|------------|
| **Frontend** | ✅ Live | https://tryonline.vercel.app |
| **Backend**  | ✅ Live | https://heroic-celebration-production-9f72.up.railway.app |
| **RunPod**   | ✅ Running | Endpoint + API key in backend env; avatar pipeline available |
| **Supabase** | ✅ In use | Env vars set in Vercel + Railway |

---

## What’s done

- **Category A (analytics):** Schema, events API, frontend event wiring, webhook, aggregation, metrics API, preferred fit, dashboard UI.
- **Category B (fit accuracy):** Fit metrics API, dashboard Fit Accuracy section, dynamic user/product data, avatar + garment loading.
- **Deploy:** Backend on Railway, frontend on Vercel, RunPod for avatar GPU.
- **Code (Part B):** CORS from env, PORT from env, env.example, test-viewer and Next.js env for production.
- **Widget one-click to viewer:** Store "Try On" now opens the GLB viewer directly (no intermediate fake PDP). Widget URL uses `open=1`; test-viewer.html hides the simulated PDP and auto-opens the overlay when loaded with `open=1`.

---

## What still needs to be done (in order)

### 1. CORS (if not already done)

- **Check:** From https://tryonline.vercel.app, sign in, onboarding, or any API call — if you see CORS errors in the browser console, do this:
- **Railway:** tryonline / heroic-celebration → **Variables** → set **CORS_ORIGINS** to include:
  - `https://tryonline.vercel.app`
  - Example: `http://localhost:3000,https://tryonline.vercel.app`
- **Redeploy** the backend after changing variables.

### 2. Widget URL + CORS test

- **Full experience (avatar + measurements):** Include `user_id` (and optionally `preferred_fit`) in the URL. Example:  
  `https://tryonline.vercel.app/test-viewer.html?user_id=YOUR_USER_ID&preferred_fit=regular&product_id=demo-npc-tshirt&shop=demo.myshopify.com&variant_id=1&open=1`  
  Without `user_id`, the viewer shows only the garment and measurements stay "—".
- **CORS-only:**  
  `https://tryonline.vercel.app/test-viewer.html?shop=demo.myshopify.com&product_id=demo-npc-tshirt&variant_id=1&open=1`
- Confirm: page loads; API calls work; no CORS errors; with user_id, avatar and measurements load.

### 3. Shopify app (pilot)

- Create **Shopify Partner app** (custom/private).
- Add **theme app extension:**
  - App block: “Try On” button that opens the widget.
  - App embed: cart listener (use `frontend/public/shopify-tryon-cart-snippet.js` in extension `assets/`).
- **Widget URL** in Liquid:
  - `https://tryonline.vercel.app/test-viewer.html?shop={{ shop.permanent_domain }}&product_id={{ product.id }}&variant_id={{ product.selected_or_first_available_variant.id }}`
- Install on a dev store; add the block; test: **Try On → iframe → add to cart → checkout**.
- Configure **orders/paid webhook** to your backend (e.g. `POST /api/webhooks/shopify/orders-paid`) and set **SHOPIFY_WEBHOOK_SECRET** in Railway.

When 1–3 are verified/done = **pilot is live**.

### 4. Domain (when ready)

- Register or attach custom domain in Vercel (and optionally for backend).
- Add that origin to **CORS_ORIGINS** in Railway.
- Update the widget URL in the Shopify extension to use the new domain.

### 5. App Store listing (later)

- After pilot is going well: listing, icon (1200×1200), compliance webhooks, submit for review.

---

## Why analytics_daily is empty

Events are stored in **analytics_events** (raw). **analytics_daily** is filled by a batch job, not in real time. To populate it:

- Run: `cd backend && python scripts/aggregate_analytics_daily.py 2026-02-23` (use the date you want). Requires `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in env.
- For production, run daily (e.g. cron at 1am). See `docs/IMPLEMENTATION_STEP_BY_STEP.md` and `backend/scripts/aggregate_analytics_daily.py`.

---

## Optional / future work (not blocking pilot)

- **Shopper login in widget:** Add a **login button** in the TryOn widget so shoppers can log in to TryOn from the store (for personalized avatar/size). Not in scope for first pilot; noted in `docs/BRAND_APP_ONBOARDING_PLAN.md` (gaps).
- **Brand leads:** Dedicated brand lead form and `brand_leads` table (see `docs/IMPLEMENTATION_PLAN_WHEN_BACK.md` §2). Not implemented yet.
- **Checkout profile API:** Expose default address for brand checkout (see `docs/NEXT_STEPS_PLAN.md` Option A).
- **Step 2 MORE DATA:** Enrich events with country, city, brand_id (see `docs/NEXT_STEPS_PLAN.md` Option B).
- **Regional size visualization:** Brand dashboard improvements (see `docs/NEXT_STEPS_PLAN.md` Option C).

---

## Key references

| What | Where |
|------|--------|
| Launch plan | `docs/SHOPIFY_APP_STORE_WIDGET_PLAN.md` |
| Launch without domain | `docs/LAUNCH_WHILE_DOMAIN_PENDING.md` |
| Implementation steps | `docs/IMPLEMENTATION_STEP_BY_STEP.md` |
| Next steps (post-pilot) | `docs/NEXT_STEPS_PLAN.md` |

---

*Last updated: February 19, 2026.*
