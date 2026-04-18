# Ramin launch: second Shopify app (RDD) + custom distribution

**Status:** Primary plan for **tomorrow evening** (replaces Liquid-only integration).

**Why this path:** The **public Tryon** app is **in App Store review**, so Shopify **blocks install** on **raminstudios** until approved. **Custom distribution** on that same app is tied to **another** Plus org (`tryon-9621`), not Ramin. **Manual OAuth** hits the same review gate.

**Plan:** Create a **new** app under **RDD** in Shopify Partners, choose **Custom distribution** from the start, point it at the **same** backend and theme extension code, **generate an install link** for **`raminstudios.myshopify.com`**, install on Ramin, then add the **Try On** block + **cart embed** in the theme (normal app flow, no raw Liquid copy-paste).

---

## Before you start (decisions)

1. **App name:** e.g. **Tryon Pilot** or **Tryon (Ramin)** so it is clear this is **private / pilot**, not the public listing.
2. **Do not** submit this app to the **App Store** until you are ready; keep it **custom-only** so installs are not blocked by listing review.
3. **Shopify policy:** This should be a **legitimate pilot** for a real merchant, not a throwaway duplicate whose only purpose is to evade review forever. Long term, **merge** to one public app after approval or retire the pilot app.

---

## Step 1 — Create the new app (RDD)

1. **partners.shopify.com** → **Apps** → **Create app** (manual is fine).
2. When Shopify asks for **distribution method**, choose **Custom distribution** (not Public). If you already picked wrong, you may need a **new** app; distribution mode is hard to change later.
3. Note the new **Client ID** and **Client secret** (Instellingen / API credentials).

---

## Step 2 — Align app URLs, scopes, webhooks with production Tryon

In **Dev Dashboard** for the **new** app, match the **active** Tryon version as closely as possible:

- **App URL:** `https://tryon.global/app` (or whatever you use today).
- **Redirect URLs:** include  
  `https://heroic-celebration-production-9f72.up.railway.app/api/shopify/auth/callback`  
  (and any other callbacks you rely on).
- **Scopes:** same as **tryon-6** (add more if the public app has more than `read_orders` in a newer version).
- **Webhooks / compliance URLs:** same Railway base as today.

---

## Step 3 — Link this repo to the new app and deploy the extension

1. **Option A (clean):** Copy `shopify_app/` to a small folder or new branch, run `shopify app config link` and select the **new** app, then `shopify app deploy` (or your `deploy.sh`) so the **theme app extension** is attached to the **new** `client_id`.
2. **Option B:** Temporarily change `shopify.app.toml` **client_id** to the new app, deploy, then revert if you still deploy the public app from the same folder (be careful not to mix up which app you deploy).

After deploy, confirm **Thema-extensies** shows **tryon-widget** (or your handle) on the **new** app version.

---

## Step 4 — Backend: second OAuth client (important)

The new app has a **different** `client_id` and **client_secret**. Your Railway (or other) backend must:

- Accept OAuth **callback** for this app (same path is OK if Shopify allows one redirect URL for both apps, or add a second callback route if needed).
- Store **sessions** keyed by **shop** (and optionally by **client_id**) so **both** apps can coexist without clobbering tokens.

**Concrete work:** add env vars e.g. `SHOPIFY_CLIENT_ID_PILOT`, `SHOPIFY_CLIENT_SECRET_PILOT` (names up to you) and teach `shopify.py` / auth flow to pick credentials by **shop** or by **OAuth state**. If you only ever install the **pilot** app on **raminstudios**, a simple branch on `shop == raminstudios.myshopify.com` is enough for v1.

---

## Step 5 — Custom distribution → install link for Ramin

1. **Partners** → **new app** → **Distributie** → **Aangepaste distributie / Custom distribution**.
2. Enter store: **`raminstudios.myshopify.com`** (or the exact `.myshopify.com` from **Instellingen → Domeinen**).
3. **Generate install link** → **Copy**.
4. Open the link while logged in as someone who can **install apps** on **Ramin** → **Install** → approve scopes.

---

## Step 6 — Theme (same as normal app install)

1. **Online Store → Themes → Customize** → product template.
2. **Add block** → **Apps** → **Try On** → **Save**.
3. **Theme settings → App embeds** → enable **TryOn cart** → **Save**.

---

## Step 7 — Smoke test

- PDP **Try On** opens, widget loads from **tryon.global**.
- **Add to cart** from widget; cart line includes **`tryon_session_id`** where applicable.
- **Webhooks** fire for **raminstudios** (orders, uninstall) using the **pilot** app token.

---

## Fallback if anything blocks

- If Shopify still blocks custom install, fall back to **Liquid integration** (keep a copy of the old steps in git history from commit before this doc replaced `LIQUID_INTEGRATION_RAMIN_PLAN.md`, or ask to restore that file).

---

## Deprecated for this launch

- ~~**Liquid-only** theme paste~~ (not tomorrow’s primary path).
- ~~**Manual OAuth URL** on production Tryon client~~ (blocked while **in review**).

See also **`2026-04-07_SHOPIFY_RAMIN_MANUAL_INSTALL.md`** (manual URL kept for reference; superseded as primary plan).

---

*Updated 2026-04-08: primary Ramin launch path = second app + custom distribution.*
