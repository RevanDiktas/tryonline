# Onboarding + garments: one concrete flow

**Purpose:** Single place that ties together: install → brand in DB → onboarding UI → how garments get on the store. No confusion about order or who does what.

---

## 1. End-to-end flow (what happens in order)

```
1. Brand installs Tryon
   → Custom install link (Partners → Distribution) or later App Store.
   → Shopify shows “Install / Approve” screen.

2. Brand approves
   → Shopify redirects the browser to our BACKEND callback URL (must be first in redirect_urls).
   → Backend receives code + shop, exchanges code for access_token, creates/updates row in `brands` (shopify_domain + shopify_access_token).
   → Backend redirects browser to frontend: https://tryonline.vercel.app/app?shop=xxx.

3. Brand sees onboarding (/app)
   → “Welcome to Try On” and shop name.
   → (Next) Steps: “Add Try On button” (deep link) → “Enable cart” (deep link) → Done + “We’ll set up your products” + dashboard link.

4. Garments (how they get on the store)
   → Widget works by product: GET /api/products/{product_id}/tryon-config looks up `garments` by shopify_product_id.
   → So: for each product that should have try-on, we need a row in `garments` with that product’s Shopify product ID.
   → brand_id on garments is optional but useful for “which brand owns this” and analytics.
   → Who adds garments: today you (or ops) add them after onboarding: create in CLO, then insert/update `garments` with shopify_product_id (and brand_id = the brand we created in step 2).
```

So: **install → OAuth callback → brand row → onboarding UI**. Garments are added separately (you link them to products by `shopify_product_id`; optionally set `brand_id` to the new brand).

---

## 2. Critical link: OAuth callback must hit the backend

- **Redirect URLs** in the app config must list the **backend callback first**:
  - 1st: `https://<backend-public-url>/api/shopify/auth/callback`
  - 2nd: `https://tryonline.vercel.app` (or frontend URL)
- If the frontend URL is first, Shopify may send the OAuth **code** to the frontend. The frontend does not exchange the code; only the backend does. So the code is lost and **no brand is created**.
- With the backend callback first, Shopify sends the code to the backend → we exchange it, create the brand, redirect to /app.

---

## 3. What each system does

| System | Responsibility |
|--------|----------------|
| **Shopify** | Install flow, OAuth, embedding our app URL in Admin. |
| **Backend (Railway)** | OAuth callback: exchange code → create/update `brands` with shop + token. Session check for /app. |
| **Frontend (Vercel)** | `/app` onboarding UI. Session check calls backend; if no session, redirect to backend auth. |
| **Supabase `brands`** | One row per store (shopify_domain, shopify_access_token). Created in OAuth callback. |
| **Supabase `garments`** | One row per product that has try-on (shopify_product_id; optional brand_id). You add these after a brand is created. |
| **Widget** | Loads try-on by product_id; backend returns garment by shopify_product_id. No direct “onboarding” step for garments. |

---

## 4. Checklist: “Brand created?” and “Garments linked?”

- **Brand created?**  
  Supabase → `brands` → row with `shopify_domain` = store (e.g. tryon-9621.myshopify.com) and `shopify_access_token` set.  
  If not: fix redirect URL order (backend callback first) and re-run install flow (reinstall or use install link again).

- **Garments linked?**  
  Supabase → `garments` → rows with `shopify_product_id` = the store’s product IDs; optionally `brand_id` = that brand’s id.  
  You add these manually (or via internal tool) after the brand exists.

---

## 5. One-paragraph summary

Brand installs → Shopify redirects to **backend** callback (backend URL must be first in redirect_urls) → backend creates `brands` row and redirects to /app → merchant sees onboarding. Garments are not created by the app; you add rows to `garments` with the right `shopify_product_id` (and optional `brand_id`) so the widget can load try-on for those products.
