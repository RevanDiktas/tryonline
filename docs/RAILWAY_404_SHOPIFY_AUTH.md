# If /api/shopify/auth returns 404 on Railway

The backend **must** run from the **backend** folder so that `app.main` and the Shopify routes are loaded.

## 1. Set Root Directory

1. Railway → your **backend** service (e.g. heroic-celebration).
2. **Settings** → **Source** (or **Build**).
3. Set **Root Directory** to: **`backend`** (exactly).
4. Save.

## 2. Redeploy

Trigger a new deployment (e.g. **Deploy** → **Redeploy** or push a commit to the branch Railway watches).

## 3. Confirm routes

- **GET** `https://<your-railway-url>/routes`  
  Should include `"shopify_ok": true` and paths like `/api/shopify/auth`, `/api/shopify/auth/callback`.

- **GET** `https://<your-railway-url>/api/shopify`  
  Should return `200` and `{"status":"ok", ...}`.

If `/routes` shows `shopify_ok: false` or `/api/shopify` returns 404, Root Directory is still wrong or the deploy didn’t use the latest code.

## 4. If using Dockerfile

- **Build**: Dockerfile path = **`backend/Dockerfile`** (from repo root).
- **Root Directory** can be **`backend`** so the build context is the backend folder.
- Start is then from the Dockerfile CMD; no need to set a custom start command unless you override it.
