# STATUS

One-page index of where this project is right now. Update at the end of each working session.

**Last updated:** 2026-08-20
**Active branch:** `feature/photoreal-avatar` (site + backend ship from `feature/analytics`)
**Latest full reports:**
- `docs/progress/2026-08-20_STATUS_REPORT.md` (Web Summit research pass + photoreal floor-frame fix)
- `docs/progress/2026-08-04_STATUS_REPORT.md` (drape coverage 714/714, widget 404 fixed, outfit pairing)
- `docs/progress/2026-08-03_STATUS_REPORT.md` (La Fam jeans fixed + full backfill)
- `docs/progress/2026-07-18_STATUS_REPORT.md` (La Fam launch prep, pre-draping, multi-garment decision)
- `docs/progress/2026-07-12_STATUS_REPORT.md` (photoreal Stage 2b complete at v0.9)
- Plan document: **Road to Lisbon**, https://claude.ai/code/artifact/880131f7-e5f9-45fc-abe6-c6f99daa425e

## Headline

**Everything now points at Web Summit Lisbon, 9 to 12 November.** Three
deliverables: an MCP that plugs into ChatGPT and Claude, an avatar that reads as
a person, and an iOS app. Target 30 September, hard stop end of October.

Today closed the photoreal endpoint's coordinate frame bug. It was shipping
pelvis-centred avatars, which makes the drape handler rescale garments by roughly
1.72x while reporting `body_collisions=0`. Fixed at the source, built, and
verified in production against the exact La Fam garment that caused it.

**Do not plan around a ChatGPT directory listing.** Review is reported at 60 to
120 days. Both hosts accept a remote MCP server by URL with no approval, and that
is the demo.

## The three tracks

| Track | State | Next |
|---|---|---|
| MCP on ChatGPT + Claude | **Nothing written.** Backend surface + auth already exist | OAuth 2.1 server in front of Supabase Auth, then tools, then the UI component |
| Human-like avatar | Stage 1 + 2b done and GPU verified; floor frame fixed 2026-08-20 | **Stage 3**, multi-image splat appearance bake. Needs 3 to 4 guided photos |
| iOS App Store app | **Nothing written.** No RN / Expo / Capacitor / PWA | Apple enrolment + D-U-N-S first, it is the long pole |

Decisions locked 2026-08-20, do not relitigate: MCP is **shopper facing**, app is
**iOS only**, hair is a **cheap authored cap** (HairStep deferred past the Summit).

## Photoreal avatar stages

| Stage | Status |
|---|---|
| 1 base image, all CUDA exts green on A40 | done |
| 2b photo to SMPL-X body + 16-key measurements, ~31 s, no volume | done v0.9 |
| floor frame (feet at Y=0) | **done 2026-08-20, endpoint v14** |
| 3 multi-image splat appearance bake | **NEXT. This is the "human-like" deliverable** |
| 4 watertight drape mesh + real drape gate | not started |
| 5 / 6 SCHP clothing strip + painted underwear | not started |
| hair cap fitted to SMPL-X scalp | not started |
| 7 non-SMPL-X remesh (commercial license) | post demo |

Endpoint `bun2qr20qvnre5`, no network volume, keep OFF Blackwell (sm_120) GPUs.
Never touch live `tryonline-lhm` (`lo2s3qevrvfotn`); flip Railway
`RUNPOD_ENDPOINT_ID` only after e2e plus a drape smoke test.

**Before any photoreal build:** run
`python3 avatar-creation-photoreal/scripts/verify_floor_frame.py`. Exit 0 means
the frame is right. It pulls the drape logic from `git show drape:...` on every
run so it cannot drift from what is deployed.

## What "done" means here

A change is done when:
1. It runs locally without console errors (frontend) or import errors (backend).
2. It does not break `/dashboard`, `/brand`, the live PDP widget, or drape-test.html.
3. It respects the design system (sharp corners, B/W only, sentence case, no em-dashes, no "Palantir").
4. For RunPod handler changes: traced end-to-end against actual source before a build is kicked off (builds cost 14-30 min).
5. Metrics are read back off the artifact, never off what was computed in memory.

## Open workstreams

| Stream | State | Next |
|---|---|---|
| MCP server | Not started | OAuth 2.1 AS, then 7 annotated tools, then the MCP App viewer |
| iOS app | Not started | Apple enrolment + D-U-N-S (calendar time we do not control) |
| Photoreal avatar | Floor frame closed; Stage 2b green | Stage 3 splat bake |
| La Fam pilot | Drapes 714/714, widget serving, outfit pairing live | **Size charts still empty. Blocking.** |
| Photo preprocessing | EXIF orientation + 5:3 padding still manual | Fold into the upload path; phone photos hit this |
| Height normalization | Uniform 1.105x inflates every girth | Decide before the MCP exposes `recommend_size` |
| Drape retarget | v47.1 on the `drape` branch | Cherry-pick to `feature/analytics` when needed |
| Ramin pilot | Cached drapes good; 52 old failures have later good rows | Convert oversized PNG textures to JPEG |
| Shopify App Store | Rejected; running on custom distribution links | Not re-submitting for now |
| Stripe payments | `/pricing` is marketing only | Resolve Shopify Billing decision first |
| Pitch deck | 17 slides on `feature/analytics` | Slide 6 "paid pilot" and slide 7 "10 measurements" still wrong |

## Blocking, not engineering

`size_chart` is `{}` on all four La Fam garments. `tryon-config` substitutes a
hardcoded `{"m": {chest:100, waist:84, hips:98}}`, so size recommendation runs on
invented numbers and states them with full confidence. The 3D try-on is
unaffected and good. Revan fills the charts with the La Fam owner, then go live.
If anything ships before that, hide the recommendation rather than show a
fabricated one.

## Test surfaces (don't break these)

- `/` landing, `/pricing`, `/demo`, `/brand/cohorts`
- `/dashboard` (shopper home), `/brand` (brand dashboard)
- Live PDP widget via `frontend/public/test-viewer.html`
- Drape test at `frontend/public/drape-test.html`

## Pointers

- Repo conventions and architecture: `CLAUDE.md`
- Failure patterns to honor: `FAILURES.md`
- Strategy + pricing: `docs/strategy/`
- Daily progress logs: `docs/progress/`
- Photoreal endpoint: `bun2qr20qvnre5`, handler `avatar-creation-photoreal/handler.py`
- Live LHM endpoint: `lo2s3qevrvfotn`, handler `avatar-creation-lhm/handler.py`
- Drape endpoint: `e86juazm1b4mig`, handler on the `drape` branch (v47.1)
- Memory: `~/.claude/projects/-Volumes-SanDisk-mvp-pipeline/memory/`
- Upright test photo: `lhm-artifacts/inputs/1779046184_user_001_padded.jpg`
  (the older `inputs/2026-05-20/user_001.jpg` is stored SIDEWAYS, EXIF orientation 5)
