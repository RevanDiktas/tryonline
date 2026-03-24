# Shopify app landing: brand-only in app, both on website

## Behavior

- **In the Shopify app** (merchant opens Tryon from Shopify Admin): show **only** “Launch Your Brand” (brand onboarding). No “Create Your Fit Passport” (shopper) option.
- **On the main website** (tryon.global): keep **both** “Create Your Fit Passport” and “Launch Your Brand”.

## How it’s implemented (this repo)

The app landing lives at **`frontend/app/app/page.tsx`** (route `/app`).

- **Shopify context:** When the URL has a `shop` query param (e.g. `?shop=store.myshopify.com`), the page treats the visitor as being in the Shopify app and shows only the “Launch Your Brand” card.
- **Website context:** When there is no `shop` param (e.g. someone visits `https://tryon.global/app` directly), both the shopper and brand options are shown.

After OAuth, the backend redirects to `/app?shop=...`, so merchants coming from Shopify always see the brand-only view.

## If tryon.global is a different codebase

If the live site at **tryon.global** is built from another repo, apply the same rule there on the equivalent of the `/app` landing:

- If the URL has a `shop` query parameter (or you detect the Shopify embedded app), render **only** the “Launch Your Brand” / brand onboarding.
- Otherwise, render **both** “Create Your Fit Passport” and “Launch Your Brand”.

Detection options in that codebase:

- Prefer: `new URLSearchParams(window.location.search).get('shop')` (or your framework’s search params).
- Alternative: check that the app is embedded in an iframe and the parent host is `admin.shopify.com` (then show brand-only).
