import { NextResponse } from 'next/server';

/**
 * GET /widget-config - returns backend URL for the embed so the widget can
 * fallback to a direct request when the same-origin rewrite fails (e.g. deploy cache).
 */
export async function GET() {
  const backendUrl = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '');
  return NextResponse.json({ backendUrl });
}
