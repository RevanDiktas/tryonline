import { createServerClient } from '@supabase/auth-helpers-nextjs';
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

/**
 * GET /auth/me — returns current user from session (cookie).
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
    return NextResponse.json({ user_id: session.user.id });
  } catch (e) {
    console.error('[auth/me]', e);
    return NextResponse.json({ user_id: null }, { status: 500 });
  }
}
