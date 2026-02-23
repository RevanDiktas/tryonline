# Launch Steps You Can Do Without the Final Domain

**Use this while you and your co-founder decide on the domain.**  
You can run the full pilot on **default host URLs** (e.g. `yourapp.vercel.app`, `yourapp.up.railway.app`), then add the custom domain later.

---

## Do now (no domain needed)

### 1. Supabase — verify
- [ ] Project exists; apply all migrations and create buckets (`photos`, `avatars`, `garments`).
- [ ] Note: **Project URL**, **anon key**, **service_role key**, **JWT secret** (for backend + frontend env).

### 2. Backend deploy (Railway or Render)
- [ ] Create project; connect repo (e.g. `feature/analytics` or `main`); set root to `backend/` (or use Dockerfile).
- [ ] Set env vars:  
  `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`,  
  `RUNPOD_API_KEY`, `RUNPOD_ENDPOINT_ID`,  
  `CORS_ORIGINS` (see step 4 — use your **Vercel default URL**),  
  `SHOPIFY_WEBHOOK_SECRET` (optional for pilot),  
  `PHOTOS_BUCKET`, `AVATARS_BUCKET` if different.
- [ ] Deploy; confirm `/health` works.
- [ ] **Note the backend URL** (e.g. `https://yourapp.up.railway.app` or `https://yourapp.onrender.com`).

### 3. Frontend deploy (Vercel)
- [ ] Import repo; set root to `frontend/`.
- [ ] Set env:  
  `NEXT_PUBLIC_API_URL` = your **backend URL** from step 2,  
  `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- [ ] Deploy; test `/` and `/test-viewer.html`.
- [ ] **Note the frontend URL** (e.g. `https://tryon-frontend.vercel.app` or `https://yourapp.vercel.app`).

### 4. CORS — use the Vercel URL
- [ ] In **backend** env (Railway/Render), set:  
  `CORS_ORIGINS=https://your-actual-frontend.vercel.app`  
  (Use the exact URL from step 3; add a second origin if you use Vercel preview URLs, e.g. `https://*.vercel.app` if your stack supports it, or list the main one only.)
- [ ] Redeploy backend if you added CORS after first deploy.

### 5. RunPod — verify
- [ ] Endpoint is running; **RunPod API key** and **endpoint ID** are in backend env.
- [ ] Optional: trigger one test avatar job from the backend to confirm.

### 6. Widget URL + CORS test
- [ ] Open:  
  `https://<your-vercel-url>/test-viewer.html?shop=demo.myshopify.com&product_id=demo-npc-tshirt&variant_id=1`
- [ ] Confirm page loads and API calls work (e.g. session creation, events). If you see CORS errors, double-check `CORS_ORIGINS` in the backend.

### 7. Shopify app (pilot)
- [ ] Create **Shopify Partner app** (custom/private).
- [ ] Add **theme app extension**: app block (Try On button) + app embed (cart listener from `frontend/public/shopify-tryon-cart-snippet.js`).
- [ ] Widget URL in Liquid:  
  `https://<your-vercel-url>/test-viewer.html?shop={{ shop.permanent_domain }}&product_id={{ product.id }}&variant_id={{ product.selected_or_first_available_variant.id }}`
- [ ] Install on dev store; add block; test Try On → add to cart.

When this works, **pilot is live** — even without the final domain.

---

## When you have the domain

1. **Register** the domain and add it in **Vercel** (and optionally in Railway/Render for the API).
2. **Backend:** add the new frontend origin to `CORS_ORIGINS` (e.g. `https://app.yourdomain.com`).
3. **Frontend:** ensure `NEXT_PUBLIC_API_URL` still points at your backend (or use same-origin rewrites if you put API under the same domain).
4. **Shopify extension:** update the widget URL in Liquid to `https://<your-domain>/test-viewer.html?shop=...&product_id=...&variant_id=...`.
5. Rebuild/redeploy the theme extension and re-test.

**App Store listing** (later): use the final domain there; no “Shopify” or “Example” in the app’s URLs.

---

## Summary

| Step                    | Needs domain? | Do now? |
|-------------------------|---------------|--------|
| Supabase verify         | No            | Yes    |
| Backend deploy           | No (use default URL) | Yes |
| Frontend deploy         | No (use default URL) | Yes |
| CORS (use Vercel URL)   | No            | Yes    |
| RunPod verify           | No            | Yes    |
| Widget + CORS test      | No (use Vercel URL)  | Yes |
| Shopify pilot           | No (use Vercel URL)  | Yes |
| Custom domain on Vercel | Yes           | After you have the domain |
| App Store listing       | Yes (final URL)      | After pilot |
