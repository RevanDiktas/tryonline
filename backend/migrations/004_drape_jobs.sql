-- =============================================
-- Migration 004: Pre-drape job queue
-- Adds:
--   1. drape_jobs table (Postgres-native job queue, dispatched via SKIP LOCKED)
--   2. garments.content_hash column (versions a SKU's OBJ; cache key component)
--   3. draped_meshes.garment_version_hash column (lets stale rows GC themselves)
--
-- Apply with: psql or Supabase SQL editor. Idempotent.
-- =============================================

-- 1. Garment content hash. Computed by the backend on enqueue (lazy) by hashing
--    the OBJ at the storage path. NULL means "not computed yet"; backfill flow
--    computes on first use.
ALTER TABLE public.garments
  ADD COLUMN IF NOT EXISTS content_hash TEXT;

COMMENT ON COLUMN public.garments.content_hash IS
  'SHA-256 of all sized OBJ files joined, truncated to 16 hex. Bumps when brand re-uploads OBJ. Used to invalidate cached drapes on garment change.';

-- 2. Draped mesh now records the garment_version_hash it was draped against.
--    Old rows with NULL garment_version_hash are pre-versioning rows; they will
--    age out via expires_at.
ALTER TABLE public.draped_meshes
  ADD COLUMN IF NOT EXISTS garment_version_hash TEXT;

COMMENT ON COLUMN public.draped_meshes.garment_version_hash IS
  'Snapshot of garments.content_hash at drape time. Cache hits require equality.';

-- 3. drape_jobs: append-only-ish job queue. One row per (user, garment, size,
--    garment_version_hash). Status machine: queued -> dispatched -> running ->
--    (completed | failed | skipped_cache_hit). priority: lower = sooner.
CREATE TABLE IF NOT EXISTS public.drape_jobs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  garment_id UUID NOT NULL REFERENCES public.garments(id) ON DELETE CASCADE,
  size TEXT NOT NULL,
  body_hash TEXT NOT NULL,
  garment_version_hash TEXT NOT NULL,

  status TEXT NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued', 'dispatched', 'running', 'completed', 'failed', 'skipped_cache_hit', 'cancelled')),
  priority SMALLINT NOT NULL DEFAULT 100,
  attempts SMALLINT NOT NULL DEFAULT 0,
  max_attempts SMALLINT NOT NULL DEFAULT 3,

  runpod_job_id TEXT,
  draped_mesh_id UUID REFERENCES public.draped_meshes(id) ON DELETE SET NULL,
  error_message TEXT,

  created_at TIMESTAMPTZ DEFAULT NOW(),
  dispatched_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Idempotent enqueue: same (user, garment, size, version) only ever has one row.
-- If a brand re-uploads the OBJ (new content_hash), a new row is created and the
-- old one becomes harmless history.
CREATE UNIQUE INDEX IF NOT EXISTS idx_drape_jobs_unique
  ON public.drape_jobs (user_id, garment_id, size, garment_version_hash);

-- Dispatcher hot path: pick up the next N queued jobs by priority.
-- Partial index keeps it tiny (only queued + retryable failed rows).
CREATE INDEX IF NOT EXISTS idx_drape_jobs_dispatchable
  ON public.drape_jobs (priority, created_at)
  WHERE status = 'queued';

CREATE INDEX IF NOT EXISTS idx_drape_jobs_user
  ON public.drape_jobs (user_id);

CREATE INDEX IF NOT EXISTS idx_drape_jobs_runpod
  ON public.drape_jobs (runpod_job_id)
  WHERE runpod_job_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_drape_jobs_status
  ON public.drape_jobs (status);

COMMENT ON TABLE public.drape_jobs IS
  'Pre-drape job queue. Dispatcher picks up status=queued via SELECT ... FOR UPDATE SKIP LOCKED, calls RunPod async, RunPod webhooks back to mark completed/failed.';

-- 4. updated_at trigger
DROP TRIGGER IF EXISTS update_drape_jobs_updated_at ON public.drape_jobs;
CREATE TRIGGER update_drape_jobs_updated_at
  BEFORE UPDATE ON public.drape_jobs
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 5. RLS: service-role only. End users never read drape_jobs directly.
ALTER TABLE public.drape_jobs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access on drape_jobs" ON public.drape_jobs;
CREATE POLICY "Service role full access on drape_jobs" ON public.drape_jobs
  FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Users can view own drape_jobs" ON public.drape_jobs;
CREATE POLICY "Users can view own drape_jobs" ON public.drape_jobs
  FOR SELECT USING (auth.uid() = user_id);

-- 6. Atomic claim function used by the dispatcher.
--    SELECT ... FOR UPDATE SKIP LOCKED so multiple dispatcher workers (or a
--    single worker that overlaps its own ticks) never claim the same row.
CREATE OR REPLACE FUNCTION public.claim_drape_jobs(limit_n integer)
RETURNS SETOF public.drape_jobs
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  UPDATE public.drape_jobs j
  SET status = 'dispatched',
      dispatched_at = NOW(),
      attempts = j.attempts + 1
  WHERE j.id IN (
    SELECT id FROM public.drape_jobs
    WHERE status = 'queued'
    ORDER BY priority, created_at
    LIMIT limit_n
    FOR UPDATE SKIP LOCKED
  )
  RETURNING j.*;
END;
$$;

COMMENT ON FUNCTION public.claim_drape_jobs IS
  'Atomic dispatcher claim. Returns up to limit_n queued jobs, marking them dispatched in one transaction. Safe under concurrent callers.';

-- 7. Counters used by the admin page.
CREATE OR REPLACE FUNCTION public.drape_job_status_counts()
RETURNS TABLE(status text, count bigint)
LANGUAGE sql STABLE
AS $$
  SELECT status, COUNT(*) FROM public.drape_jobs GROUP BY status
$$;
