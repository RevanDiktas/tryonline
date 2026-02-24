# Garments storage layout

When a **brand** is created (on Shopify app install), the backend ensures a shared **Supabase Storage bucket** exists so garment files can be stored in a consistent structure.

## Bucket and path convention

- **Bucket name:** `garments` (config: `garments_bucket`).
- **Path inside bucket:** `{brand_id}/{product_id}/{filename}`

So the full object key is:

```
garments/{brand_id}/{product_id}/xs.glb
garments/{brand_id}/{product_id}/s.glb
garments/{brand_id}/{product_id}/m.glb
...
```

- **brand_id** = UUID from `brands.id` (created at signup).
- **product_id** = e.g. Shopify product ID or your internal product identifier (same as `garments.shopify_product_id` when you use Shopify).
- **filename** = e.g. `xs.glb`, `s.glb`, `thumbnail.png`, etc.

## When the bucket is created

- On **first brand signup**, `upsert_brand_for_shop` calls `ensure_garments_bucket()` before inserting the new brand. The bucket is created once; later brands reuse it.
- The bucket is **public** so try-on config can serve GLB URLs without signed URLs.

## Storing URLs in `garments` table

In `garments.sizes` (JSONB) you can store either:

1. **Full URL** — e.g. `https://xxx.supabase.co/storage/v1/object/public/garments/brand_id/product_id/m.glb` (unchanged when serving).
2. **Relative path** — e.g. `garments/brand_id/product_id/m.glb`. The products API (`/products/{product_id}/tryon-config`) resolves this to a full URL using your Supabase project URL.

Using the relative path keeps the DB portable and matches the convention above.

## Backend helpers (Python)

- **`SupabaseService.ensure_garments_bucket()`** — Idempotent: creates the `garments` bucket if it doesn’t exist. Called when creating a new brand.
- **`SupabaseService.garment_storage_path(brand_id, product_id, filename)`** — Returns `brand_id/product_id/filename` for uploads or DB paths.
- **`SupabaseService.get_garment_public_url(brand_id, product_id, filename)`** — Returns the full public URL for that path in the garments bucket.

When you add or update garments (e.g. from a script or future upload API), upload files to the bucket at `garment_storage_path(...)` and store in `garments.sizes` either the relative path `garments/{brand_id}/{product_id}/{size}.glb` or the full URL from `get_garment_public_url`.
