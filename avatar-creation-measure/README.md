# avatar-creation-measure: measurement-only RunPod worker

Photos + height + weight + gender in, body measurements in cm out. No avatar, no textures, no network volume.
Drafted 2026-11-20. **Not built, not pushed, not deployed.** The checkpoint in `weights/` is a wiring-test model
whose numbers mean nothing; the Docker build refuses it.

```
photo(s) -> preprocess.py   segment the person (DeepLabV3), check the photo, frame like BodyM (720 x 960)
         -> model.py        silhouette CNN, averaged over the accepted shots -> 14 measurements
height + weight -> fit.py   SMPL-X body for display only
```

| file | what it is |
|---|---|
| `handler.py` | the worker (contract in its docstring) |
| `preprocess.py`, `test_preprocess.py` | copy of `.local_prototype/measure_core/` (photo gates; thresholds explained in `measure_core/GATES.md`) |
| `model.py` | `Net` / `meta` copied from `.local_prototype/measure_ml/cnn_bodym_v2.py`, plus loading and averaging |
| `fit.py` | copy of `.local_prototype/measure_core/fit.py` (SMPL-X to height + weight) |
| `weights/measure_cnn.pt` + `.json` | the measurement CNN and its version / SHA-256 sidecar |
| `scripts/local_invoke.py` | runs the real handler locally; **run it before every build** |
| `Dockerfile` | everything baked in; tests and a selftest run as build steps |

The three copied modules must stay identical to their sources (`diff` them before a build).

## Output keys and what they measure

BodyM computed its labels on SMPL meshes registered to 3D scans. It does not document the individual definitions;
what is written here is inferred from the values (see `.local_prototype/measure_ml/RESULTS.md`).

| our key | BodyM column | what it is, and the caveat |
|---|---|---|
| `chest` | chest | Chest girth. Runs about 3.7 cm above an ANSUR nipple-level chest for the same height and weight, so it is a "largest chest" measure. |
| `waist` | waist | Girth at about navel level, **not** a tailor's natural waist (which sits higher and is smaller). |
| `hips` | hip | Hip girth, 1.6 to 2.6 cm above an ANSUR seat (buttock) girth. |
| `thigh` | thigh | Thigh girth lower on the leg than a tailor's upper-thigh tape: about 5 to 6 cm smaller than a tape at the crotch. |
| `bicep` | bicep | Relaxed upper arm. A flexed bicep reads about 2 cm more. |
| `forearm` | forearm | Relaxed forearm. |
| `wrist`, `calf`, `ankle` | same | Girths; `ankle` is about 2 cm above a minimum-ankle tape. |
| `shoulder_width` | shoulder-breadth | Straight line between shoulder points on the body model, about 36 cm on average. **Not** a tailor's shoulder width and 3.4 cm narrower than bone-to-bone (biacromial). |
| `arm_length` | arm-length | Shoulder point to wrist on the body model, about 50 cm on average. Shorter than a sleeve length; definition unknown. |
| `leg_length` | leg-length | Inside-leg style length, about 78 cm on average. **Not** our older `inseam` key and not floor-to-crotch (that is about 4 cm more), so it is kept under its own name. |
| `torso_length` | shoulder-to-crotch | Top of shoulder to crotch. |
| `height` | (input) | The height the person stated, echoed. The model's own estimate is returned separately as `height_from_photo_cm`. |

Tailoring extras (`extras_keys` lists them): `neck`, `neck_base`, `shoulder_biacromial`, `shoulder_bideltoid`,
`shoulder_length`, `sleeve_outseam`, `sleeve_spine_wrist`, `back_length_waist`, `across_back`, `crotch_height`,
`waist_height`, `cervicale_height`. These come from `weights/ansur_extras.json`: a height + weight + age regression on
ANSUR II tape measurements (typical error 0.8 to 1.9 cm, age missing = 35). The photo does not change them.

Other fields:
- `height_weight_only`: the same keys from height + weight + gender alone, so a caller can show how far the photo moved each one.
- `method`: `front_and_side` or `front_only` (side missing or refused; the reason is in `notes` and `checks.side`).
- `checks.front[i]` / `checks.side[i]`: one entry per photo sent: `ok`, `reason`, `message` (a sentence for the tester), `numbers`.
- Refused front photo: `error` (the message), `reason` (the code), `checks`, and **no** `measurements`.
- `gender: "neutral"`: BodyM has only male and female, so the result is the mean of the two predictions; a note says so.
- `body.tpose_obj_base64`: SMPL-X T-pose, mm, feet on y = 0, 10,475 vertices in SMPL-X order, faces 1-indexed (about 0.8 MB of base64). `null` with a `reason` when height is outside 140 to 210 cm, BMI outside 15 to 45, or the fit does not converge; measurements are still returned. Send `"body": false` to skip it.
- Reasons: `missing_front_url`, `missing_height_cm`, `missing_weight_kg`, `missing_gender`, `bad_input`, `photo_too_large`, `unreadable`, `internal_error`, and the photo gates `no_person`, `landscape`, `several_people`, `too_small`, `cut_off_top`, `cut_off_bottom`, `cut_off_side`, `not_standing`, `arms_not_clear` (front), `not_side_view` (side).

## Before any build (project rule: verify locally first)

```bash
cd avatar-creation-measure
V=../avatar-creation/venv310/bin/python
$V -m py_compile handler.py model.py preprocess.py fit.py
$V test_preprocess.py
diff preprocess.py ../.local_prototype/measure_core/preprocess.py && diff fit.py ../.local_prototype/measure_core/fit.py
$V scripts/local_invoke.py --front <full-body photo> --refuse <mirror selfie> --height 192 --weight 83 --gender male
```
Expected: ping `ok: true`; the good photo gives 13 measurements + `height` and a body; the selfie is refused with
`arms_not_clear`; missing weight gives `missing_weight_kg`; a refused side photo falls back to `front_only`.

## The model in `weights/`

Installed 2026-11-20: `bodym-v1-30ep-s0` = `.local_prototype/measure_ml/cnn_model_official_s0.pt` (`cnn_bodym.py official 30 0`).
BodyM Test-A 10.4 mm, Test-B 13.7 mm mean error over 14 measurements with front + side. It was trained with bbox
framing, so the sidecar says `"framing": "bbox"` and `model.py` crops to the person before the downscale
(`"native"` = plain downscale, for a `cnn_bodym_v2.py` checkpoint).

To replace it: copy the new `.pt` to `weights/measure_cnn.pt`, set `version`, `sha256` (`shasum -a 256`) and `framing`
in `weights/measure_cnn.json`, run the local harness, commit (the folder's `.gitignore` lets the `.pt` through).
