import { createServerClient } from '@supabase/auth-helpers-nextjs';
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

/**
 * GET /auth/me - returns current user from session (cookie).
 * Used by the widget to avoid showing login gate when user is already signed in (session memory).
 */
export async function GET() {
  try {
    const cookieStore = cookies();
    const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
      },
    });
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.user?.id) {
      return NextResponse.json({ user_id: null }, { status: 401 });
    }
    const meta = session.user.user_metadata as { name?: string; full_name?: string } | undefined;
    const name = meta?.full_name || meta?.name || session.user.email?.split('@')[0] || 'User';
    return NextResponse.json({ user_id: session.user.id, name });
  } catch (e) {
    console.error('[auth/me]', e);
    return NextResponse.json({ user_id: null }, { status: 500 });
  }
}
