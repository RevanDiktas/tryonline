# Heatmap worker (Warp + GarmentCode fork)

Phase **0.5** in-repo worker: Docker image that builds **[NvidiaWarp-GarmentCode](https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode)** (Warp + garment collision / XPBD extras), then runs a **GPU smoke test**.

## License (important)

That fork ships under **NVIDIA’s license** (see fork `LICENSE.md`). It may restrict **commercial** use compared with current upstream policies. **Verify with counsel** before production; this image is for **engineering spikes**.

## What you do in Git (this repo)

1. **Branch** (already typical): `feature/warp-heatmap-worker` (or stay on it).
2. **Commit** `heatmap-worker/` and **push** to GitHub:
   ```bash
   git add heatmap-worker/
   git commit -m "feat(heatmap-worker): Docker + Garment-Warp build + GPU smoke"
   git push -u origin feature/warp-heatmap-worker
   ```
3. You do **not** need to clone the Garment fork into a separate repo for day-to-day work—the **Dockerfile clones it at build time**.

## Build the image (any machine with Docker)

From the **repository root** (`mvp_pipeline/`):

```bash
docker build -f heatmap-worker/Dockerfile -t tryonline-heatmap-worker:phase0.5 .
```

Optional: pin the fork to a commit (reproducible builds):

```bash
docker build -f heatmap-worker/Dockerfile \
  --build-arg GARMENT_WARP_REF=<git-sha> \
  -t tryonline-heatmap-worker:phase0.5 .
```

**Note:** First build may take **tens of minutes** (native compile). Use a machine or CI with enough CPU/RAM.

## Run locally (needs NVIDIA GPU + nvidia-docker)

```bash
docker run --rm --gpus all tryonline-heatmap-worker:phase0.5
```

## Run on RunPod

1. Push the branch so RunPod (or your registry build) can clone this repo.
2. **Serverless / Pod**: use the same `docker build` command (or point RunPod’s build at `heatmap-worker/Dockerfile` with **build context = repo root**).
3. **Start command**: default `CMD` already runs `scripts/smoke_gpu.py`.
4. After smoke passes, run **asset load** (signed Supabase URLs):

   ```bash
   python /workspace/scripts/load_assets.py \
     --body-url "https://..." \
     --garment-url "https://..."
   ```

## Next (Phase 1)

Add XPBD cloth + `body_apose.obj` collision + `m.glb` strain export; keep **mm** units consistent with the avatar pipeline.
