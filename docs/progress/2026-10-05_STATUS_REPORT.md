# Status: 2026-10-05

Branch `claude/analytics-and-onboarding-part2`, cut from `feature/analytics` (`aebbb0d`).
Pull request: https://github.com/RevanDiktas/tryonline/pull/1 (base `feature/analytics`).
Not merged, not deployed. Written in a cloud session without access to the Mac, so
`feature/widget-onboarding` (`a69bc77`, local only) was not available: nothing here
touches `test-viewer.html`.

## WHERE THINGS STAND

- **Live store, unchanged.** Pressing Try On still sends a shopper without an avatar to
  tryon.global to sign up and onboard. In-widget onboarding is NOT live.
- **In-widget onboarding part 1.** Revan confirms it works (2026-10-05). It is still only
  on the Mac, on `feature/widget-onboarding`.
- **This branch.** Pushed and in PR #1. It changes the dashboard numbers and adds backend
  support for the widget; it does not change what the Try On button does.

**To get in-widget onboarding live.**
1. Push `feature/widget-onboarding` from the Mac.
2. Merge it into `feature/analytics` so Vercel serves the new widget.
3. Re-release the Shopify theme block only if that branch changed anything under
   `shopify_app`.

Email sign-up, photo and avatar build then run inside the card. Google and Apple sign-in
still open the popup until the session hand-off (see OPEN) is decided and built.

## DONE: analytics steps 2-4 (yesterday's NEXT UP item 3)

**One definition per metric** (`backend/app/services/analytics_cohort.py`). Every ROI
route builds the same `Cohort`, so a card, a chart and a table cannot disagree.

- **Try-on:** a widget session with a `tryon_started` in the range. Counted once.
- **Add to cart:** a try-on session that added to cart. Counted once.
- **Purchase:** a distinct Shopify order whose try-on session is in the cohort, paid
  within 30 days of that session's first try-on.
- **Return:** an order with at least one refund. Several refunds on one order are one.
- **Rates** divide like by like: sessions by sessions, orders by orders. No rate can
  pass 100%.
- **Baseline:** store orders in the range that never touched the widget.

**What changed on the dashboard.**
- `/time-series`, `/velocity`, `/device-metrics` and `/at-risk-products` counted every
  store order as a try-on purchase. They now count try-on orders only. For La Fam that
  moves "Purchases" in the trend table from the store's ~370 a month to 0, which is the
  true number: no La Fam order has a try-on session on it yet.
- Trend buckets add up to the cards above them (a session lives in the bucket of its
  first try-on).
- `/return-metrics` stays store-wide and is labelled "All store orders". Its return rate
  is now returned orders over orders placed in the range. La Fam, all time: 27 of 969
  (2.8%), not 57 refunds over 969 (5.9%): 30 of those refunds are for orders placed
  before tracking started on 2 August.
- Fit tab: "Selected" counts one choice per session (the size added to cart, else the
  last size picked), not every click. XL and XXL no longer share a rank.
- **Fake "Size Selected" funnel step removed** (`Charts.tsx`; it was the average of
  try-ons and add-to-carts).
- **Cohorts page on real data** (`/brand/cohorts`). The Ramin pilot numbers, the 1.78x
  headline and the McKinsey/Shopify/Coresight baselines are gone. It reads
  `/cohort-comparison`, `/metrics`, `/dwell-metrics` and `/metrics-by-product` for the
  brand's own last 30 days, and headlines a lift only once both sides have 20 orders.
- One event scan per range is shared by the cohort routes (60s cache), instead of one
  scan per card.

**Verified.** `scripts/check_analytics_cohort.py` (47 checks, new),
`check_analytics_ranges.py` (80) and `check_analytics_scoping.py` (76) pass. The new
definitions were recomputed in SQL against production, read-only: La Fam last 30 days =
53 opens, 36 try-ons, 9 add-to-carts, 0 try-on orders, 371 store orders. Both pages were
rendered in a browser against the real backend code over a generated store.

**Not done:** the real test order + refund on the Ramin store. It needs a person at a
checkout.

## DONE: onboarding part 2, backend half (NEXT UP item 2)

- **Gender "other".** Sent to the avatar pipeline as `neutral`; the passport keeps
  `other`. Fixes the live website onboarding failure.
- **Passport created server-side** in `/api/avatar/create`, and updated to what the
  avatar is built from. No profile row gives a 409 with a message instead of a job that
  runs for minutes and has nowhere to save.
- **Auto-drape scoped to the shop.** `/create` accepts `shop_domain`; the fan-out then
  covers that store's garments only. No shop, or an unknown one, still drapes every
  store.
- **Widget token** (`backend/app/services/widget_token.py`). Issued when a signed-in
  tryon.global page completes the widget's sign-in hand-off with its bearer token;
  checked on `/api/avatar/{uid}`, `/api/draping/check` and the wishlist widget path.
  `widget-state/complete` rejects a bearer token that is not the user it names.
- **Rollout flag `WIDGET_AUTH_REQUIRED`, default off.** Off: bare `user_id` requests
  still work and are logged, so the live widget is unaffected. On: they get a 401.

**Verified.** `scripts/check_widget_onboarding.py` (43 checks, new). Nothing was run
against RunPod or production.

## OPEN

- **Widget half of part 2**, once `feature/widget-onboarding` is pushed:
  - store `widget_token` from the `widget-state` poll and send it as `X-Widget-Token`
    on `/api/avatar/{uid}`, `/api/draping/check` and the wishlist calls;
  - send `shop_domain` in the widget's `/api/avatar/create` call;
  - offer Woman / Man / Other again.
  Then set `WIDGET_AUTH_REQUIRED=true` on Railway. Shoppers signed in before the token
  existed will have to sign in once more.
- **Google/Apple popup handing the card a session: not built.** Two things to decide
  first.
  - Copying the popup's refresh token into the card would make two clients share one
    token, and Supabase's reuse detection would sign one of them out. The clean route is
    a server-minted one-time login code (`auth.admin.generate_link` on the backend,
    `verifyOtp` in the card).
  - `/widget-signin` completes a `widget_state` for whoever is signed in. Today a crafted
    link yields that person's `user_id`. With a session hand-off the same link would
    yield their account. It needs a confirm step in the popup ("Continue as x@y on
    {store}?") and a verifier only the widget holds.
- **A shopper who onboards in one store and later visits another** has no pre-draped
  garments there. Either drape on first visit or keep the fan-out wide.
- `/api/products/{id}/tryon-config?user_id=` still takes a bare `user_id` (it returns
  drape URLs from a public bucket).
- `tryon_sessions.product_name` is "NPC Oversized T-Shirt" on every La Fam session, and
  `action` never moves past `opened`.
- Yesterday's open items stand: migration 006, the missing Terms page, `tryon-cart.js`
  over 10 KB, LHM cold start.
