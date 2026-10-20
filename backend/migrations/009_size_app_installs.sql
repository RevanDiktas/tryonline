-- 009: installs of the "TryOn Size" Shopify app (the Find my size button on its own)
--
-- TryOn Size is a separate Shopify app from Tryon / Ramin / La Fam. Its installs live here, not
-- in brands: a size-only shop needs no brand row (the card sizes from the store's own size
-- labels), and an unclaimed brand row is what brand/register could be used to take over.
--
--   shop_domain       the verified *.myshopify.com host (from the session token's `dest`)
--   access_token      offline Admin API token from token exchange; null after uninstall
--   plan_name         the active Managed Pricing plan, null when none
--   plan_status       Shopify's AppSubscriptionStatus (ACTIVE, PENDING, CANCELLED, ...)
--   active            true only while the app is installed AND a plan is ACTIVE (trial included);
--                     mirrored into the app-data metafield the block reads, so the button shows
--   uninstalled_at    set by app/uninstalled; shop/redact deletes the row 48h later
--
-- Written and read through the backend (service role) only, so RLS is on with no policies.
-- Apply with: psql or Supabase SQL editor. Idempotent.

CREATE TABLE IF NOT EXISTS size_app_installs (
  shop_domain     text PRIMARY KEY,
  access_token    text,
  scope           text,
  plan_name       text,
  plan_status     text,
  active          boolean NOT NULL DEFAULT false,
  installed_at    timestamptz NOT NULL DEFAULT now(),
  uninstalled_at  timestamptz,
  updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS size_app_installs_active_idx ON size_app_installs (active);

ALTER TABLE size_app_installs ENABLE ROW LEVEL SECURITY;
