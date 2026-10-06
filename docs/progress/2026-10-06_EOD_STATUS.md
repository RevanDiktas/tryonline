# 2026-10-06 end of day

Everything below is live: feature/analytics, Vercel + Railway, and the La Fam, Ramin and public
Shopify apps. Each item was checked on the live site.

## Shipped today

- **Two buttons, one block** (cea6464). Products with a 3D garment show **Try On**: an avatar
  straight away for measured shoppers. Every other product with sizes shows **Find my size**.
  New fast endpoint `GET /api/products/tryon-handles`.
- **Size card rebuilt as a quiz** (41e56b1, 7256778, e0f95c8, 843111c).
  - No account wall: seven questions, then an estimated size.
  - The result shows Add to cart, plus Try On (3D products) or Create my fit passport.
  - Every size is scored as a 0-100 "% match": the chance it fits, averaged over the
    measurement's uncertainty. The top score is always the recommended size; checks are in
    `frontend/scripts/check_size_estimator.mjs`.
  - A sold-out best size moves the card to the best size in stock.
  - iOS-style sheet with round line-art body figures (style A, Revan approved).
  - Answers are also stored on the store's own site, so Safari remembers them.
- **Cart updates instantly on La Fam** (6d5a970). The Baseline theme only refreshes on
  `baseline:modalcart:afteradditem`.
- **Size Finder analytics** (e24be46): six new event types, `GET /api/analytics/size-finder`, and
  a Size Finder tab on the brand dashboard. Also fixed: `tryon_sessions` updates were rejected
  by the DB check, so the 114 old rows were never backfilled. That backfill is Revan's call.
- **Fake size chart removed**: the backend no longer invents one for products without a chart.
- **Website relaunch** (1af0be5, 44536e9, 0e98636).
  - Copy leads with size ("Your size in 30 seconds").
  - New `/product` page, with the real card running live in a phone frame.
  - `/demo` now has a Find my size product.
  - `/start` lead form, saved to the Supabase table `brand_leads`. Revan sends install links by
    hand; there is no alert yet, so check the table.
  - The home page uses sourced industry stats instead of the Ramin pilot numbers.
  - SEO: titles, canonicals, sitemap, robots, OG image.
  - One shared nav and footer.
- **Pricing** (`frontend/lib/plans.ts`):

  | Plan | Price | Includes |
  |---|---|---|
  | Size Pro | $29 | Find my size only |
  | Try-On | $109 | 40 garments in 3D |
  | Scale | $279 | 200 garments |
  | Brand | $2,490 + $1,500 setup | 400+ garments |

  No free tier; every plan has a 30-day trial. Try-ons and avatars are never limited.

## Tomorrow: Phase 2, self-serve brands and the App Store

Plan: `docs/plans/2026-10-06_SELF_SERVE_AND_APP_STORE.md`. Steps, in order:

1. One login via Shopify session tokens and token exchange.
2. Billing through Managed Pricing, with the four plans above.
3. Guided theme setup.
4. Compliance: GDPR deletion, CSP, uninstall, JS assets under 10 KB.
5. Listing, then submit using the shopify-app-review-prep checklist.

Needed from Revan first:

- The last reviewer email (after the 2026-05-09 resubmit).
- A decision on the protected-customer-data request for orders/refunds on the public app.

## Open, not urgent

- The $29 plan: Revan mentioned "1,000"; it was read as no limits.
- `pitch-deck.html` still shows the Ramin "94%" pilot stat.
- Drape skin-through fix (sleeves), from the 2026-10-06 start note.
- Testing gotcha: headless Playwright with a phone viewport drops taps into cross-site iframes
  near the bottom of the screen. Launch with
  `--disable-site-isolation-trials --disable-features=IsolateOrigins,site-per-process`.
