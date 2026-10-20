/**
 * RFC 9728 Protected Resource Metadata for the TryOn MCP server: tells an MCP client that
 * https://tryon.global/mcp takes tokens from our Supabase Auth (OAuth 2.1 server). Served at
 * /.well-known/oauth-protected-resource/mcp (the RFC's path for a resource with a path) and at
 * the bare /.well-known/oauth-protected-resource for clients that try that first.
 */
import { protectedResourceHandler } from 'mcp-handler';
import { AUTH_ISSUER } from './auth';

export const resourceMetadata = protectedResourceHandler({
  authServerUrls: [AUTH_ISSUER],
  resourceUrl: 'https://tryon.global/mcp',
});

export function metadataOptions(): Response {
  return new Response(null, {
    status: 204,
    headers: { 'access-control-allow-origin': '*', 'access-control-allow-methods': 'GET, OPTIONS', 'access-control-allow-headers': '*' },
  });
}
