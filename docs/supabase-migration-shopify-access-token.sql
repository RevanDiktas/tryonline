-- Add Shopify OAuth access token to brands (for embedded app install flow).
-- Run this in Supabase SQL editor if the column does not exist.

ALTER TABLE public.brands
  ADD COLUMN IF NOT EXISTS shopify_access_token TEXT;

COMMENT ON COLUMN public.brands.shopify_access_token IS 'Shopify Admin API access token (set on app install/OAuth).';
