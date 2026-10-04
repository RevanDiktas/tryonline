-- 006: one return event per Shopify refund
--
-- Shopify retries refunds/create until it gets a 200. Purchases are already
-- unique per order (idx_analytics_events_purchase_order_id); returns had no
-- such guard, so a retry after a slow or failed response counted the same
-- refund twice and inflated return rates. The webhook also checks before
-- inserting, but only the index closes the race between two retries.
--
-- Also indexes the refund handler's purchase lookup (shop + order_id), which
-- used to scan every purchase row.
--
-- Apply with: psql or Supabase SQL editor. Idempotent.

CREATE UNIQUE INDEX IF NOT EXISTS idx_analytics_events_return_refund_id
  ON analytics_events (shop_domain, (event_data->>'refund_id'))
  WHERE event_type = 'return';

CREATE INDEX IF NOT EXISTS idx_analytics_events_purchase_shop_order
  ON analytics_events (shop_domain, (event_data->>'order_id'))
  WHERE event_type = 'purchase';
