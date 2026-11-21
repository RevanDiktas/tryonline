# Status, 2026-11-21 (end of day)

## Short version

- The single measurement network was taken apart and rebuilt as a **five-stage pipeline** (locator, measurer,
  specialists, reconciler, confidence). All five stages exist in code and have been run end to end on people the
  model never trained on.
- On real people the pipeline is better than the old network but **not at the bar**: average error 10.4 mm
  against 11.7 mm, chest within 3% for 81% of people against 75%. The bar is 96%.
- On computer-generated bodies with exact measurements and **clean capture**, the same pipeline **meets the bar on
  four measurements** (hip 97.5%, ankle 97.2%, chest 96.8%, arm length 96.5%). Under realistic capture it does
  not. A third photo does not help. The gap is in how the photo is taken and cut out, not in the number of views.
- Nothing was committed, pushed or deployed. The measure endpoint and the avatar pipeline are as they were.
- The acceptance bar stays exactly as Revan set it (every measurement within 3% for 96 of 100 people). Outside
  research is a source of methods and data only.

## The bar and the direction (Revan, today)

- The bar is ours and is not adjusted to what published work reaches.
- Pursue both more data and a smarter approach; if one is blocked, push the other ten times harder.
- Build a pipeline of several networks and scripts that each narrow the answer, not one network.

## What was built (all in `.local_prototype/measure_ml/`)

| Stage | File | State |
|---|---|---|
| 1 Locator + 2 Measurer | `pipe_profiles2.py` (version 1: `pipe_profiles.py`) | Works on all 8,978 BodyM photos at full size (about 2 mm per pixel) |
| 3 Specialists (torso, arms, legs) | `pipe_specialists.py` | Trained and scored |
| 4 Reconciler | `pipe_reconciler.py` | Trained and scored |
| 5 Confidence | `pipe_confidence.py` | Runs, but does not work yet (see below) |
| Synthetic pretraining | `pipe_pretrain.py` | Runs, no measurable gain |
| Synthetic tests | `pipe_synth_ceiling.py`, `pipe_synth_views.py`, `pipe_synth_capture.py` | Run |

Synthetic bodies (second session, `.local_prototype/synth/`): 2,000 bodies from the Anny body model (Apache 2.0
code, CC0 assets; the optional SMPL-X topology is non-commercial and was not used), each with front and side
outlines in BodyM's format, 14 exact measurements, plus clean, 45-degree and back renders of the same bodies.
ANSUR II table: `ansur_table.py`, `ansur_table.npz`.

## Results on real people

Old single network, by number of training people (front + side, one run each, different test people):

| Split | People trained | Average error, 14 measurements | Chest deviation recovered |
|---|---|---|---|
| 20/80 | 501 | 12.4 mm | not recorded |
| 40/20/40 | 1,002 | 11.7 mm | 38% |
| 80/20 | 2,004 | 10.7 mm | 47% |
| Dataset's own | 2,018 | 12.2 mm | 46% |

Pipeline on the 40/20/40 split (1,002 trained, reconciler fitted on 501, scored on 1,002 unseen people):

| Share of people within 3% | Old network | Specialists | Pipeline with reconciler |
|---|---|---|---|
| Arm length | 89.4% | 88.3% | 92.5% |
| Leg length | 89.7% | 90.4% | 92.1% |
| Hip | 86.9% | 88.9% | 89.7% |
| Shoulder to crotch | 86.0% | 88.2% | 88.9% |
| Shoulder breadth | 78.7% | 82.3% | 85.0% |
| Chest | 75.3% | 80.2% | 81.9% |
| Thigh | 70.5% | 73.4% | 75.2% |
| Forearm | 58.5% | 71.8% | 72.2% |
| Calf | 63.4% | 72.7% | 71.6% |
| Waist | 68.6% | 66.8% | 70.2% |
| Ankle | 60.5% | 70.4% | 68.9% |
| Bicep | 46.8% | 62.9% | 64.8% |
| Wrist | 53.9% | 62.7% | 60.8% |
| Average error, 14 measurements | 11.7 mm | 10.8 mm | 10.4 mm |

Average accuracy of the pipeline is 97.9% across the 13 measurements (old network 97.6%, height and weight alone
97.1%). The share of a person's chest deviation recovered rose from 38% to 51%, bicep from 19% to 50%.

What helped and what did not:

- **Helped:** full-size outlines with one specialist per body region (largest gains on wrist, ankle, calf,
  bicep, forearm); the reconciler.
- **No measurable effect:** the locator fix for heavy people and arms against the body (leg mismatches fell from
  40 photos to 5, crotch spread for BMI 35+ from 9.3 to 4.9 cm, but scores did not move); ANSUR II measurement
  relations; pretraining on synthetic bodies.
- **Does not work yet:** the confidence stage. The signs of trouble barely track the real errors (the most-sure
  half of people are right on chest 87% of the time, the least-sure quarter 76%), so almost nothing is released
  at the bar. The networks and the repeated photos make the same mistake on the same person.

## Results on synthetic bodies (exact measurements, 1,598 trained, 400 tested)

| Share within 3% | Realistic front + side | Clean front + side | + 45 degrees | + back | + both |
|---|---|---|---|---|---|
| Hip | 87.2 | 97.5 | 89.8 | 87.0 | 87.2 |
| Ankle | 73.0 | 97.2 | 72.8 | 67.0 | 67.8 |
| Chest | 85.2 | 96.8 | 83.2 | 84.5 | 84.8 |
| Arm length | 81.5 | 96.5 | 81.0 | 76.2 | 78.8 |
| Calf | 84.0 | 95.0 | 82.0 | 82.0 | 79.8 |
| Thigh | 80.2 | 93.8 | 78.5 | 76.2 | 79.8 |
| Waist | 80.5 | 92.5 | 81.5 | 78.8 | 80.8 |
| Leg length | 85.5 | 92.0 | 85.0 | 85.8 | 86.0 |
| Wrist | 49.8 | 91.5 | 48.8 | 49.2 | 51.5 |
| Shoulder to crotch | 83.5 | 89.2 | 80.8 | 84.0 | 82.0 |
| Forearm | 67.0 | 87.5 | 64.8 | 65.5 | 61.5 |
| Shoulder breadth | 58.0 | 84.5 | 57.8 | 56.8 | 59.5 |
| Bicep | 54.5 | 80.8 | 54.2 | 52.2 | 49.8 |
| Average error | 10.1 mm | 6.1 mm | 10.3 mm | 10.4 mm | 10.5 mm |

"Realistic" = randomised phone camera 2 to 4 m away, arm and leg angles, slight turn, hair on half the bodies,
rough edges. "Clean" = flat camera, fixed pose, no hair, clean edges.

- Deviation recovered on chest: 90% clean, 78% realistic, about 45% on real people.
- Giving the network the camera distance and height changed nothing (10.0 mm against 10.1 mm), so the camera's
  position is not the main cost. That leaves pose, turn, hair and outline roughness.
- The same test with every capture setting given to the network (pose, turn, hair, edge roughness) was still training when this report was written; its result is in `.local_prototype/measure_ml/pipe_synth_capture_v2.log`.
- These are synthetic bodies. They show what the pipeline can do with clean outlines; they do not show it on
  real people.

## Data found today

- **ANSUR II** (6,068 tape-measured people, numbers only, already on disk): two to three times BodyM's count of
  very tall, very short and heavy people. Only 6 of our 14 measurements map cleanly, with offsets up to 3.8 cm,
  so it cannot be mixed in as labels. It has 1 man with chest 110+ at BMI under 25 (BodyM has 3).
- **Synthetic bodies:** cover every tail, including 105 men with chest 110+ at BMI under 25. Weak points: women
  too wide below the chest (+4.7 cm waist, +6.0 cm hip against BodyM women), no very large-busted heavy women,
  calf reads 3.2 cm high.
- **No public dataset** pairs photos with measurements for muscular, very tall or very heavy people. Research
  report: `~/Downloads/Body measurement model training.md`.
- **BodyM's reference values are computed on fitted 3D scans, not taped.** Agreement with a tailor's tape can
  only be tested on tape-measured people.

## Documents made today (in `~/Downloads`)

- `TryOn_measurement_pipeline_paper.pdf` (and two page images): two-page technical note in research-paper
  format, Revan as author. It claims no pipeline accuracy; today's results are not in it yet. Its five
  references were not checked against the sources.
- `TryOn_pipeline_map.png`: the pipeline on one real person.
- Explainer page: https://claude.ai/artifact/BcgmY4W9nZjGDQXGN4KjA1 (private until shared).
- `pipe_locator_check.png`, `synth_bodies_check.png`, `synth_bodies_2000_check.png`, `synth_views_check.png`.

## Tomorrow, in this order

1. **Find which capture condition costs the accuracy.** Render the synthetic bodies clean plus one condition at
   a time (pose, turn, hair, rough edges, camera) and score each. Whatever costs the most is what the app must
   control or the pipeline must undo.
2. **Carry that to real photos.** Either normalise the outline before measuring (pose and turn), or tighten the
   capture in `measure.html` (arm position, hair tied back, phone position), or both.
3. **Check real outlines against synthetic clean ones.** BodyM's outlines include clothing and hair; see how far
   they are from the clean case, since that bounds what BodyM alone can teach.
4. **Tape-measured test set.** Ask Brave Particle for customer photos with tailor measurements, each measured
   twice. This is the only way to test against a tape, and it needs Revan to ask.
5. **Confidence stage:** revisit once errors are no longer shared by every opinion.
6. Add today's results to the paper and check its references.

## Open

- **RunPod balance** was $8.57 on 2026-11-20 and also pays for production. Everything today ran on the laptop.
  Larger synthetic sets or image networks need a top-up of about $50.
- **Brave Particle** does not get the measure link and `AVATAR_MEASUREMENTS_SOURCE` stays `mesh` until the bar is
  met on real people.
- **Two photos the new locator fails on** (of 6,134) have not been looked at.
- **The 320 x 240 run of the old network** was taken out of the queue; the pipeline already works at full size.
- From 2026-11-20, unchanged: drape endpoint min workers (due back to 0), the measure endpoint's name, the
  uncommitted work in the `lhm` and `analytics` worktrees, the TryOn Size Shopify submission.
- Everything from today is uncommitted and lives under `.local_prototype/`, which is untracked.
