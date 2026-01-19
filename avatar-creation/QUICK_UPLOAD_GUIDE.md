# Quick Guide: Download & Upload Models to RunPod Volume

## 📥 Step 1: Download These 6 Files from Browser

Open each link in your browser and download. **Browser downloads work even when `gdown` fails!**

### File 1: Checkpoint (2.5GB) - MOST IMPORTANT
**Link:** https://drive.google.com/uc?id=1ISfMrpiiwoSzLoQXsXsX5FUcOxZY5Bzu  
**Save as:** `epoch=35-step=1000000.ckpt`  
**Size:** ~2.5GB  
**Time:** ~10-20 minutes

### File 2: SMPL Neutral Model (~247MB)
**Link:** https://drive.google.com/uc?id=1A2qaP3xWZRuBOPaNx0-tovBBhtftxuSv  
**Save as:** `basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl`  
**Size:** ~247MB  
**Time:** ~2-3 minutes

### File 3: SMPL Male Model (~247MB)
**Link:** https://drive.google.com/uc?id=1MYc-Qduvki8xcvEGQSwmCiEhg3Ehs0o5  
**Save as:** `basicmodel_m_lbs_10_207_0_v1.1.0.pkl`  
**Size:** ~247MB  
**Time:** ~2-3 minutes

### File 4: SMPL Female Model (~247MB)
**Link:** https://drive.google.com/uc?id=1Xr4UaC8job6f0UPMnwwzWRi3pxf8znoE  
**Save as:** `basicmodel_f_lbs_10_207_0_v1.1.0.pkl`  
**Size:** ~247MB  
**Time:** ~2-3 minutes

### File 5: Mean Params (Small)
**Link:** https://drive.google.com/uc?id=1cqbspPE9LM2ysB_YvBcRZR3JGVb3ve_I  
**Save as:** `smpl_mean_params.npz`  
**Size:** ~few MB

### File 6: Joint Regressor (Small)
**Link:** https://drive.google.com/uc?id=1hoGaaioCh9bo3jNY84N3A5VB51DRqnQE  
**Save as:** `SMPL_to_J19.pkl`  
**Size:** ~few MB

---

## 📁 Step 2: Organize Files Locally

After downloading, organize them like this on your computer:

```
~/models_4dhumans/
├── checkpoints/
│   └── epoch=35-step=1000000.ckpt  (2.5GB)
└── data/
    ├── basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl  (~247MB)
    ├── basicmodel_m_lbs_10_207_0_v1.1.0.pkl  (~247MB)
    ├── basicmodel_f_lbs_10_207_0_v1.1.0.pkl  (~247MB)
    ├── smpl_mean_params.npz
    └── SMPL_to_J19.pkl
```

**Quick commands to organize:**
```bash
# Create folders
mkdir -p ~/models_4dhumans/checkpoints
mkdir -p ~/models_4dhumans/data

# Move files (adjust paths based on where browser saved them)
# Usually saved to ~/Downloads/ on Mac
mv ~/Downloads/epoch=35-step=1000000.ckpt ~/models_4dhumans/checkpoints/
mv ~/Downloads/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl ~/models_4dhumans/data/
mv ~/Downloads/basicmodel_m_lbs_10_207_0_v1.1.0.pkl ~/models_4dhumans/data/
mv ~/Downloads/basicmodel_f_lbs_10_207_0_v1.1.0.pkl ~/models_4dhumans/data/
mv ~/Downloads/smpl_mean_params.npz ~/models_4dhumans/data/
mv ~/Downloads/SMPL_to_J19.pkl ~/models_4dhumans/data/
```

---

## ☁️ Step 3: Upload to RunPod Volume

### Method A: RunPod Web Interface (Easiest)

1. **Go to RunPod Storage:**
   - Visit: https://www.runpod.io/console/storage
   - Log in to your account

2. **Find Your Network Volume:**
   - Click on "Network Volumes" or "Volumes"
   - Find the volume you're using (the one mounted at `/runpod-volume`)

3. **Create Folder Structure:**
   - Click on your volume
   - Create folder: `4DHumans`
   - Inside `4DHumans`, create:
     - `logs/train/multiruns/hmr2/0/checkpoints/`
     - `data/`

4. **Upload Files:**
   - Navigate to: `4DHumans/logs/train/multiruns/hmr2/0/checkpoints/`
   - Upload: `epoch=35-step=1000000.ckpt` (2.5GB - this will take a while!)
   
   - Navigate to: `4DHumans/data/`
   - Upload all 5 files:
     - `basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl`
     - `basicmodel_m_lbs_10_207_0_v1.1.0.pkl`
     - `basicmodel_f_lbs_10_207_0_v1.1.0.pkl`
     - `smpl_mean_params.npz`
     - `SMPL_to_J19.pkl`

### Method B: Using S3 API (If Web Interface Doesn't Work)

I can create a Python script to upload via S3 API. Let me know if you need this!

---

## ✅ Step 4: Verify Upload

After uploading, the file structure on your volume should be:

```
/runpod-volume/4DHumans/
├── logs/
│   └── train/
│       └── multiruns/
│           └── hmr2/
│               └── 0/
│                   └── checkpoints/
│                       └── epoch=35-step=1000000.ckpt  (2.5GB)
└── data/
    ├── basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl  (~247MB)
    ├── basicmodel_m_lbs_10_207_0_v1.1.0.pkl  (~247MB)
    ├── basicmodel_f_lbs_10_207_0_v1.1.0.pkl  (~247MB)
    ├── smpl_mean_params.npz
    └── SMPL_to_J19.pkl
```

---

## 🧪 Step 5: Test It Works

Run a test avatar creation job. In the logs, you should see:

```
[RunPod] Network Volume detected at /runpod-volume
[Config] Using RunPod Network Volume cache: /runpod-volume/4DHumans
[DEBUG download_models] ✓ Found checkpoint in Network Volume: /runpod-volume/4DHumans/logs/.../epoch=35-step=1000000.ckpt (2.50 GB)
✅ Checkpoint found in cache (volume working!)
```

If you see this → **Success!** ✅ Models are working!

---

## 📋 Quick Checklist

- [ ] Downloaded checkpoint (2.5GB)
- [ ] Downloaded 3 SMPL models (~247MB each)
- [ ] Downloaded 2 supporting files
- [ ] Organized files in folders
- [ ] Created folder structure in RunPod volume
- [ ] Uploaded checkpoint to `4DHumans/logs/train/multiruns/hmr2/0/checkpoints/`
- [ ] Uploaded 5 data files to `4DHumans/data/`
- [ ] Verified file sizes match
- [ ] Tested a job - models found automatically

---

## ⚠️ Important Notes

1. **Checkpoint is 2.5GB** - Upload will take 10-30 minutes depending on your internet
2. **Volume must be mounted** - Make sure your RunPod endpoint has the volume attached
3. **Exact paths matter** - Files must be in the exact paths shown above
4. **One-time setup** - Once uploaded, models persist forever!

---

## Need Help?

If you run into issues:
- Can't find volume in RunPod dashboard
- Upload fails or times out
- Files not found after upload
- Need S3 API upload script

Just ask! 🚀
