-- =============================================
-- MIGRATION: Add pipeline_files column to fit_passports
-- =============================================
-- Run this migration if you already have an existing database
-- Date: 2026-01-16
-- Purpose: Store all pipeline output file URLs (GLB, OBJ, PNG, JSON, NPZ) per user

-- Add pipeline_files JSONB column to fit_passports table
ALTER TABLE public.fit_passports
ADD COLUMN IF NOT EXISTS pipeline_files JSONB;

-- Create GIN index for efficient JSONB queries
CREATE INDEX IF NOT EXISTS idx_fit_passports_pipeline_files 
ON public.fit_passports USING GIN (pipeline_files);

-- Optional: Migrate existing avatar_url to pipeline_files format
-- (This will preserve existing data by moving avatar_url into the JSONB structure)
UPDATE public.fit_passports
SET pipeline_files = jsonb_build_object('avatar_glb', avatar_url)
WHERE avatar_url IS NOT NULL 
  AND pipeline_files IS NULL;

-- Verify the migration
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_schema = 'public' 
      AND table_name = 'fit_passports' 
      AND column_name = 'pipeline_files'
  ) THEN
    RAISE NOTICE 'Migration successful: pipeline_files column added to fit_passports';
  ELSE
    RAISE EXCEPTION 'Migration failed: pipeline_files column not found';
  END IF;
END $$;
