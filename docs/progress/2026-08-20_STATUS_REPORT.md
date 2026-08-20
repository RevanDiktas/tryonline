# Status Report - 2026-08-20

Two things this session: a full research pass on the three Web Summit
deliverables, and one of them moved. The photoreal endpoint's coordinate frame
bug is found, fixed, built and verified in production against the exact garment
that caused it.

Plan document: **Road to Lisbon**,
https://claude.ai/code/artifact/880131f7-e5f9-45fc-abe6-c6f99daa425e

---

## The three deliverables, and where they actually stand

Web Summit Lisbon is 9 to 12 November. Revan's target is 30 September, hard stop
end of October.

| Track | State | The gap |
|---|---|---|
| MCP on ChatGPT and Claude | **0 percent written** | OAuth layer, tools, UI component |
| Human-like avatar | **Geometry done, appearance not started** | Stage 3 splat bake |
| iOS App Store app | **0 percent** | Everything, plus a D-U-N-S number |

Verified by grep, not assumed: there is no MCP code in the repo. Every hit is a
vendored library inside a virtualenv. There is no React Native, Expo, Capacitor
or PWA manifest anywhere.

### Decisions locked

- **MCP is shopper facing.** Fit passport, find garments, try on in the chat,
  recommend a size, save it. A brand-facing analytics server comes after.
- **App is iOS only.** One Expo build, one review queue. Android later.
- **Hair is an authored cap** fitted to the SMPL-X scalp. HairStep stays the
  post-Summit upgrade.

### The finding that reshapes the schedule

ChatGPT app directory review is reported at **60 to 120 days**. Submitting on
8 September puts the optimistic end at 7 November, two days before the doors
open. So the plan does not depend on a listing.

It does not need to. Both hosts accept a remote MCP server by URL today, with no
approval: ChatGPT through Settings, Apps, Developer mode, and Claude through
custom connectors. That is the demo, and an attendee can install it on their own
phone at the booth. Done means installable by URL on both hosts. Listed is upside.

Two more that shape the build:

- **MCP Apps is one standard across both hosts.** Same MIME type, same
  postMessage bridge, and OpenAI publishes a migration guide from its own Apps
  SDK. The try-on viewer gets built once and ships to both.
- **Do not iframe tryon.global into the component.** OpenAI's guidelines say
  nested frames get extra manual review and are often not approved for broad
  distribution. The viewer has to be a real bundle inside our own component.

Full research detail: memory `reference-mcp-directory-submission-2026-08-20`.

---

## FIXED - the photoreal endpoint was shipping pelvis-centred avatars

Commit `c9ce07c`. Endpoint `bun2qr20qvnre5` rolled from version 13 to 14 in about
22 minutes.

### What was wrong

`avatar-creation-photoreal/handler.py` converted A-pose vertices to millimetres
with `verts_apose_m * 1000.0` and never re-zeroed to the floor. SMPL-X output is
pelvis-centred, so the OBJ shipped in the broken convention. Measured off the
v0.9 sample:

```
X [ -633.3 ..  633.1] mm   span 1266.4
Y [-1353.5 ..  432.3] mm   span 1785.9   <- pelvis-centred
Z [ -148.5 ..  137.1] mm   span  285.6
```

Height correct, frame wrong. The 3 August session re-zeroed the avatar files
already sitting in storage and repointed the database. **The handler that
produces them was never fixed**, so every avatar this endpoint made carried the
bug in, and Stage 3 would have baked appearance on top of it.

### Why it is invisible

The drape handler's `_is_prefitted` fails on both of its conditions in a
pelvis-centred frame: no garment vertex lands within 50 mm of a body vertex, and
the garment's Y span is not inside the body's. `align_meshes` then falls through
to its rescale branch. A garment scaled far too large never intersects the body,
so `body_collisions` and `residual_inside` both report 0 and every metric looks
clean.

### The fix

`_zero_to_floor(verts_mm)` translates each mesh so its lowest vertex sits at
Y=0. Y only: `align_meshes` does its own torso-filtered XZ centering and shifting
X or Z here would fight it. Applied to A-pose and T-pose right after the mm
conversion.

Measurements still run on the untranslated metre-space T-pose, so the
measurement path is unchanged. The offsets are recorded in the npz
(`apose_feet_offset_mm`, `tpose_feet_offset_mm`, `frame_convention`) and the
response gains `frame_convention` plus a `frame_check` block read back off the
arrays that were actually written. File keys and the file set are unchanged, so
the backend needs no change.

### Verified in production, same photo before and after

```
BEFORE   Y [-1329.9 ..  426.2] mm    frame_check absent
AFTER    Y [     0.0 .. 1756.1] mm    feet_on_floor: true
```

A-pose offset -1329.888 mm, T-pose offset -1330.072 mm. They agree to 0.18 mm,
which they must, since the legs are unposed in both. **Every measurement is
identical across the two runs**, which is the empirical proof that the
translation cannot move a reported number.

### End to end against the garment that caused it

La Fam `denim-slogan-jeans/sj_m.obj`, 34,024 verts, 1.021 m, run through the
drape branch's own `_normalize_to_meters`, `_is_prefitted` and `align_meshes`:

```
BEFORE   _is_prefitted = False   scale 1.720249   jeans 1.021 m -> 1.756 m,  dy -2.14 m
AFTER    _is_prefitted = True    scale 1.000000   jeans 1.021 m -> 1.021 m,  dy  0.00 m
```

1.720 rather than the 1.771 on record because this body is 1.756 m and that one
was slightly taller. Same mechanism, now closed.

Regression gate kept as `avatar-creation-photoreal/scripts/verify_floor_frame.py`.
It imports `_zero_to_floor` from the real handler and pulls
`_is_prefitted` + `align_meshes` from `git show drape:...` on every run, so it
cannot drift from what is deployed. Exit 0 means fixed. Run it before any
photoreal build.

**Note on branches:** the working-tree `avatar-creation/draping/handler.py` on
`feature/photoreal-avatar` is around v45.x and has no `_is_prefitted` at all. The
deployed v47.1 lives on the `drape` branch. Test against the branch, not against
the copy sitting next to you.

---

## Two open findings from the same session

### The stored test photo is sideways

`lhm-artifacts/inputs/2026-05-20/user_001.jpg` is 3088x2316 landscape with EXIF
orientation 5. Most loaders ignore EXIF, so the pose estimator almost certainly
saw the subject lying on their side. **That is the photo the July "Stage 2b green
at v0.9" result was measured on**, and it reported `is_full_body: true` with a
plausible 16-key bundle, which is how it went unnoticed.

Today's runs used the preprocessed `inputs/1779046184_user_001_padded.jpg`
(2316x3860, upright, 3:5). The preprocessing is still a manual step outside the
pipeline, so any phone upload hits this. The EXIF and padding work was flagged
back in May as "a small followup PR" and never landed.

### Height normalization inflates every girth uniformly

On the upright photo, Multi-HMR estimates an intrinsic height of **173.75 cm**.
Passing the subject's 192 cm applies a **1.105x normalization to every
measurement**, which is isometric and therefore wrong for a lean tall build:

| | at intrinsic 173.75 cm | normalized to 192 cm |
|---|---|---|
| waist | 88.05 | 97.3 |
| chest | 101.49 | 112.2 |
| hips | 99.65 | 110.1 |
| head | 56.22 | 62.1 |

Head 62.1 cm is well above a typical adult male 57. This is not a regression:
the old pipeline produced 192/109/95/109 on 22 May, the same family of numbers.
It is a standing property of how height normalization works here.

It matters more now than it did, because the shopper MCP exposes
`recommend_size`, and a number said by ChatGPT carries the host's authority with
no widget around it to soften the claim.

**Unconfirmed:** 192 cm / 78 kg were taken from the May test passport, not
confirmed by Revan this session. The normalization factor swings everything, so
confirm before drawing conclusions from the table above.

---

## Still blocking, unchanged

`size_chart` is `{}` on all four La Fam garments and `tryon-config` substitutes a
hardcoded fallback, so size recommendation states an invented number with full
confidence. Flagged on 4 August, still open, and it gets worse the moment the MCP
exposes it.

---

## Next session

1. Privacy policy and support page on tryon.global. Both directories reject
   without one and Anthropic calls it an immediate rejection.
2. OAuth 2.1 authorization server in FastAPI in front of Supabase Auth. This is
   the only genuinely new backend engineering in the MCP track.
3. Revan: Apple Developer enrolment plus the D-U-N-S check, Claude Team plan
   (the gate on the submission portal), verified org on the OpenAI platform.
4. Revan: 3 to 4 guided photos for Stage 3, and confirm height and weight.
