-- Align DB with storefront: theme passes product.handle (e.g. rs-zip-up), not Admin numeric ID.
-- Run once in Supabase SQL editor if your table only has shopify_product_id.

ALTER TABLE public.garments
  ADD COLUMN IF NOT EXISTS shopify_product_handle TEXT;

UPDATE public.garments
SET shopify_product_handle = shopify_product_id
WHERE shopify_product_handle IS NULL
  AND shopify_product_id IS NOT NULL
  AND shopify_product_id !~ '^[0-9]+$';

CREATE INDEX IF NOT EXISTS idx_garments_shopify_product_handle
  ON public.garments (shopify_product_handle);
