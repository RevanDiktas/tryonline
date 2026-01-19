# Dropbox Download Process - How It Works

## Overview

You're NOT uploading to RunPod. Instead:
1. **You upload to Dropbox** (from your computer)
2. **Docker build downloads from Dropbox** (on RunPod's fast servers)
3. **Models get baked into Docker image** (permanent)

---

## Step-by-Step Process

### Step 1: Upload to Dropbox (You Do This - 5-10 min)

**On your local machine:**
1. Go to https://www.dropbox.com
2. Upload all 6 files from `~/models_4dhumans/` to Dropbox
3. Get share links for each file
4. Change `&dl=0` to `&dl=1` in each link

**Time:** ~5-10 minutes (your upload speed)

---

### Step 2: Set Environment Variables in RunPod (You Do This - 2 min)

**In RunPod dashboard:**
1. Go to your Serverless Endpoint → Settings
2. Add 6 environment variables with Dropbox URLs:
   - `DROPBOX_CHECKPOINT_URL=https://...&dl=1`
   - `DROPBOX_SMPL_NEUTRAL_URL=https://...&dl=1`
   - etc.

**Time:** 2 minutes

---

### Step 3: Trigger Docker Build (RunPod Does This - 20-30 min)

**What happens automatically:**

1. **Build starts** on RunPod's servers
2. **Download script runs** (`download_models_buildtime.py`)
3. **Checks for Dropbox URLs** in environment variables
4. **Downloads from Dropbox** directly to RunPod's servers:
   ```
   [Build] Downloading HMR2 Checkpoint from Dropbox...
   [Build]   URL: https://www.dropbox.com/scl/fi/.../epoch=35-step=1000000.ckpt?dl=1
   [Build]   Progress: 500.0MB / 2500.0MB (20.0%)
   [Build]   Progress: 1000.0MB / 2500.0MB (40.0%)
   ...
   [Build] ✓ Downloaded HMR2 Checkpoint (2500.0MB)
   ```
5. **Validates file sizes** (ensures correct downloads)
6. **Saves to Docker image** at `/root/.cache/4DHumans/`
7. **Build completes** with models baked in

**Time:** ~20-30 minutes total
- Checkpoint (2.5GB): ~10-15 min
- SMPL models (3x 236MB): ~2-3 min each
- Small files: ~30 seconds

---

## Why This Is Fast

✅ **RunPod's servers download** (not your slow home internet)
- RunPod has fast connections (100+ MB/s)
- Your upload was 4 hours because of slow home internet
- Build download is ~20-30 min on RunPod's fast network

✅ **No quota issues**
- Dropbox has no download limits (for reasonable usage)
- Google Drive was hitting quota limits

✅ **One-time setup**
- Models get baked into Docker image
- Every job uses pre-downloaded models
- No runtime downloads needed

---

## What Happens During Build

```
[Build] ============================================================
[Build] BUILD-TIME MODEL DOWNLOAD
[Build] ============================================================
[Build] 
[Build] Checking for Dropbox URLs...
[Build] ✓ Found DROPBOX_CHECKPOINT_URL
[Build] ✓ Found DROPBOX_SMPL_NEUTRAL_URL
[Build] ✓ Found DROPBOX_SMPL_MALE_URL
[Build] ✓ Found DROPBOX_SMPL_FEMALE_URL
[Build] ✓ Found DROPBOX_MEAN_PARAMS_URL
[Build] ✓ Found DROPBOX_JOINT_REGRESSOR_URL
[Build] 
[Build] ============================================================
[Build] DOWNLOADING CHECKPOINT (2.5GB)
[Build] ============================================================
[Build] Downloading HMR2 Checkpoint from URL...
[Build]   URL: https://www.dropbox.com/scl/fi/.../epoch=35-step=1000000.ckpt?dl=1
[Build]   Progress: 500.0MB / 2500.0MB (20.0%)
[Build]   Progress: 1000.0MB / 2500.0MB (40.0%)
[Build]   Progress: 1500.0MB / 2500.0MB (60.0%)
[Build]   Progress: 2000.0MB / 2500.0MB (80.0%)
[Build]   Progress: 2500.0MB / 2500.0MB (100.0%)
[Build] ✓ Downloaded HMR2 Checkpoint (2500.0MB)
[Build] 
[Build] ============================================================
[Build] DOWNLOADING SMPL MODELS (~247MB each)
[Build] ============================================================
[Build] Downloading SMPL Neutral Model from URL...
[Build] ✓ Downloaded SMPL Neutral Model (236.0MB)
[Build] Downloading SMPL Male Model from URL...
[Build] ✓ Downloaded SMPL Male Model (236.0MB)
[Build] Downloading SMPL Female Model from URL...
[Build] ✓ Downloaded SMPL Female Model (236.0MB)
[Build] 
[Build] ============================================================
[Build] DOWNLOADING SUPPORTING FILES
[Build] ============================================================
[Build] ✓ Downloaded SMPL Mean Params (0.001MB)
[Build] ✓ Downloaded SMPL Joint Regressor (1.0MB)
[Build] 
[Build] ============================================================
[Build] DOWNLOAD SUMMARY
[Build] ============================================================
[Build] ✓ Checkpoint: Downloaded
[Build] ✓ SMPL Neutral: Downloaded
[Build] ✓ SMPL Male: Downloaded
[Build] ✓ SMPL Female: Downloaded
[Build] ✓ Mean Params: Downloaded
[Build] ✓ Joint Regressor: Downloaded
[Build] 
[Build] ✓ All critical files downloaded successfully!
[Build]   Models are baked into the Docker image.
[Build]   Runtime downloads will be skipped if these files exist.
```

---

## Timeline

| Step | Who | Time | What |
|------|-----|------|------|
| 1. Upload to Dropbox | You | 5-10 min | Upload files from your computer |
| 2. Set env vars | You | 2 min | Paste Dropbox URLs in RunPod |
| 3. Trigger build | You | 1 click | Start Docker build |
| 4. Download models | RunPod | 20-30 min | Build downloads from Dropbox |
| 5. Build completes | RunPod | - | Models baked into image |

**Total time:** ~30-45 minutes (vs 4 hours for your upload!)

---

## After Build Completes

✅ Models are permanently in Docker image
✅ Every job uses pre-downloaded models
✅ No runtime downloads = no quota issues
✅ Faster job startup (no download time)
✅ Works forever!

---

## Summary

**You upload to Dropbox once** (5-10 min)
↓
**Set URLs in RunPod** (2 min)
↓
**Build downloads from Dropbox** (20-30 min on RunPod's fast servers)
↓
**Done!** Models baked into image permanently

No more quota issues, no more slow uploads! 🚀
