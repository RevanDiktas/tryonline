# Get the pilot done today — step-by-step

Do these in order. Check off each box as you go.

---

## Part A: CORS (≈10 min)

### Step 1 — Check if CORS is already OK

1. Open: **https://tryonline.vercel.app**
2. Open DevTools: **Right‑click → Inspect → Console** (or F12 / Cmd+Option+I).
3. Sign in (or try onboarding / any action that calls the backend).
4. Look for **red CORS errors** in the console (e.g. "blocked by CORS policy", "No 'Access-Control-Allow-Origin'").

- [ ] **No CORS errors** → Skip to **Part B**.
- [ ] **You see CORS errors** → Do Step 2.

### Step 2 — Fix CORS in Railway

1. Go to **https://railway.app** and log in.
2. Open your project → select the **heroic-celebration** (backend) service.
3. Click **Variables** (or **Settings → Variables**).
4. Find **CORS_ORIGINS**:
   - If it doesn’t exist: **New variable** → Name: `CORS_ORIGINS`, Value: `http://localhost:3000,https://tryonline.vercel.app`
   - If it exists: Edit the value and make sure it includes `https://tryonline.vercel.app` (comma‑separated, no spaces after commas if possible). Example: `http://localhost:3000,https://tryonline.vercel.app`
5. Save. Railway will redeploy the backend (or click **Redeploy** if it doesn’t).
6. Wait 1–2 minutes, then test again at https://tryonline.vercel.app — CORS errors should be gone.

- [ ] CORS_ORIGINS set and backend redeployed.
- [ ] Retested; no CORS errors.

**What this tells us:** The app and widget on tryonline.vercel.app call the backend via **Next.js rewrites** (same origin), so the browser may never hit Railway directly. No CORS errors = either CORS is set correctly on Railway, or all requests go through Vercel (both are fine). You’re good to move on; the **widget test** (Part B) is the real “full stack works” check.

---

## Part B: Widget URL test (≈5 min)

### Step 3 — Test the widget page and API

**Two kinds of URLs:**

- **Garment only (no avatar, no measurements):**  
  `?shop=...&product_id=...&variant_id=...&open=1`  
  Use for anonymous store visitors or quick CORS check.
- **Full experience (avatar + measurements):**  
  Add `user_id=<your-fit-passport-uuid>` and optionally `preferred_fit=regular`.  
  The viewer then loads the user’s avatar and measurements from the API.

**Recommended test URL (full experience — replace with your user ID):**

```
https://tryonline.vercel.app/test-viewer.html?user_id=YOUR_USER_ID&preferred_fit=regular&product_id=demo-npc-tshirt&shop=demo.myshopify.com&variant_id=1&open=1
```

To get your `user_id`: sign in at https://tryonline.vercel.app, then use the user ID from the Fit Passport / Supabase `users` or `fit_passports` table (e.g. the `id` of the user or the user_id linked to the passport).

**Quick CORS-only test (no user):**

```
https://tryonline.vercel.app/test-viewer.html?shop=demo.myshopify.com&product_id=demo-npc-tshirt&variant_id=1&open=1
```

1. Open one of the URLs above (with `user_id` for avatar + measurements).
2. You should see the TryOn viewer; with `open=1` the overlay may open automatically. With `user_id`, measurements and avatar should load.
3. Open **DevTools → Console**. There should be **no CORS errors**.
4. (Optional) Open **DevTools → Network**. Filter by "Fetch/XHR". Use the widget a bit; you should see requests to your backend (e.g. session, events).

- [ ] Page loads.
- [ ] No CORS errors in console.
- [ ] With user_id: avatar and measurements appear; API calls work.

---

## Part C: Shopify app — deploy & dev store (≈30–45 min)

### Step 4 — Confirm app is linked (repo already has client_id)

Your repo has `shopify_app/shopify.app.toml` with a `client_id`. That means the app is likely already created and linked.

- If you **haven’t** created a TryOn app in Partners yet:
  1. Go to **https://partners.shopify.com** → **Apps** → **Create app** → **Create app manually**.
  2. Name it (e.g. **TryOn**).
  3. In the app: **Configuration** (or **App setup**) → copy **Client ID**.
  4. In the repo, edit `shopify_app/shopify.app.toml`: set `client_id = "YOUR_CLIENT_ID"` (paste the value). Save.
- If the app **is** already created and `shopify.app.toml` has the right client_id: do nothing.

- [ ] App exists in Partners and `shopify.app.toml` has the correct `client_id`.

### Step 5 — Install Shopify CLI (if needed)

In a terminal:

```bash
npm install -g @shopify/cli @shopify/theme
```

Then log in (if prompted):

```bash
cd /Volumes/Expansion/mvp_pipeline/shopify_app
shopify auth login --store YOUR_DEV_STORE.myshopify.com
```

(Use a development store you created in Partners, or create one: Partners → **Stores** → **Add store** → **Development store**.)

- [ ] Shopify CLI installed.
- [ ] Logged in (or will log in when deploy prompts).

### Step 6 — Deploy the theme extension

From the project (use the deploy script so the bundle is built on main disk and avoids ._* issues on external volumes):

```bash
cd /Volumes/Expansion/mvp_pipeline/shopify_app
npm run deploy
```

Or, if you prefer the CLI directly (and you’re not on an external volume):

```bash
cd /Volumes/Expansion/mvp_pipeline/shopify_app
shopify app deploy
```

When prompted, choose your **Partner org** and **app** (TryOn). After success, the extension (Try On block + TryOn cart embed) is deployed.

- [ ] Deploy succeeded.

### Step 7 — Create a development store (if you don’t have one)

1. **Partners** → **Stores** → **Add store** → **Development store**.
2. Store name, password, purpose (e.g. “Test TryOn”). Create.
3. **Apps** → your TryOn app → **Test your app** (or install link) → choose this store → Install.

- [ ] Dev store created (or already existed).
- [ ] App installed on dev store.

### Step 8 — Add Try On block and cart embed on the store

1. In the **development store admin**: **Online Store** → **Themes** → **Customize**.
2. Open a **product** page (e.g. click a product or use the template dropdown → “Default product”).
3. In the product section, click **Add block** → under **Apps**, select **Try On**.
4. Save (top right).
5. **Theme settings** (gear icon) → **App embeds** → find **TryOn cart** → turn it **On** → Save.

- [ ] Try On block added to product page.
- [ ] TryOn cart embed enabled.

### Step 9 — Quick storefront test

1. Visit the storefront (View your store) and open a product that has the block.
2. Click **Try On**. The widget should open in a modal (iframe to tryonline.vercel.app).
3. If the widget has “Add to cart”, use it; confirm the item is in the store cart.

- [ ] Try On opens widget.
- [ ] Add to cart works (if available in widget).

---

## Part D: Orders/paid webhook (≈15 min)

### Step 10 — Create the webhook in Shopify

1. In the **development store admin**: **Settings** → **Notifications**.
2. Scroll to **Webhooks** → **Create webhook** (or **Add webhook**).
3. Set:
   - **Event:** Order payment paid (or **Orders** → **Order payment paid**).
   - **Format:** JSON.
   - **URL:**  
     `https://heroic-celebration-production-9f72.up.railway.app/api/webhooks/shopify/orders-paid`
4. Create. Shopify will show a **Signing secret** (or “Webhook signing secret”). **Copy it** — you need it in Step 11.

- [ ] Webhook created.
- [ ] Signing secret copied.

### Step 11 — Set SHOPIFY_WEBHOOK_SECRET in Railway

1. **Railway** → your project → **heroic-celebration** (backend) → **Variables**.
2. **New variable** (or edit existing):
   - Name: `SHOPIFY_WEBHOOK_SECRET`
   - Value: paste the **signing secret** from Step 10.
3. Save. Redeploy the backend if Railway didn’t auto‑redeploy.

- [ ] SHOPIFY_WEBHOOK_SECRET set.
- [ ] Backend redeployed.

### Step 12 — Verify webhook

1. In the dev store, place a **test order** (Try On → Add to cart → Checkout; use Shopify’s test payment if available).
2. In **Railway** → your backend → **Deployments** → open the latest deploy → **View logs** (or use **Logs** tab). Look for a POST to `/api/webhooks/shopify/orders-paid` and no 4xx/5xx.
3. Optionally run the backend’s webhook test script (if you have one):
   ```bash
   cd /Volumes/Expansion/mvp_pipeline/backend
   # If you have a script, e.g.:
   # python scripts/test_webhook_purchase.py
   ```

- [ ] Test order placed.
- [ ] Logs show webhook received (and no HMAC/auth errors).

---

## Done today checklist

| # | What | Done |
|---|------|------|
| 1 | CORS set in Railway + no errors on tryonline.vercel.app | ☐ |
| 2 | Widget test URL loads, no CORS, API works | ☐ |
| 3 | Shopify app linked (client_id in shopify.app.toml) | ☐ |
| 4 | Theme extension deployed (Try On + TryOn cart) | ☐ |
| 5 | App installed on dev store | ☐ |
| 6 | Try On block + TryOn cart embed added in theme | ☐ |
| 7 | Storefront: Try On → widget → add to cart works | ☐ |
| 8 | Webhook orders/paid created in Shopify | ☐ |
| 9 | SHOPIFY_WEBHOOK_SECRET set in Railway | ☐ |
| 10 | Test order placed; webhook received in logs | ☐ |

When all are checked, **pilot is live.**

---

## Quick reference

| What | URL / value |
|------|-------------|
| Frontend | https://tryonline.vercel.app |
| Backend | https://heroic-celebration-production-9f72.up.railway.app |
| Widget test | https://tryonline.vercel.app/test-viewer.html?shop=demo.myshopify.com&product_id=demo-npc-tshirt&variant_id=1&open=1 |
| Webhook URL | https://heroic-celebration-production-9f72.up.railway.app/api/webhooks/shopify/orders-paid |
| Railway | https://railway.app |
| Shopify Partners | https://partners.shopify.com |

---

## Why `analytics_daily` is empty (and how to fix it)

**Raw events** go into `analytics_events` (you see 90 records there). **Daily rollups** go into `analytics_daily`; that table is filled by a **batch job**, not in real time.

To populate `analytics_daily` from existing events (e.g. for today):

```bash
cd /Volumes/Expansion/mvp_pipeline/backend
# Use your backend .env (SUPABASE_URL, SUPABASE_SERVICE_KEY)
python scripts/aggregate_analytics_daily.py 2026-02-23
```

Replace `2026-02-23` with the date you want to aggregate. With no argument, the script runs for **yesterday**. For production, run it daily (e.g. cron at 1am: `0 1 * * * cd /path/to/backend && python scripts/aggregate_analytics_daily.py`).

After running for today’s date, refresh the `analytics_daily` table in Supabase; you should see rows for that date.

---

*Last updated: Feb 23, 2026*
