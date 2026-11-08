# Status: 2026-11-08 — La Fam demo prep (Web Summit, 2026-11-09)

Branch `feature/analytics` (production). Commits today: `cb610b5` (repair script `--brand`),
`fd2e08d` (widget drape lock + this report), and the Railway note below. Backend on Railway
and widget on Vercel follow the branch automatically.

**Deploy state at close (19:50 CET).** Vercel serves `fd2e08d` (live `test-viewer.html`
byte-identical to the commit). Railway's automatic build of `fd2e08d` FAILED at 19:39 with
no build or deploy log at all, although the commit touched nothing under `backend/`; the
previous deploy (`cb610b5`) stayed online. `railway redeploy --from-source --yes` at 19:43
built the same commit cleanly and `/version` now reports `fd2e08d`. Treated as a transient
Railway failure: same commit, no code change, clean on retry.

## WHERE THINGS STAND

- **Three database problems fixed and verified live.** The 738 MTL-failed drapes are
  re-queued and completing, the four La Fam garments have companions, and the jeans
  (`denim-slogan-jeans`, `7ade3692`) are draping for every avatar.
- **Drape queue draining.** At 19:40 CET: 62 of 240 jeans drapes done, 950 colourway-copy
  jobs still queued, 2 in flight, about 3 jobs a minute. Expected to finish around
  00:30 CET. A new avatar created during the day already received its 6-per-garment
  fan-out (visible as the extra 6 queued jobs per garment), so new accounts are covered.
- **Drape endpoint warm for the demo.** `tryonline-drape` (`e86juazm1b4mig`) runs with
  min workers 1, max 3, from 2026-11-08 to 2026-11-12. **Set min workers back to 0 after
  Nov 12** (`PATCH https://rest.runpod.io/v1/endpoints/e86juazm1b4mig {"workersMin": 0}`).
- **Drape behaviour locked (non-negotiable, Revan 2026-11-08).** The try-on always shows
  the shopper's avatar wearing the garment draped to their body plus the companion, and
  holds an undraped garment back until the drape arrives. `config.tryGarmentOnly` is forced
  false in `test-viewer.html` (`TRYON_DRAPE_LOCK`); the `try_garment_only` URL parameter is
  ignored. Rule recorded in `CLAUDE.md` under DO NOT.

## WHAT WAS DONE

### 1. Sidecar repair (738 drapes)

- Cause: `POST /api/garments/{id}/duplicate` copied `.obj`/`.glb` but not `.mtl`/textures.
  Fix was already on `feature/analytics` (`f42dcf1`, `_copy_sidecar_files`).
- Ran `python -m scripts.repair_duplicate_sidecars --brand a3e127f6-... --apply` from the
  analytics worktree (python3.13 + the main repo's venv site-packages). 20 sidecar files
  copied into each copy folder; 738 jobs reset to queued (234 + 234 + 234 + 36).
- Added `--brand` because the dry run also matched a Ramin pair (`Bow sweats` <- `rs bow
  zipup`) whose 26 failures are the oversized-payload issue, not MTL. Re-queuing them would
  have run ahead of the repairs at priority 50 and failed again.
- Verified: one job from each copy family bumped to the front completed with the restored
  MTL. Dispatcher confirmed alive on Railway (`dispatched_at` advancing within 30 s).

### 2. Companions

- SQL applied as given: jeans <-> diamond t-shirt black; diamond t-shirt blue and the
  pink/yellow longsleeve -> jeans.
- Verified: `GET /api/products/denim-slogan-jeans/tryon-config?shop=la-fam-ams.myshopify.com`
  returns `companion` with six `model_urls`; with a `user_id` that has cached tee drapes it
  returns six `draped_urls` too.
- Not done (outside the brief): the four 2026-11-06 copies (white tee, three wsaewtf
  longsleeves) have no companion.

### 3. Jeans drapes

- Storage had the OBJs under non-standard names: `dj_xs.obj` and `sj_{s,m,l,xl,xxl}.obj`,
  each with its own `.mtl` and the three JPG textures they reference. Set `obj_sizes` to
  those paths. The old jeans drapes did not survive the garment row being re-created, so
  this is a full re-drape.
- `enqueue_for_garment(..., priority=100)` -> 234 jobs (39 avatars x 6 sizes), ahead of the
  738 copies at 200, behind anything a shopper has on screen (0/1).
- Verified: all six sizes, `xs` included, completed drapes at 27-37 s each.

## LATENCY (reproduced from the widget code, not a browser capture)

No browser automation was available and the flow needs a signed-in session, so each hop was
timed from the Mac against production.

| Hop (in widget order) | Measured |
|---|---|
| `/api/avatar/{id}` via tryon.global rewrite | 1.70 s |
| then `/widget-config` + `/api/avatar/{id}` direct, sequential | 0.46 s + 0.69 s |
| `tryon-config` (3 runs, parallel with the above) | 1.41-1.79 s |
| `POST /api/events/tryon-session` (awaited before the scene starts) | not measured |
| Preload: avatar GLB 0.3 MB + six jeans GLBs ~5.9 MB each + companion 1.5 MB (~37 MB) | 0.5-0.8 s each here |
| Railway round trip (`/health`) | 0.28 s |

- First paint waits for **every** size GLB (`preloadAllModels` / `tryPresentTryonModel`),
  so ~37 MB must download before the avatar appears. On conference Wi-Fi this dominates.
- The avatar is fetched twice in sequence (rewrite, then direct) and `tryon-config` spends
  over a second in sequential Supabase calls: ~3 s before the scene starts.
- RunPod round trip for a shopper with no cached drape (from `drape_jobs` history): warm
  25-50 s; after >2 min idle median 125 s, p90 250 s. Cold start is real; hence min workers 1.

## VERIFIED VS ASSUMED

Verified: every number above came from `drape_jobs`/`draped_meshes`/`storage.objects`,
live HTTP calls, or the RunPod API. Assumed: the Railway dispatcher env (2 in flight was
inferred from behaviour, not read from variables); the real browser waterfall on the PDP.
Not browser-tested: the widget lock. It is a no-op on the live store path (the theme block
never sets `try_garment_only`), and all inline scripts pass `node --check`.

## OPEN

- Set `tryonline-drape` min workers back to 0 after 2026-11-12.
- Companion for the four 2026-11-06 copies.
- Widget preload of all sizes (~37 MB) before first paint; avatar double-fetch; 1.5 s
  `tryon-config`. None touched today (out of scope for the demo).
- Dispatcher runs 2 in flight while the endpoint allows 3.
