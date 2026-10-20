/**
 * The OAuth consent page (/oauth/consent) keeps its authorization id here while Google / Apple
 * sign-in leaves the site; /auth/callback sends the shopper back to finish it. Kept for 15
 * minutes only, so an abandoned consent never hijacks a later, ordinary sign-in.
 */
const KEY = 'tryon_oauth_consent';
const TTL_MS = 15 * 60 * 1000;

export function rememberOAuthConsent(id: string): void {
  try { sessionStorage.setItem(KEY, JSON.stringify({ id, at: Date.now() })); } catch { /* storage blocked */ }
}

export function clearOAuthConsent(): void {
  try { sessionStorage.removeItem(KEY); } catch { /* storage blocked */ }
}

export function pendingOAuthConsentId(): string | null {
  try {
    const v = JSON.parse(sessionStorage.getItem(KEY) || 'null');
    if (v && typeof v.id === 'string' && typeof v.at === 'number' && Date.now() - v.at < TTL_MS) return v.id;
    clearOAuthConsent();
  } catch { /* storage blocked or bad value */ }
  return null;
}

/** The consent page to return to after a social sign-in, or null when none is pending. */
export function pendingOAuthConsentPath(): string | null {
  const id = pendingOAuthConsentId();
  return id ? `/oauth/consent?authorization_id=${encodeURIComponent(id)}` : null;
}
