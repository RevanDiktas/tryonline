# Find my size: your size on any product, from your account

Started 2026-10-05 on `claude/find-my-size`, stacked on
`claude/analytics-and-onboarding-part2` (PR #1), which it needs. Not merged, not deployed,
not on any store, and **never run against the real RunPod endpoint or a real account**.

## One onboarding, two surfaces

A shopper is onboarded once: account, height and weight, one photo. That always starts
the full build on RunPod (`POST /api/avatar/create`), which produces a fit passport
(measurements) **and** an avatar. What a surface fetches depends on what it shows:

| Surface | Shows | Fetches |
|---|---|---|
| "Find my size" card (`size-finder.html`) | Size only | `GET /api/measurements/passport/{id}`: the fit passport |
| Try On widget (`test-viewer.html`) | Size on the avatar | `GET /api/avatar/{id}`: passport + avatar |

So a shopper who starts in the size card already has an avatar when they open the Try On
widget, and the other way round. A size needs no 3D garment, so the card answers on every
product with two or more sizes, in every store with the block: one account, every store.

## What the shopper sees

Everything happens in the card, on the store's product page.

1. **Find your size.** Create an account, or sign in.
2. **Account.** Name, email, password, consent to storing the photo and measurements.
3. **About you.** Body type (Woman / Man / Other), height, weight.
4. **One full-body photo.** Camera or photo library, with an example pose.
5. **Measuring you.** Progress and elapsed time. The shopper can close the card and keep
   shopping.
6. **Your size.** The size, chest / waist / hips, a fit preference, add to cart.

After that, "Your size: L" shows next to the size picker on every product, without a
click. If the Try On block is on the page and the product has a 3D garment, the card
offers "See it on your own body".

The card is in Tryon's own look (Inter, black on white, like the Try On widget). A block
setting, "Match my store", passes the store's colours, font and button shape instead.

## How it is wired

- **Account.** The card holds its own Supabase session: email and password straight
  against the auth REST API, keys from `/widget-config`. It inserts the `users` profile
  row a fit passport hangs off, and never overwrites an existing one.
- **Build.** The same three endpoints tryon.global/onboarding uses: `upload-photo`,
  `create`, `status`. `create` gets `shop_domain`, so the avatar is pre-draped for this
  store's garments. From PR #1: `create` makes the passport itself, and "Other" goes to
  the pipeline as `neutral`.
- **Photo.** Redrawn upright in the browser at up to 2048 px before upload, so a phone
  photo of several MB becomes a few hundred KB.
- **Closing mid-build.** The build runs on the backend either way. The card stores the
  job id and picks it up on the next open or the next product page. If the backend forgot
  the job (a restart), the passport's own status says how it ended.
- **Only a `completed` passport is a measurement.** A pending one holds what the shopper
  typed and nothing measured.
- **Google / Apple** still open tryon.global in a popup and hand back the user id only.
  That is enough to show a measured shopper their size. A new shopper who signs in that
  way is pointed to tryon.global for the photo, or can sign in with email in the card.
  This goes away with the session hand-off (see PR #1's status report).

## Files

| File | What it is |
|---|---|
| `frontend/public/size-finder.html` | The card: account, photo, build, size. |
| `shopify_app/extensions/tryon-widget/blocks/find-my-size.liquid` | New theme app block. |
| `backend/app/api/routes/measurements.py` | `GET /passport/{user_id}`: passport only. |
| `frontend/app/widget-config/route.ts` | Also returns the public Supabase URL and key. |
| `backend/app/models/events.py` | Nine `size_finder_*` event types. |
| `frontend/public/size-estimator.js` | The optional estimate. Pure module. |
| `scripts/fit_size_estimator.py` | Re-fits the optional estimate from the public dataset. |
| `frontend/scripts/check_size_estimator.mjs` | 35 offline checks of the estimate. |

## Checked, and not checked

Run in a browser at phone width, on a mock store page built from the block's real
script, against the real backend code. Storage, RunPod and Supabase auth were local
stand-ins.

- A new shopper end to end: sign-up, validation, details, photo, build, size.
- The stand-in RunPod received gender `neutral` for "Other", the typed height and weight,
  and a signed photo URL. A 3024 x 4032 test photo was uploaded at 30 KB.
- Closing the card mid-build: the store button changed to "Your size: L" by itself when
  the build finished.
- A later page view fetched `/api/measurements/passport/{id}` and no avatar.
- A failed build shows "That photo did not work" and the passport ends `failed`.
- Sign-in on a fresh browser, a wrong password, and sign-up with a taken email.
- `backend/scripts/check_widget_onboarding.py`: 48 checks, including the passport route.

Checked against the production database, read-only (2026-10-05):

- Sign-up needs no email confirmation: all 85 accounts are confirmed and no confirmation
  mail was ever sent, so sign-up returns a session and the card can carry on.
- `on_auth_user_created` creates the `users` row from the sign-up metadata (`name`,
  `user_type`), which is what the card sends. The card's own insert is a no-op backup.
- `users` allows a signed-in shopper to insert their own row; `fit_passports` requires
  `user_id`, `height` and `gender`, all of which `/create` writes.
- **The `photos` bucket is public.** The backend comments say it is private. Shoppers'
  full-body photos are readable by anyone who has the URL. Not changed here.

**Not checked.**
- The real RunPod endpoint, real Supabase auth, real storage.
- A real Shopify theme: Shopify has never rendered the block.
- A real phone camera inside a store iframe.
- The Google / Apple popup.

## How accurate the size is

Exactly as good as the measurements on the passport, and those vary. One person (195 cm,
85 kg) was measured four times with a chest of 111, 112, 115 and 115 cm. A size band is 6
to 10 cm wide, so that spread can move someone a size. This card has no avatar on screen
for the shopper to sanity-check.

It uses what the passport stores: height, chest, waist, hips, inseam, shoulder width, arm
length, neck, thigh and torso length. If the pipeline extracts more, the rest are not
stored where the card can read them.

## The estimate (optional, off by default)

Fitted on ANSUR II, the public US Army body survey (4,081 men, 1,986 women), using their
self-reported height and weight. Against the tape-measure size for the same people,
through the same engine, with European size bands:

| | Same size | Within one size |
|---|---|---|
| Men, tops | 69% | 99.3% |
| Men, bottoms | 62% | 98.8% |
| Women, tops | 54% | 97.8% |
| Women, bottoms | 65% | 99.1% |

So the card shows a likelihood per size and says "you are between L and XL" when a
second size is at least 25% likely. Limits: soldiers aged 17-58 only; women's bottoms are
sized from hips because the dataset's waist is at the navel; how far a build answer moves
the estimate (`SHAPE_WEIGHT = 0.6`) is a judgement, not a measurement.

## Analytics

- New events: `size_finder_opened`, `size_finder_account_created`,
  `size_finder_signin_clicked`, `size_finder_signed_in`, `size_finder_measure_clicked`,
  `size_finder_build_started`, `size_finder_build_completed`, `size_finder_build_failed`,
  `size_finder_completed`. Each carries `metadata.basis`: `measured` or `estimate`.
- `size_recommended`, `size_selected` and `add_to_cart` are reused with
  `metadata.source = "size_finder"`.
- Cart lines carry `_tryon_session_id` and `_tryon_source: size_finder`.
- **Not on the dashboard yet.** These sessions never send `tryon_started`, so they stay
  out of the try-on numbers.

## To put it on a store

1. Merge PR #1, then this. Railway must be live first: the card needs the passport
   route, server-side passport creation and the new event types.
2. `shopify_app/deploy.sh` to release the extension with the new block.
3. In the theme editor, add "Find my size" under the size picker.
4. Do one real run on the Ramin test store before La Fam. Delete the test account after.

## Open

- **The wait.** A first build can take ten minutes or more when the RunPod worker is
  cold. The card lets the shopper leave and come back, but the fix is on the worker
  (minimum workers, or a measurements-first step).
- **One sign-in per store, per browser.** Browsers keep each store's copy of the card
  separate.
- **The Try On widget does not read this card's session.** It shares the remembered user
  id, so it recognises the shopper, but its own in-widget onboarding is the unpushed
  `feature/widget-onboarding`. The two should end up on one shared piece of code.
- **Password reset** is not in the card. It links nowhere yet.
- **No Terms page.** The consent line links the Privacy Policy only.
- **Size charts.** Without a 3D garment there is no chart, so a brand whose sizes run
  small or large cannot say so.
- **Pricing, language (English only), dashboard section:** all undecided.
