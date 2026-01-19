import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

if (!supabaseUrl || !supabaseAnonKey) {
  console.error('[Supabase] Missing environment variables!');
  console.error('[Supabase] NEXT_PUBLIC_SUPABASE_URL:', supabaseUrl ? 'SET' : 'NOT SET');
  console.error('[Supabase] NEXT_PUBLIC_SUPABASE_ANON_KEY:', supabaseAnonKey ? 'SET' : 'NOT SET');
  console.error('[Supabase] Create .env.local file with these variables');
}

export const supabase = createClient(supabaseUrl || 'https://placeholder.supabase.co', supabaseAnonKey || 'placeholder-key');

// Database types
export interface DbUser {
  id: string;
  email: string;
  name: string;
  created_at: string;
}

export interface DbFitPassport {
  id: string;
  user_id: string;
  height: number;
  gender: 'male' | 'female' | 'other';
  avatar_url: string | null;
  chest: number | null;
  waist: number | null;
  hips: number | null;
  inseam: number | null;
  created_at: string;
  updated_at: string;
}
