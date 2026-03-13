# Deploy with Shopify client secret (git + Shopify)

Use this when redeploying so the backend can verify webhooks (orders/paid + compliance) and Shopify has the right URLs.

---

## 1. Set the secret in `.env` (local)

In **`backend/.env`** add or set:

```env
# Shopify: app Client secret — for webhook HMAC (orders/paid + compliance).
# Get from: Partner Dashboard → Tryon (tryon-3) → API credentials → Client secret.
SHOPIFY_WEBHOOK_SECRET=paste_your_client_secret_here_without_quotes
```

- **No quotes** around the value.
- **One line**: paste the Client secret as-is (it’s a long string from the Partner Dashboard).
- Get the value: **Shopify Partners** → **Apps** → **Tryon** (tryon-3) → **API credentials** (or **Client credentials** / **App setup**) → copy **Client secret**.

---

## 2. Deploy backend (Railway)

1. **Set the same secret in Railway**
   - Railway project → your backend service → **Variables**.
   - Add or edit: `SHOPIFY_WEBHOOK_SECRET` = same Client secret value (no quotes).

2. **Deploy**
   - Push to the branch Railway watches, or run `railway up` from the `backend/` directory.
   - Backend URL example: `https://heroic-celebration-production-9f72.up.railway.app`.

---

## 3. Deploy / configure Shopify app (terminal + Partner Dashboard)

When you deploy the **Shopify app** from the terminal (e.g. `shopify app deploy`), the version that gets created is driven by your **app config** (e.g. `shopify.app.toml` in the app project). That config should have:

- **Redirect URLs** matching what’s in the Versions page (e.g. Railway callback + `https://tryon.global/app`).
- **Compliance webhook URI** pointing at your **backend**:
  - `https://YOUR_RAILWAY_URL/api/webhooks/shopify/compliance`  
  Example: `https://heroic-celebration-production-9f72.up.railway.app/api/webhooks/shopify/compliance`

If your app config lives in a **separate repo** (e.g. a clone or `shopify_app` elsewhere), ensure that repo’s `shopify.app.toml` (or equivalent) has:

```toml
[webhooks]
api_version = "2026-01"   # match the version in your Versions page

[[webhooks.subscriptions]]
compliance_topics = ["customers/data_request", "customers/redact", "shop/redact"]
uri = "https://heroic-celebration-production-9f72.up.railway.app/api/webhooks/shopify/compliance"
```

Then run your usual deploy (e.g. `shopify app deploy` from that app’s directory). If the compliance webhook URL is only configurable in the **Partner Dashboard**, set it there to the same URL after deploy.

---

## 4. Quick checklist

| Step | Where | What |
|------|--------|------|
| 1 | `backend/.env` | `SHOPIFY_WEBHOOK_SECRET=<Client secret>` (no quotes) |
| 2 | Railway → Variables | Same `SHOPIFY_WEBHOOK_SECRET` |
| 3 | Deploy backend | Push / `railway up` so new code + env are live |
| 4 | Shopify app config or Dashboard | Compliance webhook URI = `https://<railway-url>/api/webhooks/shopify/compliance` |
| 5 | Deploy Shopify app | `shopify app deploy` (or update version) so Shopify has the right URLs |

After that, re-run the automated check in Partners → Distribution → “Uitvoeren”; the webhook and HMAC checks should pass.
