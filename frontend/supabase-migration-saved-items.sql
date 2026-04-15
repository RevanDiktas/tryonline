-- =============================================
-- SAVED ITEMS TABLE (Wishlist + Closet)
-- Stores items shoppers have hearted (wishlist) or purchased (closet).
-- =============================================

CREATE TABLE IF NOT EXISTS public.saved_items (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
  list_type TEXT CHECK (list_type IN ('wishlist', 'closet')) NOT NULL,

  -- Product Info (from Shopify PDP or orders/paid webhook)
  product_id TEXT NOT NULL,
  variant_id TEXT,
  shop_domain TEXT NOT NULL,

  -- Display metadata
  product_name TEXT,
  product_image_url TEXT,
  product_price NUMERIC,
  currency TEXT DEFAULT 'USD',
  brand_name TEXT,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Prevent duplicate saves per user/product/store/list combo
CREATE UNIQUE INDEX IF NOT EXISTS idx_saved_items_unique
  ON public.saved_items (user_id, product_id, shop_domain, list_type);

-- Fast lookup by user + list type
CREATE INDEX IF NOT EXISTS idx_saved_items_user
  ON public.saved_items (user_id, list_type);

-- RLS
ALTER TABLE public.saved_items ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own saved items" ON public.saved_items;
CREATE POLICY "Users can view own saved items" ON public.saved_items
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own saved items" ON public.saved_items;
CREATE POLICY "Users can insert own saved items" ON public.saved_items
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own saved items" ON public.saved_items;
CREATE POLICY "Users can delete own saved items" ON public.saved_items
  FOR DELETE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own saved items" ON public.saved_items;
CREATE POLICY "Users can update own saved items" ON public.saved_items
  FOR UPDATE USING (auth.uid() = user_id);

-- Service role bypass (backend uses service key for webhook inserts)
DROP POLICY IF EXISTS "Service role full access to saved items" ON public.saved_items;
CREATE POLICY "Service role full access to saved items" ON public.saved_items
  FOR ALL USING (auth.role() = 'service_role');
