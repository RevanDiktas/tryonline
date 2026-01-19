# Option 2: Wait for Quota Reset + Build-Time Download
## Complete Step-by-Step Guide

---

## 📋 Overview

This guide walks you through downloading models during Docker build, which bakes them into the image permanently. This is a **one-time setup** - once models are in the image, you'll never hit quota issues again.

**Total Time:** ~30-45 minutes (build time)
**Wait Time:** ~24 hours for quota reset

---

## Step 1: Wait for Google Drive Quota to Reset ⏰

### How to Check if Quota Has Reset

1. **Try downloading a test file:**
   ```bash
   # Install gdown if you don't have it
   pip install gdown
   
   # Try downloading a small file from your Google Drive
   gdown "https://drive.google.com/uc?id=1ISfMrpiiwoSzLoQXsXsX5FUcOxZY5Bzu" -O test_download.ckpt
   ```

2. **If it works** → Quota has reset! ✅ Proceed to Step 2
3. **If you get "quota exceeded"** → Wait longer (usually resets every 24 hours)

### Alternative: Check via Browser

1. Open this link in your browser:
   ```
   https://drive.google.com/uc?id=1ISfMrpiiwoSzLoQXsXsX5FUcOxZY5Bzu
   ```
2. If it downloads → Quota reset! ✅
3. If you see "quota exceeded" → Keep waiting

---

## Step 2: Verify Your Code is Up to Date ✅

Make sure the latest code (with build-time download script) is pushed:

```bash
cd /Volumes/Expansion/mvp_pipeline

# Check if you're on latest commit
git pull origin main

# Verify the download script exists
ls -la avatar-creation/download_models_buildtime.py

# Should see: download_models_buildtime.py
```

If the file doesn't exist, you need to pull the latest code:
```bash
git pull origin main
```

---

## Step 3: Trigger Docker Build in RunPod 🐳

### Option A: Via RunPod Web Interface (Easiest)

1. **Go to RunPod Dashboard:**
   - Visit: https://www.runpod.io/console/serverless
   - Log in to your account

2. **Find Your Serverless Endpoint:**
   - Click on "Serverless" in the left sidebar
   - Find your endpoint (the one you're using for avatar creation)

3. **Trigger Rebuild:**
   - Click on your endpoint
   - Look for "Settings" or "Configuration" tab
   - Find "Docker Image" or "Container Image" section
   - Click "Rebuild" or "Update" button
   - OR change the image tag slightly (e.g., add `:v2`) and save

4. **Monitor Build:**
   - Go to "Builds" or "Activity" tab
   - You'll see build progress
   - Build will take **20-45 minutes** (downloading 3.2GB of models)

### Option B: Via RunPod API (If Available)

```bash
# Set your API key
export RUNPOD_API_KEY="your-api-key-here"

# Trigger rebuild (check RunPod API docs for exact endpoint)
curl -X POST "https://api.runpod.io/v1/endpoints/YOUR_ENDPOINT_ID/rebuild" \
  -H "Authorization: Bearer $RUNPOD_API_KEY"
```

---

## Step 4: Monitor Build Progress 📊

### What to Look For

During the build, you should see logs like:

```
[Build] Downloading HMR2 Checkpoint...
[Build] Downloading checkpoint from: https://drive.google.com/uc?id=1ISfMrpiiwoSzLoQXsXsX5FUcOxZY5Bzu
[Build] ✓ Downloaded HMR2 Checkpoint (2500.0MB)

[Build] Downloading SMPL Neutral Model...
[Build] ✓ Downloaded SMPL Neutral Model (247.5MB)

[Build] Downloading SMPL Male Model...
[Build] ✓ Downloaded SMPL Male Model (247.3MB)

[Build] Downloading SMPL Female Model...
[Build] ✓ Downloaded SMPL Female Model (247.8MB)

[Build] Download Summary:
✓ Checkpoint: Downloaded
✓ SMPL Neutral: Downloaded
✓ SMPL Male: Downloaded
✓ SMPL Female: Downloaded
✓ Mean Params: Downloaded
✓ Joint Regressor: Downloaded
```

### ⚠️ If You See Quota Errors

If you see:
```
⚠️  Google Drive quota exceeded
⚠️  Build-time download had issues (quota or network)
```

**Don't worry!** The build will continue, but:
- Models won't be in the image
- They'll try to download at runtime (may hit quota again)
- You'll need to wait longer and rebuild

---

## Step 5: Verify Build Success ✅

### Check Build Logs

1. In RunPod dashboard, go to your endpoint's build logs
2. Look for the download summary at the end
3. Should see: `✓ All critical files downloaded successfully!`

### Verify Image Size

After build completes:
1. Check the Docker image size
2. Should be **~3-4GB larger** than before (models are ~3.2GB)
3. If size didn't increase much → models didn't download

---

## Step 6: Test the Pipeline 🧪

### Run a Test Job

1. **Trigger a test avatar creation** from your frontend/backend
2. **Check the logs** - should see:
   ```
   [Config] Using RunPod Network Volume cache: /runpod-volume/4DHumans
   [DEBUG download_models] Checkpoint found in cache (volume working!)
   ✅ Checkpoint found in cache: /root/.cache/4DHumans/logs/.../epoch=35-step=1000000.ckpt (2.50 GB)
   ```

3. **If you see this** → Models are working! ✅
4. **If you see quota errors** → Build didn't download models, try again

---

## Step 7: What Happens Next 🎉

### Success Scenario

✅ Models are baked into Docker image
✅ Every job uses pre-downloaded models
✅ **No more quota issues!**
✅ Jobs start faster (no download time)

### If Build Failed

❌ Models not in image
❌ Jobs will try runtime download
❌ May hit quota again

**Solution:** Wait longer for quota reset, then rebuild

---

## Troubleshooting 🔧

### Problem: Build keeps failing with quota errors

**Solution:**
- Wait longer (quota resets every ~24 hours)
- Try building at different times (off-peak hours)
- Consider Option 1 (manual upload to volume) instead

### Problem: Build succeeded but jobs still fail

**Check:**
1. Verify image size increased (~3GB larger)
2. Check build logs for download success messages
3. Check job logs - are models being found?

**Solution:**
- If models weren't downloaded → Rebuild
- If models were downloaded but not found → Check paths in code

### Problem: Build takes too long

**Normal:** Build should take 20-45 minutes
- Downloading 2.5GB checkpoint: ~10-20 min
- Downloading 3x SMPL models: ~5-10 min each
- Docker layer creation: ~5-10 min

**If it's stuck:**
- Check build logs for errors
- May need to cancel and retry

---

## Summary Checklist ✅

- [ ] Step 1: Waited ~24 hours for quota reset
- [ ] Step 2: Verified quota has reset (test download works)
- [ ] Step 3: Verified code is up to date (download script exists)
- [ ] Step 4: Triggered Docker build in RunPod
- [ ] Step 5: Monitored build progress (saw download messages)
- [ ] Step 6: Verified build success (saw "✓ All critical files downloaded")
- [ ] Step 7: Tested pipeline (job runs without quota errors)

---

## Next Steps 🚀

Once this is working:
- ✅ Models are permanently in your Docker image
- ✅ No more quota issues
- ✅ Faster job startup times
- ✅ More reliable pipeline

You're all set! 🎉
