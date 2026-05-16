# avatar-creation-lhm

Phase 0 serverless endpoint wrapping aigc3d/LHM (Large Animatable Human
Reconstruction Model, ICCV 2025).

## Why this exists

PERSONA takes ~90 min per avatar with per-subject training and three license
risks (Sapiens, Inria 3DGS rasterizer, SVD). LHM is feed-forward, ~5 seconds
per avatar, Apache 2.0, same SMPL-X + 3D Gaussian Splat output. See
`docs/research/PERSONA_INTEGRATION_FRAMEWORK.md` for the comparison.

## Files

- `Dockerfile.runpod` — base PyTorch 2.3.0 + CUDA 12.1, clones LHM, installs
  all deps from `install_cu121.sh`, bakes `LHM-MINI` + prior model + motion
  video into the image (~12 GB total).
- `handler.py` — dev-mode dispatch handler. Commands: `info`, `ls`, `cat`,
  `download_model`, `inference`, `inference_mesh`, `shell`.
- `requirements.txt` — handler-side Python deps. (LHM's own deps live inside
  the cloned repo at `/workspace/LHM/requirements.txt`.)

## Deploy on RunPod (serverless)

1. Push this directory on a new branch.
2. RunPod console → Serverless → New Endpoint → "Import from GitHub".
3. Point at this repo + branch, Dockerfile path
   `avatar-creation-lhm/Dockerfile.runpod`. Build context: **repo root**
   (the default). The COPY in the Dockerfile is qualified with the subdir
   so this works regardless of what you set.
4. GPU: any 24 GB+ (RTX 4090 / L40S / A5000). For `LHM-MINI` 16 GB is
   enough but stick with 24 GB to test the bigger variants too.
5. Env vars on the endpoint:
   - `SUPABASE_URL`            (e.g. `https://cykwthsbrylonconqlfz.supabase.co`)
   - `SUPABASE_SERVICE_KEY`    (service-role key, NOT anon)
   - `LHM_BUCKET`              (defaults to `lhm-artifacts`)
   - `LHM_DEFAULT_MODEL`       (defaults to `LHM-MINI`, baked into image)
   - `LHM_ALLOW_SHELL`         (set to `1` for Phase 0; turn OFF for prod)
6. First build takes ~30 min (CUDA-extension compiles + model downloads).
   Subsequent rebuilds when only `handler.py` changes are ~30 sec.

## Calling the endpoint

```bash
curl -s -X POST https://api.runpod.ai/v2/<ENDPOINT_ID>/runsync \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": {"command": "info"}}'
```

### Phase 0 walkthrough commands

```jsonc
// 1) Sanity-check container
{"input": {"command": "info"}}

// 2) Confirm the LHM repo + shipped examples are present
{"input": {"command": "ls", "path": "/workspace/LHM/train_data/example_imgs"}}

// 3) Run inference on a shipped example image, get a video back
{"input": {
  "command": "inference",
  "image_url": "https://<your-supabase>/.../example.png",
  "model_name": "LHM-MINI",
  "export_video": true
}}

// 4) Run mesh export on the same image
{"input": {
  "command": "inference_mesh",
  "image_url": "https://<your-supabase>/.../example.png",
  "model_name": "LHM-MINI"
}}

// 5) Download a bigger variant if MINI quality is too low
{"input": {"command": "download_model", "repo_id": "3DAIGC/LHM-500M-HF"}}

// 6) Inspect any file the run produced
{"input": {"command": "ls", "path": "/workspace/LHM/exps"}}

// 7) Run an arbitrary shell command (only if LHM_ALLOW_SHELL=1)
{"input": {"command": "shell", "cmd": "ls -la /workspace/LHM/exps && du -sh /workspace/LHM/exps/*"}}
```

## Supabase bucket setup (one-time)

Create the `lhm-artifacts` bucket in Supabase, public read enabled (we'll
tighten with RLS in Phase 1):

```sql
-- in Supabase SQL editor
insert into storage.buckets (id, name, public)
values ('lhm-artifacts', 'lhm-artifacts', true)
on conflict (id) do nothing;
```

## Gate criteria (Phase 0 pass)

- LHM produces a recognizable animated avatar from Revan's test photo in
  under 30 seconds wall time on a 4090.
- The exported mesh (`.obj` or `.glb`) loads in a Three.js scene.
- A Ramin draped garment composites on top of the LHM mesh without obvious
  scale or position breakage.

If all three: proceed to Phase 1 (production handler, frontend integration).
If any fail: document the specific failure in `LHM_PHASE0_RESULTS.md` and
either iterate on settings or pivot to IDOL / HumanSplat / PSHuman.
