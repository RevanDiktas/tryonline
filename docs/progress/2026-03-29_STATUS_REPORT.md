# Status Report — 2026-03-29 (Sunday)

## Heatmap / RunPod — where we are

Fit heatmaps are still **R&D / infrastructure**, not a finished product feature. Today we moved the **serverless plumbing** forward; **strain/pressure visualization for shoppers** is still ahead.

### Done today

- **Second RunPod endpoint** for heatmap work: same API key, separate **`RUNPOD_HEATMAP_ENDPOINT_ID`** (documented in `backend/env.example` + `app/config.py`).
- **Backend:** `RunPodService.submit_heatmap_job` / `get_heatmap_job_status` in `backend/app/services/runpod.py` (avatar endpoint unchanged).
- **Smoke test:** `backend/scripts/smoke_runpod_heatmap.py` — submits `{"action": "smoke"}`, polls until `COMPLETED`; warns if response still has `"minimal": true`.
- **Git / CI:** Canonical branch for this worker is **`feature/heatmap`** only (merged prior work, removed **`feature/warpheatmap`**). Workflow **`heatmap-runpod Docker image`** triggers on that branch (and `feature/warp-heatmap-worker`).
- **Docker:** `heatmap-runpod/Dockerfile` — `chmod` on `tools/packman` after clone to fix GitHub Actions **Permission denied: packman** during Warp build; compile parallelism env vars to ease runner RAM.
- **RunPod:** **`tryonline-heatmap`** on **`feature/heatmap`**, context **`.`**. **Minimal** image (`Dockerfile.minimal`) **built and pushed successfully** (logs ~2026-03-29); smoke jobs return **`ok` + `minimal: true`** — confirms queue, workers, and API.
- **User switched Dockerfile path** to **`heatmap-runpod/Dockerfile`** for the **full** Garment-Warp worker and redeployed; worker logs showed smoke jobs **Started./Finished.** quickly (handler returns fast path or minimal overlap — **confirm tomorrow** via script `output` JSON: expect **no** `minimal`, fields like **`devices`** / **`round_trip`** when full image is live).

### Not done yet (honest gap)

- **Product heatmaps** (per try-on, storage, widget): not implemented; roadmap items in `docs/plans/HEATMAP_PERSONA_ROADMAP.md` / `docs/GARMENT_AUTOMATION_RESEARCH.md`.
- **Full worker proof:** need a clean **`python scripts/smoke_runpod_heatmap.py`** run showing **GPU smoke** output (not minimal), after RunPod finishes building/pulling the large image; **`IN_QUEUE`** can last minutes when workers are throttled or cold.
- **GitHub Actions `build-and-push`** for the full image may still fail or need retries (heavy build); **RunPod’s own builder** is the parallel path.

---

## Next session (tomorrow evening — suggested order)

1. Confirm **RunPod Builds** tab: latest build **Completed** for **`heatmap-runpod/Dockerfile`**.
2. From repo **`backend/`**: `python scripts/smoke_runpod_heatmap.py` (use `--timeout 600` if needed). Capture **`output`** — verify **full** vs **minimal**.
3. If build fails: download **build logs**, search `ERROR` / `packman` / `OOM`; iterate Dockerfile or use **GHCR** `tryonline-heatmap:latest` + registry deploy.
4. When smoke is green: sketch **API + job row** for “heatmap job” (stub) per roadmap — still before merchant-facing UI.

---

## Files touched this cycle (reference)

| Area | Files |
|------|--------|
| Backend | `app/config.py`, `app/services/runpod.py`, `env.example`, `scripts/smoke_runpod_heatmap.py` |
| RunPod / Docker | `heatmap-runpod/Dockerfile`, `heatmap-runpod/README.md`, `heatmap-worker/README.md` |
| CI | `.github/workflows/heatmap-runpod-image.yml` |

---

*Paused for today — continue heatmap path tomorrow evening.*
