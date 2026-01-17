# RunPod HMR2 Checkpoint Setup Guide

## Problem
The HMR2 checkpoint file is **2.5GB** and too large to upload directly to RunPod S3 (timeout errors). We'll upload it to **Google Drive** and download it in the container at runtime.

---

## Step 1: Find the Checkpoint File Locally

The checkpoint file should be at one of these locations:

```bash
# Option 1: In cache directory
~/.cache/4DHumans/logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt

# Option 2: In 4D-Humans-clean directory
avatar-creation/4D-Humans-clean/logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt

# Option 3: In your Colab environment
/content/.cache/4DHumans/logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt
```

**Check the file exists:**
```bash
ls -lh path/to/epoch=35-step=1000000.ckpt
# Should show ~2.5GB file
```

---

## Step 2: Upload to Google Drive

### Option A: Web Interface (Recommended - Most Reliable)

1. Go to [Google Drive](https://drive.google.com)
2. Click **"New"** → **"File upload"**
3. Select `epoch=35-step=1000000.ckpt` (the 2.5GB file)
4. Wait for upload to complete (may take 10-30 minutes)
5. **Right-click** the uploaded file → **"Share"** → **"Change to anyone with the link"**
6. Click **"Copy link"**
7. The URL will look like:
   ```
   https://drive.google.com/file/d/1ABC123XYZ789.../view?usp=sharing
   ```
8. **Extract the FILE ID** (the long string between `/d/` and `/view`):
   ```
   FILE_ID = 1ABC123XYZ789...
   ```

### Option B: Using gdown CLI (if you have it installed)

```bash
# Install gdown if needed
pip install gdown

# Upload (requires Google Drive API credentials)
# Note: gdown is primarily for downloading, not uploading
# For uploading, use the web interface or Google Drive API
```

---

## Step 3: Set Environment Variable in RunPod

1. Go to [RunPod Dashboard](https://www.runpod.io/console)
2. Navigate to **Serverless** → Your endpoint (`tryonline` or similar)
3. Click **"Edit"** or **"Settings"**
4. Scroll to **"Environment Variables"**
5. Add a new variable:
   - **Key:** `GOOGLE_DRIVE_CHECKPOINT_ID`
   - **Value:** `YOUR_FILE_ID_HERE` (paste the file ID from Step 2)
6. Click **"Save"** or **"Update"**

---

## Step 4: Deploy Updated Docker Image

The Dockerfile already includes `gdown` and the handler already has Google Drive download logic. 

**After setting the environment variable:**

1. The container will automatically download the checkpoint on first use
2. Download happens when `download_models()` is called (during pipeline initialization)
3. The file will be cached in `/workspace/.cache/4DHumans/` for subsequent runs

---

## Step 5: Test the Setup

1. Send a test job to your RunPod endpoint
2. Check the logs in RunPod dashboard → **Logs** tab
3. You should see:
   ```
   Checkpoint not found. Attempting to download from Google Drive...
   Downloading from: https://drive.google.com/uc?id=YOUR_FILE_ID
   (This may take 10-30 minutes for 2.5GB file...)
   ✅ Checkpoint downloaded from Google Drive!
   ```

---

## Troubleshooting

### "Checkpoint not found" error
- **Check:** Environment variable `GOOGLE_DRIVE_CHECKPOINT_ID` is set correctly in RunPod
- **Check:** File ID is correct (no extra spaces or characters)
- **Check:** Google Drive file is shared as "Anyone with the link"

### "Download failed" error
- **Check:** File size matches (should be ~2.5GB)
- **Try:** Re-sharing the file with a fresh link
- **Try:** Verify the file ID in a browser: `https://drive.google.com/uc?id=YOUR_FILE_ID`

### Download too slow
- **Note:** First download takes 10-30 minutes (2.5GB on first worker startup)
- **Solution:** The file is cached after first download, so subsequent runs are instant
- **Alternative:** Use RunPod Volumes to pre-upload the file (but S3 upload is slow)

---

## Alternative: Hardcode File ID in Code

If you prefer not to use environment variables, you can hardcode the file ID in:

```
avatar-creation/4D-Humans-clean/hmr2/models/__init__.py
```

Change line ~100:
```python
GOOGLE_DRIVE_CHECKPOINT_FILE_ID = "YOUR_FILE_ID_HERE"  # Hardcoded
```

But **environment variable is preferred** (easier to change without rebuilding image).

---

## Summary

1. ✅ Upload `epoch=35-step=1000000.ckpt` to Google Drive
2. ✅ Get file ID from share link
3. ✅ Set `GOOGLE_DRIVE_CHECKPOINT_ID` environment variable in RunPod
4. ✅ Test with a job - checkpoint downloads automatically on first run

**The checkpoint will be cached after first download, so future runs are fast!**
