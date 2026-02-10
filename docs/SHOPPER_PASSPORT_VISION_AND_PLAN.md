# Shopper Passport — Vision & Implementation Plan

**Purpose:** Make TryOn the place where shoppers store everything that makes checkout instant. One passport across all TryOn brands → one-click checkout. Better shopper experience = more usage = more data for brands = FOMO to adopt TryOn.

---

## 1. Vision

### 1.1 The idea

- **Stripe does it for software/subscriptions.** TryOn does it for **physical goods and online brands.**
- Shoppers save **addresses** (multiple: home, work, gift) and **payment method** once in their TryOn dashboard (their **passport**).
- On the user dashboard they **toggle which address** (and which payment) to use by default or per context.
- When they go to checkout at any TryOn-integrated brand: **everything is pre-filled.** They **confirm**, not re-type. One click.
- Result: faster checkout, fewer errors, higher conversion, happier shoppers.

### 1.2 Why it matters for TryOn

- **Shopper = bait for data.** The nicer we make it for the shopper, the more they use TryOn → the more valuable our data and attribution for brands.
- At some point **nobody wants to go back** to typing address and card on every site. We become the standard; taking it away feels like a step backward.
- So: **optimize try-on over time**, but **already now** add things that change how people feel about online shopping. Saved address + payment on the passport is one of those things.

### 1.3 Payment: our own system vs partners

- **Goal:** Where possible, **don’t depend on Stripe (or another processor) as the identity of “saved payment.”** If we store and process payment ourselves, we can **claim a transaction fee** like Stripe does.
- **Reality:** Storing and processing card/bank details ourselves means **PCI DSS** (and often **money-transmitter / payment-institution** licensing). That’s real legal and operational work. If it’s manageable and we’re willing to invest, we can move toward **our own system** and transaction fees. If the legal burden is too high for now, we can **defer saved payment** and ship **addresses only** first, then add payment once we have a clear path (own system when legal is ready, or a tokenized partner only if we need speed without taking a fee).
- **For the doc:** Phase 1 is **addresses for sure**; **saved payment** we add when we’re ready (own system preferred; partner only if we need to ship fast and accept no fee).

---

## 2. Scope: What goes on the passport (today + later)

| Area | Phase 1 (now) | Later |
|------|----------------|-------|
| **Body & fit** | ✓ Already: measurements, avatar, preferred_fit (fit_passports) | — |
| **Addresses** | Multiple addresses; mark default; use at checkout | — |
| **Payment** | Add when ready: our own system (transaction fee) if legal is clear; otherwise defer or use partner (no Stripe as default) | Multiple methods, default; our own processing + fee |
| **Wishlist** | — | Save items across TryOn brands (product_id + shop) |
| **Order history** | — | TryOn-attributed purchases (“What you bought with TryOn”) |
| **Checkout UX** | Dashboard: manage addresses (and payment when we add it); “Shipping & Billing” section | Merchant integration: prefill / confirm flow |

**Explicitly out of scope for passport (no need to build):**

- **Preferred size per category** — We already have **preferred_fit** and **recommended size**; recommendation is our product. Not needed on passport.
- **Return preferences** — Handled per brand; not a passport feature.

---

## 3. Implementation Plan — Phase 1

### 3.1 Schema

**Addresses (Phase 1):**  
- `user_addresses`: id, user_id, label (e.g. "Home", "Work"), name, line1, line2, city, state, postal_code, country, is_default, created_at, updated_at  

**Payment (when we add it):**  
- Prefer **our own system** (store only what we need for our own processing + fee; design for PCI / legal from day one if we go this route).  
- If we use a partner, store only tokens/IDs (e.g. payment_method_id), never raw card numbers.  
- Table could be: `user_payment_methods`: id, user_id, provider ('tryon' | 'partner'), external_id or encrypted_ref, display_last4, display_brand, expiry_month, expiry_year, is_default, created_at. (Exact shape depends on own-system vs partner.)

**RLS:** Same pattern as fit_passports — user can only read/update/insert their own rows.

### 3.2 Backend API

**Addresses (Phase 1):**  
- `GET /api/me/addresses` — list addresses for current user  
- `POST /api/me/addresses` — add address (body: label, name, line1, line2, city, state, postal_code, country; optional is_default)  
- `PATCH /api/me/addresses/{id}` — update address; allow setting is_default  
- `DELETE /api/me/addresses/{id}` — remove address  

**Payment (when we add it):**  
- `GET /api/me/payment-methods` — list (masked) payment methods  
- `POST /api/me/payment-methods` — add (our own flow or partner token)  
- `PATCH /api/me/payment-methods/{id}` — set is_default  
- `DELETE /api/me/payment-methods/{id}` — remove  

**Merchant-facing (Phase 2):**  
- `GET /api/checkout-profile` (or similar) — with **user consent**. Returns default shipping address (and “payment on file” when we have it). Brands use this to prefill checkout.

### 3.3 Frontend — User dashboard

- New section: **“Shipping & Billing”** on the user dashboard.
  - **Addresses:** List saved addresses; add / edit / delete; **toggle default** (“Use this at checkout”).
  - **Payment:** (When we add it) Show saved method (masked); add one; set default. No Stripe dependency unless we explicitly choose a partner.
- Same theme-aware, borderless style as rest of dashboard (black/white lab aesthetic).
- Copy: “Your details are ready for TryOn brands — just confirm at checkout.”

### 3.4 Migration

- Migration: `user_addresses` first. Add `user_payment_methods` (and any partner/own-system fields) when we implement saved payment.

---

## 4. Merchant integration (how brands use the passport)

- **Phase 1:** No merchant integration yet. Value = single place for the user to manage addresses (and payment when we add it); set expectation (“Ready for TryOn brands”).
- **Phase 2:** Brands can call our API with user consent to get default address (and payment-on-file flag when applicable) to prefill their checkout (e.g. Shopify Checkout UI Extension, or a TryOn “Confirm your info” bridge page).

---

## 5. Passport features we will add (prioritized)

| Feature | Status | Notes |
|--------|--------|-------|
| **Multiple addresses + default** | Phase 1 | Implement now. |
| **Saved payment** | When ready | Prefer our own system (transaction fee); add only when legal path is clear or we accept a partner. |
| **Wishlist / saved items** | Planned | Save items across TryOn brands (product_id + shop). Cross-brand “try later” list. |
| **Order history (TryOn-attributed)** | Planned | “Purchases you made after try-on” — reinforces value. |

**Not on the passport (no need to build):** Preferred size per category (we have preferred_fit + recommended size). Return preferences (brand-dependent).

---

## 6. Future vision: social, webshop, closet

These are later-stage ideas to keep in the product vision; not part of Phase 1 scope.

### 6.1 Social: friends and sharing

- Connect with **social media**; **add friends** on TryOn.
- **Recommend items** or **send items** to friends (“You’d look great in this”).
- Builds community and retention.

### 6.2 TryOn webshop and closet

- **TryOn webshop:** Our own shop on TryOn with **API links to brands**. One place to browse and buy from TryOn-integrated brands, ship to your saved address.
- **Your closet:** Every item you’ve **purchased via TryOn** gets its **3D garment** added to **your closet** on TryOn.
  - **Use case:** You’re out of town, back in two days, party right when you land. You don’t know what to wear. On TryOn you open **your closet** — all your past TryOn purchases as 3D garments — and **build your outfit** there. Then you go. Optionally, you can also **browse things you don’t own yet** and order to your address. So: closet = your 3D wardrobe from past purchases + mix with browse-and-order for anything else.
- This makes TryOn the place for “what do I wear?” as well as “what should I buy?”

---

## 7. Summary

- **Vision:** Passport = one place for body, fit, addresses, and (when we’re ready) payment. One-click checkout at TryOn brands. Shopper experience drives usage → data → brand FOMO.
- **Payment:** We prefer **our own system** so we can claim a transaction fee. Storing/processing bank/card ourselves has legal weight (PCI, licensing). Phase 1 = **addresses**; add **saved payment** when we have a clear path (own system if legal is acceptable, or partner only if we need speed and accept no fee).
- **Phase 1:** Schema and API for **user_addresses**; dashboard “Shipping & Billing” section; no Stripe dependency. Payment tables and UI when we’re ready.
- **Next features:** Wishlist (saved items), order history (TryOn-attributed).
- **Future:** Social (friends, recommend/send items); TryOn webshop + **closet** (your 3D garments from past purchases, outfit builder, browse and order).

---

*Last updated: February 6, 2026.*
