# Checkout Profile API — Shipping address for brands

**Purpose:** Let TryOn-integrated brands (or our bridge page) get the shopper’s **default shipping address** so checkout can be prefilled. The shopper has already saved addresses in their TryOn dashboard; this API returns the one marked “Use at checkout.”

---

## Endpoint

**GET** `/api/checkout-profile`

**Auth:** The request must include the **shopper’s Supabase access token** so we can verify identity and return only that user’s default address.

- **Header:** `Authorization: Bearer <access_token>`
- The `access_token` is the Supabase session access token (JWT). Your frontend gets it from the logged-in user’s session (e.g. `supabase.auth.getSession()` → `session.access_token`).

**Responses:**

- **200** — Success. Body:
  ```json
  {
    "address": {
      "label": "Home",
      "name": "Jane Doe",
      "line1": "123 Main St",
      "line2": "Apt 4",
      "city": "Amsterdam",
      "state": "Noord-Holland",
      "postal_code": "1012 AB",
      "country": "Netherlands"
    }
  }
  ```
  All fields except `line2` and `state` are always present. `line2` and `state` may be `null`.

- **401** — Missing or invalid token (e.g. expired, wrong audience).
- **404** — User has no saved addresses. Ask them to add one in their TryOn dashboard.
- **503** — Checkout profile API not configured (backend missing `SUPABASE_JWT_SECRET`).

---

## Who calls this API?

1. **TryOn bridge page (recommended)**  
   Your app hosts a “Confirm your address” page. The user lands there after clicking “Checkout” from the TryOn widget. The page:
   - Reads the user’s Supabase `access_token` from the session.
   - Calls `GET /api/checkout-profile` with `Authorization: Bearer <access_token>`.
   - Shows the returned address and a “Continue to [Brand] checkout” button, then redirects to the brand’s checkout (and can pass address in URL/attributes if the brand supports it).

2. **Brand’s checkout extension (e.g. Shopify)**  
   If the brand runs a Checkout UI Extension that can perform authenticated requests on behalf of the shopper, it would need to receive the same `access_token` (e.g. via URL param or cart attribute when redirecting to checkout) and then call this API. **Important:** The token must be the shopper’s Supabase access token, not a brand API key.

---

## Backend configuration

- **SUPABASE_JWT_SECRET** — Required for this API. In Supabase: **Project Settings → API → JWT Secret**. Copy it into your backend `.env`. Without it, the API returns 503.

---

## Security

- We do not return `user_id` or any internal IDs — only the shipping address fields needed for prefill.
- The token is verified using Supabase’s JWT secret (signature, audience `authenticated`, expiry). Only a valid Supabase access token for the shopper will yield their address.

---

## Example (bridge page, JavaScript)

```js
const session = await supabase.auth.getSession();
const accessToken = session?.data?.session?.access_token;
if (!accessToken) {
  // User not logged in → redirect to login or show “Sign in to use saved address”
  return;
}
const res = await fetch('https://your-api.com/api/checkout-profile', {
  headers: { Authorization: `Bearer ${accessToken}` },
});
if (res.status === 404) {
  // No address → show “Add an address in your TryOn dashboard” or collect here
  return;
}
if (!res.ok) throw new Error('Failed to load address');
const { address } = await res.json();
// Prefill your form or redirect to brand checkout with address
```

---

*Last updated: February 2026.*
