# End of day, 2026-11-26: chest from photos

## Short version

- **Chest is not solved.** The live worker still reads your chest at about 99 against a tape of 110. Nothing was
  deployed today; the worker on RunPod is unchanged (`v0.3-street`).
- **Every cheap photo-only route has now failed the same test.** Today added five: retraining on arms-down
  photos, a surface-shape model trained on synthetic bodies, a geometry rebuild of the chest, Meta's SAM 3D Body,
  and trusting the outline more.
- **The photos do carry chest signal, but too little of it survives.** Shuffling the photos between people always
  made chest worse, and your side photos show your chest 3 to 4.5 cm deeper than men of your height and weight.
- **Waist, thigh and forearm hold on your photos** in every run today. Hip held on the earlier photos and missed
  on tonight's.
- **Spend:** $0.87 of the day's budget (balance $22.21 this morning, $21.34 now). No GPU is rented.
- **What is left for chest:** real photos with tape measurements (Brave Particle fittings), or the iPhone depth
  sensor in the iOS app.

## The day in order

| Time | What happened |
|---|---|
| 07:00 to 08:00 | Three go/no-go tests on the 24 real people failed: side-outline depth (0.23), the same with arms cut out (0.23), Meta's Sapiens shape reader on the front photo (−0.13). Needed 0.35. |
| 08:20 to 08:45 | Arms-down retrain finished on the laptop. No gain. |
| 08:48 to 18:34 | **Lost.** The first terminal hung on a small local test because the internal disk was full. Nothing ran while you were at work. |
| 18:36 to 18:45 | First terminal recovered and rented a GPU that could not be connected to. Work moved to this terminal on your instruction; the first terminal confirmed the handover. |
| 18:45 to 20:15 | Surface-shape run on a new GPU, scored on real people with three sizes of shape reader. Failed. |
| 20:45 to 21:20 | Your two new photos through the live worker; geometry rebuild; hip check; SAM 3D Body after Meta approved access. All failed on chest. |

## What was tested today

The test is the same each time: on the 24 real people with tape-measured chests, does the method pick out people
whose chest is bigger or smaller than height and weight suggest? The bar is 0.35 on a 0-to-1 scale, or beating
the live worker's 2.30 cm chest error.

| Route | Result | Verdict |
|---|---|---|
| Retrain on arms-down photos only | Catches 38% of a bigger-than-expected chest, the same as before; arms-out photos also 38% | Arm position is not the cause |
| Trust the outline more (scale the photo reading up to full strength) | Average chest error rises from 2.4 to 4.0 cm; big chests do not improve (5.9 to 5.6) | Dead |
| Surface-shape model trained on 10,000 synthetic bodies | Synthetic bodies: chest error 1.0 cm. Real people: 4.91, 4.46 and 4.34 cm with the small, medium and largest shape reader | Fails on real photos |
| Geometry rebuild (front width and side depth, arms cut off using the shape reader) | 0.26 | Fails |
| SAM 3D Body (Meta, trained on real photos) | Chest −0.08, waist −0.03, hip +0.53 | Fails on chest |

- **Synthetic to real is the break.** Outlines, colour and surface shape all work on synthetic bodies and all
  fail on real photos. The surface-shape model read synthetic chests to 1 cm through a baggy shirt.
- **The signal grows with a better shape reader** (0.29, 0.34, 0.44 across the three sizes), but stays far from
  beating the live worker.
- **Repeat photos explain part of the noise.** On BodyM, two side photos of the same person differ by 1.0 to
  1.4 cm in chest depth, while real differences between people of the same height and weight are only about
  1.6 to 2.1 cm.
- **SAM 3D Body's hip reading is real but small.** Adding it to the height-and-weight estimate brings hip error
  from 3.40 to 3.05 cm on these 24 people (live worker 3.27). Not pursued; hip is not the problem.

## Your photos

Tape: chest 110, waist 89, hip 100.5, thigh 59, forearm 29.

| | Live worker, earlier photos | Live worker, tonight's photos | Surface-shape model | SAM 3D Body |
|---|---|---|---|---|
| Chest | 99.1 | 97.9 | 98.8 | 115.6 to 118.6 |
| Waist | 88.6 | 88.4 | 91.3 | 97.2 to 100.4 |
| Hip | 100.1 | 103.9 | 100.1 | 121.1 to 122.3 |
| Thigh | 58.9 | 60.6 | not read | not read |
| Forearm | 27.5 | 27.3 | not read | not read |

- **Every model reads your photos as less chest and more waist.** The surface-shape model took 1.5 to 2.6 cm off
  your chest and added 3 to 4.4 cm to your waist on every version.
- **SAM 3D Body makes everything bigger and does not see your build.** Its chest-to-waist ratio for you is 1.18
  to 1.19; your real ratio is 1.24, and it gives the average man in the test group 1.17.
- **The 112 you saw on an old avatar** came from the old avatar path on 19 November. The same run gave waist 97.6
  and hips 110.5, and three other photos that evening gave chest 109.7, 117.5 and 118.2. That path inflates every
  girth by 5 to 11%; it hit your chest by accident.

## Hip on tonight's photos

| Photos used | Hip (tape 100.5) |
|---|---|
| Earlier front + earlier side, one of each (4 combinations) | 100.1 to 100.7 |
| New front + earlier side | 101.8 |
| Earlier front + new side | 101.0 |
| New front + new side | 103.9 |

- One photo per view is fine: single pairs give the same hip as the four-photo run.
- Both new photos push hip up. The worker labelled the track pants "straight", the same as the jeans, so looser
  fabric got the same allowance. The new photos were also taken from further away; these six photos cannot
  separate the two causes.
- To settle it: one more pair in jeans from the same spot as tonight's photos.

## What was not done

- **Brave Particle message:** drafted in the session, not sent. Three assumptions in it need your confirmation:
  about a minute per fitting, a consent step on the capture page (not built), and starting with 20 fittings.
- **iPhone depth sensor capture:** not started. It is an app feature, not a quick test.
- **Price of the paid 1,000-person photo set:** not asked.
- **Today's report is not committed.**

## Housekeeping

- **Internal disk:** 1.8 GB free became 8.0 GB by clearing re-downloadable caches (uv, npm, pip, the Cursor
  updater download, a Rust build cache, Xcode's symbols for your iPhone). Cursor's stored chats (about 6.3 GB),
  the iOS simulators and Chrome's data were left alone.
- **Test photos saved:** the 24 people's photos, your six photos and the first terminal's scripts were copied
  from a temporary folder to `.local_prototype/measure_ml/diag_2026-11-26/`. A reboot would have wiped them.
- **Your photos on the live endpoint:** sent through a private temporary bucket each time and deleted afterwards.
- **Hugging Face:** your account now has access to Meta's SAM 3D Body models; your name, date of birth and
  country were shared with Meta to get it.
- **RunPod:** four GPUs rented and ended today; one could not be connected to and was ended after about four
  minutes. The GPU helper and key are in `.local_prototype/synth/gpu/`.

## Where the files are

| What | Where |
|---|---|
| Surface-shape training and real-photo scoring | `.local_prototype/synth/rgb_pilot/pilot3.py`, `score_real3.py`, `score_real3_1b.py`, `score_real3_2b.py` |
| Shape-reader maps of the real photos (three sizes) | `.local_prototype/synth/sapiens/sapiens_out.npz`, `sapiens_out_1b.npz`, `sapiens_out_2b.npz` |
| Geometry rebuild | `.local_prototype/synth/sapiens/geo_chest.py` |
| SAM 3D Body run and scoring | `.local_prototype/synth/sam3d/run_sam3d.py`, `score_sam3d.py`, `sam3d_out.npz` |
| Direct outline read and repeat-photo noise | `.local_prototype/measure_ml/chest_direct.py`, `edges_side.npz` |
| Live-endpoint test scripts | `.local_prototype/measure_ml/diag_2026-11-26/live2.py`, `live_pairs.py` |

## Decisions for you

1. **Send the Brave Particle message?** It is the only route left that gives the model real clothed photos with
   tailor-measured chests.
2. **Start the iPhone depth capture** as part of the iOS app work?
3. **Launch with the live worker as it is**, with chest shown as an estimate, while 1 or 2 runs?
4. **One more photo pair in jeans** from tonight's spot, to settle the hip question.
