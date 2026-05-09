import { NextRequest, NextResponse } from 'next/server';

/**
 * Shopify-embedded app host. Requests on this host are restricted to the
 * brand-only surface (no pricing, no shopper UI). Anything outside the
 * allowlist returns 404 so reviewers cannot reach off-platform billing pages
 * or unrelated routes from inside the Shopify admin iframe.
 */
const SHOPIFY_HOST = 'app.tryon.global';

const ALLOWED_PATH_PREFIXES = [
  '/app',
  '/brand',
  '/onboarding',
  '/login',
  '/signup',
  '/api/',
  '/auth/',
];

const STATIC_ASSET_RE = /\.(png|jpg|jpeg|gif|svg|webp|ico|woff2?|ttf|otf|css|js|map|json|glb|gltf|obj|mtl|txt|xml)$/i;

function isAllowed(path: string): boolean {
  if (path === '/') return true;
  return ALLOWED_PATH_PREFIXES.some((p) =>
    p.endsWith('/') ? path.startsWith(p) : path === p || path.startsWith(p + '/'),
  );
}

export function middleware(req: NextRequest) {
  const host = (req.headers.get('host') || '').toLowerCase().split(':')[0];
  if (host !== SHOPIFY_HOST) {
    return NextResponse.next();
  }

  const path = req.nextUrl.pathname;

  if (STATIC_ASSET_RE.test(path)) {
    return NextResponse.next();
  }

  if (path === '/') {
    const url = req.nextUrl.clone();
    url.pathname = '/brand';
    return NextResponse.rewrite(url);
  }

  if (!isAllowed(path)) {
    return new NextResponse('Not Found', { status: 404 });
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon\\.ico|robots\\.txt).*)'],
};
