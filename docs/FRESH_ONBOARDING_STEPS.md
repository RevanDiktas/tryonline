# Fresh onboarding — from scratch

Use this when you want a clean install and one brand in `brands`.

---

## 1. (Optional) Clean Supabase

**brands** is usually empty. If you ever had a test row and want to remove it so the next install creates a fresh one, run in **Supabase → SQL Editor**:

```sql
-- Remove dev store brand so next install creates a new row (optional)
DELETE FROM public.brands WHERE shopify_domain = 'tryon-9621.myshopify.com';
```

Then run the query. If the table is already empty, this does nothing.

---

## 2. Uninstall the app from the store

- In the store Admin: **Settings** → **Apps and sales channels** (or **Apps**).
- Find **Tryon** → **Uninstall** / Remove.

---

## 3. Open the app again (embedded)

- In the store Admin go to **Apps** → **Tryon** (or use the custom install link from Partners → Distribution).

---

## 4. Complete install

- You should see: **“Complete install to connect your store. Click the button below…”** and a **“Complete install”** button.
- Click **“Complete install”**.
- The tab will go to our backend, then to Shopify’s install/approve screen. Click **Install** / **Approve**.
- You are redirected back to the app; you should see **“Welcome to Try On”** and the shop domain.

---

## 5. Check Supabase

- **Supabase** → **Table Editor** → **brands**.
- There should be one row: **shopify_domain** = `tryon-9621.myshopify.com`, **shopify_access_token** set.

---

## If the button doesn’t appear

- Deploy the latest frontend (with the “Complete install” button) to Vercel and hard-refresh the app tab (Ctrl+Shift+R / Cmd+Shift+R).
- Or use the **install link** from Partners → Distribution in a **new tab** (not from Apps → Tryon), approve the app there, and then open Apps → Tryon again.
