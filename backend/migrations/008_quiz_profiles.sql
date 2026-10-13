-- 008: the size quiz saved to an account
--
-- The "Find my size" card asks seven questions and estimates a size. A shopper who makes an
-- account keeps those answers here, so every store that uses Tryon can show their estimated
-- size without asking again. This is NOT a measurement: fit_passports stays the home of what
-- a photo measured (status = completed), and a completed fit passport always wins over this.
--
--   profile   what the shopper answered: gender, height (cm), weight (kg), age, ageBand,
--             shape { chest|belly|hips: -1|0|1 }, units, fit
--   estimate  the body the answers imply (chest, waist, hips in cm), for reporting only;
--             the card always recomputes from `profile`
--
-- Written and read through the backend (service role) only, so RLS is on with no policies:
-- nobody can read or write this table with the anon key.
--
-- Apply with: psql or Supabase SQL editor. Idempotent.

CREATE TABLE IF NOT EXISTS quiz_profiles (
  user_id    uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  profile    jsonb NOT NULL,
  estimate   jsonb,
  shop_domain text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE quiz_profiles ENABLE ROW LEVEL SECURITY;
