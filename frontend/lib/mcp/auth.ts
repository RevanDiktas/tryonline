/**
 * Access tokens for the TryOn MCP server. Supabase Auth is the authorization server (OAuth 2.1
 * server, dynamic client registration on); the shopper approves an AI app on /oauth/consent and
 * the app sends us the Supabase access token it got.
 *
 * Accepted only when:
 *   - signed by this Supabase project's key (JWKS, ES256), issuer = our auth URL, not expired
 *   - aud = "authenticated" (a signed-in user, not an anon or service key)
 *   - it carries client_id: it was issued to an OAuth client through the consent screen. A
 *     website session token has no client_id, so one copied out of a browser is refused here.
 *
 * Known gap (post Web Summit): the spec wants the audience bound to this server
 * (RFC 8707). Supabase tokens say aud "authenticated" for every client. Binding it needs a
 * custom access token hook on the project, which touches every sign-in, so it waits.
 */
import { createRemoteJWKSet, jwtVerify } from 'jose';

const SUPABASE_URL = (process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://cykwthsbrylonconqlfz.supabase.co').replace(/\/+$/, '');
export const AUTH_ISSUER = `${SUPABASE_URL}/auth/v1`;
const JWKS = createRemoteJWKSet(new URL(`${AUTH_ISSUER}/.well-known/jwks.json`));

export interface McpAuthInfo {
  token: string;
  clientId: string;
  scopes: string[];
  expiresAt?: number;
  extra: { userId: string; email?: string };
}

export async function verifyAccessToken(token: string | undefined): Promise<McpAuthInfo | undefined> {
  if (!token) return undefined;
  try {
    const { payload } = await jwtVerify(token, JWKS, {
      issuer: AUTH_ISSUER,
      audience: 'authenticated',
      algorithms: ['ES256', 'RS256'],
    });
    const clientId = typeof payload.client_id === 'string' ? payload.client_id : '';
    const userId = typeof payload.sub === 'string' ? payload.sub : '';
    if (!clientId || !userId || payload.role !== 'authenticated') return undefined;
    return {
      token,
      clientId,
      scopes: typeof payload.scope === 'string' ? payload.scope.split(' ').filter(Boolean) : [],
      expiresAt: payload.exp,
      extra: { userId, email: typeof payload.email === 'string' ? payload.email : undefined },
    };
  } catch {
    return undefined;
  }
}
