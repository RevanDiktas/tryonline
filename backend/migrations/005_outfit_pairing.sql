-- =============================================
-- Migration 005: Outfit pairing
--
-- A shopper on the jeans PDP should see the jeans WITH a top; a shopper on a
-- top's PDP should see that top WITH the jeans. Without this every viewer
-- renders one garment on a bare avatar.
--
-- The pairing is directional and stored per garment, so the same product can be
-- the primary on its own page and the companion on another's. Nullable: a
-- garment with no companion renders exactly as it does today, which is what
-- keeps every other brand unaffected.
--
-- Apply with: psql or Supabase SQL editor. Idempotent.
-- =============================================

-- 1. The pairing column. Self-referencing; ON DELETE SET NULL so removing a
--    garment degrades its partner to single-garment rendering rather than
--    breaking the partner's PDP.
ALTER TABLE public.garments
  ADD COLUMN IF NOT EXISTS companion_garment_id UUID
  REFERENCES public.garments(id) ON DELETE SET NULL;

COMMENT ON COLUMN public.garments.companion_garment_id IS
  'Garment shown alongside this one in the viewer so the avatar is never half-dressed. Directional: tops point at a bottom, bottoms point at a top. NULL = render this garment alone.';

-- Lookup is per-garment on the read path, but index the reverse direction so
-- "what points at me" stays cheap when we later invalidate on garment delete.
CREATE INDEX IF NOT EXISTS idx_garments_companion
  ON public.garments (companion_garment_id)
  WHERE companion_garment_id IS NOT NULL;

-- 2. Seed the La Fam pilot pairings.
--    jeans            -> diamond t-shirt black
--    each of 3 tops   -> denim slogan jeans
--
--    Keyed on (brand_id, shopify_product_id) rather than hardcoded UUIDs so
--    this is safe to re-run and readable against the storefront.
DO $$
DECLARE
  v_brand   UUID := 'a3e127f6-d606-44ae-9d9d-779e8c82c2ec';  -- la fam
  v_jeans   UUID;
  v_blacktee UUID;
BEGIN
  SELECT id INTO v_jeans
    FROM public.garments
   WHERE brand_id = v_brand AND shopify_product_id = 'denim-slogan-jeans';

  SELECT id INTO v_blacktee
    FROM public.garments
   WHERE brand_id = v_brand AND shopify_product_id = 'diamond-t-shirt-black';

  IF v_jeans IS NULL OR v_blacktee IS NULL THEN
    RAISE NOTICE 'La Fam jeans or black tee not found — skipping pairing seed';
    RETURN;
  END IF;

  -- Bottom -> top
  UPDATE public.garments
     SET companion_garment_id = v_blacktee
   WHERE id = v_jeans;

  -- Every top -> the jeans
  UPDATE public.garments
     SET companion_garment_id = v_jeans
   WHERE brand_id = v_brand
     AND shopify_product_id IN (
       'diamond-t-shirt-black',
       'diamond-t-shirt-blue',
       'striped-la-fam-longsleeve-copy'
     );
END $$;

-- 3. Verify (should return 4 rows, each with a companion whose category is the
--    opposite of its own).
--
-- SELECT g.name, g.category, c.name AS companion, c.category AS companion_category
--   FROM public.garments g
--   JOIN public.garments c ON c.id = g.companion_garment_id
--  WHERE g.brand_id = 'a3e127f6-d606-44ae-9d9d-779e8c82c2ec'
--  ORDER BY g.name;
