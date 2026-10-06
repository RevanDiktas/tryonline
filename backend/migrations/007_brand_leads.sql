-- 007: brands that asked to start from tryon.global/start
--
-- Until the public Shopify app is in the App Store, a brand starts by leaving its store
-- and email here; the TryOn team sends a private install link. The website writes rows
-- through the backend (service role) only, so RLS is on with no policies: nobody can read
-- or write this table with the anon key.
--
-- Apply with: psql or Supabase SQL editor. Idempotent.

CREATE TABLE IF NOT EXISTS brand_leads (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at   timestamptz NOT NULL DEFAULT now(),
  brand_name   text NOT NULL,
  contact_name text,
  email        text NOT NULL,
  shop_domain  text,
  plan         text,
  notes        text,
  source       text,
  status       text NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'link_sent', 'installed', 'live', 'lost'))
);

ALTER TABLE brand_leads ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_brand_leads_created_at ON brand_leads (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_brand_leads_email ON brand_leads (lower(email));
