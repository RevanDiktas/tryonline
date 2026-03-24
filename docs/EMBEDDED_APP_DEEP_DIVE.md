# Why the embedded app check (Controles ingesloten apps) might not pass — deep dive

## What Shopify actually checks (as of 2024–2025)

From the changelog and community posts, the **embedded app check** runs automatically (about every **2 hours**) and expects:

1. **Latest App Bridge script from Shopify’s CDN**  
   - Loaded as the **first** `<script>` in the document.  
   - **No `async`, `defer`, or `type="module"`** — otherwise App Bridge aborts and `window.shopify` / `getSessionToken` never appear.

2. **Session tokens for user authentication**  
   - The app must **use** session tokens (e.g. call `getSessionToken()` and/or use `fetch('shopify:admin/...')`, which is auto-authenticated when App Bridge is loaded correctly).

3. **Session data from a real visit**  
   - You must **log in and use the app on a development store** so there is session/usage data. The check is tied to the **exact app** you’re submitting (same `application_url` / same app in Partners).

So: **same app config as submission** + **real usage on a dev store** + **correct App Bridge loading** + **session token usage** are what the checker is looking for.

---

## What we did to satisfy the checker

- **App URL** in Partners and `shopify.app.toml`: `https://tryon.global/app`  
  So the **first** document Shopify loads is our minimal HTML, not the Next.js app.

- **`/app` route (minimal HTML)**  
  - One sync script: `https://cdn.shopify.com/shopifycloud/app-bridge.js` (no async/defer).  
  - Meta: `shopify-api-key` = your app’s client ID.  
  - Inline script: wait for `window.shopify.getSessionToken`, call it, call `fetch('shopify:admin/api/2024-01/shop.json')`, then redirect to `/?shop=...&host=...` in the **same** iframe (no nested iframe).

- **No App Bridge on the `/` page when embedded**  
  After redirect, the Next.js app runs in the same iframe. We **do not** inject App Bridge again there (that would load it with `async` and not first → App Bridge aborts and console errors). The checker only needs to see correct behavior on the **first** load (`/app`).

- **`[access.admin]` + `direct_api_mode = "online"`** in `shopify.app.toml`  
  So `fetch('shopify:admin/...')` from the embed is allowed and auto-authenticated.

So on paper we already:

- Use the **latest App Bridge from CDN** and only on the first document.
- Use **session tokens** (getSessionToken + shopify:admin fetch) on that first document.
- Avoid the “first script / no async” failure by not loading App Bridge again on `/`.

---

## What can still go wrong

### 1. Checker runs **after** redirect (unlikely but possible)

- If the checker follows the redirect to `/?shop=...`, it would see the **Next.js** document, where we intentionally do **not** load App Bridge (to avoid async/first-script errors).
- In that case the checker might not see `getSessionToken` or `shopify:admin` on the **current** document. We don’t know for sure if the checker only inspects the **initial** URL (`/app`) or also the post-redirect URL.

**Mitigation:** Keep `/app` as the **only** App URL. Don’t change the app URL to `https://tryon.global/` so the first request is always `/app`.

### 2. No recent session data

- The check runs every ~2 hours and expects **session data** from a real visit.
- If no one has opened the app in the dev store (or the store isn’t the one linked to the app you’re submitting), the check might stay pending or fail.

**What you should do:**  
Before and after each deploy:

- Open the **exact** app you’re submitting (same Partners app, same `application_url`).
- Log in to a **development store** that has this app installed.
- Open the app from the admin (so it loads `https://tryon.global/app?shop=...&host=...`).
- Use the app (e.g. click around, open ROI & Attribution, Garments, etc.) so there is clear usage.
- Wait for the next check window (up to ~2 hours). Optionally trigger a new deployment so the checker sees the latest code.

### 3. postMessage error (target origin tryon.global vs admin.shopify.com)

- The error says: **target origin provided (`https://tryon.global`) does not match the recipient window’s origin (`https://admin.shopify.com`)**.
- So some code is calling `postMessage(..., 'https://tryon.global')` toward a window that is actually `admin.shopify.com` (e.g. the parent frame). That is either:
  - **Shopify’s** script (e.g. `common-*.js` in the admin), or  
  - Some script in our app that posts to `window.top` / `window.parent` with the wrong `targetOrigin`.

We removed the **nested** iframe (app → iframe → Next app) so the only frame is **admin → tryon.global**. Our only `postMessage` is in `embed/page.tsx` and uses `'*'` as targetOrigin, so it’s not the source of this mismatch. The rest likely comes from **Shopify’s** embed/Admin code. We can’t fix that; it shouldn’t block the **embedded app** check as long as App Bridge and session token usage are correct on `/app`.

### 4. CSP blocking `eval`

- If your **site** (tryon.global) sends a strict `Content-Security-Policy` that blocks `eval` (e.g. no `unsafe-eval` in `script-src`), any script or dependency that uses `eval`/`new Function`/string `setTimeout` will be blocked.
- We don’t set CSP in the Next app; Vercel or another layer might. Easing CSP (e.g. adding `unsafe-eval`) is a **security trade-off** and not required for the embedded check. Only consider it if something critical (e.g. a library) clearly depends on it.

### 5. Backend session token verification (optional for the check)

- The **automated** embedded check is about the **frontend**: App Bridge loaded correctly + session token **usage** (getSessionToken and/or shopify:admin).
- For **production** security, your **backend** should verify the session token (JWT from Shopify) on requests from the embedded app. Right now we don’t; we use Supabase/other auth for API routes. Adding session token verification is recommended for production but is **not** what the “Controles ingesloten apps” check is testing.

---

## Checklist before “Ter controle indienen”

1. **Partners & TOML**  
   - App URL = `https://tryon.global/app`.  
   - Embedded = true.  
   - Same app as the one you’re submitting (e.g. tryon-6).

2. **Deploy**  
   - Latest code (with `/app` shell + no App Bridge injection on `/` when in iframe) is deployed to tryon.global.

3. **Generate session data**  
   - Install the app on a **development store** (or use the one you already have).  
   - Open the app from the admin (Apps → Tryon).  
   - Use the app (navigate, open tabs, etc.).  
   - Do this with the **same** app/URL that is in your submission (no ngrok vs prod mismatch).

4. **Wait for the check**  
   - The embedded check runs automatically about every 2 hours.  
   - After a recent deploy + a real visit to the app, wait for the next run and see if “Controles ingesloten apps” turns green.

5. **Console**  
   - When you open the app yourself, in the **first** document (before redirect) you should **not** see “App Bridge must be the first script” or “getSessionToken not found after 40 attempts”.  
   - After redirect, those messages are expected to be gone because we don’t load App Bridge on `/`.  
   - postMessage / CSP / chart warnings may remain; they’re not part of the embedded app check criteria above.

---

## If it still doesn’t pass

- Confirm in the **Network** tab that the **first** request is to `https://tryon.global/app?shop=...&host=...` and returns the minimal HTML with **one** script (App Bridge).  
- Confirm in the **Console** (context = the app iframe) that **before** redirect you don’t see App Bridge errors.  
- Try from another browser/incognito (no extensions) to rule out extensions breaking the embed.  
- In Partners, ensure you’re looking at the **same** app version that uses `https://tryon.global/app` and that the dev store is linked to that app.

---

## Summary

- **Why it might not have passed before:** App Bridge was loaded with `async` or not first (e.g. on the Next.js page), so it aborted and session token usage was never visible. We fixed that by serving **only** the minimal `/app` page with App Bridge as the first script, then redirecting to `/` without loading App Bridge again.  
- **What you need to do:** Use the **exact** app you’re submitting on a **dev store** (open and interact), deploy the current fix, and wait for the next automatic run (~2 hours). No extra “accept” or consent is required; the check is automatic once the app and session data are in place.
