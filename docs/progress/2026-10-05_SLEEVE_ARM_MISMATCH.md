# Arms poking out of sleeves: diagnosis (2026-10-05, 22:40)

Seen on `test5@gmail.com` (`bdfebfca-459a-482b-bc14-34604454c0d5`, 195 cm, LHM avatar) wearing
La Fam "stripped long sleeve pink/yellow" XL: the sleeves hang steeper than the arms, and
each forearm leaves its sleeve through the cloth around the elbow.

Written from a cloud session by reading code only. No mesh was downloaded, nothing was run,
nothing in the drape handler was changed. Verify on the Mac before building.

## Cause

Nothing in the drape pipeline ever moves a sleeve onto the shopper's arm.

1. **There is no cloth simulation.** Since v36 the handler ships the retargeted mesh
   (`SKIP_NEWTON_SIM`, `pygarment_drape`, "v36 STRUCTURAL CHANGE"). The garment keeps the
   shape CLO3D exported.
2. **La Fam garments are treated as already fitted.** v47 `_is_prefitted()` returns an identity
   transform when >= 60% of the garment's verts are within 50 mm of the body. So the sleeves
   stay at the arm angle of the avatar the garment was authored on in CLO3D.
3. **The shopper's arms are at a fixed 45 degrees.** `avatar-creation-lhm/handler.py`:
   `APOSE_SHOULDER_RAD = 45 deg`, applied in `_build_apose_body_pose` to SMPL-X shoulders
   only. In the screenshot the sleeves sit at roughly 55 degrees below horizontal and the
   arms at roughly 45 (read off the image, not measured on meshes).
4. **The only correction is `_retarget_garment_to_body`**, which pushes cloth verts that are
   inside the body out along the nearest body-face normal (sleeves to 1 mm,
   `SLEEVE_OFFSET_M`), at most 15 capped iterations. Where an arm crosses a sleeve wall, the
   verts on either side of the arm are pushed in opposite directions. The cloth cannot be
   carried around the arm that way, so the arm ends up through the sleeve.

The same mismatch is a candidate for the forearm and cuff holes in `2026-10-05_NIGHT_STATUS.md`
("seams split open near the cuff"): worth re-checking those renders with this in mind before
welding seams.

Why it was not seen earlier: Ramin's garments were tuned for months against this 45 degree
body. La Fam's arrive in world coordinates on a different CLO3D avatar, and v47 deliberately
stopped moving them.

## Fix options

**A. Re-pose the sleeves in the drape handler (recommended).** After alignment, before the
retarget, for each arm:

- Body arm axis: shoulder to wrist. From `smpl_params` joints if available, else PCA of body
  verts with |x| beyond the shoulder.
- Sleeve axis: PCA of garment verts beyond the same shoulder x (use `Sleeves_*` materials
  when the garment has them, else the x-threshold; the v19 L/R split already does this by x).
- Rotate sleeve verts about the shoulder pivot by the angle between the two axes, with a
  smooth blend weight from 0 at the armhole to 1 a few cm down the sleeve so the torso and
  shoulder seam do not tear.
- Then the existing retarget cleans up the remaining millimetres.
- Gate it: skip when the angle is under ~3 degrees (Ramin on a 45 degree body stays
  bit-identical), log the angle per arm, and report it in the response.

This handles any brand's authoring pose and any future avatar pose.

**B. Change the avatar's arm angle** (`APOSE_SHOULDER_RAD` on `feature/lhm`). One constant,
but it only helps new avatars, it breaks Ramin (authored for 45), and brands will not share
one authoring pose. Not recommended on its own.

**C. Pose the avatar per garment in the viewer.** The viewer shows a static GLB; it would
need the rig and a per-garment pose. Much larger change.

## How to verify (Mac, per the handler-rigor rule)

- Inputs: `avatars/bdfebfca-459a-482b-bc14-34604454c0d5/body_apose.obj` and the longsleeve XL
  OBJ (garment `e309ebd8-...` or look up by name in `garments`).
- Measure before/after: angle between arm axis and sleeve axis per side; count of body verts
  on the forearm that lie outside the sleeve tube (should be only the hand past the cuff).
- Render back and side views before/after for longsleeve S/XL, a La Fam tee, and RS Zip Up
  (must be unchanged).
- A handler version bump re-drapes every avatar x garment x size in the background.
