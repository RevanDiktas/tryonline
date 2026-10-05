# Start here: 2026-10-06

Written 2026-10-05 22:45 from the cloud session. Read with `2026-10-05_NIGHT_STATUS.md`
(laptop, 21:55) and `2026-10-05_SLEEVE_ARM_MISMATCH.md`.

## 1. First thing: arms poke out of La Fam sleeves

**What Revan saw:** `test5@gmail.com` (`bdfebfca-459a-482b-bc14-34604454c0d5`) in the La Fam
striped longsleeve XL on lafamamsterdam.com: sleeves hang steeper than the arms and each
forearm comes out through the sleeve.

**Cause (from reading code, not yet measured on meshes):** the drape handler never moves a
sleeve onto the shopper's arm. No cloth sim since v36; La Fam garments are "pre-fitted" (v47)
and left where CLO3D exported them; avatars have arms fixed at 45 degrees
(`APOSE_SHOULDER_RAD`, `avatar-creation-lhm/handler.py`); `_retarget_garment_to_body` only
pushes cloth out of the body and cannot carry a sleeve around an arm that crosses it.
Full reasoning and options: `2026-10-05_SLEEVE_ARM_MISMATCH.md`.

**Do, in this order:**

1. **Confirm before building anything.** Download test5's `body_apose.obj` and the longsleeve
   XL garment OBJ. Measure the arm axis and the sleeve axis per side (expected: roughly 45 vs
   55 degrees below horizontal). If they match, the diagnosis is wrong: stop and look again.
2. **Build the sleeve re-pose** in `avatar-creation/draping/handler.py` on the `drape` branch:
   rotate each sleeve about the shoulder to the body's arm axis, blended from 0 at the armhole,
   before the retarget. Skip under ~3 degrees so Ramin on a 45 degree body is unchanged.
3. **Follow the handler-rigor rule:** `py_compile`, run locally, measure, render back and side
   views before/after for longsleeve S and XL, one La Fam tee, RS Zip Up. Show Revan. Then build.
4. **Fold in last night's plan only after re-checking it.** The forearm and cuff holes in the
   night status ("seams split near the cuff") may be this same mismatch. Re-render those after
   the re-pose before welding seams or raising the clearance.
5. The version bump re-drapes everything in the background. Consider drape `workersMax` 2 -> 4
   and `DRAPE_MAX_IN_FLIGHT=4` on Railway for the backlog.

## 2. Then: make the first drape fast

Today's numbers: a drape sim takes 12 to 80 s per size, but the first one after a quiet period
took ~4.5 min (GPU start), and a full set for a new avatar took 12 to 38 min with 2 in flight.
Options are settings, both cost money: one always-on drape worker; max workers 2 -> 4.
Revan has not decided.

## 3. Then: finish the avatar build speed-up (`feature/lhm`)

The survey ran. A cold avatar build is ~100 to 106 s, of which ~61 s is downloading an 18.8 GB
tarball; only **68 of 243 entries, 4.97 GB**, are needed (`tar_bytes` 18818365440). A warm
worker builds in **14.6 s** total.

Next: embed the 68 entries in `avatar-creation-lhm/handler.py` and fetch only those byte
ranges (HTTP Range, parallel), falling back to the current slim fetch on any mismatch.
Expected: ~61 s -> roughly 15 to 20 s for the data step. Read the entries with:

```sql
select event_data->'stages'->'prior_survey'
from analytics_events
where event_type = 'avatar_build_timing' and event_data->'stages' ? 'prior_survey'
order by created_at desc limit 1;
```

Once embedded, remove the survey code from the handler. Handler-only pushes build fine; the
Dockerfile model-baking step failed twice on RunPod with no log, do not re-add it as it was.

## What changed after the night status (cloud session, all merged to `feature/analytics`)

- **#12** New avatars are pre-draped for every store again, sign-up store first (priority 10),
  other stores behind (priority 50). The store-only scope had left test-link accounts with
  no La Fam drapes.
- **#13** `fill_drape_gaps`: opening an undraped garment also queues everything else that
  shopper is missing (priority 50, once an hour). `prioritize_drape` retries a failed drape
  when the shopper opens it again after 10 min; the fan-out still never retries. The
  "Fitting ..." note moved into the 3D area (it covered Add to cart). `check_drape_priority.py`
  updated; all backend checks pass. **Not verified live**: the note was rendered in isolation
  only, and the Railway/Vercel deploys of #12 to #14 were not confirmed.
- **#14** The sleeve diagnosis doc.

## Still open (unchanged)

- One drape keeps timing out: Ramin "sports sweats" L for `719aec87...` (`executionTimeout
  exceeded`, 2 of 3 attempts used).
- Test accounts `test1@gmail.com` to `test8@gmail.com` and their stored files; stored files of
  the deleted `tryingon@gmail.com`.
- Revan has not yet tested: closing the card mid-build and reopening; an existing account going
  straight to the viewer.
- Privacy policy (IP -> country/city), raw IP column, RLS on `brands`/`garments`, public
  `photos` bucket, `WIDGET_AUTH_REQUIRED`.
