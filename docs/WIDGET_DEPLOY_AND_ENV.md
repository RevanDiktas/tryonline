# Widget deploy verification and env vars

## Why the grey square and wrong avatar/tshirt?

1. **Grey square when signing in (picture 2)**  
   The grey was the **Shopify host page** overlay (`.tryon-modal { background: rgba(0,0,0,0.5) }`), not the iframe. The extension was updated so this overlay is `transparent`; the PDP should show through.

2. **Grey + wrong t-shirt/avatar (picture 3)**  
   The widget only uses avatar and garment from the API (Supabase). If you still see the NPC t-shirt or a wrong avatar, either:
   - The **deployed** `test-viewer.html` was an older build (cache or wrong deploy).
   - **API/env**: backend URL or Supabase isn’t set correctly, so the widget gets 404 and you might be seeing cached or old behavior.

## Vercel env vars (required for widget)

In **Vercel → Project → Settings → Environment Variables** set:

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | **Yes** (production) | Backend base URL (e.g. `https://your-app.railway.app`). Used by Next.js rewrites so `/api/*` is proxied to the backend. If missing, requests go to `127.0.0.1:8000` and fail. |
| `NEXT_PUBLIC_SUPABASE_URL` | **Yes** | Supabase project URL (e.g. `https://xxxx.supabase.co`). |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | **Yes** | Supabase anon/public key. |

After changing env vars, **redeploy** (Deployments → ⋯ → Redeploy).

## Deploy and verify

### 1. Push and deploy

```bash
cd /Volumes/Expansion/mvp_pipeline
git add -A
git status   # confirm: test-viewer.html, tryon-button.liquid, vercel.json, etc.
git commit -m "fix: Shopify modal transparent, widget v3 Supabase-only, open-direct in iframe"
git push origin main
```

Wait for Vercel to finish (Deployments → Ready).

### 2. Confirm widget version (no cache)

Open (use the same URL your store uses, with `open=1`):

```
https://tryonline.vercel.app/test-viewer.html?open=1&v=3
```

- **View Page Source** (right‑click → View Page Source).
- Search for: `tryon-widget v3`.
- If you see it, the new HTML is live. If not, wait a few minutes and hard refresh, or redeploy without cache.

### 3. Re-deploy Shopify extension

So the store uses the new modal (transparent overlay) and `v=3` iframe URL:

```bash
cd /Volumes/Expansion/mvp_pipeline/shopify_app
./deploy.sh
```

Then in Shopify admin, **save/publish the theme** so the updated block is active.

### 4. Test on the store

- Hard refresh or use an **incognito** window.
- Open a product page, click **Try On**.
- **Sign-in screen:** The area behind the small “Sign in” popup should show the PDP (no grey overlay). If it’s still grey, the theme may be cached; try another device or clear cache.
- **After sign-in:** You should see either:
  - Your avatar + the garment from Supabase for that product, or
  - “Avatar not ready” / “Product try-on not available” if the API returns nothing.

### 5. If avatar/garment are still wrong

- **Check env:** Vercel → Settings → Environment Variables. Ensure `NEXT_PUBLIC_API_URL` is the backend URL (e.g. Railway).
- **Check backend:**  
  - Garment: backend must have a row in `garments` with `shopify_product_id` = the product’s ID (from the store URL or Liquid).  
  - Avatar: backend `/api/avatar/:userId` must return `avatar_url` (and measurements) from your pipeline/Supabase.
- **Browser console:** On the product page, open DevTools → Console. Look for `[TryOn]` logs and any failed `fetch` to `/api/avatar/...` or `/api/products/.../tryon-config`. 404 or CORS errors point to env or backend.

## Summary of code changes (this pass)

- **Shopify `tryon-button.liquid`:** `.tryon-modal` background set to `transparent`; iframe URL uses `&v=3`.
- **Widget `test-viewer.html`:** Version comment `tryon-widget v3`; `openDirect` true when in iframe even without `open=1`; default `productId`/`variantId` empty (no demo fallback); transparent styles apply when `open-direct` or in iframe.
- **Backend:** No demo NPC t-shirt; 404 when garment not in DB.
- **Vercel:** `Cache-Control: no-cache` for `/test-viewer.html` (in `vercel.json`).
