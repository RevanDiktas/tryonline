import { NextRequest, NextResponse } from 'next/server';

/**
 * Minimal same-origin endpoint used only to prove that a Shopify session token
 * can be acquired in the embedded app and sent as Authorization: Bearer <token>.
 */
export async function POST(request: NextRequest) {
  const auth = request.headers.get('authorization') || '';
  const hasBearer = auth.toLowerCase().startsWith('bearer ') && auth.length > 10;
  return NextResponse.json({ ok: true, has_bearer: hasBearer }, { status: 200 });
}
