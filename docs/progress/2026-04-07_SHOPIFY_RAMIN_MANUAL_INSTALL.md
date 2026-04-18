# Ramin Studio: manual Shopify app install (cross-account)

**Update 2026-04-08:** Primary launch plan is now **second app under RDD + custom distribution** (install link for **raminstudios**). See **`RAMIN_SECOND_APP_CUSTOM_DISTRIBUTION.md`**. This file stays as reference for the **manual OAuth URL** shape if you need it later.

---

**Why (original):** Dev Dashboard **App installeren** only lists stores under **RDD handel** (`organization_id`). **Ramin** lives on another Shopify account, so it never appears there. Install by opening OAuth on **Ramin’s** `*.myshopify.com` domain.

**Blocked while public Tryon is in review:** Shopify shows **“Deze app wordt beoordeeld”** and disables install on **production** stores for that **client_id**. The URL below does not bypass that for the **submitted** app.

**When:** Use tomorrow (or any day) when ready. App version at time of writing: **tryon-6** (redirect + scopes below match that version).

---

## 1. Install URL (you only edit two parts)

Replace **`YOUR_SHOP`** and **`YOUR_CLIENT_ID`**. Nothing else unless you ship a **new app version** with different scopes or redirect URLs.

```
https://YOUR_SHOP.myshopify.com/admin/oauth/authorize?client_id=YOUR_CLIENT_ID&scope=read_orders&redirect_uri=https%3A%2F%2Fheroic-celebration-production-9f72.up.railway.app%2Fapi%2Fshopify%2Fauth%2Fcallback
```

| Placeholder | What to put |
|-------------|-------------|
| **YOUR_SHOP** | Ramin’s shop subdomain only (the part **before** `.myshopify.com`). |
| **YOUR_CLIENT_ID** | Tryon **API key** from Dev Dashboard **Instellingen** (Client ID). |

---

## 2. How to run it

1. Use a **private/incognito** window.
2. Log into Shopify as someone who can **install apps** on **Ramin** (owner or staff with app permissions).
3. Paste the full URL (with your two replacements) in the address bar and go.
4. Approve **Install** / scopes when Shopify prompts.
5. Backend must complete OAuth (same flow as on dev stores).

---

## 3. After install (theme)

In **Ramin** admin:

1. **Online Store → Themes → Customize** → product template.
2. **Add block** → **Apps** → **Try On** → **Save**.
3. **Theme settings → App embeds** → enable **TryOn cart** → **Save**.

---

## 4. If OAuth errors

- **`redirect_uri` mismatch:** `redirect_uri` must match **exactly** one of the URLs on **Versions → tryon-6 → Redirect URLs**. Current callback encoded in the link above:  
  `https://heroic-celebration-production-9f72.up.railway.app/api/shopify/auth/callback`
- **Scope mismatch:** Use whatever **Bereiken / Scopes** shows on the **active** version (currently `read_orders` in tryon-6). If you add scopes in a new version, update `scope=` in the URL (comma → `%2C` if needed).

---

## 5. Reference (no secrets)

- **App URL (embedded):** `https://tryon.global/app`
- **Theme extension handle:** `tryon-widget`
- **OAuth callback (primary):** Railway URL above (see Versions page)

---

*Saved 2026-04-07 so the manual install link and steps are easy to find tomorrow.*
