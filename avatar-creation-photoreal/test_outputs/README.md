# Photoreal endpoint - test outputs

Decoded artifacts from `avatar-creation-photoreal` (RunPod `bun2qr20qvnre5`) test
jobs, for eyeballing the avatar output. One folder per run:

```
<build>__<gender>_h<height>__<shortjobid>/
  body_apose.obj        SMPL-X A-pose mesh (mm) - the shipped body pose
  body_tpose.obj        SMPL-X T-pose mesh (mm) - drape/appearance frame
  avatar_textured.glb   per-vertex-tinted GLB (open this to look at the avatar)
  skin_texture.png      flat skin swatch (neutral-tan placeholder in Stage 2b)
  smpl_params.npz       SMPL-X params (betas/pose/...)
  result.json           full flat contract MINUS files_base64 (measurements, sizes, meta)
  input_photo.jpg       the source photo the job ran on (if fetched)
```

Open the `.glb` in any GLTF viewer (macOS Quick Look, or
https://gltf-viewer.donmccurdy.com) to inspect pose / proportions / body shape.

Binary artifacts are gitignored (see `.gitignore`); only `README.md` and each
run's `result.json` are tracked, so the metadata is versioned without bloating
the repo. Decoder: `scripts/decode_result.py` (repo).
