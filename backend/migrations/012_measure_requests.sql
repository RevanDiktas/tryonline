-- 012: body measurements from photos for partners, no shopper account (/api/measure)
--
-- A made-to-measure partner (first: Brave Particle) sends a front photo and an optional
-- side photo with a height; each photo runs on the avatar GPU endpoint and the row keeps
-- what came back, so the partner's own tape measurements can be compared against it.
--
--   partner        who the API key belongs to (the name in MEASURE_API_KEYS)
--   label          free text from the partner (tester name, order reference)
--   views          per photo: {front: {...}, side: {...}} with photo_path, runpod_job_id,
--                  status, measurements (cm), error, queue_ms, gpu_ms, gpu, cost_usd, pipeline_s
--   measurements   the combined result in cm; `method` says how it was combined
--   files          storage paths (photos bucket, private) of the body meshes
--   actual         the partner's tape measurements in cm, same keys as measurements
--   gpu_ms         GPU milliseconds RunPod billed as execution time, all views together
--   gpu_cost_usd   what those jobs cost: run time plus idle tail, at each worker's GPU price
--
-- Written and read through the backend (service role) only, so RLS is on with no policies.
-- Apply with: psql or Supabase SQL editor. Idempotent.

CREATE TABLE IF NOT EXISTS measure_requests (
  id            uuid PRIMARY KEY,
  partner       text NOT NULL,
  label         text,
  height_cm     numeric NOT NULL,
  weight_kg     numeric,
  gender        text NOT NULL,
  status        text NOT NULL DEFAULT 'processing',
  views         jsonb NOT NULL DEFAULT '{}'::jsonb,
  measurements  jsonb,
  method        text,
  files         jsonb NOT NULL DEFAULT '{}'::jsonb,
  actual        jsonb,
  actual_notes  text,
  error         text,
  gpu_ms        integer,
  gpu_cost_usd  numeric,
  created_at    timestamptz NOT NULL DEFAULT now(),
  completed_at  timestamptz,
  updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS measure_requests_partner_created_idx
  ON measure_requests (partner, created_at DESC);

ALTER TABLE measure_requests ENABLE ROW LEVEL SECURITY;
