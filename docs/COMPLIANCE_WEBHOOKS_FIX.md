# Compliance Webhooks Fix (App Store Check)

## Why the checks failed

1. **"Biedt verplichte webhooks voor naleving" (Provides required webhooks for compliance)**  
   The app had no endpoint registered for the three mandatory GDPR/CCPA topics: `customers/data_request`, `customers/redact`, `shop/redact`. Shopify must be able to POST to a URL that responds with 200.

2. **"Verifieert webhooks met HMAC-handtekeningen" (Verifies webhooks with HMAC signatures)**  
   The backend was comparing HMAC using **hex** digest, while Shopify sends the `X-Shopify-Hmac-Sha256` header as **base64**. Verification always failed in production.

## What was changed

### 1. HMAC verification (`backend/app/api/routes/webhooks.py`)

- **Before:** `hmac.new(...).hexdigest()` compared to the header (wrong).
- **After:** HMAC is computed, then **base64-encoded** and compared to the header, matching [Shopify’s docs](https://shopify.dev/docs/apps/build/webhooks/subscribe/https).
- This applies to both the existing `orders-paid` webhook and the new compliance endpoint.

### 2. Compliance webhook endpoint

- **New route:** `POST /api/webhooks/shopify/compliance`
- Accepts all three mandatory topics on one URL (Shopify sends to a single URI).
- Reads `X-Shopify-Topic` to distinguish: `customers/data_request`, `customers/redact`, `shop/redact`.
- Verifies `X-Shopify-Hmac-Sha256`; returns **401** if invalid.
- Returns **200** immediately so Shopify’s delivery succeeds; actual data handling can be added or queued later.

## What you need to do

### 1. Configure the compliance webhook URI

Shopify must know where to send the three compliance webhooks.

- **If you use `shopify.app.toml`** (e.g. in your Shopify app repo or `shopify_app/`):

  ```toml
  [webhooks]
  api_version = "2024-01"   # or your app’s API version

  [[webhooks.subscriptions]]
  compliance_topics = ["customers/data_request", "customers/redact", "shop/redact"]
  uri = "https://YOUR_BACKEND_HOST/api/webhooks/shopify/compliance"
  ```

  Replace `YOUR_BACKEND_HOST` with your live backend (e.g. Railway URL like `https://your-app.up.railway.app`).

- **If you configure in Partner Dashboard:**  
  In the app’s Distribution / App setup, set the compliance webhook URL to:

  `https://YOUR_BACKEND_HOST/api/webhooks/shopify/compliance`

### 2. Use the app client secret for HMAC

The HMAC secret must be your app’s **Client secret** (API secret) from the Partner Dashboard, not a separate value.

- In Railway (or your backend env), set:
  - `SHOPIFY_WEBHOOK_SECRET` = your app’s **Client secret**
- If this was already set for `orders-paid`, no change needed as long as it’s the same secret.

### 3. Deploy and re-run the check

1. Deploy the backend so the new code and route are live.
2. In Partners → Your app → Distribution → App Store review, run **“Uitvoeren”** again for “Automatische controle op veelvoorkomende fouten”.
3. Both “Biedt verplichte webhooks voor naleving” and “Verifieert webhooks met HMAC-handtekeningen” should pass.

## Endpoint summary

| Purpose              | Method | Path                                   |
|----------------------|--------|----------------------------------------|
| Orders/paid          | POST   | `/api/webhooks/shopify/orders-paid`    |
| Compliance (all 3)   | POST   | `/api/webhooks/shopify/compliance`     |

Compliance topics: `customers/data_request`, `customers/redact`, `shop/redact` — same path, topic in `X-Shopify-Topic` header.
