# TryOn Widget — Shopify App

This folder contains the **Shopify theme app extension** that lets merchants add the TryOn virtual try-on widget to their store. Shoppers see a **Try On** button on product pages; clicking it opens the TryOn experience in a modal. Add-to-cart from the widget is attributed via `tryon_session_id` for analytics.

## What’s included

| Item | Purpose |
|------|--------|
| **Try On block** | Product-page block: “Try On” button that opens the widget in a modal iframe |
| **TryOn cart embed** | App embed: listens for `TRYON_ADD_TO_CART` and adds the item to cart with `tryon_session_id` |
| **Widget URL** | `https://tryonline.vercel.app/test-viewer.html` (your deployed frontend) |

Merchants install the app, add the block to the product section, and enable the cart embed. No theme code editing required.

---

## Prerequisites

- [Shopify Partners account](https://partners.shopify.com)
- [Shopify CLI](https://shopify.dev/docs/apps/build/cli-for-apps) installed: `npm install -g @shopify/cli @shopify/theme`
- **Node.js 20.10 or newer** (CLI requires it; use `nvm use 20` or install from [nodejs.org](https://nodejs.org))

---

## 1. Create the app in Partners

1. Go to [partners.shopify.com](https://partners.shopify.com) → **Apps** → **Create app** → **Create app manually**.
2. Name it (e.g. **TryOn Widget**).
3. In **App setup** / **Client credentials**, copy the **Client ID**.
4. (Optional) Set **App URL** to `https://tryonline.vercel.app` if you want a redirect from the app listing.

---

## 2. Link this project to your app

From this repo (root or `shopify_app` folder, depending on where you run the CLI):

```bash
cd shopify_app
shopify app config link
```

When prompted, choose your Partner org and the app you created. This fills in `client_id` in `shopify.app.toml` (or you can paste the Client ID into `shopify.app.toml` manually).

---

## 3. Deploy the extension

**Recommended (especially if the project is on an external drive):**

```bash
cd shopify_app
bash deploy.sh
```

This copies the project to `/tmp` and runs `shopify app deploy` from there. On macOS, when the project lives on an external volume, the CLI’s bundle step can create `._*` (AppleDouble) files, which Shopify rejects; building the bundle on the main disk avoids that.

**Or deploy in place:**

```bash
cd shopify_app
shopify app deploy
```

This builds and deploys the theme app extension to your app. New installs of the app will get the extension.

---

## 4. Install the app on a store

- **Development store:** In Partners, open your app → **Test your app** → **Select store** (or create a dev store) → **Install app**.
- **Custom/private install:** Use the app’s install link from the Partners dashboard (e.g. **Install app** / **Get install link**).

After install, the merchant still has to add the block and enable the embed (below).

---

## 5. Add the widget on the store (merchant steps)

1. **Add the “Try On” block**
   - In the store admin: **Online Store** → **Themes** → **Customize**.
   - Open a **product** template (e.g. **Default product**).
   - In the main product section, click **Add block** → under **Apps**, choose **Try On** (or your app name).
   - Optionally change the button label in the block settings.
   - **Save**.

2. **Enable the TryOn cart embed**
   - In the same theme editor: **Theme settings** (left) → **App embeds**.
   - Find **TryOn cart** and turn it **on**.
   - **Save**.

Shoppers will see **Try On** on product pages; clicking it opens the TryOn widget. Adding to cart from the widget sends the item to the store cart with `tryon_session_id` for your backend/analytics.

---

## Widget URL and backend

- **Widget:** Served from `https://tryonline.vercel.app/test-viewer.html`. Query params are set by the block: `shop`, `product_id`, `variant_id`.
- **Backend:** Your existing backend (e.g. Railway) and CORS must allow requests from `https://tryonline.vercel.app`. Configure the **orders/paid** webhook to your backend and set `SHOPIFY_WEBHOOK_SECRET` for attribution.

---

## Troubleshooting

- **Validation errors about `._*.liquid`, `._*.json`, or "Invalid template encoding"**  
  The CLI is bundling macOS AppleDouble (`._*`) files. Always use **`npm run deploy`** (the script copies to `/tmp`, strips `._*`, and skips the cached bundle). If it still fails, clean source and re-run:
  ```bash
  find shopify_app -name '._*' -type f -delete
  cd shopify_app && npm run deploy
  ```

- **"Node version must be >= 20.10.0"**  
  Upgrade Node (e.g. `nvm install 20 && nvm use 20`, or install Node 20 LTS from [nodejs.org](https://nodejs.org)), then run deploy again.

---

## Project layout

```
shopify_app/
├── shopify.app.toml          # App config (client_id, name, etc.)
├── README.md                # This file
└── extensions/
    └── tryon-widget/
        ├── shopify.extension.toml
        ├── blocks/
        │   ├── tryon-button.liquid      # Product-page “Try On” block
        │   └── tryon-cart-embed.liquid # App embed for cart listener
        ├── assets/
        │   └── tryon-cart.js           # Cart add + session_id logic
        └── locales/
            └── en.default.schema.json
```

---

## Optional: Custom domain

When you use a custom domain for the frontend (e.g. `https://app.tryon.com`):

1. Change the widget base URL in `extensions/tryon-widget/blocks/tryon-button.liquid`: set `assign widget_base = 'https://app.tryon.com'` (or use a block setting so merchants can override).
2. Redeploy: `shopify app deploy`.
3. Ensure backend CORS includes that origin.

---

## Troubleshooting

- **Button doesn’t appear**  
  Ensure the block is added to a **product** section in a JSON template (e.g. Default product). Vintage themes or non-product templates won’t show it unless the theme supports app blocks there.

- **CORS errors in the widget**  
  Add `https://tryonline.vercel.app` (and your custom domain if used) to your backend `CORS_ORIGINS` (e.g. on Railway) and redeploy.

- **Add to cart doesn’t attach session**  
  Make sure the **TryOn cart** app embed is enabled under **Theme settings** → **App embeds**.

- **Extension not in theme editor**  
  Run `shopify app deploy` again and re-open the theme editor; ensure the app is installed on that store.
