-- Migration: Add demo product to garments (optional)
-- Run when you want to test product config from DB instead of fallback
-- Replace URLs with your Supabase storage URLs after uploading GLBs

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.garments WHERE shopify_product_id = 'demo-npc-tshirt') THEN
    INSERT INTO public.garments (name, category, shopify_product_id, sizes, size_chart, fit_type, is_active)
    VALUES (
      'NPC Oversized T-Shirt',
      'tops',
      'demo-npc-tshirt',
      '{"xs": "/models/avatar_with_tshirt_xs.glb", "s": "/models/avatar_with_tshirt_s.glb", "m": "/models/avatar_with_tshirt_m.glb", "l": "/models/avatar_with_tshirt_l.glb", "xl": "/models/avatar_with_tshirt_xl.glb"}'::jsonb,
      '{"xs": {"chest": 88, "waist": 72, "hips": 86}, "s": {"chest": 92, "waist": 76, "hips": 90}, "m": {"chest": 100, "waist": 84, "hips": 98}, "l": {"chest": 108, "waist": 92, "hips": 106}, "xl": {"chest": 116, "waist": 100, "hips": 114}}'::jsonb,
      'regular',
      true
    );
  END IF;
END $$;

-- For Supabase storage URLs (after uploading), update sizes:
-- UPDATE garments SET sizes = '{"xs": "https://xxx.supabase.co/.../xs.glb", ...}'::jsonb WHERE shopify_product_id = 'demo-npc-tshirt';
