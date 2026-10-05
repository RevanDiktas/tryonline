# Handoff: 2026-10-05 evening

Written from a cloud session (no access to RunPod, Railway logs or the Mac) so the work can
continue in Claude Code on the laptop. Read this after `2026-10-05_STATUS_REPORT.md`, which
covers the morning (analytics definitions, onboarding part 2, the first size finder).

## Branches

| Branch | What deploys from it | Head |
|---|---|---|
| `feature/analytics` | Railway backend + the three Vercel projects (tryon.global) | `e1fefd0` plus this file |
| `feature/lhm` | RunPod endpoint `tryonline-lhm` (the live avatar worker), Dockerfile `avatar-creation-lhm/Dockerfile.runpod` | `904d566` |
| `feature/widget-onboarding` | nothing; exists only on the Mac, unpushed (`a69bc77`) | - |

`main` is stale. `avatar-creation/` (4D-Humans) is NOT what production runs; the live worker
is `avatar-creation-lhm/handler.py` on `feature/lhm`. PR #7 changed the 4D-Humans pipeline by
mistake and was closed unmerged.

## Merged to `feature/analytics` today (PRs #3 to #10)

- **#3 Product picture in the size card.** The store block sends the product or variant image;
  the card shows thumbnail + brand + name. Needs the block released to show in a store.
- **#4 Details per account.** Bug found in a real run: typed height/weight/body type were kept
  per device, so a second account on the same phone skipped step 2 and was measured as a
  195 cm woman (120 cm hips, "XXL"). Details are now keyed to the account and cleared on
  sign-out.
- **#5, #6, #8 Build screen and timing.** Progress only moves forward; screen says "Getting your
  measurements", no product name, no timer; backend polls RunPod every 2 s (was 5 s). The
  backend writes one `avatar_build_timing` row to `analytics_events` per finished build:
  `queue`, `gpu`, `pipeline`, `save`, `total` (seconds) and `stages` (the worker's own
  per-stage seconds, `data_source`, `using_volume`, `data_log`).
- **#9 Location from IP.** `/widget-config` returns `geo` (country, countryCode, city) from
  Vercel's IP headers. The size card and `test-viewer.html` attach country and city to every
  event. Verified live for the endpoint and locally for the card; the try-on viewer's events
  are unverified (it sent none in the local preview).
- **#10 Copy.** "This can take around 2 minutes."

## Avatar build speed: where it stands

Measured with the new timing rows (all cold workers, seconds):

| Run (UTC) | Worker version | Queue | Model data step | Pose model load | Rest on GPU | Backend save | Total |
|---|---|---|---|---|---|---|---|
| 13:55 | `65bbd02` | 14.5 | 85.6 | 7.5 | ~6 | 5.0 | 122.4 |
| 15:33 | `34fe46a` | 10.7 | 97.7 | 7.6 | ~6 | 8.4 | 140.2 |
| 15:50 | `76a04b6` | 18.1 | 59.2 | 7.4 | ~6 | 4.9 | 100.0 |

Findings:

1. Pose inference is 0.5 s. The model is not the problem.
2. The endpoint has **no network volume** (`using_volume: false`). Every fresh worker ran the
   full bootstrap: download and unpack `LHM_prior_model.tar` and `motion_video.tar` from Aliyun.
3. Production needs only `pretrained_models/human_model_files` and
   `pretrained_models/gagatracker` from the prior tarball. `76a04b6` fetches just that tarball
   and unpacks just those trees ("slim fetch"): 18.8 GB downloaded in 54.8 s, unpacked in 2.8 s.
4. So the remaining ~55 s is downloading 18.8 GB to use a small part of it.

### What is on `feature/lhm` now (`904d566`)

Handler only; the Dockerfile is byte-identical to the last known-good one.

- `cmd_avatar_production`: `timings` in the output; `data_source` is `baked` (files already on
  disk), `slim_fetch`, `bootstrap`, or `bootstrap_after_baked_failed`.
- `_fetch_production_models()`: the slim fetch. Any failure falls back to `_ensure_lhm_data()`.
- `recover()`: if a model fails to load from the local copy, run the full bootstrap once and
  retry.
- **Survey (new in `904d566`, not yet run):** after the download it walks the tarball with
  `tarfile` and returns `timings.prior_survey = {tar_bytes, entries: [[name, kind, offset_data,
  size, linkname], ...]}` for the two needed trees. It lands in
  `analytics_events.event_data -> 'stages' -> 'prior_survey'` on the next cold build.

### Next step (not done)

Use the survey to fetch only the needed bytes:

1. Run one fresh sign-up after the `904d566` build is live, then read the survey:
   ```sql
   select created_at, event_data->'stages'->'data_log', event_data->'stages'->'prior_survey'
   from analytics_events where event_type = 'avatar_build_timing'
   order by created_at desc limit 1;
   ```
2. Embed the entries in `handler.py` as a constant (handler-only change, so the build stays
   on the safe path). At runtime: check the remote `Content-Length` equals `tar_bytes`, download
   the needed byte ranges in parallel (HTTP Range against the Aliyun URL, e.g. 16 threads with
   `httpx`), write each file from its `offset_data` and `size`, recreate dirs and symlinks.
   On any mismatch or error fall back to the slim fetch.
3. Expected: the data step drops from ~59 s to roughly 10 s if the trees are a couple of GB
   (the survey's `data_log` line gives the real size). Unverified until measured.

Alternatives, in case the range approach disappoints:

- **Network volume** (RunPod Storage, ~30 GB, attach to the endpoint). The handler already
  supports it: first job fills it, later workers skip the download. Costs a small monthly fee
  and ties workers to one data centre.
- **Active worker = 1** removes cold starts entirely but bills around the clock.
- **Baking into the image**: tried, see below.

### Build failures to know about

Commits `4ea2ca4` and `26a6189` added one `RUN` step to the Dockerfile that downloaded the
prior tarball and kept the two trees. Both RunPod builds failed within a second of
"Creating cache directory", with no further log. The Dockerfile parses with Docker's own
parser, RunPod's status page showed no incident, and restoring the old Dockerfile (`34fe46a`)
built fine. Cause unknown. Do not re-add that step in the same form. If baking is retried,
change one thing at a time (for example a script file plus a plain `RUN bash script`) and
expect a failed build to leave the previous release serving.

Handler-only pushes have built and rolled out every time today.

## Open items

- **Stored files of the deleted test account.** Account `tryingon@gmail.com`
  (`deb94dc8-ec9f-4b07-8c8f-bfcd682f32a9`) and its rows were deleted, but its files remain in
  Storage: `photos/<id>/` (public bucket), `avatars/<id>/`, and draped garments under
  `draped-artifacts/*/<id>_*`. Delete them from the Supabase Storage screen.
- **Test accounts from today, not cleaned up:** `test1@gmail.com` to `test5@gmail.com`
  (created 2026-10-05 between 10:33 and 15:48 UTC), each with a fit passport, avatar files and
  events. One other sign-up at 13:13 UTC looks like a real shopper (passport still `pending`,
  no photo sent); leave it.
- **Shopify block not released.** `find-my-size.liquid` (with the product image) needs
  `shopify_app/deploy.sh` for the Ramin test app and adding the block in the theme editor.
- **Measurements scale with typed height.** Same person, same day: 112/98/110 at 190 cm and
  115/101/113 at 195 cm (chest/waist/hips). A wrong height moves the size. Repeatability
  (111 to 115 cm chest across runs) is still open from the morning report.
- **Raw IP addresses** are still stored on each event. Country and city are now saved
  directly, so the IP column could be dropped; not done, waiting for a decision.
- **Privacy policy** should mention deriving country and city from the IP address.
- **IP location now wins over the profile** for signed-in shoppers' events (it used to be the
  typed profile country/city).
- **Still flagged from the morning:** `photos` bucket is public; RLS is off on `brands` and
  `garments`; `WIDGET_AUTH_REQUIRED` is still off; the widget token and `shop_domain` are not
  wired into `test-viewer.html` (waits for `feature/widget-onboarding` to be pushed).

## Things that did not get verified

- The try-on viewer's events carrying country/city (no events fired in the local preview).
- PR #10's Vercel deploy (merged, not checked).
- The survey code on a real worker (tested only against small sample tarballs).
- That a failed RunPod build always leaves the previous release serving (it did today).

## Working notes for the next session

- Local preview stack used for card testing lives outside the repo and is gone with the cloud
  session: a fake Supabase/RunPod server, `next dev` with `NEXT_PUBLIC_API_URL`,
  `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` set, and Playwright scripts.
- Check scripts that must keep passing: `backend/scripts/check_widget_onboarding.py`,
  `check_analytics_cohort.py`, `check_analytics_ranges.py`, `check_analytics_scoping.py`,
  `frontend/scripts/check_size_estimator.mjs`.
- Standalone card test link (no store needed):
  `https://tryon.global/size-finder.html?shop=ph2360-eq.myshopify.com&product_id=rs-zip-up&product_name=RS%20Zip%20Up&brand_name=Ramin%20Studios&sizes=S,M,L,XL&product_image=<https image url>`
