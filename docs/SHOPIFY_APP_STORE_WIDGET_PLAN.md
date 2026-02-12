# TryOn Launch Plan — From Zero to Shipped

**Purpose:** Single source of truth to **ship the product**. Covers: (1) infrastructure and launch order (domain, backend, frontend, RunPod, Shopify), (2) what runs where and whether frontend/backend can share a server, (3) every code change required before and for launch, (4) the Shopify App Store widget deployment (size limits, extension, submission). No code is written in this doc—only research and the plan.

**Status:** Plan only. Execute in order. Use the checklists and code-change list when implementing.

**"App Store" in this doc = Shopify App Store** (the place where Shopify merchants discover and install apps for their stores). We are **not** referring to the Apple App Store (iOS/phone apps).

---

# PART A — LAUNCH ORDER & INFRASTRUCTURE

## A.1 What runs where (no ambiguity)

| Component | Where it runs | Notes |
|-----------|----------------|--------|
| **Frontend (Next.js)** | Your own hosting (recommended: **Vercel**). Serves: dashboard, onboarding, `/embed`, `/test-viewer.html`, static assets. | Must be on a **stable public URL** with HTTPS. No "Shopify" or "Example" in domain (App Store rule). |
| **Backend (FastAPI)** | Your own hosting (recommended: **Railway** or **Render**). Serves: REST API (`/api/*`), webhooks, health. | Reads Supabase, calls RunPod, must be reachable by frontend and by Shopify (webhooks). |
| **Database + Storage** | **Supabase** (already in use). PostgreSQL + Storage buckets (photos, avatars, garments). | No change of host for launch. |
| **Avatar pipeline (GPU)** | **RunPod Serverless** (already in use). Runs 4D-Humans in a container; invoked by backend via RunPod API. | **RunPod is GPU-only.** Do not run the FastAPI backend on RunPod. Backend stays on Railway/Render. |
| **Shopify (merchant store)** | Only the **theme app extension**: a small "Try On" button block + a small cart-listener script. | The full GLB viewer and all our app logic load from **our domain** (iframe). |

So: **Frontend** and **Backend** are on **separate** services (Vercel + Railway/Render). **RunPod** is only for the avatar GPU job. **Same server for frontend + backend** is possible (one VPS with Docker Compose + reverse proxy) but adds ops; for speed and simplicity, **use Vercel + Railway/Render** as in the existing deployment guide.

## A.2 Launch order (do this sequence)

Order matters so each step has what it needs.

| Step | What | Why this order |
|------|------|----------------|
| **1** | **Domain** | You need a final hostname for frontend (and optionally backend) so TLS and CORS are correct from day one. No "Shopify"/"Example" in the name. |
| **2** | **Supabase** | Already have project? If not: create project, apply schema/migrations, create storage buckets, note URL + anon key + service role key + JWT secret. Backend and frontend both depend on it. |
| **3** | **Backend** | Deploy FastAPI to Railway or Render. Backend needs: Supabase env vars, RunPod env vars, and (for production) CORS and PORT from env. Frontend will call this API. |
| **4** | **Frontend** | Deploy Next.js to Vercel (or your chosen host). Set env: `NEXT_PUBLIC_API_URL` = backend URL, Supabase public URL + anon key. Attach custom domain. |
| **5** | **RunPod** | Already have serverless endpoint for avatar pipeline? If not: build and push Docker image from `avatar-creation/`, create serverless endpoint, set env (e.g. Supabase, checkpoint URL). Backend already has RunPod API key + endpoint ID. |
| **6** | **Widget URL and CORS** | Confirm widget page is reachable at `https://<your-domain>/test-viewer.html` (and optionally `/embed`). Backend CORS must allow your frontend origin (and, if you use direct API from iframe, that origin). |
| **7** | **Shopify app (pilot)** | Create Shopify Partner app (custom/private first). Add theme app extension (button + cart script). Point widget URL to `https://<your-domain>/test-viewer.html?shop=...&product_id=...&variant_id=...`. Install on dev store or pilot brand. |
| **8** | **App Store (later)** | When pilot is going well: complete listing, compliance webhooks, icon, run automated checks, submit for review. |

So: **Domain → Supabase → Backend → Frontend → RunPod → Widget/CORS → Shopify pilot → App Store when ready.**

## A.3 Can frontend and backend be on the same server?

**Yes, but not recommended for first ship.**

- **Option A (recommended):** Frontend on **Vercel**, backend on **Railway** or **Render**. Zero server management, automatic HTTPS, and your repo already assumes this (see `docs/DEPLOYMENT_GUIDE.md`).
- **Option B:** One **VPS** (e.g. DigitalOcean, Hetzner) with Docker Compose: one container for Next.js (or Node serving Next build), one for FastAPI, plus Nginx (or Traefik) as reverse proxy and Let's Encrypt for TLS. More control, more ops (updates, monitoring, backups).
- **RunPod:** Use **only** for the GPU avatar pipeline. RunPod Serverless is for containerized GPU workloads, not for serving your main API. The FastAPI app stays on Railway/Render (or your VPS).

## A.4 RunPod: what it is and what it is not

- **What RunPod does:** Hosts your **avatar pipeline** (4D-Humans in a Docker image). Backend submits a job (photo URL, user id, etc.); RunPod runs the container, returns results; backend writes to Supabase. You pay per GPU-second.
- **What RunPod is not:** A place to run your FastAPI backend or Next.js frontend. The "server" in "our server" for the API and the widget is **Railway/Render** (backend) and **Vercel** (frontend).

## A.5 Are we listing on the Shopify App Store?

- **Pilot first:** We use a **custom/private Shopify app** and install it on a dev store or one pilot brand (manual/custom install). No listing on the Shopify App Store yet.
- **Later:** When pilot is going well, we **submit the app to the Shopify App Store** so any merchant can discover and install it. That’s when we do listing, compliance webhooks, icon, review, etc.
- So: we **are** planning to list on the **Shopify App Store** (not the Apple App Store); we do it **after** the pilot, not before first launch.

---

# PART A.6 — TIME ESTIMATE (HOURS)

Assumes: RunPod already running, frontend/backend/Supabase already built and linked, only a few small issues.

| Phase | Tasks | Hours |
|-------|--------|--------|
| **Code changes (Part B)** | CORS from env, PORT from env, env.example, test-viewer apiUrl default, Next env | 2–3 |
| **Domain** | Register or confirm; document | 0.5–1 |
| **Supabase** | Verify project, schema, buckets, keys | 0.5–1 |
| **Backend deploy** | Railway/Render: project, env, deploy, health check, optional custom domain | 2–3.5 |
| **Frontend deploy** | Vercel: env, deploy, custom domain, smoke test | 1.75–2.75 |
| **RunPod** | Confirm endpoint + API key in backend env | 0.25–0.5 |
| **Widget URL + CORS** | Test production widget URL and CORS | 0.5–0.75 |
| **Shopify app (pilot)** | Partner app, theme extension (block + embed), wire URL, build, install on dev store, test, fix 1–2 issues | 5.5–9 |
| **Buffer** | A few errors / platform quirks | 2–4 |
| **Total to pilot launch** | | **~18–24 hours** |

**Pilot launch** = domain + backend + frontend live, RunPod verified, widget on your domain, Shopify custom app with extension working on a dev store (try-on → add to cart).

**Shopify App Store listing** (after pilot): add ~4–8 hours for listing, icon, compliance, automated checks, submit; then 1–2 weeks for Shopify’s review.

Use the total (e.g. **~20 hours**) and your hours per day to set a launch date (e.g. 4 hrs/day → ~5–6 days to pilot).

---

# PART B — CODE CHANGES REQUIRED (CHECKLIST)

All of these are **required or strongly recommended** for a clean launch. Implement them; do not "just document."

### B.1 Backend

| # | Change | Where | Why |
|---|--------|--------|-----|
| B1.1 | **CORS from environment** | `backend/app/main.py` | Currently `allow_origins` is hardcoded (`localhost`, `*.vercel.app`, `tryon.com`). For production, backend must allow your **real** frontend origin (e.g. `https://app.yourdomain.com`). Add e.g. `CORS_ORIGINS` in config (and in `env.example`), parse as list, and use in `CORSMiddleware`. |
| B1.2 | **PORT from environment** | `backend/app/config.py` and `main.py` (or Dockerfile CMD) | Railway and Render set `PORT`. Add `port: int = 8000` to Settings (from env `PORT`). When running uvicorn programmatically, use `settings.port`. In Dockerfile/start command use `$PORT` so the same image works on Render/Railway. |
| B1.3 | **SHOPIFY_WEBHOOK_SECRET in env.example** | `backend/env.example` | Backend already has `shopify_webhook_secret` in config. Document it in `env.example` so production can verify `orders/paid` webhooks (HMAC). |
| B1.4 | **Health check without curl** | `backend/Dockerfile` | Dockerfile uses `curl` in HEALTHCHECK. Some base images don't have curl. Use `python -c` or add curl to the image so health check works on your host. |

### B.2 Frontend

| # | Change | Where | Why |
|---|--------|--------|-----|
| B2.1 | **Production API base for static widget** | `frontend/public/test-viewer.html` | Widget uses `config.apiUrl` (from query `api_url` or default `http://localhost:8000`). When the page is served from your production domain, API calls should go to the **same origin** (so Vercel rewrites `/api/*` to backend) or to your backend URL. Default: if `window.location.origin` is your production domain, set `apiUrl` to `''` (same-origin); else keep `http://localhost:8000` for local dev. So the extension does **not** need to pass `api_url`; production just works. |
| B2.2 | **Next.js env for production** | Vercel (or host) dashboard | Set `NEXT_PUBLIC_API_URL` to your backend URL (e.g. `https://api.yourdomain.com`). If you use same-origin and rewrites, you can leave it empty so the app uses relative `/api` (via rewrites). Ensure `next.config.js` rewrites point to that backend when `NEXT_PUBLIC_API_URL` is set. |
| B2.3 | **Images / domains** | `frontend/next.config.js` | If you serve images from Supabase or another host, add that host to `images.domains` (or the Next.js 14 `remotePatterns` if applicable) so `<Image>` works in production. |

### B.3 Shopify theme extension (when you build it)

| # | Change | Where | Why |
|---|--------|--------|-----|
| B3.1 | **Widget URL** | Extension Liquid (app block) | Build iframe (or link) URL: `https://<your-production-domain>/test-viewer.html?shop={{ shop.permanent_domain }}&product_id={{ product.id }}&variant_id={{ product.selected_or_first_available_variant.id }}`. No `api_url` param needed if B2.1 is done. |
| B3.2 | **Cart listener** | Extension assets | Copy `frontend/public/shopify-tryon-cart-snippet.js` into the extension's `assets/` (e.g. `tryon-cart.js`) and reference it from the app embed block. |

### B.4 Environment variables summary

**Backend (Railway/Render):** `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`, `RUNPOD_API_KEY`, `RUNPOD_ENDPOINT_ID`, `PHOTOS_BUCKET`, `AVATARS_BUCKET` (if different), `CORS_ORIGINS` (e.g. `https://app.yourdomain.com`), `SHOPIFY_WEBHOOK_SECRET`, `PORT` (set by host; optional in config with default 8000).

**Frontend (Vercel):** `NEXT_PUBLIC_API_URL` (backend URL, or empty if using same-origin rewrites), `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

**RunPod (endpoint env):** As per existing RunPod setup (e.g. Supabase, checkpoint URL).

---

# PART C — STEP-BY-STEP LAUNCH (SERVER BY SERVER)

**Step 1 — Domain:** Register a domain (e.g. yourdomain.com). Use subdomains if desired: `app.yourdomain.com` (frontend), `api.yourdomain.com` (backend). Ensure no "Shopify" or "Example" in the name. Attach to Vercel/Railway in later steps.

**Step 2 — Supabase:** Create or use existing project. Apply all migrations; create storage buckets (`photos`, `avatars`, `garments`) and policies. Note: Project URL, anon key, service_role key, JWT secret.

**Step 3 — Backend (Railway or Render):** Create project; connect repo; set build/start (Dockerfile or `pip install` + `uvicorn app.main:app --host 0.0.0.0 --port $PORT`). Set all backend env vars (Supabase, RunPod, CORS_ORIGINS, SHOPIFY_WEBHOOK_SECRET). Implement B1.1 and B1.2. Deploy; test `/health`. Optionally attach `api.yourdomain.com`.

**Step 4 — Frontend (Vercel):** Import repo; root `frontend/`. Set `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`. Deploy; test `/` and `/test-viewer.html`. Add custom domain (e.g. `app.yourdomain.com`); update DNS.

**Step 5 — RunPod:** Build and push avatar pipeline image; create or reuse Serverless Endpoint; set env. Put Endpoint ID and API key in backend env. Trigger test avatar job from backend.

**Step 6 — Widget URL and CORS:** Open `https://<your-frontend-domain>/test-viewer.html?shop=demo.myshopify.com&product_id=demo-npc-tshirt&variant_id=1`. Confirm page loads and try-on/events work. Implement B2.1. Confirm backend CORS allows frontend origin.

**Step 7 — Shopify app (pilot):** Create app in Partners (custom/private). Add theme app extension (button block + cart embed). Use B3.1 and B3.2. Configure OAuth and webhook URLs to backend. Install on dev store; add block; enable embed. Test: Try On → iframe → add to cart → checkout → webhook.

**Step 8 — App Store (when ready):** Complete listing (icon 1200×1200, description, screenshots, compliance webhooks, emergency contact). Run automated checks; submit; respond to reviewer.

---

# PART D — SHOPIFY APP STORE WIDGET (SIZE LIMITS & EXTENSION)

## 1. Size limits — what's true and why we're okay

### 1.1 What Shopify actually enforces

| Limit | Scope | Value | Enforced? | Source |
|-------|--------|--------|-----------|--------|
| **Liquid file size** | Per-file in theme app extension (markup + schema) | **100 KB** | Yes | Theme app extension configuration; build/deploy fails if exceeded |
| **JavaScript (extension assets)** | Per JS file in extension `assets/` (compressed/gzip) | **10 KB** | Theme Check **suggestion** (not yet hard block) | [AssetSizeJavascript](https://shopify.dev/docs/storefronts/themes/tools/theme-check/checks/asset-size-javascript); default `threshold_in_bytes: 10000` |
| **Locale file** | Per locale JSON | 15 KB | Yes | Changelog |
| **Extension bundle** | All assets in the extension | 10 MB | Yes | Community / docs |

So: **100 KB** applies to **Liquid**; **10 KB** applies to **each JavaScript file** that lives **inside** the theme app extension (and is measured compressed). Both are real constraints, but they apply only to what we ship **in the extension**, not to what we host ourselves.

### 1.2 Where our "widget" actually runs

Our try-on experience is **not** inside the Shopify theme. It runs on **our domain**:

- **Heavy experience:** `test-viewer.html` (~34 KB, 1095 lines), loads Three.js from unpkg, full 3D viewer, analytics, session, size algo. Served from **our** frontend (e.g. `https://yourapp.com/test-viewer.html` or `/embed`).
- **Cart listener on storefront:** `shopify-tryon-cart-snippet.js` (~1.6 KB). This is the only script we need **on the merchant's store** so that when the iframe sends `TRYON_ADD_TO_CART` via `postMessage`, the store adds the item with `tryon_session_id`.

So:

- **Theme app extension** = thin launcher: "Try On" button + (optionally) tiny script to open iframe + cart listener.
- **Our domain** = full widget (test-viewer / embed, Three.js, API calls). None of that is in the extension bundle, so **none of it counts toward the 10 KB or 100 KB limits**.

### 1.3 What we put in the extension (and why we're under the limits)

| Item | Where it lives | Size | Limit | OK? |
|------|----------------|------|--------|-----|
| **App block (product page)** | Liquid file: button + schema; optional small "open iframe" script | Liquid: &lt; 2 KB. If we use a separate JS asset: &lt; 1 KB (e.g. `openIframe(widgetUrl)`) | 100 KB Liquid, 10 KB JS | Yes |
| **App embed (cart listener)** | `assets/tryon-cart.js` (our existing cart snippet) | ~1.6 KB raw → well under 10 KB compressed | 10 KB JS | Yes |
| **Full try-on UI (Three.js, viewer, etc.)** | **Our** URL (iframe `src`) | 34 KB+ HTML, external Three.js | Not in extension | N/A |

Conclusion: **We do not have a size problem** for App Store, as long as we keep the extension to:

- One small Liquid block (button + optional inline or tiny asset script).
- One small JS asset for the cart listener.

The "100 KB" and "10 KB" rules apply to the **extension package only**. Our big widget stays on our servers and is loaded in an iframe; that's the intended hybrid pattern and matches our existing strategy doc.

---

## 2. Our code vs Shopify guidelines

### 2.1 What we have today (relevant to the extension)

| Asset | Path | Size (bytes) | Role |
|-------|------|--------------|------|
| Try-on viewer (full page) | `frontend/public/test-viewer.html` | ~34,199 | Full 3D try-on; **hosted on our domain**, loaded in iframe. Not in extension. |
| Embed (React) | `frontend/app/embed/page.tsx` | N/A (built) | Alternative embed; **our domain**. Not in extension. |
| Cart snippet | `frontend/public/shopify-tryon-cart-snippet.js` | ~1,678 | Listens for `TRYON_ADD_TO_CART`, calls `/cart/add.js` with `tryon_session_id`. This **is** what we ship in the extension (as app embed). |
| Demo embed viewer | `frontend/public/embed-viewer.html` | ~7,269 | Demo; not needed in extension. |

Widget URL params we already support (and the extension must pass through): `product_id`, `variant_id`, `shop`, `user_id`, `preferred_fit`, and optionally `country`. Our strategy doc already shows building the iframe URL like:

`https://yourapp.com/widget?shop={{ shop }}&product_id={{ product.id }}&variant_id={{ product.selected_or_first_available_variant.id }}`.

So the extension only needs to render a button and set that URL (or open it in an iframe); no need to duplicate any of the viewer logic.

### 2.2 Architecture alignment

- **Hybrid model:** We own platform, data, and full UI; Shopify is distribution + storefront surface. Our `SHOPIFY_DEPLOYMENT_STRATEGY.md` already describes this. App Store listing is just the public distribution of that same architecture.
- **Checkout:** We send users to **Shopify checkout** (Add to Cart → store's cart → Shopify checkout). No bypass of Shopify payments. Compliant.
- **Billing:** For paid plans we must use Shopify Billing API or Managed Pricing; no off-platform billing for App Store apps. To be implemented when we add paid tiers.
- **Session tokens / auth:** Embedded admin (if we use it) must use session tokens; storefront launcher is a button + iframe to our URL, so no third-party cookie dependency for the storefront piece.

### 2.3 App Store requirements (high level)

- **Policy:** Partner Program Agreement; no circumvention of platform; truthful listing; no "Shopify"/"Example" in app URLs or API contact email.
- **Functionality:** App does what the listing says; no critical/minor errors during review; uses Shopify APIs (we'll use Admin API for product/catalog and webhooks).
- **Security:** Valid TLS for our domain; only necessary OAuth scopes (e.g. `read_products`, `read_orders`, compliance webhooks).
- **Listing:** Icon 1200×1200; compliance webhooks subscribed; emergency contact; app listing in at least one language; no unsubstantiated claims.

We already have (or plan): our own backend, our own frontend, webhook for `orders/paid`, analytics, and event tracking. The main net-new work for App Store is: **Shopify app repo** (OAuth + theme app extension + optional admin UI) and **listing + compliance**.

---

## 3. Step-by-step deployment plan (Shopify / App Store)

### Phase 1: Prepare (no Shopify app repo yet)

1. **Confirm production base URL** — Decide the canonical base URL for the widget (e.g. `https://app.tryon.com` or `https://tryon.yourdomain.com`). Ensure no "Shopify" or "Example" in the domain, TLS valid, and `test-viewer.html` (and optionally `/embed`) reachable with query params: `shop`, `product_id`, `variant_id`, and optionally `user_id`, `preferred_fit`, `country`.
2. **Document widget URL contract** — One place that states base URL + path, required params (`shop`, `product_id`, `variant_id`), optional params. So the theme app extension and any manual installs use the same contract.
3. **Cart attribution** — Extension will ship the cart listener (app embed) so `TRYON_ADD_TO_CART` from the iframe adds the item with `tryon_session_id`. Our existing `shopify-tryon-cart-snippet.js` does this.

### Phase 2: Shopify app and theme app extension

4. **Create Shopify Partner app** — Partner account → Create app (custom/private for pilot; later for App Store). Configure OAuth (redirect URLs, scopes: at least `read_products`, `read_orders`). Compliance webhooks for App Store. App URLs and API contact email: no "Shopify"/"Example".
5. **Scaffold theme app extension** — App block (product page): one Liquid file with button + schema; optional tiny script to open iframe. App embed (body): one Liquid file loading `tryon-cart.js` (copy of `shopify-tryon-cart-snippet.js`). Do **not** put test-viewer or Three.js in the extension.
6. **Wire widget URL in Liquid** — In the app block, build URL: `https://<your-production-domain>/test-viewer.html?shop={{ shop.permanent_domain }}&product_id={{ product.id }}&variant_id={{ product.selected_or_first_available_variant.id }}`.
7. **Run Theme Check / build** — `shopify app build`; fix any errors. AssetSizeJavaScript is suggestion only; our cart JS is small.
8. **Test on development store** — Install app; add block to product section; enable embed. Click Try On → widget in iframe → try-on → add to cart; verify cart and (if possible) webhook attribution.

### Phase 3: App Store submission (when ready)

9. **Configuration and listing** — App icon 1200×1200; no "Shopify" in URLs or API contact email; emergency contact. One App Store listing (primary language); accurate description and screenshots; no unsubstantiated stats.
10. **Automated checks** — Run all on the App Store review page; fix failures.
11. **Submit for review** — Submit; respond promptly; fix "Paused" items and resubmit.
12. **Post-approval** — Monitor installs; document theme compatibility issues; consider "manual paste" fallback for stores that don't support app blocks.

---

## 4. Obstacles and how we handle them

- **4.1 "Our widget is too big for 10 KB"** — The 10 KB limit applies to JS **in the extension**. Our heavy widget stays on our domain; extension = launcher + cart script only.
- **4.2 "100 KB Liquid limit"** — Our app block is one small Liquid file. We're nowhere near 100 KB. If we add many blocks later, split and stay under 100 KB per file.
- **4.3 Iframe in app embed** — We use an app **block** (button + open iframe) and app **embed** (cart listener only). Iframe is opened by the block's small script, not embedded in the embed block. If issues arise, fallback: button opens our URL in new tab.
- **4.4 GraphQL Admin API** — New public apps must use GraphQL Admin API. When building the Shopify app (OAuth, product sync, webhooks), use GraphQL for all Shopify calls.
- **4.5 Session tokens** — If we offer embedded admin, use session tokens for auth; storefront launcher stays button + our URL.
- **4.6 Billing** — When we charge, use Shopify Billing API or Managed Pricing only.

---

## 5. Checklist before submission

- [ ] Production widget URL is stable and uses no "Shopify"/"Example" in domain.
- [ ] Theme app extension contains only: small Liquid block(s) and cart listener JS (&lt; 10 KB compressed).
- [ ] Full try-on experience (test-viewer / embed) is only on our domain, loaded via iframe or redirect.
- [ ] App block passes `shop`, `product_id`, `variant_id` (and optional params) to our URL.
- [ ] Cart listener (app embed) is enabled so `TRYON_ADD_TO_CART` adds item with `tryon_session_id`.
- [ ] OAuth and scopes are minimal and justified.
- [ ] Compliance webhooks subscribed; app icon 1200×1200; emergency contact set; listing complete and accurate.
- [ ] `shopify app build` and automated review checks pass.
- [ ] Tested on dev store: install → add block → enable embed → try-on → add to cart → (optional) checkout and webhook.

---

## 6. Summary

- **10 KB / 100 KB:** True for **extension** Liquid and JS only. Our **full widget is on our domain** and loaded in an iframe, so we don't hit those limits.
- **Our code:** We already have the widget URL contract, cart snippet, and backend; we only need a thin extension (button + cart listener) and a proper Shopify app (OAuth, webhooks, listing).
- **Plan:** Domain → Supabase → Backend → Frontend → RunPod → Widget/CORS → Shopify pilot → App Store when ready. Implement Part B code changes as you go.

---

## 7. References

- [Theme app extension configuration (file structure, schema, limits)](https://shopify.dev/docs/apps/build/online-store/theme-app-extensions/configuration)
- [Theme app extension build tutorial](https://shopify.dev/docs/apps/build/online-store/theme-app-extensions/build)
- [AssetSizeJavascript (10 KB threshold, theme app extensions)](https://shopify.dev/docs/storefronts/themes/tools/theme-check/checks/asset-size-javascript)
- [App Store requirements](https://shopify.dev/docs/apps/launch/shopify-app-store/app-store-requirements)
- [Submit app for review](https://shopify.dev/docs/apps/launch/app-store-review/submit-app-for-review)
- Internal: `docs/strategy/SHOPIFY_DEPLOYMENT_STRATEGY.md` (hybrid architecture, widget URL pattern)
- Internal: `docs/DEPLOYMENT_GUIDE.md` (Vercel, Railway/Render, RunPod, Supabase)
