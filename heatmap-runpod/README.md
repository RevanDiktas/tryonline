**Preferred when RunPod’s “build from GitHub” fails silently:** use **GitHub Actions → GHCR**, then deploy the image from RunPod’s **container registry** flow.

- Workflow: `.github/workflows/heatmap-runpod-image.yml` (pushes `ghcr.io/<owner>/tryonline-heatmap:latest`).
- Dockerfile: **`heatmap-runpod/Dockerfile`**, Docker context **repo root (`.`)**.

See `docs/research/RUNPOD_HEATMAP_BUILD_RESEARCH.md` for failure modes and RunPod settings.
