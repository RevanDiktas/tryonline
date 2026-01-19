# Quick Setup: Use Dropbox Instead of Google Drive

## Why Dropbox?
- ✅ No quota limits (for reasonable usage)
- ✅ Faster downloads
- ✅ Can upload from your browser (fast)
- ✅ Works TODAY - no waiting!

---

## Step 1: Upload Files to Dropbox

### Option A: Upload via Browser (Easiest)

1. **Go to Dropbox:** https://www.dropbox.com
2. **Create a folder:** `4dhumans-models` (or any name)
3. **Upload all 6 files:**
   - `epoch=35-step=1000000.ckpt` (2.5GB)
   - `basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl` (236MB)
   - `basicmodel_m_lbs_10_207_0_v1.1.0.pkl` (236MB)
   - `basicmodel_f_lbs_10_207_0_v1.1.0.pkl` (236MB)
   - `smpl_mean_params.npz` (small)
   - `SMPL_to_J19.pkl` (1MB)

4. **Make folder public:**
   - Right-click folder → Share → Create link
   - Or: Settings → Make public

5. **Get share links for each file:**
   - Right-click each file → Share → Copy link
   - Save all 6 links

### Option B: Upload via Dropbox App (Faster)

1. Install Dropbox desktop app
2. Drag files to Dropbox folder
3. Get share links (same as above)

---

## Step 2: Get Direct Download Links

For each file, convert the share link to direct download:

**Share link format:**
```
https://www.dropbox.com/s/XXXXX/filename.pkl?dl=0
```

**Direct download (change `dl=0` to `dl=1`):**
```
https://www.dropbox.com/s/XXXXX/filename.pkl?dl=1
```

**OR use this format:**
```
https://dl.dropboxusercontent.com/s/XXXXX/filename.pkl
```

---

## Step 3: Update Download Script

I'll update the script to use Dropbox URLs. You'll just need to provide the 6 Dropbox links.

---

## Step 4: Test Download Speed

Dropbox should be MUCH faster:
- No quota limits
- Better CDN
- Should download in ~10-20 minutes during build

---

## Quick Checklist

- [ ] Upload all 6 files to Dropbox
- [ ] Make folder/file public
- [ ] Get direct download links (dl=1 format)
- [ ] Update download script with Dropbox URLs
- [ ] Trigger Docker build
- [ ] Done! (~20-30 min build time)

---

**This will work TODAY and be much faster!** 🚀
