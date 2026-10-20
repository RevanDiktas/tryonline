# 2026-10-20 end of day

Two pre-Lisbon deliverables: a shopper MCP server, and TryOn Size (Find my size as its own
Shopify app). The MCP is live and works in Claude and ChatGPT. TryOn Size is built and released to
Shopify, but its backend is waiting on a Railway outage.

## Shipped: TryOn MCP (live, verified by Revan in Claude and ChatGPT)

`https://tryon.global/mcp` (feature/analytics 0b5b527 → 4a13720). A shopper links their TryOn
account once (Claude: Settings → Connectors → custom; ChatGPT: chatgpt.com/plugins → Add custom
MCP server). After that, the assistant gives them their size for any Shopify product link, with
an in-chat size card.

- **Tools** (all annotated):
  - `find_products`: store, collection or domain → product links.
  - `recommend_size`: product link → size, % per size, stock, reason, plus the card.
  - `get_my_fit_passport`.
  - `save_my_size_profile`: the 7 quiz answers given in the chat.
  - `save_to_wishlist`.
- **Same answers as the store card**: it imports `public/sizing-engine.js` and
  `public/size-estimator.js` and makes the card's calls.
- **Auth**: Supabase Auth's OAuth 2.1 server, with dynamic registration turned on in the
  dashboard. The consent page is `/oauth/consent`. Tokens must verify against Supabase's ES256
  key and carry `client_id`, so website session tokens are refused.
- **Card**: an MCP App (`lib/mcp/size-card.ts`) using a pinned MCP Apps client served from
  `tryon.global/mcp-assets`. No iframe.
- **Tests**: end-to-end with a fake JWKS and backend, the real La Fam storefront and the official
  MCP client. All pass.

**Learned today (each one cost a fix):**
- Supabase sends the client's plain `redirect_uri` with every authorization request, not only
  after consent. Only skip the consent screen when it carries `?code=`.
- A Supabase authorization belongs to the first account that opens it. "Not you?" now declines the
  request, signs out and sends the shopper back to reconnect.
- Supabase sends the app name as `client.name`, but the auth-js types say `client_name`.
- `withMcpAuth({ resourceUrl })` wants the origin (`https://tryon.global`), not the `/mcp` URL.
- ChatGPT won't use a tool unprompted unless told when it applies, so we send server
  `instructions`. It also needs `find_products`: unlike Claude, it doesn't web-search for product
  pages.
- Shopify throttles `/products.json` per IP (429, 60 s). `/search/suggest.json` holds up, so we
  search first and cache for 2 minutes.
- Prices dropped: Vercel's US IP gets USD from Shopify Markets while the store says EUR (€110 came
  back as "127 EUR").
- A sold-out best size only names an in-stock size that scores at least 30%.

## Built and released to Shopify: TryOn Size (NOT live yet: Railway outage)

A separate app with only the Find my size block. $19/month, 30-day trial, unlimited, no Admin API
scopes. Code: `shopify_size_app/`, `backend/app/api/routes/size_app.py`,
`frontend/app/size-app/route.ts`, migration `009_size_app_installs` (applied).

**Done today:**
- Dev Dashboard app **TryOn Size** created:
  - client_id `4a902807121d5f2b63a81c31bbf91429`
  - org RDD handel
  - secret in Railway variable `SHOPIFY_CLIENT_SECRET_SIZE`
- Dev store **tryon-size-demo**: Basic plan, test data, and 3 products from
  `~/Downloads/tryon-size-demo-products.csv`, with XL and 30 sold out.
- Code pushed (830c83c). Vercel is live: `app.tryon.global/size-app` returns 200.
- Shopify config and block released as **tryon-size-3** via
  `cd shopify_size_app && PATH=$HOME/.nvm/versions/node/v20.20.0/bin:$PATH bash deploy.sh`.
  The block uid is in the repo. The first attempt hit `ECONNRESET`; just retry.
- Cross-store leak fixed: tryon-config for a shop with no brand no longer searches every brand's
  garments. Checked against the live database: no live store is affected.
- Website: Size Pro is $19.

**Blocked:** Railway had a platform-wide build outage ("Major Outage", builds paused for all
workspaces). The backend is still on `6b911f4`, without the size-app routes or the new secret.
Railway says triggers must be **resubmitted** once builds resume.

## Next session, in order

1. **Railway:** heroic-celebration → ⋮ on the top deployment → **Redeploy** (or "Deploy latest
   commit"). Check that `/version` reports 830c83c and that `POST /api/size-app/session` returns
   401, not 404.
2. **Install TryOn Size on tryon-size-demo.**
   - Expect: the admin page loads, the plan step shows "To do", and the theme-editor link adds the
     block.
   - Check the `size_app_installs` row and the `tryon_size.active` metafield after choosing a plan.
3. **Partner dashboard:**
   - Public distribution, then Managed Pricing: one plan, $19 every 30 days, 30-day trial.
   - Set `SHOPIFY_APP_HANDLE_SIZE` if the handle isn't `tryon-size`.
4. **Dev Dashboard → Contactgegevens:** replace the Apple private-relay email with a real one.
5. **Review checklist** (the shopify-app-review-prep skill), then the listing and submit.
   - Storefront screenshots from La Fam, with their OK. Admin screenshots from the dev store.
   - The old public **Tryon** listing shows "Gepauzeerd" (paused). Find the reviewer email before
     submitting.
6. **Decide:** give the store size card the same ≥30% sold-out rule? It currently offers e.g. XL at
   1% as "next best".

## After Web Summit

- MCP directory listings: Claude needs a Team or Enterprise org; ChatGPT review takes 60 to 120
  days.
- Audience-bind MCP tokens (RFC 8707) with a Supabase custom access token hook.
- Next 14.0.4 security upgrade.
- Clean up the duplicate "Claude" OAuth clients from today's tests (they're cosmetic).
