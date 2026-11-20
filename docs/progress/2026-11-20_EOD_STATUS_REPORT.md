# Status, 2026-11-20 (end of day)

## Short version

- The new measurement endpoint is built and works, but the model behind it is **not accurate enough to ship**. It
  read Revan's chest as 101.7 cm against a tape of 110. The same pattern shows on held-out people: anyone far from
  the average for their height and weight is pulled back towards it.
- A new acceptance bar was set today: **every measurement at least 97% accurate for 96 of 100 people**, judged per
  person, not on the average. The current model fails it on every measurement.
- Nothing was committed, pushed or deployed today. Production is exactly as it was this morning.
- Vanrycke opted out for now (too busy); contact again at the beginning of 2027. Brave Particle is the only client
  deadline.

## Done today

**Measurement endpoint (`2jsyed38mp4uj8`)**
- Created on RunPod from branch `feature/measure-worker`; first build passed.
- Ping: every model loads on the GPU (RTX 4090). Cold start about 19 s, warm requests 0.6 to 2.5 s.
- Full-body test photo (192 cm, 83 kg, male): chest 101.7, waist 88.6, hips 103.3, identical to the local run.
- Mirror selfie, cropped photo and missing weight are each refused with the right message.
- Not wired into production: `RUNPOD_MEASURE_ENDPOINT_ID` is not set on Railway.

**Backend fix found while testing (uncommitted, analytics worktree)**
- RunPod reports a refused photo as a failed job. The measure route would have shown the generic "could not be
  completed" message instead of the worker's instruction to the tester. Fixed in `measure.py`.
- `check_measure_route.py`: two cases added in the shape RunPod really sends, and an ordering flake in the script
  fixed. 45 of 45 checks pass, six runs in a row.

**Photo girths inside the avatar job (uncommitted, default off)**
- `avatar-creation-measure/embedded.py` (new, in the lhm worktree): the measurement model as a module. Gives the
  same girths as the standalone worker on all three real test photos.
- `avatar-creation-lhm/handler.py`: the production avatar job returns the nine photo girths next to today's
  measurements (`measurements_photo`). `measurements` itself is unchanged, and the step can never fail the job.
- `avatar-creation-lhm/Dockerfile.runpod`: bakes the segmenter and the network in, with a selftest at build time.
- Backend: new setting `AVATAR_MEASUREMENTS_SOURCE` (default `mesh`), and every new avatar logs both sets as an
  `avatar_measurements_compare` event.
- Local checks: 10 of 10 on real photos through the real handler, 4 of 4 on model failures, 8 of 8 on the backend
  helper. An independent review found one unstaged file and one mislabelled error; both fixed.
- Not tested: the Docker build, and the step running next to the avatar model on the GPU.

## The accuracy finding

Shipped model, 487 held-out people, front + side outlines:

| | Average accuracy | People at 97% or better |
|---|---|---|
| Hips | 98.3% | 86% |
| Leg length | 98.3% | 87% |
| Chest | 97.9% | 76% |
| Waist | 97.3% | 65% |
| Bicep | 96.7% | 55% |
| Wrist | 96.5% | 50% |

- **People far from average are read wrong.** 13% of people have a chest 6 cm or more away from what height and
  weight predict. For them the chest error is 6.1 cm from a front photo and 4.3 cm with a side photo as well. The
  model picks up 28% of a person's deviation from the front and 46% with the side.
- **On Revan:** waist 88.6 against 89 and hips 103.3 against 100.5 are fine; chest 101.7 against 110 is not. The
  old avatar path said 118.2, so on chest the new model is no better, only wrong in the other direction.
- **Training-data gap:** of the 1,218 men the model trained on, 230 are within one BMI point of Revan and none has
  a chest of 110 (largest 107.9). Only 44 are 190 cm or taller.
- **Coarse input:** outlines are 160 x 120 pixels, about 1.2 cm of body per pixel.

**20/80 split (501 people trained, 2,004 tested), finished 17:54**

| | 20/80 split | Shipped model (2,018 trained) |
|---|---|---|
| Average error, 14 measurements | 12.4 mm | 12.2 mm |
| Chest, average error | 2.3 cm | 2.1 cm |
| Chest, people far from average | 5.9 cm | 4.5 cm |
| Chest, people at 97% or better | 73% | 76% |

Four times as many training people barely moves the overall result and helps the unusual builds only slowly. More
of the same data will not reach the bar. The two columns are tested on different people and each is one training
run, so a point or two either way is noise.

Sheets in `~/Downloads`: `chest_outliers_front_side.png` (eight held-out men built like Revan),
`measure_training_data.png` (inputs, splits, who the model learned from).

## Decisions made today

- Acceptance bar: 97% accurate for 96% of people, per measurement. Revan's tape reading is ground truth.
- Brave Particle does not get the link until the bar is met or lowered.
- The avatar pipeline stays on today's measurements (`AVATAR_MEASUREMENTS_SOURCE` stays `mesh`).
- Splits 40/20/40 and 80/20 and the 320 x 240 model are held for tomorrow.
- Vanrycke work stops. The AR pages stay live; the backend and Shopify half stays parked, uncommitted.

## Tomorrow, in this order

1. Start the held runs so they train while we work: splits 40/20/40 and 80/20
   (`.local_prototype/measure_ml/run_splits_queue.sh`, take 20/80 out of its list), then
   `cnn_bodym_hr.py ../bodym official 30 0`. Score each with `split_report.py`.
2. Go through the ML concepts again and choose: cross-validation, slice evaluation, learning curve, a real
   tape-measured test set, transfer learning, synthetic data, ensembling, reweighting, uncertainty estimation,
   active learning.
3. Deep research: how the leading labs train and keep improving models, aimed at body measurement from photos
   and at a loop that lets our model improve over time. End with what is realistic on a laptop or a small GPU.
4. Find where to get more data: synthetic bodies, other public datasets, Brave Particle's tailor measurements
   with the customer photos, a public vision model trained on people to start from.

## Open

- **RunPod balance** was $8.57 at 16:47 and also pays for production. Training on a rented GPU needs a top-up; on
  the laptop (4-core i5) one run fills the machine, so runs cannot be done in parallel.
- **Drape endpoint min workers:** set to 1 for Web Summit and due back to 0 after 2026-11-12. Not confirmed today
  (the RunPod management API could not be reached from the session). If it is still 1 it bills around the clock.
  Its max workers went from 3 to 2 today to make room for the measure endpoint.
- **Measure endpoint name:** it was created as `tryonline`, the same name as the old avatar endpoint. Rename to
  `tryonline-measure` if not done yet. It runs with max workers 1.
- **Uncommitted work in two worktrees.** `/Volumes/SanDisk/mvp_pipeline-lhm`: the avatar handler change (a push
  to `feature/lhm` rebuilds the production avatar endpoint). `/Volumes/SanDisk/mvp_pipeline-analytics`: the
  measure route fix, the avatar measurement switch, this morning's measure page changes, and the parked Vanrycke
  files, which must not be swept into another commit.
- **Dockerfile cache-bust:** the avatar Dockerfile says to bump `CACHEBUST` on every push; the last six pushes
  did not. Decide at push time.
- From before today, unchanged: the TryOn Size Shopify submission, and the idle timeout and H100 question on
  `tryonline-lhm`.
