# Status, 2026-11-22 (end of day)

## Short version

- Step 1 of yesterday's plan is done: the synthetic bodies were rendered clean plus one capture condition at a
  time, and each was scored with the same split and networks as yesterday.
- **Three conditions cost accuracy: edge roughness, pose and camera. Three cost nothing: turn, framing and (almost)
  hair.** Pose and camera together cost more than the two apart.
- The synthetic edge is about twice as rough as real outlines, so on real photos **pose and camera are the costs
  that carry over**. With clean edges the realistic set scores 8.3 mm (chest 91.5% within 3%), against 6.2 mm
  clean (chest 96.2%) and 10.1 mm fully realistic (chest 83.5%).
- The cost does not come from extreme captures: error is the same at 2 m and at 4 m, and across arm angles.
- **The variation is learnable from data.** Showing the network each training body under three captures instead
  of one brings the clean-edge realistic set from 8.3 mm to 6.9 mm on the same test bodies, with chest, hip and
  ankle back at the bar. Training four times longer on one capture makes it worse (9.1 mm). Synthetic only so far.
- A side photo with the feet cut off is harmless alone, but costs about 5 points on chest and waist when the side
  photo is also at a different scale from the front one, which is what real photos have.
- Nothing was committed, pushed or deployed. The measure endpoint and the avatar pipeline are as they were. The
  acceptance bar is unchanged and is not met on real people.

## How it was run

Two Claude sessions. The second (`mvp-pipeline-16`) rendered; this one scored.

- Renders: `.local_prototype/synth/make_conds.py` (new). `render_pair_cond` makes every random draw the realistic
  renderer makes and applies only the switched-on conditions. Checked on 20 bodies: all six on reproduces
  yesterday's realistic masks and all six off reproduces the clean masks, 0 pixels different both ways. Contact
  sheet: `~/Downloads/cond_contact_sheet_synth_02165.png`. Files: `synth/out2/cond_<name>.npz`.
- Scoring: `.local_prototype/measure_ml/pipe_synth_conditions.py` (new), queue script `score_next_condition.sh`.
  Results in `pipe_synth_conditions_v2_s0.json`, per-body predictions in `pipe_synth_conditions_pred_v2_s0_*.npz`.
- Controls: clean scored 6.2 mm (6.1 yesterday) and realistic 10.1 mm (10.1 yesterday). Single measurements move
  by up to about 2 points between identical runs; 400 test bodies. Differences of a point or two mean nothing.

## Results (1,598 synthetic bodies trained, 400 tested, share within 3% of the exact value)

One condition added to clean capture:

| | Clean | Edge | Pose | Camera | Hair | Turn | Framing | Realistic (all six) |
|---|---|---|---|---|---|---|---|---|
| Ankle | 96.5 | 90.0 | 97.2 | 93.0 | 97.8 | 96.8 | 96.5 | 73.2 |
| Arm length | 97.0 | 94.2 | 90.5 | 96.0 | 95.8 | 97.0 | 96.0 | 82.2 |
| Bicep | 78.5 | 65.5 | 79.2 | 73.2 | 77.0 | 80.0 | 81.2 | 55.0 |
| Calf | 96.0 | 92.2 | 94.8 | 93.5 | 94.5 | 95.5 | 96.8 | 82.8 |
| Chest | 96.2 | 94.8 | 96.2 | 94.0 | 97.0 | 96.8 | 97.8 | 83.5 |
| Forearm | 86.8 | 76.8 | 84.0 | 84.8 | 86.8 | 88.0 | 88.8 | 69.0 |
| Hip | 97.5 | 95.0 | 94.8 | 96.5 | 96.8 | 97.8 | 97.5 | 88.0 |
| Leg length | 92.2 | 89.2 | 88.5 | 89.8 | 90.5 | 90.5 | 90.0 | 85.5 |
| Shoulder breadth | 85.0 | 74.5 | 78.2 | 76.8 | 83.0 | 86.2 | 85.2 | 57.8 |
| Shoulder to crotch | 89.5 | 87.0 | 89.2 | 88.0 | 89.0 | 89.0 | 89.0 | 83.5 |
| Thigh | 93.2 | 86.0 | 89.8 | 90.0 | 92.2 | 92.8 | 93.2 | 79.2 |
| Waist | 92.8 | 88.2 | 90.5 | 90.2 | 92.2 | 93.2 | 92.8 | 80.0 |
| Wrist | 90.8 | 59.5 | 87.8 | 89.8 | 90.8 | 93.2 | 92.2 | 51.5 |
| At the bar (of 13) | 5 | 0 | 2 | 2 | 3 | 4 | 5 | 0 |
| Average error, mm | 6.2 | 7.8 | 6.9 | 6.9 | 6.4 | 6.1 | 6.1 | 10.1 |

Combinations and the two real-photo conditions:

| | Clean | Pose + camera | Realistic, clean edges | Side scale | Side cut | Side cut + scale |
|---|---|---|---|---|---|---|
| Chest | 96.2 | 91.8 | 91.5 | 97.5 | 96.8 | 96.2 |
| Waist | 92.8 | 88.8 | 86.8 | 93.0 | 92.5 | 90.0 |
| Hip | 97.5 | 93.5 | 92.8 | 97.8 | 97.8 | 96.0 |
| Shoulder breadth | 85.0 | 68.8 | 67.8 | 85.2 | 84.8 | 82.0 |
| Bicep | 78.5 | 69.5 | 68.5 | 80.5 | 80.8 | 79.0 |
| Wrist | 90.8 | 80.5 | 79.2 | 90.0 | 91.0 | 90.2 |
| Average error, mm | 6.2 | 8.0 | 8.3 | 6.2 | 6.2 | 6.6 |

What the numbers say:

- **Edge roughness (+1.6 mm alone, 1.8 mm inside the realistic set)** falls on the small girths: wrist 90.8 to
  59.5, bicep 78.5 to 65.5. Measured on 300 masks each, BodyM's real edges wander 0.34 px (front) and 0.45 px
  (side), the same as synthetic clean (0.34 / 0.40); synthetic realistic is 0.81 / 0.95. So yesterday's
  "realistic" overstated this, and real outlines are already clean at this scale.
- **Pose (+0.7 mm)** hits shoulder breadth, arm length, leg length and hip; chest is untouched.
- **Camera (+0.7 mm)**, a phone 2 to 4 m away against a flat view, hits shoulder breadth, bicep and chest.
- **Pose + camera together: 8.0 mm**, against 7.6 if they simply added. That is nearly all of the realistic set
  with clean edges (8.3 mm).
- **Flat across the range.** Pose + camera by camera distance: 8.0 mm at 2.0 to 2.6 m, 7.9 at 2.6 to 3.3, 8.0 at
  3.3 to 4.0. Same for camera height and arm angle. The cost comes from having any variation with 1,598 training
  bodies, not from the far ends of it. Asking people to stand further back would not help by itself.
- **Hair (+0.2 mm overall, +0.4 on bodies with hair)**: waist and leg length lose 2 to 3 points because the
  person is scaled by outline height and hair adds to it.
- **Turn up to 5 degrees and framing: no cost.**
- **Side photo.** A different side scale alone: no cost, the pipeline rescales the side outline by its own
  height. Feet cut off alone: no cost, because the borrowed front scale is exactly right when both photos share a
  scale. Both together: on cut bodies whose side scale is off by 5% or more, chest goes 97.6 to 92.9 and waist
  94.1 to 88.2 (85 bodies).

## Real people (1,002 unseen, yesterday's pipeline predictions)

- A cut side photo goes with chest within 3% for 76.6% of people against 84.4% uncut. With height, build, sex and
  photo source held equal the cut still costs about 4.5 points on chest and 3.9 on bicep. This is observational.
  It matches the synthetic side cut + scale result.
- BodyM: 23% of train side photos are cut at the feet; side/front height ratio is 1.04 with sd 0.07. The synthetic
  realistic set had neither.
- Pose spread in BodyM (arm angle sd 0.14 rad, leg 0.06) is about the same as the synthetic realistic set.
- The realistic set with clean edges (8.3 mm, chest 91.5%) is the closest synthetic match to real photos, and real
  people score 10.4 mm, chest 81.9%. So real photos carry a further cost the synthetic set does not model:
  clothing, the side cut and scale, and outlines that are smooth but wrong at larger scale are the suspects.

## More captures per body (added 21:55)

Every body was rendered three more times with fresh random camera, pose and hair, clean edges
(`synth/out2/cond_no_edge_rep1.npz`, `_rep2`, `_rep3`). Training bodies are shown under several captures; the 400
test bodies keep their single original capture. Script: `measure_ml/pipe_synth_reps.py`.

| Share within 3% | Clean | Realistic, clean edges, 3 captures per body | 1 capture | 1 capture, trained 4x longer |
|---|---|---|---|---|
| Ankle | 96.5 | 96.5 | 89.0 | 79.8 |
| Arm length | 97.0 | 95.0 | 86.0 | 84.5 |
| Bicep | 78.5 | 71.8 | 68.5 | 58.5 |
| Calf | 96.0 | 94.0 | 89.5 | 85.2 |
| Chest | 96.2 | 96.0 | 91.5 | 92.0 |
| Forearm | 86.8 | 84.2 | 78.5 | 75.2 |
| Hip | 97.5 | 96.2 | 92.8 | 91.2 |
| Leg length | 92.2 | 88.8 | 87.2 | 85.5 |
| Shoulder breadth | 85.0 | 80.5 | 67.8 | 64.8 |
| Shoulder to crotch | 89.5 | 89.5 | 85.5 | 85.0 |
| Thigh | 93.2 | 88.8 | 86.0 | 81.5 |
| Waist | 92.8 | 91.2 | 86.8 | 84.5 |
| Wrist | 90.8 | 87.0 | 79.2 | 76.8 |
| Average error, mm | 6.2 | 6.9 | 8.3 | 9.1 |

- Three captures per body recover about two thirds of the gap between the clean-edge realistic set and clean.
- The gain is from the extra captures: four times the training on one capture overfits and scores worse.
- This is on synthetic bodies. It has not been tried on real people.
- **Four captures per body (finished 22:19): 6.8 mm, the same as three within run-to-run noise.** Ankle 94.5,
  arm length 96.0, bicep 71.5, calf 94.5, chest 95.0, forearm 85.0, hip 95.5, leg length 89.8, shoulder breadth
  80.0, shoulder to crotch 90.2, thigh 92.5, waist 92.2, wrist 85.0. The gain levels off at about three captures,
  and about 0.6 mm above clean remains. More captures of the same bodies will not remove it; more distinct bodies
  or normalising the outline for pose and camera are the candidates.

## Next session, in this order

1. Done: the four-capture score is in the section above.
2. **Carry it to real people:** pretrain on three captures per synthetic body, then fine-tune on BodyM. Yesterday's
   pretraining used one capture per body and gave no gain; several captures per body is the untried version.
3. **Side photo scale when the feet are cut:** take the side scale from a landmark both photos share (head top to
   crotch or to the shoulder line) instead of borrowing the front scale, and re-score real people. Also make
   `measure.html` refuse a side photo with the feet out of frame.
4. Compare BodyM's real outlines with the clean case beyond edge wander (clothing, larger-scale shape).
5. Tape-measured test set from Brave Particle (needs Revan to ask); confidence stage; paper. Unchanged.

## Other things today

- Accelerator application: suggested B2B / Enterprise Applications as primary category and Consumer Applications
  as secondary. Usage figures pulled from `analytics_events` (widget events, counted by distinct IP address,
  2 Oct to 21 Nov, team traffic not removed): about 16 daily, 75 weekly, 278 monthly active shoppers; day 1
  retention 24%, day 7 5%, day 30 0%; growth about 8% a month once the first window is scaled to 30 days.
- Supabase reports row-level security disabled on `brands` and `garments`. Not touched; needs policies first.

## Open

- From yesterday, unchanged: RunPod balance ($8.57 on 2026-11-20, not rechecked), drape endpoint min workers due
  back to 0, the measure endpoint's name, uncommitted work in the `lhm` and `analytics` worktrees, the TryOn Size
  Shopify submission, the two photos the locator fails on.
- The side-scale runs cap the side/front ratio at 1.10 for uncut bodies (frame size); cut bodies go up to 1.20.
- Everything from today is uncommitted and lives under `.local_prototype/`, which is untracked.
