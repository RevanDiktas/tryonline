-- =============================================
-- Migration 003: Cloth Draping Support
-- Adds OBJ mesh storage, fabric config, and draped mesh caching
-- =============================================

-- 1. Add OBJ sizes + fabric config columns to garments table
ALTER TABLE public.garments
ADD COLUMN IF NOT EXISTS obj_sizes JSONB DEFAULT '{}';

ALTER TABLE public.garments
ADD COLUMN IF NOT EXISTS fabric_config JSONB DEFAULT '{}';

COMMENT ON COLUMN public.garments.obj_sizes IS 'Per-size OBJ mesh paths: {"m": "garments/brand_id/product_id/m.obj", ...}';
COMMENT ON COLUMN public.garments.fabric_config IS 'Fabric material properties: {"stretch_compliance": 0.001, "bend_compliance": 0.01, "thickness": 0.003, "density": 0.3, "preset": "cotton_medium"}';

-- 2. Create draped_meshes cache table
CREATE TABLE IF NOT EXISTS public.draped_meshes (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  garment_id UUID REFERENCES public.garments(id) ON DELETE CASCADE NOT NULL,
  size TEXT NOT NULL,
  body_hash TEXT NOT NULL,

  draped_glb_url TEXT NOT NULL,
  draped_obj_url TEXT,

  simulation_method TEXT DEFAULT 'geometric_fallback',
  processing_time_seconds NUMERIC(6,2),
  vertex_count INTEGER,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '90 days')
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_draped_meshes_unique
  ON public.draped_meshes (garment_id, size, body_hash);

CREATE INDEX IF NOT EXISTS idx_draped_meshes_garment
  ON public.draped_meshes (garment_id);

CREATE INDEX IF NOT EXISTS idx_draped_meshes_body_hash
  ON public.draped_meshes (body_hash);

CREATE INDEX IF NOT EXISTS idx_draped_meshes_expires
  ON public.draped_meshes (expires_at);

COMMENT ON TABLE public.draped_meshes IS 'Cache of draped garment meshes per body shape + garment + size combination';

-- 3. Create draping_requests table for async job tracking
CREATE TABLE IF NOT EXISTS public.draping_requests (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
  garment_id UUID REFERENCES public.garments(id) ON DELETE CASCADE NOT NULL,
  size TEXT NOT NULL,
  body_hash TEXT NOT NULL,

  status TEXT CHECK (status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
  runpod_job_id TEXT,

  draped_mesh_id UUID REFERENCES public.draped_meshes(id) ON DELETE SET NULL,
  error_message TEXT,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_draping_requests_status
  ON public.draping_requests (status);

CREATE INDEX IF NOT EXISTS idx_draping_requests_user
  ON public.draping_requests (user_id);

CREATE INDEX IF NOT EXISTS idx_draping_requests_garment
  ON public.draping_requests (garment_id, size, body_hash);

-- 4. Trigger for updated_at on draping_requests
DROP TRIGGER IF EXISTS update_draping_requests_updated_at ON public.draping_requests;
CREATE TRIGGER update_draping_requests_updated_at
  BEFORE UPDATE ON public.draping_requests
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 5. RLS policies (service role bypasses RLS, but add basic policies)
ALTER TABLE public.draped_meshes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.draping_requests ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access on draped_meshes" ON public.draped_meshes;
CREATE POLICY "Service role full access on draped_meshes" ON public.draped_meshes
  FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Users can view own draping_requests" ON public.draping_requests;
CREATE POLICY "Users can view own draping_requests" ON public.draping_requests
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role full access on draping_requests" ON public.draping_requests;
CREATE POLICY "Service role full access on draping_requests" ON public.draping_requests
  FOR ALL USING (true) WITH CHECK (true);
