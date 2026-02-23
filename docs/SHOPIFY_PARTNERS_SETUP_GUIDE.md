# Shopify Partners Setup — Step-by-Step

Use this guide while signing up and creating your TryOn Widget app. You’re already on the signup page and logged in.

---

## Step 1: Choose “Create a new partner organization”

On the screen that says **“Hoe wil je aan de slag als partner?”** (How do you want to get started as partner?):

- Click: **“Een nieuwe partnerorganisatie maken en instellen”** (Create and set up a new partner organization).

You need your own organization to create and distribute your app.  
*(The other option is only if someone invited you to their existing org.)*

---

## Step 2: Fill in your partner organization details

Shopify will ask for:

- **Organization name** — e.g. your name, “TryOn”, or your company name.
- **Country/region** — where you’re based (for payouts and legal).
- Any other required fields (e.g. role, how you’ll use Shopify).

Complete the form and continue.

---

## Step 3: Confirm or create your Partners account

- If you’re already logged in (e.g. with Apple), you may just need to accept terms or confirm details.
- If asked to “Create account”, use the same email you’re logged in with (e.g. your Apple private relay email) or add a business email you prefer for Partners.

Finish until you land on the **Partners dashboard** (overview with Apps, Stores, etc.).

---

## Step 4: Create your app

1. In the left sidebar, click **Apps**.
2. Click **Create app** → **Create app manually** (we already have the code in `shopify_app/`).
3. **App name:** e.g. **TryOn Widget** or **TryOn - Virtual Fitting Room**.
4. Click **Create** (or **Create app**).

You’ll be taken to the app’s overview/settings.

---

## Step 5: Get your Client ID

1. In the app, go to **Configuration** or **App setup** (or **Client credentials** in the left menu).
2. Find **Client ID** (sometimes called “API key” or “Client ID”).
3. **Copy the Client ID** — you’ll use it in the next step.

Keep this tab open; we’ll link it to the repo.

---

## Step 5b: Create version — Scopes & redirect URLs

When you create or edit a version (e.g. **Versies** → **Een versie aanmaken**), scroll down and set:

| Section | What to do |
|--------|-------------|
| **Webhooks API-versie** | Leave default (e.g. 2026-01). |
| **Bereiken** (Required scopes) | Add: `read_orders` (needed for the orders/paid webhook so your backend can get order attribution). Click "Bereiken selecteren" and add `read_orders`, or type it in the comma-separated list. |
| **Optionele bereiken** | Leave empty. |
| **Verouderde installatie-flow gebruiken** | Leave **unchecked**. |
| **Omleidings-URL's** (Redirect URLs) | Add: `https://tryonline.vercel.app` (where Shopify redirects after install; use your real App URL). |
| **POS** / **App-proxy** | Leave collapsed; no need to change. |

Then click **Uitbrengen** (Release) to save the version.

---

## Step 6: Link the repo to your app (on your machine)

1. Open a terminal and go to the project:
   ```bash
   cd /Volumes/Expansion/mvp_pipeline/shopify_app
   ```
2. If you have [Shopify CLI](https://shopify.dev/docs/apps/build/cli-for-apps) installed:
   ```bash
   shopify app config link
   ```
   - When prompted, choose your **Partner organization** and the **TryOn Widget** app you just created.  
   - The CLI will write the Client ID into `shopify.app.toml` for you.

   **If you don’t have the CLI yet:**  
   - Open `shopify_app/shopify.app.toml` in the repo.  
   - Set `client_id = "YOUR_CLIENT_ID_HERE"` (paste the value from Step 5).  
   - Save the file.

---

## Step 7: Deploy the theme extension

From the same folder:

```bash
cd /Volumes/Expansion/mvp_pipeline/shopify_app
shopify app deploy
```

*(Install Shopify CLI first if needed: `npm install -g @shopify/cli @shopify/theme`.)*

After a successful deploy, your app will have the **Try On** block and **TryOn cart** embed. New installs get the extension automatically.

---

## Step 8: Create a development store (to test)

1. In Partners dashboard, go to **Stores** → **Add store** → **Development store**.
2. Fill in store name, password, and purpose (e.g. “Test apps”).
3. Create the store.
4. In your app’s page in Partners, use **Test your app** (or the install link) and choose this development store to install the app.

---

## Step 9: Add the widget on the dev store

1. In the **development store admin**: Online Store → Themes → **Customize**.
2. Open a **product** page (e.g. use the template dropdown and pick “Default product”).
3. In the main product section, click **Add block** → under **Apps**, select **Try On** (or your app name).
4. Save.
5. Go to **Theme settings** (gear icon) → **App embeds** → turn **TryOn cart** **On** → Save.

Visit a product on the storefront; you should see the **Try On** button and the widget opening from tryonline.vercel.app.

---

## Quick reference

| Step | Where | Action |
|------|--------|--------|
| 1 | Signup page | Click “Create and set up a new partner organization” |
| 2 | Form | Enter org name, country, etc. |
| 3 | Account | Confirm/complete account |
| 4 | Partners → Apps | Create app → Create app manually → name it |
| 5 | App → Configuration | Copy Client ID |
| 6 | Your repo | `shopify app config link` or paste Client ID in `shopify.app.toml` |
| 7 | Terminal | `shopify app deploy` |
| 8 | Partners → Stores | Add development store |
| 9 | Dev store theme | Add Try On block + enable TryOn cart embed |

---

## If the UI is in Dutch

You can switch to English:

- Look for a language/region selector (often bottom of the page or in account settings).
- Or change the URL: replace `?locale=nl` with `?locale=en` (e.g. `partners.shopify.com/signup?locale=en`).

---

*Last updated: February 2026*
