# Embedded app — start now checklist

Use this to get the embedded app (Phase 1.1) running. Code is in place; you only need config and one migration.

---

## 1. Run the DB migration

Add the column for storing the Shopify access token:

- Open **Supabase** → SQL Editor.
- Run the contents of **`docs/supabase-migration-shopify-access-token.sql`**:

```sql
ALTER TABLE public.brands
  ADD COLUMN IF NOT EXISTS shopify_access_token TEXT;

COMMENT ON COLUMN public.brands.shopify_access_token IS 'Shopify Admin API access token (set on app install/OAuth).';
```

---

## 2. Backend environment variables

In your backend (e.g. Railway/Render), set:

| Variable | Where to get it | Example |
|----------|-----------------|--------|
| `SHOPIFY_CLIENT_ID` | Partners → Tryon app → Client credentials (API key) | `daf4359349b8033a4165df358aa6e05c` (from `shopify_app/shopify.app.toml`) |
| `SHOPIFY_CLIENT_SECRET` | Partners → Tryon app → Client credentials (Client secret) | *(copy from Partners)* |
| `FRONTEND_APP_URL` | Your Next.js app URL | `https://tryonline.vercel.app` |
| `BACKEND_PUBLIC_URL` | Your FastAPI public URL | `https://your-app.railway.app` or `https://your-app.onrender.com` |

- **BACKEND_PUBLIC_URL** must be the exact URL where the backend is reachable (HTTPS). It is used as the OAuth **redirect_uri** base so Shopify can send the user back to `/api/shopify/auth/callback` on your backend.

---

## 3. Shopify Partners — redirect URL

1. Go to **Shopify Partners** → **Apps** → **Tryon** → **App setup** (or **Configuration**).
2. Under **URLs** (or **Allowed redirection URL(s)**), add your **backend** OAuth callback URL:
   - `https://<BACKEND_PUBLIC_URL>/api/shopify/auth/callback`
   - Example: `https://your-app.railway.app/api/shopify/auth/callback`
3. Save.

Later, when you switch the embedded app to the new route, set **App URL** to:

- `https://tryonline.vercel.app/app`

(You can do that after the first test works.)

---

## 4. Frontend (optional for session check)

The `/app` page uses relative `/api/...` so Next.js rewrites to your backend. Ensure:

- **Vercel** (or your host) has **NEXT_PUBLIC_API_URL** set to your backend URL (e.g. `https://your-app.railway.app`) so the rewrites target the correct API.

---

## 5. Test the flow

1. **Backend**: Deploy with the new env vars; ensure `/api/shopify/session?shop=your-dev-store.myshopify.com` returns 401 (no session yet).
2. **Frontend**: Deploy so `https://tryonline.vercel.app/app` is live.
3. **Partners**: Set **App URL** to `https://tryonline.vercel.app/app` (so opening the app in Admin loads this page).
4. **Install** the app on a **development store** (Partners → Tryon → Test your app → Select store).
5. Open the app from the store’s Admin → **Apps** → **Tryon**.
   - You should see “Redirecting to install…” then Shopify’s grant screen, then “Welcome to Try On” after authorizing.
6. In **Supabase**, check that a row in **brands** exists for that store’s `shopify_domain` and that `shopify_access_token` is set.

---

## Summary of what’s in the repo

| Piece | Location |
|-------|----------|
| Backend OAuth (auth + callback + session) | `backend/app/api/routes/shopify.py` |
| Config (client id/secret, URLs) | `backend/app/config.py` |
| Brand upsert + session check | `backend/app/services/supabase.py` |
| Migration (add column) | `docs/supabase-migration-shopify-access-token.sql` |
| Embedded app page | `frontend/app/app/page.tsx` |

After this works, add the onboarding steps (deep links for “Add Try On button” and “Enable cart”) as in `docs/COMPLETE_STEPS_WALKTHROUGH.md` Phase 1.2–1.3.
