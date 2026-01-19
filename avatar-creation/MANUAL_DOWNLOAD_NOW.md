# Manual Download Guide (Browser Downloads Work!)

## ✅ Good News: You Can Download Manually!

Since browser downloads work (even when `gdown` fails), you can download all files **right now** and upload them to RunPod volume. This is actually **faster** than waiting for quota reset!

---

## Step 1: Download All Files Manually 📥

Open these links in your browser and download each file:

### 1. Checkpoint (2.5GB) - Most Important!
```
https://drive.google.com/uc?id=1ISfMrpiiwoSzLoQXsXsX5FUcOxZY5Bzu
```
**Save as:** `epoch=35-step=1000000.ckpt`

### 2. SMPL Neutral Model (~247MB)
```
https://drive.google.com/uc?id=1A2qaP3xWZRuBOPaNx0-tovBBhtftxuSv
```
**Save as:** `basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl`

### 3. SMPL Male Model (~247MB)
```
https://drive.google.com/uc?id=1MYc-Qduvki8xcvEGQSwmCiEhg3Ehs0o5
```
**Save as:** `basicmodel_m_lbs_10_207_0_v1.1.0.pkl`

### 4. SMPL Female Model (~247MB)
```
https://drive.google.com/uc?id=1Xr4UaC8job6f0UPMnwwzWRi3pxf8znoE
```
**Save as:** `basicmodel_f_lbs_10_207_0_v1.1.0.pkl`

### 5. Mean Params (Small file)
```
https://drive.google.com/uc?id=1cqbspPE9LM2ysB_YvBcRZR3JGVb3ve_I
```
**Save as:** `smpl_mean_params.npz`

### 6. Joint Regressor (Small file)
```
https://drive.google.com/uc?id=1hoGaaioCh9bo3jNY84N3A5VB51DRqnQE
```
**Save as:** `SMPL_to_J19.pkl`

---

## Step 2: Organize Files Locally 📁

Create a folder structure matching what RunPod expects:

```bash
# Create directory
mkdir -p ~/models_4dhumans/checkpoints
mkdir -p ~/models_4dhumans/data

# Move downloaded files to correct locations
# (Adjust paths based on where your browser saved them)

# Checkpoint
mv ~/Downloads/epoch=35-step=1000000.ckpt ~/models_4dhumans/checkpoints/

# SMPL models
mv ~/Downloads/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl ~/models_4dhumans/data/
mv ~/Downloads/basicmodel_m_lbs_10_207_0_v1.1.0.pkl ~/models_4dhumans/data/
mv ~/Downloads/basicmodel_f_lbs_10_207_0_v1.1.0.pkl ~/models_4dhumans/data/

# Supporting files
mv ~/Downloads/smpl_mean_params.npz ~/models_4dhumans/data/
mv ~/Downloads/SMPL_to_J19.pkl ~/models_4dhumans/data/
```

---

## Step 3: Upload to RunPod Volume ☁️

### Option A: Using RunPod Web Interface (Easiest)

1. **Go to RunPod Dashboard:**
   - Visit: https://www.runpod.io/console/storage
   - Find your Network Volume

2. **Upload Files:**
   - Click on your volume
   - Navigate to or create: `4DHumans/`
   - Create folder structure:
     ```
     4DHumans/
     ├── logs/train/multiruns/hmr2/0/checkpoints/
     │   └── epoch=35-step=1000000.ckpt
     └── data/
         ├── basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl
         ├── basicmodel_m_lbs_10_207_0_v1.1.0.pkl
         ├── basicmodel_f_lbs_10_207_0_v1.1.0.pkl
         ├── smpl_mean_params.npz
         └── SMPL_to_J19.pkl
     ```
   - Upload each file to the correct location

### Option B: Using S3 API (If Available)

I can create a script to upload via S3 API if you prefer. Let me know!

---

## Step 4: Verify Upload ✅

After uploading, the next job should automatically find the models:

**Expected log output:**
```
[RunPod] Network Volume detected at /runpod-volume
[Config] Using RunPod Network Volume cache: /runpod-volume/4DHumans
[DEBUG download_models] ✓ Found checkpoint in Network Volume: /runpod-volume/4DHumans/logs/.../epoch=35-step=1000000.ckpt (2.50 GB)
✅ Checkpoint found in cache (volume working!)
```

---

## Why This Works Better 🎯

- ✅ **No quota issues** - Browser downloads bypass programmatic limits
- ✅ **Works immediately** - No waiting 24 hours
- ✅ **One-time setup** - Files persist in volume forever
- ✅ **Faster jobs** - No download time at runtime

---

## Quick Checklist ✅

- [ ] Downloaded checkpoint (2.5GB)
- [ ] Downloaded all 3 SMPL models (~247MB each)
- [ ] Downloaded supporting files (mean params, joint regressor)
- [ ] Organized files in correct folder structure
- [ ] Uploaded to RunPod volume in correct paths
- [ ] Verified upload (check file sizes in RunPod)
- [ ] Tested a job (should find models automatically)

---

## Need Help?

If you need help with:
- Creating upload script
- Verifying file paths
- Troubleshooting upload issues

Just ask! 🚀
