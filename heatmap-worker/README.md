# Heatmap worker (Warp + GarmentCode fork)

Phase **0.5** in-repo worker: Docker image that builds **[NvidiaWarp-GarmentCode](https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode)** (Warp + garment collision / XPBD extras), then runs a **GPU smoke test**.

## License (important)

That fork ships under **NVIDIA’s license** (see fork `LICENSE.md`). It may restrict **commercial** use compared with current upstream policies. **Verify with counsel** before production; this image is for **engineering spikes**.

## What you do in Git (this repo)

1. **Branch:** use **`feature/heatmap`** on RunPod and in git (single branch for this worker).
2. **Commit** `heatmap-worker/` and **push** to GitHub:
   ```bash
   git add heatmap-worker/
   git commit -m "feat(heatmap-worker): Docker + Garment-Warp build + GPU smoke"
   git push -u origin feature/heatmap
   ```
3. You do **not** need to clone the Garment fork into a separate repo for day-to-day work—the **Dockerfile clones it at build time**.

## Build the image (any machine with Docker)

From the **repository root** (`mvp_pipeline/`). **Context must be `heatmap-worker/`** (small upload; repo root caused RunPod builds to fail early):

```bash
docker build -f heatmap-worker/Dockerfile -t tryonline-heatmap-worker:phase0.5 heatmap-worker
```

Optional: pin the fork to a commit (reproducible builds):

```bash
docker build -f heatmap-worker/Dockerfile \
  --build-arg GARMENT_WARP_REF=<git-sha> \
  -t tryonline-heatmap-worker:phase0.5 heatmap-worker
```

**Note:** First build may take **tens of minutes** (native compile). Use a machine or CI with enough CPU/RAM.

## Run locally (needs NVIDIA GPU + nvidia-docker)

Default image `CMD` is **`handler.py`** (RunPod serverless loop). For a **one-shot smoke** without RunPod:

```bash
docker run --rm --gpus all tryonline-heatmap-worker:phase0.5 \
  python -u -c "from worker_core import run_smoke; raise SystemExit(run_smoke()[0])"
```

## Run on RunPod Serverless (recommended flow)

**Do not reuse the existing `tryonline` avatar endpoint** for this image unless you intend to replace that worker. Create a **separate endpoint** (e.g. `tryonline-heatmap`) so builds and GPU settings stay independent.

### Before the console

1. **GitHub → RunPod:** [Settings → Connections](https://console.runpod.io/user/settings) → connect GitHub and allow access to **`tryonline`** (your repo).
2. **Branch pushed:** e.g. **`feature/heatmap`** with this `heatmap-worker/` folder.

### In the RunPod console

1. **Serverless** → **+ New endpoint** → **Import Git Repository**.
2. Select repo **`RevanDiktas/tryonline`** (or your org name + repo).
3. **Branch:** **`feature/heatmap`** (tracks this worker on RunPod).
4. **Dockerfile path:** **`heatmap-runpod/Dockerfile`**. Use a normal `Dockerfile` filename inside a folder (see `docs/research/RUNPOD_HEATMAP_BUILD_RESEARCH.md`); odd root filenames + `runpod/pytorch` base were suspected when builds died right after “Creating cache directory.”
5. **Build context:** **`.`** (repo root) or leave empty if that defaults to root.
6. **GPU:** pick a **CUDA** instance (e.g. RTX 4000 class); worker needs a real GPU at **runtime** (build uses `nvcc`, no GPU required during `docker build` on RunPod’s builders).
7. Deploy and open the endpoint → **Builds** tab until status **Completed** (first build can take **a long time**; RunPod allows up to **160 minutes**).

### After deploy: trigger builds / updates

RunPod’s GitHub integration typically **builds from a [GitHub Release](https://docs.runpod.io/serverless/github-integration#update-your-endpoint)**, not every push. After pushing commits, **create a release** (or use your team’s documented “redeploy” action) so a new image builds.

### Test a job (smoke)

Send a job whose `input` is:

```json
{ "input": { "action": "smoke" } }
```

Expect `ok: true` and a `devices` list in the output.

### Test asset load (signed URLs)

```json
{
  "input": {
    "action": "load_assets",
    "body_url": "https://.../body_apose.obj",
    "garment_url": "https://.../m.glb"
  }
}
```

### Optional: Pods instead of Serverless

You can start a **GPU Pod** with the same image from RunPod’s registry (after one successful Serverless build) and override command to `python /workspace/scripts/smoke_gpu.py` for quick manual checks—no `runpod` job queue involved.

## Next (Phase 1)

Add XPBD cloth + `body_apose.obj` collision + `m.glb` strain export; keep **mm** units consistent with the avatar pipeline.
