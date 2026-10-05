# Find my size: a size without an avatar

Started 2026-10-05 on `claude/find-my-size` (cut from `feature/analytics`). Not merged,
not deployed, and not yet on any store.

## What it is

The avatar try-on gives a size from a photo. It takes minutes, needs an account, and only
works on products that have a 3D garment. "Find my size" is the fast tier beside it:

- Six quick answers: women's or men's, height, weight, age (optional), two taps about
  build, and how the shopper likes things to fit.
- No account, no photo, no 3D garment. It works on **every product with two or more
  sizes**, using the store's own size labels and stock.
- The size comes from the same sizing engine as the avatar tier (`sizing-engine.js`), so
  both tiers follow one set of rules.
- Once a shopper has answered, every product page shows "Your size: L" next to the size
  picker without a click.
- If the Try On block is on the page and the product has a 3D garment, the card offers
  "See it on your own body" as the next step.

## Files

| File | What it is |
|---|---|
| `frontend/public/size-estimator.js` | Body estimate + size likelihoods. Pure module. |
| `frontend/public/size-finder.html` | The card, opened in an iframe on the store. |
| `shopify_app/extensions/tryon-widget/blocks/find-my-size.liquid` | New theme app block. |
| `scripts/fit_size_estimator.py` | Re-fits the estimator from the public dataset. |
| `frontend/scripts/check_size_estimator.mjs` | 35 offline checks (`node`). |
| `backend/app/models/events.py` | Two new event types. |

## How accurate it is

The estimator is fitted on ANSUR II, the public US Army body survey (4,081 men, 1,986
women), using their self-reported height and weight. Measured against the tape-measure
size for the same people, through the same engine, with European size bands:

| | Same size | Within one size |
|---|---|---|
| Men, tops | 69% | 99.3% |
| Men, bottoms | 62% | 98.8% |
| Women, tops | 54% | 97.8% |
| Women, bottoms | 65% | 99.1% |

That is height, weight and age only. If shoppers answered the two build questions
perfectly it would rise to roughly 76-82%; how well they really answer is unknown.

Because one in three is a size off, the card never shows a bare size. It shows a
likelihood per size and says "you are between L and XL" when a second size is at least
25% likely. The stated likelihood was checked against reality on the same data: when the
card says 65%, it is right about 65-70% of the time.

**Limits.**
- Soldiers aged 17-58: leaner than shoppers in general, and nobody older. Outside the
  sampled range the card says the result is a rough guide.
- The dataset measures the waist at the navel, which is not the natural waist women's
  charts use. So women's bottoms are sized from the hips, not the waist.
- How far a build answer moves the estimate (`SHAPE_WEIGHT = 0.6`) is a judgement, not a
  measurement.
- Women's tops are the weakest case (54%). A bra-size question would help most there.
- It could not be calibrated against our own avatars: the 25 completed passports are
  mostly test accounts and disagree with themselves (one 195 cm / 85 kg person measured
  with a chest of 111, 112 and 115 cm).

## Privacy

Answers are stored in the shopper's browser only. Height, weight and age are never sent
to the API. Only the outcome is: the size, its likelihood, and whether they picked another
size or added to cart.

## Analytics

- New events: `size_finder_opened`, `size_finder_completed`.
- `size_recommended`, `size_selected` and `add_to_cart` are reused with
  `metadata.source = "size_finder"`.
- Cart lines carry `_tryon_session_id` and `_tryon_source: size_finder`, so orders link
  back.
- **Not on the dashboard yet.** A size-finder session never sends `tryon_started`, so it
  stays out of the try-on numbers. Its orders are currently in neither the try-on group
  nor the store baseline.

## Checked

- `node frontend/scripts/check_size_estimator.mjs`: 35 checks.
- The full shopper flow in a browser, phone and desktop width, on a mock store page built
  from the block's real script: open, validation, result, sold-out size, add to cart,
  and the size appearing on reload without a click.
- Not checked: a real Shopify theme. The block has never been rendered by Shopify.

## To put it on a store

1. Merge, so Vercel serves `/size-finder.html` and Railway accepts the two new events.
2. `shopify_app/deploy.sh` to release the extension with the new block.
3. In the theme editor, add the "Find my size" block under the size picker.

Order matters: the backend must be deployed before the block, or its events are rejected
(the card still works; only tracking is lost).

## Open decisions

- **Pricing.** Whether this is a separate, cheaper plan. Nothing gates it today: any store
  with the block gets it.
- **Language.** The card is English only. La Fam's store is Dutch.
- **Dashboard.** A size-finder section, and where its orders belong in the comparison.
- **Bra size** as an optional question for women's tops.
- **Size charts.** A brand's own chart is not used; the engine sizes from the body. Brands
  whose sizes run small or large have no way to say so yet without a 3D garment.
