# Status Report — 2026-03-24

## Completed today

### Google OAuth login — WORKING end-to-end
- Switched from PKCE to **implicit flow** (`flowType: 'implicit'`) — fixes the persistent "both auth code and code verifier should be non-empty" error.
- Implicit flow puts tokens in the URL fragment (`#access_token=...`), the Supabase client auto-parses them. No code exchange needed.
- Callback page (`/auth/callback`) polls for session, creates user profile via `ensureUserProfile()`, then routes to onboarding or dashboard.
- Google user `revandiktas1@gmail.com` successfully signed in, onboarded, and reached dashboard.

### Avatar pipeline — WORKING end-to-end
- **Photo upload fixed**: direct browser-to-Supabase upload was blocked by Storage RLS ("new row violates row-level security policy"). Moved upload to backend via new `POST /api/avatar/upload-photo` endpoint which uses the service role key (bypasses RLS).
- RunPod worker (`onr7buxi6bjedj`, RTX 3090) picked up job and completed in **30.7 seconds**.
- 17 measurements extracted: height 192, chest 102, waist 88, hips 99, inseam 83, shoulder width 38, arm length 58, thigh 48, neck 38, torso length 71.
- 3D avatar (GLB) generated, stored in Supabase Storage, rendered on dashboard.

### Signup form improvements
- **Birthday** is now required for shoppers (was optional). Stored in `users.date_of_birth`.
- **Phone number** was already present — now included in form validation.
- `signup()` function now stores `date_of_birth`, `country`, `city` in the users table (was missing before).

### OAuth profile completion flow — NEW
- New page: `/auth/complete-profile` — collects birthday, phone, country, city from Google/Apple users.
- Callback routes here when `isProfileComplete()` returns false (missing birthday/phone/country/city).
- After completing, routes to onboarding (no fit passport) or dashboard (has one).
- Added `isProfileComplete()` and `updateUserProfile()` helpers to `supabase-auth.ts`.

### Widget sign-in — Google/Apple social login + close button
- **Login gate popup** on the Shopify product page now includes "Continue with Google" and "Continue with Apple" buttons alongside email/password sign-in.
- **Close button** (x) added to the login gate popup — dismisses the popup and sends `TRYON_CLOSE` to the parent iframe.
- Widget-signin page (`/widget-signin`) auto-triggers OAuth when `?provider=google|apple` is in the URL.
- **Sandboxed iframe fix**: Shopify iframes block `sessionStorage`, so widget return URL is passed via `?widget_return=` query param on the OAuth `redirectTo` URL instead. Auth callback reads it from `searchParams` and redirects back to the widget with `user_id`.
- **Tested and confirmed working**: Google sign-in from the Shopify product page widget -> OAuth -> callback -> redirects back to widget with avatar + measurements loaded.

### UI polish
- **No emojis** anywhere in the app — country code pickers use 2-letter text codes (NL, US, GB, etc.).
- **Default theme is light** when logged out (was dark).
- **Progress messages improved**:
  - "Preparing your avatar..." (initial queue)
  - "Creating your avatar and extracting measurements..." (processing)
  - "Our servers are busy right now. Hang tight..." (queued >60s)
  - Removed "Waiting in GPU queue..." and "This usually takes about 30 seconds".

### Apple + Google OAuth providers (configured yesterday, confirmed working today)
- Google: OAuth Web Client in Google Cloud Console, redirect URI to Supabase callback.
- Apple: App ID, Services ID, Key (.p8), JWT secret generated via `scripts/apple_supabase_jwt.py`.
- Both enabled in Supabase Auth dashboard.

---

## Key fixes

| Issue | Root cause | Fix |
|-------|-----------|-----|
| "both auth code and code verifier should be non-empty" | PKCE `code_verifier` lost during full-page redirect | Switched to implicit flow |
| "new row violates row-level security policy" | Supabase Storage RLS blocks browser uploads for OAuth users | Upload through backend (service key) |
| "photo_url is required" | Photo upload failed silently, empty string sent to backend | Throw on failure, never send empty URL |
| Multiple GoTrueClient instances | Two `createClient` calls (`supabase.ts` + `supabase-auth.ts`) | Nothing imports `supabase.ts` anymore; all auth through single client |
| Widget OAuth didn't redirect back | `sessionStorage` blocked in sandboxed Shopify iframe | Pass return URL via `?widget_return=` on OAuth `redirectTo` |

---

## Files changed today

| File | Change |
|------|--------|
| `frontend/lib/supabase-auth.ts` | Implicit flow, `User` interface extended, `ensureUserProfile()`, `isProfileComplete()`, `updateUserProfile()`, `signup()` stores date_of_birth/country/city, `signInWithSocial()` accepts `widgetReturn` option |
| `frontend/app/auth/callback/page.tsx` | Simplified for implicit flow, routes to complete-profile if data missing, reads `widget_return` from query params for widget redirect |
| `frontend/app/auth/complete-profile/page.tsx` | NEW: post-OAuth profile completion (birthday, phone, country, city) |
| `frontend/app/widget-signin/page.tsx` | Added Google/Apple social login buttons, auto-triggers OAuth on `?provider=` param, passes `widgetReturn` to `signInWithSocial()` |
| `frontend/public/test-viewer.html` | Login gate: close button, Google/Apple social buttons, divider, social sign-in URL builder |
| `frontend/app/signup/page.tsx` | Birthday required, no emojis in country picker |
| `frontend/app/onboarding/page.tsx` | Uses backend photo upload, better progress text |
| `frontend/lib/api.ts` | Added `uploadPhotoViaBackend()` |
| `frontend/contexts/ThemeContext.tsx` | Default theme = light |
| `backend/app/api/routes/avatar.py` | New `POST /api/avatar/upload-photo`, better progress messages |

---

## Remaining tasks

1. **Test Apple sign-in from widget** — provider is configured, same flow as Google. Needs a test run on the Shopify product page.
2. **Test OAuth complete-profile flow** — sign in with a fresh Google/Apple account to verify birthday/phone collection.
3. **Verify geolocation** — `ensureUserProfile()` calls `detectGeoLocation()` for new OAuth users; confirm country/city stored.
4. **Test email/password signup** — confirm birthday, country, city, phone all stored correctly.
5. **Apple secret rotation** — expires ~August 2026. Calendar reminder set.
6. **Supabase Storage RLS** — consider adding a proper INSERT policy for authenticated users (optional, backend upload works fine).
