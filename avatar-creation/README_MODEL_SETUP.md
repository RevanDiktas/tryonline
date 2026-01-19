# Model Setup Guide

## Problem: Google Drive Quota Exceeded

The models are hosted on Google Drive, which has download quota limits. When quota is exceeded, downloads fail.

## Solutions (Choose One)

### ✅ Solution 1: Manual Upload to RunPod Volume (RECOMMENDED)

**One-time setup - files persist forever:**

1. **Download models locally** (when quota resets, usually ~24 hours):
   ```bash
   # Create directory
   mkdir -p ~/models_4dhumans
   cd ~/models_4dhumans
   
   # Download checkpoint (2.5GB) - wait for quota reset
   gdown "https://drive.google.com/uc?id=1ISfMrpiiwoSzLoQXsXsX5FUcOxZY5Bzu" -O epoch=35-step=1000000.ckpt
   
   # Download SMPL models (~247MB each)
   gdown "https://drive.google.com/uc?id=1A2qaP3xWZRuBOPaNx0-tovBBhtftxuSv" -O basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl
   gdown "https://drive.google.com/uc?id=1MYc-Qduvki8xcvEGQSwmCiEhg3Ehs0o5" -O basicmodel_m_lbs_10_207_0_v1.1.0.pkl
   gdown "https://drive.google.com/uc?id=1Xr4UaC8job6f0UPMnwwzWRi3pxf8znoE" -O basicmodel_f_lbs_10_207_0_v1.1.0.pkl
   
   # Download supporting files
   gdown "https://drive.google.com/uc?id=1cqbspPE9LM2ysB_YvBcRZR3JGVb3ve_I" -O smpl_mean_params.npz
   gdown "https://drive.google.com/uc?id=1hoGaaioCh9bo3jNY84N3A5VB51DRqnQE" -O SMPL_to_J19.pkl
   ```

2. **Upload to RunPod Volume** using RunPod's S3 API or web interface:
   ```bash
   # Using the check_volume.py script (modify to upload)
   # Or use RunPod web interface to upload files
   ```
   
   **File structure on volume:**
   ```
   /runpod-volume/4DHumans/
   ├── logs/train/multiruns/hmr2/0/checkpoints/
   │   └── epoch=35-step=1000000.ckpt (2.5GB)
   └── data/
       ├── basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl (~247MB)
       ├── basicmodel_m_lbs_10_207_0_v1.1.0.pkl (~247MB)
       ├── basicmodel_f_lbs_10_207_0_v1.1.0.pkl (~247MB)
       ├── smpl_mean_params.npz
       └── SMPL_to_J19.pkl
   ```

3. **Done!** Models will be found automatically on next job run.

---

### ✅ Solution 2: Wait for Quota Reset + Build-Time Download

**Automatic - but requires waiting:**

1. **Wait ~24 hours** for Google Drive quota to reset
2. **Trigger Docker build** - the build-time download script will automatically download models
3. **Models get baked into image** - no more quota issues!

**Note:** If quota is still exceeded during build, build will continue and models will download at runtime (may hit quota again).

---

### ✅ Solution 3: Alternative Hosting Service

**If you want to host models elsewhere:**

1. Upload models to:
   - AWS S3 (free tier: 5GB)
   - Dropbox (free: 2GB)
   - Your own server
   - Any direct download URL

2. Update `download_models_buildtime.py` to use new URLs instead of Google Drive

3. Rebuild Docker image

---

## Current Status

The code automatically checks for models in this order:
1. ✅ RunPod Network Volume (`/runpod-volume/4DHumans/`)
2. ✅ Build-time downloaded models (if build succeeded)
3. ⚠️ Runtime download from Google Drive (may hit quota)

**Recommendation:** Use Solution 1 (manual upload to volume) for immediate fix, or Solution 2 (wait + build) for automatic setup.
