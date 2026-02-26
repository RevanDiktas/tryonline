/**
 * Supabase auth and user/fit-passport helpers for the frontend.
 * Uses NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.
 *
 * We use createClient (localStorage-based) instead of createBrowserClient
 * (cookie-based) because the app runs inside Shopify admin as a third-party
 * iframe where browsers block third-party cookies.
 */
import { createClient, type User as SupabaseAuthUser } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

const supabase = createClient(supabaseUrl, supabaseAnonKey);

export interface User {
  id: string;
  email: string;
  name?: string;
  phone?: string;
  user_type?: string;
  created_at?: string;
}

export interface FitPassport {
  id: string;
  user_id: string;
  height: number;
  weight?: number;
  gender: string;
  avatar_url?: string | null;
  avatarUrl?: string | null;
  status?: string;
  preferred_fit?: string;
  chest?: number | null;
  waist?: number | null;
  hips?: number | null;
  inseam?: number | null;
  shoulder_width?: number | null;
  arm_length?: number | null;
  neck?: number | null;
  thigh?: number | null;
  torso_length?: number | null;
  pipeline_files?: Record<string, string> | null;
  created_at?: string;
  updated_at?: string;
}

function authUserToUser(a: SupabaseAuthUser): User {
  return {
    id: a.id,
    email: a.email ?? '',
    name: (a.user_metadata as { name?: string })?.name,
  };
}

export async function getCurrentUser(): Promise<User | null> {
  const { data: { session } } = await supabase.auth.getSession();
  if (!session?.user) return null;
  const { data: profile } = await supabase
    .from('users')
    .select('id, email, name, phone, user_type, created_at')
    .eq('id', session.user.id)
    .single();
  if (profile) {
    return { id: profile.id, email: profile.email, name: profile.name, phone: profile.phone, user_type: profile.user_type, created_at: profile.created_at };
  }
  const u = authUserToUser(session.user);
  const authCreated = (session.user as { created_at?: string }).created_at;
  return authCreated ? { ...u, created_at: authCreated } : u;
}

export async function login(email: string, password: string): Promise<{ user: User | null; error: string | null }> {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) return { user: null, error: error.message };
  if (!data.user) return { user: null, error: 'No user' };

  // Try getting the full profile from the users table
  const user = await getCurrentUser();
  if (user) return { user, error: null };

  // Fallback: session might not be available yet (e.g. in iframe with cookie restrictions).
  // Use the auth data directly + try to read the profile with the signed-in client.
  const { data: profile } = await supabase
    .from('users')
    .select('id, email, name, phone, user_type, created_at')
    .eq('id', data.user.id)
    .single();

  if (profile) {
    return { user: { id: profile.id, email: profile.email, name: profile.name, phone: profile.phone, user_type: profile.user_type, created_at: profile.created_at }, error: null };
  }

  // Last resort: construct user from auth metadata
  const meta = data.user.user_metadata as { name?: string; user_type?: string } | undefined;
  return {
    user: {
      id: data.user.id,
      email: data.user.email ?? email,
      name: meta?.name,
      user_type: meta?.user_type ?? 'shopper',
    },
    error: null,
  };
}

export interface SignupOptions {
  email: string;
  password: string;
  name?: string;
  phone?: string;
  dateOfBirth?: string;
  country?: string;
  city?: string;
  userType?: string;
}

export async function signup(options: SignupOptions): Promise<{ user: User | null; error: string | null }> {
  const { data: authData, error: authError } = await supabase.auth.signUp({
    email: options.email,
    password: options.password,
    options: {
      data: {
        name: options.name,
        phone: options.phone,
        country: options.country,
        city: options.city,
        user_type: options.userType ?? 'shopper',
      },
    },
  });
  if (authError) return { user: null, error: authError.message };
  if (!authData.user) return { user: null, error: 'This email may already be registered. Try signing in instead.' };

  const profileData = {
    id: authData.user.id,
    email: authData.user.email!,
    name: options.name ?? authData.user.email?.split('@')[0] ?? 'User',
    phone: options.phone ?? null,
    user_type: options.userType ?? 'shopper',
    updated_at: new Date().toISOString(),
  };

  // Try INSERT first; if row already exists (e.g. from a DB trigger), fall back to UPDATE.
  // Avoids PostgREST 406 issues with UPSERT on tables with multiple unique constraints.
  const { error: insertErr } = await supabase.from('users').insert(profileData);
  if (insertErr) {
    await supabase.from('users').update({
      name: profileData.name,
      phone: profileData.phone,
      user_type: profileData.user_type,
      updated_at: profileData.updated_at,
    }).eq('id', authData.user.id);
  }

  const user = await getCurrentUser();
  return { user, error: null };
}

export async function logout(): Promise<void> {
  await supabase.auth.signOut();
}

export async function hasFitPassport(userId: string): Promise<boolean> {
  const { data } = await supabase.from('fit_passports').select('id, avatar_url, status').eq('user_id', userId).single();
  return !!(data && (data.avatar_url || data.status === 'completed'));
}

export async function getFitPassport(userId: string): Promise<FitPassport | null> {
  const { data, error } = await supabase.from('fit_passports').select('*').eq('user_id', userId).single();
  if (error || !data) return null;
  return {
    ...data,
    avatarUrl: data.avatar_url,
  } as FitPassport;
}

export async function createFitPassport(
  userId: string,
  height: number,
  gender: string,
  weight?: number
): Promise<void> {
  await supabase.from('fit_passports').upsert({
    user_id: userId,
    height,
    gender,
    weight: weight ?? null,
    status: 'pending',
    updated_at: new Date().toISOString(),
  }, { onConflict: 'user_id' });
}

export async function updateFitPassport(
  userId: string,
  updates: {
    preferredFit?: string;
    avatarUrl?: string;
    measurements?: Record<string, number>;
    [key: string]: unknown;
  }
): Promise<FitPassport | null> {
  const payload: Record<string, unknown> = { updated_at: new Date().toISOString() };
  if (updates.preferredFit !== undefined) payload.preferred_fit = updates.preferredFit;
  if (updates.avatarUrl !== undefined) payload.avatar_url = updates.avatarUrl;
  if (updates.measurements) {
    Object.assign(payload, updates.measurements);
  }
  const { data, error } = await supabase
    .from('fit_passports')
    .update(payload)
    .eq('user_id', userId)
    .select()
    .single();
  if (error) return null;
  return data ? { ...data, avatarUrl: data.avatar_url } as FitPassport : null;
}

export async function uploadUserPhoto(
  userId: string,
  file: File,
  _photoType?: string
): Promise<{ url: string | null; error: string | null }> {
  const path = `${userId}/${file.name}`;
  const { data, error } = await supabase.storage.from('photos').upload(path, file, { upsert: true });
  if (error) return { url: null, error: error.message };
  const { data: urlData } = supabase.storage.from('photos').getPublicUrl(data.path);
  return { url: urlData.publicUrl, error: null };
}

export async function saveUserPhoto(userId: string, photoUrl: string): Promise<void> {
  await supabase.from('user_photos').insert({
    user_id: userId,
    photo_url: photoUrl,
    photo_type: 'front',
  });
}

export async function hasAvatarFiles(userId: string): Promise<boolean> {
  const fp = await getFitPassport(userId);
  return !!(fp && (fp.avatar_url || fp.avatarUrl || (fp.pipeline_files && Object.keys(fp.pipeline_files).length > 0)));
}
