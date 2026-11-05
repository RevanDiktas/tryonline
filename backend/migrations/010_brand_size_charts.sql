-- 010: one size chart per category (or per Shopify product type) for a brand.
--
-- A 3D garment keeps its own chart on garments.size_chart. Every other product the
-- size finder sees falls back to the brand's category chart: match the Shopify
-- product type first (case-insensitive, e.g. "T-shirt"), else the inferred category
-- (tops / bottoms / outerwear / dresses / accessories). Backend (service role) only.
-- Idempotent.

CREATE TABLE IF NOT EXISTS brand_size_charts (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id      uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  name          text NOT NULL,
  category      text NOT NULL CHECK (category IN ('tops', 'bottoms', 'outerwear', 'dresses', 'accessories')),
  product_types text[] NOT NULL DEFAULT '{}',          -- lowercased Shopify product.type values
  fit_type      text NOT NULL DEFAULT 'regular' CHECK (fit_type IN ('slim', 'regular', 'oversized')),
  size_chart    jsonb NOT NULL DEFAULT '{}'::jsonb,   -- {"s": {"chest": 52, "length": 70}, ...} cm, flat
  is_active     boolean NOT NULL DEFAULT true,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE brand_size_charts ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_brand_size_charts_brand ON brand_size_charts (brand_id);
