-- Migration: Ensure fit_passports has preferred_fit column
-- Run in Supabase SQL Editor if analytics_events.preferred_fit stays "regular" despite selecting Loose on dashboard
-- This adds the column if missing (e.g. project created before preferred_fit was in schema)

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'fit_passports' AND column_name = 'preferred_fit'
  ) THEN
    ALTER TABLE public.fit_passports ADD COLUMN preferred_fit TEXT DEFAULT 'regular';
    ALTER TABLE public.fit_passports ADD CONSTRAINT fit_passports_preferred_fit_check
      CHECK (preferred_fit IN ('slim', 'regular', 'loose'));
    UPDATE public.fit_passports SET preferred_fit = 'regular' WHERE preferred_fit IS NULL;
  END IF;
END $$;
