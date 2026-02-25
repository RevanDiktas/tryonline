-- Link brands to their owner user account.
-- Run this in Supabase SQL Editor.

ALTER TABLE public.brands
  ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES public.users(id);

CREATE INDEX IF NOT EXISTS idx_brands_user_id ON public.brands(user_id);

COMMENT ON COLUMN public.brands.user_id IS 'The auth user who owns/manages this brand account.';
