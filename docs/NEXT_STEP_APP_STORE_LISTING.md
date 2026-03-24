# Next step: Create the app listing (English)

You're on the right page. Here’s what to do next.

---

## 1. Click **"Aanmaken"** (Create)

Under **"Maak de content van de melding aan (Engels)"** (Create the content of the listing (English)), click the blue **Aanmaken** button.

- That opens the **listing form** (same page may expand, or you may get a new section/URL like `.../distribution/app-store` with a listing tab or form below).
- If nothing seems to change, scroll down on the same page or check the left sidebar for a **"Listing"** or **"App listing"** link under Distribution.
- Progress is **auto-saved** as you fill fields.

---

## 2. Fill the listing form (required)

Complete at least these so the step can be marked done and you can continue:

| Field | Requirement | Tryon example |
|-------|-------------|----------------|
| **App name** | Max 30 characters, unique, lead with brand | `Tryon` or `Tryon — Virtual Try-On` |
| **Tagline / Short description** | Max 62 chars (or 100 for “app introduction” depending on UI) | e.g. *Virtual try-on on product pages. Shoppers see their fit; you get fewer returns.* |
| **App icon** | 1200×1200 px, JPEG or PNG | Your Tryon logo, square, no “Shopify” |
| **App details / Long description** | Up to ~500 characters | What Tryon does, who it’s for, main benefit |
| **Feature list** | Short bullets, ~80 chars each | e.g. “Try on products in 3D on the product page”, “Size recommendation”, “Add to cart with fit” |
| **Screenshots** | 3–6 images, 1600×900 (16:9) | Product page with Try On, widget open, cart with item |
| **Privacy policy URL** | Required | `https://tryon.global/privacy` (or your real URL) |
| **Support / Contact email** | Where Shopify and merchants can reach you | Your support email |
| **Pricing** | Free or paid | e.g. “Free to install” if no charge yet |

Optional but useful: **Demo store URL** (link to a dev store where Tryon is installed and working), **Feature media** (short video or 1600×900 image).

---

## 3. “Controles ingesloten apps” (Embedded app checks)

- There are **no fields to fill** here.
- Checks run **automatically every 2 hours**.
- You need to **use the app in a dev store**: open your app from the Shopify admin (embedded app at tryon.global/app), click around, load the app. That generates session data so Shopify can verify:
  - Latest App Bridge from Shopify’s CDN
  - Session tokens for user verification

So: install Tryon on a dev store, open the app in the admin, use it for a few minutes. After the next 2-hour cycle, the checks may turn green.

---

## 4. After the listing is complete

- **“Maak de content van de melding aan (Engels)”** should show a green check when all required listing fields are saved.
- **“Ter controle indienen”** (Submit for review) usually stays disabled until the listing is complete; once the listing step is done, the button should become clickable (or you’ll get a clear message about what’s still missing).

---

## If “Aanmaken” doesn’t seem to do anything

- Try a **hard refresh** (Ctrl+F5 or Cmd+Shift+R) and click **Aanmaken** again.
- Try another browser or **incognito** in case of extensions blocking the form.
- Check the **URL** after clicking; you might be on something like `.../distribution/app-store` or `.../listings` with the form on that page.
- In the **left sidebar**, under your app (Tryon), see if there is a **“Listing”** or **“App listing”** or **“Content”** item and open it.

Once the listing form is open, fill the required fields above, save, and you should be able to continue and submit for review when embedded checks are green.
