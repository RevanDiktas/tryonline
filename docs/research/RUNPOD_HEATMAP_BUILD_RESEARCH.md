# RunPod GitHub build failures (heatmap worker) — research notes

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

## Fallback if GitHub builds keep failing

1. **Build locally or in GitHub Actions** with  
   `docker build --platform linux/amd64 -f heatmap-runpod/Dockerfile -t YOUR_DOCKERHUB/tryonline-heatmap:TAG .`  
   then push to Docker Hub (or GHCR) and create the endpoint **from container registry** instead of GitHub.

2. **Download full build logs** from RunPod (download icon) and open a ticket with **help@runpod.io** including endpoint ID — early-stage failures are often visible only in the raw log bundle.

## References

- [Deploy workers from GitHub](https://docs.runpod.io/serverless/github-integration)
- [Create a Dockerfile](https://docs.runpod.io/serverless/workers/create-dockerfile)
- [runpod-workers/worker-basic](https://github.com/runpod-workers/worker-basic) (minimal layout)

*Last updated: 2026-03-29*
