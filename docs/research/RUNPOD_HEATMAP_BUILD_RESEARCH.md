# RunPod GitHub build failures (heatmap worker) — research notes

## Mental model (how this is supposed to work)

1. **You push code to GitHub** — same as any other service.
2. **RunPod does not run “a script that imports another script” in a special way** — it starts **one container** whose `CMD` runs **`python handler.py`**. That file calls `runpod.serverless.start(...)`. Everything else is normal Python: modules next to `handler.py` in `/workspace` are imported with plain `import`.
3. **GitHub Actions → GHCR** is optional CI: it builds the same Dockerfile and pushes an image so RunPod can **pull a prebuilt image** instead of using RunPod’s flaky “build from GitHub” button.

## Symptom

Serverless **Build Failed** within ~10–30s. UI logs often stop after:

- `Successfully cloned repository …`
- `Creating cache directory.`

No `Step 1/…` Docker output appears, so the failure is **before or at the very start** of `docker build` from the user’s perspective.

## What RunPod documents

From [GitHub integration — Limitations](https://docs.runpod.io/serverless/github-integration):

| Limitation | Relevance |
|------------|-----------|
| **Privately hosted base images not supported** | `FROM` must resolve on builders without private registry auth. Prefer **Docker Hub / public** images. |
| **No GPU during `docker build`** | GPU-only compile steps during build will fail; **NVCC on CPU** is OK. |
| **Build time ≤ 160 min** | Not the issue for instant failures. |
| **Image ≤ 80 GB** | Not the issue for instant failures. |

From [Deploy workers from Docker Hub](https://docs.runpod.io/serverless/workers/deploy): images should target **`linux/amd64`** (RunPod infra).

## Likely causes (ranked)

1. **Non-standard Dockerfile path / name**  
   Some UIs only validate `**/Dockerfile` literally. A root file named `Dockerfile.runpod-heatmap` can pass “Docker file found” but still break an internal step. **Mitigation:** use directory + literal `Dockerfile`, e.g. `heatmap-runpod/Dockerfile`.

2. **Base image pull on builders**  
   `FROM runpod/pytorch:…` may be slow, rate-limited, or treated differently than mainstream Hub images. **Mitigation:** `FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-devel` (public Docker Hub, CUDA 11.8 devel, matches prior intent).

3. **Build context vs `COPY` paths**  
   If the platform always uses **repo root** as context, `COPY requirements.txt` (with file only under `heatmap-worker/`) fails immediately. **Mitigation:** `COPY heatmap-worker/...` and context `.` .

4. **Huge context**  
   Less likely to produce *zero* Docker lines, but still worth trimming via root `.dockerignore` (without excluding `heatmap-worker/` or `backend/` if you still build root `Dockerfile`).

## Recommended RunPod settings (current repo layout)

- **Dockerfile path:** `heatmap-runpod/Dockerfile`
- **Build context:** `.` (repo root) or empty if that defaults to root
- **Branch:** `feature/heatmap` (or your tracking branch)

## “Failed” in ~2 seconds with no Docker steps

That duration is **too short** for a real `docker build` (even pulling a base image). It usually means **pre-build validation** failed, a **transient builder error**, or the UI is not showing stderr. Treat GitHub-integrated builds as unreliable until you see `Step 1/N` lines.

## Fallback if GitHub builds keep failing

### A) GitHub Actions → GHCR (in this repo)

Workflow: `.github/workflows/heatmap-runpod-image.yml`  
Runs on push to `feature/heatmap` (and manual **Run workflow**). Pushes:

- `ghcr.io/<github-owner-lowercase>/tryonline-heatmap:latest`
- `ghcr.io/<github-owner-lowercase>/tryonline-heatmap:<sha>`

**GitHub:** Repository **Settings → Actions → General → Workflow permissions** → allow **Read and write** (needed for `GITHUB_TOKEN` to push packages).

**RunPod:** Create or edit the endpoint → **deploy from container registry** (not GitHub) → image `ghcr.io/revandiktas/tryonline-heatmap:latest` (adjust owner if different). Connect GHCR if RunPod asks for registry auth (PAT with `read:packages`).

### B) Manual local build

```bash
docker build --platform linux/amd64 -f heatmap-runpod/Dockerfile -t YOUR_REGISTRY/tryonline-heatmap:TAG .
docker push YOUR_REGISTRY/tryonline-heatmap:TAG
```

### C) Support

**Download full build logs** from RunPod (download icon) and email **help@runpod.io** with endpoint ID.

## References

- [Deploy workers from GitHub](https://docs.runpod.io/serverless/github-integration)
- [Create a Dockerfile](https://docs.runpod.io/serverless/workers/create-dockerfile)
- [runpod-workers/worker-basic](https://github.com/runpod-workers/worker-basic) (minimal layout)

*Last updated: 2026-03-29*
