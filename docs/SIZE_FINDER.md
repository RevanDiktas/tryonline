# Find my size: your size on any product, from your account

Started 2026-10-05 on `claude/find-my-size` (cut from `feature/analytics`). Not merged,
not deployed, and not yet on any store.

## What it is

The avatar try-on needs a 3D garment for every product, and those take a long time to
make. "Find my size" is the tier beside it that needs none:

- The shopper signs in to their Tryon account. The measurements on it (taken from their
  photo) go through the same sizing engine as the try-on (`sizing-engine.js`).
- It answers on **every product with two or more sizes**, using the store's own size
  labels and stock. No garment has to be built.
- **One account, every store.** Any store with the block reads the same account. A
  shopper already signed in on tryon.global is handed over in one click.
- A signed-in shopper sees "Your size: L" next to the size picker on every product,
  without clicking.
- If the Try On block is on the page and the product has a 3D garment, the card offers
  "See it on your own body" as the next step.

**The three states of the card.**

| Shopper | Sees |
|---|---|
| Not signed in | Sign in (popup), or create an account (new tab on tryon.global) |
| Signed in, not measured yet | "One photo to go", linking to the photo step on tryon.global |
| Signed in and measured | Their size, their chest/waist/hips, and a fit preference |

Only a passport with status `completed` counts as measured. A pending one holds the
height the shopper typed and nothing else.

**Optional estimate without an account** (block setting, off by default). Height, weight
and two build questions give an estimated size with its likelihood. See "The estimate"
below. It exists for stores that want something for shoppers who will not sign up.

## Files

| File | What it is |
|---|---|
| `frontend/public/size-estimator.js` | The optional estimate. Pure module. |
| `frontend/public/size-finder.html` | The card, opened in an iframe on the store. |
| `shopify_app/extensions/tryon-widget/blocks/find-my-size.liquid` | New theme app block. |
| `scripts/fit_size_estimator.py` | Re-fits the optional estimate from the public dataset. |
| `frontend/scripts/check_size_estimator.mjs` | 35 offline checks (`node`). |
| `backend/app/models/events.py` | Six new event types. |

## How accurate the measured size is

It is exactly as good as the measurements on the account, and those vary. The same
person (195 cm, 85 kg) was measured four times with a chest of 111, 112, 115 and 115 cm.
A size band is 6 to 10 cm wide, so a 4 cm spread can move someone a size. Two passports
look wrong outright (187 cm / 73 kg with a 109 cm chest; 177 cm / 57 kg woman with an
86 cm waist). This tier leans on the measurements alone, with no avatar on screen for
the shopper to sanity-check, so measurement repeatability matters more here than in the
try-on.

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

## Privacy

- Account mode: the card reads the shopper's measurements from their account and sends
  events with their user id, like the Try On widget.
- Estimate mode: the answers stay in the shopper's browser. Height, weight and age are
  never sent to the API.

## Analytics

- New events: `size_finder_opened`, `size_finder_signin_clicked`,
  `size_finder_signup_clicked`, `size_finder_measure_clicked`, `size_finder_signed_in`,
  `size_finder_completed`. Each carries `metadata.basis`: `measured` or `estimate`.
- `size_recommended`, `size_selected` and `add_to_cart` are reused with
  `metadata.source = "size_finder"`.
- Cart lines carry `_tryon_session_id` and `_tryon_source: size_finder`, so orders link
  back.
- **Not on the dashboard yet.** A size-finder session never sends `tryon_started`, so it
  stays out of the try-on numbers. Its orders are currently in neither the try-on group
  nor the store baseline.

## Checked

- `node frontend/scripts/check_size_estimator.mjs`: 35 checks (the optional estimate).
- In a browser, on a mock store page built from the block's real script, against the real
  backend code over test accounts: the signed-out card, sign-in hand-off, a measured
  shopper's size, fit preference, sold-out size, add to cart, the size appearing on
  reload without a click, and the "one photo to go" card for an unmeasured shopper.
- Not checked: the real sign-in popup (tryon.global's page was stood in for by its
  hand-off response), a real Shopify theme, and a real account.

## To put it on a store

1. Merge, so Vercel serves `/size-finder.html` and Railway accepts the two new events.
2. `shopify_app/deploy.sh` to release the extension with the new block.
3. In the theme editor, add the "Find my size" block under the size picker.

Order matters: the backend must be deployed before the block, or its events are rejected
(the card still works; only tracking is lost).

## Open decisions

- **Measuring without building the avatar.** A new shopper still goes through the full
  photo step on tryon.global, which builds the avatar and can take 10 minutes. This tier
  only needs the measurements. A measurements-only run of the pipeline would make
  sign-up fast; that is pipeline work and has not been looked at.
- **One sign-in per store, per browser.** Browsers keep each store's copy of the card
  separate, so a shopper signs in once in each store. If they are already signed in on
  tryon.global it is one click.
- **Which measurements.** The card uses what `/api/avatar/{id}` returns: height, chest,
  waist, hips, inseam, shoulder width, arm length, neck, thigh and torso length. If the
  pipeline extracts more than the passport stores, the rest are not used.
- **Size charts.** For a product without a 3D garment there is no chart, so the engine
  sizes from the body alone. A brand whose sizes run small or large cannot say so yet.
- **Pricing.** Nothing gates this: any store with the block gets it.
- **Language.** The card is English only. La Fam's store is Dutch.
- **Dashboard.** No size-finder section yet. Its sessions never send `tryon_started`, so
  they stay out of the try-on numbers.
- **Widget token.** The card already sends `X-Widget-Token` when it has one. That needs
  PR #1 merged to mean anything.
