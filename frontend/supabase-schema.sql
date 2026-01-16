-- =============================================
-- TRYON - Complete Database Schema for Supabase
-- Run this in Supabase SQL Editor
-- =============================================

-- =============================================
-- 1. USERS TABLE (extends Supabase auth.users)
-- =============================================
CREATE TABLE IF NOT EXISTS public.users (
  id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  phone TEXT,
  date_of_birth DATE,
  country TEXT,
  city TEXT,
  user_type TEXT CHECK (user_type IN ('shopper', 'brand')) NOT NULL DEFAULT 'shopper',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- 2. FIT PASSPORTS TABLE (Body measurements + Avatar)
-- =============================================
CREATE TABLE IF NOT EXISTS public.fit_passports (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES public.users(id) ON DELETE CASCADE UNIQUE NOT NULL,
  
  -- Basic Info
  height INTEGER NOT NULL, -- in cm
  weight INTEGER, -- in kg (optional)
  gender TEXT CHECK (gender IN ('male', 'female', 'other')) NOT NULL,
  
  -- Avatar
  avatar_url TEXT, -- URL to the GLB/OBJ file in storage
  avatar_thumbnail_url TEXT, -- Preview image
  pipeline_files JSONB, -- All pipeline output file URLs: {"avatar_glb": "url", "face_crop": "url", ...}
  
  -- Body Measurements (all in cm)
  chest INTEGER,
  waist INTEGER,
  hips INTEGER,
  inseam INTEGER,
  shoulder_width INTEGER,
  arm_length INTEGER,
  neck INTEGER,
  thigh INTEGER,
  torso_length INTEGER,
  
  -- Fit Preferences
  preferred_fit TEXT CHECK (preferred_fit IN ('slim', 'regular', 'loose')) DEFAULT 'regular',
  
  -- Processing Status
  status TEXT CHECK (status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
  processing_started_at TIMESTAMP WITH TIME ZONE,
  processing_completed_at TIMESTAMP WITH TIME ZONE,
  
  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add pipeline_files column if table already exists (migration for existing databases)
ALTER TABLE public.fit_passports
ADD COLUMN IF NOT EXISTS pipeline_files JSONB;

-- =============================================
-- 3. USER PHOTOS TABLE (Original uploads)
-- =============================================
CREATE TABLE IF NOT EXISTS public.user_photos (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
  fit_passport_id UUID REFERENCES public.fit_passports(id) ON DELETE CASCADE,
  
  photo_url TEXT NOT NULL, -- URL in storage bucket
  photo_type TEXT CHECK (photo_type IN ('front', 'side', 'back')) DEFAULT 'front',
  
  -- We delete photos after processing for privacy
  is_processed BOOLEAN DEFAULT FALSE,
  delete_after_processing BOOLEAN DEFAULT TRUE,
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- 4. TRYON SESSIONS TABLE (Analytics & Tracking)
-- =============================================
CREATE TABLE IF NOT EXISTS public.tryon_sessions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
  
  -- Session Info
  session_token TEXT UNIQUE NOT NULL,
  
  -- Product Info (from Shopify)
  shop_domain TEXT,
  product_id TEXT,
  product_name TEXT,
  variant_id TEXT,
  
  -- What happened
  sizes_viewed TEXT[], -- Array of sizes viewed: ['S', 'M', 'L']
  size_recommended TEXT, -- What we recommended
  size_selected TEXT, -- What user chose
  
  -- Actions
  action TEXT CHECK (action IN ('opened', 'viewed', 'tried_on', 'added_to_cart', 'purchased')),
  
  -- Attribution
  purchase_order_id TEXT, -- Shopify order ID if purchased
  purchase_amount DECIMAL(10, 2),
  
  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE
);

-- =============================================
-- 5. ANALYTICS EVENTS TABLE (Detailed event logging)
-- =============================================
CREATE TABLE IF NOT EXISTS public.analytics_events (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
  session_id UUID REFERENCES public.tryon_sessions(id) ON DELETE SET NULL,
  
  -- Event Details
  event_type TEXT NOT NULL, -- 'tryon_opened', 'avatar_created', 'size_viewed', etc.
  event_data JSONB, -- Additional event-specific data
  
  -- Context
  shop_domain TEXT,
  product_id TEXT,
  
  -- Device Info
  user_agent TEXT,
  ip_address INET,
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- 6. BRANDS TABLE (B2B - for future)
-- =============================================
CREATE TABLE IF NOT EXISTS public.brands (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  
  -- Brand Info
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  shopify_domain TEXT UNIQUE,
  
  -- Branding
  logo_url TEXT,
  primary_color TEXT DEFAULT '#000000',
  secondary_color TEXT DEFAULT '#ffffff',
  
  -- Plan
  plan_tier TEXT CHECK (plan_tier IN ('starter', 'pro', 'enterprise')) DEFAULT 'starter',
  monthly_avatar_limit INTEGER DEFAULT 500,
  
  -- Stripe
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  
  -- Status
  status TEXT CHECK (status IN ('active', 'inactive', 'suspended')) DEFAULT 'active',
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- 7. GARMENTS TABLE (CLO3D garments per brand)
-- =============================================
CREATE TABLE IF NOT EXISTS public.garments (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  brand_id UUID REFERENCES public.brands(id) ON DELETE CASCADE,
  
  -- Product Info
  name TEXT NOT NULL,
  category TEXT CHECK (category IN ('tops', 'bottoms', 'outerwear', 'dresses', 'accessories')),
  shopify_product_id TEXT,
  
  -- Garment Files (per size)
  sizes JSONB, -- {"XS": "url", "S": "url", "M": "url", "L": "url", "XL": "url"}
  
  -- Fit Metadata
  fit_type TEXT CHECK (fit_type IN ('slim', 'regular', 'oversized')) DEFAULT 'regular',
  
  -- Size Chart (measurements in cm)
  size_chart JSONB, -- {"XS": {"chest": 86, "length": 65}, "S": {...}, ...}
  
  thumbnail_url TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- INDEXES for faster queries
-- =============================================
CREATE INDEX IF NOT EXISTS idx_fit_passports_user_id ON public.fit_passports(user_id);
CREATE INDEX IF NOT EXISTS idx_fit_passports_pipeline_files ON public.fit_passports USING GIN (pipeline_files);
CREATE INDEX IF NOT EXISTS idx_user_photos_user_id ON public.user_photos(user_id);
CREATE INDEX IF NOT EXISTS idx_tryon_sessions_user_id ON public.tryon_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_tryon_sessions_shop ON public.tryon_sessions(shop_domain);
CREATE INDEX IF NOT EXISTS idx_analytics_events_user_id ON public.analytics_events(user_id);
CREATE INDEX IF NOT EXISTS idx_analytics_events_type ON public.analytics_events(event_type);
CREATE INDEX IF NOT EXISTS idx_garments_brand_id ON public.garments(brand_id);

-- =============================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fit_passports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_photos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tryon_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_events ENABLE ROW LEVEL SECURITY;

-- Users: can only access own data
CREATE POLICY "Users can view own profile" ON public.users
  FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON public.users
  FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Users can insert own profile" ON public.users
  FOR INSERT WITH CHECK (auth.uid() = id);

-- Fit Passports: can only access own passport
CREATE POLICY "Users can view own fit passport" ON public.fit_passports
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update own fit passport" ON public.fit_passports
  FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own fit passport" ON public.fit_passports
  FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can delete own fit passport" ON public.fit_passports
  FOR DELETE USING (auth.uid() = user_id);

-- User Photos: can only access own photos
CREATE POLICY "Users can view own photos" ON public.user_photos
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own photos" ON public.user_photos
  FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can delete own photos" ON public.user_photos
  FOR DELETE USING (auth.uid() = user_id);

-- TryOn Sessions: can only access own sessions
CREATE POLICY "Users can view own sessions" ON public.tryon_sessions
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own sessions" ON public.tryon_sessions
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Analytics Events: can only access own events
CREATE POLICY "Users can view own events" ON public.analytics_events
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own events" ON public.analytics_events
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- =============================================
-- STORAGE BUCKETS (run separately in Storage settings)
-- =============================================
-- Create these buckets in Supabase Dashboard > Storage:
-- 1. "avatars" - For storing avatar GLB/OBJ files (public)
-- 2. "photos" - For user uploaded photos (private, delete after processing)
-- 3. "garments" - For CLO3D garment files (public)
-- 4. "brand-assets" - For brand logos etc (public)

-- =============================================
-- FUNCTIONS
-- =============================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at
  BEFORE UPDATE ON public.users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fit_passports_updated_at
  BEFORE UPDATE ON public.fit_passports
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_brands_updated_at
  BEFORE UPDATE ON public.brands
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_garments_updated_at
  BEFORE UPDATE ON public.garments
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
