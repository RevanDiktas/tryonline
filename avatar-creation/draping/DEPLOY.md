# Draping Service — Deployment Guide

## Overview

This is a **new, separate** RunPod serverless endpoint for cloth draping.
It does NOT touch the existing avatar endpoint ("tryonline").

| Endpoint     | Purpose               | Branch             | Status   |
|--------------|-----------------------|---------------------|----------|
| tryonline    | Avatar generation      | main / feature/*   | LIVE     |
| (heatmap)    | Heatmaps (delayed)    | —                   | UNUSED   |
| **draping**  | **Cloth simulation**  | **drape**           | **NEW**  |

---

## Step 1: Build & Push Docker Image

From your machine (needs Docker Desktop running):

```bash
cd avatar-creation/draping

# Build locally first to verify
./build.sh

# Push to DockerHub (need: docker login)
./build.sh push
```

This pushes `revandiktas/tryon-draping:latest` to DockerHub.

---

## Step 2: Create RunPod Serverless Endpoint

1. Go to **[runpod.io](https://runpod.io)** → **Serverless** → **New Endpoint**
2. Settings:
   - **Name**: `tryon-draping`
   - **Container Image**: `revandiktas/tryon-draping:latest`
   - **GPU Type**: Any (16GB+ VRAM — geometric fallback needs no GPU, but XRTailor will)
   - **Min Workers**: `0` (pay nothing when idle)
   - **Max Workers**: `3`
   - **Idle Timeout**: `5` seconds
   - **Execution Timeout**: `180` seconds
3. Click **Create**
4. **Copy the Endpoint ID** (looks like `abc123def456`)

---

## Step 3: Test the Endpoint

```bash
# Replace YOUR_ENDPOINT_ID and YOUR_RUNPOD_API_KEY
curl -X POST "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync" \
  -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "body_obj_url": "https://YOUR_SUPABASE_URL/storage/v1/object/public/avatars/USER_ID/body_tpose.obj",
      "garment_obj_url": "https://YOUR_SUPABASE_URL/storage/v1/object/public/garments/BRAND_ID/PRODUCT_ID/m.obj",
      "fabric_config": {"stretch_compliance": 0.001, "bend_compliance": 0.01, "thickness": 0.003},
      "simulation_mode": "swift",
      "garment_id": "test",
      "size": "m",
      "user_id": "test"
    }
  }'
```

Expected response:
```json
{
  "output": {
    "success": true,
    "simulation_method": "geometric_fallback",
    "vertex_count": 12345,
    "processing_time_seconds": 1.5,
    "draped_glb_base64": "...",
    "draped_obj_base64": "..."
  }
}
```

---

## Step 4: Wire to Backend (Railway)

Once the endpoint is tested and working:

1. Go to **Railway** → your backend service → **Variables**
2. Add: `RUNPOD_DRAPING_ENDPOINT_ID=YOUR_ENDPOINT_ID`
3. The backend `draping.py` API will now route draping requests to RunPod
4. Push the `drape` branch changes to `feature/analytics` or `main` when ready

**DO NOT** add this env var until the endpoint is tested!

---

## Step 5: Run Database Migration

In **Supabase SQL Editor**, run:
```
backend/migrations/003_draping_tables.sql
```

This adds:
- `obj_sizes` + `fabric_config` columns to `garments`
- `draped_meshes` cache table
- `draping_requests` job tracker

---

## Auto-Build on Push (Optional)

RunPod can auto-rebuild when you push to the `drape` branch:

1. In RunPod endpoint settings → **GitHub Integration**
2. Connect repo: `RevanDiktas/tryonline`
3. Branch: `drape`
4. Dockerfile path: `avatar-creation/draping/Dockerfile`
5. Build context: `avatar-creation/draping/`

Now every `git push origin drape` triggers a new build + deploy.

---

## Local Testing (No RunPod Needed)

```bash
cd avatar-creation/draping

# Test with local OBJ files
python test_local.py --body-obj /path/to/body_tpose.obj --garment-obj /path/to/garment.obj

# Test with real Supabase data
export SUPABASE_URL="https://xxx.supabase.co"
export SUPABASE_SERVICE_KEY="eyJ..."
python test_with_supabase.py --user-id "your-uuid"
```

---

## Architecture

```
Shopper opens widget
       │
       ▼
  GET /tryon-config?user_id=X
       │
       ├─ Cache hit? → return draped GLB URL (instant)
       │
       └─ Cache miss? → return original GLB + trigger draping
              │
              ▼
        POST /api/draping/request
              │
              ▼
        Background: call RunPod draping endpoint
              │
              ▼
        RunPod: download body OBJ + garment OBJ
              │
              ▼
        RunPod: geometric drape (or XRTailor if available)
              │
              ▼
        Upload draped GLB → Supabase Storage
              │
              ▼
        Widget polls → hot-swaps mesh in real-time
```
