-- =============================================
-- Migration: Analytics Category A
-- Run in Supabase SQL Editor
-- =============================================

-- 0. OPTIONAL: Clear test data (run this first if you want a fresh start)
-- Uncomment and run separately, or run the whole file
/*
DELETE FROM public.analytics_events;
DELETE FROM public.tryon_sessions;
*/

-- 1. Add columns to analytics_events (Category A schema)
ALTER TABLE public.analytics_events
  ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES public.brands(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS variant_id TEXT,
  ADD COLUMN IF NOT EXISTS country TEXT,
  ADD COLUMN IF NOT EXISTS city TEXT,
  ADD COLUMN IF NOT EXISTS preferred_fit TEXT;

-- 2. Create analytics_daily for pre-aggregated metrics
CREATE TABLE IF NOT EXISTS public.analytics_daily (
  id BIGSERIAL PRIMARY KEY,
  brand_id UUID REFERENCES public.brands(id) ON DELETE CASCADE,
  shop_domain TEXT,
  date DATE NOT NULL,
  tryons_started INT NOT NULL DEFAULT 0,
  add_to_carts INT NOT NULL DEFAULT 0,
  purchases INT NOT NULL DEFAULT 0,
  unique_sessions INT NOT NULL DEFAULT 0,
  revenue DECIMAL(12, 2) NOT NULL DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Unique: one row per scope per date (brand when set, else shop_domain)
CREATE UNIQUE INDEX IF NOT EXISTS idx_analytics_daily_brand_date
  ON public.analytics_daily (brand_id, date) WHERE brand_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_analytics_daily_shop_date
  ON public.analytics_daily (shop_domain, date) WHERE brand_id IS NULL AND shop_domain IS NOT NULL;

-- 3. Indexes for analytics_events (Category A queries)
CREATE INDEX IF NOT EXISTS idx_analytics_events_session_id ON public.analytics_events(session_id);
CREATE INDEX IF NOT EXISTS idx_analytics_events_created_at ON public.analytics_events(created_at);
CREATE INDEX IF NOT EXISTS idx_analytics_events_event_type_created ON public.analytics_events(event_type, created_at);
CREATE INDEX IF NOT EXISTS idx_analytics_events_brand_id ON public.analytics_events(brand_id);
CREATE INDEX IF NOT EXISTS idx_analytics_events_country ON public.analytics_events(country);

-- 4. Indexes for analytics_daily
CREATE INDEX IF NOT EXISTS idx_analytics_daily_date ON public.analytics_daily(date);
CREATE INDEX IF NOT EXISTS idx_analytics_daily_brand_id ON public.analytics_daily(brand_id);

-- 5. Purchase idempotency: prevent duplicate purchase events per order
CREATE UNIQUE INDEX IF NOT EXISTS idx_analytics_events_purchase_order_id
  ON public.analytics_events ((event_data->>'order_id'))
  WHERE event_type = 'purchase' AND event_data->>'order_id' IS NOT NULL;
