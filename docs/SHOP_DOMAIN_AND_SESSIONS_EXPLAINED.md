# Where shop domain and product IDs come from

## 1. "Shop: tryon-9621.myshopify.com" on the Welcome screen

**Where it comes from:** **Shopify**, not our database.

When you open the app from **Apps → Tryon** in the store Admin, Shopify loads our embedded app URL with query parameters:

```
https://tryonline.vercel.app/app?shop=tryon-9621.myshopify.com&host=...
```

So `shop` is in the URL. Our `/app` page reads it with `searchParams.get('shop')` and displays it as "Shop: {shop}". No lookup in `brands` or any other table — it’s just the URL param Shopify adds so we know which store is opening the app.

---

## 2. Product ID 9174253764826 "still showing" after you removed it

It depends **where** you see it.

### If you see it in the `tryon_sessions` table (Supabase)

- **What `tryon_sessions` is:** One row per try-on session (when someone used the widget). Each row stores `shop_domain`, `product_id`, `session_token`, etc. at the time of that session.
- **Removing a product/garment** (e.g. deleting a row in `garments` or changing a product on Shopify) does **not** delete or change old `tryon_sessions` rows. They are historical records.
- So **product_id 9174253764826 will keep appearing** in existing session rows until you delete those rows (or clear the table) in Supabase. That’s expected.

To stop seeing that product ID in the table you can:

- In Supabase → Table Editor → `tryon_sessions`: filter by `product_id` = `9174253764826` and delete those rows, or  
- Leave them as history; they don’t affect whether the product has try-on anymore.

### If you see it on the storefront / in the widget

- Try-on is shown for a product only if there is a row in **`garments`** with `shopify_product_id` = that product’s ID.
- If you removed the **garment** for product 9174253764826 (deleted the row or set it inactive), the widget should no longer offer try-on for that product. If it still does, check that there is no remaining `garments` row with `shopify_product_id` = `9174253764826`.

---

## 3. Shop domain in the database

- **`tryon_sessions.shop_domain`** is set when a try-on session is created: the widget sends `shop` (e.g. from the store’s URL), and the backend stores it on the session row. So rows with `tryon-9621.myshopify.com` are from try-on usage on that store.
- **`brands.shopify_domain`** is set when the app is installed and our OAuth callback runs: we create/update a brand row with the store’s domain. If the callback never runs (e.g. redirect went to frontend), `brands` stays empty even though you see the shop domain on the Welcome screen (from the URL).

So: **Welcome screen shop** = from Shopify URL. **Shop in DB** = from our backend when we create a session or a brand.
