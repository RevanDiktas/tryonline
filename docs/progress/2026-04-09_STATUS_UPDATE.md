# Status update — 2026-04-09

## Wins today

- **TryonRaminPilot** loads in admin (`…/apps/tryonraminpilot/app`); **Go to Brand Dashboard** works and the **brand analytics dashboard** is usable (zeros expected on a fresh install).
- **Theme editor**: Try On app block from **TryonRaminPilot** is on the live **Standaard product** template; button appears on the PDP as intended.
- **Vercel**: `NEXT_PUBLIC_SHOPIFY_EMBEDDED_CLIENT_ID` (and related OAuth/shop-resolution work on `feature/analytics`) aligns embedded App Bridge with the pilot app.

---

## Topic A — `shopify_access_token` NULL for RaminStudios while the app feels “connected”

### Thesis

**The dashboard “Connected: …” state is not the same as “we have a Shopify Admin API access token in Supabase.”**  
The UI treats the brand as connected when **`brands.shopify_domain`** is set (from signup or profile), because `getMyBrand` returns that field. **`shopify_access_token` is only written when our backend successfully completes the OAuth code exchange and runs `upsert_brand_for_shop` for a shop hostname that exactly matches how we look up the row.**

From the current backend implementation:

- OAuth callback and `upsert_brand_for_shop` normalize Shopify’s shop to **`something.myshopify.com`** (full hostname).
- `upsert_brand_for_shop` finds an existing row with **`eq("shopify_domain", shop)`** and only then **updates** `shopify_access_token`. If there is **no** row with that exact string, it **inserts a new** brand row (placeholder email, token set).

**Observation from your Supabase screenshot:** the RaminStudios row shows **`shopify_domain` = `raminstudios`** (short form, not `raminstudios.myshopify.com`). In that situation:

1. OAuth completes for **`raminstudios.myshopify.com`**.
2. Lookup for `shopify_domain == "raminstudios.myshopify.com"` **does not** match the row where `shopify_domain == "raminstudios"`.
3. The token is either stored on a **different** `brands` row (new insert keyed to the full domain) or, if something prevented insert/update, never attached to the row you are looking at.

So the most plausible explanation for **NULL on the row you expect** is **shop domain string mismatch between signup/UI and OAuth**, not “Shopify didn’t install.”

### Secondary factors to validate tomorrow (no code changes in this doc)

- Confirm in Supabase whether a **second** brand row exists with `shopify_domain = raminstudios.myshopify.com` and a non-null token.
- Confirm Railway logs for `[Shopify callback]` / `upsert_brand_for_shop` around install time (`brand created` vs `db_failed`).
- Align data entry: **`shopify_domain` should always be the full `*.myshopify.com` host** everywhere (signup, APIs, pilot shop list) so upsert updates the same row the user logs into.

### Summary line for Topic A

> **Thesis:** Missing `shopify_access_token` on the RaminStudios row is consistent with **`shopify_domain` not matching Shopify’s canonical hostname** (`*.myshopify.com`), so OAuth updates (or inserts) a different record than the one tied to the logged-in user; the UI “connected” flag is driven by presence of **any** `shopify_domain` on the user’s brand, not by token presence.

---

## Topic B — Try On block on “Blanc” also appears on the hat; removing it on one product removes it everywhere

### Thesis

**This is expected Shopify Online Store 2.0 behavior, not a bug in our extension.**

You added the **Try On** block to the **default product template** (“Standaard product”). In OS 2.0, **templates are shared**: every product that uses that template inherits the **same** sections and **same** app blocks. The theme editor preview switches products, but the underlying JSON template is still one file — so the block is global for that template.

**Removing or hiding the block in the editor while still editing that shared template** therefore removes it for **all** products assigned to that template (e.g. zip-up and hat), which matches what you saw.

### Ways to show Try On on some products but not others (conceptual — Shopify platform options)

1. **Alternate product template (native, no app code required)**  
   - Duplicate the default product template (e.g. `product.json` → `product.without-tryon.json` or Shopify’s “Add template” flow).  
   - Remove the Try On block only from the duplicate.  
   - In **Admin → Products → [Hat]**, set **Theme template** to the template **without** the block.  
   - Leave clothing products on the default template **with** the block.

2. **Metafield + conditional Liquid (requires theme or app-block code change later)**  
   - e.g. product metafield `custom.show_tryon` and wrap the block output in `{% if product.metafields... %}`.  
   - This is flexible but **is** a code/design change to the block or theme.

3. **Product type / tags / handles in Liquid (same — code change)**  
   - Hide button when `product.type == 'Accessories'` etc.

### Summary line for Topic B

> **Thesis:** App blocks live on **templates**, not on individual product records; one default product template ⇒ one shared layout for every product using it. To exclude the hat, use a **second product template** without the block and assign only the hat (or only non-try-on products) to that template — that is the standard Shopify approach without custom Liquid logic.

---

## Next session (tomorrow)

1. **Data:** Reconcile `brands` rows for Ramin (short `raminstudios` vs `raminstudios.myshopify.com`); decide on one canonical domain and optional migration / manual fix for `shopify_domain` + token on the user’s row.  
2. **Theme:** If you want hat without Try On, add an alternate product template and assign it to the hat product only.  
3. **Optional product question:** When you return, specify whether you want per-product control only via templates or via metafields (future block/schema work).

---

## Files / branches (reference)

- OAuth + upsert: `backend/app/api/routes/shopify.py`, `backend/app/services/supabase.py` (`upsert_brand_for_shop`).  
- “Connected” UI: `frontend/app/brand/page.tsx` (`brandShop` from `shopify_domain`).  
- PDP block: `shopify_app/extensions/tryon-widget/blocks/tryon-button.liquid`.  
- Ongoing work: `feature/analytics`.
