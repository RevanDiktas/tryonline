**RunPod “Build from GitHub” often dies after clone + “Creating cache directory” with no Docker logs.** That is a **RunPod builder / integration** problem, not your repo layout. Use one of the paths below.

---

### A) Prove it: minimal image via RunPod GitHub (optional)

1. In the endpoint repo settings, set **Dockerfile path** to **`heatmap-runpod/Dockerfile.minimal`** (context **`.`**).
2. Rebuild.

- If **this** still fails the same way → open a ticket with **help@runpod.io** (attach downloaded logs). Nothing in our Warp stack is involved.
- If **this** succeeds → their builder works for small images; use **GHCR** for the heavy Warp image (B).

---

### B) Recommended: GitHub Actions → GHCR → RunPod “container registry”

1. GitHub repo **Settings → Actions → General → Workflow permissions** → **Read and write** (packages).
2. Push to **`feature/heatmap`** or run workflow **heatmap-runpod Docker image** manually.
3. Wait for jobs:
   - **`build-minimal`** → `ghcr.io/revandiktas/tryonline-heatmap-minimal:latest` (fast smoke).
   - **`build-and-push`** → `ghcr.io/revandiktas/tryonline-heatmap:latest` (full Warp worker; can take a long time or OOM on free runners).
4. In RunPod, **do not** use “import from GitHub” for this. Create the endpoint from **container registry**:
   - Image: `ghcr.io/revandiktas/tryonline-heatmap-minimal:latest` first (test), then `:latest` for real work.
   - Connect GHCR with a PAT that has **`read:packages`** if RunPod asks.

---

### Files

| File | Role |
|------|------|
| `heatmap-runpod/Dockerfile` | Full Garment-Warp worker |
| `heatmap-runpod/Dockerfile.minimal` | Python + runpod only (diagnostic) |
| `.github/workflows/heatmap-runpod-image.yml` | Builds both and pushes to GHCR |

More context: `docs/research/RUNPOD_HEATMAP_BUILD_RESEARCH.md`.
