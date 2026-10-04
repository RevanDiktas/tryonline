# Status: 2026-10-04

Branches touched: `feature/analytics` (production) and the new `feature/widget-onboarding`
(local only, worktree `/Volumes/SanDisk/mvp_pipeline-onboarding`).
Trigger: check drape jobs, continue dashboard step 3 (data correctness), and act on the
mentor's review of the La Fam widget.

---

## WIN: every drape is in place

- **`drape_jobs`.** 1,491 jobs, 1,439 completed, 52 failed. Nothing queued or running.
- **The 52 failures** happened in one burst, 2026-10-03 13:45–13:48 UTC. RunPod reported
  COMPLETED but the result had neither `success` nor an error, so the callback logged
  "RunPod status=COMPLETED" (`draping.py:667`). All 52 were redone and completed later.
- **Coverage** against production's avatar-based `body_hash`: 24 avatars × 42
  garment-size combos = **1,008 / 1,008**, none missing, none on an old garment version.
- **Files.** All 1,008 GLBs return 200 (1–6 MB, median 1.5 MB).
- **Gotcha.** `feature/photoreal-avatar` still has the old measurement-based
  `compute_body_hash`. Run coverage checks with production's
  `body_clustering.py` or they show false gaps.

## WIN: purchases and returns tied to the try-on (`9dea9a2`, live)

**Cause.**
- The refund webhook selected only `session_id`, then read `event_data` from it, so it
  never matched an order. Return rate always read 0.
- Purchases were stored without product, device or country, so every order showed under
  "unknown" in the device and region panels.

**Fix.**
- **Widget orders** take user, product (handle), variant, device and location from their
  try-on session.
- **Store orders** keep Shopify's `client_details` and the shipping country (full name,
  e.g. "Netherlands", as other events store it).
- **Refunds** copy all of that from their purchase. The lookup is by shop + `order_id`,
  and each `refund_id` is counted once.
- **Unknown or malformed session ids** no longer fail the insert. Before, they made
  Shopify retry forever. The order is now stored unlinked, with
  `unmatched_tryon_session_id`.
- **Cart property** renamed to `_tryon_session_id`, so it is hidden in cart and checkout.
  The webhook still reads the old name.

**Verified.**
- 16/16 handler checks against an in-memory DB (`~/Downloads/tryon-widget-qa/test_webhooks_step1.py`).
- The new lookups ran read-only against the production DB.
- Railway is live on `9dea9a2`.
- Unsigned webhook calls return 401.
- Blocks: `la-fam-7` (checked on lafamamsterdam.com), `tryonraminpilot-18`, and the
  public app.

**Not proven yet:** a real order linking to a try-on. Only 1 of La Fam's 957 orders even
matches a widget add-to-cart by variant. 44 try-on sessions in a year is a volume
problem, not a bug.

## WIN: range menu confirmed live

The production `/brand` bundle contains Today → Last year. That closes yesterday's
"NOT VERIFIED".

## Mentor review of the La Fam widget (saved to memory)

- The login wall before any payoff is the biggest drop-off.
- Lead with size ("Find your size in 30 seconds"); the avatar is the bonus.
- The card is cut off on short screens.
- The card doesn't match the store's look.
- The Try On button is easy to miss: put it by the size picker.
- The goal is usage scale (5K tries a month).
- Users went 35 → 80 in 4 days with no marketing yet.

## IN PROGRESS: onboarding inside the widget (`a69bc77`, local, not deployed)

Decision (Revan): full onboarding inside the widget. Account + photo → RunPod avatar,
from the first click, without leaving the store page.

**Built in `test-viewer.html`.**
- **Steps:** Get started → account (name, email, password, consent) → height, weight and
  body type → one full-body photo ("Take a photo" opens the phone camera; or the photo
  library) → build progress → try-on.
- **Session.** The card holds its own Supabase session (publishable key, supabase-js
  loaded only when needed). It calls the same `upload-photo` / `create` / `status`
  endpoints as tryon.global/onboarding, so **no backend change is needed for part 1**.
- **Email sign-in inside the card.** Google and Apple still use the popup.
- **Build resilience.** A build keeps polling while the widget is closed, resumes after
  a page change, and checks for the avatar if the backend forgot the job (restart).
- **Short screens.** The card scrolls instead of being cut off (mentor point).
- **Bug fix.** Only a `completed` passport counts as an avatar. **17 live shoppers** have
  a `pending` passport and no avatar; the live widget sends them into a try-on that loads
  a GLB that doesn't exist.

**Checked:** all widget scripts parse (`node --check`). **Not yet run in a browser.**

**Corrections to what was said earlier today.**
- A size from height and weight alone would be fake. The engine needs chest, waist and
  hips, which come from the photo (`sizing-engine.js:315-329`); without them the widget
  falls back to defaults. **The size arrives with the avatar.** An instant estimate needs
  a new model; that's a later decision.
- Calling RunPod straight from the button is out: it would expose the API key.

## OPEN

- **Local test harness.** `next dev` in the onboarding worktree exited with code 1. The
  rtk shell wrapper hid the error. Start it outside rtk:
  `cd /Volumes/SanDisk/mvp_pipeline-onboarding/frontend && NEXT_PUBLIC_API_URL=https://heroic-celebration-production-9f72.up.railway.app npx next dev -p 3000 -H 0.0.0.0`
  - `node_modules` is a symlink to the main checkout. Suspect that, or the Node version.
  - Mock store: `~/Downloads/tryon-widget-qa/mockstore/index.html`. Serve it on port
    8080. It iframes `:3000` cross-origin, like a real store, and uses the **RaminStudios
    test store** (`ph2360-eq`, `rs-zip-up`), so La Fam's analytics stay clean.
  - **Phone.** The Mac was on `172.20.10.9` (iPhone hotspot); check the phone can reach it.
- **Before testing, read RunPod `tryonline-lhm` worker settings** (read-only): min
  workers, idle timeout, FlashBoot. A cold first job takes over 10 min, which hits the
  10-min backend cap.
- **Test data.** The test account and avatar will land in production Supabase. Delete
  them afterwards.
- **Migration 006** (`backend/migrations/006_return_refund_unique.sql`). Revan to run it
  in the Supabase SQL editor.
- **Gender "other" always fails.** The backend accepts it and the LHM handler rejects it
  (`handler.py:2686`). This affects the live website onboarding. The fix (map other →
  neutral) goes with part 2. The widget offers Woman / Man only until then.
- **No Terms page.** `/terms` is a 404 (the website signup links `#`). The widget consent
  links the Privacy Policy only.
- **`tryon-cart.js` is 13.5 KB** against the 10 KB block limit. Shopify still released
  the block, with a warning.
- **The 2026-10-03 open items still stand.** LHM cold start, in-memory jobs and
  widget-state, the 2.3 MB payload, the HF token rotation, and leftover test data.

## NEXT UP

1. **Get the local harness running and test part 1 with Revan.** Desktop first, then
   iPhone camera. Watch a full build through to the try-on, then try close/reopen during
   the build, a page change during the build, a bad photo, an existing email, and a short
   window.
2. **Part 2** (local backend, then deploy):
   - Google/Apple popup handing the card a session (one-time code exchange).
   - A widget token closing the bare-`user_id` gap (`/api/avatar/{uid}`,
     `widget-state/complete`).
   - Gender other → neutral.
   - Create the passport server-side in `/create`.
   - Scope the auto-drape fan-out to the current shop.
3. **Analytics steps 2–4.**
   - One definition per metric, using distinct sessions.
   - Try-on cohort only, with a 30-day window.
   - Remove the fake "Size Selected" funnel step.
   - Cohorts page on real data via `/cohort-comparison`.
   - Real test order + refund on the Ramin store.
